import shlex
import subprocess
from pathlib import Path

import typer

LOCALHOST_PORT = 4200
LOCALHOST_URL = f"http://localhost:{LOCALHOST_PORT}/api"
SCRIPTES_PATH = Path(__file__).parent.parent.parent.joinpath("scripts")

app = typer.Typer()


@app.command()
def connect_eks(eks_cluster_name: str, update: bool = False) -> None:
    """Config EKS cluster to for kubectl"""
    valid_eks_cluster_name = shlex.quote(eks_cluster_name)
    sh_path = SCRIPTES_PATH.joinpath("connect_eks.sh")
    sh_path.chmod(0o755)
    subprocess.run(
        [sh_path, valid_eks_cluster_name, str(update).lower()],
        check=True,
    )


@app.command()
def connect_remote_prefect(
    eks_cluster_name: str, localhost_port: int = 4200
) -> None:
    """Create live connection to Prefect on EKS"""
    sh_path = SCRIPTES_PATH.joinpath("connect_remote_prefect.sh")
    sh_path.chmod(0o755)
    subprocess.run(
        [
            sh_path,
            shlex.quote(eks_cluster_name),
            shlex.quote(str(localhost_port)),
        ],
        shell=False,
        check=True,
    )


@app.callback()
def callback() -> None:
    # Description for the CLI app
    """Work with Prefect on EKS"""
    pass
