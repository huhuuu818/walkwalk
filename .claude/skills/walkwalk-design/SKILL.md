---
name: walkwalk-design
description: Visual and copy specification for "Walk Walk", the break-reminder desktop app (color, typography, layout, buttons, motion, readability). MUST be read and followed before producing ANY visual output for this project — the reminder popup, settings panel, menu-bar icon, website/landing page, promo images, README artwork, any UI mockup or front-end code. Triggers include popup styling, UI, layout, design, colors, fonts, buttons, mockups, "make it look better", and any change to tkinter/HTML/SVG interface code. If the output will be seen by human eyes, use this skill, even when the user doesn't explicitly say "follow the design spec".
---

# Walk Walk · Design Specification v1.0

## 0. Positioning in one line

**"High-saturation colored paper + handwritten doodles + black ink lines"** — every popup should feel like a party flyer suddenly slapped onto the screen, not a system notification. Every design decision serves the product's core hypothesis: *conspicuous but not hostile*. High saturation delivers "conspicuous", doodles and handwriting deliver "not hostile", and the readability rules deliver "comfortable".

Reference imagery: a black-ink hand-drawn birthday flyer on colored paper; an orange-and-blue illustrated wristwatch poster. The texture is **print**, not software — flat, solid, hard-edged, with no frosted glass, gradients, or soft shadows. **No emoji anywhere.** The graphic vocabulary has exactly two families: abstract geometric shapes (solid dots, outlined triangles, squares, half-circles) and single-line hand-drawn doodles.

## 1. Color system

### 1.1 Seven palettes (one per day)

Each palette has five roles: `bg` (saturated paper base) / `card` (light card stock) / `ink` (always `#141414`) / `accent` (the only decorative color allowed to carry text; used for the primary button and selected states) / `sticker` (pure-graphic decoration, never carries text). Parenthesized numbers are WCAG contrast ratios against ink.

| Palette | bg | card | accent (text-safe) | sticker (graphics only) |
|------|----|------|------|------|
| A tomato | `#FF4B1E` (5.5) | `#F2E4C7` (14.7) | `#FFD500` (13.0) | `#0BA6DF` |
| B sky | `#35A8E0` (6.9) | `#F7F1E3` (16.4) | `#FFE014` (14.0) | `#E8281E` |
| C grass | `#00A551` (5.7) | `#F7F1E3` (16.4) | `#FFE014` (14.0) | `#E8281E` |
| D lemon | `#FFD90F` (13.3) | `#FFFDF5` (18.1) | `#35A8E0` (6.9) | `#E8281E` |
| E postbox | `#E8381E` (4.4) | `#F2E4C7` (14.7) | `#FFD500` (13.0) | `#0BA6DF` |
| F grape | `#A47CF5` (6.0) | `#F7F1E3` (16.4) | `#FFE014` (14.0) | `#00A551` |
| G flamingo | `#FF6FA5` (7.1) | `#FFFDF5` (18.1) | `#FFE014` (14.0) | `#0BA6DF` |

### 1.2 Hard readability rules (WCAG 2.1 AA)

There is exactly one text color: ink `#141414`. Readability is guaranteed by controlling which text may sit on which surface:

