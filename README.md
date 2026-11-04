# Omarchy YouTube Audio

Plugin Quickshell natif pour Omarchy : une icône casque et note ouvre un petit
panneau flottant de lecture YouTube. L'interface suit les couleurs du thème
Omarchy actif. Les pictogrammes proviennent de la police Font Awesome déjà
disponible sur Omarchy.

## Dépendances

Sur Arch Linux / Omarchy :

```sh
sudo pacman -S --needed python mpv yt-dlp woff2-font-awesome
```

Quickshell est fourni par Omarchy. Python 3.10+ utilise uniquement sa
bibliothèque standard. Une session Wayland doit fournir `XDG_RUNTIME_DIR`.

## Installation dans Omarchy

Après avoir installé les dépendances, ajoutez le dépôt comme plugin Omarchy :

```sh
omarchy plugin add https://github.com/OWNER/omarchy-youtube-audio.git
```
```sh
omarchy plugin enable maeder.youtube-audio
```

Omarchy place alors l'icône dans la section droite de la barre. Pour une copie
locale du dépôt, copiez les fichiers du plugin ainsi :

```sh
mkdir -p ~/.config/omarchy/plugins/maeder.youtube-audio
cp manifest.json index.py ~/.config/omarchy/plugins/maeder.youtube-audio/
cp -a quickshell ~/.config/omarchy/plugins/maeder.youtube-audio/
omarchy-shell shell rescanPlugins
omarchy plugin enable maeder.youtube-audio
```

### Interface

- Clic gauche sur l'icône casque-note : ouvre le panneau juste sous l'icône,
  en se repositionnant selon le côté de la barre.
- La fenêtre mesure 360 × 210 px (avant mise à l'échelle Omarchy), apparaît en
  fondu et se ferme quand le clic est fait à l'extérieur.
- Collez ou saisissez une URL YouTube (Ctrl+V ou l'icône presse-papiers), puis
  appuyez sur Entrée ou cliquez sur le bouton Lecture à droite du champ pour
  lancer l'audio. Une nouvelle URL remplace la lecture en cours ; le panneau
  reste ouvert après le lancement.
- Le titre défile si nécessaire. Les commandes reculent de 30 secondes,
  lecture/pause, avancent de 30 secondes et basculent la lecture courante en
  fenêtre vidéo PiP en conservant sa position. Le PiP recherche une piste vidéo
  (jusqu'à 720p) avant d'arrêter l'audio ; si elle est indisponible, l'audio
  continue.
- Les couleurs, bordures et états des commandes suivent le thème Omarchy actif.

## Contrôleur en terminal et intégration Waybar historique

L'interface Waybar reste disponible pour les installations qui l'utilisent.
Elle requiert Waybar et un sélecteur (wofi ou rofi). Pour installer la commande
`yt-audio` seule depuis le dépôt :

```sh
./install.sh
```

Le programme est installé dans `~/.local/bin`. Assurez-vous que ce dossier
figure dans le `PATH` hérité par Waybar. Pour choisir un autre préfixe :

```sh
PREFIX=/chemin ./install.sh
```

### Aperçu local Waybar

Pour afficher les deux modules sans modifier la barre Omarchy ni ta
configuration Waybar habituelle :

```sh
./install.sh
waybar -c "$PWD/waybar-preview.jsonc" -s "$PWD/waybar-preview.css"
```

Cette prévisualisation s'affiche en bas de l'écran. Ferme-la avec `Ctrl+C`
dans le terminal qui l'a lancée. Le clic gauche sur le bouton PiP ouvre le
sélecteur de vidéos.

### Configuration Waybar

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

La commande `pip` ouvre la vidéo dans une petite fenêtre mpv. Pour que
Hyprland la traite comme fenêtre flottante, ajoutez le contenu de
[`hyprland-pip.lua`](./hyprland-pip.lua) à la configuration utilisateur
Hyprland, après `require("default.hypr.omarchy")`. Cette configuration est
nécessaire : Omarchy règle normalement les nouvelles fenêtres mpv flottantes à
875×600. La règle PiP les épingle et les réduit à 300×169, en haut à droite.
Un événement Hyprland réapplique la taille après que mpv a créé sa fenêtre.
Rechargez ensuite avec `hyprctl reload` et vérifiez `hyprctl configerrors`.

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
yt-audio pip-current                      # bascule la lecture courante en PiP
yt-audio toggle                           # pause/reprise
yt-audio seek -30                         # recule de 30 secondes
yt-audio volume +5                        # volume +5 %
yt-audio stop
yt-audio status                           # JSON utilisé par Waybar
```

Pour démarrer une autre lecture, arrêtez d'abord celle en cours. Le journal de
démarrage mpv est écrit dans `$XDG_RUNTIME_DIR/youtube-audio-mpv.log`.
