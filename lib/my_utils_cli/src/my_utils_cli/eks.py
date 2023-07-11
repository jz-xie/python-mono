import shlex
import subprocess
from shlex import quote
from typing import Any, Dict, Optional

import typer

app = typer.Typer()

@app.command()
def connect_eks(eks_cluster_name: str, update: bool = False) -> None:
    """Config EKS cluster to for kubectl"""
    eks_cluster_name = quote(eks_cluster_name)
    if update:
        update_kubeconfig = shlex.split(
            f"aws eks update-kubeconfig --name {eks_cluster_name}"
        )
        subprocess.run(update_kubeconfig)
    cluster_arn = subprocess.check_output(
        shlex.split(
            f"aws eks describe-cluster --name {eks_cluster_name} --query 'cluster.arn'"
        )
    ).decode("utf-8")
    activate_context = f"kubectl config use-context {cluster_arn}"
    subprocess.run(shlex.split(activate_context))