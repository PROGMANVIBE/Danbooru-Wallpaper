# Changelog

All notable changes to the **Danbooru Wallpaper Application** are documented in this file. Every version entry is organized into four standardized sections:
- **Summary**: A plain-language overview for non-technical users.
- **Add or Changed**: Features, settings, and behaviors that were added or updated.
- **Removed**: Legacy controls, behaviors, or unused components that were removed.
- **Technical**: Detailed engineering, root-cause, and implementation notes.

---

## v2.3.15 — Principal Systems, Concurrency, Rendering & Security Audit Remediation (12 Verified Findings Resolved)

### Summary
This update resolves 12 verified engineering audit findings across the Win32 desktop host, multi-monitor concurrency, HTTP media proxy, and WebView2 rendering engines. It prevents 64-bit window handle truncation when restoring the Settings window on duplicate launches, eliminates multi-threaded display hotplug race conditions, restores the Masonry Cardboard Box Loading Screen CSS rules, keeps Polaroid layouts and pause snapshots aligned when monitors resize, aborts in-flight GIF downloads immediately when paused, and hardens Cloudflare DoH DNS resolution and HTTP Range media verification.

### Add or Changed
- **64-Bit Safe Window Focus on Duplicate Launch**: Added explicit 64-bit Win32 `ctypes` type signatures to `user32.ShowWindow` and `user32.SetForegroundWindow` so duplicate `.exe` launches reliably restore and focus the Settings window even when Windows allocates high 64-bit `HWND` handles.
- **Thread-Safe Multi-Monitor Hotplug Synchronization**: Protected all display topology refreshes and background resyncs with dedicated re-entrant synchronization locks (`TOPOLOGY_LOCK` and `_RESYNC_LOCK`) so simultaneous manual **Resync Displays** clicks and background HDMI hotplug events never collide.
- **Restored Masonry Cardboard Box Loading Screen & Black Edge Fill Selector**: Added the `#masonryLoadingOverlay.active` and `#masonryLoadingOverlay.fade-out` CSS rules alongside the `#stage.masonry-black-mode` selector alias so the animated cardboard box loading screen displays and fades smoothly whenever Masonry mode initializes.
- **Polaroid Pause Z-Order & Live Viewport Resize Scaling**: Sorted Polaroid pause snapshots by ascending card creation order (`id`) so paused frames match live screen overlap, and added proportional viewport resize re-projection for live Polaroid stacks when monitor resolution or DPI changes.
- **Instant GIF Preload Cancellation on Pause**: Attached an `AbortController` to in-flight GIF `fetch()` requests and added pause state guards across GIF and "Previous" button media loaders so pausing a display immediately stops active downloads.
- **Validated Pre-Staged Masonry Reflow Plans**: Stamped pre-staged Masonry reflow plans with viewport dimensions, gap size, and layout mode so changing gap sliders or resizing a display mid-prestage cleanly falls back to an exact live layout calculation.
- **Exact HTTP Range Slicing & Mid-Stream Seek Verification**: Ensured small byte-0 HTTP Range probes return the exact requested byte range after 64-byte magic-byte verification, and verified unverified mid-stream MP4 Range seeks via a 64-byte preflight header check while returning true `206 Partial Content`.
- **Fail-Closed Cloudflare DoH Resolution & Session Thread Safety**: Hardened the standard-library TLS fallback (`DoHSNIHTTPSConnection`) to fail closed if Cloudflare DoH resolution cannot verify a public unicast IPv4 address, and guarded `HybridDoHSession` state transitions with an internal re-entrant lock.
- **Smarter Page-1 Tag Pool Retry & Polaroid Size Clamping**: Prevented empty Page-1 responses during transient Danbooru errors from skipping directly to Page 2, normalized legacy `scrolldirection` and `searchtags` values on startup, and automatically reconciled Polaroid `Min Size <= Max Size` inputs when saving settings.

### Removed
- **Unchecked OS DNS Fallback in Standard-Library DoH Transport**: Removed the fallback that allowed `DoHSNIHTTPSConnection.connect()` to dial raw hostnames via OS DNS if Cloudflare DoH resolution returned `None`.

### Technical
- **Root-Cause Audit & Fixes (`danbooru_service.py`, `index.html`)**:
  - **[CRITICAL-01] Missing 64-Bit `ctypes` Signatures on `user32.ShowWindow` & `user32.SetForegroundWindow` (`danbooru_service.py`)**: Declared `user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]` (`restype = wintypes.BOOL`) and `user32.SetForegroundWindow.argtypes = [wintypes.HWND]` (`restype = wintypes.BOOL`) so 64-bit `HWND` values above `0x7FFFFFFF` are never truncated to 32-bit `c_int`.
  - **[CRITICAL-02] Unsynchronized Multi-Thread Mutation of `CONNECTED_SCREENS` & Concurrent Resync Race (`danbooru_service.py`)**: Added `TOPOLOGY_LOCK = threading.RLock()`, `_RESYNC_LOCK = threading.Lock()`, and `get_connected_screens_snapshot()` to serialize `CONNECTED_SCREENS` reads/mutations and prevent overlapping `resync_all_displays_and_desktop()` calls across the watchdog, Tkinter UI, and tray threads.
  - **[CRITICAL-03] Missing `#masonryLoadingOverlay.active` & `.fade-out` CSS Rules (`index.html`)**: Defined `#masonryLoadingOverlay.active { display: flex; }`, `#masonryLoadingOverlay.fade-out { opacity: 0; transition: opacity 0.65s cubic-bezier(0.22, 1, 0.36, 1); }`, and `#stage.masonry-black-mode .masonry-flip-inner`.
  - **[HIGH-01] `/media` HTTP Range Byte-0 Over-Delivery & Unverified Mid-Stream Range Downgrade (`danbooru_service.py`)**: Sliced expanded byte-0 Range probes (`bytes=0-N` where `N < 63`) back to `N + 1` bytes with matching `Content-Range: bytes 0-N/total` and `Content-Length` headers after 64-byte magic-byte inspection, and added a 64-byte preflight magic-byte verification request for unverified `range_start > 0` seeks.
  - **[HIGH-02] Fail-Open OS DNS Fallback in `DoHSNIHTTPSConnection.connect` & `HybridDoHSession` Lock (`danbooru_service.py`)**: Raised ` OSError` when `resolve_hostname_doh()` returns `None` or a non-public IPv4 address, and guarded `HybridDoHSession` session recreation and `.using_curl` transitions with `self._lock = threading.RLock()`.
  - **[HIGH-03] In-Flight GIF `fetch()` Lack of `AbortController` & Missing Pause Guards (`index.html`)**: Added `AbortController` cancellation in `cleanupMediaNode()` and `APP_PAUSED || WALLPAPER_PAUSED` checks across all GIF preloader Promise and `onload` callbacks.
  - **[HIGH-04] Polaroid Freeze-Snapshot Z-Order Inversion & Missing Viewport Resize Live-Stack Re-Projection (`index.html`)**: Sorted `allItems` by ascending `item.id` in `renderFreezeSnapshot()` and proportionally scaled `targetX`/`targetY` and `startX`/`startY` of live Polaroid items in `performViewportResizeSync()`.
  - **[MEDIUM-01] Legacy `scrolldirection` / `searchtags` Normalization, Label Parity & Polaroid `minsize <= maxsize` UI Sync (`danbooru_service.py`)**: Extended `_normalize_project_dict_in_place()`, aligned `NUMERIC_SPECS` labels with `project.json`, and synced the `maxsize` widget variable when `minsize > maxsize` in `SettingsDialog.save_display_settings()`.
  - **[MEDIUM-02] `fill_tag_pool` Wrap-Around Retry Page-1 Skip on Transient Failure (`danbooru_service.py`)**: Added an empty-posts backoff guard on the wrap-around Page-1 retry so `pool["page"]` remains at `1` with exponential backoff.
  - **[MEDIUM-03] `createMediaElementFromDescriptor` Untracked Media Elements & Missing Pause Check (`index.html`)**: Registered "Previous" navigation media nodes in `inFlightMedia` and checked `APP_PAUSED || WALLPAPER_PAUSED` on load completion.
  - **[MEDIUM-04] Pre-Staged Masonry `reflowPlan` Missing Viewport & Gap Validation Stamp (`index.html`)**: Stamped `planSw`, `planSh`, `planGap`, and `planLayout` onto `reflowPlan` in `preStageNextMasonrySwitch()` and validated them in `reflowMasonryGroupWithFlip()`.
  - **[LOW-01] & [LOW-02] Tkinter Timer Cleanup, Masonry Header Copy & PDH Handle Finalizer (`danbooru_service.py`)**: Cancelled `_nav_cooldown_job` and `_tag_flash_job` in `SettingsDialog.close_dialog()`, updated the Masonry section header to `"MASONRY LAYOUT SETTINGS (UNCROPPED 2D SCALEX FLIP & REFLOW)"`, and added `__del__` / `<Destroy>` cleanup for `AppResourceMonitor.close()`.

---

## v2.3.14 — PyInstaller Single-Instance Enforcement, Duplicate-Launch Settings Handoff & Exclusive Port Binding

### Summary
This update fixes a bug where double-clicking or launching `DanbooruWallpaper.exe` while the application was already running in the Windows system tray spawned duplicate instances, multiple tray icons, and competing background processes. Now, only a single instance of the application can run at a time—and launching the `.exe` again while it is already running automatically brings the existing **Application Settings** window to the front of your screen and exits the duplicate launch cleanly.

### Add or Changed
- **Single-Instance Protection for PyInstaller `.exe`**: Prevented duplicate launches of `DanbooruWallpaper.exe` from spawning extra system tray icons or duplicate wallpaper processes, even during rapid double-clicks at startup.
- **Automatic Settings Window Focus on Second Launch**: Launching `DanbooruWallpaper.exe` while the application is already running in the system tray now signals the running instance to immediately open and focus the **Application Settings** window before closing the duplicate launch.
- **Exclusive Local Server Port Binding (`127.0.0.1:8088`)**: Hardened the local media proxy server socket on Windows so another process can never bind over port `8088` while the app is running, while preserving 100% of multi-monitor shared tag pool deduplication (`TAG_POOLS`).

### Removed
- **Permissive Windows `SO_REUSEADDR` Server Socket Flag**: Disabled `allow_reuse_address = True` on Windows so a secondary OS process cannot hijack or share the listening TCP port `127.0.0.1:8088`.

### Technical
- **Root-Cause Audit & Fixes (`danbooru_service.py`)**:
  - **Pre-Import Win32 Named Mutex (`enforce_single_instance_or_exit`, `_SINGLE_INSTANCE_MUTEX_HANDLE`)**: Previously, `danbooru_service.py` performed ~400–900ms of heavy third-party imports (`webview`, `curl_cffi`, `pystray`, `PIL`, `tkinter`) with no kernel mutex check at the top of the entry script. Added `enforce_single_instance_or_exit()` at the top of `danbooru_service.py` (immediately after `import os, sys, ctypes`) using `ctypes.WinDLL("kernel32", use_last_error=True)` and `CreateMutexW(None, False, "Local\\DanbooruWallpaper_SingleInstance_Mutex_v1")` with explicit 64-bit `.argtypes` and `.restype`.
  - **PyInstaller `--onefile` Bootloader Immunity & Handle Retention**: Using a Win32 Named Mutex acquired strictly inside the Python runtime avoids the PyInstaller `--onefile` parent/child bootloader trap (where the C bootloader parent and unpacked Python child share the exact same `DanbooruWallpaper.exe` process name). Retaining `_SINGLE_INSTANCE_MUTEX_HANDLE` and `_SINGLE_INSTANCE_EVENT_HANDLE` in module-level globals prevents Python garbage collection from prematurely closing the kernel handles, and `ctypes.get_last_error() == ERROR_ALREADY_EXISTS (183)` is checked immediately after `CreateMutexW`.
  - **Kernel Named Event + Local Loopback UX Handoff (`_signal_existing_instance_to_show_settings`, `single_instance_signal_worker_loop`, `_bring_tk_window_to_win32_foreground`)**: When a duplicate launch detects `ERROR_ALREADY_EXISTS (183)` (or `ERROR_ACCESS_DENIED (5)`), it signals the auto-reset Win32 Named Event `"Local\\DanbooruWallpaper_ShowSettings_Event_v1"` via `OpenEventW`/`SetEvent` (which works even during cold-start double-clicks before port `8088` is bound), sends a 0.35s fallback loopback request to `GET http://127.0.0.1:8088/show_settings`, closes its handle, and terminates immediately via `os._exit(0)`. The primary instance's `single_instance_signal_worker_loop` daemon thread wakes on `WaitForSingleObject` and schedules `TK_ROOT.after(0, open_settings_dialog_window)`, using `user32.SetForegroundWindow` and `SW_RESTORE` to elevate the Settings window above Windows Explorer.
  - **Windows `SO_EXCLUSIVEADDRUSE` Port Hardening (`ReusableThreadingHTTPServer.server_bind`)**: On Windows, `SO_REUSEADDR` (`allow_reuse_address = True`) allows multiple distinct processes to bind to `127.0.0.1:8088` simultaneously without raising `WSAEADDRINUSE`. Changed `allow_reuse_address = (os.name != "nt")` and applied `socket.SO_EXCLUSIVEADDRUSE` in `server_bind()` on Windows. Multi-monitor shared tag pool deduplication (`TAG_POOLS`) is completely unaffected because all monitors (`screen_1`, `screen_2`, etc.) run inside the single primary process and connect as concurrent HTTP clients to the single `ThreadingHTTPServer`.

---

## v2.3.13 — Removed Slideshow and Masonry Bottom Settings Description Lines

### Summary
This update cleans up the bottom of the **Display** settings tab by removing the multi-line helper description notes underneath the **Slideshow** and **Masonry** display mode settings.

### Add or Changed
- **Streamlined Slideshow & Masonry Display Settings Layout**: Kept the **Slideshow** and **Masonry** mode sections compact and uncluttered above the **"Save & Apply Display Settings"** button.

