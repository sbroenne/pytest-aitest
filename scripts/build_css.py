#!/usr/bin/env python3
"""Build Tailwind CSS for report templates.

This script runs npm to compile and purge the CSS for our report templates.
Run this after modifying any templates or the input.css file.

Usage:
    uv run python scripts/build_css.py           # Production build (minified)
    uv run python scripts/build_css.py --watch   # Development (watch mode)

Prerequisites:
    cd src/pytest_aitest/templates && npm install
"""

import subprocess
import sys
from pathlib import Path

TEMPLATES_DIR = Path(__file__).parent.parent / "src" / "pytest_aitest" / "templates"
OUTPUT_CSS = TEMPLATES_DIR / "partials" / "tailwind.css"


def build_css(watch: bool = False) -> None:
    """Build the Tailwind CSS file."""
    script = "watch" if watch else "build"
    cmd = ["npm", "run", script]
    
    print(f"Running: {' '.join(cmd)} in {TEMPLATES_DIR}")
    result = subprocess.run(cmd, cwd=TEMPLATES_DIR)
    
    if result.returncode == 0 and not watch:
        size = OUTPUT_CSS.stat().st_size
        print(f"✓ Built {OUTPUT_CSS.name} ({size:,} bytes)")
    elif result.returncode != 0:
        print(f"✗ Build failed with code {result.returncode}")
        sys.exit(1)


def main() -> None:
    """Main entry point."""
    watch = "--watch" in sys.argv or "-w" in sys.argv
    build_css(watch=watch)


if __name__ == "__main__":
    main()
