# Changelog — v2.3.0 (Display Tab Per-Screen Search, Shared Tag-Pool Deduplication, Danbooru Tag Category Colors, 4-Layer Media Tags Box & Direct Tray Click)

## 🎯 v2.3.0 Per-Screen Display Search & Danbooru Category Color Updates

- **Removed Standalone Floating Search Bar (`FloatingSearchBar`) & Integrated All Search Controls into the `Display` Tab**:
  - Removed the separate floating desktop search window (`FloatingSearchBar`) and the obsolete `"Search Bar Position: Locked/Unlocked"` setting on the Credentials tab.
  - Placed all search and playback features directly inside the **Display** tab of the Application Settings window (`SettingsDialog`), immediately below the **`Select Screen`** dropdown and the **`Display wallpaper on this screen`** checkbox, with no minimize button.
- **Per-Screen Playback & Refresh Controls Above the `TAGS` Search Bar**:
  - Positioned the per-screen status indicator badge (`● Ready`, `✔ P:X (Y pooled)`, `⏸ Screen Paused`, `○ Screen Disabled (No Fetch)`, `✖ API Error`) on the left and the **Refresh (`⟳`)**, **Previous (`◀`)**, **Next (`▶`)**, and **Pause (`PAUSE`)** buttons on the right **above** the new `TAGS =` search bar and **below** the `Select Screen` dropdown and display checkbox.
  - All four buttons (**Refresh `⟳`**, **Previous `◀`**, **Next `▶`**, and **Pause `PAUSE`**) operate independently on **only the currently selected screen** in the `Select Screen` dropdown.
- **Independent Per-Screen `TAGS` Search & Strict No-Fetch Guard for Unchecked Screens**:
  - Added `"searchtags"` (`order: 0`, default `"scenery no_humans"`) to each screen's properties in `project.json` and `danbooru_service.py`.
  - If a screen's **`Display wallpaper on this screen`** checkbox is unchecked (`enabled == False`), both `danbooru_service.py` (`/api`, `fill_tag_pool`, `ensure_screen_tag_pool_populated_async`) and `index.html` (`SCREEN_ENABLED = false` default startup state until `/properties` confirms `enabled: true`) strictly skip all media fetching and preloading for that screen.
- **Shared Tag-Pool Deduplication Across Screens (`TAG_POOLS`)**:
  - Implemented `TAG_POOLS` keyed by `canonical_pool_key(tags)`. When multiple enabled screens use the same `TAGS` query, they share a single upstream Danbooru API fetch pool (`TAG_POOLS[pool_key]`) while maintaining independent per-screen `seen_ids` cursors—eliminating duplicate HTTP requests to `danbooru.donmai.us` for identical tag searches.
- **Below-Input Auto-Suggestion & Saved Searches Dropdowns**:
  - Configured both the live tag auto-suggestion popup (`self.suggest_dropdown`) and the saved searches popup (`self.saved_dropdown`, `▼` button) to always populate **below** the `TAGS` search box (`ry = self.search_container.winfo_rooty() + self.search_container.winfo_height() + 2`).
- **Permanent 4-Layer Scrollable Displayed Media Tags Box**:
  - Placed a permanent full-width sub-panel box (`self.media_tags_box_frame` with `self.media_tags_text`, `height=4`, `wrap="word"`, and vertical `ttk.Scrollbar`) directly below the `TAGS` search box.
  - Displays all tags of the **most recently displayed media** on the currently selected screen (reported in real time by `index.html` via `GET /report_shown?screen=<id>&post_id=<post_id>` when a media element becomes visible on screen).
  - Clicking any tag in the permanent 4-layer box immediately appends that tag to the selected screen's `TAGS` search bar and applies the updated search.
- **Authentic Danbooru Category Color Coordination Across All 3 Tag Locations**:
  - All tags in the **`TAGS` search box**, the **auto-suggestion dropdown**, and the **permanent 4-layer displayed media tags box** are color-coordinated by their official Danbooru tag category (`DANBOORU_TAG_COLORS`, with light and dark theme palettes):
    - **General (`category 0`)**: Blue (`#0075f8` Light / `#009be6` Dark)
    - **Artist (`category 1`)**: Red (`#c00004` Light / `#ff8a8b` Dark)
    - **Copyright (`category 3`)**: Purple (`#a800aa` Light / `#c797ff` Dark)
    - **Character (`category 4`)**: Green (`#00ab2c` Light / `#35c64a` Dark)
    - **Meta (`category 5`)**: Orange (`#fd9200` Light / `#ead084` Dark)
