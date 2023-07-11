import shlex
import subprocess
from shlex import quote
from typing import Any, Dict, Optional

import typer
from prefect import Flow
from prefect.blocks.core import Block
from prefect.deployments import Deployment
from prefect.filesystems import S3
from prefect.infrastructure import KubernetesJob
from prefect.infrastructure.kubernetes import KubernetesImagePullPolicy
from prefect.server.schemas.schedules import SCHEDULE_TYPES
from rich import print
from my_utils_cli.eks import connect_eks

PREFECT_S3_BUCKET_STAGING = "bigdata-prefect-storage-staging"
PREFECT_S3_BUCKET_PRODUCTION = "bigdata-prefect-storage-production"
K8S_BLOCK_NAME = "k8s"


# https://docs.ray.io/en/latest/cluster/kubernetes/user-guides/config.html


# def create_s3_filesystem(s3_bucket: str) -> None:
#     block = S3(
#         bucket_path=f"{s3_bucket}",
#     )
#     block.save(name=s3_bucket, overwrite=True)
# from typing import Pattern, Match
# import re

# re.Pattern
# '^([+-]?[0-9.]+)([eEinumkKMGTP]*[-+]?[0-9]*)$'


app = typer.Typer()

def create_k8s_job(name: str = K8S_BLOCK_NAME) -> None:
    block_k8s = KubernetesJob(
        name=name,
        finished_job_ttl=30,
        pod_watch_timeout_seconds=300,
        env={
            "EXTRA_PIP_PACKAGES": "s3fs",
            "PREFECT_LOGGING_EXTRA_LOGGERS": "my_logger",
        },
        namespace="prefect",
        image_pull_policy=KubernetesImagePullPolicy.ALWAYS.value,
    )
    block_k8s.save(name="k8s", overwrite=True)

def create_deployment_from_flow(
    flow: Flow,
    deployment_name: str,
    service_account_name: str,
    image: Optional[str] = None,
    flow_parameters: Optional[Dict[str, Any]] = None,
    s3_storage_bucket: Optional[str] = PREFECT_S3_BUCKET_STAGING,
    cpu_request: Optional[str] = "2000m",
    cpu_limit: Optional[str] = "8000m",
    memory_request: Optional[str] = "2Gi",
    memory_limit: Optional[str] = "8Gi",
    version: Optional[str] = None,
    schedule: Optional[SCHEDULE_TYPES] = None,
    work_queue_name: Optional[str] = "default",
) -> None:
    storage = S3(
        bucket_path=f"{s3_storage_bucket}/{flow.name}/{deployment_name}/"
    )
    k8s_job_name = f"{flow.name}-{deployment_name}"
    kubernetes_job_block = KubernetesJob.load(K8S_BLOCK_NAME)
    deployment = Deployment.build_from_flow(
        flow=flow,
        name=deployment_name,
        version=version,
        work_queue_name=work_queue_name,
        parameters=flow_parameters,
        storage=storage,
        schedule=schedule,
        infrastructure=kubernetes_job_block,
        infra_overrides={
            "name": k8s_job_name,
            "EXTRA_PIP_PACKAGES": "s3fs",
            "service_account_name": service_account_name,
            "image": image,
            "customizations": [
                {
                    "op": "add",
                    "path": "/spec/template/spec/containers/0/resources",
                    "value": {
                        "requests": {
                            "cpu": cpu_request,
                            "memory": memory_request,
                        },
                        "limits": {
                            "cpu": cpu_limit,
                            "memory": memory_limit,
                        },
                    },
                }
            ],
        },
    )
    deployment.apply()


@app.command()
def connect_remote_prefect(
    eks_cluster_name: str, localhost_port: int = 4200
) -> None:
    """Create live connection to Prefect on EKS"""
    connect_eks(quote(eks_cluster_name))
    prefect_api_url = f"http://localhost:{localhost_port}/api"
    subprocess.run(
        shlex.split(f"prefect config set PREFECT_API_URL={prefect_api_url}")
    )
    pod_name = subprocess.check_output(
        shlex.split(
            'kubectl get pods --namespace prefect -l "app.kubernetes.io/name=prefect-server,app.kubernetes.io/instance=prefect-server" -o jsonpath="{.items[0].metadata.name}"'
        )
    ).decode("utf-8")
    container_port = subprocess.check_output(
        shlex.split(
            f'kubectl get pod --namespace prefect {pod_name} -o jsonpath="{{.spec.containers[0].ports[0].containerPort}}"'
        )
    ).decode("utf-8")
    print(f"Visit {prefect_api_url} to use your application")
    subprocess.run(
        shlex.split(
            f"kubectl port-forward {pod_name} {localhost_port}:{container_port} --namespace prefect --address localhost"
        )
    )


@app.callback()
def callback() -> None:
    # Description for the CLI app
    """Work with Prefect on EKS"""
    pass


if __name__ == "__main__":
    create_k8s_job()
