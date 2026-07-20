<p align="center">
  <img src="assets/icon/icon.png" width="128" alt="Walk Walk icon">
</p>

<h1 align="center">Walk Walk</h1>

<p align="center"><em>A break reminder that won't let you ignore it.</em></p>

---

Walk Walk is a tiny desktop app that reminds you to stand up and move. Instead of a polite notification you'll swat away without reading, it throws a poster-style popup onto your screen that **physically wanders around until you catch it with your cursor** — a two-second game that breaks you out of the scroll before you even decide to.

- **Zero dependencies** — a single Python file using only the standard library (`tkinter`). No accounts, no installers, no frameworks.
- **Fully offline** — nothing is collected, nothing is sent. Ever.
- **macOS & Windows**, packaged double-clickable builds or straight from source.
- Current version: **1.0.0** (`python3 walkwalk.py --version`)

## How it works

Every 45 minutes (configurable: 15/30/45/60) a small poster pops up somewhere random on your screen and starts roaming — constant speed, bouncing off the edges. Move your mouse onto it and it stops: the title flips from *"Catch me first!"* to *"Time to walk!"*, and you get one of **300 original one-liners** (motivation, terrible dad jokes, fun facts, gentle stretch prompts…) hand-set in HuFont, our own handwriting typeface.

Then you choose:

- **I'm up!** — done, see you next round
- **Skip ▾** — mute the next 1–5 reminders, shown as real durations ("Next 2 · 1.5 h")
- **Not today** — tucked in the corner, silences the rest of the day

Some care has gone into not being annoying:

- **In a meeting? It stays quiet.** When a reminder comes due while your camera or mic is busy (Windows: system device state; macOS: running meeting apps), it skips that round silently — no popup, no Skip consumed.
- **Every day gets a look of its own** — one of 7 high-saturation paper-and-ink palettes is drawn each morning; positions and quotes are random every time, so your brain never files the reminder under "ignore".
- **Everything is hand-drawn.** No system buttons, no native chrome, no emoji — every control is drawn from scratch so it looks like a printed flyer, identically on every OS.

## Settings

Click the ☰ icon on the popup's info bar — the panel expands inside the popup itself:

- **Schedule**: Active hours (e.g. 9:30–18:30, pick your weekdays) or Always
- **Every**: reminder interval — 15 / 30 / 45 / 60 minutes
- **Speed**: how fast the popup roams, from a stroll to genuinely hard to catch
- **Start at login**: run automatically at boot (pairs well with Always)

Config lives in `~/.walkwalk_config.json`. Changes apply immediately.

## Install & run

### Option 1 — build a double-clickable app (no Python needed afterwards)

Packaging must run on the target OS (PyInstaller can't cross-build):

- **macOS**: `cd` into the project folder and run `bash packaging/build_mac.sh` → produces `dist/Walk Walk.app`; drag it into Applications.
- **Windows**: double-click `packaging\build_windows.bat` → produces `dist\Walk Walk.exe`; copy it wherever you like.

> **First launch of an unsigned app:** on macOS, right-click the app → Open → Open (only needed once). On Windows, if SmartScreen appears, click "More info" → "Run anyway". The builds are unsigned because code-signing certificates are paid; the source is right here to audit.

**Autostart** (optional): tick **Start at login** in Settings — that's it. (The `packaging/install_autostart_*` scripts do the same thing for packaged builds.)

### Option 2 — run from source

```bash
python3 walkwalk.py
```

Requires Python 3 with `tkinter` (bundled on macOS and in the official Windows installer; on Linux: `sudo apt install python3-tk`). The app has no main window — it schedules quietly in the background and pops up when it's time. Quit with `Ctrl+C` in the terminal (packaged builds: end the "Walk Walk" process from Activity Monitor / Task Manager).

### Try it right now

```bash
python3 walkwalk.py --demo
```

`--demo` fires a popup immediately (no 45-minute wait, all mute rules bypassed) and shows a small TEST MODE panel — click it and press **S** to fire again, cycling through all seven palettes. Other flags: `--palette=cycle|A..G|<name>` to preview palettes, `--version`.

## The font

Quotes and titles are set in **HuFont**, an original handwriting typeface made for this app (bundled, in `fonts/ttf/`). On first run Walk Walk installs it into your user font directory and shows a one-time "restart to see it" notice — restart the app once and the handwriting appears. If installation fails the app silently falls back to system fonts; you can also install the three files in `fonts/ttf/` manually by double-clicking them.

## Make it yours

- **Quotes**: edit `quotes.json` — 300 lines across six categories, each entry just needs a `"text"`. Keep lines short (they render big, max two lines), and avoid hyphens/em-dashes — HuFont's charset doesn't include them. If the file breaks, the app falls back to built-ins.
- **App icon**: replace `assets/icon/icon.png` (1024×1024) and run `python3 packaging/make_icons.py` (needs `pillow`) to regenerate the `.icns` / `.ico` used by the build scripts.

## Privacy

Walk Walk runs **entirely offline**: no network access, no telemetry, no data collection of any kind. Configuration stays in a local JSON file. Meeting detection reads only the system's "camera/mic in use" state (Windows) or the process list (macOS) at the moment a reminder fires, and never records anything.

## Known limitations

- Running from source keeps a terminal process alive; packaged builds don't.
- Multi-monitor setups: popups appear on the primary display only.
- Schedules can't cross midnight (night owls: use Always mode).
- macOS meeting detection is heuristic (well-known meeting apps by process name) and can miss uncommon ones.
- On Linux, the Pango text renderer has a known quirk with a few standalone HuFont glyphs; macOS and Windows are unaffected.

## For developers

The full product spec is in [`docs/PRD.md`](docs/PRD.md); the visual specification (palettes, type table, layout rules, and the anti-native implementation checklist) lives in [`.claude/skills/walkwalk-design/SKILL.md`](.claude/skills/walkwalk-design/SKILL.md). A static HTML mockup used for pixel comparison is in [`mockup/`](mockup/).
