#!/usr/bin/env python3
"""Sync Gold → PostgreSQL + MongoDB (hors pipeline complet)."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ude_platform.sync_databases import sync_gold_to_databases

if __name__ == "__main__":
    result = sync_gold_to_databases()
    print(result)
    sys.exit(0 if all(result.values()) else 1)
