#!/usr/bin/env python3
"""Regenerate all app-icon artifacts from assets/icon/icon.png (1024x1024).

Run this once after replacing icon.png (needs pillow: pip install pillow):

    python3 packaging/make_icons.py

Outputs, all committed to the repo so end users never need this script:
  assets/icon/icon.icns     - macOS bundle icon (PyInstaller --icon, build_mac.sh)
  assets/icon/icon.ico      - Windows exe icon (PyInstaller --icon, build_windows.bat)
  assets/icon/icon-256.png  - runtime window/taskbar icon (tk iconphoto)
"""
import os
import struct

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ICON_DIR = os.path.join(HERE, "..", "assets", "icon")
SRC = os.path.join(ICON_DIR, "icon.png")

# ICNS chunks that accept raw PNG payloads: (type, pixel size)
ICNS_PNG_TYPES = [
    (b"ic11", 32),    # 16pt @2x
    (b"ic12", 64),    # 32pt @2x
    (b"ic07", 128),
    (b"ic13", 256),   # 128pt @2x
    (b"ic08", 256),
    (b"ic14", 512),   # 256pt @2x
    (b"ic09", 512),
    (b"ic10", 1024),  # 512pt @2x
]


def png_bytes(img, size):
    import io
    buf = io.BytesIO()
    img.resize((size, size), Image.LANCZOS).save(buf, format="PNG")
    return buf.getvalue()


def main():
    img = Image.open(SRC).convert("RGBA")

    chunks = b""
    for four_cc, size in ICNS_PNG_TYPES:
        data = png_bytes(img, size)
        chunks += four_cc + struct.pack(">I", 8 + len(data)) + data
    with open(os.path.join(ICON_DIR, "icon.icns"), "wb") as f:
        f.write(b"icns" + struct.pack(">I", 8 + len(chunks)) + chunks)

    img.save(os.path.join(ICON_DIR, "icon.ico"), format="ICO",
             sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])

    img.resize((256, 256), Image.LANCZOS).save(os.path.join(ICON_DIR, "icon-256.png"))

    for name in ("icon.icns", "icon.ico", "icon-256.png"):
        path = os.path.join(ICON_DIR, name)
        print(f"{name}: {os.path.getsize(path)} bytes")


if __name__ == "__main__":
    main()
