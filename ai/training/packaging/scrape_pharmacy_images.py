"""Compatibility entry point for the correctly placed scraper module."""
from __future__ import annotations
import sys
from pathlib import Path
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from ai.training.packaging.data_scrapers.scrape_pharmacy_images import main
if __name__ == "__main__": main()
