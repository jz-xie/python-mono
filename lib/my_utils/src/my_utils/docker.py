from my_utils.aws.session_handler import get_account_id
import subprocess
import shlex
from shlex import quote


def docker_login_ecr(aws_account_id: str, region: str = "us-east-1"):
    get_cred = f"aws ecr get-login-password --region {region}"
    login = f"docker login --username AWS --password-stdin {aws_account_id}.dkr.ecr.{region}.amazonaws.com"
    cred = subprocess.Popen(shlex.split(f"{get_cred}"), stdout=subprocess.PIPE)
    subprocess.run(shlex.split(f"{login}"), stdin=cred.stdout)


def docker_build_image(
    project_name: str,
    tag: str = "latest",
    docker_file_path: str = "Dockerfile",
    ssh_key_path: str = "$HOME/.ssh/id_rsa",
) -> None:
    image = quote(f"{project_name}:{tag}")
    subprocess.run(
        shlex.split(
            f"docker buildx build . -t {image} -f {quote(docker_file_path)} --ssh default={quote(ssh_key_path)}"
        )
    )


def docker_push_image(
    project_name: str,
    tag: str = "latest",
    region: str = "us-east-1",
) -> None:
    aws_account_id = get_account_id()
    ecr_url = quote(f"{aws_account_id}.dkr.ecr.{region}.amazonaws.com")
    image = quote(f"{project_name}:{tag}")
    docker_login_ecr(aws_account_id, region)
    subprocess.run(shlex.split(f"docker tag {image} {ecr_url}/{image}"))
    subprocess.run(shlex.split(f"docker push {ecr_url}/{image}"))


# def docker_build_push_image(
#     project_name: str,
#     tag: str = "latest",
#     region: str = "us-east-1",
#     docker_file_path: str = "Dockerfile",
# ) -> None:
#     """Create and push Docker image to AWS ECR"""
#     aws_account_id = get_account_id()
#     docker_login_ecr(aws_account_id, region)
#     docker_push_image(
#         quote(project_name),
#         aws_account_id,
#         quote(tag),
#         quote(region),
#         quote(docker_file_path),
#     )


# docker_login_ecr(aws_account_id=get_account_id())
