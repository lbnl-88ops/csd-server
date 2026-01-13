from dataclasses import dataclass
from pathlib import Path
from typing import List
from typing_extensions import Annotated

from flask import Flask, jsonify, send_file
import typer
from rich import print

typer_app = typer.Typer(
    help="Charge state distribute file server.", no_args_is_help=True
)
app = Flask(__name__)


@dataclass(init=False)
class ServerState:
    directory: Path


state = ServerState()


def list_files(directory: Path) -> List[Path]:
    files = list(directory.glob("csd_*"))
    return files


@app.route("/files", methods=["GET"])
def files():
    return jsonify([str(f) for f in list_files(state.directory)])


@app.route("/download/<filename>", methods=["GET"])
def download_file(filename):
    file_path = state.directory / filename
    if file_path.exists():
        return send_file(file_path, as_attachment=True)
    else:
        return jsonify({"error": "File not found"}), 404


@typer_app.command()
def main(
    csd_directory: Annotated[Path, typer.Argument(help="Directory to serve")],
    port: Annotated[int, typer.Option(help="Port to use")] = 5000,
):
    directory = csd_directory.resolve()
    if not csd_directory.exists():
        print(f"[red]Directory {directory} does not exist[/red]")
        raise typer.Abort()
    print(f"Serving files from {directory}")
    files = list_files(csd_directory)
    print(f"Serving [bold]{len(files)}[/bold] CSD files")
    state.directory = directory
    app.run("0.0.0.0", port)


if __name__ == "__main__":
    typer_app()
