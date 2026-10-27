"""Test environment: the module-level case store stays in memory (no files under data/cases)."""
import os

os.environ.setdefault("RECOURSE_CASE_DIR", "")