### Removed
- **Slideshow Settings Description Text**: Removed the 2-line bulleted description text (`slide_note`) at the bottom of the **Slideshow** settings section.
- **Masonry Settings Description Text**: Removed the 3-line bulleted description text (`masonry_note`) at the bottom of the **Masonry** settings section.

### Technical
- **Settings UI Cleanup (`danbooru_service.py`)**:
  - Removed the `slide_note` (`tk.Label`) widget from `self.slideshow_section_frame` and `self._themed_labels_muted` in `SettingsDialog._build_display_tab()`.
  - Removed the `masonry_note` (`tk.Label`) widget from `self.masonry_section_frame` and `self._themed_labels_muted` in `SettingsDialog._build_display_tab()`.
  - Removed `slide_note` and `masonry_note` from the click-outside `<Button-1>` focus-release binding tuple (`_defocus_tag_input_on_outside_click`).

---

## v2.3.12 — Win32 HDMI Hotplug Hardening, Desktop Icon Scale Protection, Glass-Pane Coexistence & Automatic Desktop Recovery Watchdog

### Summary
This update fixes a critical Windows 11 24H2+ multi-monitor issue where turning an HDMI TV (third screen) on or off while the wallpaper is running could cause the wallpaper to tile across the screen like Windows Task View, fail to update monitor coordinates, or cause all desktop icons to suddenly grow in size. The application now detects HDMI display connections and disconnections automatically in the background, protects your desktop icon size during high-DPI TV transitions, coexists cleanly with companion desktop overlay tools like Glass-Pane, and adds a one-click **"Resync Displays"** button in both the Settings window and the System Tray menu.

### Add or Changed
- **Automatic HDMI TV & Display Hotplug Recovery**: Turning an HDMI TV or secondary monitor on or off while the app is running now automatically updates all monitor positions, creates or hides the TV's wallpaper surface as needed, and keeps remaining monitors playing smoothly without restarting the app.
- **Fixed "Task View" Tiled Viewport Glitch**: Prevented Windows DPI auto-scaling and disconnected TV windows from shrinking or tiling wallpaper viewports across your remaining monitors when displays turn on or off.
- **Desktop Icon Size Protection**: Prevented Windows Explorer from enlarging your desktop icons when connecting or disconnecting a high-DPI 4K HDMI TV while the wallpaper is attached to the desktop.
- **Manual "Resync Displays" Button in Settings & System Tray**: Added a **Resync Displays** button next to the **Select Screen** dropdown in the **Display** tab and in the right-click System Tray menu for instant on-demand display and desktop Z-order recovery.
- **Live Screen Selector Dropdown Refresh**: If the Application Settings window is open when you turn an HDMI TV or monitor on or off, the **Select Screen** dropdown updates automatically.
- **Glass-Pane & Window Snap Isolation**: Configured wallpaper windows as strictly passive, click-through surfaces so Windows 11 Snap Assist, Task View, and companion utilities such as **Glass-Pane** (`PROGMANVIBE/Glass-Pane`) never snap, resize, or false-pause the wallpaper.

### Removed
- **Repeated `0x052C` Progman Broadcasts**: Stopped sending repeated `0x052C` initialization messages to `Progman` on every geometry sync once the desktop `WorkerW` layer is already active.
- **Orphaned Disconnected Monitor Windows**: Stopped leaving disconnected monitors' wallpaper windows visible inside `Progman` when a display is powered off.
- **Browser Pinch & Ctrl+Wheel Zoom inside Wallpaper Surfaces**: Disabled Chromium pinch-zoom (`--disable-pinch`) and blocked `Ctrl+Wheel` / `Ctrl++/-` zoom shortcuts inside the WebView2 renderer.

### Technical
- **Root-Cause Fixes (`danbooru_service.py`, `index.html`)**:
  - **Conditional One-Time `0x052C` Topology Resolution (`_probe_existing_desktop_topology`, `enumerate_desktop_topology`)**: Separated non-destructive `Progman` / `WorkerW` inspection (`_probe_existing_desktop_topology()`) from `0x052C` broadcasting. `0x052C` (`wParam=0, lParam=0` and `wParam=0xD, lParam=0x1`) is now sent only when no valid `WorkerW` exists yet (initial launch or after an `explorer.exe` restart), preventing `explorer.exe` from resetting `SHELLDLL_DefView` icon metrics or detaching sibling `Progman` overlays during runtime syncs.
  - **Desktop Icon Spacing & View Mode Guard (`find_desktop_listview_hwnd`, `capture_desktop_icon_metrics`, `restore_desktop_icon_metrics_if_inflated`)**: Snapshots baseline `LVM_GETVIEW` and `LVM_GETITEMSPACING` metrics from `SHELLDLL_DefView` -> `SysListView32` before attachment and automatically restores them via `LVM_SETVIEW` and `LVM_SETICONSPACING` if an HDMI TV DPI transition inflates desktop icon spacing.
  - **Collision-Free Two-Pass Monitor ID Registry (`_KNOWN_DEVICE_TO_SCREEN_ID`, `refresh_connected_screens_preserving_ids`)**: Fixed a bug where connecting a new monitor whose sort order preceded an existing monitor could assign duplicate `screen_id` values (`two "screen_2"` entries). Implemented a persistent `_KNOWN_DEVICE_TO_SCREEN_ID` registry with a two-pass assignment that preserves existing `screen_id` bindings across power-off/on cycles and assigns strictly collision-free `screen_{n}` IDs to newly connected HDMI displays.
  - **Disconnected Monitor Hiding & `disconnected_paused` State (`sync_all_screens_z_order_and_geometry`, `is_screen_effectively_paused`)**: Fixed a bug where `if not hwnd or sid not in screens_by_id: continue` skipped disconnected monitors' HWNDs when an HDMI TV was powered off, leaving the disconnected TV's `WS_VISIBLE` child window clamped onto remaining monitors inside `Progman`. Disconnected screen HWNDs are now immediately hidden (`~WS_VISIBLE`, `SWP_HIDEWINDOW`) and marked `disconnected_paused = True` to halt their WebView2 render loops and tag-pool workers until reconnected.
  - **Passive Click-Through Window Styles & Glass-Pane Coexistence (`_apply_passive_wallpaper_window_styles`, `detect_fullscreen_monitors`)**: Applied `user32.EnableWindow(hwnd, False)` (`WS_DISABLED`) and `WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE | WS_EX_TRANSPARENT` to all wallpaper host HWNDs (and disabled hit-testing on child `WindowsForms10.*` / `Chrome_WidgetWin_*` containers), and added `GlassPane` / `Glass-Pane` class and title exclusions to `detect_fullscreen_monitors()`.
  - **Background Display Hotplug & Self-Healing Watchdog (`get_display_topology_signature`, `resync_all_displays_and_desktop`, `verify_and_heal_desktop_hwnds`, `ensure_webview_windows_for_connected_screens`)**: Extended `fullscreen_monitor_worker_loop()` to poll virtual screen bounds (`SM_XVIRTUALSCREEN`, `SM_YVIRTUALSCREEN`, `SM_CXVIRTUALSCREEN`, `SM_CYVIRTUALSCREEN`) and `EnumDisplayMonitors` every `0.75s` (with a 2-tick EDID/DPI settle debounce), dynamically provisioning `pywebview` windows for newly connected monitors and verifying `GetParent(hwnd)` and `GetWindowRect(hwnd)` every `2.25s` to self-heal WinForms DPI auto-scaling drift.
  - **Debounced Viewport Resize & Zoom Guard (`index.html`)**: Added `120ms` resize debouncing (`performViewportResizeSync()`) and `window.forceViewportResync()` alongside `wheel` (`e.ctrlKey`) and `keydown` zoom blockers.

---

## v2.3.11 — Principal Systems, Concurrency, Rendering & Security Audit Fixes (13 Verified Issues Resolved)

### Summary
This update is a comprehensive stability, security, and quality-of-life release that resolves 13 behind-the-scenes issues. It prevents the app from freezing when resizing or dragging sliders across multiple monitors, stops the wallpaper from accidentally pausing when you maximize normal desktop apps with an auto-hidden Windows taskbar, keeps your monitor settings tied to the right physical screens even after unplugging or reconnecting displays, and ensures smooth decimal slider adjustments and accurate GPU usage readings on dual-graphics-card PCs.

### Add or Changed
- **Eliminated Cross-Monitor Flicker & Freezes**: Updating settings on one screen no longer causes other connected monitors to briefly flicker or lock up the Settings window.
- **Smarter Fullscreen App Detection**: Maximized desktop apps (such as web browsers or Discord) on monitors with an auto-hidden Windows taskbar no longer falsely trigger the "Pause during full screen application" feature, while true fullscreen games and F11 fullscreen videos continue to pause the wallpaper automatically.
- **Reliable Multi-Monitor Slider Adjustments**: Dragging settings sliders rapidly across multi-monitor setups no longer drops "Pause", "Next", or "Previous" commands.
- **Persistent Monitor Assignments**: Unplugging, reconnecting, or waking monitors now keeps your saved wallpaper settings matched to the exact same physical display.
- **Accurate Dual-GPU Performance Readings**: Computers with both integrated graphics (iGPU) and a dedicated graphics card (dGPU) now display accurate GPU usage percentages in the Resource Graph without adding separate adapters together.
- **Preserved Artist Names in Scroll Mode**: Scrolling wallpaper items now retain artist name metadata across all queue and buffer paths.
- **Smooth Decimal Slider Saving**: Decimal values on speed and fade sliders (`Scroll Speed`, `Slideshow Fade`, and `Drop Speed`) are now saved at their exact decimal precision instead of rounding to whole numbers.
- **Improved Resource Graph Window Placement**: Opening the Resource Graph window now centers it neatly over the open Application Settings window instead of the top-left corner of your monitor.
- **Hardened Media Streaming & Login Privacy**: Video and image streams now validate file size limits and file signatures across partial downloads and redirects, and your Danbooru login credentials are never sent to public image CDN servers.

### Removed
- **Blocking Cross-Thread Window Resize Calls**: Removed synchronous cross-thread `SendMessageW(WM_SIZE)` calls that could freeze the interface under heavy multi-monitor activity.
- **CDN Credential Forwarding**: Removed HTTP Basic Authentication credential forwarding to public `cdn.donmai.us` media servers so credentials are strictly limited to `danbooru.donmai.us` API calls.
- **Redundant Multi-Monitor Geometry Nudges**: Removed full-screen geometry nudges on unaffected monitors when syncing a single target screen.

### Technical
- **Critical Fixes (`danbooru_service.py`, `index.html`)**:
  - **Cross-Thread Win32 `SendMessageTimeoutW(WM_SIZE)` Deadlock Prevention (`danbooru_service.py`)**: Replaced blocking `user32.SendMessageW(hwnd, WM_SIZE, ...)` on the top-level WebView2 window inside `resize_webview_child_containers()` with bounded `user32.SendMessageTimeoutW(..., SMTO_NORMAL, 150, ...)` so holding `INJECTION_LOCK` on a background worker can never deadlock against the GUI thread during synchronous WebView2 or `evaluate_js` calls.
  - **HTTP Range Continuation Magic-Byte Verification, Byte-0 Probe Promotion & `Content-Range` Total Size Enforcement (`danbooru_service.py`)**: Hardened `/media` Range parsing (`re.match(r"^bytes=(\d+)-(\d*)$", client_range)`) so zero-offset probes smaller than 64 bytes (`bytes=0-0` / `bytes=0-1`) are transparently promoted to `bytes=0-65535` (preventing false HTTP 415 rejections on `< 8` byte responses), `mark_mp4_url_verified(target_url)` is strictly gated on `range_start == 0 and len(first_chunk) >= 32`, `is_range_cont` requires `range_start > 0`, and `Content-Range` total resource size (`/\d+$`) is validated against `max_allowed_bytes` (15 MB for MP4, 25 MB for images).
  - **Scratch-Canvas Downscale Generation/Pause Abort Guard (`index.html`)**: Added early entry guards (`!inFlightMedia.has(...) || gen !== preloadGeneration || APP_PAUSED || WALLPAPER_PAUSED || !SCREEN_ENABLED`) to `img.onload`, `downscaleScratchCanvas.toBlob()`, and `scaledImg.onload` inside `pumpPreloader()` so paused or cancelled preloads never touch `downscaleScratchCanvas` or allocate orphaned Blob URLs.
- **High-Severity Fixes (`danbooru_service.py`)**:
  - **Expanded & Coalesced `_JS_EVAL_QUEUE` (`maxlen=128`) (`danbooru_service.py`)**: Increased `_JS_EVAL_QUEUE` capacity from `16` to `128` and coalesced consecutive identical `(win, js_code)` entries in `_async_evaluate_js()` so rapid slider drags across multi-monitor setups never evict critical `applyPauseStates` or `trigger Wallpaper Next/Previous` commands.
  - **Targeted `sync_all_screens_z_order_and_geometry()` (`danbooru_service.py`)**: Scoped the 1-pixel frame nudge (`screen_w - 1, screen_h - 1`), `SWP_FRAMECHANGED`, `resize_webview_child_containers()`, and `RDW_INVALIDATE | RDW_ALLCHILDREN` strictly to `target_screen_id` (or newly enabled screens), updating unaffected screens with a lightweight Z-order-only `SetWindowPos(..., SWP_NOACTIVATE | SWP_ASYNCWINDOWPOS)` to eliminate cross-monitor flicker.
  - **Fullscreen Detector Auto-Hidden Taskbar & Captioned Window Accuracy (`danbooru_service.py`)**: Refined `detect_fullscreen_monitors()` (`has_full_caption` and `is_maximized_desktop_win`) so maximized Chromium/Electron desktop windows on monitors with an auto-hidden Windows taskbar and non-maximized captioned windows filling the monitor do not trigger false-positive fullscreen auto-pauses, while true borderless fullscreen games and F11 browsers are accurately detected.
  - **Host-Scoped Basic Auth & Thread-Safe Per-Request Headers in `HybridDoHSession` & `StdlibDoHSession` (`danbooru_service.py`)**: Restricted HTTP Basic Auth credentials (`USERNAME`, `API_KEY`) strictly to `danbooru.donmai.us` (never forwarding `Authorization: Basic ...` headers to public `cdn.donmai.us` media nodes) and passed `headers=merged_req_headers` and `auth=req_auth` per request without mutating shared session state across threads.
