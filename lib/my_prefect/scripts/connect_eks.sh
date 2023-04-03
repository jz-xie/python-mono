#!/bin/bash
if $2 = true; then
    aws eks update-kubeconfig --name $1
fi
cluster_arn=$(aws eks describe-cluster --name $1 --query 'cluster.arn' | tr -d '"')
kubectl config use-context $cluster_arn