- **Instant System Tray Left-Click to Open Settings**:
  - Updated `setup_tray()` in `danbooru_service.py` so `pystray.MenuItem("Settings", on_tray_settings, default=True)` is the default primary action: **left-clicking** the Danbooru Wallpaper system tray icon immediately opens (or brings to front) the Application Settings window, while **right-clicking** opens the context menu with `Settings` and `Exit`.

---

## 🛡️ v2.2.1 High-Stress Stability & Resource Graph Accuracy Updates

- **Fixed Application Freeze & ~50% GPU Spike Under Rapid `"Next"` Button Presses (Max 36-Tile Masonry)**:
  - **1.0-Second Internal `"Next"` / `"Previous"` Cooldown**: Added `NAV_BUTTON_COOLDOWN_SEC = 1.0` in `danbooru_service.py` (with visual cooldown feedback on the `◀` / `▶` buttons in `FloatingSearchBar`) and `MANUAL_NAV_COOLDOWN_MS = 1000` in `index.html` (`window.triggerNextMedia` / `window.triggerPreviousMedia`) to prevent rapid-fire click floods from queuing dozens of overlapping transitions per second.
  - **Single-Flight JS Evaluation Worker (`_js_eval_worker`)**: Replaced per-click `threading.Thread` spawning in `_async_evaluate_js` with a single-flight background queue worker so rapid UI actions never pile up concurrent threads contending on `pywebview`'s WinForms `Control.Invoke` semaphore.
  - **Strict Single-Flip Concurrency & Reflow Guard (`isAnyMasonryTileBusy`)**: Enforced `if (isAnyMasonryTileBusy()) return false;` in `triggerNextMasonryFlip()` and removed the `busyGroups` bypass (`if (eligible.length === 0 && forceIgnorePlayGuard)`) so rapid manual `"Next"` triggers never launch overlapping 3D GPU layers or recalculate BSP/Row geometry from mid-animation rects.
  - **Steady-State Preload Cap & Serialized Scratch-Canvas Downscaling**: Capped `readyImageQueue` in Masonry mode to `10` items once all `MASONRY_TILES` (`36`) are populated on screen (instead of holding 42 extra decoded media nodes in RAM/VRAM), and serialized `downscaleScratchCanvas` with `isDownscaleCanvasBusy` while deferring canvas downscaling during active flips.
- **Fixed Memory Resource Graph Scaling Against 100% Total Physical System RAM**:
  - Updated `ResourceGraphDialog` in `danbooru_service.py` (left-sidebar Memory mini sparkline, single `Memory` graph view, and `All Graphs (3x)` stacked view) to plot `self.monitor.ram_pct_history` against a fixed `0% – 100%` scale of total physical system memory (`total_phys_mb`) rather than a dynamic `4096 MB` ceiling—so actual system memory percentage displays at its true proportional height on the graph.

---

## ⚡ v2.2.0 Performance, Stability & Telemetry Updates

- **Removed Blurred Sections in `Rows` (Google Photos) Masonry Mode**:
  - Added `#stage.rows-mode` styling and updated `applyTileAmbientBackdrop()` / `rebuildFullMasonryLayout()` so that when `Rows` is selected, all blurred/ambient background sections are completely removed (`background-image: none`) and each tile cleanly fills its exact justified horizontal row cell (`object-fit: cover`).
- **Fixed Fatal Application Freeze When Toggling Masonry Layouts (>3 Times)**:
  - **Root Cause Identified**: Toggling between Masonry layouts previously invoked `push_properties_to_webview(sid)` synchronously on the Tkinter UI thread, which executed blocking cross-thread Win32 `SetWindowPos(..., SWP_FRAMECHANGED)`, `SendMessageW(WM_SIZE)`, and `RedrawWindow(..., RDW_UPDATENOW)` calls on the WebView2 HWND followed immediately by a blocking `win.evaluate_js(...)` semaphore wait and a redundant `window.dispatchEvent(new Event('resize'))`. Rapidly toggling >3 times caused a classic Win32 cross-thread message-pump deadlock between the Tkinter GUI thread and the WebView2 WinForms UI thread with zero Python traceback or log output. Additionally, `solveAspectLockedSubtree()` in `index.html` reordered `masonryGroups` when `numGroups >= 3` without re-indexing `group.index` and `tile.groupIndex`.
  - **Fix**: Replaced blocking cross-thread `push_properties_to_webview` calls with a coalesced single-flight background worker (`_property_push_worker`), restricted Win32 geometry resyncs strictly to screen `enabled` state changes using `SWP_ASYNCWINDOWPOS = 0x4000`, added `prop_seq` in `/epoch` as a lock-free poll fallback, removed the redundant `resize` event dispatch, and re-indexed `masonryGroups` after BSP solving.
