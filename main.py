#!/usr/bin/env python3
"""Compatibility wrapper to run the CLI directly from the repo."""

import sys
from pathlib import Path

# Add src to path for direct execution
sys.path.insert(0, str(Path(__file__).parent / "src"))

from openreview_downloader.cli import main


if __name__ == "__main__":
    main()
