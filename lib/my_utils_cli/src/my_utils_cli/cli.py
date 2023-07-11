import typer

version = 0
from rich import print
from my_utils_cli import docker, prefect
from my_utils_cli.aws_login import login
from my_utils_cli.eks import connect_eks

app = typer.Typer()


app.add_typer(docker.app, name="docker")
app.add_typer(prefect.app, name="prefect")

LOGO = rf"""
   ___  ______  _   _ _   _ _     
  |_  ||___  / | | | | | (_) |    
    | |   / /  | | | | |_ _| |___ 
    | |  / /   | | | | __| | / __|
/\__/ /./ /___ | |_| | |_| | \__ \
\____/ \_____/  \___/ \__|_|_|___/  v{version}
"""

LOGO_FOOTNOTE = "Made by [blue]JZ[/blue]"



@app.callback()
def callback() -> None:
    """MY UTILS CLI"""
    pass


@app.command()
def info() -> None:
    """Get more information about my utils."""
    print(f"[bold green]{LOGO}")
    print(LOGO_FOOTNOTE)
    # click.echo(LOGO_FOOTNOTE)


app.command()(login)
app.command()(connect_eks)
# app.command()(docker_push_image)