- **Background Pre-Rendering & Pre-Organization of Next Masonry Switch (Zero Memory Bloat)**:
  - Added a single-slot pre-staging pipeline (`preStageNextMasonrySwitch()` + `precomputeGroupReflowPlan()`) that runs `1.2s` before the flip timer fires while the screen is completely still:
    1. Pre-picks the target tile and next descriptor, pre-Solves the exact post-flip BSP or Justified Row geometry (`newRects`), and pre-calculates every sibling tile's inverse FLIP transform matrix (`invDx`, `invDy`, `invSx`, `invSy`).
    2. Pre-attaches the incoming `<img>` or `<video>` into a hidden `.masonry-prestage-slot` inside the target tile (`visibility: hidden`, `opacity: 0`) and forces GPU texture upload via `img.decode()` prior to starting the flip.
    3. At the 90-degree flip midpoint, swaps visibility and applies pre-computed FLIP transforms with zero DOM insertion, zero image decode, and zero layout solver math.
  - **Strict Memory Bounds**: Enforces a single-slot invariant (`preStagedMasonrySwitch`, max 1 hidden node across the entire grid) and downscales oversized static images in Masonry mode (`>1280px`) during preload via a reusable `1×1`-reset scratch canvas with immediate `URL.revokeObjectURL()` cleanup on tile eviction.
- **Relabeled Masonry Layout Toggle Button & Config to `"Mondrian"` vs. `"Rows"`**:
  - Updated `danbooru_service.py`, `index.html`, and `project.json` (`masonrylayout`) from `"mondrian"` / `"google_photos"` (`"Aspect-Locked BSP Mondrian Solver"` / `"Google Photos (Justified Rows)"`) to **`"Mondrian"`** (`"mondrian"`) and **`"Rows"`** (`"rows"`), with transparent backward-compatibility for existing saved configs.
- **New `"📊 Resource Graph"` Button & Windows Task Manager Performance Pop-Out (`ResourceGraphDialog`)**:
  - Added a **`📊 Resource Graph`** button in the top header of the Settings window that launches a Windows Task Manager Performance-style pop-out window monitoring the wallpaper application's entire process tree (`Python` + child `msedgewebview2.exe` processes) for **CPU (%)**, **Memory (Working Set & Private Commit MB / % of Total Physical System RAM)**, and **GPU (%)** with scrolling 60-second time grids, left-sidebar mini sparklines, and a stacked 3-graph overview mode.

---

## 🎨 v2.1.0 Display Modes & Search Bar Navigation Updates

- **Renamed Display Setting to `Polaroid`**:
  - Updated the display mode name and internal property prefix from `Polaroid` across `danbooru_service.py`, `index.html`, `project.json`, `README.md`, and the `[POLAROID]` log glossary entry.
