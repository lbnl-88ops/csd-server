from dataclasses import dataclass
import os
from pathlib import Path
from typing import List

from flask import Flask, jsonify, send_file, request
import typer
from rich import print

from .db import ServerDatabaseManager

CSD_DIRECTORY = os.getenv("CSD_DIRECTORY")
EMITTANCE_DIRECTORY = os.getenv("EMITTANCE_DIRECTORY")


@dataclass(init=False)
class ServerState:
    csd_directory: Path
    emittance_directory: Path
    db: ServerDatabaseManager


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

    # --- Database Endpoints ---
    @app.route("/db/users", methods=["GET"])
    def get_users():
        return jsonify(state.db.get_all_users())

    @app.route("/db/users/add", methods=["POST"])
    def add_user():
        username = request.json.get("username")
        success = state.db.add_user(username)
        return jsonify({"success": success})

    @app.route("/db/users/update_last_used", methods=["POST"])
    def update_last_used():
        username = request.json.get("username")
        success = state.db.update_last_used(username)
        return jsonify({"success": success})

    @app.route("/db/stats", methods=["GET"])
    def get_stats():
        username = request.args.get("username")
        eval_count, pending_count = state.db.get_user_stats(username)
        return jsonify({"eval_count": eval_count, "pending_count": pending_count})

    @app.route("/db/pending_random", methods=["GET"])
    def get_pending_random():
        username = request.args.get("username")
        timestamp = state.db.get_random_pending_timestamp(username)
        return jsonify({"csd_timestamp": timestamp})

    @app.route("/db/leaderboard", methods=["GET"])
    def get_leaderboard():
        return jsonify(state.db.get_leaderboard())

    @app.route("/db/evaluations/save", methods=["POST"])
    def save_evaluation():
        data = request.json
        success = state.db.save_evaluation(
            data.get("username"), data.get("csd_timestamp"), data.get("results")
        )
        return jsonify({"success": success})

    csd_directory = Path(CSD_DIRECTORY).resolve()
    emittance_directory = Path(EMITTANCE_DIRECTORY).resolve()

    for directory in [csd_directory, emittance_directory]:
        if not directory.exists():
            print(f"[red]Directory {directory} does not exist[/red]")
            raise typer.Abort()
    print(f"Serving files from {csd_directory}, {emittance_directory}")
    print(f"Serving [bold]{len(list_files(csd_directory))}[/bold] CSD files")
    print(
        f"Serving [bold]{
            len(list_files(emittance_directory, 'emittance_scan_*'))
        }[/bold] emittance scan files"
    )
    state.csd_directory = csd_directory
    state.emittance_directory = emittance_directory
    state.db = ServerDatabaseManager()
    return app


if __name__ == "__main__":
    app = create_app()
    app.run()