- **Medium & Low-Severity Fixes (`danbooru_service.py`, `index.html`)**:
  - **Multi-GPU Adapter LUID Bucketing in `_query_pdh_gpu_utilization()` (`danbooru_service.py`)**: Included the physical GPU adapter prefix (`luid_0x..._phys_\d+`) in PDH engine keys so dual-GPU (iGPU + dGPU) systems aggregate engine utilization per adapter rather than summing across distinct GPUs.
  - **Redirect Hop Path Token Validation (`danbooru_service.py`)**: Added `FORBIDDEN_URL_TOKENS` path/query validation to every redirect hop in both `SafeDoHRedirectHandler.redirect_request()` and `HybridDoHSession.get()`.
  - **Persistent `screen_id` Mapping Across Monitor Re-Enumeration (`danbooru_service.py`)**: Added `"device"` to `enumerate_connected_monitors()` and `refresh_connected_screens_preserving_ids()` so opening `SettingsDialog` preserves existing `screen_id` bindings by Win32 device name.
  - **Scroll Mode `artistTags` Preservation (`index.html`)**: Added `artistTags: ready.artistTags` to all 8 `activeItems` entries in `spawnImmediateScrollNextItem()` and `fillScrollBuffer()` so Polaroid-style artist metadata stays intact across scroll items.
  - **Fractional Slider Precision Preservation (`danbooru_service.py`)**: Updated `_coerce_and_clamp_props_dict()` to honor `schema.get("precision")` and float `step` metadata so fractional values on `scrollspeed`, `slideshowfade`, and `dropspeed` are not rounded to integers when their default value is an `int`.
  - **`ResourceGraphDialog` Window Anchoring (`danbooru_service.py`)**: Anchored `ResourceGraphDialog` to the open `SettingsDialog` coordinates (`SETTINGS_DIALOG_INSTANCE`) instead of the withdrawn `TK_ROOT` `(0, 0)` corner.

---

## v2.3.10 — Optimized Mondrian & Row Tree Solvers (Audited & Hardened), Pause Background Process Suspension, Fullscreen App Auto-Pause & Single-Row Masonry Buttons

### Summary
This update makes the Masonry grid layout significantly faster and eliminates visual glitches like black empty spaces, overlapping images, or old images peeking through gaps after turning a screen off and back on. It also adds a new per-screen switch that automatically pauses your wallpaper whenever you play a fullscreen game or watch a fullscreen video, completely stops background downloads and CPU/GPU work while a screen is paused, and streamlines the Masonry settings buttons so the bottom Save button always fits comfortably.

### Add or Changed
- **Faster, Glitch-Free Masonry Grid Layouts**: Upgraded both the `Mondrian` and `Rows` grid engines so tile arrangements calculate 6–10× faster and never leave black empty holes, squished tiles on portrait monitors, or stuck overlapping images.
- **Clean Display Turn-Off & Turn-On**: Turning a screen off and back on now completely clears all old images so frozen tiles never peek through the gaps behind the new grid.
- **True Zero-Resource Pause Mode**: Pausing a screen now completely halts background image downloads, video decoding, image resizing, and animations for that screen until you unpause it.
- **"Pause during full screen application" Switch**: Added a new on/off switch next to "Display wallpaper on this screen" that automatically pauses the wallpaper on a monitor whenever a fullscreen game or video player is active on that monitor, and resumes when you exit fullscreen.
- **Combined Single-Row Masonry Buttons**: Placed the `Masonry Layout: Mondrian / Rows` and `Edge Fill: Blur / Black` buttons side-by-side on a single row to save vertical space.
- **Taller Application Settings Window**: Increased the Settings window height from `700px` to `760px` so the bottom `"Save & Apply Display Settings"` button is never cramped.

### Removed
- **Separate Edge Fill Settings Row**: Removed the separate second row for the `Edge Fill` button in the Masonry settings panel and consolidated both buttons into a single 2-column row.
- **Paused Background Activity**: Removed background tag-pool prefetching, media preloading, and video decoding on paused displays.
- **Unbalanced Portrait Caterpillar Layouts**: Removed the unbalanced `'caterpillar'` layout tree option when displaying 7 or more Masonry groups, which previously crushed tiles on vertical monitors.

