import typer

# from my_utils import __version__ as version

from my_utils.docker import docker_build_image, docker_push_image
from rich import print

app = typer.Typer()


LOGO = rf"""
   ___  ______  _   _ _   _ _     
  |_  ||___  / | | | | | (_) |    
    | |   / /  | | | | |_ _| |___ 
    | |  / /   | | | | __| | / __|
/\__/ /./ /___ | |_| | |_| | \__ \
\____/ \_____/  \___/ \__|_|_|___/  v{version}
"""

LOGO_FOOTNOTE = "Made by [blue]JZ[/blue]"


# @click.group(name="my_utils")
# @click.version_option(
#     version, "--version", "-V", help="Show version and exit."
# )


@app.callback()
def callback() -> None:
    """my_utils CLI"""
    pass


@app.command()
def info() -> None:
    """Get more information about my_utils."""
    print(f"[bold green]{LOGO}")
    print(LOGO_FOOTNOTE)
    # click.echo(LOGO_FOOTNOTE)


app.command()(docker_build_image)
app.command()(docker_push_image)
# main.add_command(create)
# main.add_command(login_aws)
# main.add_command(flows_cli)
