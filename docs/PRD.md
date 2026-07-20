# Walk Walk · Product Requirements Document (PRD)

- Version: 1.0.0 (first public release)
- Date: 2026-07-20
- Status: implemented in `walkwalk.py`
- Visual specification: see the `walkwalk-design` design skill (`.claude/skills/walkwalk-design/SKILL.md`); this document does not repeat visual details.

---

## 1. Background

People who work long hours at a desk tend not to leave their workstation for stretches at a time, leading to neck and shoulder strain, eye fatigue, and declining focus. Existing break reminders fall into two camps, each with a fatal flaw: system-notification reminders appear in a fixed corner of the screen and are quickly habituated away by the brain, while forced-lockscreen tools interrupt so aggressively that users uninstall them out of resentment.

The core hypothesis of this product: **a reminder must be conspicuous without being hostile.** A popup that appears at a random position, in a randomly chosen color palette, and physically wanders around the screen defeats visual habituation — the reminder actually gets seen. At the same time, soft controls (Skip, automatic meeting silence, Not today) respect flow state and meetings, so the tool never fights its user.

## 2. Target users

People who spend six or more hours a day in front of a computer (designers, engineers, writers). They agree they should stand up more, but lose track of time the moment they enter a work groove, and need an external trigger.

They are sensitive to interruption and dislike forced lockscreens; they respond to warmth and playfulness (the English encouragement quotes exist for this); and they will not tolerate installation or configuration overhead for a small utility.

## 3. Goals and success metrics

Product goal: during working hours, get the user to genuinely stand up once every 45–60 minutes on average.

| Metric | Definition | Target |
|--------|-----------|--------|
| Response rate | Popups answered with "I'm up!" / total popups | ≥ 60% |
| Skip rate | Reminders skipped via the dropdown / total | ≤ 30% |
| 7-day retention | Users still running the app on day 7 | ≥ 50% (applies to a future multi-user version) |

The current release is a fully local, offline tool with no analytics; these metrics are a measurement framework for future versions.

## 4. Functional requirements

### 4.1 Core reminder logic

| ID | Requirement | Notes | Priority |
|----|-------------|-------|----------|
| F1 | Active-hours window | By default reminders fire only on weekdays between 9:30–18:30; silent outside the window. Hours and weekdays are configurable in Settings | P0 |
| F2 | Fixed interval | One reminder every 45 minutes by default (interval selectable, see F22); the timer starts when the app launches | P0 |
| F3 | Configurable schedule | Hours, weekdays, mode, reminder interval (F22), and walk speed (F23) are all editable in the Settings panel (F15); changes apply immediately | P1 |
| F3a | Always mode | Ignores hours and weekdays — as long as the app is running, reminders fire on the interval. Combined with Start at login (F19) this gives "timer starts at boot" | P0 |

### 4.2 Popup behavior

