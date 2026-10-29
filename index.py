#!/usr/bin/env python3
"""Omarchy YouTube Audio controller for Waybar and mpv."""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urlparse


SOCKET_NAME = "youtube-audio-mpv.sock"
LOG_NAME = "youtube-audio-mpv.log"
PIP_TITLE = "YouTube Audio PiP"
IPC_TIMEOUT = 1.0
START_TIMEOUT = 8.0


class PlayerError(RuntimeError):
    """An expected player or configuration error."""


def socket_path() -> Path:
    runtime_dir = os.environ.get("XDG_RUNTIME_DIR")
    if not runtime_dir:
        raise PlayerError("XDG_RUNTIME_DIR est absent ; lancez ce programme depuis votre session graphique.")
    directory = Path(runtime_dir)
    if not directory.is_dir():
        raise PlayerError(f"Le répertoire XDG_RUNTIME_DIR n'existe pas : {directory}")
    return directory / SOCKET_NAME


def log_path() -> Path:
    return socket_path().with_name(LOG_NAME)


def _read_response(sock: socket.socket, request_id: int) -> dict:
    buffer = b""
    while len(buffer) <= 1_048_576:
        chunk = sock.recv(65536)
        if not chunk:
            raise PlayerError("mpv a fermé la connexion IPC sans répondre.")
        buffer += chunk
        while b"\n" in buffer:
            line, buffer = buffer.split(b"\n", 1)
            try:
                response = json.loads(line)
            except json.JSONDecodeError as error:
                raise PlayerError(f"Réponse IPC mpv invalide : {error}") from error
            if response.get("request_id") == request_id:
                return response
    raise PlayerError("La réponse IPC mpv dépasse la taille maximale.")


def ipc(command: list, *, missing_ok: bool = False) -> dict | None:
    path = socket_path()
    request_id = time.monotonic_ns() & 0x7FFFFFFF
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
            connection.settimeout(IPC_TIMEOUT)
            connection.connect(str(path))
            payload = {"command": command, "request_id": request_id}
            connection.sendall(json.dumps(payload).encode("utf-8") + b"\n")
            response = _read_response(connection, request_id)
    except FileNotFoundError:
        if missing_ok:
            return None
        raise PlayerError("Aucune lecture mpv en cours.") from None
    except ConnectionRefusedError:
        if missing_ok:
            return None
        raise PlayerError("Le socket mpv existe, mais aucun lecteur ne répond.") from None
    except socket.timeout as error:
        raise PlayerError("Délai dépassé en attendant mpv.") from error
    except OSError as error:
        raise PlayerError(f"Impossible de communiquer avec mpv : {error}") from error

    if response.get("error") == "property unavailable" and command[0] == "get_property":
        return {"data": None}
    if response.get("error") != "success":
        if missing_ok:
            return None
        raise PlayerError(f"mpv a refusé la commande {command[0]} : {response.get('error', 'erreur inconnue')}")
    return response


def get_property(name: str):
    response = ipc(["get_property", name])
    return response.get("data") if response else None


def media_url(query: str) -> str:
    query = query.strip()
    if not query:
        raise PlayerError("Saisissez une URL YouTube ou des mots-clés de recherche.")
    parsed = urlparse(query)
    if parsed.scheme in ("http", "https") and parsed.netloc:
        return query
    return f"ytsearch1:{query}"


def choose_query() -> str | None:
    if shutil.which("wofi"):
        command = ["wofi", "--dmenu", "--prompt", "YouTube Audio"]
    elif shutil.which("rofi"):
        command = ["rofi", "-dmenu", "-p", "YouTube Audio"]
    else:
        raise PlayerError("Installez wofi ou rofi pour choisir une vidéo depuis Waybar.")
    try:
        result = subprocess.run(command, text=True, capture_output=True, check=False)
    except OSError as error:
        raise PlayerError(f"Impossible d'ouvrir le sélecteur : {error}") from error
    if result.returncode == 1:
        return None
    if result.returncode != 0:
        detail = result.stderr.strip() or f"code de sortie {result.returncode}"
        raise PlayerError(f"Le sélecteur a échoué : {detail}")
    return result.stdout.strip() or None


def _tail_log(path: Path) -> str:
    try:
        with path.open("rb") as log:
            log.seek(0, os.SEEK_END)
            size = log.tell()
            log.seek(max(0, size - 4096))
            return log.read().decode("utf-8", errors="replace").strip()
    except OSError:
        return ""


