#!/bin/bash

prefect config set PREFECT_API_URL=http://localhost:$2/api

cluster_arn=$(aws eks describe-cluster --name $1 --query 'cluster.arn' | tr -d '"')
kubectl config use-context $cluster_arn

export POD_NAME=$(kubectl get pods --namespace prefect -l "app.kubernetes.io/name=prefect-server,app.kubernetes.io/instance=prefect-server" -o jsonpath="{.items[0].metadata.name}")
export CONTAINER_PORT=$(kubectl get pod --namespace prefect $POD_NAME -o jsonpath="{.spec.containers[0].ports[0].containerPort}")
echo "Visit http://127.0.0.1:$2 to use your application"
kubectl port-forward $POD_NAME $2:$CONTAINER_PORT \
    --namespace prefect \
    --address localhost
