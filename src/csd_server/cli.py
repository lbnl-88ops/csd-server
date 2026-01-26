from dataclasses import dataclass
import os
from pathlib import Path
from typing import List
from typing_extensions import Annotated

from flask import Flask, jsonify, send_file
import typer
from rich import print


CSD_DIRECTORY = os.getenv("CSD_DIRECTORY")


@dataclass(init=False)
class ServerState:
    directory: Path


state = ServerState()


def list_files(directory: Path) -> List[Path]:
    files = list(directory.glob("csd_*"))
    return files


def create_app():
    if CSD_DIRECTORY is None:
        raise RuntimeError()
    app = Flask(__name__)

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

    csd_directory = Path(CSD_DIRECTORY)
    directory = csd_directory.resolve()
    if not csd_directory.exists():
        print(f"[red]Directory {directory} does not exist[/red]")
        raise typer.Abort()
    print(f"Serving files from {directory}")
    found_files = list_files(csd_directory)
    print(f"Serving [bold]{len(found_files)}[/bold] CSD files")
    state.directory = directory
    return app


if __name__ == "__main__":
    app = create_app()
    app.run()