def start_player(query: str, *, pip: bool) -> None:
    path = socket_path()
    if path.exists():
        if path.is_socket():
            response = ipc(["get_property", "pause"], missing_ok=True)
            if response is not None:
                raise PlayerError("mpv est déjà en cours. Arrêtez la lecture avant d'en lancer une autre.")
            path.unlink()
        else:
            raise PlayerError(f"Le chemin IPC existe mais n'est pas un socket : {path}")

    mpv = shutil.which("mpv")
    ytdlp = shutil.which("yt-dlp")
    if not mpv:
        raise PlayerError("mpv est requis (paquet Arch : mpv).")
    if not ytdlp:
        raise PlayerError("yt-dlp est requis (paquet Arch : yt-dlp).")

    url = media_url(query)
    arguments = [
        mpv,
        "--no-terminal",
        "--ytdl=yes",
        "--ytdl-format=best" if pip else "--ytdl-format=bestaudio/best",
        f"--input-ipc-server={path}",
        f"--title={PIP_TITLE}" if pip else "--title=YouTube Audio",
    ]
    if pip:
        arguments.extend(
            [
                "--force-window=yes",
                "--ontop",
                "--geometry=640x360-24-48",
            ]
        )
    else:
        arguments.extend(["--no-video", "--force-window=no"])
    arguments.append(url)

    log = log_path()
    try:
        with log.open("ab") as output:
            process = subprocess.Popen(
                arguments,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=output,
                start_new_session=True,
            )
    except OSError as error:
        raise PlayerError(f"Impossible de démarrer mpv : {error}") from error

    deadline = time.monotonic() + START_TIMEOUT
    while time.monotonic() < deadline:
        if process.poll() is not None:
            details = _tail_log(log)
            message = f"mpv s'est arrêté au démarrage (code {process.returncode})."
            raise PlayerError(f"{message}\n{details}" if details else message)
        if path.exists():
            try:
                response = ipc(["get_property", "pause"], missing_ok=True)
            except PlayerError:
                response = None
            if response is not None:
                return
        time.sleep(0.1)

    process.terminate()
    try:
        process.wait(timeout=2)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()
    details = _tail_log(log)
    message = "mpv n'a pas ouvert son socket IPC à temps."
    raise PlayerError(f"{message}\n{details}" if details else message)


def play(query: str | None, *, pip: bool) -> None:
    if query is None:
        query = choose_query()
    if query:
        start_player(query, pip=pip)


def status() -> dict:
    path = socket_path()
    if not path.exists():
        return {
            "text": "♫ YouTube",
            "tooltip": "Aucune lecture. Clic gauche : choisir une vidéo.",
            "class": "stopped",
        }
    if not path.is_socket():
        raise PlayerError(f"Le chemin IPC existe mais n'est pas un socket : {path}")

    paused = bool(get_property("pause"))
    title = get_property("media-title") or "YouTube"
    title = re.sub(r"[\x00-\x1f\x7f]+", " ", str(title))
    title = re.sub(r"\s+", " ", title).strip() or "YouTube"
    display_title = title if len(title) <= 36 else title[:33].rstrip() + "…"
    icon = "⏸" if paused else "▶"
    return {
        "text": f"{icon} {html.escape(display_title)}",
        "tooltip": f"{'En pause' if paused else 'Lecture'} : {html.escape(title)}",
        "class": "paused" if paused else "playing",
    }


def pip_button() -> dict:
    return {
        "text": "▣ PiP",
        "tooltip": "Clic gauche : choisir une vidéo à ouvrir dans mpv.",
        "class": "pip",
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="yt-audio",
        description="Contrôle la lecture YouTube audio ou PiP via mpv.",
    )
    subparsers = parser.add_subparsers(dest="action", required=True)
    for action, description in (
        ("play", "Lancer une lecture audio"),
        ("pip", "Lancer une vidéo dans une fenêtre PiP"),
    ):
        command = subparsers.add_parser(action, help=description)
        command.add_argument("query", nargs="?", help="URL ou recherche YouTube")
    subparsers.add_parser("toggle", help="Mettre en pause ou reprendre")
    subparsers.add_parser("stop", help="Arrêter la lecture")
    volume = subparsers.add_parser("volume", help="Modifier le volume")
    volume.add_argument("delta", type=int, help="Variation en pourcentage, ex. +5 ou -5")
    subparsers.add_parser("status", help="Afficher l'état pour Waybar")
    subparsers.add_parser("pip-button", help="Afficher le bouton PiP pour Waybar")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.action == "play":
            play(args.query, pip=False)
        elif args.action == "pip":
            play(args.query, pip=True)
        elif args.action == "toggle":
            ipc(["cycle", "pause"])
        elif args.action == "stop":
            ipc(["quit"], missing_ok=True)
        elif args.action == "volume":
            ipc(["add", "volume", args.delta])
        elif args.action == "status":
            print(json.dumps(status(), ensure_ascii=False))
        elif args.action == "pip-button":
            print(json.dumps(pip_button(), ensure_ascii=False))
    except PlayerError as error:
        print(f"yt-audio: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
