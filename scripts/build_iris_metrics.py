"""Construit le snapshot d'indicateurs natifs IRIS."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ude_platform.iris_metrics import build_iris_metrics  # noqa: E402


if __name__ == "__main__":
    result = build_iris_metrics()
    print(f"{len(result['iris'])} IRIS calculés")
