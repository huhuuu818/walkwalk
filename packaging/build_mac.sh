#!/usr/bin/env bash
# Run this on a Mac to package walkwalk.py into a double-clickable Walk Walk.app
# Usage: open Terminal, cd into the project folder, run: bash packaging/build_mac.sh
set -euo pipefail
cd "$(dirname "$0")/.."

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 not found - install Python 3 first (https://www.python.org/downloads/)"
  exit 1
fi

python3 -m venv .build-venv
source .build-venv/bin/activate
pip install --quiet --upgrade pip pyinstaller

pyinstaller --windowed --onefile --noconfirm \
  --name "Walk Walk" \
  --icon "assets/icon/icon.icns" \
  --add-data "quotes.json:." \
  --add-data "fonts/ttf:fonts/ttf" \
  --add-data "assets/icon/icon-256.png:assets/icon" \
  walkwalk.py

deactivate

echo ""
echo "Build complete: dist/Walk Walk.app"
echo "Drag it into your Applications folder, then just double-click to run."
