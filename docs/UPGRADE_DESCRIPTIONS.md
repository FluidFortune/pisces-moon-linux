<!--
  Pisces Moon OS — UPGRADE_DESCRIPTIONS.md
  Copyright (C) 2026 Eric Becker / Fluid Fortune
  SPDX-License-Identifier: AGPL-3.0-or-later
  See LICENSE file. Commercial licenses available via fluidfortune.com.
-->

# PISCES MOON OS — v0.5 UPGRADE SUITE
## What's New: Complete App Descriptions
### May 2026 — Eric Becker / Fluid Fortune

---

## GAMES (5 apps upgraded)

---

### SIMCITY — pisces-moon-city.html
**The biggest visual upgrade in the suite. Completely rebuilt from flat grid to full isometric 3D renderer.**

The game now renders on Canvas using isometric projection — every tile is a three-faced diamond with a top face and two visible side walls. Buildings have height levels (1–4) that grow visually as zones develop, shown as progressively taller isometric blocks with the correct left wall, right wall, and rooftop faces. Roads have center-line dashes. Parks show tree icons. Power plants glow yellow. Fire stations, police stations, and schools each have distinct iconography on their rooftops.

**Controls:** Click or drag to place zones. Shift+drag or right-click+drag to pan. Mouse wheel or pinch (mobile) to zoom (0.4×–2.5×). On touch: single tap to place, two-finger pinch to zoom, two-finger drag to pan.

**Zoning:** Residential (green), Commercial (blue), Industrial (orange), Park (dark green). Each costs a different amount and generates different demand.

**Infrastructure:** Roads (required for growth), Power plants (required for building occupation), Water plants (required for full population), Fire stations, Police stations, Schools — all affect happiness and population multipliers.

**Simulation:** Runs on a 500ms tick. Buildings grow from level 1 to level 4 based on demand. Demand is calculated dynamically — residential demand grows when commercial/industrial zones exist (jobs), commercial demand grows when residential density increases (customers), industrial demand grows when there's labor supply. The three demand bars at the bottom of the sidebar update in real time.

**Economy:** Tax income calculated as population × 7% × multiplier. Maintenance costs deducted annually (power/water/fire/police/school). Net income shown in header. Random events fire every ~5 years: festivals (+§2000), storms (−§1500), grants (+§5000), crime waves, baby booms, drought warnings.

**Happiness meter:** Shown as emoji (😢 → 😐 → 😄) based on power/water availability, park coverage, and service buildings.

**Speed control:** Pause / Normal / Fast / Ultrafast.

---

### PAC-MAN — pacman.html
**Full arcade Pac-Man with a 21×22 proper maze, four-ghost AI, and swipe touch controls.**

The maze is hardcoded from the classic layout — walls, dots, power pellets in the correct positions. Walls render in blue with neon inner outlines. Dots are small salmon-colored circles. Power pellets pulse with a sine-wave opacity animation.

**Touch controls:** Swipe in any direction to queue the next turn. The input includes a gesture buffer — a swipe registered slightly early queues the direction and executes it as soon as the corridor opens, preventing missed turns.

**Ghost AI — each ghost has a distinct personality:**
- **Blinky (red):** Directly targets Pac-Man's current tile. Relentless chaser.
- **Pinky (pink):** Targets 4 tiles ahead of Pac-Man's current direction. Tries to cut off escape routes.
- **Inky (cyan):** Targets an offset position from Pac-Man. Unpredictable flanking behavior.
- **Clyde (orange):** Chases directly when far away, retreats to his home corner when within 8 tiles. Makes him seem erratic.

**Scared mode:** Power pellet activates blue frightened ghosts. They flee toward the opposite corner of Pac-Man. Flash warning when scared timer is nearly expired. Eaten scared ghosts return to the ghost house and re-enter.

**Level progression:** Speed increases each level. Ghost pathfinding improves. Dot count resets, maze resets.

**Keyboard support:** Arrow keys also work. High score saved to localStorage.

---

### GALAGA — galaga.html
**Full Galaga arcade with formation entry, dive attacks, boss fighters, and swipe/tap touch controls.**

**Touch controls:** Slide finger left/right anywhere on screen to move the ship — no need to track a specific element. Tap (quick touch without movement) to fire. The ship follows your finger position in real time during a slide.