### Technical
- **Optimized Mondrian & Row Tree Solvers + Full Masonry Tree Logic Audit (`index.html`)**:
  - **Rows Solver (`solveOptimalRowsPartitionForAspects`)**:
    - **Bounded LRU Memoization**: Added `ROWS_SOLVER_CACHE` (64 entries) keyed by quantized aspect ratios, viewport dimensions, and gap so repeated layout checks return in $O(1)$.
    - **Candidate Permutation Deduplication**: Deduplicated the 5 candidate tile permutations per row count $R$ by quantized aspect-ratio signature so identical permutations are never solved twice.
    - **Incremental Two-Row Delta Math**: Replaced full-bucket cloning (`b.slice()`), array `splice()`, and $O(R + N)$ `evaluateBuckets()` inside the 4-pass pairwise swap/move refinement loop with $O(1)$ incremental two-row delta math (`rowCostFromSumAspect()`), computing exact height/variance deltas from `rowSums[r1]` and `rowSums[r2]` and mutating only when a strictly improving swap or move is committed.
    - **Pairwise Swap Variable Refresh & Bijection Guard (`isValidIndexPermutation`)**: Fixed a bug in the pairwise swap loop where `u = b1[i1]` and `aU = clamped[u]` were hoisted outside the `i2` loop without refreshing `u = v; aU = aV;` after an improving swap. Previously, if a second `i2` improved on the same `i1`, `b1[i1] = v` overwrote the first swapped tile (dropping it from `masonryTileList` while leaving its `<div class="masonry-tile">` orphaned on `#stage`) and duplicated the original `u` across two slots (creating empty `#0b0b0d` black voids where the shared DOM node could only occupy the second slot's transform). Added `isValidIndexPermutation(indices, n)` validation across `solveOptimalRowsPartitionForAspects`, `buildGooglePhotosJustifiedLayout`, and `precomputeGroupReflowPlan`.
  - **Mondrian BSP Tree Solver (`solveAspectLockedSubtree`, `buildSubtreeWithFixedMaskAndTopology`, `solveGlobalMondrianPlanForProxies`, `reflowMasonryGroupWithFlip`)**:
    - **Subtree LRU Memoization**: Added `MONDRIAN_SUBTREE_CACHE` (256 entries) keyed by quantized leaf aspects, group box aspect, and gap ratios, with permutation bijection validation (`isValidIndexPermutation`) on cache hit/miss.
    - **Flat Post-Order Evaluation & Branch-and-Bound Pruning**: Replaced per-bitmask recursive tree allocations (`buildTree()`), recursive `computeRatio()`, and recursive `assignRects()` across split-direction bitmasks with a flat post-order array (`propagateAspectPostOrder()`) and branch-and-bound early pruning (`evaluateSubtreeDistortion(..., bestScore)`).
    - **Full Bitmask Search for 7–10 Top-Level Groups (`numInternals <= 9`) & Degenerate `'caterpillar'` Prevention**: Extended exact bitmask search from `numInternals <= 5` (`<= 6` groups) up to `numInternals <= 9` (`<= 10` groups, covering up to 36 tiles) and restricted `topologies` to `['balanced']` for `n >= 7`. Fixed the `numInternals > 5` fallback where `break;` only exited the inner `o` loop without updating `bestScore`, which had allowed `tIdx = 1` (`'caterpillar'`) to overwrite `bestRoot` and assign 85%–90% of a portrait display to Group 0 while crushing the remaining 7–8 groups (31 tiles) into the bottom 15% of the screen.
    - **Exact Topology & Bitmask Subtree Reconstruction (`buildSubtreeWithFixedMaskAndTopology`)**: Stored `winTopology` and `topWinMask`/`topWinTopology` alongside `winMask` on all local and global reflow plans and reconstructed `group.subtreeRoot` and `masonryTreeRoot` directly via `buildSubtreeWithFixedMaskAndTopology()` instead of re-invoking `solveAspectLockedSubtree(..., false)` (which searched all topologies and could pick a different topology than `plannedRects`).
    - **Pre-Stage / Mid-Flip Population Race & Global Plan Atomicity**: Prevented `finalizePreloadedMedia()` and `populateMasonryIfNeeded()` from mutating `masonryTileList` or rebuilding the grid while a flip or pre-stage is active, stabilized `getDesiredMasonryTileCount(allowSteadyStateChange = false)` during steady-state playback, and validated 1-to-1 tile ID membership in `reflowMasonryGroupWithFlip()` *before* mutating `t.groupIndex`.
    - **Defensive `#stage` DOM Sweep on Display Off/On (`clearStageAll`, `setScreenEnabled`, `destroyItem`)**: Updated `clearStageAll()` and `setScreenEnabled(false/true)` to abort in-flight fetches, clear `postQueue`, clean up `tile.activePreStage.stagedMediaEl`, and sweep all residual child nodes from `#stage` so zero orphaned tiles can ever remain frozen behind the Masonry grid and peek through `MASONRY_GAP` when turning a display off and back on.
- **Stop Unneeded Background Processes When Paused (`danbooru_service.py`, `index.html`)**:
  - **Backend (`danbooru_service.py`)**: Added `is_screen_effectively_paused(screen_id)` combining manual `"paused"` and `"fullscreen_paused"`. Paused screens are excluded from `is_any_enabled_screen_using_pool()`, `ensure_screen_tag_pool_populated_async()`, `ensure_all_enabled_screen_pools_populated()`, and `/api` background buffer replenishment (`fill_post_buffer()`), halting background network/CPU activity when no unpaused screen uses that pool. Resuming a screen immediately triggers `ensure_screen_tag_pool_populated_async(screen_id)`.
  - **Frontend (`index.html`)**: Added `suspendBackgroundProcessesForPause()` and `setActiveWaapiAnimationsPaused(paused)` inside `window.applyPauseStates()`. Pausing a display immediately aborts in-flight `/api` fetches (`apiFetchAbortController.abort()`), increments `preloadCancelEpoch` to cancel in-flight image/video preloads and scratch-canvas bitmap downscales, releases pre-staged Masonry elements (`tile.nextElement`), pauses all `<video>` decoders, pauses active WAAPI animations, and blocks `fetchNextPage()` and `pumpPreloader()` until unpaused.
- **Per-Screen `"Pause during full screen application"` Switch & Win32 Fullscreen Monitor Detector (`danbooru_service.py`, `project.json`)**:
  - **Schema & Defaults**: Added `"pausefullscreen"` (`bool`, default `True`, `"text": "Pause during full screen application"`) to `project.json` and `get_default_properties_dict()`.
  - **Display Tab UI Switch**: Added `self.fullscreen_pause_wrap` (`self.fullscreen_pause_switch` pill switch + `"Pause during full screen application"` label) on the right side of the same row (`enable_row`) as `"Display wallpaper on this screen"` in the Display tab.
  - **Win32 Monitor Worker Loop**: Added `detect_fullscreen_monitors()` and `fullscreen_monitor_worker_loop()` using 64-bit safe Win32 `ctypes` (`GetForegroundWindow`, `IsIconic`, `DwmGetWindowAttribute(DWMWA_CLOAKED)`, `GetWindowRect`, and `MonitorFromWindow`) to detect fullscreen games or video players per monitor every `0.75s` and automatically pause/resume the wallpaper on that screen.
- **Increased Application Settings Window Height & Combined Masonry Row (`danbooru_service.py`, `project.json`)**:
  - **Settings Window Height**: Increased the base `SettingsDialog` window height from `700px` to `760px` (`min(760, max(700, sh - 40))`) in `__init__()` and `_update_tag_input_height()`.
  - **Single-Row Toggle Buttons**: Placed both Masonry toggle buttons side-by-side on a single 2-column row (`self.masonry_layout_row`): `"Masonry Layout: Mondrian"` ↔ `"Masonry Layout: Rows"` and `"Edge Fill: Blur"` ↔ `"Edge Fill: Black"`.

---

## v2.3.8 — Masonry Mid-Flip Vertical Line Fix, Immediate Polaroid Canvas Baking & Cardboard Box Loading Screen

### Summary
This update fixes a visual bug in Masonry mode where flipping tiles could occasionally get stuck as a thin vertical slit, reduces memory usage in Polaroid mode by merging landed photo cards directly into the background image, and introduces an animated brown cardboard box loading screen that opens and fades smoothly into your complete Masonry wall instead of popping tiles in one at a time.

### Add or Changed
- **Fixed Masonry Tiles Stuck as Thin Vertical Lines**: Resolved an animation issue where a flipping Masonry tile could remain squished into a thin vertical line after flipping to a new image or video.
- **Immediate Polaroid Background Flattening**: Landed non-animated Polaroid photos are now immediately merged into the background canvas once they land (unless sitting on top of a moving video/GIF Polaroid), freeing up memory and keeping animations smooth.
- **Animated Cardboard Box Loading Screen for Masonry Mode**: Switching to or turning on Masonry mode now displays the Danbooru brown cardboard box on a clean black background while your initial batch of images prepares. Once ready, the box flaps fold open with a warm glow and fade smoothly into the finished Masonry grid all at once.

### Removed
- **Incremental One-by-One Masonry Tile Pop-In**: Removed one-by-one stuttery tile mounting when initially loading the Masonry grid.
- **30-Card Static Polaroid DOM Retention**: Removed the 30-card live DOM buffer for static landed Polaroid cards, lowered the live animated card cap from `30` to `10`, and reduced the covered-card grace period from `4` drops to `2`.

### Technical
- **Masonry Mid-Flip Stuck / Slim Vertical Line Bug Fix (`index.html`)**:
  - **Root Cause Fixed**: In `launchTileFlipPhase1()`, Phase 1's Web Animations API (`element.animate()`) animation `anim1` (`scaleX(1) -> scaleX(0.01)`) was configured with `fill: 'forwards'`, and `anim1.onfinish` set `chosenTile.flipAnim = null` *before* calling `executeMasonryFlipMidpoint(chosenTile)`. Consequently, `cancelTileFlipAnimation(tile)` inside `executeMasonryFlipMidpoint()` saw `tile.flipAnim === null` and never called `anim1.cancel()`. When Phase 2's `anim2` (`scaleX(0.01) -> scaleX(1)`, `fill: 'none'`) completed 0.24s later, the tile's `.masonry-flip-inner` immediately snapped back to `anim1`'s uncancelled `fill: 'forwards'` state (`transform: scaleX(0.01)`) in the WAAPI animation cascade—leaving the tile permanently compressed into a slim vertical line surrounded by black space while the newly swapped `<video>` or animated GIF continued playing inside the slit.
  - **Inline Midpoint Transform & `fill: 'none'`**: Switched `anim1` in `launchTileFlipPhase1()` from `fill: 'forwards'` to `fill: 'none'` (using inline `chosenTile.flipInner.style.transform = 'scaleX(0.01)'` during Phase 1 and resetting `tile.flipInner.style.transform = ''` in `executeMasonryFlipMidpoint()`).
  - **Explicit WAAPI Animation Cancellation**: Updated `cancelTileFlipAnimation(tile)` and `cancelTileReflowAnimation(tile)` to explicitly cancel both the stored reference (`tile.flipAnim` / `tile.reflowAnim`) and all active element animations via `getAnimations()`, and invoked `cancelTileFlipAnimation()` at the start of `executeMasonryFlipMidpoint()` and `finishMasonryTileFlip()`.
  - **Elapsed-Time Watchdog Recovery**: Added elapsed-time watchdog recovery in `updateMasonryMode()` for both `tile.isFlipping` and `tile.isReflowing` so a delayed or interrupted WAAPI callback can never leave a tile stuck.
- **Polaroid Backing Canvas Verification & Immediate Static Card Baking (`index.html`)**:
  - **Root Cause Fixed**: Previously, `MAX_LIVE_POLAROID_DOM = 30` kept the first 30 landed static Polaroids alive in `#stage` as full DOM subtrees (`<div class="polaroid-item">`, `<img>`, caption `<span>`s, and Blob URLs) without baking any of them into `#polaroidBaseCanvas` until the stack exceeded 30 cards or a card had 100% of its `coverageGrid` cells covered for 4 consecutive drops. In addition, `finishFallingPolaroidItem()` did not call `markCoverageForLandedItem(item)` upon landing or sort `pendingPolaroidBakes` by ascending `zIndex`.
  - **Rotated Bounding-Box Overlap Check & Immediate Static Bake**: Added `doPolaroidsOverlap(a, b)` (using rotated bounding-box extents) and updated `prunePolaroidStackIfNeeded()` so every landed static Polaroid (`!item.isAnimated`) that does not overlap an older live animated Polaroid below it is immediately queued into `pendingPolaroidBakes`, baked onto `#polaroidBaseCanvas`, and its DOM node + Blob URL freed via `destroyItem()`.
  - **Tightened Live Animated DOM Caps & Ascending Z-Index Bake Order**: Reduced `MAX_LIVE_POLAROID_DOM` to `10` (for live animated GIF/MP4 Polaroids) and `OCCLUDED_GRACE_DROPS` to `2`, ensured `finishFallingPolaroidItem()` cancels lingering WAAPI drop animations and records coverage immediately upon landing, and sorted `pendingPolaroidBakes` by ascending `item.id` (`zIndex`) so canvas layers always bake in exact bottom-to-top order.
- **Masonry Cardboard Box Loading Screen & Smooth Fade-In Transition (`index.html`)**:
  - **High-DPI Isometric Cardboard Box Overlay**: When turning on or switching to the Masonry display for a screen, instead of mounting tiles one-by-one and triggering 12–36 consecutive full-grid layout solves and WAAPI reflows while media is still decoding, `index.html` now displays `#masonryLoadingOverlay` on `#0b0b0d` black with a high-DPI 2D canvas (`#masonryBoxCanvas`) rendering the application's brown isometric cardboard box (`drawMasonryCardboardBox()`, matching `create_cardboard_box_icon()` in `danbooru_service.py`).
  - **Atomic Grid Mount & Flap-Opening Transition Sequence**: The cardboard box remains closed (sealed with packing tape) while initial tiles preload and decode in the background (`masonryLoadPhase === 'loading'`). Once the tile batch is ready, `populateMasonryIfNeeded(true)` mounts and lays out the complete Masonry grid in a single atomic pass behind the black overlay, the cardboard box's top four flaps smoothly fold open (`masonryLoadPhase === 'opening'`) with a warm interior glow, and the overlay fades smoothly from black to the complete Masonry display (`masonryLoadPhase === 'fading' -> 'done'`).

---

## v2.3.7 — Per-Screen Slide Switch, V-Sync On/Off + Target FPS Pacing & Fluid Polaroid Drop Animations

### Summary
This update modernizes the screen enable control with a smooth on/off slide switch, adds a per-screen V-Sync toggle with a custom Target FPS limit (`15 – 240 FPS`) so you can match your monitor's refresh rate or cap frame rates to save power, and makes falling Polaroid photo animations buttery-smooth without mid-air stutters.

### Add or Changed
- **Modern On/Off Slide Switch for Screens**: Replaced the old square checkbox for `"Display wallpaper on this screen"` with a modern pill-shaped slide switch that works in both Light and Dark themes.
- **Per-Screen V-Sync & Custom FPS Cap**: Added a `"V-Sync On"` / `"V-Sync Off"` button for each monitor. When V-Sync is On, animations sync seamlessly to your monitor's refresh rate; when turned Off, a `"Target FPS (15 – 240)"` box appears so you can set your own exact frame rate limit.
- **Smooth, Stutter-Free Polaroid Drops**: Redesigned how Polaroid photos fall and land so background tasks and shadow rendering never cause mid-air frame drops.

### Removed
- **Legacy Screen Enable Checkbox**: Removed the legacy square checkbox (`tk.Checkbutton`) for `"Display wallpaper on this screen"`.
- **Mid-Drop Canvas Blur & Downscale Contention**: Removed expensive 24px Gaussian `shadowBlur` passes and mid-drop background image downscaling while a Polaroid photo is actively falling.

### Technical
- **On/Off Slide Switch for `"Display wallpaper on this screen"` (`danbooru_service.py`)**:
  - **Custom Theme-Aware Pill Switch**: Replaced the legacy `tk.Checkbutton` in `SettingsDialog._build_display_tab()` with a custom theme-aware pill slide switch (`self.screen_enable_switch` on the left, clickable `"Display wallpaper on this screen"` label on the right) rendered with smooth sliding circular thumb feedback in both Light and Dark themes (`_draw_screen_enable_switch()` & `_on_toggle_screen_enable_switch()`).
- **Per-Screen V-Sync Button (`"V-Sync On"` / `"V-Sync Off"`) & Conditional Target FPS Input Box (`danbooru_service.py`, `index.html`, `project.json`)**:
  - **Schema Properties**: Added per-screen `"vsync"` (`bool`, default `True`) and `"targetfps"` (`15 – 240`, default `60`, `"condition": "vsync.value == false"`) properties across `project.json` and `get_default_properties_dict()`.
  - **Display Tab Controls**: Directly below the `"Display wallpaper on this screen"` slide switch row, added `self.vsync_row` with a toggle button (`"V-Sync On"` / `"V-Sync Off"`). When switched to `"V-Sync Off"`, `self.target_fps_subframe` (`"Target FPS (15 – 240):"` + numeric input box) appears immediately to the right of the button.
  - **Drift-Compensated Frame Pacing**: Wired `VSYNC_ENABLED` and `TARGET_FPS` in `index.html`: when `V-Sync On` is active, the wallpaper animation loop runs locked to the display's native `requestAnimationFrame` refresh rate; when `V-Sync Off` is active, a sub-millisecond drift-compensated accumulator paces rendering to the configured Target FPS (`15 – 240` FPS).
- **Fluid, Stutter-Free Polaroid Drop Animation Pipeline (`index.html`)**:
  - **Root Causes Fixed**: Previously, Polaroid drops stuttered intermittently due to synchronous `prunePolaroidStackIfNeeded()` -> `bakePolaroidToCanvas()` calls executing a 24px Gaussian `shadowBlur` pass and DOM teardown right on the landing frame or while another Polaroid was mid-air, main-thread preloader scratch-canvas downscaling (`toBlob`), synchronous `computeAmbientBackdropDataUrl()`, and undecoded GIF frames competing with active drops, and DOM insertion before initial transform setup paired with a `scale(3.6)` 64px blur shadow that forced per-frame GPU shadow re-rasterization.
  - **Off-Main-Thread WAAPI Drop Animations**: Moved Polaroid drop animations to off-main-thread Web Animations API (`launchPolaroidWaapiDrop()` using `element.animate()` with `cubic-bezier(0.22, 1, 0.36, 1)`) when V-Sync is On, and set initial `translate3d`/`scale`/`rotate` before DOM insertion with consistent shadow geometry (`contain: layout style paint; backface-visibility: hidden;`).
  - **Deferred Idle-Window Canvas Baking**: Deferred static Polaroid canvas baking via `pendingPolaroidBakes` and `processPendingPolaroidBakes()` so `bakePolaroidToCanvas()` runs 1 item per frame strictly when `fallingItems.length === 0`, and replaced the expensive 24px `shadowBlur` pass with fast layered rounded-rect ambient shadows.
  - **Pre-Decoding & Downscale Suspension During Drops**: Pre-decoded both GIF and static images via `img.decode()`, bounded Polaroid textures to `1280px`, and paused scratch-canvas downscaling while `isAnyPolaroidFalling()` is true.

---

## v2.3.6 — Masonry GPU Optimization, Variable-Height Zero-Gap Rows, Polaroid Artist Captions & Settings UX Enhancements

### Summary
This update cuts graphics card (GPU) usage dramatically during Masonry tile transitions, improves the `Rows` layout so images fit together without extra empty gaps, adds red `"By: <artist>"` credits on the bottom of Polaroid photos, lets you click the `Post #` in Settings to open the artwork directly on Danbooru in your web browser, and remembers which Settings tab and monitor you were last viewing during your current session.

### Add or Changed
- **Session Memory for Active Tab & Selected Monitor**: Closing and reopening the Settings window while the app is running now reopens on the exact tab (`Credentials`, `Display`, or `Logs`) and monitor you were last using.
- **Edge Fill (`Blur` / `Black`) Available in Both Masonry Modes**: Extended the `Blur` / `Black` edge fill option so it works in both `Mondrian` and `Rows` Masonry modes.
- **Major GPU Usage Reduction in Masonry Mode**: Replaced heavy 3D perspective flips with smooth 2D horizontal card turns and hardware-accelerated animations, eliminating ~40% GPU spikes during tile flips.
- **Zero-Gap Variable-Height Masonry Rows**: Improved the `Rows` layout so each row naturally adjusts its height to fit uncropped artwork with zero extra horizontal or vertical gaps beyond your chosen `Gap` setting.
- **Accurate App-Only Resource Graph**: Updated the Resource Graph so it only measures the wallpaper app itself (ignoring external web browsers opened via links) and avoids double-counting GPU engines.
- **Clickable `Post #` Browser Link & Larger Header Font**: Clicking `Post #<id>` above the Displayed Media Tags box now opens that post on Danbooru in your default web browser, and the header (`DISPLAYED MEDIA TAGS (CLICK TO ADD):`) is slightly larger and easier to read.
- **Polaroid Artist Credits (`"By: <artist>"`)**: Every Polaroid photo now displays `"By: "` followed by the artist's name in Danbooru's signature red color on the bottom-left white border.

### Removed
- **3D Perspective Depth-Buffer Flips**: Removed 3D depth-buffer perspective (`perspective: 1100px`, `preserve-3d`, `rotateY`) on Masonry tiles in favor of lightweight 2D horizontal card turns (`scaleX`).
- **External Process & Synthetic GPU Telemetry**: Removed external browser child processes and synthetic CPU-to-GPU spike multipliers from Resource Graph telemetry, as well as the `"(TASK MANAGER VIEW)"` suffix from the Resource Graph window title.
- **Mondrian-Only Restriction on Edge Fill**: Removed the restriction that hid the `Edge Fill` button when switching from `Mondrian` to `Rows`.

### Technical
- **Runtime-Only Settings Tab & Selected Display Memory (`danbooru_service.py`)**:
  - **Process-Lifetime Session State**: When the Application Settings window is closed and reopened during an active session, it now automatically reopens on the last active tab (`Credentials`, `Display`, or `Logs`) and the last selected display (`Select Screen:`). Stored strictly in process-lifetime memory (`_RUNTIME_LAST_SETTINGS_TAB` and `_RUNTIME_LAST_SELECTED_SCREEN_ID`) so fresh application startups always open cleanly on the default initial state.
- **Masonry Edge Fill (`Blur` / `Black`) Persisted Across Both Mondrian and Rows (`danbooru_service.py`, `index.html`, `project.json`)**:
  - **Unified Masonry Condition**: Extended the `Mondrian Edge Fill:` (`Blur ⇄` / `Black ⇄`) toggle button so it remains visible and persists across both `Mondrian` and `Rows` Masonry layouts (`"condition": "displaymode.value == 'masonry'"`), and wired `#stage.masonry-black-mode` and ambient backdrop synthesis in `index.html` to apply `Blur` or `Black` edge fill in both layouts.
- **Combined 3-Part Masonry GPU Utilization Optimization (`index.html`)**:
  - **Off-Main-Thread Web Animations API (`element.animate()`)**: Replaced manual CSS style toggling and forced synchronous DOM reflows on neighbor FLIP transitions and card flips with compositor-driven WAAPI animations and scoped `will-change: transform` only on moving tiles.
  - **2D Horizontal Card Turn (`scaleX`) & Suspended Backdrop Resampling**: Replaced the 3D perspective depth-buffer (`perspective: 1100px`, `preserve-3d`, `rotateY`) with a lightweight 2D horizontal turn (`scaleX(1 -> 0.01 -> 1)`) and temporarily suspended dual-texture `background-image` resampling on `.is-flipping` / `.is-reflowing` tiles during motion.
  - **Local-First Neighbor Reflows & Tighter Texture Downscaling**: Prioritized local row/group reflows over 36-tile global reshuffles, lowered the Masonry scratch-canvas downscale ceiling to `960px`, and standardized fallback frame pacing to 60 FPS.
- **Variable-Height Masonry Rows Solver for Zero Extra Gaps (`index.html`)**:
  - **Multi-Candidate DP & Inter-Row Swap/Move Refinement**: Redesigned `solveOptimalRowsPartitionForAspects()` to allow full row height variance ($H_r = W_{\text{avail},r} / \sum_{i \in r} A_i$) across candidate row counts $R \in [1, 12]$ with multi-candidate DP and pairwise inter-row tile swap/move refinement so $\sum_{r=1}^R H_r$ matches available screen height (`normScale` $\approx 1.000$). Every tile box now matches its uncropped media aspect ratio (`object-fit: contain`), leaving only the configured `Gap (0 – 10 px)` between tiles and rows.
- **Strict Application-Only Resource Graph Telemetry & Title Update (`danbooru_service.py`)**:
  - **Process Tree Filtering & Engine Grouping**: Filtered `_enumerate_app_process_tree()` strictly to the wallpaper process and its child `msedgewebview2.exe` processes (excluding external web browsers launched via hyperlinks), grouped PDH GPU counters by engine type (`engtype_*`) to report the maximum engine load without multi-engine double-counting, removed the synthetic `child_ticks_delta * 45.0` GPU spike multiplier when PDH counters are active, and updated the Resource Graph window title to `📊 PERFORMANCE — RESOURCE GRAPH`.
- **Clickable `Post #` Browser Hyperlink, Header Retitle & `+1pt` Font Size (`danbooru_service.py`)**:
  - **Hyperlink Binding & Typography**: Retitled the Displayed Media Tags header to `DISPLAYED MEDIA TAGS (CLICK TO ADD):`, increased both the header and `Post #<id> (<n> tags)` font sizes by `+1pt` (`("Segoe UI", 9, "bold")`), and turned `Post #<id>` into an underlined clickable hyperlink that opens `https://danbooru.donmai.us/posts/<id>` in the default web browser.
- **Polaroid Bottom-Left `"By: <artist>"` Red Artist Tag Caption (`index.html`)**:
  - **DOM & Canvas 2D Caption Rendering**: Added `"By: "` followed by the post's artist tag(s) (`post.tag_string_artist`) in Danbooru's red artist tag color (`#c00004`) aligned on the bottom-left white chin of every Polaroid across live DOM Polaroids, canvas-baked Polaroids (`#polaroidBaseCanvas`), and pause/freeze snapshots (`#freezeOverlayCanvas`).

---

## v2.3.5 — Comprehensive Codebase Audit, 64-Bit Win32 `ctypes` Hardening, Bounded LRU Caches & True Chunked Streaming

### Summary
This under-the-hood maintenance and reliability update ensures the app can run continuously for days or weeks without slowly gaining memory or crashing on 64-bit Windows systems. It streams large video and image files in small pieces instead of loading whole files into RAM at once, caps internal tag and DNS caches so they never grow indefinitely, and strengthens security checks on downloaded files.

### Add or Changed
- **64-Bit Windows Compatibility & Crash Prevention**: Hardened all Windows system calls used for process and hardware monitoring so 64-bit Windows handles are never cut off or misread.
- **Long-Session Memory Stability**: Capped all internal caches for post tags, tag color categories, search pools, and DNS lookups so running the wallpaper for days or weeks never leaks memory.
- **True Low-Memory Media Streaming**: Large videos and high-resolution images now stream in small 64 KB chunks instead of buffering the entire file in memory first.
- **Enhanced Malicious File Blocking**: Added extra file-header security checks to block disguised XML, shell script, and executable payloads.
- **100% Settings Schema Consistency**: Synchronized all internal default settings with `project.json` so saving settings never loses dropdown options or visibility rules.

### Removed
- **Dead Code & Unused Symbols**: Removed unused imports (`import math`), unused constants (`CLOUDFLARE_DOH_ENDPOINT`, `DANBOORU_CATEGORY_ORDER`, `DANBOORU_CATEGORY_NAMES`), dead methods (`_get_ram_scale_ceiling_mb`), and obsolete `tile.pendingReady` references.
- **Eager Full-File RAM Buffering**: Removed full-file in-memory buffering (`resp.content`) prior to streaming media chunks.
- **Legacy `POST_TAGS_ORDER` Deque**: Removed the dual-structure `POST_TAGS_ORDER` deque that left orphaned entries in the tag cache.

### Technical
- **64-Bit Win32 `ctypes` Signature Hardening & Invalid Handle Protection (`danbooru_service.py`)**:
  - **Root Cause Fixed**: In `AppResourceMonitor` and `_detect_primary_gpu_name`, Win32 calls (`CreateToolhelp32Snapshot`, `Process32FirstW`, `Process32NextW`, `OpenProcess`, `GetProcessTimes`, `CloseHandle`, `GlobalMemoryStatusEx`, `K32GetProcessMemoryInfo`, `EnumDisplayDevicesW`, and `pdh` counter APIs) lacked explicit `argtypes` and `restype` declarations. Under 64-bit Windows (`win-amd64`), `ctypes` defaulted to signed 32-bit `c_int` return values—causing `CreateToolhelp32Snapshot` failure checks (`snap == ctypes.c_void_p(-1).value`) to always evaluate to `False` (`-1 != 18446744073709551615`) and truncating 64-bit `HANDLE` pointers above `0x7FFFFFFF`.
  - **Remediation**: Declared explicit 64-bit safe `argtypes` and `restype` (`wintypes.HANDLE`, `ctypes.c_void_p`, `wintypes.BOOL`, `wintypes.LONG`) across all `kernel32`, `user32`, `psapi`, and `pdh` functions, and hardened `INVALID_HANDLE_VALUE` checks across `_enumerate_app_process_tree()` and `_query_process_ticks_and_ram()`.
- **Elimination of Memory Cycling & Unbounded Cache Leaks (`danbooru_service.py`)**:
  - **`POST_TAGS_CACHE` Eviction Bug Fixed**: Previously, `POST_TAGS_ORDER = deque(maxlen=2500)` was appended *before* checking `if len(POST_TAGS_ORDER) >= 2500:`, causing `deque(maxlen=2500)` to silently drop the oldest post ID while `.popleft()` popped the second-oldest post ID—leaving the oldest entry permanently orphaned in `POST_TAGS_CACHE`. In addition, `/report_shown` wrote directly to `POST_TAGS_CACHE` without registering the post ID in `POST_TAGS_ORDER`. Replaced both with `OrderedDict`-backed `cache_post_tags_locked(post_id, tags_list)` enforcing strict `MAX_POST_TAGS_CACHE = 2500` LRU eviction.
  - **Bounded `TAG_CATEGORY_CACHE`, `TAG_POOLS`, and `DOH_CACHE`**: Converted `TAG_CATEGORY_CACHE` (`MAX_TAG_CATEGORY_CACHE = 10000`, preserving `SEEDED_TAG_CATEGORIES`), `TAG_POOLS` (`MAX_TAG_POOLS = 16` inactive pool eviction), and `DOH_CACHE` (`MAX_DOH_CACHE_ENTRIES = 128` + TTL pruning) to bounded `OrderedDict` LRU caches so long-running multi-day sessions never cycle or leak RAM.
- **True Chunked Media Streaming Without Full-Buffer RAM Spikes (`danbooru_service.py`)**:
  - **Root Cause Fixed**: `iter_response_chunks(resp)` previously accessed `getattr(resp, "content", None)` *before* checking `hasattr(resp, "iter_content")`, and `HybridDoHSession.get()` omitted `stream=stream` when calling `self._curl_session.get()`, forcing entire 15 MB MP4 or 25 MB image payloads to materialize in RAM before yielding the first chunk.
  - **Remediation**: Forwarded `stream=stream` to `self._curl_session.get()` and reordered `iter_response_chunks()` to stream via `resp.iter_content(chunk_size=65536)` first.
- **Import Verification, Active Security Signature Wiring & Dead Symbol Removal (`danbooru_service.py`, `index.html`)**:
  - **Dead Symbol Cleanup**: Removed unused `import math`, dead `CLOUDFLARE_DOH_ENDPOINT`, dead `DANBOORU_CATEGORY_ORDER` / `DANBOORU_CATEGORY_NAMES`, dead `AppResourceMonitor._prev_gpu_sub_times`, dead `ResourceGraphDialog._get_ram_scale_ceiling_mb`, and dead `tile.pendingReady` references in `index.html`.
  - **Payload Signature Enforcement**: Wired `FORBIDDEN_PAYLOAD_SIGNATURES` directly into `verify_media_magic_bytes()` (adding `b"<?xml"`, `b"#!"`, and Mach-O `b"\xca\xfe\xba\xbe"` checks).
  - **Error-Path Blob URL Revocation**: Hardened Blob URL revocation on error/cancellation paths in `index.html` (`pumpPreloader` GIF and downscaler Scratch Canvas callbacks) and preserved full descriptor fields across Scroll axis changes.
- **100% Schema Parity Between `get_default_properties_dict()` and `project.json` (`danbooru_service.py`, `project.json`)**:
  - **Property Metadata Synchronization**: Fixed duplicate `"order": 2` on `"displaymode"` and `"scrolldirection"` in `get_default_properties_dict()` and synchronized all `"condition"`, `"options"`, `"editable"`, and `"order"` (`0`–`16`) fields with `project.json` so `_normalize_project_dict_in_place()` never strips Wallpaper Engine combo options or visibility conditions.

---

## v2.3.4 — Zero-Blur Mondrian Reshuffle & Resize on Tile Flip, `Blur` / `Black` Edge Fill Toggle & Flexible `Target Tile Count` (`±25%`) for Mondrian and Rows

### Summary
This update makes the Masonry grid adapt intelligently to the exact shape of every image so your artwork is shown completely uncropped with virtually zero blurry filler bars. When a tile flips to a new image, neighboring tiles smoothly resize or reorganize to fit the new shape, the tile count can flex by up to `±25%` to find the cleanest fit, and a new `Edge Fill` button lets you choose between soft `Blur` or solid `Black` for any tiny remaining margins.

### Add or Changed
- **Smart Grid Reshuffle & Resize on Tile Flips**: Whenever a Masonry tile flips to a new artwork with a different shape (portrait, landscape, or square), nearby tiles smoothly resize or rearrange so every image fits its box without cropping or large blurred borders.
- **New `Blur` / `Black` Edge Fill Button**: Added an edge fill toggle button in the Masonry settings so you can choose between a color-matched blurred backdrop (`Blur`) or solid dark space matching the grid lines (`Black`).
- **Flexible `Target Tile Count (4 – 36)` (`±25%`)**: Renamed `Tile Count` to `Target Tile Count (4 – 36)` and allowed the layout engine to automatically add or remove up to 25% of tiles when needed to eliminate awkward gaps and keep 100% of your media uncropped.

### Removed
- **Artificial Random Tile Size Jitter**: Removed random aspect-ratio jitter (`sizeJitter`) that previously forced mismatched tile boxes and blurry borders in Mondrian mode.
- **Rigid Fixed-Box Group Constraints on Tile Flip**: Removed fixed group bounding-box constraints during Mondrian tile flips that prevented neighboring groups from resizing when a portrait image replaced a landscape image (or vice versa).

### Technical
- **Zero-Blur Mondrian Reshuffle & Resize on Media Tile Flip (`index.html`)**:
  - **Root-Cause Elimination of Artificial Aspect Distortion**: Removed random `sizeJitter` (`0.92 + Math.random() * 0.16` → `1.0`) across all tiles and groups, widened bottom-up BSP ratio propagation bounds in `propagateAspectBottomUp()` from `[0.22, 0.78]` to `[0.06, 0.94]`, and expanded `solveAspectLockedSubtree()` to evaluate both balanced `(2+2)` and caterpillar `(1+3)` binary tree topologies across up to 12 leaf permutations (`generateCandidateLeafOrders()`).
  - **Tier 1A Local Group Reshuffle & Resize (`precomputeGroupReflowPlan` & `reflowMasonryGroupWithFlip`)**: Reorders and resizes sibling tiles inside the flipped tile's local group (`allowReorder = true`) when doing so achieves near-zero leaf distortion (`maxErr <= 0.012`).
  - **Tier 1B / Tier 2 Adjacent Group Resize & Full-Grid Re-Partition**: Whenever a flipped tile's new aspect ratio changes its group's effective aspect ratio beyond `0.012`, the solver automatically re-solves the top-level screen BSP tree (`resizedTopRoot`) or re-partitions all active tiles across candidate group counts (`solveGlobalMondrianPlanForProxies`, `scope: 'global'`) so adjacent tiles and groups smoothly resize/re-organize via GPU FLIP (`translate3d` + `scale3d`) to eliminate edge blur completely while keeping all media uncropped (`object-fit: contain`).
- **Dedicated `Mondrian Edge Fill:` (`Blur` / `Black`) Settings Button Row (`danbooru_service.py`, `project.json`, `index.html`)**:
  - **Schema Property**: Added `"masonryedgefill"` (`"blur"` | `"black"`, default `"blur"`) to `project.json` and `danbooru_service.py`.
  - **Settings Toggle Row**: When **Masonry → Mondrian** is selected in the **Display** tab, a dedicated row (`self.mondrian_edge_row`) appears directly below **`Masonry Layout:`** featuring **`Mondrian Edge Fill:`** on the left and a toggle button (`self.masonry_edge_fill_btn`) on the right that alternates between **`"Blur  ⇄"`** and **`"Black  ⇄"`** (automatically hidden via `pack_forget()` when **`Rows`** is selected).
  - **Renderer Styling**: **`Blur`** retains the 24×24 color-matched ambient blurred backdrop for any residual sub-pixel margin, while **`Black`** applies `#stage.mondrian-black-mode .masonry-flip-inner` (`background-image: none !important; background-color: #0b0b0d !important;`) to display pure `#0b0b0d` black space matching the inter-tile gap color.
- **`Target Tile Count (4 – 36)` with Dynamic `±25%` Flexibility Window for Both `Mondrian` and `Rows` (`danbooru_service.py`, `project.json`, `index.html`)**:
  - **Label & Schema Update**: Renamed the Masonry `"Tile Count (4 – 36):"` slider and schema property to **`"Target Tile Count (4 – 36):"`** across both **`Mondrian`** and **`Rows`** layouts.
  - **Dynamic `±25%` Bounds Solver**: Implemented `getTargetTileCountBounds(MASONRY_TILES)` (`delta = Math.max(1, Math.round(target * 0.25))`, clamped to `[4, 36]`), `getDesiredMasonryTileCount()`, `adjustMasonryTileCountOnFlipIfBeneficial()`, and `solveOptimalRowsPartitionForAspects()` (dynamic programming row partitioner) so the layout solver dynamically adjusts the displayed tile count by up to `±25%` on initial build, layout changes, and tile flips to minimize Mondrian edge blur/black space and achieve 100% uncropped (`object-fit: contain`) tiles in `Rows` mode.

---

## v2.3.3 — Saved Searches Bar Button, Continuous Marquee Saved Rows, Duplicate Toast & Dark Mode Tab Styling

### Summary
This update fixes the Saved Searches menu button so it is never cut off on the right side of the window, places a wide `"Saved Searches ▾"` bar directly above the search box, smoothly scrolls long saved tag lists horizontally so you can read every tag, shows a helpful notification if you try to save a duplicate search, and styles the top Settings tabs with clean dark backgrounds and crisp white borders in Dark Mode.

### Add or Changed
- **Full-Width `Saved Searches ▾` Bar Above the Search Box**: Moved the Saved Searches button into the control bar directly above the `TAGS =` box, spanning the space between the status badge and the playback buttons, with uniform `28 px` button heights across the entire row.
- **Auto-Scrolling Marquee for Long Saved Searches & Trash-Can (`🗑`) Delete Buttons**: Opening `Saved Searches ▾` shows a full-width dropdown where long saved tag searches continuously scroll horizontally so every tag is readable, paired with a `🗑` button on the right to delete unwanted entries.
- **`"Save Search Tags"` Option & Duplicate Notification Toast**: Clicking `"Save Search Tags"` at the top of the dropdown saves your current tags, or shows a brief 2-second `"Saved Search Tags already exists"` popup if that exact search is already saved.
- **True Dark Mode Settings Tabs**: Redesigned the top `Credentials`, `Display`, and `Logs` tabs so they display dark backgrounds, bright readable text, `2 px` spacing between tabs, and a `1 px` white outline in Dark Mode.

### Removed
- **Inline Right-Edge Search Box Arrow**: Removed the small down-arrow button from inside the right edge of the `TAGS =` text box where long text width settings previously pushed it out of view.
- **Native White Windows Tab Header**: Removed the native Windows `ttk.Notebook` tab header bar that ignored Dark Mode colors and stayed bright white.

### Technical
- **Debugged & Relocated Saved Searches to a Dedicated Full-Span Button Above the `TAGS =` Search Bar (`SettingsDialog._build_display_tab` & `render_saved_dropdown`)**:
  - **Root Cause Fixed**: In v2.3.2, `self.tag_input = tk.Text(self.search_container, ...)` omitted an explicit `width` (defaulting to `width=80` characters $\approx 640\text{ px}$) and was packed with `side="left", fill="both", expand=True` *before* `self.saved_arrow_btn.pack(side="right", fill="y")`. Because `tk.Text`'s requested width exceeded `self.search_container`'s available width (`~520 px`), Tkinter's packer allocated 100% of the container width to `self.tag_input` and clipped `self.saved_arrow_btn` off the right edge.
  - **New `Saved Searches ▾` Button Placement**: Removed the arrow from inside `self.search_container` (and set `width=20` on `self.tag_input`). Added `self.saved_searches_btn_frame` / `self.saved_searches_btn` (`"Saved Searches  ▾"`) in `self.search_controls_row` directly above the `TAGS =` search box, packed `side="left", fill="x", expand=True` so it spans the full width between the Page/Pool status indicator on the left and the Refresh (`⟳`) button on the right.
  - **Standardized Control Row Height (`28 px`)**: Wrapped the status indicator (`self.status_frame`), the `Saved Searches ▾` button (`self.saved_searches_btn_frame`), and the playback buttons (`self.refresh_btn_frame`, `self.prev_btn_frame`, `self.next_btn_frame`, `self.pause_btn_frame`) in uniform `height=28` frames with `pack_propagate(False)` so all controls above the `TAGS =` search bar share an identical height.
  - **Full-Width Dropdown Below `TAGS =` with Continuous Horizontal Marquee & Trash-Can (`🗑`) Delete Buttons**: Clicking **`Saved Searches ▾`** opens `self.saved_dropdown` anchored directly below the `TAGS =` search bar, spanning the full search box width. Each saved search row features a `tk.Canvas` viewport that continuously loop-scrolls horizontally from left to right (`_tick_saved_dropdown_marquee`) whenever a saved search has a large number of tags or tags too long to fit on one line, paired with a small trash-can (`🗑`) delete button on the right.
  - **`"Save Search Tags"` Top Option**: Placed **`"Save Search Tags"`** as the first option at the top of the Saved Searches dropdown to save the current tags in the search bar and add them to the dropdown.
  - **`"Saved Search Tags already exists"` Floating Toast Popup (`_show_saved_search_toast`)**: If **`"Save Search Tags"`** is pressed when a saved search for the current tags already exists, a floating toast popup (`self.toast_popup`) appears with **`"Saved Search Tags already exists"`** and automatically dismisses after 2 seconds (`2000ms`).
- **Dark Mode Application Settings Tabs with 1px Contrasting White Outline & 2px Tab Spacing (`_select_settings_tab` & `_update_settings_tabs_theme`)**:
  - **Root Cause Fixed**: Windows `ttk.Notebook` (`vista` / `xpnative` theme via `uxtheme.dll`) renders tab backgrounds using native Windows visual-style bitmaps that ignore `style.configure("TNotebook.Tab", background=...)` and `foreground`, leaving tabs white in Dark Mode.
  - **Custom Theme-Aware Tab Bar**: Replaced the native `ttk.Notebook` header with custom `tk.Frame` + `tk.Label` tab headers (`Credentials`, `Display`, `Logs`) spaced `2 px` apart (`padx=(0, 2)`). In Dark Mode, inactive tabs use `#232329` with `#f3f3f5` text, the active tab uses `#0067c0` with `#ffffff` text, and every tab has a `1 px` contrasting white outline (`highlightthickness=1, highlightbackground="#ffffff"`).

---

## v2.3.2 — Saved Searches Dropdown (`SAVE SEARCH`), Dynamic Search TAGS Box Scaling & Focus-Out Auto-Search

### Summary
This update adds a Saved Searches menu for bookmarking and switching between your favorite tag combinations, allows the `TAGS` search box to expand automatically up to 5 lines tall when you enter many tags so nothing gets cut off, and waits until you finish typing and click outside the search box before starting a new search.

### Add or Changed
- **Saved Searches Menu**: Added a Saved Searches dropdown menu below the `TAGS =` search box that lets you save your current tag search, load any saved search with one click, or delete old saved searches.
- **Auto-Expanding Multi-Line Search Box (1 to 5 Lines)**: The `TAGS =` search box now wraps long tag lists onto multiple lines and grows automatically from 1 line up to 5 lines tall (with vertical scrolling beyond 5 lines) while keeping Danbooru category colors on every word.
- **Search Only When Done Typing (Focus-Out Search)**: Instead of refreshing your wallpaper while you are still mid-word in the search box, automatic tag search now waits until you click outside the `TAGS` box (when the blinking text cursor disappears).

### Removed
- **Mid-Typing 1-Second Search Timer**: Removed the 1-second timer on `<KeyRelease>` that previously triggered premature searches if you paused briefly while typing a tag.
- **Single-Line Search Box Clipping**: Removed single-line horizontal clipping on the `TAGS =` search box.

### Technical
- **Saved Searches Dropdown (`▼`) with `"SAVE SEARCH"` Top Option (`SettingsDialog.render_saved_dropdown`)**:
  - **Dropdown Trigger Button**: Placed the down-arrow (`▼`) button on the far right of the Search `TAGS =` box in the **Display** tab of Application Settings.
  - **Bookmark & Persistence (`saved_searches.json`)**: Clicking `▼` opens a dropdown directly below the Search TAGS box listing all saved searches (`%APPDATA%\DanbooruWallpaper\saved_searches.json`), with **`SAVE SEARCH`** at the top to immediately bookmark the current search `TAGS`.
  - **One-Click Load & Delete**: Clicking any saved search applies it to the selected screen; clicking the delete button (`-`) on the right removes that saved search.
- **Dynamic Height Scaling of the Search TAGS Box (`_update_tag_input_height`)**:
  - **Display-Line Auto-Height (1–5 Lines)**: Updated `self.tag_input` in `danbooru_service.py` to wrap long or numerous tags (`wrap="word"`) and dynamically scale its height from **1 line up to 5 lines** based on rendered display lines (`self.tag_input.count("1.0", "end-1c", "displaylines")`), scrolling vertically beyond 5 lines so typed tags are never clipped out of view.
  - **Wrapped-Line Category Color Indexing**: Updated `_recolor_search_input_tags()` to use character-offset indexing (`1.0 + N chars`) so Danbooru category colors remain accurate across all wrapped lines.
- **Focus-Out Automatic Tag Search When Caret Stops Blinking (`_on_tag_input_focus_out` & `_is_tag_input_focused`)**:
  - **Caret Focus Guard**: Updated automatic tag search so it waits until the Search TAGS box is no longer being typed in (i.e., the vertical line pipe cursor `|` is no longer blinking inside the search box).
  - **KeyRelease Timer Removal**: Removed the 1-second mid-typing timer from `<KeyRelease>` so typing or pausing while focused inside the search box never triggers preemptive searches.
  - **Click-Outside Focus Release**: Bound `<FocusOut>` on `self.tag_input` and click-outside focus release across the Display tab so clicking outside the Search TAGS box stops the blinking cursor and immediately triggers the automatic search if tags were added or deleted.

---

## v2.3.1 — Bug Fixes and Real-Time Tag Refresh Updates

### Summary
This update fixes a bug that prevented Display Mode changes from saving and applying right away, ensures the Displayed Media Tags box updates in real time the exact moment a new image or video appears on your screen, and adds automatic tag refreshing when adding or removing tags.

### Add or Changed
- **Fixed Saving & Applying Display Mode Settings**: Switching display modes (`Scroll`, `Polaroid`, `Slideshow`, or `Masonry`) or adjusting sliders now saves and updates your wallpaper immediately.
- **Real-Time Displayed Media Tags Updates**: The Displayed Media Tags box in Settings now updates the instant a new image or video becomes visible on your screen across all four display modes.
- **Automatic Tag Refresh on Tag Changes**: Adding, pasting, deleting, or clicking a tag automatically refreshes the selected screen's wallpaper pool without requiring a manual restart.

### Removed
- **Stale Property & Epoch Response Caching**: Removed browser caching on internal `/properties` and `/epoch` requests that previously caused screens to stay stuck on old settings.
- **Premature Off-Screen Tag Reporting in Scroll Mode**: Removed early off-screen tag reporting in `Scroll` mode when items were pre-queued off-screen so tags are reported only when an item actually enters the visible screen area.

### Technical
- **Fixed Display Mode Settings Stuck on Last Used Settings (`save_display_settings`)**:
  - **Root Cause**: `SettingsDialog.save_display_settings()` previously called `get_or_create_tag_pool_locked(st["pool_key"], new_tags)` with 2 arguments instead of 1 (`raw_tags`), raising a `TypeError` before `store_project_json(project_data)` and `push_properties_to_webview(sid, sync_geometry=enabled_changed)` could execute. In addition, `ensure_screen_tag_pool_populated_async()` and `ensure_all_enabled_screen_pools_populated()` were missing the `force_reset: bool = False` parameter, and `index.html` fetched `/properties` without cache-busting query parameters (`&_t=${Date.now()}`, `{ cache: 'no-store' }`).
  - **Fix**: Corrected `get_or_create_tag_pool_locked(new_tags)` in `save_display_settings()`, added `force_reset: bool = False` to `ensure_screen_tag_pool_populated_async()` and `ensure_all_enabled_screen_pools_populated()`, unified `st["wallpaper_paused"]` and `pool["posts"]` key names, and added `&_t=${Date.now()}` and `{ cache: 'no-store' }` to `/properties` and `/epoch` fetches in `index.html` so Display Mode and per-mode settings save and apply immediately.
- **Real-Time Refresh of Displayed Media Tags on Each New Displayed Media File**:
  - **Root Cause**: `SettingsDialog._poll_display_status()` raised a `TypeError` on its initial tick when opening Settings (`get_or_create_tag_pool_locked(pool_key, query)`), terminating the periodic UI status and tag poll loop immediately after opening; `SettingsDialog.on_screen_media_displayed` was missing for the `/report_shown` push callback; and in `index.html` Scroll mode (`fillScrollBuffer`), `recordShownMedia` was called when items were pre-queued off-screen up to `3.5x` viewport width rather than when each item entered the visible screen viewport.
  - **Fix**: Fixed `_poll_display_status()` so the 400ms UI poll loop runs continuously while Settings is open, implemented `SettingsDialog.on_screen_media_displayed(self, screen_id, post_id, tags_list=None)` for immediate push updates from `/report_shown`, preserved `postId` and `tags` across all preloaded and requeued descriptors in `index.html`, and updated `updateScrollMode()` so `recordShownMedia(item)` fires the instant each scrolling media item enters the visible screen viewport (as well as on every Polaroid drop, Slideshow transition, and Masonry tile population or 3D flip).
- **Automatic 1-Second Delayed Refresh When Tags Are Added or Deleted (`_schedule_auto_tag_refresh`)**:
  - **Debounced Tag Refresh Timer**: Added `self._auto_tag_refresh_job` (`1000ms` timer) and `self._last_applied_tags_by_screen` in `SettingsDialog`.
  - **Unified Tag Mutation Triggers**: Whenever a tag is added or deleted in the `TAGS` search bar—whether by typing or deleting characters (`<KeyRelease>`, `BackSpace`, `Delete`, `<<Paste>>`, `<<Cut>>`), selecting an auto-suggestion (`_select_suggestion`), or clicking a tag in the permanent 4-layer Displayed Media Tags box (`_append_tag_to_search_input`)—the 1-second timer automatically applies the updated `TAGS`, increments the screen's `epoch` so the WebView flushes old media, and refreshes the screen's tag pool.

---

## v2.3.0 — Per-Screen Display Search and Danbooru Category Color Updates

### Summary
This major update moves the floating desktop search bar directly into the **Display** tab of the Application Settings window so each monitor can have its own independent tag search and playback controls. It also adds official Danbooru color-coding (General, Artist, Copyright, Character, and Meta) to all tags, adds a scrollable box showing all tags from the artwork currently on your screen (which you can click to add to your search), and lets you open Settings with a single left-click on the system tray icon.

### Add or Changed
- **Integrated Per-Screen Search & Playback Controls**: Placed `Refresh`, `Previous`, `Next`, `Pause`, status indicators, and the `TAGS =` search box directly inside the **Display** tab so every monitor can run its own custom search tags and playback controls independently.
- **Zero Background Downloads on Disabled Screens**: Unchecking `"Display wallpaper on this screen"` completely stops all network requests and media preloading for that monitor.
- **Shared Search Pool for Identical Monitor Tags**: If two or more monitors use the same search tags, they share a single download pool from Danbooru so the app never downloads duplicate listings, while still showing different images on each screen.
- **Scrollable "Displayed Media Tags" Box**: Added a 4-line scrollable box below the search bar that lists all tags for the artwork currently showing on the selected monitor; clicking any tag adds it to your search.
- **Official Danbooru Tag Category Colors**: Color-coded all tags across the search bar, autocomplete suggestions, and Displayed Media Tags box using Danbooru's official colors (Blue for General, Red for Artist, Purple for Copyright, Green for Character, and Orange for Meta) in both Light and Dark themes.
- **One-Click System Tray Settings Access**: Left-clicking the system tray icon now immediately opens or focuses the Application Settings window.

### Removed
- **Standalone Floating Desktop Search Bar (`FloatingSearchBar`)**: Removed the separate floating desktop search bar window and its minimize button.
- **Search Bar Position Lock Setting**: Removed the obsolete `"Search Bar Position: Locked/Unlocked"` setting from the Credentials tab.
- **Duplicate Identical-Tag API Requests**: Removed duplicate Danbooru API requests when multiple screens are configured with identical search tags.

### Technical
- **Integrated Search Controls in the `Display` Tab (`SettingsDialog`)**:
  - **Floating Window Removal**: Removed the separate floating desktop search window (`FloatingSearchBar`) and the obsolete `"Search Bar Position: Locked/Unlocked"` setting on the Credentials tab.
  - **Display Tab Layout**: Placed all search and playback features directly inside the **Display** tab of the Application Settings window (`SettingsDialog`), immediately below the **`Select Screen`** dropdown and the **`Display wallpaper on this screen`** checkbox, with no minimize button.
- **Per-Screen Playback and Refresh Controls Above the `TAGS` Search Bar**:
  - **Status Badge & Control Row**: Positioned the per-screen status indicator badge (`Ready`, `P:X (Y pooled)`, `Screen Paused`, `Screen Disabled (No Fetch)`, `API Error`) on the left and the **Refresh**, **Previous**, **Next**, and **Pause (`PAUSE`)** buttons on the right above the `TAGS =` search bar and below the `Select Screen` dropdown and display checkbox.
  - **Per-Screen Action Scoping**: All four buttons (**Refresh**, **Previous**, **Next**, and **Pause (`PAUSE`)**) operate independently on only the currently selected screen in the `Select Screen` dropdown.
- **Independent Per-Screen `TAGS` Search and Strict No-Fetch Guard for Unchecked Screens**:
  - **Per-Screen `"searchtags"` Property**: Added `"searchtags"` (`order: 0`, default `"scenery no_humans"`) to each screen's properties in `project.json` and `danbooru_service.py`.
  - **Disabled-Screen No-Fetch Guard**: If a screen's **`Display wallpaper on this screen`** checkbox is unchecked (`enabled == False`), both `danbooru_service.py` (`/api`, `fill_tag_pool`, `ensure_screen_tag_pool_populated_async`) and `index.html` (`SCREEN_ENABLED = false` default startup state until `/properties` confirms `enabled: true`) strictly skip all media fetching and preloading for that screen.
- **Shared Tag-Pool Deduplication Across Screens (`TAG_POOLS`)**:
  - **Canonical Pool Keying**: Implemented `TAG_POOLS` keyed by `canonical_pool_key(tags)`. When multiple enabled screens use the same `TAGS` query, they share a single upstream Danbooru API fetch pool (`TAG_POOLS[pool_key]`) while maintaining independent per-screen `seen_ids` cursors—eliminating duplicate HTTP requests to `danbooru.donmai.us` for identical tag searches.
- **Below-Input Auto-Suggestion and Saved Searches Dropdowns**:
  - **Dropdown Anchoring**: Configured both the live tag auto-suggestion popup (`self.suggest_dropdown`) and the saved searches popup (`self.saved_dropdown`) to always populate below the `TAGS` search box (`ry = self.search_container.winfo_rooty() + self.search_container.winfo_height() + 2`).
- **Permanent 4-Layer Scrollable Displayed Media Tags Box**:
  - **Scrollable Tag Sub-Panel**: Placed a permanent full-width sub-panel box (`self.media_tags_box_frame` with `self.media_tags_text`, `height=4`, `wrap="word"`, and vertical `ttk.Scrollbar`) directly below the `TAGS` search box.
  - **Real-Time `/report_shown` Sync**: Displays all tags of the most recently displayed media on the currently selected screen (reported in real time by `index.html` via `GET /report_shown?screen=<id>&post_id=<post_id>` when a media element becomes visible on screen).
  - **Click-to-Append Tag Binding**: Clicking any tag in the permanent 4-layer box appends that tag to the selected screen's `TAGS` search bar and schedules a refresh.
- **Danbooru Category Color Coordination Across All Tag Locations**:
  - **Theme-Aware Category Palette (`DANBOORU_TAG_COLORS`)**: All tags in the **`TAGS` search box**, the **auto-suggestion dropdown**, and the **permanent 4-layer displayed media tags box** are color-coordinated by their official Danbooru tag category:
    - **General (`category 0`)**: Blue (`#0075f8` Light / `#009be6` Dark)
    - **Artist (`category 1`)**: Red (`#c00004` Light / `#ff8a8b` Dark)
    - **Copyright (`category 3`)**: Purple (`#a800aa` Light / `#c797ff` Dark)
    - **Character (`category 4`)**: Green (`#00ab2c` Light / `#35c64a` Dark)
    - **Meta (`category 5`)**: Orange (`#fd9200` Light / `#ead084` Dark)
- **Direct System Tray Left-Click to Open Settings**:
  - **Primary Default Tray Action**: Updated `setup_tray()` in `danbooru_service.py` so `pystray.MenuItem("Settings", on_tray_settings, default=True)` is the default primary action: left-clicking the Danbooru Wallpaper system tray icon immediately opens (or brings to front) the Application Settings window, while right-clicking opens the context menu with `Settings` and `Exit`.

---

## v2.2.1 — High-Stress Stability and Resource Graph Accuracy Updates

### Summary
This update prevents the app from freezing or spiking GPU usage when rapidly clicking the `"Next"` or `"Previous"` buttons in large 36-tile Masonry grids, lowers standby memory usage once the Masonry grid is full, and updates the Memory graph in the Resource Graph window so it accurately shows usage out of 100% of your computer's total installed RAM.

### Add or Changed
- **Rapid-Click Freeze Protection (`1.0s` Cooldown & Single-Flip Guard)**: Added a 1-second cooldown and animation guard on the `"Next"` and `"Previous"` buttons so rapid clicking never piles up overlapping animations or freezes the app.
- **Lower Memory Usage on Full Masonry Grids**: Capped the standby preload queue to `10` items once all Masonry tiles on screen are filled, saving substantial RAM and video memory.
- **True 0%–100% System RAM Graph Scaling**: Updated the Memory graphs in the Resource Graph window to plot against your PC's actual total physical RAM (`0% – 100%`) instead of an arbitrary 4 GB cap.

### Removed
- **Unbounded Per-Click JS Evaluation Threads**: Removed per-click `threading.Thread` spawning for JavaScript evaluation in favor of a single ordered background worker queue.
- **Mid-Animation `busyGroups` Flip Bypass**: Removed the `busyGroups` bypass that previously allowed manual `"Next"` clicks to force overlapping 3D flips on tiles that were already mid-animation.
- **Hardcoded 4096 MB Memory Graph Ceiling**: Removed the fixed `4096 MB` scale ceiling on the Memory Resource Graph.

### Technical
- **Fixed Application Freeze and High GPU Utilization Under Rapid `"Next"` Button Presses (Max 36-Tile Masonry)**:
  - **1.0-Second Internal `"Next"` / `"Previous"` Cooldown**: Added `NAV_BUTTON_COOLDOWN_SEC = 1.0` in `danbooru_service.py` and `MANUAL_NAV_COOLDOWN_MS = 1000` in `index.html` (`window.triggerNextMedia` / `window.triggerPreviousMedia`) to prevent rapid-fire click floods from queuing overlapping transitions.
  - **Single-Flight JS Evaluation Worker (`_js_eval_worker`)**: Replaced per-click `threading.Thread` spawning in `_async_evaluate_js` with a single-flight background queue worker so rapid UI actions never pile up concurrent threads contending on `pywebview`'s WinForms `Control.Invoke` semaphore.
  - **Strict Single-Flip Concurrency and Reflow Guard (`isAnyMasonryTileBusy`)**: Enforced `if (isAnyMasonryTileBusy()) return false;` in `triggerNextMasonryFlip()` and removed the `busyGroups` bypass (`if (eligible.length === 0 && forceIgnorePlayGuard)`) so rapid manual `"Next"` triggers never launch overlapping 3D GPU layers or recalculate BSP/Row geometry from mid-animation rects.
  - **Steady-State Preload Cap and Serialized Scratch-Canvas Downscaling**: Capped `readyImageQueue` in Masonry mode to `10` items once all `MASONRY_TILES` (`36`) are populated on screen (instead of holding 42 extra decoded media nodes in RAM/VRAM), and serialized `downscaleScratchCanvas` with `isDownscaleCanvasBusy` while deferring canvas downscaling during active flips.
- **Fixed Memory Resource Graph Scaling Against 100% Total Physical System RAM**:
  - **Physical RAM Percentage Normalization**: Updated `ResourceGraphDialog` in `danbooru_service.py` (left-sidebar Memory mini sparkline, single `Memory` graph view, and `All Graphs (3x)` stacked view) to plot `self.monitor.ram_pct_history` against a fixed `0% - 100%` scale of total physical system memory (`total_phys_mb`) rather than a dynamic `4096 MB` ceiling.

---

## v2.2.0 — Performance, Stability, and Telemetry Updates

### Summary
This update adds a live **Resource Graph** window (similar to the Windows Task Manager Performance view) to monitor the app's CPU, Memory, and GPU usage, fixes a freeze that could happen when rapidly switching Masonry layouts, pre-loads the next Masonry tile behind the scenes so flips happen without any pause, and simplifies the Masonry layout names to `"Mondrian"` and `"Rows"`.

### Add or Changed
- **New `Resource Graph` Performance Window**: Added a `Resource Graph` button in the top header of Settings that opens a live 60-second performance monitor showing CPU %, Memory MB/%, and GPU % for the wallpaper application.
- **Fixed Freeze When Toggling Masonry Layouts**: Moved wallpaper settings updates onto a non-blocking background worker so rapidly switching between `"Mondrian"` and `"Rows"` never freezes the Settings window.
- **Seamless Pre-Staged Masonry Tile Flips**: The app now prepares the next image and calculates the new layout `1.2 seconds` before a tile flips, making the flip animation completely seamless while keeping memory usage low.
- **Simplified `"Mondrian"` and `"Rows"` Layout Names**: Renamed the long technical layout labels to `"Mondrian"` and `"Rows"` while keeping backward compatibility with existing saved settings.

### Removed
- **Blurred Background Bars in `Rows` Mode**: Removed blurred background filler bars when `Rows` mode is active (`#stage.rows-mode` sets `background-image: none`).
- **Synchronous UI-Thread Property Pushes**: Removed blocking cross-thread Win32 resync and `evaluate_js` calls from the Tkinter UI thread when toggling display settings.
- **Verbose Masonry Layout Labels**: Removed the long layout strings `"Aspect-Locked BSP Mondrian Solver"` and `"Google Photos (Justified Rows)"`.

### Technical
- **Removed Blurred Sections in `Rows` (Google Photos) Masonry Mode**:
  - **Justified Cell Styling**: Added `#stage.rows-mode` styling and updated `applyTileAmbientBackdrop()` / `rebuildFullMasonryLayout()` so that when `Rows` is selected, all blurred/ambient background sections are completely removed (`background-image: none`) and each tile cleanly fills its exact justified horizontal row cell (`object-fit: cover`).
- **Fixed Application Freeze When Toggling Masonry Layouts (>3 Times)**:
  - **Root Cause Identified**: Toggling between Masonry layouts previously invoked `push_properties_to_webview(sid)` synchronously on the Tkinter UI thread, which executed blocking cross-thread Win32 `SetWindowPos(..., SWP_FRAMECHANGED)`, `SendMessageW(WM_SIZE)`, and `RedrawWindow(..., RDW_UPDATENOW)` calls on the WebView2 HWND followed immediately by a blocking `win.evaluate_js(...)` semaphore wait and a redundant `window.dispatchEvent(new Event('resize'))`. Rapidly toggling >3 times caused a Win32 cross-thread message-pump deadlock between the Tkinter GUI thread and the WebView2 WinForms UI thread. Additionally, `solveAspectLockedSubtree()` in `index.html` reordered `masonryGroups` when `numGroups >= 3` without re-indexing `group.index` and `tile.groupIndex`.
  - **Fix**: Replaced blocking cross-thread `push_properties_to_webview` calls with a coalesced single-flight background worker (`_property_push_worker`), restricted Win32 geometry resyncs strictly to screen `enabled` state changes using `SWP_ASYNCWINDOWPOS = 0x4000`, added `prop_seq` in `/epoch` as a lock-free poll fallback, removed the redundant `resize` event dispatch, and re-indexed `masonryGroups` after BSP solving.
- **Background Pre-Rendering and Pre-Organization of Next Masonry Switch (Zero Memory Bloat)**:
  - **Pre-Computed Reflow Plan (`preStageNextMasonrySwitch` + `precomputeGroupReflowPlan`)**: Runs `1.2s` before the flip timer fires while the screen is stationary to pre-pick the target tile and next descriptor, pre-solve the exact post-flip BSP or Justified Row geometry (`newRects`), and pre-calculate every sibling tile's inverse FLIP transform matrix (`invDx`, `invDy`, `invSx`, `invSy`).
  - **Hidden Slot Texture Upload**: Pre-attaches the incoming `<img>` or `<video>` into a hidden `.masonry-prestage-slot` inside the target tile (`visibility: hidden`, `opacity: 0`) and forces GPU texture upload via `img.decode()` prior to starting the flip.
  - **Zero-Allocation Midpoint Swap**: At the 90-degree flip midpoint, swaps visibility and applies pre-computed FLIP transforms with zero DOM insertion, zero image decode, and zero layout solver math.
  - **Strict Memory Bounds**: Enforces a single-slot invariant (`preStagedMasonrySwitch`, max 1 hidden node across the entire grid) and downscales oversized static images in Masonry mode (`>1280px`) during preload via a reusable `1x1`-reset scratch canvas with immediate `URL.revokeObjectURL()` cleanup on tile eviction.
- **Relabeled Masonry Layout Toggle Button and Config to `"Mondrian"` vs. `"Rows"`**:
  - **Schema & Config Migration**: Updated `danbooru_service.py`, `index.html`, and `project.json` (`masonrylayout`) from `"mondrian"` / `"google_photos"` (`"Aspect-Locked BSP Mondrian Solver"` / `"Google Photos (Justified Rows)"`) to **`"Mondrian"`** (`"mondrian"`) and **`"Rows"`** (`"rows"`), with transparent backward-compatibility for existing saved configs.
- **Resource Graph Button and Windows Task Manager Performance Pop-Out (`ResourceGraphDialog`)**:
  - **Process-Tree Telemetry Dialog**: Added a **`Resource Graph`** button in the top header of the Settings window that launches a Windows Task Manager Performance-style pop-out window monitoring the wallpaper application's entire process tree (`Python` + child `msedgewebview2.exe` processes) for **CPU (%)**, **Memory (Working Set & Private Commit MB / % of Total Physical System RAM)**, and **GPU (%)** with scrolling 60-second time grids, left-sidebar mini sparklines, and a stacked 3-graph overview mode.

---

## v2.1.0 — Display Modes and Search Bar Navigation Updates

### Summary
This update introduces the new **Masonry** display mode—which arranges up to 36 images and videos into a live grid that periodically flips tiles and smoothly adjusts to fit each artwork's shape—along with **Previous** and **Next** navigation buttons to step backward or forward through your wallpaper media at any time, and renames the photo-stack display mode to **Polaroid**.

### Add or Changed
- **New `Masonry` Display Mode**: Added a full-screen multi-tile grid mode supporting `4 – 36` tiles, customizable `Gap (0 – 10 px)`, `Delay (1 – 60 s)`, and two live layout styles (`Mondrian` mosaic and `Rows` justified rows).
- **Full Playthrough Protection for GIFs & Videos**: Animated GIFs and MP4 videos in Masonry mode are guaranteed to play through at least one full loop before their tile is eligible to flip to a new file.
- **Smooth On-Demand GPU Animations**: Only the actively flipping tile and its immediate neighbors animate during a flip, keeping Masonry mode smooth even with more than 10 tiles on screen.
- **New `Previous` and `Next` Playback Buttons**: Added `Previous` and `Next` buttons next to `Refresh` so you can immediately skip to the next image/video or bring back the previously shown artwork across all display modes.
- **Renamed Display Mode to `Polaroid`**: Standardized the falling photo card mode name to `Polaroid` across all menus, configuration files, and logs.

### Removed
- **Permanent 3D GPU Layer Promotion on Idle Tiles**: Removed permanent `perspective: 1100px`, `preserve-3d`, and `will-change: transform` properties on stationary Masonry tiles that previously caused stutter above 10 tiles.
- **Legacy Falling Photo Mode Naming**: Removed legacy non-Polaroid naming references for the falling photo stack mode.

### Technical
- **Renamed Display Setting to `Polaroid`**:
  - **Cross-File Identifier Standardization**: Updated the display mode name and internal property prefix to `Polaroid` across `danbooru_service.py`, `index.html`, `project.json`, `README.md`, and the `[POLAROID]` log glossary entry.
- **New `Masonry` Display Mode (`masonry`) — Dual Layout Engines (`Mondrian` and `Rows`), On-Demand 3D GPU Layers, and Localized Reflow**:
  - **Mondrian Engine (`mondrian`)**: Bottom-up binary space partition solver that computes split orientations and exact harmonic/additive split ratios from each media file's true aspect ratio (`naturalW / naturalH`).
  - **Rows Engine (`rows`)**: Justified horizontal rows (like Google Photos Web) where tiles in each row share an exact justified height (`availRowW / sum(aspect_i)`) and row heights normalize proportionally to fill `100vw x 100vh` without any blurred background bars.
  - **On-Demand 3D GPU Layer Promotion (`>10` Tile Stutter Elimination)**: Idle tiles remain lightweight 2D layers without permanent `perspective: 1100px`, `preserve-3d`, or `will-change: transform`. Only the single actively flipping tile is promoted to a 3D GPU layer (`.is-flipping`), and only the flipped row (in `Rows` mode) or local 3-5 tile subgroup (in `Mondrian` mode) reflows via GPU FLIP (`translate3d` + `scale3d`).
  - **Animated Media Full-Playthrough Protection**: Added full-playthrough protection for animated GIFs (via single-pass Blob URL preloading and binary GIF89a Graphic Control Extension `0x21 0xF9` frame duration parsing) and MP4 videos (`ended` / `timeupdate` loop tracking) so animated files always finish playing at least once before they can be flipped.
  - **Masonry Property Schema**: Added Masonry display settings in `project.json` and the Display tab: **Masonry Layout** toggle button (`Mondrian` / `Rows`), **Tile Count** (`4 - 36`, default `12`), **Gap** (`0 - 10 px`, default `4 px`), and **Delay** (`1 - 60 s`, default `5 s`).
- **Playback Previous and Next Navigation Buttons**:
  - **Header Navigation Controls**: Added **Previous** and **Next** navigation buttons next to the **Refresh** button.
  - **Previous Requeue Logic**: **Previous** requeues the last shown file to the front of the media queue so that it displays next.
  - **Deduplicated Next Trigger (`NAV_SEQ`)**: **Next** immediately plays/displays the next queued file across all display modes (`scroll`, `polaroid`, `slideshow`, and `masonry`), with `NAV_SEQ` sequence deduplication so `evaluate_js` and `/epoch` polling never double-fire.

---

## v2.0.1 — Security Audit and Anti-Malware Hardening

### Summary
This security update protects your computer by inspecting every downloaded image and video before it is displayed, ensuring that only genuine image (`JPG`, `PNG`, `GIF`, `WEBP`) and video (`MP4`) files from trusted Danbooru servers can ever load, while blocking disguised scripts, executables, untrusted website redirects, and oversized files.

### Add or Changed
- **Genuine File Signature Verification**: Every downloaded file is inspected at the binary level to confirm it is a real image or MP4 video before it reaches the wallpaper display.
- **Disguised Malware & Script Blocking**: Automatically detects and blocks disguised scripts (`PHP`, `HTML`, `SVG`, `JavaScript`), Windows/Linux executables (`.exe`, `.bat`, `.ps1`, `ELF`), and archive files (`ZIP`/`PHAR`).
- **Safe URL & Redirect Verification**: Ensures media URLs and any server redirects only connect to official `danbooru.donmai.us` and `cdn.donmai.us` servers over HTTPS.
- **File Size Limits & Browser Sandboxing**: Enforced a `25 MB` limit on images alongside the `15 MB` limit on MP4 videos, locked down security headers, and disabled local file-system access inside the wallpaper viewer.

### Removed
- **Unverified Upstream HTTP Header Forwarding**: Removed blind trust in upstream server `Content-Type` and `Content-Disposition` HTTP headers.
- **Unchecked Automatic HTTP Redirects**: Removed unchecked automatic HTTP redirect following (`allow_redirects=True`) in network sessions.
- **Unbounded Image Stream Sizes & WebView Navigation**: Removed unbounded stream sizes on static and animated image downloads, as well as drag-and-drop and right-click context menu navigation inside the wallpaper view.

### Technical
- **Binary Magic-Byte Signature Verification (`verify_media_magic_bytes`)**:
  - **Magic-Byte Header Inspection**: `/media` proxy inspects the first chunk of every upstream file to verify genuine `JPEG` (`FF D8 FF`), `PNG` (`89 50 4E 47`), `GIF87a/89a`, `RIFF/WEBP`, or ISO-BMFF `MP4` (`ftyp`) magic signatures before forwarding any bytes to WebView2.
  - **Malicious Payload Signature Blocking**: Actively detects and blocks embedded PHP tags (`<?php`, `<?=`), HTML/SVG script payloads (`<script`, `<html`, `<svg`), Windows PE executables (`MZ`), ELF binaries, and ZIP/PHAR archives (`PK\x03\x04`).
- **Strict URL Path and Double-Extension Filtering (`validate_safe_media_url`)**:
  - **Path Regex & Token Validation**: Enforces `SAFE_MEDIA_PATH_RE` and `FORBIDDEN_URL_TOKENS` across both `/posts.json` metadata ingestion and `/media` proxy requests, blocking `.php`, `.phtml`, `.phar`, `.exe`, `.bat`, `.ps1`, `.scr`, `.hta`, `.svg`, `.html`, path traversal (`..`), null bytes, and extension mismatches.
- **Forced Safe Response Headers, `nosniff`, and Strict CSP**:
  - **Hardcoded Safe Response Headers**: Never trusts or forwards upstream `Content-Type` or `Content-Disposition` headers; derives `Content-Type` exclusively from verified binary magic bytes and forces `Content-Disposition: inline`, `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, and a locked-down `Content-Security-Policy`.
- **Hop-by-Hop Redirect Host Pinning and Stream Size Caps**:
  - **Manual Redirect Host Validation**: Disabled unchecked automatic redirects in `HybridDoHSession` and enforced hop-by-hop redirect host validation against `ALLOWED_MEDIA_HOSTS` (`danbooru.donmai.us`, `cdn.donmai.us`).
  - **Stream Size Caps & WebView2 Sandboxing**: Enforced a `25 MB` stream cap on static/animated images alongside the `15 MB` cap on MP4 videos, plus `--disable-file-system` WebView2 isolation flags.

---

## v2.0.0 — Core Architectural Foundation

### Summary
This foundational release establishes the standalone Windows 10/11 Danbooru Wallpaper application. It streams artwork, animated GIFs, and silent videos directly behind your desktop icons across single and multi-monitor setups, bypasses ISP network blocks automatically using encrypted DNS-over-HTTPS, and protects your saved Danbooru login credentials with built-in Windows encryption.

### Add or Changed
- **Standalone Multi-Monitor Desktop Wallpaper Host**: Renders live Danbooru wallpapers directly behind desktop icons across single and multiple monitors on Windows 10 and Windows 11.
- **Local Media Streaming Proxy (`127.0.0.1:8088`)**: Built an internal local streaming server that handles all Danbooru API searches and streams images and videos smoothly to each screen.
- **Automatic ISP Block Bypass (HTTP/2 + Cloudflare DoH)**: Uses modern browser TLS connections with automatic fallback to Cloudflare `1.1.1.1` DNS-over-HTTPS so wallpapers load reliably even on restrictive networks.
- **Windows-Encrypted Credential Storage**: Protects your Danbooru username and API key on disk using Windows Data Protection API (DPAPI) encryption tied to your Windows user account.
- **System Tray Icon & Settings Interface**: Added a system tray icon and a themed Settings window (`Credentials`, `Display`, and `Logs`) for managing monitors, display modes (`Scroll`, `Polaroid`, and `Slideshow`), and search tags.

### Removed
- **External Wallpaper Host Dependency**: Removed reliance on external third-party wallpaper host software by running as a self-contained Windows desktop application.
- **Plaintext Credential Storage**: Removed plaintext storage of Danbooru API keys on disk in favor of Windows DPAPI encryption.
- **Direct Cross-Origin Browser Requests**: Removed direct browser-to-CDN cross-origin requests by routing all media through the local `127.0.0.1:8088/media` proxy.

### Technical
- **Ephemeral Local `/media` Streaming Proxy and Hybrid HTTP/2 + Cloudflare DoH Transport (`HybridDoHSession`)**:
  - **Hybrid HTTP/2 + DoH Transport**: Routes all `<img>` and `<video>` traffic through `http://127.0.0.1:8088/media` using `curl_cffi` HTTP/2 Chrome TLS impersonation with automatic runtime fallback to `StdlibDoHSession` (`DoHSNIHTTPSConnection` over Cloudflare `1.1.1.1` DoH + TLS 1.3 SNI).
  - **Win32 Desktop Wallpaper Injection**: Injects ephemeral `pywebview` (`private_mode=True`) instances behind `SHELLDLL_DefView` via Win32 `ctypes` (`Progman` on Windows 11 24H2+, `WorkerW` on Windows 10 / earlier Windows 11).
  - **DPAPI Credential Encryption**: Encrypts Danbooru credentials at rest in `%APPDATA%\DanbooruWallpaper\config.json` via Windows DPAPI (`CryptProtectData` / `CryptUnprotectData`).
