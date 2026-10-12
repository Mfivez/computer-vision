"""Vérifier les ressources locales ; télécharger seulement avec --download.

Ce script n'exécute aucun modèle et ne remplace aucun fichier existant.
Les URL et empreintes sont explicites dans ressources/assets_manifest.json.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "ressources" / "assets_manifest.json"
TRUSTED_PREFIXES = (
    "https://github.com/ultralytics/assets/releases/download/v8.3.0/",
    "https://raw.githubusercontent.com/ultralytics/ultralytics/"
    "e544db43838fd058370cad216bf82a7639f29b35/",
)


def verify(path: Path, expected: dict) -> None:
    """Contrôler la taille puis l'empreinte sans charger le modèle en mémoire."""
    if not path.is_file():
        raise FileNotFoundError(f"Ressource absente : {expected['path']}")
    if path.stat().st_size != expected["bytes"]:
        raise ValueError(f"Taille inattendue : {expected['path']}")
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    if digest.hexdigest() != expected["sha256"]:
        raise ValueError(f"Empreinte différente : {expected['path']}")


def download(path: Path, expected: dict) -> None:
    """Récupérer une ressource connue, vérifier puis créer le fichier cible."""
    url = expected["url"]
    if not url.startswith(TRUSTED_PREFIXES):
        raise ValueError(f"Source non prévue : {url}")
    # Le plafond évite de recevoir un fichier différent de celui du manifeste.
    request = Request(url, headers={"User-Agent": "computer-vision-course-assets/1"})
    with urlopen(request, timeout=60) as response:
        data = response.read(expected["bytes"] + 1)
    if len(data) != expected["bytes"]:
        raise ValueError(f"Taille téléchargée inattendue : {expected['path']}")
    if hashlib.sha256(data).hexdigest() != expected["sha256"]:
        raise ValueError(f"Empreinte téléchargée inattendue : {expected['path']}")
    path.parent.mkdir(parents=True, exist_ok=True)
    # Le mode xb refuse d'écraser un fichier apparu entre-temps.
    with path.open("xb") as destination:
        destination.write(data)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="Vérifier sans réseau (mode par défaut).")
    mode.add_argument("--download", action="store_true", help="Télécharger les seules ressources absentes.")
    args = parser.parse_args()
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    errors = []
    for asset in manifest["assets"]:
        path = (ROOT / asset["path"]).resolve()
        try:
            if not path.is_relative_to(ROOT):
                raise ValueError("Chemin hors du projet refusé.")
            if not path.exists() and args.download:
                print(f"Téléchargement explicite : {asset['path']}", flush=True)
                download(path, asset)
            verify(path, asset)
            print(f"OK : {asset['path']}")
        except (OSError, ValueError) as error:
            errors.append(str(error))
            print(f"ERREUR : {error}", file=sys.stderr)
    if errors:
        print("Aucun fichier existant n'a été remplacé. Vérifier SOURCES.txt avant toute intervention.")
        return 1
    print("Ressources vérifiées. Aucun téléchargement implicite n'est nécessaire dans les notebooks.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
