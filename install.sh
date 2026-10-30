#!/bin/sh
set -eu

PREFIX=${PREFIX:-"$HOME/.local"}
REPOSITORY=${1:-${YT_AUDIO_REPOSITORY:-}}
TEMP_DIR=

if ! command -v python3 >/dev/null 2>&1; then
    printf '%s\n' "Erreur : python3 est requis (Arch : sudo pacman -S --needed python)." >&2
    exit 1
fi

for dependency in mpv yt-dlp; do
    if ! command -v "$dependency" >/dev/null 2>&1; then
        printf 'Erreur : %s est requis (Arch : sudo pacman -S --needed mpv yt-dlp wofi).\n' "$dependency" >&2
        exit 1
    fi
done

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
SOURCE="$SCRIPT_DIR/index.py"

if [ ! -f "$SOURCE" ]; then
    case "$REPOSITORY" in
        */*) ;;
        *)
            printf '%s\n' "Usage distant : curl -fsSL URL/install.sh | sh -s -- OWNER/REPOSITORY" >&2
            exit 2
            ;;
    esac
    if ! command -v curl >/dev/null 2>&1; then
        printf '%s\n' "Erreur : curl est requis pour télécharger le programme." >&2
        exit 1
    fi
    case "$REPOSITORY" in
        *[!A-Za-z0-9._/-]*|*..*|/*|*/../*|*/..)
            printf '%s\n' "Erreur : nom de dépôt GitHub invalide." >&2
            exit 2
            ;;
    esac
    TEMP_DIR=$(mktemp -d)
    trap 'if [ -n "$TEMP_DIR" ]; then rm -rf -- "$TEMP_DIR"; fi' EXIT HUP INT TERM
    SOURCE="$TEMP_DIR/index.py"
    if ! curl -fLsS "https://raw.githubusercontent.com/$REPOSITORY/main/index.py" -o "$SOURCE"; then
        printf '%s\n' "Erreur : impossible de télécharger index.py depuis $REPOSITORY (branche main)." >&2
        exit 1
    fi
fi

install -Dm755 "$SOURCE" "$PREFIX/bin/yt-audio"
printf 'Installé : %s/bin/yt-audio\n' "$PREFIX"
printf '%s\n' "Vérifiez que $PREFIX/bin est dans PATH."
printf '%s\n' "Ajoutez les exemples Waybar et Hyprland du dépôt à votre configuration utilisateur."
