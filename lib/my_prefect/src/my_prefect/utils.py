from typing import Optional

from prefect import Flow
from prefect.blocks.core import Block
from prefect.deployments import Deployment
from prefect.filesystems import S3
from prefect.infrastructure import KubernetesJob
from prefect.server.schemas.schedules import SCHEDULE_TYPES

PREFECT_S3_BUCKET = "prefect-s3-storage"
K8S_BLOCK_NAME = "k8s"

REMOTE_RAY_ADRESS = (
    "ray://raycluster-kuberay-head-svc.ray.svc.cluster.local:10001"
)
# https://docs.ray.io/en/latest/cluster/kubernetes/user-guides/config.html


# def create_s3_filesystem(s3_bucket: str = PREFECT_S3_BUCKET) -> None:
#     block = S3(
#         bucket_path=f"{s3_bucket}",
#     )
#     block.save(name=PREFECT_S3_BUCKET, overwrite=True)
from typing import Pattern, Match
import re

re.Pattern
# '^([+-]?[0-9.]+)([eEinumkKMGTP]*[-+]?[0-9]*)$'


def create_k8s_job(name: str = K8S_BLOCK_NAME) -> None:
    block_k8s = KubernetesJob(
        name=name,
        finished_job_ttl=30,
        env={"EXTRA_PIP_PACKAGES": "s3fs"},
        namespace="prefect",
    )
    block_k8s.save(name="k8s", overwrite=True)


def create_deployment_from_flow(
    flow: Flow,
    deployment_name: str,
    service_account_name: str,
    image: Optional[str] = None,
    cpu_request: Optional[str] = "4000m",
    cpu_limit: Optional[str] = "8000m",
    memory_request: Optional[str] = "4Gi",
    memory_limit: Optional[str] = "8Gi",
    version: Optional[str] = None,
    schedule: Optional[SCHEDULE_TYPES] = None,
    work_queue_name: Optional[str] = "default",
) -> None:
    storage = S3(
        bucket_path=f"{PREFECT_S3_BUCKET}/{flow.name}/{deployment_name}/"
    )
    kubernetes_job_block = KubernetesJob.load(K8S_BLOCK_NAME)
    deployment = Deployment.build_from_flow(
        flow=flow,
        name=deployment_name,
        version=version,
        work_queue_name=work_queue_name,
        storage=storage,
        schedule=schedule,
        infrastructure=kubernetes_job_block,
        infra_overrides={
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
