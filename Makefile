dev:
	minikube start && kubectl apply  -k kustomize/overlays/dev
prod:
	minikube start && kubectl apply  -k kustomize/overlays/prod
delete-dev:
	kubectl delete  -k kustomize/overlays/dev && minikube stop
delete-prod:
	kubectl delete  -k kustomize/overlays/prod && minikube stop