- **New `Masonry` Display Mode (`masonry`) — Dual Layout Engines (`Mondrian` & `Rows`), On-Demand 3D GPU Layers & Localized Reflow**:
  - Added a **Masonry Layout** toggle button (`masonrylayout`) in the Display tab and `project.json` to switch live between two media layout engines:
    1. **Mondrian (`mondrian`)**: Bottom-up binary space partition solver that computes split orientations and exact harmonic/additive split ratios from each media file's true aspect ratio (`naturalW / naturalH`).
    2. **Rows (`rows`)**: Justified horizontal rows (like Google Photos Web) where tiles in each row share an exact justified height (`availRowW / sum(aspect_i)`) and row heights normalize proportionally to fill `100vw × 100vh` without any blurred background bars.
  - **On-Demand 3D GPU Layer Promotion (`>10` Tile Stutter Elimination)**: Idle tiles remain lightweight 2D layers without permanent `perspective: 1100px`, `preserve-3d`, or `will-change: transform`. Only the single actively flipping tile is promoted to a 3D GPU layer (`.is-flipping`), and only the flipped row (in `Rows` mode) or local 3–5 tile subgroup (in `Mondrian` mode) reflows via GPU FLIP (`translate3d` + `scale3d`).
  - Added full-playthrough protection for animated GIFs (via single-pass Blob URL preloading and binary GIF89a Graphic Control Extension `0x21 0xF9` frame duration parsing) and MP4 videos (`ended` / `timeupdate` loop tracking) so animated files always finish playing at least once before they can be flipped.
  - Added Masonry display settings in `project.json` and the Display tab: **Masonry Layout** toggle button (`Mondrian` ⇄ `Rows`), **Tile Count** (`4 – 36`, default `12`), **Gap** (`0 – 10 px`, default `4 px`), and **Delay** (`1 – 60 s`, default `5 s`).
- **Search Bar Previous (`◀`) & Next (`▶`) Vertical Rectangle Buttons**:
  - Added two vertical rectangle arrow buttons (`◀` and `▶`) on the right side of the refresh button (`⟳`) on the floating search bar.
  - **Previous (`◀`)** requeues the last shown file to the front of the media queue so that it displays next.
  - **Next (`▶`)** immediately plays/displays the next queued file across all display modes (`scroll`, `polaroid`, `slideshow`, and `masonry`), with `NAV_SEQ` sequence deduplication so `evaluate_js` and `/epoch` polling never double-fire.

---

## 🛡️ Security Audit & Anti-Malware Hardening

- **Binary Magic-Byte Signature Verification (`verify_media_magic_bytes`)**:
  - `/media` proxy now inspects the first chunk of every upstream file to verify genuine `JPEG` (`FF D8 FF`), `PNG` (`89 50 4E 47`), `GIF87a/89a`, `RIFF/WEBP`, or ISO-BMFF `MP4` (`ftyp`) magic signatures before forwarding any bytes to WebView2.
  - Actively detects and blocks embedded PHP tags (`<?php`, `<?=`), HTML/SVG script payloads (`<script`, `<html`, `<svg`), Windows PE executables (`MZ`), ELF binaries, and ZIP/PHAR archives (`PK\x03\x04`).
- **Strict URL Path & Double-Extension Filtering (`validate_safe_media_url`)**:
  - Enforces `SAFE_MEDIA_PATH_RE` and `FORBIDDEN_URL_TOKENS` across both `/posts.json` metadata ingestion and `/media` proxy requests, blocking `.php`, `.phtml`, `.phar`, `.exe`, `.bat`, `.ps1`, `.scr`, `.hta`, `.svg`, `.html`, path traversal (`..`), null bytes, and extension mismatches.
- **Forced Safe Response Headers, `nosniff`, & Strict CSP**:
  - Never trusts or forwards upstream `Content-Type` or `Content-Disposition` headers; derives `Content-Type` exclusively from verified binary magic bytes and forces `Content-Disposition: inline`, `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, and a locked-down `Content-Security-Policy`.
- **Hop-by-Hop Redirect Host Pinning & Stream Size Caps**:
  - Disabled unchecked automatic redirects in `HybridDoHSession` and enforced hop-by-hop redirect host validation against `ALLOWED_MEDIA_HOSTS` (`danbooru.donmai.us`, `cdn.donmai.us`).
  - Enforced a `25 MB` stream cap on static/animated images alongside the `15 MB` cap on MP4 videos, plus `--disable-file-system` WebView2 isolation flags.

---

## 🚀 v2.0.0 Core Architectural Foundation

- **Ephemeral Local `/media` Streaming Proxy & Hybrid HTTP/2 + Cloudflare DoH Transport (`HybridDoHSession`)**:
  - Routes all `<img>` and `<video>` traffic through `http://127.0.0.1:8088/media` using `curl_cffi` HTTP/2 Chrome TLS impersonation with automatic runtime fallback to `StdlibDoHSession` (`DoHSNIHTTPSConnection` over Cloudflare `1.1.1.1` DoH + TLS 1.3 SNI).
  - Encrypts Danbooru credentials at rest in `%APPDATA%\DanbooruWallpaper\config.json` via Windows DPAPI (`CryptProtectData`).