| ID | Requirement | Notes | Priority |
|----|-------------|-------|----------|
| F4 | Small window | Roughly 1/16 of the screen area (width and height each 1/4 of the screen), floor **360×240**; if the title cannot fit on one line even at its minimum size, the window widens — the title never wraps | P0 |
| F5 | Random spawn position | Every popup appears at a random position (8px margin on all sides, so the walk range is effectively the whole screen) to defeat visual habituation | P0 |
| F5a | Daily palette | On the first reminder of each day one of **7** high-saturation palettes is drawn at random (definitions in design skill §1.1); every popup and the settings area use it for the rest of the day; it changes at midnight. Position and quote are still randomized per popup | P0 |
| F6 | Always on top | The popup stays above all windows until the user deals with it | P0 |
| F7 | Snake-style walk | After appearing, the window keeps moving: constant speed, random initial heading, bounces off screen edges (60px reserved at the bottom for the Dock/taskbar), with a small per-frame chance of picking a new heading. Speed, frame rate, and turn probability are constants; speed is user-configurable (F23) | P0 |
| F7a | Catch by hover | The moment the pointer enters the window, it stops for good (never resumes within that popup). The title switches from "Catch me first!" to "Time to walk!", and the wavy-line snake mascot coils into a spiral (geometric doodle, no emoji). Only genuine pointer movement counts — the popup passing under a stationary cursor is ignored | P0 |
| F7b | Draggable once caught | After stopping, the user can drag the window by any blank area to reposition it; dragging is inert while it is still walking | P1 |
| F8 | English quote card | Each popup shows one short English line drawn at random from the local `quotes.json` library (**300 original messages** in 6 categories: motivational, funny one-liners, wholesome, dad jokes, fun facts, break prompts), set in the HuFont handwriting face. The quote lays out at 24px, wraps to two lines before ever shrinking (18px minimum), and the **quote card is a fixed two-line-height box** that never stretches with the quote. The file is user-editable; if missing or broken the app falls back to 10 built-in lines. Note: HuFont's charset has no hyphen or em-dash — avoid them in custom quotes | P0 |
| F8a | Info bar | Left: wordmark "walk walk"; center: **walk no.X** (the day's Xth reminder, resets at midnight); right: settings entry (hamburger icon). The info bar shows real data only | P0 |

### 4.3 User actions

| ID | Requirement | Notes | Priority |
|----|-------------|-------|----------|
| F9 | "I'm up!" primary button | Closes the popup; the next reminder proceeds as scheduled | P0 |
| F10 | "Skip ▾" dropdown | Menu items read "Next 1 · 45 min" through "Next 5 · 3 h 45 m" (duration = N × the **currently configured interval**, so the user understands exactly how long they are muting; a bare "Skip 1" is forbidden). Selecting one closes the popup; the next N reminders are silently skipped, then service resumes | P0 |
| F11 | Skips don't carry over | Skip counts are consumed as reminders come due; they reset when the app restarts | P2 |
| F12 | Automatic meeting detection | When a reminder comes due, if the camera or microphone is in use by any app, that reminder is silently skipped (no popup, no Skip consumed, timer proceeds to the next round). Windows: registry `CapabilityAccessManager\ConsentStore` webcam/microphone `LastUsedTimeStop == 0` (standard library only, reliable). macOS: no zero-dependency public API, so a heuristic checks for common meeting apps (Zoom, Teams, Meet…) by process name. Detection failure counts as "not in a meeting" — better to over-remind than under-remind. The check runs synchronously before the popup with a 200ms budget | P0 (Win) / P1 (mac heuristic) |
| F13 | "Not today" | Fixed at the popup's **bottom-right**, deliberately de-emphasized (55% ink, underline, one size down) to prevent accidental clicks. Suppresses all remaining reminders for the day; recovers automatically the next day, no restart needed | P0 |
| F14 | Mute precedence | Evaluation order: Not today > meeting detection > Skip N; a popup appears only when none of the three applies and the schedule window is active | P1 |

### 4.4 Settings

| ID | Requirement | Notes | Priority |
|----|-------------|-------|----------|
| F15 | Inline settings panel | Hamburger icon at the info bar's right (Canvas-drawn: three equal, equidistant, round-capped bars). Clicking it freezes the walk and expands a compact settings area **downward inside the same window** below the action row (height increase ≤ the popup body); clicking again or Cancel collapses it. **Zero-shift expansion**: the window's top-left corner must not move on expand/collapse — it only grows downward; only if the bottom would run off screen does the whole window move up by exactly the overflow, restored on collapse. **No flicker**: the panel is built once and kept resident, expand/collapse only shows/hides it (never destroy + rebuild), with a fixed order (expand = grow window first, then show; collapse = hide first, then shrink) and no `update()` calls. The panel uses the current day's palette | P0 |
| F16 | Hours and weekdays | In Active-hours mode: start/end time (hand-drawn −/+ steppers) and weekday multi-select chips mon–sun plus an "Every day" select-all chip. Validation: end must be after start; at least one day selected. Errors surface as inline hand-drawn text, never a native dialog | P0 |
| F17 | Mode switch | "Active hours" vs "Always", mutually exclusive pills. In Always mode the from/to and days rows are **hidden entirely** (never grayed out — the design system bans gray, and hiding makes the panel shorter); restored when switching back. Applies on save, immediately | P0 |
| F18 | Config persistence | Settings are stored in `~/.walkwalk_config.json`; a missing or corrupt file falls back to defaults — the app never crashes over configuration | P0 |
| F19 | Start at login | Checkbox, off by default. macOS: writes `~/Library/LaunchAgents/com.walkwalk.plist`; Windows: a Startup-folder shortcut / `HKCU\...\Run` entry. Unchecking removes it. Works without packaging (points at `walkwalk.py` itself). Combined with Always mode: timer starts at boot | P0 |
| F20 | Anti-native red lines | ① **Every Toplevel** (popup and notice windows) drops system chrome: `overrideredirect(True)`, plus on macOS `::tk::unsupported::MacWindowStyle style <win> plain noActivates` to remove the forced corner mask and shadow. ② No native/ttk widgets of any kind (Spinbox/Checkbutton/Radiobutton/OptionMenu/Menu, including `messagebox` — validation errors and notices use hand-drawn surfaces): pills, checkboxes, steppers, sliders are all Frame/Label/Canvas. **The Skip dropdown must not be a separate window** (modern macOS force-rounds every borderless Toplevel at the window-server level; no Tk call can prevent it) — it is an **in-window Canvas overlay**, `place`-positioned and raised, opening **upward** (menu bottom = trigger top − 4px), 28px rows, dismissed by outside click or Esc. ③ Icons are drawn on Canvas, never Unicode glyphs; square canvas, computed coordinates, geometric center = canvas center. ④ HuFont auto-installs on first run — **TTF only** (`fonts/ttf/*.ttf`; the OTFs are design sources and must never be installed): macOS copies into `~/Library/Fonts/`, Windows uses ctypes `AddFontResourceExW` plus the user font directory. An install during the current process requires an app restart to take effect, and the app must say so (hand-drawn notice). On failure, silently fall back to system sans. ⑤ A button is **one Canvas** — rectangle, text, and any triangle on the same canvas, coordinates from `font.measure`/`metrics`; vertical centering uses the **cap-height optical formula** `cy = h/2 + (CAP_EM*S − ascent + descent)/2` (HuFont CAP_EM = 0.700). Never Frame+Label+padding; never mix HuFont and sans in one Label. ⑤a The title stays on one line: HuFont Bold from 32px stepping down to 22px; it sits directly on bg with no underlay block; head padding 24/16. ⑥ Hover/pressed fills come from the fixed complementary-color table in design skill §5 — never computed. ⑦ **Zero borderless controls**: every clickable element has a full 1.5px ink outline in every state (card fill unselected / accent fill selected); the single exception is "Not today". ⑧ **Single geometry exit**: all size/position changes go through one `set_geometry(w,h,x,y)` helper that always emits the full `WxH+X+Y` string (a size-only `geometry()` lets the window manager re-place the window) and records x/y as the single source of truth; the walk timer is cancelled before any resize; walking, expansion, and dragging all use this exit. ⑨ On completion, every state (popup / settings expanded / dropdown open / hover / pressed) is screenshot-compared against `mockup/walkwalk-mockup.html`; any native-looking chrome, widget, font, alignment, or missing border fails the build | P0 |
| F21 | Debug modes | ① Palettes: `--palette=cycle` (rotate A→G, one per popup) / `--palette=A..G` or a palette name (lock one) / env `WALKWALK_PALETTE`; default is F5a's daily random. ② Quick test: `--demo` (alias `--test`, env `WALKWALK_TEST=1`) **fires a reminder immediately at launch** and shows a TEST MODE panel (click it, press S to fire again); in demo mode palettes rotate by default so every press shows the next color. ③ `--version` prints the version and exits | P1 |
| F22 | Reminder interval | "Every 15/30/45/60 min" single-select chip row (15-minute granularity). Saving applies immediately: the pending timer is cancelled and re-armed with the new interval; Skip menu durations (F10) follow the current interval. Stored as `interval_minutes`, default 45 | P0 |
| F23 | Walk speed | "Speed" row with a **hand-drawn slider** (F20② bans native `tk.Scale`: 2px ink track + accent square handle with 1.5px ink outline, complementary hover/pressed, click or drag to set). Range 2–30 px/frame (the top end ≈ 900px/s is deliberately absurd — catching the popup becomes a game), default 8. Takes effect from the next popup. Stored as `walk_speed` | P1 |

### 4.5 Language and copy

The UI is **English only**. Fixed copy: walking title "Catch me first!" / caught "Time to walk!" / primary button "I'm up!" / dropdown trigger "Skip ▾" with items "Next 1 · 45 min" … "Next 5 · 3 h 45 m" / bottom-right "Not today" / settings labels "Schedule / Active hours / Always / From / Days / Every day / Every / Speed / Start at login". Voice: short, imperative, playful; buttons state their outcome, never "OK/Submit". No emoji anywhere; graphics are geometric shapes and single-line doodles only (design skill §3).

### 4.6 Explicit non-goals (v1.x)

No forced lockscreen or un-dismissable countdowns; no sitting detection via camera or sensors (note: F12 reads only the system's "device in use" state, never any image or audio); no statistics dashboard; no cloud sync. The tool stays lightweight and non-adversarial.

## 5. Interaction flow

The popup appears at a random position in the day's palette and starts walking on top of everything → the user chases it with the pointer; hovering catches it and it stops for good (title switches, snake coils — the catch feedback) → once stopped it can be dragged → action row: "I'm up!" + "Skip ▾", with "Not today" tucked bottom-right → any action closes the popup → the timer continues; after the configured interval the next round is evaluated (popup only if within the schedule window and none of Not today / meeting detection / Skip applies).

Design intent: the tiny act of chasing is itself an attention switch and a hand movement, much harder to reflex-dismiss than a static popup; hover-to-catch (rather than precise clicking) keeps the cost of catching low; meeting silence moves from "the user must predict and toggle a mode" to "the system gets out of the way on its own."

All visual decisions (palettes, type, layout, buttons, geometric icons) are governed by the `walkwalk-design` design skill.

## 6. Technical approach

Python 3 + tkinter, zero third-party dependencies, delivered as a single file, macOS / Windows.

- Scheduling: `tk.after()` drives the reminder loop; the root window is `withdraw()`n and acts purely as a background scheduler
- Popup: `Toplevel` + `-topmost` + chrome stripping per F20①; sizes and spawn coordinates from `winfo_screenwidth/height`; the settings panel and Skip menu are hand-drawn per F20②
- Meeting detection: per F12, synchronous with a 200ms budget before each popup
- Quotes: `quotes.json` loaded at startup (either the shipped `{"quotes": […]}` wrapper or a bare list is accepted); a broken file falls back to 10 built-in lines
- Fonts: on first run the fixed TTFs (`fonts/ttf/*.ttf`, the only install source; the OTFs are design sources and are never installed) are copied into the user font directory, with a hand-drawn "restart to see it" notice; tkinter refers to the family by name and silently falls back to system sans when unavailable
- Config: JSON at `~/.walkwalk_config.json`; unreadable config falls back to defaults, never crashes
- Packaging and autostart (`packaging/`): PyInstaller builds "Walk Walk.app" / "Walk Walk.exe" with the app icon; F19's Start at login works unpackaged too, pointing directly at `walkwalk.py`
- Running: `python3 walkwalk.py` from a terminal, or double-click the packaged app; quit with Ctrl+C (packaged: end the process from Activity Monitor / Task Manager)

Known limitations: running from source requires the terminal process to stay alive; multi-monitor setups spawn on the primary display only; the timer starts at launch rather than aligning to the clock; schedules cannot cross midnight (night shifts can use Always mode); macOS meeting detection is heuristic and can miss uncommon meeting apps; on Linux the Pango renderer has a known quirk with a few standalone HuFont glyphs (macOS/Windows use different renderers and are unaffected).

## 7. Roadmap

**v1.0.0 (this release)**: everything specified above.

**Candidates for future versions**: real camera/microphone occupancy detection on macOS (CoreAudio/AVFoundation instead of the process-name heuristic); a resident menu-bar icon with settings access outside popup moments; multi-monitor random placement; overnight schedule ranges; optional online quote refresh; a simple daily walk-count stat; interval jitter (45±5 min) as further anti-habituation.

## 8. Risks and open questions

The main risk remains reminder fatigue; mitigation has been layered from a single random position into position + palette + quote triple randomness. macOS meeting detection may miss uncommon meeting apps and interrupt a call — the fallback principle is "when detection fails, over-remind", and Skip remains the manual escape hatch. HuFont depends on a per-machine install; distribution must surface the one-time restart notice.

Open questions: should walk no.X count only answered ("I'm up!") reminders rather than all popups, to better reflect genuine stand-ups? Does "Not today" need a confirmation step? Should meeting detection be toggleable in Settings (some users may want reminders even during meetings)? To be decided from real usage feedback.
