"""Normalise l'export Contours...IRIS IGN-INSEE pour le dashboard.

Usage:
    python scripts/update_iris_geojson.py source.geojson \
        dashboard/static/data/paris_iris.geojson
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


SOURCE_URL = (
    "https://data.iledefrance.fr/api/explore/v2.1/catalog/datasets/iris/"
    "exports/geojson?where=dep%3D75"
)
MILLÉSIME = 2024


def _arrondissement(code_commune: str) -> int:
    if len(code_commune) != 5 or not code_commune.startswith("751"):
        raise ValueError(f"Code commune parisien invalide: {code_commune}")
    numéro = int(code_commune[-2:])
    if not 1 <= numéro <= 20:
        raise ValueError(f"Arrondissement hors limites: {code_commune}")
    return numéro


def normalise(source: dict) -> dict:
    features = []
    codes = set()
    for feature in source.get("features", []):
        props = feature.get("properties") or {}
        code_commune = str(props.get("insee_com", ""))
        if not code_commune.startswith("751"):
            continue
        code_iris = str(props.get("code_iris", ""))
        if len(code_iris) != 9 or code_iris in codes:
            raise ValueError(f"Code IRIS invalide ou dupliqué: {code_iris}")
        if not feature.get("geometry"):
            raise ValueError(f"Géométrie absente pour {code_iris}")
        codes.add(code_iris)
        features.append(
            {
                "type": "Feature",
                "properties": {
                    "code_iris": code_iris,
                    "nom_iris": props.get("nom_iris") or code_iris,
                    "type_iris": props.get("typ_iris"),
                    "arrondissement": _arrondissement(code_commune),
                    "code_commune": code_commune,
                    "nom_commune": props.get("nom_com"),
                },
                "geometry": feature["geometry"],
            }
        )
    features.sort(key=lambda item: item["properties"]["code_iris"])
    if len(features) != 992:
        raise ValueError(f"992 IRIS attendus pour Paris, {len(features)} reçus")
    return {
        "type": "FeatureCollection",
        "name": "Contours IRIS Paris",
        "metadata": {
            "millesime": MILLÉSIME,
            "source": "Contours...IRIS®, IGN-INSEE",
            "source_url": SOURCE_URL,
            "licence": "Licence Ouverte 2.0",
            "indicateurs": "Les indicateurs métier sont hérités de l'arrondissement parent.",
        },
        "features": features,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    with args.source.open(encoding="utf-8") as stream:
        output = normalise(json.load(stream))
    args.destination.parent.mkdir(parents=True, exist_ok=True)
    with args.destination.open("w", encoding="utf-8") as stream:
        json.dump(output, stream, ensure_ascii=False, separators=(",", ":"))
    print(f"{len(output['features'])} IRIS écrits dans {args.destination}")


if __name__ == "__main__":
    main()
