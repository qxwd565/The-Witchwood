#!/usr/bin/env python3
"""Compatibility build entrypoint; reads sparse date-first sources and never bootstraps from baseline."""
import runpy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
runpy.run_path(str(ROOT/"tools/sync-witchwood-history.py"),run_name="__main__")