- **Body text / quotes / button labels / utility small text → only on card or accent** (contrast ≥ 6.9; all AA, AAA on card).
- **bg may carry large text only**: ≥ 24px, or ≥ 19px bold (the WCAG large-text threshold). All seven bg colors are ≥ 4.4 against ink, meeting large-text AA (≥ 3:1). E postbox is the only bg below 4.5 — on E, even large text must be bold.
- **Sticker colors never carry any text** (they don't reach 4.5 against ink); they are shapes only.
- De-emphasized text is ink at 55% opacity, and only ever on card (measured effective contrast still > 4.5). Gray is forbidden.
- Before adding any new color, compute its contrast against ink and slot it into one of the three tiers above; if it doesn't pass, it doesn't enter the palette.

### 1.3 Usage rules

- **One palette per day, chosen at random** on the day's first reminder; every popup and the settings area use it all day; it changes at midnight — "what color is today" becomes a small daily surprise. Position and quote remain per-popup random. Never mix colors across palettes in one screen.
- accent + sticker combined: at most three placements per screen, of which text-carrying accent at most one (the primary button).
- The settings area expands **inline** at the bottom of the popup (not a separate window) and inherits the current palette; the whole expanded block sits on a card-colored band; every control is hand-drawn (see §7).
- Forbidden: gradients, muted/low-saturation colors, any gray, system default blue `#007AFF`, overlays below 40% opacity.

## 2. Typography

### 2.1 Three roles

| Role | Face | Used for |
|------|------|----------|
| Handwritten display | **HuFont** (the **TTF** files under `fonts/ttf/` are the delivery and install standard; the OTFs are design sources only) | **Quote text**, popup title, wordmark, large numerals. The emotional lead of every popup |
| UI sans | Helvetica Neue / Inter → PingFang SC → sans-serif | Button labels, form labels, functional text |
| Utility small | Helvetica Neue / Inter → same fallbacks | Info bar, timestamps, numbering, footnotes; all-lowercase English |

### 2.2 Language and the HuFont charset

**The UI is English only**, which lets HuFont — a Latin-only face (`A–Z a–z 0–9 basic punctuation · '' "" …`; **no hyphen, no em-dash, no CJK**) — carry the entire display layer. Rules:

- **Quotes are short English lines** (≤ 10 words, from quotes.json), HuFont Bold 20–24px, centered, line height 1.35, the visually largest element on the card; when attributed, a utility-size "— Author" goes beneath;
- If CJK ever appears (e.g. localized documentation images), write the font stack as `'HuFont','PingFang SC',sans-serif` so CJK falls through — never let HuFont try to render CJK (it will drop glyphs).

### 2.3 Typesetting rules

- Popup title: HuFont Bold, **strictly one line** — measure at 32px and step down 2px at a time to a 22px floor; if it still doesn't fit, widen the window rather than wrapping. A slight rotation (−3°–3°) is allowed. "Catch me first!" while walking, "Time to walk!" once caught.
- The title sits **directly on bg with no underlay block of any other color** (an underlay would mix palettes — red line); title-area padding is fixed at 24px top / 16px bottom, never 0.
- Utility small text: 10px, all lowercase, letter-spacing +2%, like the top strip of a flyer.

**Type-size table (binding — to change a size, change this table first).** Hard rule: **every font size and every padding/margin must be an even number** (round odd sizes to the nearest even; round odd spacings up):

| Element | Face | Size |
|------|------|------|
| Popup title | HuFont Bold | 32, single-line auto-fit floor 22 (steps of −2, always even) |
| Quote | HuFont Bold | **24**, max 2 lines, floor 18 (steps of −2) |
| Quote attribution | utility | 10 |
| wordmark | HuFont Bold | 14 |
| walk no.X | utility | 10 |
| Primary button I'm up! | sans Bold | **14** |
| Secondary button Skip / menu items | sans Medium | **14** |
| Save / Cancel | sans Bold / Regular | 14 |
| De-emphasized Not today | sans Regular | 10 (utility tier) |
| Settings labels / chips / steppers / checkbox | sans Medium | 12 |
| Settings group captions | utility | 10 |

**Settings-panel vertical rhythm (binding)**: 10px top and bottom padding on the block (Schedule-to-top distance = Save-to-bottom distance — the block sits centered); 6px between rows; 4px inside the Days group (label row → chip row); 10px above AND below the divider (matching the bottom margin: speed→line = line→last row = last row→bottom edge). The validation-error line does not exist in the resting layout — it appears only when a save fails, growing the window with it.

**HuFont size compensation**: HuFont's strokes are thin and visually light; at equal point size it reads smaller than the sans. **Wherever HuFont sits next to or aligned with sans text, multiply the HuFont size by 1.15 for equal visual weight.** The table above already includes this compensation — use its values as-is.
- On the E postbox bg, titles must be bold (see §1.2).

### 2.4 Loading

- Web/HTML/SVG: `@font-face` with the font files (base64-inline them when delivering a single file).
- tkinter: cannot load font files at runtime — the face must be installed system-wide (`font=('HuFont', 24, 'bold')`); when unavailable, fall back to the sans stack and never error over it. Install the TTFs only; never install the OTFs.

## 2.5 Brand and fixed copy

- Product name **Walk Walk**; the wordmark is all-lowercase "walk walk", HuFont Bold. "WW" (two stacked HuFont Ws) may serve as an icon abbreviation.
- Fixed UI copy (do not rewrite): primary button **"I'm up!"**; skip dropdown: trigger **"Skip ▾"**, items **"Next 1 · 45 min" / "Next 2 · 1.5 h" / "Next 3 · 2 h 15 m" / "Next 4 · 3 h" / "Next 5 · 3 h 45 m"** (duration = N × the configured interval, auto-converted; a bare "Skip 1" is forbidden); bottom-right de-emphasized **"Not today"**; titles "Catch me first!" / "Time to walk!"; settings labels "Schedule / Active hours / Always / From / Days / Every day / Every / Speed / Start at login" (labels capitalized; inline words like "to" and units like "min" stay lowercase).
- Copy voice: short, imperative, playful; buttons state their outcome — never "OK/Submit".

## 3. Graphics and icons: zero emoji

**No emoji in any interface or copy, ever.** Icons are abstract geometric shapes. The vocabulary:

| Meaning | Shape | Drawing |
|------|--------|------|
| Reminder / now | Solid dot | sticker or accent fill, like the yellow dot of a watch face |
| Direction / action (stand up, dropdown) | Triangle | 1.5px ink outline or solid; dropdown indicator is a small solid ▾ shape |
| Schedule / hours (settings) | Square | 1.5px ink outlined hollow square |
| Settings | Hamburger | three equal-length horizontal bars, 2px ink, round caps, horizontally centered, evenly spaced |
| Mute / pause | Two vertical bars | solid ink |
| Mascot · little snake | Single wavy line | one 2px ink wavy stroke with a solid dot for a head; coils into a spiral once caught |

Rules: at most one geometric shape per control; 8px between a shape and its text; sticker shapes (solid dot / half-circle / triangle) sit like stickers on a card corner, may rotate slightly (−8°–8°), at most one per screen.

## 4. Layout

### 4.1 Popup structure (top to bottom)

```
┌──────────────────────────────────┐ ← bg saturated paper, outer corner radius 16px
│ walk walk    walk no.3         ≡ │ ← info bar: card-colored band + 1px ink rule below
│──────────────────────────────────│   left wordmark / center count / right settings (hamburger)
│  ▲● Time to walk!        ~~~~•   │ ← title area: directly on bg (large text only), HuFont + snake doodle
│ ┌──────────────────────────────┐ │
│ │  "Stretch now, glow all day" │ │ ← quote card: card color, square corners, 1.5px ink outline
│ │         — Thoreau            │ │    HuFont Bold large + utility attribution (if any)
│ └──────────────────────────────┘ │      ◗ ← sticker shape on the corner
│ [I'm up!] [Skip ▾]     Not today │ ← action row: primary + skip dropdown, weak button bottom-right
└──────────────────────────────────┘
```

- **The info bar sits on a card-colored band** (not bare bg) because utility small text doesn't meet the bg large-text rule — this is simultaneously a readability requirement and a signature layout. Content is fixed: left "walk walk" wordmark (HuFont Bold 14px), center "walk no.X" (the day's Xth reminder, real data), right hamburger settings icon. No decorative filler text.
- **Single-row action area**: primary "I'm up!" + secondary "Skip ▾" on the left, de-emphasized "Not today" pinned bottom-right; the action row sits on a card band (readability requirement for the de-emphasized text). There is no meeting-mode button — meeting silence is automatic and takes no UI.
- **Round outside, square inside**: the window body gets one large radius (16px); everything inside it is square (0px). Where tkinter cannot round a window, degrade fully to square — no half-hearted small radii.
- **The quote card is a fixed two-line-height box (red line)**: card height = 2 text lines + 16px padding top and bottom, **constant**, never stretching with the quote (otherwise card and window heights jump between popups). A quote lays out at 24px, wraps to two lines before ever shrinking, and only then steps down to 18px; a one-liner centers vertically in the same fixed box. **Never shrink the type just to force one line.**
- **8px grid**: all spacing in multiples of 8 where structure allows; window inner padding 24px, element gaps 16px, in-row gaps 8px. Fine-grained settings-row rhythm is governed by §2.3.

