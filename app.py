from flask import Flask, request, jsonify
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from pymongo import MongoClient
import datetime
import uuid
import json
import os

def create_app():
    app = Flask(__name__)
    return app

app = create_app()
scheduler = BackgroundScheduler()
scheduler.start()

# Connect to MongoDB and use the 'slack' database
MONGO_URI = os.getenv('MONGO_URI',"mongodb://127.0.0.1:27017")
print(MONGO_URI)
client = MongoClient(MONGO_URI)
db = client["slack"]
collection = db["scheduled_jobs"]

print("Connected to MongoDB database: slack", flush=True)

def print_message(job_id, message):
    """Ensures only one pod executes the job using a MongoDB lock."""
    job = collection.find_one_and_update(
        {"job_id": job_id, "status": "pending"},
        {"$set": {"status": "in_progress", "last_attempted_at": datetime.datetime.now()}},
        return_document=True
    )

    if job:
        print(f"Scheduled Message (Job ID: {job_id}): {message}", flush=True)

        # Mark the job as completed after execution
        if(job['is_job_recurring']):
            update_data = {"$set": {"executed_at": datetime.datetime.now(), "status": "pending"}}
        else:
            update_data = {"$set": {"executed_at": datetime.datetime.now(), "status": "completed"}}

        collection.update_one({"job_id": job_id}, update_data)

def add_job_to_scheduler(job_id, message, date_time, repeat_days):
    """Adds a job to the APScheduler with a distributed execution mechanism."""
    if repeat_days:
        repeat_days = [day.lower() for day in repeat_days]
        scheduler.add_job(
            print_message,
            trigger=CronTrigger(day_of_week=','.join(repeat_days), hour=date_time.hour, minute=date_time.minute),
            args=[job_id, message],
            id=job_id,
            replace_existing=True
        )
        print(scheduler.print_jobs())
    else:
        scheduler.add_job(
            print_message,
            trigger='date',
            run_date=date_time,
            args=[job_id, message],
            id=job_id,
            replace_existing=True
        )

@app.route('/schedule', methods=['POST'])
def schedule_message():
    """API to schedule a new message."""
    data = request.get_json()
    message = data.get("message")
    date_time_str = data.get("date_time")
    repeat_days = data.get("repeat_days", []) or []
    is_job_recurring = False

    if repeat_days:
        is_job_recurring = True

    if not message or not date_time_str:
        return jsonify({"error": "Message and date_time are required"}), 400

    try:
        date_time = datetime.datetime.strptime(date_time_str, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return jsonify({"error": "Invalid date_time format. Use 'YYYY-MM-DD HH:MM:SS'"}), 400

    job_id = str(uuid.uuid4())
    
    
    collection.insert_one({
        "job_id": job_id,
        "message": message,
        "date_time": date_time,
        "repeat_days": repeat_days,
        "status": "pending",
        "is_job_recurring": is_job_recurring,
        "executed_at": None,
        "last_attempted_at": None
    })

    add_job_to_scheduler(job_id, message, date_time, repeat_days)
    return jsonify({"message": "Scheduled successfully", "job_id": job_id})

@app.route('/jobs', methods=['GET'])
def get_jobs():
    """API to get all scheduled jobs."""
    jobs = list(collection.find({}, {"_id": 0}))
    for job in jobs:
        job["date_time"] = job["date_time"].isoformat()
        if job.get("executed_at"):
            job["executed_at"] = job["executed_at"].isoformat()
    return jsonify(jobs)

@app.route('/delete/<job_id>', methods=['DELETE'])
def delete_job(job_id):
    """API to delete a job."""
    job = collection.find_one({"job_id": job_id})
    if job:
        scheduler.remove_job(job_id)
        collection.delete_one({"job_id": job_id})
        return jsonify({"message": "Job deleted successfully"})
    return jsonify({"error": "Job not found"}), 404

def retry_stuck_jobs():
    """Retries jobs that might be stuck due to pod crashes."""
    stuck_jobs = collection.find({"status": "in_progress"})
    for job in stuck_jobs:
        job_id = job["job_id"]
        last_attempted_at = job.get("last_attempted_at", datetime.datetime.now())

        # Retry if the job has been stuck for more than 5 minutes
        if (datetime.datetime.now() - last_attempted_at).total_seconds() > 300:
            print(f"Retrying stuck job: {job_id}", flush=True)
            collection.update_one({"job_id": job_id}, {"$set": {"status": "pending"}})

def load_pending_jobs():
    """Loads pending jobs and ensures they are scheduled."""
    with app.app_context():
        retry_stuck_jobs()  # Ensure stuck jobs are retried
        pending_jobs = collection.find({"status": "pending"})
        for job in pending_jobs:
            job_id = job["job_id"]
            message = job["message"]
            date_time = job["date_time"]
            repeat_days = job.get("repeat_days", [])
            
            if repeat_days:
                add_job_to_scheduler(job_id, message, date_time, repeat_days)
            else:
                if date_time > datetime.datetime.now():
                    add_job_to_scheduler(job_id, message, date_time, repeat_days)
                else:
                    print_message(job_id, message)

if __name__ == '__main__':
    print(f"System Time: {datetime.datetime.now()}")
    load_pending_jobs()
    app.run(host='0.0.0.0', port=5001, debug=True)
