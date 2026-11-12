# Changelog — v2.2.1 (High-Stress 36-Tile Masonry Protection, 1.0s Next Cooldown & Total System RAM Graph Scaling)

## 🛡️ v2.2.1 High-Stress Stability & Resource Graph Accuracy Updates

- **Fixed Application Freeze & ~50% GPU Spike Under Rapid `"Next"` Button Presses (Max 36-Tile Masonry)**:
  - **1.0-Second Internal `"Next"` / `"Previous"` Cooldown**: Added `NAV_BUTTON_COOLDOWN_SEC = 1.0` in `danbooru_service.py` (with visual cooldown feedback on the `◀` / `▶` buttons in `FloatingSearchBar`) and `MANUAL_NAV_COOLDOWN_MS = 1000` in `index.html` (`window.triggerNextMedia` / `window.triggerPreviousMedia`) to prevent rapid-fire click floods from queuing dozens of overlapping transitions per second.
  - **Single-Flight JS Evaluation Worker (`_js_eval_worker`)**: Replaced per-click `threading.Thread` spawning in `_async_evaluate_js` with a single-flight background queue worker so rapid UI actions never pile up concurrent threads contending on `pywebview`'s WinForms `Control.Invoke` semaphore.
  - **Strict Single-Flip Concurrency & Reflow Guard (`isAnyMasonryTileBusy`)**: Enforced `if (isAnyMasonryTileBusy()) return false;` in `triggerNextMasonryFlip()` and removed the `busyGroups` bypass (`if (eligible.length === 0 && forceIgnorePlayGuard)`) so rapid manual `"Next"` triggers never launch overlapping 3D GPU layers or recalculate BSP/Row geometry from mid-animation rects.
  - **Steady-State Preload Cap & Serialized Scratch-Canvas Downscaling**: Capped `readyImageQueue` in Masonry mode to `10` items once all `MASONRY_TILES` (`36`) are populated on screen (instead of holding 42 extra decoded media nodes in RAM/VRAM), and serialized `downscaleScratchCanvas` with `isDownscaleCanvasBusy` while deferring canvas downscaling during active flips.
- **Fixed Memory Resource Graph Scaling Against 100% Total Physical System RAM**:
  - Updated `ResourceGraphDialog` in `danbooru_service.py` (left-sidebar Memory mini sparkline, single `Memory` graph view, and `All Graphs (3x)` stacked view) to plot `self.monitor.ram_pct_history` against a fixed `0% – 100%` scale of total physical system memory (`total_phys_mb`) rather than a dynamic `4096 MB` ceiling—so `6.9%` (`2215.2 MB` / `32 GB`) displays at its true `6.9%` height on the graph.

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
