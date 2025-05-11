import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

def send_email(to_email, subject, html_content):
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = "you@example.com"
    msg['To'] = to_email

    part = MIMEText(html_content, 'html')
    msg.attach(part)

    with smtplib.SMTP('smtp.example.com', 587) as server:
        server.starttls()
        server.login('you@example.com', 'your_password')
        server.sendmail(msg['From'], [msg['To']], msg.as_string())
