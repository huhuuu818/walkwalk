#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
walk walk · a break reminder that won't let you ignore it

Run:  python3 walkwalk.py
Quit: Ctrl+C in the terminal

Zero third-party dependencies, stdlib + tkinter only.
Visual/copy spec: .claude/skills/walkwalk-design/SKILL.md
Product spec:      docs/PRD.md
"""

import json
import math
import os
import platform
import random
import shutil
import subprocess
import sys
import time
import tkinter as tk
import tkinter.font as tkfont
from datetime import date, datetime, timedelta

# ============================================================
# Tunable constants
# ============================================================

VERSION = "1.0.0"              # bump on every public release

INTERVAL_MINUTES = 45          # default minutes between reminders (F2) — the effective value
                               # is configurable in settings (F22, 15-minute steps)
INTERVAL_CHOICES = (15, 30, 45, 60)  # F22: selectable reminder intervals, 15-min granularity
POPUP_MOVE_SPEED = 8           # default walk speed, px/frame — configurable via the settings
WALK_SPEED_MIN = 2             # slider (F23); slowest still reads as "wandering"...
WALK_SPEED_MAX = 30            # ...and max is deliberately ludicrous (~900px/s) — catching
                               # it becomes a game, per user request
POPUP_FRAME_MS = 20            # walk animation frame interval, ms
DIRECTION_CHANGE_PROB = 0.012  # per-frame chance of picking a new random heading
POPUP_MARGIN = 8               # edge margin for spawn position + walk bounds (F5) — kept small so the walk range is effectively the whole screen
BOTTOM_RESERVE = 60            # extra bottom margin to clear the Dock / taskbar (F7)
POPUP_MIN_WIDTH = 360   # F4 (PRD v1.4): raised from 320x200 so the single-line title
POPUP_MIN_HEIGHT = 240  # (F20⑤a) and 24/16 head padding fit without starving the quote card
CAPTURE_FLASH_MS = 150         # one-shot accent flash on capture (design skill §6) — no looping blink
CAPTURE_REQUIRES_RECENT_MOTION_S = 0.25  # ignore <Enter> as a "catch" unless the mouse itself
                                          # actually moved within this many seconds — otherwise a
                                          # fast, wide-ranging popup can wander under an idle cursor
                                          # and silently self-capture, which looks like it "just
                                          # stopped moving" instead of being caught (F7a)
CAPTURE_MIN_MOTION_PX = 4                # minimum distance between consecutive polls to count as
                                          # "the mouse actually moved" — trackpads/mice can report a
                                          # few px of sensor jitter even at rest, which would
                                          # otherwise keep re-arming the recent-motion window forever

TEST_MODE = False              # set True for a top-left dev panel: click it, press S to fire a popup instantly


def is_test_mode(argv=None, environ=None):
    """Quick-test switch that needs NO file editing: `python3 walkwalk.py --demo` (or
    `--test`, or env WALKWALK_TEST=1) behaves like TEST_MODE=True AND fires the first
    reminder immediately at launch — one command, popup on screen. The TEST_MODE constant
    still works for people who prefer editing the file."""
    if TEST_MODE:
        return True
    args = sys.argv[1:] if argv is None else argv
    if "--demo" in args or "--test" in args:
        return True
    env = os.environ if environ is None else environ
    return env.get("WALKWALK_TEST", "") not in ("", "0")

# ============================================================
# Config (F18) — migrates from the legacy break_reminder config file automatically
# ============================================================

OLD_CONFIG_PATH = os.path.expanduser("~/.break_reminder_config.json")
CONFIG_PATH = os.path.expanduser("~/.walkwalk_config.json")

DEFAULT_CONFIG = {
    "mode": "scheduled",           # "scheduled" | "always"
    "work_start": "09:30",
    "work_end": "18:30",
    "work_days": [0, 1, 2, 3, 4],  # 0=Mon ... 6=Sun
    "start_at_login": False,
    "interval_minutes": INTERVAL_MINUTES,  # F22: how often to stand up (15-min steps)
    "walk_speed": POPUP_MOVE_SPEED,        # F23: popup walk speed, px/frame
}

WEEKDAY_LABELS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


def _migrate_old_config():
    if not os.path.exists(CONFIG_PATH) and os.path.exists(OLD_CONFIG_PATH):
        try:
            os.rename(OLD_CONFIG_PATH, CONFIG_PATH)
        except OSError:
            pass


def load_config():
    _migrate_old_config()
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        config = dict(DEFAULT_CONFIG)
        config.update({k: data[k] for k in DEFAULT_CONFIG if k in data})
        return config
    except Exception:
        return dict(DEFAULT_CONFIG)


def save_config(config):
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    except Exception:
        pass  # a failed save should never crash the app


# ============================================================
# Resource paths (works both as a script and as a PyInstaller bundle)
# ============================================================

def resource_path(*parts):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, *parts)


# ============================================================
# Quotes (F8) — quotes.json next to the script, broken/missing file falls back inline
# ============================================================

FALLBACK_QUOTES = [
    {"text": "Walking is man's best medicine.", "by": "Hippocrates"},
    {"text": "A journey of a thousand miles begins with a single step.", "by": "Lao Tzu"},
    {"text": "Good ideas arrive on foot.", "by": None},
    {"text": "Stretch now, glow all day.", "by": None},
    {"text": "Your chair will survive without you.", "by": None},
    {"text": "Blood flow is brain flow.", "by": None},
    {"text": "Small walk, big magic.", "by": None},
    {"text": "Momentum starts at the ankles.", "by": None},
    {"text": "Screens wait. Sunsets don't.", "by": None},
    {"text": "Nothing blooms sitting still.", "by": None},
]


def load_quotes():
    try:
        with open(resource_path("quotes.json"), "r", encoding="utf-8") as f:
            data = json.load(f)
        # accept both the shipped {"note":…, "quotes":[…]} wrapper and a bare list
        quotes = data if isinstance(data, list) else data.get("quotes")
        if isinstance(quotes, list) and quotes:
            return quotes
    except Exception:
        pass
    return FALLBACK_QUOTES


# ============================================================
# Color system (design skill §1) — five rotating palettes
# ============================================================

INK = "#141414"

PALETTES = {
    "tomato":   {"bg": "#FF4B1E", "card": "#F2E4C7", "accent": "#FFD500", "sticker": "#0BA6DF"},
    "sky":      {"bg": "#35A8E0", "card": "#F7F1E3", "accent": "#FFE014", "sticker": "#E8281E"},
    "grass":    {"bg": "#00A551", "card": "#F7F1E3", "accent": "#FFE014", "sticker": "#E8281E"},
    "lemon":    {"bg": "#FFD90F", "card": "#FFFDF5", "accent": "#35A8E0", "sticker": "#E8281E"},
    "postbox":  {"bg": "#E8381E", "card": "#F2E4C7", "accent": "#FFD500", "sticker": "#0BA6DF"},
    "grape":    {"bg": "#A47CF5", "card": "#F7F1E3", "accent": "#FFE014", "sticker": "#00A551"},
    "flamingo": {"bg": "#FF6FA5", "card": "#FFFDF5", "accent": "#FFE014", "sticker": "#0BA6DF"},
}
PALETTE_LIST = list(PALETTES.values())

# Fixed hover/pressed backgrounds per accent (design skill §5 complementary pairs) — a deliberate
# color-relationship table, not something to compute algorithmically (F20⑥ forbids that).
COMPLEMENT_STATES = {
    "#FFD500": ("#788EFF", "#5772FF"),
    "#FFE014": ("#7D8EFF", "#5C71FF"),
    "#35A8E0": ("#EF7134", "#DB5412"),
}


def complementary_states(accent):
    return COMPLEMENT_STATES[accent]


def parse_palette_override(argv=None, environ=None):
    """F21 debug palette mode: `--palette=cycle` rotates A->G one palette per popup,
    `--palette=A`..`G` (or a palette name) locks a single one; the WALKWALK_PALETTE env
    var works the same when the flag is absent. Returns 'cycle', a palette name, or None
    for the default per-day random (F5a). Unknown values fall back to None rather than
    crashing — this is a dev convenience, not a user-facing surface."""
    spec = None
    for arg in (sys.argv[1:] if argv is None else argv):
        if arg.startswith("--palette="):
            spec = arg.split("=", 1)[1]
    if spec is None:
        spec = (os.environ if environ is None else environ).get("WALKWALK_PALETTE")
    if not spec:
        return None
    spec = spec.strip().lower()
    if spec == "cycle":
        return "cycle"
    letters = {chr(ord("a") + i): name for i, name in enumerate(PALETTES)}
    if spec in letters:
        return letters[spec]
    if spec in PALETTES:
        return spec
    return None


def _clamp8(v):
    return max(0, min(255, int(round(v))))


def blend(fg_hex, bg_hex, alpha):
    """Alpha-composite fg over bg and return an opaque hex color — used to approximate
    'ink at 55% opacity' as a solid, since tkinter Label fg has no real alpha channel."""
    fg = tuple(int(fg_hex[i:i + 2], 16) for i in (1, 3, 5))
    bg = tuple(int(bg_hex[i:i + 2], 16) for i in (1, 3, 5))
    mixed = tuple(_clamp8(fg[i] * alpha + bg[i] * (1 - alpha)) for i in range(3))
    return "#%02x%02x%02x" % mixed


def darken(hex_color, amount=0.1):
    rgb = tuple(int(hex_color[i:i + 2], 16) for i in (1, 3, 5))
    darker = tuple(_clamp8(c * (1 - amount)) for c in rgb)
    return "#%02x%02x%02x" % darker


# ============================================================
# Fonts (design skill §2) — HuFont for display, UI sans for functional text,
# with graceful fallback if HuFont isn't installed/usable on this machine
# ============================================================

_FONT_CACHE = {}


def _pick_font(candidates):
    try:
        available = set(tkfont.families())
    except Exception:
        return candidates[-1]
    for name in candidates:
        if name in available:
            return name
    return candidates[-1]  # let Tk silently substitute its default


HUFONT_TTF_NAMES = ("HuFont-Regular.ttf", "HuFont-Medium.ttf", "HuFont-Bold.ttf")


def install_hufont():
    """First-run best-effort install of the bundled HuFont TTF weights into the system font
    directory (design skill F20④), so tkinter can address them by family name.

    TTF (fonts/ttf/*.ttf) is the only install source — the .otf files kept alongside are
    design-source-only per the skill and must never be installed (design skill §2.4):
    they have a genuine maxp/hmtx defect, and being CFF-outline OTFs rather than TrueType
    glyf outlines is the more likely root cause of HuFont failing to load at all on a real
    macOS run — not just the corrupted-glyph symptom that surfaced on
    Linux/Pango. The TTF weights fix both.

    Never raises — a failure here just means display_font() falls back to system sans-serif,
    same as if HuFont were never installed at all. Returns True only if a font file was
    newly copied *in this run*: the OS font list Tk queries at startup won't see it until
    the app restarts, so the caller should surface that to the user.
    """
    installed_now = False
    try:
        system = platform.system()
        if system == "Darwin":
            dest_dir = os.path.expanduser("~/Library/Fonts")
            os.makedirs(dest_dir, exist_ok=True)
            for name in HUFONT_TTF_NAMES:
                src = resource_path("fonts", "ttf", name)
                dst = os.path.join(dest_dir, name)
                if os.path.exists(src) and not os.path.exists(dst):
                    shutil.copyfile(src, dst)
                    installed_now = True
        elif system == "Windows":
            dest_dir = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
                                     "Microsoft", "Windows", "Fonts")
            os.makedirs(dest_dir, exist_ok=True)
            import ctypes
            import winreg
            FR_PRIVATE = 0x10
            for name in HUFONT_TTF_NAMES:
                src = resource_path("fonts", "ttf", name)
                dst = os.path.join(dest_dir, name)
                if os.path.exists(src) and not os.path.exists(dst):
                    shutil.copyfile(src, dst)
                    ctypes.windll.gdi32.AddFontResourceExW(dst, FR_PRIVATE, 0)
                    weight = name.split("-")[1].split(".")[0]
                    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                          r"Software\Microsoft\Windows NT\CurrentVersion\Fonts",
                                          0, winreg.KEY_SET_VALUE)
                    winreg.SetValueEx(key, f"HuFont {weight} (TrueType)", 0, winreg.REG_SZ, dst)
                    winreg.CloseKey(key)
                    installed_now = True
    except Exception:
        pass
    return installed_now


# The TTF weights (fonts/ttf/*.ttf, design skill) fix both known defects in the old
# OTF delivery: a real maxp/hmtx metadata mismatch, and — the likelier root cause of HuFont
# failing to load at all on a real macOS run rather than just rendering corrupted glyphs —
# being CFF-outline OTFs instead of TrueType glyf outlines. Re-enabled on that basis; flip
# back to False if a real machine still shows blank/broken text after restarting.
HUFONT_USABLE = True


def init_fonts():
    """Must be called once a Tk root exists (tkfont.families() needs it)."""
    if _FONT_CACHE:
        return
    display_candidates = ["HuFont"] if HUFONT_USABLE else []
    _FONT_CACHE["display"] = _pick_font(display_candidates + ["Helvetica Neue", "Inter", "PingFang SC", "Helvetica"])
    _FONT_CACHE["ui"] = _pick_font(["Helvetica Neue", "Inter", "PingFang SC", "Helvetica"])


def display_font(size, weight="bold"):
    return (_FONT_CACHE["display"], size, weight)


def ui_font(size, weight="normal"):
    return (_FONT_CACHE["ui"], size, weight)


# ============================================================
# Geometric icon drawing (design skill §3) — zero emoji, everything is a shape on a Canvas.
# This also covers dropdown-indicator triangles etc. — no Unicode glyphs standing in for
# icons anywhere, since glyph shapes for things like ▾ aren't consistent across platforms.
# ============================================================

def canvas_center(canvas):
    """Exact geometric center of a Canvas from its actual configured size (F20⑤: alignment
    must come from the layout system, not a second independently-rounded 'half of N' guess —
    two separately-rounded halves can land a pixel apart from the real center and read as a
    crooked icon at these small sizes)."""
    return int(canvas["width"]) / 2, int(canvas["height"]) / 2


def draw_dot(canvas, cx, cy, r, color):
    canvas.create_oval(cx - r, cy - r, cx + r, cy + r, fill=color, outline="")


def draw_triangle(canvas, cx, cy, size, color, filled=True, direction="up"):
    if direction == "down":
        pts = [cx, cy + size, cx - size, cy - size * 0.8, cx + size, cy - size * 0.8]
    else:
        pts = [cx, cy - size, cx - size, cy + size * 0.8, cx + size, cy + size * 0.8]
    if filled:
        canvas.create_polygon(*pts, fill=color, outline="")
    else:
        canvas.create_polygon(*pts, fill="", outline=color, width=2)


def draw_hamburger(canvas, cx, cy, half_w, ink, gap=None):
    """Settings icon (design skill §3/F20⑥): three equal-length, equidistant horizontal
    bars with round caps. Coordinates are rounded to integer pixels — sub-pixel strokes
    blur and can look skewed — and the three y-offsets (-gap, 0, +gap) average out to
    exactly cy, so the glyph's geometric center is always the canvas center."""
    if gap is None:
        gap = max(3, round(half_w * 0.6))
    x0, x1 = round(cx - half_w), round(cx + half_w)
    y = round(cy)
    for dy in (-gap, 0, gap):
        canvas.create_line(x0, y + dy, x1, y + dy, fill=ink, width=2, capstyle=tk.ROUND)


def draw_square_outline(canvas, x0, y0, x1, y1, ink, width=2):
    canvas.create_rectangle(x0, y0, x1, y1, outline=ink, width=width)


def draw_wave(canvas, x, y, w, h, ink):
    """The mascot snake, walking state: a single wavy line with a dot head."""
    pts = []
    steps = 20
    for i in range(steps + 1):
        t = i / steps
        px = x + t * w * 0.8
        py = y + h / 2 + math.sin(t * 4 * math.pi) * h * 0.35
        pts.extend([px, py])
    canvas.create_line(*pts, fill=ink, width=2, smooth=True)
    draw_dot(canvas, x + w * 0.8, y + h / 2, 3, ink)


def draw_spiral(canvas, cx, cy, r, ink):
    """The mascot snake, caught state: coiled up."""
    pts = []
    steps = 36
    turns = 2.1
    for i in range(steps + 1):
        t = i / steps
        angle = t * turns * 2 * math.pi
        radius = t * r
        pts.extend([cx + radius * math.cos(angle), cy + radius * math.sin(angle)])
    canvas.create_line(*pts, fill=ink, width=2, smooth=True)


def draw_sticker(canvas, cx, cy, size, color, shape):
    if shape == "triangle":
        draw_triangle(canvas, cx, cy, size, color, filled=True)
    else:
        draw_dot(canvas, cx, cy, size, color)


# ============================================================
# Duration formatting for the Skip menu (F10) — "Next N" always shows the real wall-clock
# duration (N × INTERVAL_MINUTES), never a bare "Skip N"
# ============================================================

def format_skip_duration(n, interval=INTERVAL_MINUTES):
    total_min = n * interval
    h, m = divmod(total_min, 60)
    if h == 0:
        return f"{m} min"
    if m == 0:
        return f"{h} h"
    if m == 30:
        return f"{h}.5 h"
    return f"{h} h {m} m"


def skip_options(interval=INTERVAL_MINUTES):
    return [(n, f"Next {n} · {format_skip_duration(n, interval)}") for n in range(1, 6)]


# ============================================================
# Autostart at login (F19) — no packaging required, points straight at this script
# ============================================================

def _autostart_plist_path():
    return os.path.expanduser("~/Library/LaunchAgents/com.walkwalk.app.plist")


def is_autostart_enabled():
    system = platform.system()
    if system == "Darwin":
        return os.path.exists(_autostart_plist_path())
    if system == "Windows":
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                 r"Software\Microsoft\Windows\CurrentVersion\Run") as key:
                winreg.QueryValueEx(key, "WalkWalk")
            return True
        except Exception:
            return False
    return False


def _launch_target():
    """(executable, args) to relaunch this app — handles both `python3 walkwalk.py` and a frozen build."""
    if getattr(sys, "frozen", False):
        return sys.executable, []
    return sys.executable, [os.path.abspath(__file__)]


def set_autostart_enabled(enabled):
    system = platform.system()
    if system == "Darwin":
        path = _autostart_plist_path()
        if enabled:
            exe, args = _launch_target()
            arg_xml = "".join(f"<string>{a}</string>" for a in [exe] + args)
            plist = (
                '<?xml version="1.0" encoding="UTF-8"?>\n'
                '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" '
                '"http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
                '<plist version="1.0"><dict>\n'
                '<key>Label</key><string>com.walkwalk.app</string>\n'
                f'<key>ProgramArguments</key><array>{arg_xml}</array>\n'
                '<key>RunAtLoad</key><true/>\n'
                '<key>KeepAlive</key><false/>\n'
                '</dict></plist>\n'
            )
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w") as f:
                f.write(plist)
            subprocess.run(["launchctl", "unload", path], capture_output=True)
            subprocess.run(["launchctl", "load", path], capture_output=True)
        else:
            if os.path.exists(path):
                subprocess.run(["launchctl", "unload", path], capture_output=True)
                try:
                    os.remove(path)
                except OSError:
                    pass
    elif system == "Windows":
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                  r"Software\Microsoft\Windows\CurrentVersion\Run",
                                  0, winreg.KEY_SET_VALUE)
            if enabled:
                exe, args = _launch_target()
                if not getattr(sys, "frozen", False):
                    exe = exe.replace("python.exe", "pythonw.exe")
                cmd = " ".join(f'"{p}"' for p in [exe] + args)
                winreg.SetValueEx(key, "WalkWalk", 0, winreg.REG_SZ, cmd)
            else:
                try:
                    winreg.DeleteValue(key, "WalkWalk")
                except FileNotFoundError:
                    pass
            winreg.CloseKey(key)
        except Exception:
            pass
    # other platforms: no-op, nothing to wire up


# ============================================================
# Auto meeting detection (F12) — replaces the old manual meeting-mode dropdown.
# Failure/unsupported platform => treated as "not in a meeting" (better to over-remind than miss one)
# ============================================================

MEETING_PROCESS_NAMES = ("zoom.us", "Teams", "Google Meet", "Meet Helper", "Slack Huddle", "Webex")


def is_in_meeting():
    try:
        system = platform.system()
        if system == "Windows":
            return _meeting_windows()
        if system == "Darwin":
            return _meeting_mac_heuristic()
    except Exception:
        pass
    return False


def _consent_subtree_in_use(key):
    import winreg
    i = 0
    while True:
        try:
            sub_name = winreg.EnumKey(key, i)
        except OSError:
            return False
        i += 1
        try:
            with winreg.OpenKey(key, sub_name) as sub_key:
                stop, _ = winreg.QueryValueEx(sub_key, "LastUsedTimeStop")
                if stop == 0:
                    return True
        except (FileNotFoundError, OSError):
            continue


def _meeting_windows():
    import winreg
    base = r"Software\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore"
    for device in ("webcam", "microphone"):
        for suffix in ("", r"\NonPackaged"):
            try:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, base + "\\" + device + suffix) as key:
                    if _consent_subtree_in_use(key):
                        return True
            except FileNotFoundError:
                continue
    return False


def _meeting_mac_heuristic():
    try:
        out = subprocess.run(["ps", "-axo", "comm"], capture_output=True, text=True, timeout=0.2).stdout
    except Exception:
        return False
    lowered = out.lower()
    return any(name.lower() in lowered for name in MEETING_PROCESS_NAMES)


# ============================================================
# Hand-drawn controls (design skill F20) — tk.Button/Spinbox/Checkbutton/Radiobutton/
# OptionMenu were observed rendering with native OS chrome on real macOS (ignoring custom
# colors entirely — confirmed by screenshot: a plain gray button where a yellow one should
# be). Every clickable control here is a plain Frame/Label/Canvas with mouse bindings instead,
# so its appearance is fully ours on every platform.
# ============================================================

BUTTON_HEIGHT = 36  # design skill §5: buttons are this fixed height (scaled by s())
DROPDOWN_ITEM_H = 28  # design skill §7-2: Skip menu rows (5 items = 143px, fits the 360x240 floor)
TITLE_MAX_PX = 32   # F20⑤a: title starts at 32px and steps down 2px at a time...
TITLE_MIN_PX = 22   # ...to 22px minimum; below that the WINDOW widens, the text never wraps
QUOTE_MAX_PX = 24   # §2.3 table: quote 24px, wraps to 2 lines BEFORE shrinking...
QUOTE_MIN_PX = 18   # ...and only steps down to 18 if two lines still can't hold it


def strip_native_chrome(win):
    """F20① (design skill): every Toplevel — the popup itself AND the dropdown panel — must
    lose its system chrome. overrideredirect alone is not enough on macOS: the OS still
    applies its own rounded-corner mask and drop shadow to borderless windows (that's the
    native-popover arc seen on the Skip menu), and only the unsupported MacWindowStyle
    call actually turns the window into a plain unstyled rect."""
    win.overrideredirect(True)
    if platform.system() == "Darwin":
        try:
            win.tk.call("::tk::unsupported::MacWindowStyle", "style", win._w,
                         "plain", "noActivates")
        except tk.TclError:
            pass  # older Tk builds — overrideredirect is the best we can do
    win.attributes("-topmost", True)


# Cap-height ratio per display/UI family, measured from the font files (design skill F20⑤).
# create_text(anchor='center') centers the ascent+descent BOX, but the eye centers on the
# cap-letter block — the gap between those two is exactly why text kept looking low even
# when the layout math was "correct".
CAP_EM = {"HuFont": 0.700, "Helvetica Neue": 0.717, "Inter": 0.727}
_TKFONT_OBJS = {}


def _tkfont_for(spec):
    """tkfont.Font instance for a ('family', size, *mods) spec, cached — Font construction
    is not free and buttons redraw on every hover."""
    key = tuple(spec)
    if key not in _TKFONT_OBJS:
        mods = spec[2:] if len(spec) > 2 else ()
        _TKFONT_OBJS[key] = tkfont.Font(
            family=spec[0], size=spec[1],
            weight=("bold" if "bold" in mods else "normal"),
            underline=("underline" in mods),
        )
    return _TKFONT_OBJS[key]


def _em_pixels(size):
    """Font spec sizes are in points (Tk convention for positive sizes); metrics() returns
    pixels. Convert via Tk's own point->pixel scaling so the cap-height formula compares
    like with like. Negative sizes are already pixels."""
    if size < 0:
        return -size
    root = tk._default_root
    try:
        return size * float(root.tk.call("tk", "scaling"))
    except (AttributeError, tk.TclError):
        return size * 96 / 72


def optical_text_y(height, font_spec):
    """The y to pass to create_text(anchor='center'/'w') so the CAP-LETTER BLOCK — not the
    ascent+descent box — sits at height/2 (design skill F20⑤):
        cy = h/2 + (CAP_EM*S - ascent + descent) / 2
    """
    f = _tkfont_for(font_spec)
    cap = CAP_EM.get(font_spec[0], 0.72) * _em_pixels(font_spec[1])
    return height / 2 + (cap - f.metrics("ascent") + f.metrics("descent")) / 2


class CanvasButton:
    """F20⑤ (design skill): a button is ONE tk.Canvas — rectangle, text, and any dropdown
    triangle all drawn on the same canvas from measured coordinates. The previous
    Frame+Label+padding construction was retired by the design walkthrough as impossible
    to align reliably across platforms. hard_shadow=True adds the offset ink shadow
    reserved for the primary action (§5); pressing shifts the face into the shadow.
    hover/pressed fills come from the fixed complementary table (F20⑥)."""

    def __init__(self, parent, text, bg, ink, font, command, accent,
                 padx=14, height=BUTTON_HEIGHT, hard_shadow=False,
                 dropdown_arrow=False, arrow_size=4, cursor="hand2"):
        self.text, self.bg, self.ink, self.font = text, bg, ink, font
        self.command = command
        self.hover_bg, self.press_bg = complementary_states(accent)
        self.offset = 3 if hard_shadow else 0
        self.hard_shadow = hard_shadow
        self.arrow_size = arrow_size if dropdown_arrow else 0

        self._font_obj = _tkfont_for(font)
        self._text_w = self._font_obj.measure(text)
        content_w = self._text_w + ((8 + 2 * self.arrow_size) if dropdown_arrow else 0)
        self.w = content_w + 2 * padx
        self.h = height
        self.padx = padx

        self.canvas = tk.Canvas(parent, width=self.w + self.offset, height=self.h + self.offset,
                                 bg=parent.cget("bg"), highlightthickness=0, cursor=cursor)
        self._state = "idle"
        self._redraw()
        self.canvas.bind("<Enter>", lambda e: self._set_state("hover"))
        self.canvas.bind("<Leave>", lambda e: self._set_state("idle"))
        self.canvas.bind("<ButtonPress-1>", lambda e: self._set_state("pressed"))
        self.canvas.bind("<ButtonRelease-1>", self._on_release)

    def _set_state(self, state):
        self._state = state
        self._redraw()

    def _on_release(self, _e):
        self._set_state("idle")
        self.command()

    def invoke(self):
        self.command()

    def _fill(self):
        return {"idle": self.bg, "hover": self.hover_bg, "pressed": self.press_bg}[self._state]

    def _redraw(self):
        cv = self.canvas
        cv.delete("all")
        pressed = self._state == "pressed"
        dx = dy = self.offset if (self.hard_shadow and pressed) else 0
        if self.hard_shadow and not pressed:
            cv.create_rectangle(self.offset + 1, self.offset + 1,
                                 self.offset + self.w - 1, self.offset + self.h - 1,
                                 fill=self.ink, outline="")
        cv.create_rectangle(dx + 1, dy + 1, dx + self.w - 1, dy + self.h - 1,
                             fill=self._fill(), outline=self.ink, width=1.5)
        ty = dy + optical_text_y(self.h, self.font)
        if self.arrow_size:
            # compound content ("Skip ▾"): text + gap + triangle centered AS A GROUP
            total = self._text_w + 8 + 2 * self.arrow_size
            x0 = dx + (self.w - total) / 2
            cv.create_text(x0 + self._text_w / 2, ty, text=self.text, font=self._font_obj,
                           fill=self.ink, anchor="center")
            tcx = x0 + self._text_w + 8 + self.arrow_size
            tcy = dy + self.h / 2
            a = self.arrow_size
            cv.create_polygon(tcx - a, tcy - a * 0.7, tcx + a, tcy - a * 0.7, tcx, tcy + a,
                              fill=self.ink, outline="")
        else:
            cv.create_text(dx + self.w / 2, ty, text=self.text, font=self._font_obj,
                           fill=self.ink, anchor="center")

    def pack(self, **kw):
        self.canvas.pack(**kw)
        return self


class CanvasChip:
    """Toggle chip (mode pill / day chip / Every day) as a single Canvas — F20⑦ zero
    borderless controls: 1.5px ink outline in EVERY state, card fill off / accent fill on,
    complementary hover/pressed (F20⑥)."""

    def __init__(self, parent, text, ink, off_bg, on_bg, font, on_click, accent,
                 padx=8, pady=4):
        self.text, self.ink, self.off_bg, self.on_bg, self.font = text, ink, off_bg, on_bg, font
        self.hover_bg, self.press_bg = complementary_states(accent)
        self.on = False
        self._state = "idle"
        self._font_obj = _tkfont_for(font)
        self.w = self._font_obj.measure(text) + 2 * padx + 2
        self.h = self._font_obj.metrics("linespace") + 2 * pady
        self.canvas = tk.Canvas(parent, width=self.w, height=self.h,
                                 bg=parent.cget("bg"), highlightthickness=0, cursor="hand2")
        self._redraw()
        self.canvas.bind("<Enter>", lambda e: self._set_state("hover"))
        self.canvas.bind("<Leave>", lambda e: self._set_state("idle"))
        self.canvas.bind("<ButtonPress-1>", lambda e: self._set_state("pressed"))
        self.canvas.bind("<ButtonRelease-1>", lambda e: (self._set_state("idle"), on_click(self)))

    def _set_state(self, state):
        self._state = state
        self._redraw()

    def set(self, on):
        self.on = on
        self._redraw()

    def _fill(self):
        if self._state == "hover":
            return self.hover_bg
        if self._state == "pressed":
            return self.press_bg
        return self.on_bg if self.on else self.off_bg

    def _redraw(self):
        cv = self.canvas
        cv.delete("all")
        cv.create_rectangle(1, 1, self.w - 1, self.h - 1,
                             fill=self._fill(), outline=self.ink, width=1.5)
        cv.create_text(self.w / 2, optical_text_y(self.h, self.font), text=self.text,
                       font=self._font_obj, fill=self.ink, anchor="center")

    def pack(self, **kw):
        self.canvas.pack(**kw)
        return self


def make_checkbox_row(parent, text, ink, bg, accent, font, initial, on_toggle):
    """Self-drawn checkbox (design skill §7: ink outline square, accent fill with an ink
    check mark when on): a small Canvas square + label, click toggles both."""
    row = tk.Frame(parent, bg=bg)
    box = 16
    canvas = tk.Canvas(row, width=box, height=box, bg=bg, highlightthickness=0, cursor="hand2")
    canvas.pack(side="left")
    label = tk.Label(row, text=text, bg=bg, fg=ink, font=font, cursor="hand2")
    label.pack(side="left", padx=(8, 0))

    state = {"on": initial}

    def redraw():
        canvas.delete("all")
        if state["on"]:
            canvas.create_rectangle(2, 2, box - 2, box - 2, fill=accent, outline="")
            canvas.create_line(5, 8, 7, 11, fill=ink, width=2, capstyle=tk.ROUND)
            canvas.create_line(7, 11, 11, 5, fill=ink, width=2, capstyle=tk.ROUND)
        draw_square_outline(canvas, 2, 2, box - 2, box - 2, ink, width=2)

    def toggle(_e=None):
        state["on"] = not state["on"]
        redraw()
        on_toggle(state["on"])

    canvas.bind("<Button-1>", toggle)
    label.bind("<Button-1>", toggle)
    redraw()
    return row, state


def make_slider(parent, ink, bg, accent, min_v, max_v, initial, on_change,
                width=120, height=22, step=1):
    """Hand-drawn horizontal slider (F20②: tk.Scale is a native widget and banned):
    a single Canvas with a 2px ink track and a square accent handle with the usual
    1.5px ink outline (F20⑦ — no borderless controls). Click or drag anywhere on the
    track to set; values snap to `step`; hover paints the handle with the palette's
    complementary hover color (F20⑥)."""
    hover_bg, press_bg = complementary_states(accent)
    state = {"value": max(min_v, min(max_v, initial))}
    handle = 14
    pad = handle // 2 + 2  # keep the square handle fully inside the canvas at both ends
    cv = tk.Canvas(parent, width=width, height=height, bg=bg, highlightthickness=0,
                    cursor="hand2")
    ui = {"state": "idle"}

    def x_of(value):
        frac = (value - min_v) / (max_v - min_v)
        return pad + frac * (width - 2 * pad)

    def value_of(x):
        frac = (x - pad) / (width - 2 * pad)
        raw = min_v + frac * (max_v - min_v)
        snapped = round(raw / step) * step
        return max(min_v, min(max_v, snapped))

    def redraw():
        cv.delete("all")
        cy = height / 2
        cv.create_line(2, cy, width - 2, cy, fill=ink, width=2, capstyle=tk.ROUND)
        hx = x_of(state["value"])
        fill = {"idle": accent, "hover": hover_bg, "pressed": press_bg}[ui["state"]]
        cv.create_rectangle(hx - handle / 2, cy - handle / 2, hx + handle / 2, cy + handle / 2,
                             fill=fill, outline=ink, width=1.5)

    def set_from_event(e):
        new = value_of(e.x)
        if new != state["value"]:
            state["value"] = new
            redraw()
            on_change(new)
        else:
            redraw()

    def on_press(e):
        ui["state"] = "pressed"
        set_from_event(e)

    def on_drag(e):
        set_from_event(e)

    def on_release(_e):
        ui["state"] = "idle"
        redraw()

    def on_enter(_e):
        if ui["state"] != "pressed":
            ui["state"] = "hover"
            redraw()

    def on_leave(_e):
        if ui["state"] != "pressed":
            ui["state"] = "idle"
            redraw()

    cv.bind("<ButtonPress-1>", on_press)
    cv.bind("<B1-Motion>", on_drag)
    cv.bind("<ButtonRelease-1>", on_release)
    cv.bind("<Enter>", on_enter)
    cv.bind("<Leave>", on_leave)
    redraw()
    return cv, state


def make_stepper(parent, ink, bg, font, initial_minutes, step, on_change, accent):
    """Time stepper as ONE bordered control (mockup .step: a single 1.5px ink box
    containing −, value, + — not three separately-boxed labels). Single Canvas; the −/+
    cells fill the complementary hover color on hover (F20⑥). Wraps 0..1439 minutes."""
    hover_bg, press_bg = complementary_states(accent)
    state = {"value": initial_minutes}
    f = _tkfont_for(font)

    def fmt():
        h, m = divmod(state["value"], 60)
        return f"{h:02d}:{m:02d}"

    btn_w = f.measure("+") + 16
    val_w = f.measure("88:88") + 12
    w = btn_w * 2 + val_w + 2
    h = f.metrics("linespace") + 6
    cv = tk.Canvas(parent, width=w, height=h, bg=bg, highlightthickness=0, cursor="hand2")
    hovered = {"cell": None}  # None | "minus" | "plus"

    def cell_of(x):
        if x <= btn_w:
            return "minus"
        if x >= btn_w + val_w:
            return "plus"
        return None

    def redraw():
        cv.delete("all")
        ty = optical_text_y(h, font)
        for cell, x0, x1, label in (("minus", 1, btn_w, "−"),
                                     ("plus", btn_w + val_w, w - 1, "+")):
            fill = hover_bg if hovered["cell"] == cell else bg
            cv.create_rectangle(x0, 1, x1, h - 1, fill=fill, outline="")
            cv.create_text((x0 + x1) / 2, ty, text=label, font=f, fill=ink, anchor="center")
        cv.create_text(btn_w + val_w / 2, ty, text=fmt(), font=f, fill=ink, anchor="center")
        cv.create_rectangle(1, 1, w - 1, h - 1, fill="", outline=ink, width=1.5)

    def on_motion(e):
        cell = cell_of(e.x)
        if cell != hovered["cell"]:
            hovered["cell"] = cell
            redraw()

    def on_leave(_e):
        hovered["cell"] = None
        redraw()

    def on_click(e):
        cell = cell_of(e.x)
        if cell is None:
            return
        state["value"] = (state["value"] + (step if cell == "plus" else -step)) % (24 * 60)
        redraw()
        on_change(state["value"])

    cv.bind("<Motion>", on_motion)
    cv.bind("<Leave>", on_leave)
    cv.bind("<Button-1>", on_click)
    redraw()
    return cv, state


class SkipMenu:
    """The Skip menu as an IN-WINDOW Canvas overlay (design skill §7-2). It must NOT be a
    Toplevel: the modern macOS window server force-applies a rounded-corner mask + shadow
    to every borderless window, and neither overrideredirect nor MacWindowStyle plain can
    remove it — that's the real reason the Skip menu kept its native arcs. A canvas placed
    inside the popup itself can never have system chrome. Opens UPWARD: menu bottom sits
    4px above the trigger's top edge. Dismissed by choosing, clicking anywhere else in the
    popup, or Esc."""

    def __init__(self, popup, anchor_canvas, options, ink, bg, font, on_select, accent,
                 item_height=None):
        self.popup = popup
        self.on_select = on_select
        self.options = list(options)
        self.item_h = item_height or DROPDOWN_ITEM_H
        hover_bg, _press = complementary_states(accent)
        f = _tkfont_for(font)
        pad_x = 12
        w = max(150, max(f.measure(label) for _v, label in self.options) + 2 * pad_x)
        h = self.item_h * len(self.options) + 2

        cv = tk.Canvas(popup, width=w, height=h, bg=bg, highlightthickness=0, cursor="hand2")
        self.canvas = cv
        hovered = {"idx": None}

        def redraw():
            cv.delete("all")
            for i, (_value, label) in enumerate(self.options):
                top = 1 + i * self.item_h
                if hovered["idx"] == i:
                    cv.create_rectangle(1, top, w - 1, top + self.item_h,
                                         fill=hover_bg, outline="")
                cv.create_text(pad_x, top + optical_text_y(self.item_h, font),
                               text=label, font=f, fill=ink, anchor="w")
            cv.create_rectangle(1, 1, w - 1, h - 1, fill="", outline=ink, width=1.5)

        def idx_of(y):
            i = int((y - 1) // self.item_h)
            return i if 0 <= i < len(self.options) else None

        def on_motion(e):
            i = idx_of(e.y)
            if i != hovered["idx"]:
                hovered["idx"] = i
                redraw()

        def on_leave(_e):
            hovered["idx"] = None
            redraw()

        def on_click(e):
            i = idx_of(e.y)
            if i is not None:
                self.choose(self.options[i][0])
            return "break"  # don't let the popup-wide dismiss binding see this click

        cv.bind("<Motion>", on_motion)
        cv.bind("<Leave>", on_leave)
        cv.bind("<Button-1>", on_click)
        redraw()

        # place: menu bottom edge = trigger top edge - 4px, LEFT-ALIGNED with the trigger.
        # The anchor's position inside the popup is computed by summing winfo_x/y up the
        # parent chain — never via winfo_rootx() subtraction: on macOS the root coordinates
        # of a borderless (overrideredirect) window can be reported with an offset, which
        # showed up as the menu sitting visibly left of the Skip button.
        popup.update_idletasks()
        ax, ay = 0, 0
        node = anchor_canvas
        while node is not None and node is not popup:
            ax += node.winfo_x()
            ay += node.winfo_y()
            node = node.master
        # winfo_x() is measured from the window edge INCLUDING the popup's 2px highlight
        # border, but place() coordinates start inside it — compensate or the menu lands
        # border-width to the right of the trigger
        border = int(float(popup.cget("highlightthickness") or 0))
        x = max(0, min(ax - border, popup.winfo_width() - w - 2 * border))
        y = max(0, ay - border - 4 - h)
        cv.place(x=x, y=y)
        # Canvas.lift()/tkraise() are the canvas-ITEM raise methods — for raising the
        # widget itself in the stacking order, call the plain Misc implementation
        tk.Misc.tkraise(cv)

        # click anywhere else in the popup, or Esc, closes the menu. Key events need
        # keyboard focus, which an override-redirect window doesn't always hold — grab it
        # best-effort; the click-outside path works regardless.
        self._click_bind = popup.bind("<Button-1>", self._maybe_dismiss_outside, add="+")
        self._esc_bind = popup.bind("<Escape>", lambda e: self._dismiss(), add="+")
        try:
            popup.focus_set()
        except tk.TclError:
            pass

    def _maybe_dismiss_outside(self, event):
        cv = self.canvas
        try:
            if event.widget is cv:
                return
            x, y = cv.winfo_rootx(), cv.winfo_rooty()
            w, h = cv.winfo_width(), cv.winfo_height()
        except tk.TclError:
            return
        if not (x <= event.x_root <= x + w and y <= event.y_root <= y + h):
            self._dismiss()

    def winfo_exists(self):
        try:
            return bool(self.canvas.winfo_exists()) and bool(self.canvas.winfo_manager())
        except tk.TclError:
            return False

    def choose(self, value):
        self.on_select(value)
        self._dismiss()

    @staticmethod
    def _remove_binding(widget, seq, funcid):
        """tkinter's unbind(seq, funcid) wipes EVERY handler on the sequence, not just
        funcid — and the popup's drag handler lives on the same <Button-1> event. Strip
        only our own line from the bind script instead."""
        try:
            script = widget.bind(seq)
            kept = "\n".join(line for line in script.splitlines() if funcid not in line)
            widget.bind(seq, kept if kept.strip() else "")
            widget.deletecommand(funcid)
        except tk.TclError:
            pass

    def _dismiss(self):
        self._remove_binding(self.popup, "<Button-1>", self._click_bind)
        self._remove_binding(self.popup, "<Escape>", self._esc_bind)
        try:
            self.canvas.place_forget()
            self.canvas.destroy()
        except tk.TclError:
            pass


# ============================================================
# Reminder popup (F4-F14) + inline settings (F15-F20)
# ============================================================

class ReminderPopup(tk.Toplevel):
    def __init__(self, master, on_closed, config, on_settings_saved, walk_no, palette):
        super().__init__(master)
        self.on_closed = on_closed
        self.config_data = dict(config)
        self.on_settings_saved = on_settings_saved
        self.palette = palette  # F5a: one palette per day, chosen by the caller
        self.walk_no = walk_no
        self.quote = random.choice(load_quotes())

        self.captured = False
        self.settings_open = False
        self._move_job = None
        self._drag_start = None
        self._last_pointer_pos = None
        self._pointer_last_moved_at = 0.0
        self._skip_menu = None

        self.title("walk walk")
        self.resizable(False, False)
        # F20①: no system window chrome (title bar / native rounded corners / traffic-light
        # buttons; on macOS also the forced corner mask + shadow, via MacWindowStyle) —
        # closing is entirely handled by the in-window buttons (I'm up! / Skip / Not today),
        # dragging by the custom blank-area drag below (F7b)
        strip_native_chrome(self)
        self.protocol("WM_DELETE_WINDOW", lambda: self._close())
        # outer ink frame (design skill §4.1 round-outside/square-inside): tkinter can't round the window
        # corners, but the ink outline itself is part of the cut-paper look and shouldn't
        # be dropped along with the corner radius
        self.configure(highlightthickness=2, highlightbackground=INK, highlightcolor=INK)

        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        width = max(POPUP_MIN_WIDTH, screen_w // 4)
        height = max(POPUP_MIN_HEIGHT, screen_h // 4)
        self.width, self.base_height = width, height
        # Font/icon/padding sizes below are tuned against a "comfortable" ~270px-tall popup
        # (a typical 1080p screen's screen/4). Smaller screens produce a shorter popup per F4,
        # so everything scales down together rather than clipping the quote card at the
        # 360x240 floor (F4).
        self.scale = max(0.72, min(1.0, height / 270))

        # F20⑤a + F4: the title must stay on ONE line. If the longest fixed title can't fit
        # even at the minimum title size, widen the window — never wrap. Checked with the
        # longest of the two fixed titles so a mid-life text swap (catch -> caught) can
        # never force a wrap either.
        s = lambda n: max(1, round(n * self.scale))  # noqa: E731
        longest_title = max(("Catch me first!", "Time to walk!"),
                            key=lambda t: len(t))
        min_font = tkfont.Font(family=_FONT_CACHE["display"], size=s(TITLE_MIN_PX), weight="bold")
        needed = min_font.measure(longest_title) + self._title_chrome_px(s)
        if needed > self.width:
            self.width = needed

        self.min_x, self.max_x = POPUP_MARGIN, max(POPUP_MARGIN, screen_w - self.width - POPUP_MARGIN)
        self.min_y = POPUP_MARGIN
        self.max_y = max(POPUP_MARGIN, screen_h - height - BOTTOM_RESERVE)

        x = random.randint(self.min_x, self.max_x)
        y = random.randint(self.min_y, self.max_y)
        self.pos_x, self.pos_y = float(x), float(y)
        self.cur_height = height
        self.set_geometry()  # F20⑧: the one and only way this window's geometry is applied

        # F23: walk speed comes from settings (px/frame), clamped to the slider's range
        self.speed = max(WALK_SPEED_MIN, min(WALK_SPEED_MAX,
                          int(self.config_data.get("walk_speed", POPUP_MOVE_SPEED))))
        heading = random.uniform(0, 2 * math.pi)
        self.dx = self.speed * math.cos(heading)
        self.dy = self.speed * math.sin(heading)

        self.configure(bg=self.palette["bg"])
        self._build_widgets()

        self.bind("<Enter>", self._on_capture)
        self.bind("<Motion>", self._on_capture)  # catches the case where the popup arrives
                                                  # under an already-idle cursor (no <Enter> to
                                                  # re-fire), and the user nudges the mouse
                                                  # afterward while it's still inside the window
        self._move_step()

    # ---------- geometry (F20⑧: single exit) ----------

    def set_geometry(self, width=None, height=None, x=None, y=None):
        """The ONLY place this window's geometry() is ever called (F20⑧). Always applies
        the full WxH+X+Y string — a size-only geometry(f"{w}x{h}") hands the window back
        to the window manager to re-place, which is exactly the "popup jumps when settings
        opens" bug. self.width/cur_height/pos_x/pos_y are the single source of truth;
        walking, settings expand/collapse, and dragging all funnel through here."""
        if width is not None:
            self.width = int(width)
        if height is not None:
            self.cur_height = int(height)
        if x is not None:
            self.pos_x = float(x)
        if y is not None:
            self.pos_y = float(y)
        self.geometry(f"{self.width}x{self.cur_height}+{int(self.pos_x)}+{int(self.pos_y)}")

    # ---------- UI ----------

    def _build_widgets(self):
        for child in self.winfo_children():
            child.destroy()

        p = self.palette
        s = lambda n: max(1, round(n * self.scale))  # noqa: E731

        # info bar (F8a): card-colored band, 1px ink rule below
        info_bar = tk.Frame(self, bg=p["card"], highlightthickness=0, bd=0)
        info_bar.pack(fill="x")
        tk.Frame(self, bg=INK, height=1).pack(fill="x")

        tk.Label(info_bar, text="walk walk", fg=INK, bg=p["card"],
                 font=display_font(s(14), "bold")).pack(side="left", padx=s(16), pady=s(8))
        tk.Label(info_bar, text=f"walk no.{self.walk_no}", fg=INK, bg=p["card"],
                 font=ui_font(s(10))).pack(side="left", expand=True)  # utility small text: 10
        settings_icon = tk.Canvas(info_bar, width=s(28), height=s(28), bg=p["card"],
                                   highlightthickness=0, cursor="hand2")
        settings_icon.pack(side="right", padx=s(10), pady=s(4))
        icx, icy = canvas_center(settings_icon)
        draw_hamburger(settings_icon, icx, icy, s(9), INK)
        settings_icon.bind("<Button-1>", lambda e: self._toggle_settings())

        # settings panel (F15): created ONCE here and kept resident for the popup's whole
        # life (design skill §7-8 no-flicker rule — expand/collapse only pack/pack_forget it,
        # never destroy + rebuild). Packed FIRST among side="bottom" widgets so — when shown
        # — it sits at the true bottom edge with the action row above it; hidden again at
        # the end of this build.
        self.settings_panel = tk.Frame(self, bg=p["card"])
        self.settings_sep = tk.Frame(self, bg=INK, height=1)
        self.settings_panel.pack(side="bottom", fill="x")
        self.settings_sep.pack(side="bottom", fill="x")

        # action row: primary button + skip dropdown + Not today, all on a card band.
        # Packed side="bottom" *before* the expanding quote card below, so it and the title
        # area both get their full requested size reserved first — otherwise pack silently
        # compresses whichever fixed-size row it reaches last once content (at design-skill
        # sizing) is taller than F4's screen/4 window budget.
        self._action_sep = tk.Frame(self, bg=INK, height=1)
        self._action_sep.pack(side="bottom", fill="x")
        action_row = tk.Frame(self, bg=p["card"])
        action_row.pack(side="bottom", fill="x")
        inner = tk.Frame(action_row, bg=p["card"])
        inner.pack(fill="x", padx=s(24), pady=s(16))  # mockup .actions: padding 16px 24px

        # title area — the title sits DIRECTLY on bg (F20⑤a: no underlay block of any other
        # color, ever), head padding 24 top / 16 bottom per the mockup's .head rule. The
        # title is single-line: measure at s(32) and step down 2px at a time to s(22); if
        # even the minimum size can't fit, the window is widened (in __init__) — never
        # wrapped onto a second line.
        title_area = tk.Frame(self, bg=p["bg"])
        title_area.pack(fill="x", padx=s(24), pady=(s(24), s(16)))

        icon_col = tk.Canvas(title_area, width=s(30), height=s(46), bg=p["bg"], highlightthickness=0)
        icon_col.pack(side="left", padx=(0, s(12)))
        icon_cx, _ = canvas_center(icon_col)  # dot/triangle stack vertically on purpose,
        draw_dot(icon_col, icon_cx, s(11), s(8), p["accent"])  # so only x is canvas-derived —
        draw_triangle(icon_col, icon_cx, s(33), s(10), INK, filled=True)  # y stays as tuned offsets

        title_text = "Time to walk!" if self.captured else "Catch me first!"
        title_size = self._fit_title_size(title_text, s)
        self.title_label = tk.Label(
            title_area, text=title_text,
            fg=INK, bg=p["bg"], font=display_font(title_size, "bold"), justify="left",
        )
        self.title_label.pack(side="left", fill="x", expand=True)

        self.mascot = tk.Canvas(title_area, width=s(56), height=s(28), bg=p["bg"], highlightthickness=0)
        self.mascot.pack(side="right")
        self._draw_mascot()

        # every widget whose background plays the "bg" role — the capture flash recolors
        # these together with the Toplevel so no mismatched band is ever left behind
        self._bg_widgets = [title_area, icon_col, self.title_label, self.mascot]

        # quote card (F8, design skill §4 red line): the card is a FIXED two-line-height box —
        # 2 quote lines + 16px padding top and bottom — that never stretches or shrinks with
        # the quote, so card and window height stay identical across popups. The quote lays
        # out at 24px first, wraps to two lines before ever shrinking, and only steps down
        # (to 18px min) if two lines still can't hold it; a one-liner just centers in the
        # same fixed box. (The old behavior shrank the font to force one line — that's
        # exactly why quotes looked small.)
        card_wrap = tk.Frame(self, bg=p["bg"])
        card_wrap.pack(fill="both", expand=True, padx=s(24), pady=(0, s(16)))
        self._bg_widgets.append(card_wrap)

        quote_pad = s(16)
        quote_avail = self.width - 2 * s(24) - 2 * quote_pad - 8  # outer padx, card padding, border
        quote_text = f"“{self.quote['text']}”"
        by = self.quote.get("by")
        quote_size = self._fit_quote_size(quote_text, quote_avail, s)
        two_lines = _tkfont_for(display_font(s(QUOTE_MAX_PX), "bold")).metrics("linespace") * 2
        card_h = two_lines + 2 * quote_pad + (
            _tkfont_for(ui_font(s(10))).metrics("linespace") if by else 0)

        quote_card = tk.Frame(card_wrap, bg=p["card"], highlightbackground=INK,
                               highlightthickness=2, bd=0, height=card_h)
        quote_card.pack_propagate(False)
        quote_card.pack(fill="x", expand=True)

        quote_col = tk.Frame(quote_card, bg=p["card"])
        quote_col.place(relx=0.5, rely=0.5, anchor="center")
        tk.Label(quote_col, text=quote_text, fg=INK, bg=p["card"],
                 font=display_font(quote_size, "bold"), wraplength=quote_avail,
                 justify="center").pack()
        if by:
            tk.Label(quote_col, text=f"— {by}", fg=blend(INK, p["card"], 0.7), bg=p["card"],
                     font=ui_font(s(10))).pack()

        sticker_canvas = tk.Canvas(quote_card, width=s(24), height=s(24), bg=p["card"], highlightthickness=0)
        sticker_canvas.place(relx=1.0, rely=1.0, x=-6, y=-6, anchor="se")
        stx, sty = canvas_center(sticker_canvas)
        draw_sticker(sticker_canvas, stx, sty, s(9), p["sticker"], random.choice(["dot", "triangle"]))

        self._build_action_row(inner, p, s)

        # hide the resident settings panel now that everything is built — the popup always
        # opens compact; _toggle_settings shows/hides it without ever rebuilding
        self.settings_panel.pack_forget()
        self.settings_sep.pack_forget()

        # drag-by-blank-area once caught (F7b) — no title bar anymore, this is the only way.
        # ONE bind on the Toplevel covers every descendant (the toplevel sits in each
        # child's bindtags), so the handlers must gate on WHICH widget was pressed: without
        # the allowlist, dragging the settings slider (or any control) dragged the whole
        # window along with it. Only genuine blank surfaces may start a window drag.
        self._drag_surfaces = {self, card_wrap, quote_card, quote_col, title_area,
                                self.title_label, icon_col, self.mascot, action_row, inner}
        self._drag_surfaces.update(quote_col.winfo_children())
        self.bind("<ButtonPress-1>", self._on_drag_start, add="+")
        self.bind("<B1-Motion>", self._on_drag_motion, add="+")

        self._resize_to_content()

    def _resize_to_content(self):
        """Re-apply window height for the current content, holding the top-left corner
        still (F15 zero-shift expansion). winfo_reqheight() after a build reflects natural content
        height; the window never shrinks below the F4-tuned base_height but grows to fit —
        a quote wrapping to two lines must never have its descenders clipped just to hold
        an exact screen/4 height. Only when the taller window would run past the bottom
        edge does it move — upward, by exactly the overflow — and _toggle_settings restores
        the remembered y on collapse."""
        self.update_idletasks()
        total_height = max(self.base_height, self.winfo_reqheight())
        y = self.pos_y
        if total_height > self.base_height:
            screen_h = self.winfo_screenheight()
            max_y = max(POPUP_MARGIN, screen_h - total_height - BOTTOM_RESERVE)
            if y > max_y:
                y = float(max_y)
            if not self.settings_open:
                self.max_y = max_y  # keep the walk bounds honest for the taller window
        self.set_geometry(height=total_height, y=y)

    def _build_action_row(self, inner, p, s):
        # user-tuned type sizes (all-even rule): every action button — I'm up!/Skip/menu
        # items (and Save/Cancel in settings) — is 14; the Not today weak link matches
        # the 10px utility tier (walk no.X, settings row labels)
        self.imup_btn = CanvasButton(
            inner, "I'm up!", p["accent"], INK, ui_font(s(14), "bold"),
            command=lambda: self._close("ack"), accent=p["accent"],
            padx=s(16), height=s(BUTTON_HEIGHT), hard_shadow=True,
        )
        self.imup_btn.pack(side="left")

        def open_skip_menu():
            if self._skip_menu is not None and self._skip_menu.winfo_exists():
                return  # already open — the trigger click also lands on the dismiss binding
            self._skip_menu = SkipMenu(
                self, self.skip_btn.canvas,
                skip_options(self.config_data.get("interval_minutes", INTERVAL_MINUTES)),
                INK, p["card"],
                ui_font(s(14)), on_select=lambda n: self._close("skip", n),
                accent=p["accent"], item_height=s(DROPDOWN_ITEM_H))

        # F20⑤: "Skip ▾" is one CanvasButton — text and triangle drawn on the same canvas,
        # centered as a group, never a Label + a separate arrow widget glued by padding
        self.skip_btn = CanvasButton(
            inner, "Skip", p["card"], INK, ui_font(s(14)),
            command=open_skip_menu, accent=p["accent"],
            padx=s(16), height=s(BUTTON_HEIGHT), dropdown_arrow=True, arrow_size=s(5),
        )
        self.skip_btn.pack(side="left", padx=(s(16), 0))

        not_today = tk.Label(
            inner, text="Not today", fg=blend(INK, p["card"], 0.55), bg=p["card"],
            font=ui_font(s(10), "underline"), cursor="hand2",
        )
        not_today.pack(side="right")
        not_today.bind("<Button-1>", lambda e: self._close("no_remind_today"))
        not_today.bind("<Enter>", lambda e: not_today.configure(fg=INK))
        not_today.bind("<Leave>", lambda e: not_today.configure(fg=blend(INK, p["card"], 0.55)))

    # ---------- inline settings (F15-F20) ----------

    def _title_chrome_px(self, s):
        """Horizontal pixels the title row spends on everything that isn't title text:
        outer padx (24 each side), icon column + its gap, and the mascot canvas."""
        return 2 * s(24) + s(30) + s(12) + s(56)

    def _fit_title_size(self, text, s):
        """F20⑤a single-line auto-fit: measure with the actual display font, starting at
        32px and stepping down 2px at a time to the 22px floor. The window was already
        widened in __init__ if even the floor can't fit, so this always lands on a size
        that keeps the title to one line."""
        avail = self.width - self._title_chrome_px(s)
        size = s(TITLE_MAX_PX)
        floor = s(TITLE_MIN_PX)
        f = tkfont.Font(family=_FONT_CACHE["display"], size=size, weight="bold")
        while size - 2 >= floor and f.measure(text) > avail:
            size -= 2
            f.configure(size=size)
        return size

    @staticmethod
    def _wrapped_line_count(text, font_spec, avail):
        """Greedy word wrap with the actual font — how many lines Label wraplength will
        produce (same first-fit algorithm Tk uses for word wrapping)."""
        f = _tkfont_for(font_spec)
        lines, cur = 1, ""
        for word in text.split():
            trial = word if not cur else cur + " " + word
            if f.measure(trial) <= avail:
                cur = trial
            else:
                lines += 1
                cur = word
        return lines

    def _fit_quote_size(self, text, avail, s):
        """§2.3: quote starts at 24px; wrap to TWO lines before ever shrinking; only if two
        lines still overflow does the size step down (min 18). Never shrink just to force a
        single line — that's what made quotes look small."""
        size = s(QUOTE_MAX_PX)
        floor = s(QUOTE_MIN_PX)
        while size - 2 >= floor and \
                self._wrapped_line_count(text, display_font(size, "bold"), avail) > 2:
            size -= 2
        return size

    def _toggle_settings(self):
        # F15 zero-shift expansion + §7-8 no-flicker: _freeze() cancels the walk timer BEFORE any
        # resize, so no stale walk callback can re-place the window mid-expansion. The
        # panel is resident (built once, contents refreshed while hidden) and the order is
        # fixed to kill intermediate frames: expand = grow window -> update_idletasks ->
        # show panel; collapse = hide panel -> update_idletasks -> shrink window. update()
        # is never called — it force-renders exactly the in-between frame we're avoiding.
        self._freeze()
        if self._skip_menu is not None and self._skip_menu.winfo_exists():
            self._skip_menu._dismiss()
        if not self.settings_open:
            self._expand_settings()
        else:
            self._collapse_settings()

    def _expand_settings(self):
        self.settings_open = True
        self._pre_settings_y = self.pos_y
        self._compact_height = self.cur_height
        self._populate_settings_panel()   # fresh values from config, rebuilt while hidden
        self.update_idletasks()           # settle the unmapped panel's reqheight
        panel_h = self.settings_panel.winfo_reqheight() + 1  # +1 separator line
        target = self._compact_height + panel_h
        screen_h = self.winfo_screenheight()
        max_y = max(POPUP_MARGIN, screen_h - target - BOTTOM_RESERVE)
        y = min(self.pos_y, max_y)  # shift up only by the exact overflow, if any
        self.set_geometry(height=target, y=y)     # 1. grow first
        self.update_idletasks()                    # 2. settle geometry (never update())
        # 3. only now show the panel — packed before the action-row separator so the pack
        # order (and therefore the bottom-edge stacking) matches the original build order
        self.settings_panel.pack(side="bottom", fill="x", before=self._action_sep)
        self.settings_sep.pack(side="bottom", fill="x", before=self._action_sep)

    def _collapse_settings(self):
        self.settings_open = False
        self.settings_panel.pack_forget()          # 1. hide first
        self.settings_sep.pack_forget()
        self.update_idletasks()                    # 2. settle (never update())
        y = self._pre_settings_y if getattr(self, "_pre_settings_y", None) is not None else self.pos_y
        self.set_geometry(height=self._compact_height, y=y)  # 3. shrink last, restore y
        self._pre_settings_y = None

    def _populate_settings_panel(self):
        """(Re)build the resident panel's contents from the saved config — called only
        while the panel is hidden, so Cancel discards edits without any visible rebuild."""
        p = self.palette
        s = lambda n: max(1, round(n * self.scale))  # noqa: E731
        panel = self.settings_panel
        for child in panel.winfo_children():
            child.destroy()
        cfg = self.config_data
        body = tk.Frame(panel, bg=p["card"])
        # SYMMETRIC top/bottom padding — the whole block must sit visually centered in the
        # expanded area (Schedule-to-top distance == Save-to-bottom distance). Row rhythm
        # is fixed: 6 between rows, 6 above/below the divider, 4 inside the Days group.
        body.pack(fill="x", padx=s(24), pady=(s(10), s(10)))

        state = {
            "mode": cfg.get("mode", "scheduled"),
            "start": _hm_to_minutes(cfg.get("work_start", "09:30")),
            "end": _hm_to_minutes(cfg.get("work_end", "18:30")),
            "days": set(cfg.get("work_days", [])),
            "interval": int(cfg.get("interval_minutes", INTERVAL_MINUTES)),
            "speed": max(WALK_SPEED_MIN, min(WALK_SPEED_MAX,
                          int(cfg.get("walk_speed", POPUP_MOVE_SPEED)))),
            "login": bool(cfg.get("start_at_login", False)),
        }

        # section labels: lowercase utility style per the mockup's .s-label (10px, dimmed),
        # INLINE at the left of each row — a separate label line per group made the panel
        # taller than the popup once F22/F23 landed
        dim = blend(INK, p["card"], 0.6)
        # Label column with a FIXED PIXEL width (not tk's character units — those are
        # multiples of an average glyph width, so "schedule" and "days" produced different
        # real widths per platform font and every row's controls started at a different x).
        # Every row, including the bare day-chips row, leads with this same-width holder,
        # so all controls line up on one left edge.
        label_col_px = s(64)

        def row_label(parent, text):
            holder = tk.Frame(parent, bg=p["card"], width=label_col_px, height=s(18))
            holder.pack_propagate(False)
            tk.Label(holder, text=text, bg=p["card"], fg=dim, font=ui_font(s(10)),
                     anchor="w").pack(fill="both", expand=True)
            return holder

        pill_row = tk.Frame(body, bg=p["card"])
        pill_row.pack(fill="x", pady=(0, s(6)))
        row_label(pill_row, "Schedule").pack(side="left")
        pills = {}

        def pick_mode(pill):
            for key, other in pills.items():
                other.set(other is pill)
            state["mode"] = "scheduled" if pill is pills["scheduled"] else "always"
            sync_schedule_rows()

        for key, label in (("scheduled", "Active hours"), ("always", "Always")):
            pill = CanvasChip(pill_row, label, INK, p["card"], p["accent"],
                               ui_font(s(12)), pick_mode, accent=p["accent"],
                               padx=s(12), pady=s(4))
            pill.pack(side="left", padx=(0, s(6)))
            pills[key] = pill
        pills[state["mode"]].set(True)
        self.mode_chips = pills

        # Everything only meaningful in "Active hours" mode lives in this container so F17
        # can HIDE it wholesale in Always mode — the design system bans gray, so there is
        # no dimmed/disabled look: rows that don't apply simply aren't there, and the
        # settings area gets visibly shorter.
        sched_detail = tk.Frame(body, bg=p["card"])
        sched_detail.pack(fill="x")

        hours_row = tk.Frame(sched_detail, bg=p["card"])
        hours_row.pack(fill="x", pady=(0, s(6)))
        row_label(hours_row, "From").pack(side="left")
        start_stepper, start_state = make_stepper(
            hours_row, INK, p["card"], ui_font(s(12)), state["start"], 30,
            on_change=lambda v: state.__setitem__("start", v), accent=p["accent"])
        start_stepper.pack(side="left", padx=(0, s(10)))
        tk.Label(hours_row, text="to", bg=p["card"], fg=INK, font=ui_font(s(12))).pack(side="left")
        end_stepper, end_state = make_stepper(
            hours_row, INK, p["card"], ui_font(s(12)), state["end"], 30,
            on_change=lambda v: state.__setitem__("end", v), accent=p["accent"])
        end_stepper.pack(side="left", padx=(s(4), 0))
        self.start_stepper, self.end_stepper = start_stepper, end_stepper

        days_head = tk.Frame(sched_detail, bg=p["card"])
        days_head.pack(fill="x", pady=(0, s(4)))
        row_label(days_head, "Days").pack(side="left")
        days_wrap = tk.Frame(sched_detail, bg=p["card"])
        days_wrap.pack(fill="x", pady=(0, s(6)))
        row_label(days_wrap, "").pack(side="left")  # spacer: chips align with the column too
        days_row = tk.Frame(days_wrap, bg=p["card"])
        days_row.pack(side="left")
        day_pills = []

        def toggle_day(pill, idx):
            pill.set(not pill.on)
            if pill.on:
                state["days"].add(idx)
            else:
                state["days"].discard(idx)
            every_day_pill.set(len(state["days"]) == 7)

        for i, name in enumerate(WEEKDAY_LABELS):
            pill = CanvasChip(days_row, name, INK, p["card"], p["accent"],
                               ui_font(s(12)), lambda p_, i=i: toggle_day(p_, i),
                               accent=p["accent"], padx=s(4), pady=s(4))
            pill.set(i in state["days"])
            pill.pack(side="left", padx=(0, s(2)))
            day_pills.append(pill)
        self.day_chips = day_pills

        def toggle_every_day(pill):
            turn_on = not pill.on
            pill.set(turn_on)
            state["days"] = set(range(7)) if turn_on else set()
            for dp in day_pills:
                dp.set(turn_on)

        every_day_pill = CanvasChip(days_head, "Every day", INK, p["card"], p["accent"],
                                     ui_font(s(12)), toggle_every_day,
                                     accent=p["accent"], padx=s(8), pady=s(4))
        every_day_pill.set(len(state["days"]) == 7)
        every_day_pill.pack(side="left")
        self.everyday_chip = every_day_pill

        def sync_schedule_rows():
            # F17: hide, never gray out — and follow the §7-8 no-flicker ordering here too:
            # grow BEFORE showing rows, hide rows BEFORE shrinking. Top-left stays put.
            delta = sched_detail.winfo_reqheight()
            if state["mode"] == "scheduled":
                if not sched_detail.winfo_manager():
                    target = self.cur_height + delta
                    screen_h = self.winfo_screenheight()
                    max_y = max(POPUP_MARGIN, screen_h - target - BOTTOM_RESERVE)
                    self.set_geometry(height=target, y=min(self.pos_y, max_y))
                    self.update_idletasks()
                    sched_detail.pack(fill="x", after=pill_row)
            else:
                if sched_detail.winfo_manager():
                    sched_detail.pack_forget()
                    self.update_idletasks()
                    self.set_geometry(height=self.cur_height - delta)

        # F22 + F23 — two slim single-line rows (inline dim labels, same .s-label voice)
        # so the two new options barely lengthen the expanded panel
        every_row = tk.Frame(body, bg=p["card"])
        every_row.pack(fill="x", pady=(0, s(6)))
        row_label(every_row, "Every").pack(side="left")
        interval_chips = {}

        def pick_interval(chip, minutes):
            for c in interval_chips.values():
                c.set(c is chip)
            state["interval"] = minutes

        for m in INTERVAL_CHOICES:
            chip = CanvasChip(every_row, str(m), INK, p["card"], p["accent"], ui_font(s(12)),
                               lambda c, m=m: pick_interval(c, m), accent=p["accent"],
                               padx=s(8), pady=s(4))
            chip.set(state["interval"] == m)
            chip.pack(side="left", padx=(0, s(4)))
            interval_chips[m] = chip
        tk.Label(every_row, text="min", bg=p["card"], fg=dim,
                 font=ui_font(s(10))).pack(side="left", padx=(s(2), 0))
        self.interval_chips = interval_chips

        speed_row = tk.Frame(body, bg=p["card"])
        speed_row.pack(fill="x")  # divider's own 6px pady provides the gap below
        row_label(speed_row, "Speed").pack(side="left")
        speed_val = tk.Label(speed_row, text=str(state["speed"]), bg=p["card"], fg=INK,
                              font=ui_font(s(12)), width=2, anchor="e")
        slider, speed_state = make_slider(
            speed_row, INK, p["card"], p["accent"], WALK_SPEED_MIN, WALK_SPEED_MAX,
            state["speed"],
            on_change=lambda v: (state.__setitem__("speed", v),
                                 speed_val.configure(text=str(v))),
            width=s(130), height=s(22))
        slider.pack(side="left", padx=(0, s(4)))
        speed_val.pack(side="left")
        self.speed_slider = slider
        self.speed_slider_state = speed_state

        # divider gaps match the block's 10px bottom margin: speed -> line, line -> last
        # row, and last row -> panel bottom edge are all the same width
        tk.Frame(body, bg=INK, height=1).pack(fill="x", pady=s(10))

        # last row, mockup-style: checkbox left, Cancel/Save right, all on one line
        last_row = tk.Frame(body, bg=p["card"])
        last_row.pack(fill="x")
        checkbox_row, login_state = make_checkbox_row(
            last_row, "Start at login", INK, p["card"], p["accent"], ui_font(s(12)), state["login"],
            on_toggle=lambda v: state.__setitem__("login", v))
        checkbox_row.pack(side="left")
        # mockup order: [Cancel] [Save] with the primary Save at the far right —
        # side="right" packing places the FIRST-packed widget rightmost
        self.save_btn = CanvasButton(last_row, "Save", p["accent"], INK, ui_font(s(14), "bold"),
                                      command=lambda: self._save_settings(state),
                                      accent=p["accent"], padx=s(14), height=s(BUTTON_HEIGHT))
        self.save_btn.pack(side="right")
        self.cancel_btn = CanvasButton(last_row, "Cancel", p["card"], INK, ui_font(s(14)),
                                        command=self._toggle_settings,
                                        accent=p["accent"], padx=s(14), height=s(BUTTON_HEIGHT))
        self.cancel_btn.pack(side="right", padx=(0, s(6)))

        # inline validation message (F20②: no native messagebox dialogs — this panel is
        # hand-drawn end to end, so errors surface the same way, not via an OS alert).
        # NOT packed here: an always-present (even when empty) label added phantom height
        # below the Save row and broke the panel's symmetric top/bottom margins — it only
        # appears (growing the window) when a save actually fails, via _show_settings_error
        self._settings_error = tk.Label(body, text="", bg=p["card"], fg=p["sticker"],
                                         font=ui_font(s(10), "bold"),
                                         wraplength=self.width - s(40), justify="left")

        if state["mode"] != "scheduled":
            sched_detail.pack_forget()

    def _show_settings_error(self, text):
        """Reveal the inline validation label, growing the window to make room — same
        §7-8 ordering as every other expansion (grow → update_idletasks → show)."""
        s = lambda n: max(1, round(n * self.scale))  # noqa: E731
        self._settings_error.configure(text=text)
        if not self._settings_error.winfo_manager():
            self.update_idletasks()  # settle the unmapped label's reqheight for the new text
            delta = self._settings_error.winfo_reqheight() + s(6)
            target = self.cur_height + delta
            screen_h = self.winfo_screenheight()
            max_y = max(POPUP_MARGIN, screen_h - target - BOTTOM_RESERVE)
            self.set_geometry(height=target, y=min(self.pos_y, max_y))
            self.update_idletasks()
            self._settings_error.pack(anchor="w", pady=(s(6), 0))

    def _save_settings(self, state):
        if state["mode"] == "scheduled":
            if state["end"] <= state["start"]:
                self._show_settings_error("End time must be after start time.")
                return
            if not state["days"]:
                self._show_settings_error("Pick at least one day.")
                return

        new_config = {
            "mode": state["mode"],
            "work_start": _minutes_to_hm(state["start"]),
            "work_end": _minutes_to_hm(state["end"]),
            "work_days": sorted(state["days"]),
            "start_at_login": state["login"],
            "interval_minutes": state["interval"],
            "walk_speed": state["speed"],
        }
        if state["login"] != is_autostart_enabled():
            set_autostart_enabled(state["login"])

        self.config_data = new_config
        if self.on_settings_saved:
            self.on_settings_saved(new_config)
        self._collapse_settings()

    # ---------- walk animation ----------

    def _move_step(self):
        if self.captured:
            return

        # Belt-and-suspenders: an unexpected TclError anywhere in here (older/system Tk
        # builds in particular are prone to flaky behavior on some of these calls) must never
        # silently kill the recursive self.after() chain — that would look exactly like "it
        # ran for a while then just stopped" with no error visible anywhere. Whatever happens
        # above, always try to reschedule the next frame in finally.
        try:
            try:
                pointer = (self.winfo_pointerx(), self.winfo_pointery())
            except tk.TclError:
                pointer = self._last_pointer_pos
            # skip the very first observation: comparing against the None baseline would
            # always look like "just moved", handing out a free grace window right at spawn.
            # Require a real minimum distance, not just "any change", so trackpad/mouse
            # sensor jitter at rest can't keep re-arming the recent-motion window forever.
            if self._last_pointer_pos is not None and pointer != (-1, -1):
                moved_px = math.hypot(pointer[0] - self._last_pointer_pos[0],
                                       pointer[1] - self._last_pointer_pos[1])
                if moved_px >= CAPTURE_MIN_MOTION_PX:
                    self._pointer_last_moved_at = time.monotonic()
            self._last_pointer_pos = pointer

            self.pos_x += self.dx
            self.pos_y += self.dy

            if self.pos_x <= self.min_x:
                self.pos_x = self.min_x
                self.dx = abs(self.dx)
            elif self.pos_x >= self.max_x:
                self.pos_x = self.max_x
                self.dx = -abs(self.dx)

            if self.pos_y <= self.min_y:
                self.pos_y = self.min_y
                self.dy = abs(self.dy)
            elif self.pos_y >= self.max_y:
                self.pos_y = self.max_y
                self.dy = -abs(self.dy)

            if random.random() < DIRECTION_CHANGE_PROB:
                heading = random.uniform(0, 2 * math.pi)
                self.dx = self.speed * math.cos(heading)
                self.dy = self.speed * math.sin(heading)

            self.set_geometry()  # F20⑧: pos_x/pos_y already updated above
        except tk.TclError:
            pass
        finally:
            if not self.captured:
                self._move_job = self.after(POPUP_FRAME_MS, self._move_step)

    # ---------- capture / drag ----------

    def _on_capture(self, event):
        if self.captured:
            return
        # The window itself is moving; an <Enter> can fire just because the popup wandered
        # under a stationary cursor, not because the user actually chased it. Only honor it
        # as a real catch if the mouse has genuinely moved recently (see CAPTURE_REQUIRES_
        # RECENT_MOTION_S) — otherwise ignore it and keep walking.
        since_motion = time.monotonic() - self._pointer_last_moved_at
        if since_motion > CAPTURE_REQUIRES_RECENT_MOTION_S:
            return
        self._freeze()
        # one-shot accent flash, no looping blink (design skill §6) — only for a genuine
        # catch. Recolor EVERY bg-role widget together with the Toplevel: flashing only the
        # window while its bg-colored child frames keep the old color leaves a mismatched
        # band sitting behind the title — exactly the "underlay block" F20⑤a forbids.
        p = self.palette
        self._paint_bg(p["accent"])
        self.after(CAPTURE_FLASH_MS, lambda: self._paint_bg(p["bg"]))

    def _paint_bg(self, color):
        try:
            self.configure(bg=color)
            for w in getattr(self, "_bg_widgets", []):
                w.configure(bg=color)
        except tk.TclError:
            pass  # widgets may be mid-rebuild (settings toggle) when the flash-back fires

    def _freeze(self):
        """Stop the walk. Used both by a genuine hover-catch and by opening settings (F15) —
        the flash/spiral swap only fires the first time, from whichever path gets there first."""
        if self.captured:
            return
        self.captured = True
        if self._move_job:
            self.after_cancel(self._move_job)
            self._move_job = None
        if hasattr(self, "title_label"):
            self.title_label.configure(text="Time to walk!")
        if hasattr(self, "mascot"):
            self._draw_mascot()

    def _draw_mascot(self):
        """Walking-state wave or captured-state spiral, always centered on the mascot
        canvas's actual size (F20⑤) — used both at initial build and by _freeze(), so the
        two states can't drift into using different, independently-tuned coordinates."""
        self.mascot.delete("all")
        mw, mh = int(self.mascot["width"]), int(self.mascot["height"])
        if self.captured:
            draw_spiral(self.mascot, mw / 2, mh / 2, min(mw, mh) / 2 - 2, INK)
        else:
            margin = mh * 0.11
            draw_wave(self.mascot, margin, margin, mw - 2 * margin, mh - 2 * margin, INK)

    def _on_drag_start(self, event):
        if not self.captured:
            return
        if event.widget not in getattr(self, "_drag_surfaces", ()):
            return  # press landed on a control (slider, chip, button...) — not a drag
        self._drag_start = (event.x_root, event.y_root, self.winfo_x(), self.winfo_y())

    def _on_drag_motion(self, event):
        if not self.captured or not self._drag_start:
            return
        if event.widget not in getattr(self, "_drag_surfaces", ()):
            return
        start_mx, start_my, start_wx, start_wy = self._drag_start
        new_x = start_wx + (event.x_root - start_mx)
        new_y = start_wy + (event.y_root - start_my)
        # F20⑧: going through set_geometry keeps pos_x/pos_y — the single source of truth —
        # in sync with where the user actually dragged the window. The old direct
        # geometry() call left them stale, so the next rebuild (e.g. opening settings)
        # snapped the popup back to its pre-drag position: THE "jumps when I click
        # settings" bug.
        self.set_geometry(x=new_x, y=new_y)

    # ---------- action callbacks ----------

    def _close(self, action="ack", value=None):
        if self._move_job:
            self.after_cancel(self._move_job)
        self.destroy()
        if self.on_closed:
            self.on_closed(action, value)


def _hm_to_minutes(hm):
    h, m = hm.split(":")
    return int(h) * 60 + int(m)


def _minutes_to_hm(total):
    h, m = divmod(total, 60)
    return f"{h:02d}:{m:02d}"


# ============================================================
# One-time HuFont restart notice
# ============================================================

class RestartNotice(tk.Toplevel):
    """Shown once, only the run HuFont is first copied into the system font directory
    (design skill F20④): the OS font list Tk already queried at startup won't include it
    until the app restarts. A native messagebox would violate F20②, so this is the same
    hand-drawn Frame/Label/Canvas construction as everything else."""

    def __init__(self, master):
        super().__init__(master)
        strip_native_chrome(self)  # F20①: same treatment as every other Toplevel
        bg = "#FFFDF5"
        self.configure(bg=INK, highlightthickness=0)
        card = tk.Frame(self, bg=bg, highlightthickness=2, highlightbackground=INK)
        card.pack(padx=2, pady=2)
        tk.Label(
            card, text="HuFont installed.\nRestart Walk Walk to see it.",
            bg=bg, fg=INK, font=ui_font(12, "bold"), justify="left",
        ).pack(padx=18, pady=(16, 10))
        btn_row = tk.Frame(card, bg=bg)
        btn_row.pack(fill="x", padx=18, pady=(0, 14))
        self.got_it_btn = CanvasButton(btn_row, "Got it", bg, INK, ui_font(10, "bold"),
                                        command=self._dismiss, accent="#FFE014", padx=12,
                                        height=30)
        self.got_it_btn.pack(side="right")

        self.update_idletasks()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        w, h = self.winfo_reqwidth(), self.winfo_reqheight()
        self.geometry(f"+{(sw - w) // 2}+{(sh - h) // 2}")

    def _dismiss(self):
        try:
            self.destroy()
        except tk.TclError:
            pass


# ============================================================
# Dev test panel (TEST_MODE only)
# ============================================================

class DevTestPanel(tk.Toplevel):
    """Top-left dock: click it, press S to fire a reminder popup instantly instead of waiting."""

    def __init__(self, master, on_trigger):
        super().__init__(master)
        self.on_trigger = on_trigger

        # Deliberately NOT overrideredirect: this dev-only panel is never compared against
        # the mockup (F20's chrome-stripping is about user-facing UI), and override-redirect
        # windows are unmanaged by the OS window manager — on macOS that can mean the panel
        # never actually receives real keyboard focus, so the S-key trigger silently stops
        # working. A normal decorated window can always be focused and typed into.
        self.title("TEST MODE")
        self.attributes("-topmost", True)
        self.resizable(False, False)
        self.configure(bg=INK)
        self.geometry("240x60+20+20")

        label = tk.Label(
            self, text="TEST MODE\nclick here, press S to fire a popup",
            bg=INK, fg="#FFFFFF", font=ui_font(10), justify="center",
        )
        label.pack(expand=True, fill="both", padx=8, pady=8)

        for widget in (self, label):
            widget.bind("<KeyPress-s>", lambda e: self.on_trigger())
            widget.bind("<KeyPress-S>", lambda e: self.on_trigger())
            widget.bind("<Button-1>", lambda e: self.focus_force())

        self.focus_force()


# ============================================================
# Main scheduler
# ============================================================

class ReminderApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.withdraw()
        try:
            # window/taskbar icon (mainly Windows/Linux; the macOS Dock icon comes from
            # the .app bundle). iconphoto(True, …) makes it the default for every Toplevel.
            self._app_icon = tk.PhotoImage(file=resource_path("assets", "icon", "icon-256.png"))
            self.root.iconphoto(True, self._app_icon)
        except Exception:
            pass  # icon is cosmetic — never block startup over it
        just_installed_hufont = install_hufont()  # F20④, best-effort, never blocks startup
        init_fonts()
        if just_installed_hufont and HUFONT_USABLE:
            RestartNotice(self.root)

        self.config = load_config()
        self.skip_remaining = 0
        self.no_remind_date = None   # date
        self.popup = None
        self.walk_count = 0
        self.walk_count_date = None
        self.palette = None
        self.palette_date = None
        self.palette_override = parse_palette_override()  # F21: --palette=cycle / A..G / env
        if self.palette_override is None and is_test_mode():
            # demo/test runs are for eyeballing the design: rotate through all seven
            # palettes one popup at a time instead of locking the daily pick — each press
            # of S shows the next color. An explicit --palette still wins.
            self.palette_override = "cycle"
        self._cycle_index = 0

        if is_test_mode():
            DevTestPanel(self.root, on_trigger=self._dev_trigger_popup)
            # --demo quick test: the first reminder fires right away — no waiting, no
            # file editing, no S-key needed (the panel is still there for repeat fires)
            self.root.after(300, self._dev_trigger_popup)

        self._schedule_next_tick()

    def _dev_trigger_popup(self):
        """Test-mode only: ignore skip/meeting/not-today state, fire immediately."""
        if self.popup is None:
            self.show_popup()

    def _schedule_next_tick(self):
        interval = int(self.config.get("interval_minutes", INTERVAL_MINUTES))
        self._tick_job = self.root.after(interval * 60 * 1000, self._tick)

    def _in_schedule_window(self, now):
        if self.config.get("mode") == "always":
            return True
        if now.weekday() not in self.config.get("work_days", []):
            return False
        start_h, start_m = map(int, self.config.get("work_start", "09:30").split(":"))
        end_h, end_m = map(int, self.config.get("work_end", "18:30").split(":"))
        start = now.replace(hour=start_h, minute=start_m, second=0, microsecond=0)
        end = now.replace(hour=end_h, minute=end_m, second=0, microsecond=0)
        return start <= now <= end

    def _tick(self):
        now = datetime.now()

        if self.no_remind_date == now.date():
            pass  # Not today — highest priority (F14)
        elif is_in_meeting():
            pass  # auto meeting detection (F12) — silent skip, doesn't consume Skip N
        elif self.skip_remaining > 0:
            self.skip_remaining -= 1  # consumed at trigger time (F11)
        elif self._in_schedule_window(now) and self.popup is None:
            self.show_popup()

        self._schedule_next_tick()

    def _next_walk_no(self):
        today = date.today()
        if self.walk_count_date != today:
            self.walk_count_date = today
            self.walk_count = 0
        self.walk_count += 1
        return self.walk_count

    def _current_palette(self):
        """F5a: one palette per day, picked at the first reminder of the day and reused by
        every popup/settings panel that day; changes over at midnight. F21 debug overrides:
        'cycle' rotates through all seven palettes one per popup; a fixed name locks one."""
        if self.palette_override == "cycle":
            palette = PALETTE_LIST[self._cycle_index % len(PALETTE_LIST)]
            self._cycle_index += 1
            return palette
        if self.palette_override:
            return PALETTES[self.palette_override]
        today = date.today()
        if self.palette_date != today:
            self.palette_date = today
            self.palette = random.choice(PALETTE_LIST)
        return self.palette

    def show_popup(self):
        self.popup = ReminderPopup(
            self.root, on_closed=self._on_popup_closed,
            config=self.config, on_settings_saved=self._on_settings_saved,
            walk_no=self._next_walk_no(), palette=self._current_palette(),
        )

    def _on_popup_closed(self, action, value):
        self.popup = None
        if action == "skip":
            self.skip_remaining = value
        elif action == "no_remind_today":
            self.no_remind_date = datetime.now().date()
        # action == "ack": nothing else to do

    def _on_settings_saved(self, new_config):
        old_interval = self.config.get("interval_minutes", INTERVAL_MINUTES)
        self.config = new_config
        save_config(self.config)
        # F22 takes effect immediately (same apply-on-save rule as F17): if the interval changed,
        # drop the pending tick — which was armed with the old delay — and re-arm with the new
        if new_config.get("interval_minutes", INTERVAL_MINUTES) != old_interval:
            if getattr(self, "_tick_job", None) is not None:
                try:
                    self.root.after_cancel(self._tick_job)
                except tk.TclError:
                    pass
            self._schedule_next_tick()

    def run(self):
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            sys.exit(0)


if __name__ == "__main__":
    if "--version" in sys.argv[1:]:
        print(f"Walk Walk {VERSION}")
        sys.exit(0)
    ReminderApp().run()