### 4.2 Settings area (inline expansion)

Clicking the hamburger stops the walk and expands the settings area **downward** below the action row (same window; height increase ≤ the popup body). Clicking again or Cancel collapses it. Compact single-column layout, top to bottom: Schedule (Active hours / Always exclusive pills) → From/to time (hand-drawn −/+ steppers) → Days (mon–sun square chips + Every day select-all) → Every (interval chips) → Speed (slider) → Start at login (hand-drawn checkbox) + Cancel / Save. The whole block sits on a card band; groups are separated by 1px ink rules, not whitespace; every control is hand-drawn per §7 — no native widgets.

**Zero-shift expansion (red line)**: on expand/collapse the window's **top-left corner must not move** — it only grows downward. Implementation requirements: ① every resize uses the full geometry string `f"{w}x{h}+{x}+{y}"` with the current x/y passed explicitly — **a size-only `geometry(f"{w}x{h}")` lets the window manager re-place the window, which is the #1 cause of "the popup jumps when I open settings"**; ② `after_cancel()` the walk timer before any resize so no stale callback re-places the window mid-expansion; ③ never re-center, never animate the expansion (§6 allows exactly one orchestrated moment); ④ only when the expanded bottom would run off screen may the whole window move up, by exactly the overflow, in one step — restored exactly on collapse.

