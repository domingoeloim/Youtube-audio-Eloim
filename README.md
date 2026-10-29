# Omarchy YouTube Audio

Petit contrôleur YouTube pour Waybar : lecture audio sans fenêtre, fenêtre
vidéo mpv flottante (PiP), pause, arrêt et réglage du volume. Les recherches
textuelles sont transmises à yt-dlp comme recherche YouTube.

> Omarchy utilise normalement Quickshell pour sa barre. Ce module cible
> Waybar ; il s'affiche si Waybar est installé et lancé.

## Dépendances

Sur Arch Linux / Omarchy :

```sh
sudo pacman -S --needed python mpv yt-dlp waybar wofi
```

`rofi` peut remplacer `wofi`. Python 3.10+ utilise uniquement sa bibliothèque
standard. mpv, yt-dlp et un sélecteur (wofi ou rofi) sont requis. Une session
Wayland doit fournir `XDG_RUNTIME_DIR`.

## Installation

Installez d'abord les dépendances, puis lancez cette commande depuis un
terminal :

```sh
sudo pacman -S --needed python mpv yt-dlp waybar wofi &&
curl -fsSL https://raw.githubusercontent.com/OWNER/omarchy-youtube-audio/main/install.sh |
  sh -s -- OWNER/omarchy-youtube-audio
```

Remplacez `OWNER` par le nom du compte GitHub qui publie le dépôt. Le script
installe `yt-audio` dans `~/.local/bin` et vérifie les dépendances nécessaires.
Assurez-vous que `~/.local/bin` est dans le `PATH` hérité par Waybar, puis
redémarrez Waybar. Pour choisir un autre préfixe :

```sh
curl -fsSL https://raw.githubusercontent.com/OWNER/omarchy-youtube-audio/main/install.sh |
  PREFIX=/chemin sh -s -- OWNER/omarchy-youtube-audio
```

Depuis une copie locale du dépôt, `./install.sh` installe le fichier directement.

## Waybar

1. Ajoutez `"custom/youtube-audio"` et `"custom/youtube-pip"` dans l'une des
   listes de modules de votre configuration, par exemple `"modules-right"`.
2. Copiez le contenu de [`waybar-module.jsonc`](./waybar-module.jsonc) dans
   l'objet racine de la configuration Waybar (fusionnez les objets si la
   configuration utilise déjà `custom/youtube-audio`).
3. Rechargez Waybar.

Actions par défaut :

| Action | Résultat |
| --- | --- |
| Clic gauche | Ouvre wofi/rofi pour saisir une URL ou une recherche et lance l'audio |
| Clic droit | Pause / reprise |
| Clic milieu | Arrêt |
| Molette haut/bas | Volume +5 % / -5 % |

Le module audio affiche l'état et le titre de la lecture courante. Le bouton
PiP ouvre le sélecteur et lance une vidéo dans la fenêtre flottante mpv.

## Fenêtre PiP flottante avec Hyprland

La commande `pip` crée une fenêtre mpv de 640×360 en haut de pile. Pour que
Hyprland la traite comme fenêtre flottante, ajoutez le contenu de
[`hyprland-pip.lua`](./hyprland-pip.lua) à votre configuration utilisateur
Hyprland, dans la section où vos règles `o.window(...)` sont déclarées.
Cette règle ne cible que la fenêtre dont le titre est `YouTube Audio PiP`.
Rechargez ensuite la configuration Hyprland.

Le bouton PiP Waybar appelle la commande `pip`. Elle reste aussi disponible
dans le terminal :

```sh
yt-audio pip "https://www.youtube.com/watch?v=VIDEO_ID"
yt-audio pip "nom de la vidéo"
```

## Utilisation en terminal

```sh
yt-audio play "https://youtu.be/VIDEO_ID" # audio uniquement
yt-audio play "nom de la vidéo"           # recherche puis lecture audio
yt-audio pip "nom de la vidéo"            # vidéo dans la fenêtre flottante
yt-audio toggle                           # pause/reprise
yt-audio volume +5                        # volume +5 %
yt-audio stop
yt-audio status                           # JSON utilisé par Waybar
```

Pour démarrer une autre lecture, arrêtez d'abord celle en cours. Le journal de
démarrage mpv est écrit dans `$XDG_RUNTIME_DIR/youtube-audio-mpv.log`.