**Formation system:** All 50 enemies enter the screen in sequence — back rows first, then front. Each enemy follows a curved entry path down to its formation slot. While entering, enemies cannot be shot (they're off-screen or mid-path). Once all enemies are in formation, the swarm drifts left and right as a unit.

**Enemy types:**
- **Bees (green):** Basic enemy, smallest. Animated wing flap. 50 points.
- **Butterflies (blue):** Mid-tier. Checkerboard pattern with animated inner squares. 80 points.
- **Boss Fighters (red):** Top rows. Arrow-shaped body with glowing core. 150 points.

**Dive attacks:** Random enemies break from formation and dive toward the player in a sine-wave arc. They return to formation if they miss. Dive frequency and speed scale with level.

**Enemy fire:** Random enemies fire red bullets at increasing frequency each level. Bullet speed scales with level.

**Lives display:** Ship icons in bottom left. Level counter in header. High score to localStorage.

---

### CHESS — chess.html
**Full chess with minimax alpha-beta pruning AI, tap-to-move touch, undo, flip board, hint.**

The board renders in classic brown/tan with coordinate labels (a–h, 1–8). Pieces are Unicode chess symbols sized to fill squares.

**Touch/click controls:** Tap a white piece to select it — legal move destinations highlight in olive/yellow. Tap a highlighted square to move. Tap a different white piece to reselect. The selected square glows yellow.

**AI engine:** Minimax with alpha-beta pruning. Uses piece-square tables for positional evaluation (pawns rewarded for advancement and center control, knights penalized on edge squares, etc.). Difficulty levels:
- Easy: depth 2 — sees 2 moves ahead
- Medium: depth 3 — default
- Hard: depth 4 — strong amateur level
- Expert: depth 5 — takes longer but plays well

**Last move highlight:** The from/to squares of the most recent move are highlighted yellow (faded) so you can see what the AI just played.

**Hint system:** HINT button runs the same minimax at depth 2 and highlights the recommended move in green (from and to squares).

**Undo:** Undoes the last two half-moves (your move + AI response) so you always return to your turn.

**Full rules:** Castling (kingside and queenside, both colors), en passant, pawn promotion (auto-promotes to queen), check detection, checkmate detection, stalemate detection.

**Move log:** Algebraic notation displayed below the controls for the entire game. Scrollable.

---

### SNAKE — snake.html
**Snake with swipe touch controls, obstacle progression, animated snake body with eyes.**

**Touch controls:** Swipe in any direction to turn. Direction is queued — if you swipe while mid-segment, the turn executes at the next grid step. Prevents the "swiped but it didn't register" problem.

**Visual:** Snake body uses `roundRect` for rounded segments. Color gradient from bright green at head to darker green at tail. The head has animated eyes that point in the direction of travel with white sclera and green pupils. Food pulses with a sine-wave radius animation and has a small highlight dot.

**Obstacle system:** Level 1 has no obstacles. Each level-up adds 2 obstacles — dark blue tiles that kill on contact. Obstacles are placed randomly, avoiding the current snake body and food position.

**Wrapping:** Snake wraps through walls — exits right edge, enters left edge.

**Scoring:** 10 × level per food eaten. Level up every 60 points. Speed increases with level (150ms → 60ms minimum).

**Grid:** Scales to fill available space. Background grid lines are faintly visible.

---

## TOOLS (7 apps upgraded)

---

### CALENDAR — calendar.html
**Full event calendar with three views, color-coded events, and persistence.**

**Month view:** Classic 7-column grid. Today's date highlighted with cyan border. Selected date highlighted in gold. Days in adjacent months are shown at reduced opacity for context. Days with events show colored mini-labels (up to 3 visible, +N more for overflow).

**Week view:** (same grid, filtered to current week's days)

**Agenda view:** All upcoming events sorted chronologically, displayed as a scrollable list with color bars, date, time, and description.

**Event creation (right sidebar):**
- Title, date (date picker), time (time picker), optional description
- Color selector: 6 color dots (cyan, green, red, gold, orange, purple)
- Events persist to localStorage

**Event list:** When a date is selected, all events for that day appear in the right sidebar sorted by time, with delete buttons.

**ICS-compatible structure:** Events stored with all fields needed to export as .ics in a future version.

---

### CLOCK — clock.html
**Four-tab clock suite: analog clock, stopwatch with laps, countdown timer with spin controls, 12-city world clock.**

**Analog clock:** Canvas-drawn with hour tick marks (major ticks every 3 hours in gold, minor in dark blue), hour hand (gold), minute hand (blue), second hand (red, with smooth animation), center dot. Updates every 100ms for fluid second hand sweep.

**Digital clock:** Large Orbitron font with blinking separators. Full date line below. Timezone shown.

**Stopwatch:** Start/Pause/Resume/Reset. LAP button records split times with lap number and elapsed time. Lap list scrolls, most recent at top. Display shows MM:SS.mmm to millisecond precision.

**Countdown timer:** Three spin controls (hours/minutes/seconds) with ▲/▼ buttons. Start/Pause/Resume/Reset. Display color shifts from gold → yellow → red as time runs out. Vibration alert on completion (mobile). Display turns red and shows "TIME UP!" on completion.

**World clock:** 12 cities — Los Angeles, New York, Chicago, Denver, London, Paris, Moscow, Dubai, Tokyo, Sydney, Beijing, Singapore. Each card shows local time (HH:MM:SS), short date, and a ☀/🌙 indicator based on whether it's daytime (6am–8pm) at that location. Cards highlighted differently for day vs night. Updates every second.

---

### NOTEPAD — notepad.html
**Multi-file markdown editor with live preview, find/replace, syntax toolbar, and auto-save.**

**Three-column layout:** File list (left), toolbar + editor (center), nothing on right — editor takes full center.

**File management:** Multiple named files stored in localStorage. New file button with name prompt. Delete with confirmation. Files show character count and creation date. Active file highlighted with green accent.

**Edit / Split / Preview modes:**
- Edit: just the textarea
- Split: textarea left, rendered markdown preview right side by side
- Preview: full rendered markdown only

**Markdown preview engine:** Parses headers (H1/H2/H3), **bold**, *italic*, `inline code`, ` ```code blocks``` `, > blockquotes, - unordered lists, --- horizontal rules, [links](url). All styled to match the Pisces Moon design system.

**Toolbar buttons:** Bold, Italic, Code, Heading (cycles H1→H2→H3→none), List, Quote, Link. Each wraps selected text or inserts at cursor.

**Find & Replace bar:** Toggle with FIND button or Ctrl+F. Find Next, Replace Next, Replace All. Shows result count. Highlights found text in the textarea.

**Auto-save:** 2 seconds after any edit, saves to localStorage. Status indicator shows "auto-saved" with timestamp.

**Keyboard shortcuts:** Ctrl+S to save, Ctrl+F to find, Tab for 2-space indent, Enter to send in normal mode.

**Export:** Downloads current file as .md to device.

---

### ETCH — etch.html
**Multi-layer canvas drawing app with 10 tools, undo/redo stack, color palette, opacity, zoom.**

**Tools:** Pen (hard edge, precise), Brush (2× wider, soft strokes), Eraser (destination-out compositing for true transparency), Line, Rectangle, Circle/Ellipse, Fill bucket (flood fill), Text (prompt for text, places at click position), Color picker (eyedropper — samples canvas color), Zoom in/out/reset.

**Shape preview:** Line, Rectangle, and Circle tools render a live preview on a temporary overlay canvas while dragging — you see the shape forming before committing it to the layer.

**Multi-layer system:** Add layers with the + ADD button. Toggle visibility with the eye button. Click a layer to make it active (drawing goes to active layer only). Delete layers. Layers render bottom-up. Layer list shows in reverse order (top of list = top of stack).

**Undo/Redo:** Saves snapshots of ALL layer data on each stroke start. Undo/redo navigate through the snapshot stack (up to 20 states).

**Color palette:** 20 preset colors in a 4×5 grid plus a full color picker input. Selected color shown in a preview swatch.

**Size slider:** 1–60px.

**Opacity slider:** 5–100%.

**Export:** Merges all visible layers onto a single canvas with Pisces Moon dark background, downloads as PNG.

**Touch support:** Full touch drawing on all tools. Touch events mapped to same handlers as mouse.

---

### CALCULATOR — calculator.html
**Three-mode calculator: standard arithmetic, scientific functions, unit converter.**

**Standard mode:** Standard 4×5 button grid. AC (all clear), CE (clear entry/backspace), %, ÷, ×, −, +, =, ±, decimal. Expression shown above result. Result shown in large Orbitron font.

**Scientific mode:** 5-column grid adds: sin, cos, tan, asin, acos, atan, log, ln, √, xⁿ, π, e, |x|, x², 1/x, parentheses. All trig functions operate in radians.

**Unit converter (four categories):**
- **Length:** km, m, miles, ft, in, cm — bidirectional
- **Temperature:** °F, °C, K — proper formulas (not just ratios)
- **Weight:** lb, kg, oz, g
- **Speed:** mph, km/h, m/s, knots

All converters update live as you type. Result shown in highlighted output box.

**History tape:** Last 30 calculations stored to localStorage. Click any history item to recall the result. History displayed as expression → result pairs.

**Keyboard support:** Full numeric keyboard, operators, Enter for =, Escape for AC, Backspace for CE.

---

### HASH TOOL — hash_tool.html
**File and text hashing with MD5, SHA-1, SHA-256, SHA-512, plus hash comparison.**

Text input hashes live as you type. File drag-and-drop or picker for file hashing. All four algorithms computed simultaneously and displayed side by side. Hash comparison: paste two hashes to verify match — shows green checkmark or red ✗ with character-by-character diff highlighting. HMAC support with key input. Copy-to-clipboard buttons on each hash output.

---

### SYSTEM INFO — system_info.html
**Live system dashboard with CPU/RAM sparklines, network stats, storage breakdown, and device info.**

Real-time sparklines for CPU usage estimate (via performance timing), memory usage (navigator.memory API where available), and network round-trip estimation. Battery status (level + charging state) via Battery API. Device information: user agent parsed into browser/OS/device type, screen resolution, color depth, pixel ratio, touch support, language, timezone, connection type. localStorage usage bar showing bytes used vs estimated quota.

---

## INTEL (4 apps upgraded)

---

### MEDICAL REFERENCE — medical_ref.html
**Complete emergency protocols, vital signs reference, drug database, triage guide, dosage calculator. Fully offline.**

**14 sections accessible from left navigation:**

**Emergency protocols (9):** CPR (adult, step-by-step with AED guidance), Choking/Heimlich (adult + infant), Bleeding/hemorrhage control (packing, pressure, tourniquet), Stroke/FAST recognition (visual 4-panel FAST card), Anaphylaxis (epinephrine dosing, positioning, adjuncts), Burns (rule of nines, classification, treatment), Fractures & sprains (RICE, splinting, neurovascular check), Hypothermia (mild/moderate/severe classification, rewarming), Heat stroke (vs heat exhaustion, cooling protocols).

Each protocol uses numbered step cards with bold action words, dosages in sub-text, and DO/DO NOT callout boxes.

**Vital signs reference:** 8 cards covering Heart Rate, Blood Pressure, Respiratory Rate, Temperature, SpO₂, Blood Glucose, Pediatric HR, Glasgow Coma Scale. Each card shows normal range (green), warning range (yellow), and dangerous range (red).

**Drug quick reference:** 12 common emergency/field drugs with name, adult dose, warnings, and contraindications. Live search filters the list as you type. Covers: Aspirin, Ibuprofen, Acetaminophen, Diphenhydramine, Loratadine, Epinephrine, Amoxicillin, Azithromycin, Metronidazole, Ondansetron, Loperamide, Ciprofloxacin.

**Triage (START method):** Color-coded triage categories (Black/Expectant, Red/Immediate, Yellow/Delayed, Green/Minor) with decision criteria. RPM quick-check guide for field triage.

**Dosage calculator:** Enter patient weight (kg or lb), mg/kg dose, and optional drug concentration. Calculates total mg dose and volume in mL. Warning disclaimer included.

---

### SURVIVAL REFERENCE — survival_ref.html
**Illustrated wilderness survival guide. 12 sections, fully offline. Built for actual field use.**

**STOP Protocol:** Four-panel card (Stop, Think, Observe, Plan) with the Rule of 3s (air/shelter/water/food) and survival priority order.

**Shelter:** Site selection criteria, debris hut construction step-by-step, lean-to construction, snow quinzhee. Ground insulation priority explained.

**Water:** Finding sources (terrain, vegetation indicators, dew collection), boiling, chemical treatment (iodine/chlorine with doses), solar disinfection (SODIS), improvised filter construction. Danger list (seawater, urine). Hydration indicators.

**Fire:** Tinder identification, kindling graduation, structure types (tepee/log cabin/star), bow drill friction fire technique, flint and steel. Danger list (toxic smoke species).

**Food & Foraging:** Universal edibility test protocol, edible plant grid (Cattail, Dandelion, Pine, Clover, Wild Berries, Acorns — each with edible parts and preparation notes), toxic plant danger list. Hunting/trapping/fishing/insects brief.

**Navigation:** Shadow stick compass method, watch compass method (analog), terrain reading (rivers to civilization, power lines), natural indicators (moss, wind-shaped trees, snow melt). Dead reckoning technique.

**Celestial Navigation:** Polaris/Big Dipper for North (Northern hemisphere), Southern Cross for South, Orion's belt for East/West, quarter moon method.

**Signaling:** Signal mirror technique, smoke signals (3-fire triangle), ground symbols (X, V, SOS, direction arrow), whistle protocol (3 blasts), light/flashlight SOS, bright color deployment.

**Essential Knots:** Bowline, Clove Hitch, Square Knot, Taut-Line Hitch, Sheet Bend — each with use case and relative strength.

**Weather Signs:** Red sky rule, falling pressure indicators, cloud type identification (cirrus/cumulonimbus/stratus), fog patterns, wind direction rules, animal behavior indicators.

**Hazards:** Snakebite protocol (do/do not list), poisonous plants, lightning safety (flash-to-bang rule, crouch position), swift water dangers.

---

### WEATHER — weather.html
**BME280 sensor readings + NWS forecast + severe weather alerts. Local-first.**

Reads temperature, humidity, and pressure from T-Beam BME280 via transport bridge. Displays current conditions with trend arrows. Fetches 7-day forecast from National Weather Service API (free, no key required) using device GPS coordinates. Severe weather alerts shown as banners. Pressure trend chart (sparkline, 60-point history) for storm prediction. Heat index and dew point calculated from sensor data.

---

### FIELD NOTES — field_notes.html
**Structured GPS-stamped field observation log. Different from a general notepad.**

Every entry is automatically stamped with date, time, and GPS coordinates (from T-Beam or browser geolocation). Category tags: Security Observation, Terrain Note, Contact Log, Medical Note, Intel, General. Entries stored as structured JSON. Search and filter by category or date range. Export as JSON or CSV. Each entry shows on an embedded Leaflet map so you can see where observations were made geographically. Useful for SAR teams, field researchers, trail runners, security assessments.

---

## MEDIA (1 app upgraded)

---

### AUDIO PLAYER — audio_player.html
**Full audio player with real-time waveform visualizer, playlist, shuffle/repeat, speed control.**

**File loading:** Click "LOAD FILES" to open any number of audio files (mp3, ogg, wav, flac, m4a — whatever the browser supports). Files added to library list showing name and file size. Click any track to play immediately.

**Waveform visualizer:** Canvas-based frequency spectrum analyzer using Web Audio API AnalyserNode. 128-bin FFT displayed as vertical bars filling the canvas. Color shifts from blue to cyan to white based on amplitude — higher frequencies glow brighter. Progress overlay drawn in translucent cyan showing elapsed vs remaining. Click anywhere on the waveform canvas to seek to that position.

**Progress bar:** Standard seek slider below waveform. Current time / duration displayed on both sides.

**Controls:** Previous track, skip back 10s, play/pause (large circle button), skip forward 10s, next track.

**Shuffle:** Randomizes next track selection. Toggle button highlights when active.

**Repeat:** Loops current track. Toggle button highlights when active.

**Volume:** Slider 0–100% with percentage display.

**Playback speed:** Dropdown — 0.5×, 0.75×, 1×, 1.25×, 1.5×, 2×. Useful for podcasts, language learning, or slowing down recorded audio for transcription.

---

## SUMMARY TABLE

| App | Category | Key Upgrade |
|-----|----------|-------------|
| SimCity | Games | Full isometric 3D renderer, building growth, disasters |
| Pac-Man | Games | Swipe touch controls, proper maze, 4-ghost personality AI |
| Galaga | Games | Touch slide+tap, formation entry, boss fighters |
| Chess | Games | Minimax alpha-beta AI depth 2–5, tap-to-move, hint |
| Snake | Games | Swipe touch, animated body/eyes, obstacle progression |
| Calendar | Tools | Events, 3 views, color coding, localStorage |
| Clock | Tools | Analog canvas, world clock (12 cities), timer spin controls |
| Notepad | Tools | Markdown preview, multi-file, find/replace, auto-save |
| Etch | Tools | Multi-layer, 10 tools, undo/redo, flood fill, shape preview |
| Calculator | Tools | Scientific mode, 4-category unit converter |
| Hash Tool | Tools | File hashing, HMAC, comparison, all 4 algorithms |
| System Info | Tools | Live sparklines, battery, storage, network stats |
| Medical Ref | Intel | 9 protocols, drug DB, triage, dosage calc — fully offline |
| Survival Ref | Intel | 12 sections, edible plants, knots, signaling, celestial nav |
| Weather | Intel | BME280 + NWS API + alerts, pressure trend |
| Field Notes | Intel | GPS-stamped structured log, category tags, map view |
| Audio Player | Media | Waveform FFT visualizer, playlist, shuffle/repeat/speed |

**17 apps. 272KB total HTML. All offline-capable. All touch-optimized.**

---

*Pisces Moon OS — v0.5 Upgrade Suite*
*Fluid Fortune — May 2026*
*The Clark Beddows Protocol — Local Intelligence — Your machine, your rules*
