#!/usr/bin/env bash
# Run this on a Mac to package walkwalk.py into a double-clickable Walk Walk.app
# Usage: open Terminal, cd into the project folder, run: bash packaging/build_mac.sh
set -euo pipefail
cd "$(dirname "$0")/.."

# Pick a Python whose Tcl/Tk PyInstaller can bundle (Tk 8.6.x). Very new Pythons ship
# Tcl/Tk 9.0, which PyInstaller cannot collect yet — the frozen app then silently falls
# back to macOS's ancient system Tk 8.5 and renders BLANK windows (with a "system
# version of Tk is deprecated" warning in the terminal). Building with a Tk 8.6 Python
# avoids that entirely.
PY=""
for cand in python3.13 python3.12 python3.11 python3.10 python3; do
  if command -v "$cand" >/dev/null 2>&1 && \
     "$cand" -c "import tkinter as t, sys; sys.exit(0 if abs(t.TkVersion - 8.6) < 0.01 else 1)" 2>/dev/null; then
    PY="$cand"
    break
  fi
done
if [ -z "$PY" ]; then
  if ! command -v python3 >/dev/null 2>&1; then
    echo "python3 not found - install Python 3 first (https://www.python.org/downloads/)"
    exit 1
  fi
  echo "WARNING: no Python with Tcl/Tk 8.6 found - the packaged app may show blank windows."
  echo "Install Python 3.12 or 3.13 from https://www.python.org/downloads/ and re-run this script."
  PY="python3"
fi
echo "Building with $PY ($($PY --version 2>&1), Tk $($PY -c 'import tkinter as t; print(t.TkVersion)' 2>/dev/null))"

"$PY" -m venv .build-venv
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
