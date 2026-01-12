from pathlib import Path
from typing_extensions import Annotated

import typer
from rich import print, style

app = typer.Typer(help="Charge state distribute file server.", no_args_is_help=True)


@app.command()
def main(csd_directory: Annotated[Path, typer.Argument(help="Directory to serve")]):
    if not csd_directory.exists():
        print(f"[red]Directory {csd_directory.absolute()} does not exist[/red]")
        raise typer.Abort()
    print(f"Serving files from {csd_directory.absolute()}")


if __name__ == "__main__":
    app()
