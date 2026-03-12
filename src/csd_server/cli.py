from dataclasses import dataclass
import os
from pathlib import Path
from typing import List

from flask import Flask, jsonify, send_file
import typer
from rich import print


CSD_DIRECTORY = os.getenv("CSD_DIRECTORY")
EMITTANCE_DIRECTORY = os.getenv("EMITTANCE_DIRECTORY")


@dataclass(init=False)
class ServerState:
    csd_directory: Path
    emittance_directory: Path


state = ServerState()


def list_files(directory: Path, glob="csd_*") -> List[Path]:
    files = list(directory.glob(glob))
    return files


def create_app():
    if CSD_DIRECTORY is None or EMITTANCE_DIRECTORY is None:
        raise RuntimeError()
    app = Flask(__name__)

    @app.route("/files", methods=["GET"])
    def files():
        return jsonify([str(f) for f in list_files(state.csd_directory, "csd_*")])

    @app.route("/emittance_files", methods=["GET"])
    def emittance_files():
        return jsonify(
            [str(f) for f in list_files(state.emittance_directory, "emittance_scan_*")]
        )

    @app.route("/download/<filename>", methods=["GET"])
    def download_file(filename):
        for directory in [state.csd_directory, state.emittance_directory]:
            file_path = directory / filename
            if file_path.exists():
                return send_file(file_path, as_attachment=True)
        else:
            return jsonify({"error": "File not found"}), 404

    csd_directory = Path(CSD_DIRECTORY).resolve()
    emittance_directory = Path(EMITTANCE_DIRECTORY).resolve()

    for directory in [csd_directory, emittance_directory]:
        if not directory.exists():
            print(f"[red]Directory {directory} does not exist[/red]")
            raise typer.Abort()
    print(f"Serving files from {csd_directory}, {emittance_directory}")
    print(f"Serving [bold]{len(list_files(csd_directory))}[/bold] CSD files")
    print(
        f"Serving [bold]{len(list_files(csd_directory, 'emittance_scan_*'))}[/bold] CSD files"
    )
    state.csd_directory = csd_directory
    state.emittance_directory = emittance_directory
    return app


if __name__ == "__main__":
    app = create_app()
    app.run()
