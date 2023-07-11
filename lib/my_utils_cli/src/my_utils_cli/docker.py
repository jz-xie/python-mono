import pathlib
import shlex
import subprocess
from shlex import quote

import typer
from rich import print
from my_utils.aws.session_handler import get_account_id

app = typer.Typer()

def login_ecr(aws_account_id: str, region: str = "us-east-1"):
    get_cred = f"aws ecr get-login-password --region {region}"
    login = f"docker login --username AWS --password-stdin {aws_account_id}.dkr.ecr.{region}.amazonaws.com"
    cred = subprocess.Popen(shlex.split(f"{get_cred}"), stdout=subprocess.PIPE)
    subprocess.run(shlex.split(f"{login}"), stdin=cred.stdout)

@app.command()
def build_image(
    project_name: str,
    tag: str = "latest",
    docker_file_path: str = "Dockerfile",
    ssh_key_path: str = f"{pathlib.Path.home()}/.ssh/id_rsa",
    push_image: bool = False,
    region: str = "us-east-1",
) -> None:
    image = quote(f"{project_name}:{tag}")
    print(f"SSH key path: {ssh_key_path}")
    subprocess.run(
        shlex.split(
            f"docker buildx build . -t {image} -f {quote(docker_file_path)} --ssh default={quote(ssh_key_path)}"
        ),
    )
    if push_image:
        push_image(project_name=project_name, tag=tag, region=region)

@app.command()
def push_image(
    project_name: str,
    tag: str = "latest",
    region: str = "us-east-1",
) -> None:
    aws_account_id = get_account_id()
    ecr_url = quote(f"{aws_account_id}.dkr.ecr.{region}.amazonaws.com")
    image = quote(f"{project_name}:{tag}")
    login_ecr(aws_account_id, region)
    subprocess.run(shlex.split(f"docker tag {image} {ecr_url}/{image}"))
    subprocess.run(shlex.split(f"docker push {ecr_url}/{image}"))
    print(f"Pushed image to {ecr_url}/{image}")