**Height red line**: total settings height ≤ the popup body height. In Always mode the from/to and days rows are hidden (see §5 disabled states), making the panel visibly shorter.

## 5. Buttons and controls

| Tier | Style | States |
|------|------|------|
| Primary (I'm up!) | accent fill + 1.5px ink outline + ink bold text + hard shadow `3px 3px 0 #141414` | hover: fill switches to the **complementary hover step** + lifts 1px; pressed: **complementary pressed step** + face shifts into the shadow (shadow disappears) |
| Secondary (Skip) and chips | card fill + 1.5px ink outline + ink text (selected chip = accent fill) | hover / pressed use the same complementary two-step table; no hard shadow |
| De-emphasized (Not today) | no fill, no border, ink at 55%, one size down, underlined, **only on a card band/surface** | hover: back to 100% ink |

**Complementary interaction colors (text stays ink, all ≥ 4.6:1 — never compute your own)**:

| Palette accent | hover | pressed |
|------|------|------|
| `#FFD500` (A/E) | `#788EFF` (6.2) | `#5772FF` (4.6) |
| `#FFE014` (B/C/F/G) | `#7D8EFF` (6.3) | `#5C71FF` (4.6) |
| `#35A8E0` (D) | `#EF7134` (6.2) | `#DB5412` (4.6) |

The complementary flip creates a tiny hue-inversion surprise at the moment of interaction, consistent with the high-saturation system; the two lightness steps keep hover→pressed perceptibly progressive.

- **Zero borderless controls (red line)**: anything clickable must carry a complete 1.5px ink outline in every state — unselected = card fill + outline, selected = accent fill + outline. **Never imply "this is a control" through fill alone** (bare-text mon/tue/Active hours = typographic failure). The single exception is "Not today" (an intentionally weak text button, underlined).
- **Disabled states never use gray** (the system bans gray): when a control group doesn't apply in the current mode, **hide the whole row** rather than dimming it — in Always mode the from/to and days rows collapse away (they are meaningless there, and the panel gets shorter as a bonus). For the rare case that must stay visible but inert, use 40% ink text + dashed outline — still no gray.
- Button copy states its outcome: "I'm up!", "Skip 2" — never "OK/Submit".
- The hard shadow (solid offset shadow) is the only allowed "shadow", and only on the primary button; no blur shadows anywhere.
- Size constants: buttons/chips 36px tall; dropdown menu items 28px; settings rows follow §2.3's rhythm.

## 6. Motion

- The walk itself is the biggest motion; everything else stays restrained: **one orchestrated moment per popup** — the instant of capture (bg flashes accent / card tilts back upright, all within 150ms; the snake's wave becomes a spiral).
- Buttons have displacement feedback only (§5); no scaling, no springs.
- Forbidden: breathing lights, looping blinks, any transition over 200ms.

## 7. Implementation red lines: the tkinter anti-native checklist

The design only holds if the implementation keeps "zero native widgets". These are **hard rules**; violating any one means the spec was not implemented:

1. **Every Toplevel (the popup and any notice window) must drop system chrome**: after `overrideredirect(True)`, **macOS additionally needs the native window style removed**, or the system imposes rounded corners and a shadow:

   ```python
   win.overrideredirect(True)
   if sys.platform == 'darwin':
       win.tk.call('::tk::unsupported::MacWindowStyle', 'style', win._w, 'plain', 'noActivates')
   win.attributes('-topmost', True)
   ```
   Closing is handled by the "I'm up!" button and friends; dragging is self-implemented per PRD F7b.
2. **No native/ttk widgets of any kind**: `ttk.*`, `tk.Spinbox`, `tk.Checkbutton`, `tk.Radiobutton`, `tk.OptionMenu`, `tk.Menu` popups, `tk.Scale`, and `messagebox` are all banned. Everything is `tk.Frame/Label/Canvas` + mouse events: pill radio = toggled fills; checkbox = Canvas 1.5px ink square + accent fill with ink check; stepper = one outlined box containing −/value/+; **dropdowns must never be separate windows** (established fact: the modern macOS window server force-rounds every borderless Toplevel and adds a shadow; `overrideredirect` + `MacWindowStyle plain` cannot remove it). The correct pattern is an **in-window overlay**: the menu is a `tk.Canvas` inside the popup itself, positioned with `place(x=…, y=…)` and raised, drawing a card-colored, 1.5px-ink-outlined **square** rectangle with item rows; it **opens upward** (menu bottom = Skip trigger top − 4px), rows 28px (5 items = 143px, fits even the 360×240 floor); dismissed by outside click or Esc. An in-window overlay can never grow system chrome — the problem disappears at the root. All styling values come from the palette and §5.
3. **Icons must be drawn on Canvas**, never approximated with Unicode characters (glyphs like ◉/⊙ render inconsistently across platforms): settings icon = Canvas bars; dropdown triangle, square, spiral likewise.
4. **HuFont auto-installs on first run**: if the system font directory lacks HuFont, copy it in — macOS: copy `fonts/ttf/*.ttf` to `~/Library/Fonts/`; Windows: ctypes `AddFontResourceExW` (session) plus a copy into the user font directory + registry entry (persistent). Install before building the UI; on failure fall back to the sans stack without erroring. tkinter usage: `font=('HuFont', 22, 'bold')`. TTF only — never install the OTFs.
5. **A button is one Canvas, its text placed by the optical-centering formula** (the Frame+Label+padding pattern is proven misaligned and banned): one button = one `tk.Canvas(width=w, height=h)`; rectangle, text, and triangle all drawn on that one canvas, coordinates computed from `font.measure()` / `font.metrics()` — no hand-tuned magic pixel values.

   **Vertical centering must target the cap-height block, not the line box** — `create_text(anchor='center')` centers the ascent+descent box, while the eye reads the capital-letter block; the gap between the two is exactly why text keeps looking low even when the structure is "correct":

   ```python
   CAP_EM = {'HuFont': 0.700, 'Helvetica Neue': 0.717, 'Inter': 0.727}   # measured from the font files
   f = tkfont.Font(family=fam, size=S, weight=wt)
   asc, desc = f.metrics('ascent'), f.metrics('descent')
   cy = h/2 + (CAP_EM[fam]*S - asc + desc) / 2      # visual center, not line-box center
   cv.create_text(w/2, cy, text=t, font=f, fill=INK, anchor='center')
   ```
   Measure and render with the SAME `tkfont.Font` object — a font tuple can resolve to a different substituted face than the Font instance you measured with.
   **Horizontal**: with an attached shape (e.g. "Skip ▾"), compute `total = f.measure(text) + 8 + tri_w`, derive text and triangle positions from `x0 = (w-total)/2`, and center the group; never glue two widgets together with padding.
6. **Alignment comes from the layout system, never from eyeballing**: center with `place(relx=0.5, rely=0.5, anchor='center')` or grid/pack + **symmetric** padding; no spaces or hand-nudged pixels; everything in a row aligns on the vertical midline; padding uses the even-number constants. HuFont and the sans have different ascent/descent — **never mix the two faces in one Label**; the handwriting gets its own Label, aligned to neighbors by geometric center.
7. **Canvas icon rules**: fixed square canvas (18×18 suggested), compute coordinates from constants before drawing, the shape's geometric center must equal the canvas center; hamburger = equal length, equal spacing, round caps, width 2; stroke coordinates land on integer pixels to avoid blur and skew; screenshot at 4× to self-check.
8. **Expansion/collapse must not flicker**: the settings panel is **built once and kept resident**; expanding/collapsing only shows/hides it (`pack`/`pack_forget`), **never destroy + rebuild**. The order is fixed to eliminate intermediate frames: expand = grow the window → `update_idletasks()` → show the children; collapse = hide the children → `update_idletasks()` → shrink the window (the reverse order paints a frame where the window has shrunk but the content is still there). **Never call `update()`** (it force-renders exactly the in-between frame); only `update_idletasks()`.
9. **Window geometry has one exit**: all size/position changes go through a single `set_geometry(w, h, x, y)` helper that always assembles the full `WxH+X+Y` string and records the current x/y as the single source of truth; walking, settings expansion, and dragging all use it. Scattered `geometry()` calls are forbidden.
10. **Self-check screenshots**: when done, screenshot every state against `mockup/walkwalk-mockup.html` — popup, settings expanded, **dropdown open**, hover, and pressed. If chrome, widgets, fonts, alignment, or borders match the native look anywhere, or anything is skewed or borderless, it goes back for rework. The dropdown-open state is the most commonly missed.

## 8. Relationship to the PRD

The companion document is `docs/PRD.md`. This specification owns visuals and fixed copy; the PRD owns features and interaction; where they conflict on visuals, this file wins.

## 9. Pre-flight checklist (run through before shipping any visual)

- [ ] Used one of the seven palettes — no out-of-palette colors, no gray, no gradients?
- [ ] All small text on card/accent; bg carries only ≥24px (or ≥19px bold) text; bold titles on the E red bg?
- [ ] No text on sticker colors?
- [ ] Quote is English HuFont Bold (≤10 words), attribution in utility size, no CJK forced into HuFont, no hyphens/em-dashes?
- [ ] Zero emoji; every icon comes from the §3 shape vocabulary?
- [ ] Text-carrying accent at most once; accent+sticker ≤ 3 total; hard shadow only on the primary button?
- [ ] Spacing on the grid and all sizes/spacings even; 1.5px ink outlines; info bar and action row on card bands?
- [ ] Fixed copy intact ("I'm up!" / "Skip ▾ → Next N · duration" / "Not today" / lowercase wordmark)?
- [ ] Zero native widgets: no system chrome, no ttk/Spinbox/native check/radio/dropdown/messagebox, icons Canvas-drawn, HuFont installed and active?
- [ ] Title single-line (auto-fit 32→22px), padding 24/16, directly on bg with no underlay?
- [ ] Installed from `fonts/ttf/` TTFs and restarted the app after install?
- [ ] Interaction states use the specified complementary pairs (hover/pressed), no self-computed colors?
- [ ] Every clickable element has a full 1.5px ink outline (except Not today), no bare-text controls?
- [ ] Dropdown is an **in-window Canvas overlay opening upward** (not a separate window, hence no rounded corners)?
- [ ] Buttons are single-Canvas with cap-height optical centering?
- [ ] Always mode hides (not grays) the from/to and days rows; settings height ≤ popup body?
- [ ] Zero-shift, flicker-free expansion (full geometry string with x/y, walk timer cancelled, resident panel, correct order, no `update()`)?
- [ ] All type sizes from the §2.3 table; quote card fixed at two lines; settings rows follow the §2.3 rhythm?
