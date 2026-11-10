#!/usr/bin/env python3
"""Rebuild Witchwood schema-1 compatibility APIs from the canonical migration source."""
import runpy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
runpy.run_path(str(ROOT/"tools/migrate-witchwood-v2.py"),run_name="__main__")
