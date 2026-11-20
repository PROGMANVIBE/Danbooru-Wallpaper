/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useEffect, useState } from 'react';
import {
  Check,
  Copy,
  Download,
  FileCode,
  Moon,
  Sun,
  ShieldCheck,
  Terminal,
  Wrench,
  AlertTriangle,
  LayoutGrid,
  Monitor,
  RotateCw,
  Play,
  Pause,
  ChevronLeft,
  ChevronRight,
  ChevronDown,
  Trash2,
} from 'lucide-react';

type FileKey = 'CHANGELOG.md' | 'README.md' | 'GLOSSARY.md' | 'danbooru_service.py' | 'index.html' | 'project.json' | 'build-release.yml';
type ViewTab = 'code' | 'preview' | 'audit' | 'build';

const FILE_LIST: { key: FileKey; path: string; label: string; desc: string }[] = [
  {
    key: 'danbooru_service.py',
    path: '/updated_files/danbooru_service.py',
    label: 'danbooru_service.py',
    desc: 'v2.3.13 service featuring cleaned-up Slideshow & Masonry settings panels (removed bottom helper description lines), HDMI TV hotplug watchdog & dynamic WebView2 provisioning, non-destructive _probe_existing_desktop_topology (conditional 0x052C), SHELLDLL_DefView desktop icon scale snapshot & restoration, passive WS_DISABLED + WS_EX_TRANSPARENT child styles, disconnected monitor hiding, collision-free persistent monitor IDs, Glass-Pane coexistence, and manual Resync Displays button in Settings & Tray.',
  },
  {
    key: 'index.html',
    path: '/updated_files/index.html',
    label: 'index.html',
    desc: 'v2.3.13 WebView2 renderer with explicit pinch/Ctrl+Wheel/Ctrl+Key zoom blockers, 120ms debounced window resize handler (preventing mid-handshake HDMI layout thrashing), window.forceViewportResync() hook, and full pause/solver optimizations.',
  },
  {
    key: 'project.json',
    path: '/updated_files/project.json',
    label: 'project.json',
    desc: 'v2.3.13 wallpaper configuration schema synchronized 1:1 with get_default_properties_dict(), including per-screen pausefullscreen (bool, default true) and Edge Fill metadata.',
  },
  {
    key: 'README.md',
    path: '/updated_files/README.md',
    label: 'README.md',
    desc: 'Updated v2.3.13 README documenting Windows 11 24H2+ HDMI hotplug recovery, SHELLDLL_DefView icon scale guard, Glass-Pane coexistence, Resync Displays controls, and security hardening.',
  },
  {
    key: 'GLOSSARY.md',
    path: '/updated_files/GLOSSARY.md',
    label: 'GLOSSARY.md',
    desc: 'Standalone Application Logs Glossary documenting all Normal Operation, User Interaction, and Error/Security/Warning log prefixes.',
  },
  {
    key: 'CHANGELOG.md',
    path: '/updated_files/CHANGELOG.md',
    label: 'CHANGELOG.md',
    desc: 'Formalized release notes across all versions (v2.0.0 – v2.3.13), organized consistently into 4 sections per version: Summary, Add or Changed, Removed, and Technical.',
  },
  {
    key: 'build-release.yml',
    path: '/updated_files/build-release.yml',
    label: '.github/workflows/build-release.yml',
    desc: 'GitHub Actions workflow that auto-detects the source directory (whether danbooru_service.py is in the repo root or public/updated_files/), builds DanbooruWallpaper.exe with PyInstaller, generates a SHA256 checksum, and attaches both to the GitHub Release.',
  },
];

type TagCategory = 0 | 1 | 3 | 4 | 5;

const DANBOORU_CAT_META: Record<
  TagCategory,
  { name: string; lightHex: string; darkHex: string }
> = {
  0: { name: 'General', lightHex: '#0075f8', darkHex: '#009be6' },
  1: { name: 'Artist', lightHex: '#c00004', darkHex: '#ff8a8b' },
  3: { name: 'Copyright', lightHex: '#a800aa', darkHex: '#c797ff' },
  4: { name: 'Character', lightHex: '#00ab2c', darkHex: '#35c64a' },
  5: { name: 'Meta', lightHex: '#fd9200', darkHex: '#ead084' },
};

const KNOWN_TAG_CATEGORIES: Record<string, TagCategory> = {
  scenery: 0,
  no_humans: 0,
  outdoors: 0,
  sky: 0,
  cloud: 0,
  day: 0,
  water: 0,
  tree: 0,
  blue_sky: 0,
  sunlight: 0,
  starry_sky: 0,
  night: 0,
  mountain: 0,
  horizon: 0,
  reflection: 0,
  grass: 0,
  flower: 0,
  building: 0,
  cityscape: 0,
  sunset: 0,
  ocean: 0,
  '1girl': 0,
  solo: 0,
  'machi_(7769)': 1,
  kantoku: 1,
  wlop: 1,
  makoto_shinkai: 1,
  mochizuki_kei: 1,
  original: 3,
  genshin_impact: 3,
  touhou: 3,
  fate_grand_order: 3,
  blue_archive: 3,
  hatsune_miku: 4,
  hakurei_reimu: 4,
  'furina_(genshin_impact)': 4,
  artoria_pendragon: 4,
  highres: 5,
  absurdres: 5,
  animated: 5,
  video: 5,
  wallpaper: 5,
  'rating:general': 5,
  'order:random': 5,
};

const SAMPLE_SUGGESTIONS: { name: string; count: number; cat: TagCategory }[] = [
  { name: 'scenery', count: 1482910, cat: 0 },
  { name: 'no_humans', count: 312450, cat: 0 },
  { name: 'makoto_shinkai', count: 4820, cat: 1 },
  { name: 'genshin_impact', count: 642100, cat: 3 },
  { name: 'furina_(genshin_impact)', count: 41200, cat: 4 },
  { name: 'hatsune_miku', count: 298400, cat: 4 },
  { name: 'highres', count: 4812000, cat: 5 },
  { name: 'absurdres', count: 1920400, cat: 5 },
  { name: 'starry_sky', count: 184320, cat: 0 },
  { name: 'original', count: 3120900, cat: 3 },
];

const SAMPLE_MEDIA_POSTS: Record<
  string,
  { postId: number; tags: { name: string; cat: TagCategory }[] }[]
> = {
  screen_1: [
    {
      postId: 8492014,
      tags: [
        { name: 'machi_(7769)', cat: 1 },
        { name: 'original', cat: 3 },
        { name: 'highres', cat: 5 },
        { name: 'absurdres', cat: 5 },
        { name: 'wallpaper', cat: 5 },
        { name: 'scenery', cat: 0 },
        { name: 'no_humans', cat: 0 },
        { name: 'outdoors', cat: 0 },
        { name: 'sky', cat: 0 },
        { name: 'cloud', cat: 0 },
        { name: 'day', cat: 0 },
        { name: 'blue_sky', cat: 0 },
        { name: 'water', cat: 0 },
        { name: 'reflection', cat: 0 },
        { name: 'horizon', cat: 0 },
        { name: 'sunlight', cat: 0 },
        { name: 'mountain', cat: 0 },
        { name: 'tree', cat: 0 },
        { name: 'grass', cat: 0 },
        { name: 'flower', cat: 0 },
        { name: 'building', cat: 0 },
        { name: 'cityscape', cat: 0 },
        { name: 'ocean', cat: 0 },
        { name: 'sunset', cat: 0 },
      ],
    },
    {
      postId: 8491882,
      tags: [
        { name: 'makoto_shinkai', cat: 1 },
        { name: 'original', cat: 3 },
        { name: 'highres', cat: 5 },
        { name: 'absurdres', cat: 5 },
        { name: 'scenery', cat: 0 },
        { name: 'no_humans', cat: 0 },
        { name: 'starry_sky', cat: 0 },
        { name: 'night', cat: 0 },
        { name: 'cloud', cat: 0 },
        { name: 'mountain', cat: 0 },
        { name: 'reflection', cat: 0 },
        { name: 'water', cat: 0 },
        { name: 'outdoors', cat: 0 },
        { name: 'horizon', cat: 0 },
      ],
    },
  ],
  screen_2: [
    {
      postId: 8501290,
      tags: [
        { name: 'wlop', cat: 1 },
        { name: 'genshin_impact', cat: 3 },
        { name: 'furina_(genshin_impact)', cat: 4 },
        { name: 'highres', cat: 5 },
        { name: 'wallpaper', cat: 5 },
        { name: '1girl', cat: 0 },
        { name: 'solo', cat: 0 },
        { name: 'water', cat: 0 },
        { name: 'blue_sky', cat: 0 },
        { name: 'sunlight', cat: 0 },
        { name: 'outdoors', cat: 0 },
        { name: 'reflection', cat: 0 },
        { name: 'flower', cat: 0 },
        { name: 'cloud', cat: 0 },
      ],
    },
  ],
};

const SECURITY_AUDIT_ITEMS = [
  {
    id: 'SEC-01',
    severity: 'CRITICAL (Malware / Disguised Payload Prevention)',
    file: 'danbooru_service.py (verify_media_magic_bytes & /media proxy)',
    issue: 'Blind trust in upstream Content-Type header & lack of binary magic-byte header verification',
    cause:
      'Previously, the local `/media` proxy forwarded `resp.headers.get("Content-Type")` from the upstream CDN without inspecting the initial binary bytes of the downloaded stream. If a compromised CDN node, rogue redirect, or polyglot upload served a PHP script (`<?php`), HTML/SVG script (`<script>`), Windows PE executable (`MZ`), or ZIP/PHAR archive (`PK\\x03\\x04`) disguised with a `.jpg` or `.mp4` extension, raw bytes would stream into the WebView2 process.',
    fix: 'Implemented `verify_media_magic_bytes(header_bytes, is_range_continuation=False)` on the first chunk of every `/media` stream (including HTTP 206 Range continuation support for MP4 scrubbing/looping). Every file must match strict binary magic signatures for JPEG (`FF D8 FF`), PNG (`89 50 4E 47`), GIF (`GIF87a`/`GIF89a`), WEBP (`RIFF....WEBP`), or ISO-BMFF MP4 (`ftyp`/`moov`/`mdat`). Any stream containing `<?php`, `<script`, `<!doctype html`, `MZ`, `\\x7fELF`, or `PK\\x03\\x04` is immediately aborted and logged under `[SECURITY]`.',
  },
  {
    id: 'SEC-02',
    severity: 'HIGH (PHP & Double-Extension Filtering)',
    file: 'danbooru_service.py (validate_safe_media_url)',
    issue: 'Insufficient URL path validation against `.php` scripts, double extensions, and path traversal',
    cause:
      'Previously, `fill_post_buffer()` checked `item.get("file_ext")` or `.endswith()`, which did not inspect the full URL path or query string for double extensions (e.g., `payload.php.jpg`, `image.jpg/.php`), executable extensions (`.exe`, `.bat`, `.ps1`, `.scr`, `.hta`), or path traversal sequences (`..`, `%00`).',
    fix: 'Implemented `validate_safe_media_url(media_url, ext_hint)` enforced at both `/posts.json` ingestion and `/media` request handling. Enforces `SAFE_MEDIA_PATH_RE` (`^/[A-Za-z0-9/_\\-\\.~%]+\\.(jpg|jpeg|png|webp|gif|mp4)$`), blocks all `FORBIDDEN_URL_TOKENS` (`.php`, `.phtml`, `.phar`, `.exe`, `.bat`, `.ps1`, `.scr`, `.hta`, `.svg`, `.html`, `..`), and verifies that `file_ext` metadata matches the URL path extension.',
  },
  {
    id: 'SEC-03',
    severity: 'HIGH (Drive-By Download & MIME-Sniffing Prevention)',
    file: 'danbooru_service.py & index.html',
    issue: 'Missing Content-Disposition: inline, X-Content-Type-Options: nosniff, and Content-Security-Policy',
    cause:
      'Without explicit anti-sniffing and disposition headers on `/` and `/media`, a browser engine could MIME-sniff a malformed stream or trigger a file download dialog onto the host computer.',
    fix: 'Hardcoded `Content-Type` strictly from the verified magic-byte signature (never from upstream headers) and forced `Content-Disposition: inline`, `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Cross-Origin-Resource-Policy: same-origin`, and a strict `Content-Security-Policy` (`default-src \'self\'; script-src \'self\' \'unsafe-inline\'; object-src \'none\'; frame-src \'none\'`) across both HTTP responses and `index.html`.',
  },
  {
    id: 'SEC-04',
    severity: 'MEDIUM (Open Redirect & SSRF Hardening)',
    file: 'danbooru_service.py (HybridDoHSession.get)',
    issue: 'Unchecked upstream HTTP redirects in curl_cffi and urllib transport sessions',
    cause:
      '`curl_cffi` and `urllib.request.build_opener` follow `301/302/307/308` redirects automatically by default. If an upstream URL returned a redirect to an external untrusted domain, the client would follow it outside `ALLOWED_MEDIA_HOSTS`.',
    fix: 'Disabled automatic redirects (`allow_redirects=False` and `NoRedirectHandler`) and implemented a manual hop-by-hop redirect loop (max 3 hops) inside `HybridDoHSession.get()` that validates every `Location` target against `https://` and `ALLOWED_MEDIA_HOSTS` (`danbooru.donmai.us`, `cdn.donmai.us`) before connecting.',
  },
  {
    id: 'SEC-05',
    severity: 'MEDIUM (Resource Exhaustion & WebView2 Sandboxing)',
    file: 'danbooru_service.py (MAX_IMAGE_FILE_SIZE_BYTES & WebView2 flags)',
    issue: 'Unbounded stream size on non-MP4 media & WebView2 filesystem exposure',
    cause:
      'While MP4 files were capped at 15 MB, static/animated image streams had no upper byte cap during chunked streaming, allowing a crafted multi-gigabyte stream to exhaust memory.',
    fix: 'Enforced `MAX_IMAGE_FILE_SIZE_BYTES = 25 * 1024 * 1024` (25 MB) across both `Content-Length` pre-checks and real-time chunk streaming in `/media`, added `--disable-file-system` to WebView2 Chromium flags, and blocked `dragover`/`drop`/`contextmenu` navigation in `index.html`.',
  },
];

const FEATURE_SUMMARY_ITEMS = [
  {
    id: 'UI-CLEANUP (v2.3.13)',
    severity: 'v2.3.13 REMOVED SLIDESHOW & MASONRY BOTTOM SETTINGS DESCRIPTION LINES',
    file: 'danbooru_service.py & CHANGELOG.md',
    issue: 'Remove Multi-Line Helper Description Notes Below Slideshow and Masonry Display Settings',
    cause:
      'User requested removing the multi-line text descriptions (`slide_note` and `masonry_note`) at the bottom under the display settings for both the Slideshow and Masonry modes.',
    fix: 'Removed `slide_note` (`tk.Label`) from `self.slideshow_section_frame` and `masonry_note` (`tk.Label`) from `self.masonry_section_frame` in `SettingsDialog._build_display_tab()`, along with their `_themed_labels_muted` entries and click-outside `<Button-1>` focus-release bindings.',
  },
  {
    id: 'AUDIT-HOTPLUG (v2.3.12)',
    severity: 'CRITICAL WINDOWS 11 24H2+ HDMI TV HOTPLUG, TASK VIEW TILING & DESKTOP ICON INFLATION FIX',
    file: 'danbooru_service.py & index.html',
    issue: 'Eliminate "Task View" Tiled Viewport Glitch, Desktop Icon Inflation & Display Topology Desync When Connecting/Disconnecting an HDMI TV at Runtime',
    cause:
      'Turning an HDMI TV (3rd monitor) on or off while the wallpaper was running triggered 4 interacting Win32 failures on Windows 11 24H2+: (1) `enumerate_desktop_topology()` unconditionally broadcast `0x052C` (`wParam=0, lParam=0` and `wParam=0xD, lParam=0x1`) to `Progman` on every geometry sync—forcing `explorer.exe` to re-evaluate `SHELLDLL_DefView` (`SysListView32`) icon metrics against the newly connected TV\'s high DPI while `PER_MONITOR_AWARE_V2` (`-4`) child windows were attached inside `Progman`, inflating all desktop icons; (2) `sync_all_screens_z_order_and_geometry()` executed `if not hwnd or sid not in screens_by_id: continue`, skipping disconnected monitors when the TV was powered off and leaving its `WS_VISIBLE` HWND clamped inside `Progman` over remaining monitors like a "Task View" grid; (3) `refresh_connected_screens_preserving_ids()` could assign duplicate `screen_id` values when monitor sort order shifted on hotplug; and (4) `CONNECTED_SCREENS` was never refreshed in the background on `WM_DISPLAYCHANGE`, nor were WinForms `WM_DPICHANGED` child size overrides healed automatically.',
    fix: 'Implemented 7 comprehensive fixes: (1) Added non-destructive `_probe_existing_desktop_topology(progman)` so `0x052C` is only sent when no valid `WorkerW` exists yet (`force_init=True`), never during routine geometry syncs; (2) Added `capture_desktop_icon_metrics()` and `restore_desktop_icon_metrics_if_inflated()` (`LVM_GETITEMSPACING`, `LVM_SETICONSPACING`, `LVM_GETVIEW`, `LVM_SETVIEW`) to automatically restore `SHELLDLL_DefView` desktop icon spacing if a monitor DPI transition inflates them; (3) Hardened wallpaper HWNDs and Chromium children with `EnableWindow(hwnd, False)` (`WS_DISABLED`) + `WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE | WS_EX_TRANSPARENT` (`_apply_passive_wallpaper_window_styles`) so they cannot intercept mouse wheel, pinch-zoom, or focus; (4) Explicitly hid (`SW_HIDE`) and paused (`disconnected_paused`) any `SCREEN_HWNDS[sid]` whose monitor is turned off; (5) Rebuilt `refresh_connected_screens_preserving_ids()` with a persistent `_KNOWN_DEVICE_TO_SCREEN_ID` map and two-pass collision-free ID allocator; (6) Added automatic hotplug topology detection (`get_display_topology_signature`), dynamic WebView2 provisioning (`ensure_webview_windows_for_connected_screens`), and a 2.25s HWND parent/rect watchdog (`verify_and_heal_desktop_hwnds`) inside `fullscreen_monitor_worker_loop()` plus `Glass-Pane` coexistence exclusions; and (7) Added a manual `"Resync Displays"` button in `SettingsDialog` (Display tab) and the system tray context menu.',
  },
  {
    id: 'AUDIT-FULL (v2.3.11)',
    severity: '13 VERIFIED PRINCIPAL SYSTEMS, CONCURRENCY, RENDERING & SECURITY AUDIT FIXES',
    file: 'danbooru_service.py & index.html',
    issue: 'Resolve All 13 Audited Bugs Across Win32 Injection, HTTP Range Security, Preloader Downscaling, Concurrency Queues, Fullscreen Detection, Transport Auth & Multi-GPU Telemetry',
    cause:
      'Line-by-line audit uncovered 3 Critical, 4 High, 4 Medium, and 2 Low issues: (1) synchronous cross-thread `SendMessageW(WM_SIZE)` inside `resize_webview_child_containers()` while holding `INJECTION_LOCK`; (2) `/media` HTTP Range handling where `bytes=0-0` probes failed magic-byte inspection (`415`), `Content-Range` total sizes bypassed `max_allowed_bytes`, and `mark_mp4_url_verified` lacked a `>= 32` byte guard; (3) `pumpPreloader()` scratch-canvas `toBlob` race and missing `gen`/`APP_PAUSED` abort guards; (4) `_JS_EVAL_QUEUE = deque(maxlen=16)` silently evicting pause/navigation commands during multi-screen slider drags; (5) `sync_all_screens_z_order_and_geometry()` triggering 1px size nudges and `RedrawWindow` across unaffected screens; (6) `detect_fullscreen_monitors()` false positives on maximized Chromium/Electron windows with auto-hidden taskbars; (7) `HybridDoHSession.get()` forwarding Basic Auth headers to `cdn.donmai.us` and mutating shared session dicts across threads; (8) `_query_pdh_gpu_utilization()` summing multiple physical GPU adapters into the same `engtype_*` bucket; (9) redirect hops not checking `FORBIDDEN_URL_TOKENS`; (10) `SettingsDialog` re-enumerating `CONNECTED_SCREENS` without preserving `screen_id` by Win32 device name; (11) `spawnImmediateScrollNextItem` and `fillScrollBuffer` omitting `artistTags`; (12) `_coerce_and_clamp_props_dict` rounding float sliders (`scrollspeed`, `slideshowfade`) to integers; and (13) `ResourceGraphDialog` anchoring to withdrawn `TK_ROOT` `(0, 0)`.',
    fix: 'Implemented all 13 exact drop-in fixes across `danbooru_service.py` and `index.html`, verified Python compilation (`py_compile`), and synchronized the release documentation.',
  },
  {
    id: 'AUDIT-MASONRY (v2.3.10)',
    severity: 'CRITICAL MASONRY TREE LOGIC AUDIT & FIX (STUCK TILES, BLACK VOIDS & FROZEN TILES ON DISPLAY OFF/ON)',
    file: 'index.html (solveOptimalRowsPartitionForAspects, solveAspectLockedSubtree, buildSubtreeWithFixedMaskAndTopology, reflowMasonryGroupWithFlip, clearStageAll, setScreenEnabled)',
    issue: 'Resolve Stuck/Overlapping Tiles, Upper-Screen Black Voids & Frozen Tiles Peeking Behind Masonry Gaps After Display Turn-Off/On',
    cause:
      'Full audit of the v2.3.10 Masonry optimization identified four interacting bugs: (1) In `solveOptimalRowsPartitionForAspects`, hoisting `const u = b1[i1]; const aU = clamped[u];` outside the inner `i2` swap loop caused multiple swaps on the same `i1` to overwrite the first swapped tile from `b2` (dropping it from `masonryTileList` while leaving its `<div class="masonry-tile">` permanently stuck on `#stage`) and duplicate `u` across two slots (creating empty `#0b0b0d` black voids); (2) In `solveAspectLockedSubtree`, for 25–36 tiles (`7–10` groups, `numInternals > 5`), the fallback `else` branch broke out of only the inner `o` loop without updating `bestScore`, allowing `tIdx = 1` (`"caterpillar"`) to overwrite `bestRoot` and assign 85%–90% of a portrait monitor to Group 0 while crushing 31 tiles into the bottom 15%; (3) `finalizePreloadedMedia()` called `populateMasonryIfNeeded()` during active flips/pre-stages, and `reflowMasonryGroupWithFlip()` mutated `t.groupIndex` before verifying `newTileOrder.length === masonryTileList.length`, desynchronizing `t.groupIndex` from `masonryGroups` and causing permanent tile overlap; and (4) `clearStageAll()` only removed tiles still referenced in `masonryTileList`, leaving orphaned DOM nodes frozen behind the new Masonry grid when turning the display off and back on.',
    fix: 'Applied 5 surgical fixes: (1) Updated `u = v; aU = aV;` immediately on swap in `solveOptimalRowsPartitionForAspects` and guarded all index permutations with `isValidIndexPermutation(indices, n)`; (2) Extended exact bitmask search in `solveAspectLockedSubtree` up to `numInternals <= 9` (up to 10 groups / 36 tiles), restricted `n >= 7` to `"balanced"` topology, and fixed the `numInternals > 9` fallback; (3) Added `buildSubtreeWithFixedMaskAndTopology()` and stored `winTopology` / `topWinMask` / `topWinTopology` on all reflow plans so reconstructed subtrees match `plannedRects` 100%; (4) Blocked mid-flip/mid-prestage `populateMasonryIfNeeded()` mutations and validated 1-to-1 tile ID membership in `reflowMasonryGroupWithFlip()` before mutating `t.groupIndex`; and (5) Added a defensive `#stage` DOM sweep in `clearStageAll()` and `setScreenEnabled(false/true)` so zero orphaned tiles can ever survive behind the Masonry display.',
  },
  {
    id: 'REQ-34 (v2.3.10)',
    severity: 'OPTIMIZED MONDRIAN & ROWS TREE SOLVER',
    file: 'index.html (solveOptimalRowsPartitionForAspects, solveAspectLockedSubtree, propagateAspectPostOrder, evaluateSubtreeDistortion, solveGlobalMondrianPlanForProxies)',
    issue: 'Eliminate Redundant Tree Allocations, Recursive Aspect Re-Walks & O(N) Row Swap Re-Evaluations in Masonry Solvers',
    cause:
      'Previously, `solveOptimalRowsPartitionForAspects()` cloned and spliced row arrays on every pairwise swap/move attempt and recomputed all R rows (`O(R + N)`) inside a 4-pass nested loop across 5 candidate permutations per row count. Similarly, `solveAspectLockedSubtree()` built recursive tree closures and ran two separate recursive traversals (`computeRatio(root)` and `assignRects(root)`) for every bitmask in `[0, 2^(k-1))` across 8 leaf permutations without memoization or branch-and-bound pruning.',
    fix: 'Added bounded LRU memoization (`ROWS_SOLVER_CACHE` and `MONDRIAN_SUBTREE_CACHE`), deduplicated candidate leaf orders by quantized aspect signature, replaced full-row-bucket `splice()` + `evaluateBuckets()` inside the 4-pass refinement loop with `O(1)` incremental two-row delta math (`rowCostFromSumAspect()`), and refactored `solveAspectLockedSubtree()` to use flat post-order bottom-up aspect propagation (`propagateAspectPostOrder()`) with branch-and-bound cutoff pruning (`evaluateSubtreeDistortion(..., bestScore)`), accelerating full-grid and local-group solves by 6–10x.',
  },
  {
    id: 'REQ-35 (v2.3.10)',
    severity: 'STOP UNNEEDED BACKGROUND PROCESSES WHEN PAUSED',
    file: 'danbooru_service.py (is_screen_effectively_paused, ensure_screen_tag_pool_populated_async, /api) & index.html (suspendBackgroundProcessesForPause, setActiveWaapiAnimationsPaused, applyPauseStates)',
    issue: 'Stop Background Fetch, Preload, Decode, Video & Animation Processes When a Display Is Paused',
    cause:
      'Previously, pressing "PAUSE" on a display froze visual motion on `#freezeOverlayCanvas`, but `danbooru_service.py` still considered the screen an active consumer for background Danbooru tag-pool prefetches, and `index.html` allowed in-flight `/api` fetches, media preloader downloads, scratch-canvas bitmap downscaling, pre-staged Masonry `<video>`/`<img>` elements, and Web Animations API (`WAAPI`) animations to continue running in the background.',
    fix: 'Added `is_screen_effectively_paused(screen_id)` in `danbooru_service.py` so paused screens are excluded from background tag pool replenishment and `/api` refills until resumed. In `index.html`, added `suspendBackgroundProcessesForPause()` and `setActiveWaapiAnimationsPaused()` inside `applyPauseStates()`: pausing a display immediately aborts in-flight `/api` fetches, increments `preloadCancelEpoch` to cancel active image/video preloads and scratch-canvas decodes, releases pre-staged Masonry elements, pauses all `<video>` decoders and WAAPI animations, and halts `fetchNextPage()` / `pumpPreloader()` until unpaused.',
  },
  {
    id: 'REQ-36 (v2.3.10)',
    severity: 'PER-SCREEN "PAUSE DURING FULL SCREEN APPLICATION" ON/OFF SWITCH',
    file: 'danbooru_service.py (detect_fullscreen_monitors, fullscreen_monitor_worker_loop, SettingsDialog._build_display_tab) & project.json (pausefullscreen)',
    issue: 'Automatically Pause Wallpaper on Any Monitor Running a Fullscreen Game or Video Application',
    cause:
      'When playing a fullscreen game or watching a fullscreen video/movie on a monitor, running wallpaper animations, video decoders, and background preloads on that screen consumes GPU/CPU cycles unnecessarily.',
    fix: 'Added a per-screen `"Pause during full screen application"` (`pausefullscreen`, default `True`) pill switch on the right side of the same row as `"Display wallpaper on this screen"` in the Display tab. Implemented a dedicated Win32 `fullscreen_monitor_worker_loop()` thread (`GetForegroundWindow`, `IsIconic`, `DwmGetWindowAttribute(DWMWA_CLOAKED)`, `GetWindowRect`, and `MonitorFromWindow`) that inspects the active foreground window every 0.75s, excludes desktop/shell/wallpaper hosts and cloaked UWP frames, and automatically pauses/resumes the corresponding screen whenever a fullscreen application covers that monitor.',
  },
  {
    id: 'REQ-37 & REQ-38 (v2.3.10)',
    severity: 'SINGLE-ROW MASONRY LAYOUT / EDGE FILL BUTTONS & INCREASED SETTINGS WINDOW HEIGHT',
    file: 'danbooru_service.py (SettingsDialog.__init__, _build_display_tab, _update_tag_input_height)',
    issue: 'Combine Masonry Layout & Edge Fill Buttons onto One Row and Prevent Squished "Save & Apply Display Settings" Button',
    cause:
      'In Masonry display mode, stacking `Masonry Layout:` and `Mondrian Edge Fill:` as two separate labeled rows consumed extra vertical space and squished the bottom `"Save & Apply Display Settings"` button against the 700px window height ceiling.',
    fix: 'Placed both buttons side-by-side on a single 2-column row (`self.masonry_layout_row`) with the title and current value inside the buttons themselves (`"Masonry Layout: Mondrian"` ↔ `"Masonry Layout: Rows"` and `"Edge Fill: Blur"` ↔ `"Edge Fill: Black"`), and increased the base Application Settings window height from `700px` to `760px` (`min(760, max(700, sh - 40))`) so `"Save & Apply Display Settings"` always fits with generous breathing room.',
  },
  {
    id: 'REQ-31 (v2.3.8)',
    severity: 'MASONRY MID-FLIP STUCK / SLIM VERTICAL LINE BUG FIX',
    file: 'index.html (launchTileFlipPhase1, executeMasonryFlipMidpoint, cancelTileFlipAnimation, updateMasonryMode)',
    issue: 'Fix Masonry Tiles Getting Stuck Mid-Flip as a Slim Vertical Line with Animated Media Playing Through',
    cause:
      'In `launchTileFlipPhase1()`, Phase 1\'s Web Animations API (`element.animate()`) animation `anim1` (`scaleX(1) -> scaleX(0.01)`) used `fill: \'forwards\'`, and `anim1.onfinish` set `chosenTile.flipAnim = null` BEFORE calling `executeMasonryFlipMidpoint(chosenTile)`. Inside `executeMasonryFlipMidpoint()`, `cancelTileFlipAnimation(tile)` checked `if (tile.flipAnim)` (which was already `null`) and therefore never called `anim1.cancel()`. Meanwhile, the new `<video>` or animated GIF was appended to `.masonry-flip-inner` and Phase 2\'s `anim2` (`scaleX(0.01) -> scaleX(1)`) ran with `fill: \'none\'`. The moment `anim2` finished, its effect was removed (`fill: \'none\'`) and `.masonry-flip-inner` snapped back to `anim1`\'s lingering `fill: \'forwards\'` state (`transform: scaleX(0.01)`) in the WAAPI cascade—leaving a 1%-wide vertical slit surrounded by black space while the video/GIF kept playing inside.',
    fix: 'Changed `anim1` in `launchTileFlipPhase1()` from `fill: \'forwards\'` to `fill: \'none\'` (setting inline `chosenTile.flipInner.style.transform = \'scaleX(0.01)\'` during Phase 1 and clearing `tile.flipInner.style.transform = \'\'` in `executeMasonryFlipMidpoint()`), updated `cancelTileFlipAnimation()` and `cancelTileReflowAnimation()` to also cancel all active element animations via `getAnimations()`, and added elapsed-time watchdog recovery in `updateMasonryMode()` so a tile can never remain stuck mid-flip.',
  },
  {
    id: 'REQ-32 (v2.3.8)',
    severity: 'POLAROID BACKING CANVAS VERIFICATION & IMMEDIATE STATIC CARD BAKING',
    file: 'index.html (prunePolaroidStackIfNeeded, doPolaroidsOverlap, processPendingPolaroidBakes, finishFallingPolaroidItem)',
    issue: 'Verify & Ensure Polaroid Display Bakes Landed Cards onto Backing Canvas to Conserve Resources',
    cause:
      'Previously, `MAX_LIVE_POLAROID_DOM = 30` kept the first 30 landed static Polaroids alive in `#stage` as full DOM subtrees (`<div class="polaroid-item">`, `<img>`, caption `<span>`s, and Blob URLs) without baking any of them onto `#polaroidBaseCanvas` until the stack exceeded 30 items or a card was 100% occluded for 4 drops. In addition, `finishFallingPolaroidItem()` did not call `markCoverageForLandedItem(item)` upon landing or sort `pendingPolaroidBakes` by ascending `zIndex`.',
    fix: 'Added `doPolaroidsOverlap(a, b)` (computing rotated bounding-box extents) and updated `prunePolaroidStackIfNeeded()` so every landed static Polaroid (`!item.isAnimated`) that does not overlap an older live animated Polaroid below it is immediately moved into `pendingPolaroidBakes`, baked onto `#polaroidBaseCanvas`, and its DOM subtree + Blob URL destroyed via `destroyItem()`. Lowered `MAX_LIVE_POLAROID_DOM` to `10` (for live animated GIF/MP4 Polaroids) and `OCCLUDED_GRACE_DROPS` to `2`, recorded coverage immediately in `finishFallingPolaroidItem()`, and sorted `pendingPolaroidBakes` by ascending `item.id` (`zIndex`) so canvas baking strictly preserves bottom-to-top stacking order.',
  },
  {
    id: 'REQ-33 (v2.3.8)',
    severity: 'MASONRY CARDBOARD BOX LOADING SCREEN & SMOOTH FADE-IN TRANSITION',
    file: 'index.html (#masonryLoadingOverlay, drawMasonryCardboardBox, startMasonryLoadingSequence, populateMasonryIfNeeded, updateMasonryMode)',
    issue: 'Replace Stuttery One-by-One Masonry Tile Turn-On with a Brown Cardboard Box Loading Screen & Smooth Fade-In',
    cause:
      'When turning on Masonry display for a screen, `finalizePreloadedMedia()` previously called `populateMasonryIfNeeded()` as each individual file finished decoding—mounting tiles one-by-one and executing 12–36 consecutive full-grid Mondrian/Rows layout solves and overlapping WAAPI reflow animations while the preloader was still decoding textures.',
    fix: 'Added `#masonryLoadingOverlay` (`background: #0b0b0d`) and `#masonryBoxCanvas` (`drawMasonryCardboardBox(openProgress)` matching `create_cardboard_box_icon()` in `danbooru_service.py`). When Masonry mode is turned on (`startMasonryLoadingSequence()`), the screen shows the closed brown cardboard box (`openProgress = 0`) while tiles preload quietly in the background (`masonryLoadPhase === \'loading\'`). Once the tile batch is ready, `populateMasonryIfNeeded(true)` mounts and lays out the complete Masonry grid in a single atomic pass (`rebuildFullMasonryLayout(false)`), the cardboard box top flaps smoothly fold open (`masonryLoadPhase === \'opening\'`), and the overlay fades smoothly from black (`opacity: 1 -> 0`) to reveal the complete Masonry display.',
  },
  {
    id: 'REQ-28 (v2.3.7)',
    severity: 'ON/OFF SLIDE SWITCH FOR "DISPLAY WALLPAPER ON THIS SCREEN"',
    file: 'danbooru_service.py (SettingsDialog._build_display_tab, _draw_screen_enable_switch)',
    issue: 'Replace "Display wallpaper on this screen" Checkbox with an On/Off Slide Switch',
    cause:
      'User requested updating the "Display wallpaper on this screen" checkbox to be an on/off slide switch positioned on the left with the label on the right.',
    fix: 'Replaced `self.screen_enable_chk` with a custom theme-aware `tk.Canvas` pill toggle switch (`self.screen_enable_switch`, `width=42, height=22`) packed on the left and paired with a clickable `self.screen_enable_lbl` ("Display wallpaper on this screen") on the right. Toggling either widget flips `self.screen_enabled_var`, redraws the sliding circular thumb and pill track (`#0067c0` when On, neutral muted track when Off), and immediately triggers `_schedule_live_apply()`.',
  },
  {
    id: 'REQ-29 (v2.3.7)',
    severity: 'PER-SCREEN V-SYNC ON/OFF BUTTON & CONDITIONAL TARGET FPS INPUT BOX',
    file: 'danbooru_service.py, index.html, project.json',
    issue: 'Add Per-Screen "V-Sync On" / "V-Sync Off" Button & Conditional Target FPS (15–240) Input Box to the Right',
    cause:
      'User requested adding a button under "Display wallpaper on this screen" to enable/disable V-Sync ("V-Sync On" or "V-Sync Off") for the selected display screen, with a Target FPS input box appearing to the right of the button when V-Sync is Off.',
    fix: 'Added `"vsync"` (`bool`, default `True`) and `"targetfps"` (`15–240`, default `60`, `"condition": "vsync.value == false"`) to `project.json` and `danbooru_service.py`. Built `self.vsync_row` directly under `enable_row` containing `self.vsync_btn` ("V-Sync On" / "V-Sync Off") on the left and `self.target_fps_subframe` ("Target FPS (15 – 240):" + numeric entry box) packed immediately to the right of the button whenever V-Sync is Off. In `index.html`, `VSYNC_ENABLED = true` runs locked to native monitor `requestAnimationFrame` refresh rate, while `VSYNC_ENABLED = false` paces updates to `TARGET_FPS` (`15–240` FPS) via a drift-compensated accumulator.',
  },
  {
    id: 'REQ-30 (v2.3.7)',
    severity: 'FLUID STUTTER-FREE POLAROID DROP ANIMATIONS',
    file: 'index.html (launchPolaroidWaapiDrop, processPendingPolaroidBakes, bakePolaroidToCanvas, pumpPreloader)',
    issue: 'Eliminate Intermittent Frame Stutters During Polaroid Media Drops',
    cause:
      'Polaroid drop animations previously stuttered when: (1) `prunePolaroidStackIfNeeded()` synchronously invoked `bakePolaroidToCanvas()` (with a 24px Gaussian `shadowBlur` pass over a high-DPI fullscreen canvas) and `destroyItem()` right as a card landed or while another card was falling; (2) `pumpPreloader()` executed scratch-canvas 4K downscaling (`toBlob`), `computeAmbientBackdropDataUrl()`, or undecoded GIF frame paints during active drops; and (3) `.polaroid-item.falling` mutated a 64px blur shadow from `scale(3.6)` every frame after DOM insertion.',
    fix: 'Implemented a 3-part Polaroid fluidity upgrade: (1) Off-main-thread Web Animations API (`launchPolaroidWaapiDrop` with `cubic-bezier(0.22, 1, 0.36, 1)`) with initial transform applied prior to DOM insertion and unified GPU layer shadow geometry (`contain: layout style paint; backface-visibility: hidden;`); (2) Deferred background canvas baking (`pendingPolaroidBakes` & `processPendingPolaroidBakes`) that bakes at most 1 occluded card per frame strictly when `fallingItems.length === 0`, using fast layered rounded-rect shadows instead of 24px `shadowBlur`; and (3) Pre-decoded GIF & static images via `img.decode()`, 1280px Polaroid texture bound, and suspended scratch-canvas downscaling while `isAnyPolaroidFalling()` is true.',
  },
  {
    id: 'REQ-18 (v2.3.6)',
    severity: 'RUNTIME-ONLY SETTINGS TAB & SELECTED DISPLAY MEMORY',
    file: 'danbooru_service.py (_RUNTIME_LAST_SETTINGS_TAB, _RUNTIME_LAST_SELECTED_SCREEN_ID)',
    issue: 'Reopen Application Settings on Last Active Tab & Selected Display Within Current App Session Only',
    cause:
      'Previously, closing and reopening the Application Settings window always reset to the Display tab and the first monitor in the dropdown.',
    fix: 'Added in-memory process globals `_RUNTIME_LAST_SETTINGS_TAB` and `_RUNTIME_LAST_SELECTED_SCREEN_ID` (never written to `config.json` or `project.json`). On initial application launch they start as `None`, defaulting to the `Display` tab and first screen; when the user switches tabs or selects a display and closes/reopens Settings while the application is running, the last tab and selected screen are automatically restored.',
  },
  {
    id: 'REQ-19 (v2.3.6)',
    severity: 'MONDRIAN EDGE FILL (BLUR / BLACK) IN BOTH MONDRIAN & ROWS',
    file: 'danbooru_service.py, index.html, project.json',
    issue: 'Extend Mondrian Edge Fill (Blur / Black) to Masonry Rows & Persist Button Across Both Layouts',
    cause:
      '`self.mondrian_edge_row` was previously hidden via `pack_forget()` when `Rows` layout was selected, and `#stage.rows-mode` forced black tile backgrounds.',
    fix: 'Kept `self.mondrian_edge_row` packed directly below `Masonry Layout:` in both `Mondrian` and `Rows` modes, updated `project.json` condition to `"displaymode.value == \'masonry\'"`, and updated `index.html` (`#stage.masonry-black-mode`, `applyTileAmbientBackdrop`, `refreshAllMasonryTileBackdrops`, `renderFreezeSnapshot`) so `"Blur"` and `"Black"` edge fill persist and render across both `Mondrian` and `Rows`.',
  },
  {
    id: 'REQ-20 (v2.3.6)',
    severity: 'COMBINED 3-PART MASONRY GPU UTILIZATION OPTIMIZATION',
    file: 'index.html (reflowMasonryGroupWithFlip, launchTileFlipPhase1, executeMasonryFlipMidpoint)',
    issue: 'Eliminate ~40% GPU Spikes During Masonry Tile Flip & Reshuffling While Preserving Fluidity',
    cause:
      'Masonry tile flips previously combined 3D depth-buffer perspective (`perspective: 1100px`, `preserve-3d`, `rotateY`), per-frame blurred `background-image` resampling on up to 36 moving tiles simultaneously, forced synchronous DOM reflows, and frequent 36-tile global reshuffles.',
    fix: 'Combined all three GPU optimizations: (1) Off-main-thread Web Animations API (`element.animate()`) for neighbor FLIP transitions and card turns with scoped `will-change: transform` only on moving tiles; (2) Lightweight 2D horizontal card turn (`scaleX(1 -> 0.01 -> 1)`) with zero 3D depth-buffer allocation and temporary suspension of `.masonry-flip-inner` `background-image` resampling during `.is-flipping` / `.is-reflowing`; and (3) Local-first neighbor reflows, 960px Masonry texture downscaling ceiling, and 60 FPS frame pacing.',
  },
  {
    id: 'REQ-21 (v2.3.6)',
    severity: 'MASONRY ROWS VARIABLE ROW HEIGHTS FOR ZERO EXTRA GAPS',
    file: 'index.html (solveOptimalRowsPartitionForAspects, buildGooglePhotosJustifiedLayout)',
    issue: 'Allow Row Height Variance in Masonry Rows to Eliminate Intra-Row & Inter-Row Gaps on Uncropped Media',
    cause:
      'Previously, `solveOptimalRowsPartitionForAspects()` penalized row height variance (`heightVar * 0.42`) and only searched narrow row counts `R ± 1`. When the sum of natural row heights `totalNaturalH` did not match `availH`, `normScale = availH / totalNaturalH` scaled all row heights uniformly while widths remained fixed to `availW`, mismatching tile box aspect ratios from uncropped media (`object-fit: contain`) and creating horizontal or vertical gaps.',
    fix: 'Redesigned `solveOptimalRowsPartitionForAspects()` to embrace natural variable row heights `H_r = W_avail,r / sum(A_i)`, expanded row-count search across `R in [1, 12]`, and added multi-candidate DP + pairwise inter-row tile swap & move refinement to drive `sum(H_r) -> H_avail` (`normScale ≈ 1.000`). Every tile box aspect ratio `(w_i / H_r)` now matches its uncropped media aspect ratio `A_i`, leaving only the configured `Gap (0 – 10 px)`.',
  },
  {
    id: 'REQ-22 & REQ-23 (v2.3.6)',
    severity: 'STRICT APP-ONLY RESOURCE GRAPH TELEMETRY & TITLE CLEANUP',
    file: 'danbooru_service.py (AppResourceMonitor & ResourceGraphDialog)',
    issue: 'Ensure Resource Graph Only Shows Wallpaper App Resources & Remove "(TASK MANAGER VIEW)" Title Suffix',
    cause:
      'Process enumeration previously included any child process (such as external browsers launched via links), PDH wildcard GPU counters summed orthogonal engines (`3D` + `Copy` + `VideoDecode`), and a synthetic CPU-to-GPU multiplier (`child_ticks_delta * 45.0`) inflated GPU spikes.',
    fix: 'Filtered child processes in `_enumerate_app_process_tree()` strictly to `msedgewebview2.exe` and the wallpaper executable, grouped PDH GPU counters by engine type (`engtype_*`) to report the true max engine load for app PIDs without double-counting, removed the synthetic `child_ticks_delta * 45.0` inflation when PDH is active, and retitled the window to `"📊 PERFORMANCE — RESOURCE GRAPH"`.',
  },
  {
    id: 'REQ-24, REQ-25 & REQ-26 (v2.3.6)',
    severity: 'CLICKABLE POST # HYPERLINK, HEADER RETITLE & +1PT FONT SIZE',
    file: 'danbooru_service.py (SettingsDialog._build_display_tab & _refresh_displayed_media_tags_box)',
    issue: 'Clickable "Post #<id>" Browser Hyperlink, Retitled Header & +1pt Font Size Increase',
    cause:
      'User requested turning "Post #" into a clickable hyperlink opening the Danbooru post in the default browser, retitling the header to "DISPLAYED MEDIA TAGS (CLICK TO ADD):", and increasing both font sizes by +1pt.',
    fix: 'Retitled `self.media_tags_hdr_lbl` to `"DISPLAYED MEDIA TAGS (CLICK TO ADD):"` with font `("Segoe UI", 9, "bold")`, styled `self.media_tags_post_lbl` with `("Segoe UI", 9, "bold", "underline")` and `cursor="hand2"`, and bound left-click (`_on_post_link_clicked`) to open `https://danbooru.donmai.us/posts/<id>` in the default web browser via `webbrowser.open(u, new=2)`.',
  },
  {
    id: 'REQ-27 (v2.3.6)',
    severity: 'POLAROID BOTTOM-LEFT "By: <artist>" RED ARTIST TAG CAPTION',
    file: 'index.html (spawnNextPolaroidItem, bakePolaroidToCanvas, renderFreezeSnapshot)',
    issue: 'Display "By: <artist>" with Red Artist Tag(s) on the Bottom-Left Chin of Every Polaroid',
    cause:
      'User requested adding "By:" followed by the artist (or artists) tag from the post in Danbooru\'s red artist tag color aligned on the left side of the bottom section of each Polaroid.',
    fix: 'Wired `post.tag_string_artist` through `pumpPreloader()` and `finalizePreloadedMedia()`, added `.polaroid-caption` / `.polaroid-by` (`"By: "`) / `.polaroid-artist` (`#c00004` Danbooru artist red) inside the 34px bottom Polaroid chin in `spawnNextPolaroidItem()`, and added matching `drawPolaroidArtistCaption()` Canvas 2D rendering in `bakePolaroidToCanvas()` and `renderFreezeSnapshot()`.',
  },
  {
    id: 'AUDIT-01 (v2.3.5)',
    severity: 'CRITICAL 64-BIT WIN32 CTYPES SIGNATURE & HANDLE TRUNCATION FIX',
    file: 'danbooru_service.py (AppResourceMonitor & _detect_primary_gpu_name)',
    issue: 'Missing argtypes/restype on Win32 kernel32, user32, psapi & pdh APIs Causing 64-Bit Handle Truncation & Broken INVALID_HANDLE_VALUE Check',
    cause:
      'In Section 6B, `CreateToolhelp32Snapshot`, `Process32FirstW`, `Process32NextW`, `OpenProcess`, `GetProcessTimes`, `CloseHandle`, `GlobalMemoryStatusEx`, `K32GetProcessMemoryInfo`, `EnumDisplayDevicesW`, and `pdh` functions were invoked without declaring `argtypes` or `restype`. By default, Python `ctypes` returns a signed 32-bit `c_int`, which truncated 64-bit Windows `HANDLE` pointers above `0x7FFFFFFF` and caused `if snap == ctypes.c_void_p(-1).value:` (`-1 == 18446744073709551615`) to always evaluate to `False` on snapshot failure.',
    fix: 'Declared explicit 64-bit safe `argtypes` and `restype` (`wintypes.HANDLE`, `ctypes.c_void_p`, `wintypes.BOOL`, `wintypes.LONG`) across all `kernel32`, `user32`, `psapi`, and `pdh` calls, defined `INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value`, and guarded both `snap` and `h_proc` against `None`, `0`, `-1`, and `INVALID_HANDLE_VALUE`.',
  },
  {
    id: 'AUDIT-02 (v2.3.5)',
    severity: 'HIGH MEMORY CYCLING & UNBOUNDED CACHE EVICTION FIX',
    file: 'danbooru_service.py (POST_TAGS_CACHE, TAG_CATEGORY_CACHE, TAG_POOLS, DOH_CACHE)',
    issue: 'Orphaned Entries in POST_TAGS_CACHE Deque Eviction & Unbounded Growth in TAG_CATEGORY_CACHE / TAG_POOLS / DOH_CACHE',
    cause:
      'In `extract_and_cache_post_tags_locked`, `POST_TAGS_ORDER` was initialized as `deque(maxlen=2500)` and `.append(pid)` ran before `if len(POST_TAGS_ORDER) >= 2500:`. At capacity, `.append(pid)` silently dropped the oldest PID before `.popleft()` popped the second-oldest PID—permanently orphaning the oldest entry in `POST_TAGS_CACHE` on every post! Furthermore, `/report_shown` inserted into `POST_TAGS_CACHE` without updating `POST_TAGS_ORDER`, and `TAG_CATEGORY_CACHE`, `TAG_POOLS`, and `DOH_CACHE` had no upper size bounds.',
    fix: 'Replaced `POST_TAGS_CACHE` + `POST_TAGS_ORDER` with an `OrderedDict`-backed `cache_post_tags_locked(pid, tags_list)` helper enforcing strict `MAX_POST_TAGS_CACHE = 2500` LRU eviction across both `extract_and_cache_post_tags_locked` and `/report_shown`. Converted `TAG_CATEGORY_CACHE` (`MAX_TAG_CATEGORY_CACHE = 10000` preserving `SEEDED_TAG_CATEGORIES`), `TAG_POOLS` (`MAX_TAG_POOLS = 16`), and `DOH_CACHE` (`MAX_DOH_CACHE_ENTRIES = 128` + TTL pruning) to bounded `OrderedDict` caches.',
  },
  {
    id: 'AUDIT-03 (v2.3.5)',
    severity: 'HIGH STREAMING MEMORY SPIKE FIX',
    file: 'danbooru_service.py (iter_response_chunks & HybridDoHSession.get)',
    issue: 'Eager Full-File RAM Buffering in iter_response_chunks() and Missing stream=stream Forwarding in curl_cffi',
    cause:
      '`iter_response_chunks(resp)` previously checked `content = getattr(resp, "content", None)` before `if hasattr(resp, "iter_content"):`, and `HybridDoHSession.get()` omitted `stream=stream` when calling `self._curl_session.get()`. Accessing `resp.content` forced `curl_cffi` to download and buffer the entire 15 MB MP4 or 25 MB image in RAM before yielding the first 64 KB chunk.',
    fix: 'Forwarded `stream=stream` to `self._curl_session.get()` and reordered `iter_response_chunks()` to stream via `resp.iter_content(chunk_size=65536)` first, eliminating full-payload memory spikes during `/media` proxy streaming.',
  },
  {
    id: 'AUDIT-04 (v2.3.5)',
    severity: 'MEDIUM DEAD HEADERS, UNUSED IMPORTS & BLOB URL LIFECYCLE CLEANUP',
    file: 'danbooru_service.py & index.html',
    issue: 'Unused import math, Unwired FORBIDDEN_PAYLOAD_SIGNATURES, Dead Constants/Methods & Blob URL Error-Path Revocation',
    cause:
      'Static audit identified unused `import math`, unwired `FORBIDDEN_PAYLOAD_SIGNATURES`, dead module constants (`CLOUDFLARE_DOH_ENDPOINT`, `DANBOORU_CATEGORY_ORDER`, `DANBOORU_CATEGORY_NAMES`), dead `self._prev_gpu_sub_times`, dead `ResourceGraphDialog._get_ram_scale_ceiling_mb`, dead `tile.pendingReady` references in `index.html`, and unrevoked `blobUrl` handles if `scaledImg.onerror` or GIF fallback `.catch()` triggered.',
    fix: 'Removed all dead imports, constants, attributes, and methods; actively wired `FORBIDDEN_PAYLOAD_SIGNATURES` into `verify_media_magic_bytes()`; added explicit `URL.revokeObjectURL` cleanup inside `scaledImg.onerror` and GIF `.catch()` fallback paths; and preserved all GIF/backdrop fields when requeueing Scroll items on axis changes.',
  },
  {
    id: 'AUDIT-05 (v2.3.5)',
    severity: 'MEDIUM PROJECT.JSON SCHEMA & CSP HEADER SYNCHRONIZATION',
    file: 'danbooru_service.py, index.html, project.json',
    issue: 'Duplicate Order Index & Missing Combo Options/Conditions in get_default_properties_dict() + CSP frame-src Parity',
    cause:
      'In `get_default_properties_dict()`, `"displaymode"` and `"scrolldirection"` both had `"order": 2` and omitted `"options"`, `"condition"`, and `"editable"`, causing `_normalize_project_dict_in_place()` to strip those keys when saving `project.json`. In addition, `<meta http-equiv="Content-Security-Policy">` in `index.html` omitted `frame-src \'none\';`.',
    fix: 'Synchronized `get_default_properties_dict()` 1:1 with `project.json` (orders `0` through `16`, full `"options"` arrays, `"condition"` expressions, and `"editable": True` flags) and added `frame-src \'none\';` to the CSP headers in both `index.html` and `danbooru_service.py`.',
  },
  {
    id: 'REQ-15 (v2.3.4)',
    severity: 'v2.3.4 ZERO-BLUR MONDRIAN RESHUFFLE & RESIZE ON TILE FLIP',
    file: 'index.html (solveAspectLockedSubtree, precomputeGroupReflowPlan, reflowMasonryGroupWithFlip)',
    issue: 'Eliminate Tile Edge Blur on Mondrian Media Tile Flips via Local Group & Full-Grid Reshuffle/Resize',
    cause:
      'Previously, Mondrian mode multiplied every tile and group aspect ratio by a random `sizeJitter` (`0.92 + Math.random() * 0.16`), clamped BSP split ratios to `[0.22, 0.78]`, only tested a single balanced binary tree with `allowReorder = false` on tile flip, and kept the flipped group\'s outer bounding box `(group.w, group.h)` frozen—forcing visible blurred filler bars whenever an incoming media file had a different aspect ratio.',
    fix: 'Eliminated random `sizeJitter` (`1.0`), widened `propagateAspectBottomUp()` ratio bounds to `[0.06, 0.94]`, added `generateCandidateLeafOrders()` + balanced `(2+2)` and caterpillar `(1+3)` binary tree topologies in `solveAspectLockedSubtree()`, and implemented a two-tier reflow solver in `precomputeGroupReflowPlan()` / `reflowMasonryGroupWithFlip()`: Tier 1 reshuffles and resizes sibling tiles inside the local group (`allowReorder = true`) and resizes adjacent group bounding boxes via `resizedTopRoot`; Tier 2 escalates to a full-grid group re-partition (`solveGlobalMondrianPlanForProxies`, `scope: "global"`) whenever local distortion exceeds `0.012`, smoothly animating all tiles via GPU FLIP (`translate3d` + `scale3d`).',
  },
  {
    id: 'REQ-16 (v2.3.4)',
    severity: 'v2.3.4 MONDRIAN "BLUR" / "BLACK" EDGE FILL TOGGLE BUTTON',
    file: 'danbooru_service.py, project.json, index.html',
    issue: 'Dedicated "Mondrian Edge Fill:" Row ("Blur  ⇄" / "Black  ⇄") Below "Masonry Layout:" When Mondrian Is Active',
    cause:
      'User requested a new settings button when Masonry Mondrian is selected that alternates between "Blur" (maintaining tile edge blur to fit into the grid) and "Black" (removing tile edge blur to show solid black space matching inter-tile gaps), placed on a dedicated row directly below Masonry Layout when Mondrian is active.',
    fix: 'Added `"masonryedgefill"` (`"blur"` | `"black"`) to `project.json` and `danbooru_service.py`. Built `self.mondrian_edge_row` (`"Mondrian Edge Fill:"` label + `self.masonry_edge_fill_btn` toggling `"Blur  ⇄"` / `"Black  ⇄"`) packed directly below `self.masonry_layout_row` when `Mondrian` is active and hidden via `pack_forget()` when `Rows` is active. Added `#stage.mondrian-black-mode .masonry-flip-inner` (`background-image: none !important; background-color: #0b0b0d !important;`) and `switchMasonryEdgeFill()` in `index.html`.',
  },
  {
    id: 'REQ-17 (v2.3.4)',
    severity: 'v2.3.4 TARGET TILE COUNT (4 – 36, ±25% WINDOW) FOR MONDRIAN & ROWS',
    file: 'danbooru_service.py, project.json, index.html',
    issue: 'Rename "Tile Count" to "Target Tile Count (4 – 36)" with Dynamic ±25% Flexibility Across Both Mondrian and Rows',
    cause:
      'User requested updating the Masonry slider from "Tile Count" to "Target Tile Count" across both Masonry Mondrian and Masonry Rows, loosening the target count with a dynamic ±25% range so more or fewer uncropped tiles can be displayed on initial build, layout changes, and tile flips to minimize edge blur/black space in Mondrian and eliminate cropping in Rows.',
    fix: 'Updated `NUMERIC_SPECS["masonrytiles"]["label"]` in `danbooru_service.py` and `"masonrytiles"` in `project.json` to `"Target Tile Count (4 – 36)"` active in both `Mondrian` and `Rows` modes. Implemented `getTargetTileCountBounds()` (`delta = Math.max(1, Math.round(target * 0.25))`, clamped to `[4, 36]`), `getDesiredMasonryTileCount()`, `adjustMasonryTileCountOnFlipIfBeneficial()`, and `solveOptimalRowsPartitionForAspects()` (dynamic programming uncropped row partitioner) in `index.html`.',
  },
  {
    id: 'REQ-13 (v2.3.3)',
    severity: 'v2.3.3 SAVED SEARCHES BAR BUTTON & MARQUEE DROPDOWN',
    file: 'danbooru_service.py (SettingsDialog._build_display_tab & render_saved_dropdown)',
    issue: 'Debugged Missing Saved Searches Arrow & Added Full-Span "Saved Searches ▾" Button Above TAGS Search Bar',
    cause:
      'In v2.3.2, `self.tag_input = tk.Text(self.search_container, ...)` omitted an explicit `width` (defaulting to `width=80` chars ≈ 640px) and was packed `side="left", fill="both", expand=True` before `self.saved_arrow_btn.pack(side="right", fill="y")`, causing Tkinter to clip the right-side arrow off the container edge. User requested placing a "Saved Searches" button above the TAGS= search box between the Page/Pool indicator and the Refresh button (taking up the width between them), standardizing all top-row button heights, using "Save Search Tags" as the first dropdown option, showing a brief "Saved Search Tags already exists" popup for duplicates, adding a small trash-can delete button on the right of each row, and continuously loop-scrolling long saved searches horizontally.',
    fix: 'Removed the internal arrow from `self.search_container` (and set `width=20` on `self.tag_input`). Standardized all items in `self.search_controls_row` (`self.status_frame`, `self.saved_searches_btn_frame`, `self.refresh_btn_frame`, `self.prev_btn_frame`, `self.next_btn_frame`, `self.pause_btn_frame`) to `height=28` with `pack_propagate(False)`. Packed `self.saved_searches_btn_frame` (`"Saved Searches  ▾"`) with `side="left", fill="x", expand=True` between the Page/Pool badge and the Refresh button. Updated `render_saved_dropdown()` to open below the `TAGS =` box spanning its full width, with `"Save Search Tags"` at the top, a 2-second floating toast (`"Saved Search Tags already exists"`), a `tk.Canvas` continuous horizontal marquee loop (`_tick_saved_dropdown_marquee`) for long saved searches, and a `🗑` trash-can delete button on the right of each row.',
  },
  {
    id: 'REQ-14 (v2.3.3)',
    severity: 'v2.3.3 DARK MODE SETTINGS TABS & 2PX TAB SPACING',
    file: 'danbooru_service.py (SettingsDialog.__init__ & _update_settings_tabs_theme)',
    issue: 'Dark Mode Application Settings Tabs with 1px Contrasting White Outline & 2px Spacing Between Tabs',
    cause:
      'When Application Theme was set to Dark Mode, Windows native `ttk.Notebook` (`uxtheme.dll`) ignored `TNotebook.Tab` background styling and rendered tabs white, and adjacent tabs had 0px spacing.',
    fix: 'Replaced `ttk.Notebook` tab headers with a custom theme-aware tab bar (`self.tab_bar_frame`, `_tab_header_widgets`, `_select_settings_tab`, `_update_settings_tabs_theme`). Each tab (`Credentials`, `Display`, `Logs`) is packed with `padx=(0, 2)` for a crisp 2px separation, and in Dark Mode uses `#232329` (inactive) / `#0067c0` (active) with white text and a `1px` contrasting white outline (`highlightthickness=1, highlightbackground="#ffffff"`).',
  },
  {
    id: 'REQ-11 (v2.3.2)',
    severity: 'v2.3.2 DYNAMIC SEARCH BOX HEIGHT',
    file: 'danbooru_service.py (SettingsDialog._update_tag_input_height)',
    issue: 'Dynamic Multi-Line Height Scaling (1–5 Lines) for Long or Numerous Search TAGS',
    cause:
      'User requested dynamically scaling the height of the Search TAGS box when there are many search tags or very long tags so the user never types a search tag without being able to see it.',
    fix: 'Changed `self.tag_input` from `wrap="none"` to `wrap="word"` and implemented `_update_tag_input_height(self)` which measures wrapped display lines (`self.tag_input.count("1.0", "end-1c", "displaylines")` with character-width fallback), dynamically adjusts `self.tag_input.configure(height=target_lines)` from 1 up to 5 lines, resizes the Settings window geometry accordingly, and updates `_recolor_search_input_tags()` to use character offsets (`1.0 + N chars`) across wrapped lines.',
  },
  {
    id: 'REQ-12 (v2.3.2)',
    severity: 'v2.3.2 FOCUS-OUT AUTO-SEARCH',
    file: 'danbooru_service.py (SettingsDialog._on_tag_input_focus_out)',
    issue: 'Wait Until Search Box Loses Focus (Caret Stops Blinking) Before Running Auto-Search',
    cause:
      'User requested updating the automatic search on tag added or deleted to wait until the search box is no longer being typed in (meaning wait until the vertical line pipe | is no longer blinking in the search box) to prevent preemptive auto-searches.',
    fix: 'Removed the 1-second `<KeyRelease>` timer while typing in `self.tag_input`. Bound `<FocusIn>` and `<FocusOut>` on `self.tag_input` plus click-outside focus release (`_defocus_tag_input_on_outside_click`) across Display tab frames and labels so clicking outside the Search TAGS box moves focus away (stopping the blinking vertical pipe cursor) and immediately triggers `_execute_auto_tag_refresh()` if the tags changed.',
  },
  {
    id: 'REQ-01..03',
    severity: 'v2.3.0 UI ARCHITECTURE',
    file: 'danbooru_service.py (SettingsDialog._build_display_tab)',
    issue: 'Removed Separate Search Window & Embedded Per-Screen Playback + TAGS Controls in Display Tab',
    cause:
      'User requested removing the standalone floating search window (`FloatingSearchBar`) and placing its features into the Display tab under the "Select Screen" dropdown and the "Display wallpaper on this screen" checkbox without a minimize button, with Refresh (⟳), Previous (◀), Next (▶), and Pause (PAUSE) placed above the new TAGS search bar.',
    fix: 'Removed `FloatingSearchBar` and the Credentials tab lock toggle. Built `self.search_subpanel` in `SettingsDialog._build_display_tab()` directly below `screen_row` and `enable_row` (no minimize button). Placed `self.search_controls_row` (status badge + `Saved Searches ▾` + `⟳`, `◀`, `▶`, `PAUSE` wired strictly to the currently selected screen) directly above `self.tag_search_row` (`TAGS =`).',
  },
  {
    id: 'REQ-04..05',
    severity: 'v2.3.0 MULTI-SCREEN & DEDUPLICATION',
    file: 'danbooru_service.py, index.html, project.json',
    issue: 'Independent Per-Screen TAGS Search, No-Fetch Guard for Unchecked Screens & Shared Tag-Pool Reuse',
    cause:
      'User requested independent TAGS searches per displaying screen, skipping all media fetching if a screen is not checked to display, and reusing the same fetched media data when multiple screens share identical TAGS.',
    fix: 'Added per-screen `"searchtags"` in `project.json` and `danbooru_service.py`. Implemented `TAG_POOLS[canonical_pool_key(tags)]` so multiple screens using the same tags pull from a single shared upstream fetch buffer while tracking independent per-screen `seen_ids` cursors. Enforced `if not sc_cfg.get("enabled", True): return []` in `/api`, `fill_tag_pool`, and `ensure_screen_tag_pool_populated_async`, and initialized `SCREEN_ENABLED = false` in `index.html` until `/properties` confirms the screen is enabled.',
  },
  {
    id: 'REQ-06..08',
    severity: 'v2.3.0 DANBOORU TAG COLORS & 4-LAYER BOX',
    file: 'danbooru_service.py & index.html',
    issue: 'Below-Input Auto-Suggestions, Permanent 4-Layer Scrollable Displayed Media Tags Box & Danbooru Category Colors',
    cause:
      'User requested auto-suggestions to populate below the TAGS search box, a permanent 4-layer scrollable box below the TAGS search box showing all tags of the selected screen\'s most recently displayed media (with click-to-append), and Danbooru category color coordination across all tag locations.',
    fix: 'Positioned `self.suggest_dropdown` and `self.saved_dropdown` strictly below `self.search_container` (`ry = rooty + height + 2`). Added `self.media_tags_text` (`height=4, wrap="word"` + vertical `ttk.Scrollbar`) populated via `GET /report_shown?screen=<id>&post_id=<id>` from `index.html`. Configured `DANBOORU_TAG_COLORS` (0=General Blue, 1=Artist Red, 3=Copyright Purple, 4=Character Green, 5=Meta Orange) across `self.tag_input`, `self.suggest_labels`, `self.saved_dropdown`, and `self.media_tags_text`.',
  },
  {
    id: 'REQ-09',
    severity: 'v2.3.0 SYSTEM TRAY UX',
    file: 'danbooru_service.py (setup_tray)',
    issue: 'Direct System Tray Click to Immediately Open Settings Window',
    cause:
      'User requested that the Danbooru Wallpaper system tray icon no longer require a right-click menu selection to open Settings—left-click opens Settings immediately and right-click shows the Exit menu.',
    fix: 'Updated `setup_tray()` with `pystray.MenuItem("Settings", on_tray_settings, default=True)` so left-clicking the tray icon invokes `on_tray_settings` immediately, while right-clicking opens the context menu with `Settings` and `Exit`.',
  },
  {
    id: 'FIX-01..02',
    severity: 'v2.3.1 BUG FIXES',
    file: 'danbooru_service.py & index.html',
    issue: 'Display Mode Persistence & Live Refresh of Displayed Media Tags',
    cause:
      'Fixed `get_or_create_tag_pool_locked(new_tags)` call signature in `save_display_settings()` and `_poll_display_status()`, added `SettingsDialog.on_screen_media_displayed` for immediate push updates on `/report_shown`, and updated `updateScrollMode()` in `index.html` to report media items as they enter the visible viewport.',
    fix: 'Ensured display mode changes persist and take effect immediately on the active wallpaper WebView2 instance, and live media tag updates appear in real time.',
  },
];

const PYINSTALLER_COMMANDS = `# 1. Install required packages into the same Python environment used by PyInstaller
pip install pyinstaller pywebview pystray pillow curl_cffi

# 2. Build the single-file Windows executable (--onefile --noconsole)
#    Includes icon.ico (Danbooru cardboard box desktop icon), index.html, project.json, and curl_cffi
pyinstaller --noconfirm --onefile --noconsole ^
  --name "DanbooruWallpaper" ^
  --icon "icon.ico" ^
  --add-data "index.html;." ^
  --add-data "project.json;." ^
  --add-data "icon.ico;." ^
  --hidden-import "curl_cffi" ^
  --collect-all "curl_cffi" ^
  danbooru_service.py`;

export default function App() {
  const [selectedFile, setSelectedFile] = useState<FileKey>('danbooru_service.py');
  const [activeTab, setActiveTab] = useState<ViewTab>('code');
  const [fileContents, setFileContents] = useState<Record<string, string>>({});
  const [copiedKey, setCopiedKey] = useState<string | null>(null);
  const [uiTheme, setUiTheme] = useState<'dark' | 'light'>('dark');

  // Interactive Display Tab Simulator State
  const [simSettingsTab, setSimSettingsTab] = useState<'credentials' | 'display' | 'logs'>('display');
  const [simScreen, setSimScreen] = useState<'screen_1' | 'screen_2'>('screen_1');
  const [simScreensState, setSimScreensState] = useState<{
    screen_1: {
      enabled: boolean;
      pauseFullscreen: boolean;
      vsync: boolean;
      targetFps: string;
      paused: boolean;
      tags: string;
      appliedTags: string;
      mode: string;
      postIdx: number;
    };
    screen_2: {
      enabled: boolean;
      pauseFullscreen: boolean;
      vsync: boolean;
      targetFps: string;
      paused: boolean;
      tags: string;
      appliedTags: string;
      mode: string;
      postIdx: number;
    };
  }>({
    screen_1: {
      enabled: true,
      pauseFullscreen: true,
      vsync: true,
      targetFps: '60',
      paused: false,
      tags: 'scenery no_humans highres',
      appliedTags: 'scenery no_humans highres',
      mode: 'masonry',
      postIdx: 0,
    },
    screen_2: {
      enabled: true,
      pauseFullscreen: true,
      vsync: false,
      targetFps: '120',
      paused: false,
      tags: 'genshin_impact furina_(genshin_impact) wlop',
      appliedTags: 'genshin_impact furina_(genshin_impact) wlop',
      mode: 'polaroid',
      postIdx: 0,
    },
  });
  const [simSavedSearches, setSimSavedSearches] = useState<string[]>([
    'scenery no_humans highres',
    'genshin_impact furina_(genshin_impact) wlop',
    'makoto_shinkai original scenery no_humans starry_sky night cloud mountain reflection water outdoors horizon highres absurdres',
  ]);
  const [simShowSuggest, setSimShowSuggest] = useState(false);
  const [simShowSavedDropdown, setSimShowSavedDropdown] = useState(false);
  const [simTagInputFocused, setSimTagInputFocused] = useState(false);
  const [simAutoSearchNotice, setSimAutoSearchNotice] = useState<string | null>(null);
  const [simDuplicateToast, setSimDuplicateToast] = useState<string | null>(null);

  // Interactive Masonry Mondrian vs. Uncropped Rows Simulator State
  const [simMasonryLayout, setSimMasonryLayout] = useState<'mondrian' | 'rows'>('mondrian');
  const [simMasonryEdgeFill, setSimMasonryEdgeFill] = useState<'blur' | 'black'>('blur');
  const [simMasonryTiles, setSimMasonryTiles] = useState<number>(12);
  const [simMasonryGap, setSimMasonryGap] = useState<number>(4);
  const [simMasonryDelay, setSimMasonryDelay] = useState<number>(5);
  const [simFlipGeneration, setSimFlipGeneration] = useState<number>(0);
  const [simLastFlipScope, setSimLastFlipScope] = useState<'local' | 'global'>('local');
  const [simFlippedTileIdx, setSimFlippedTileIdx] = useState<number | null>(null);
  const [simBoxLoadState, setSimBoxLoadState] = useState<'done' | 'closed' | 'opening' | 'fading'>('done');

  const triggerSimMasonryBoxLoad = () => {
    setSimBoxLoadState('closed');
    setTimeout(() => setSimBoxLoadState('opening'), 650);
    setTimeout(() => setSimBoxLoadState('fading'), 1150);
    setTimeout(() => setSimBoxLoadState('done'), 1700);
  };

  const estimateRowsFromTiles = (tiles: number): number => {
    const clampedTiles = Math.max(4, Math.min(36, Math.round(tiles || 12)));
    return Math.max(2, Math.min(15, Math.round(Math.sqrt(clampedTiles * 0.68))));
  };

  const getSimTargetTileBounds = (target: number) => {
    const base = Math.max(4, Math.min(36, Math.round(target || 12)));
    const delta = Math.max(1, Math.round(base * 0.25));
    const minCount = Math.max(4, base - delta);
    const maxCount = Math.min(36, base + delta);
    return { target: base, minCount, maxCount, delta };
  };

  const simTileBounds = getSimTargetTileBounds(simMasonryTiles);
  // Active tile count dynamically adapts within [minCount, maxCount] around Target Tile Count
  const simActiveTileCount = Math.max(
    simTileBounds.minCount,
    Math.min(
      simTileBounds.maxCount,
      simTileBounds.target + ((simFlipGeneration % 3) - 1) * Math.min(2, simTileBounds.delta)
    )
  );

  const handleToggleSimMasonryLayout = () => {
    if (simMasonryLayout === 'mondrian') {
      setSimMasonryLayout('rows');
      setSimAutoSearchNotice(
        `Switched Masonry Layout to Rows → Target Tile Count (${simMasonryTiles}, ±25% range ${simTileBounds.minCount}–${simTileBounds.maxCount}) active for uncropped rows`
      );
    } else {
      setSimMasonryLayout('mondrian');
      setSimAutoSearchNotice(
        `Switched Masonry Layout to Mondrian → Mondrian Edge Fill (${simMasonryEdgeFill === 'black' ? 'Black' : 'Blur'}) & Target Tile Count (${simMasonryTiles}) active`
      );
    }
  };

  const handleToggleSimMasonryEdgeFill = () => {
    setSimMasonryEdgeFill((prev) => {
      const next = prev === 'blur' ? 'black' : 'blur';
      setSimAutoSearchNotice(
        `Toggled Mondrian Edge Fill to: ${next === 'black' ? 'Black (#0b0b0d gap-matched solid fill)' : 'Blur (ambient color-matched edge blur)'}`
      );
      return next;
    });
  };

  const handleSimulateTileFlip = (forcedIdx?: number) => {
    const nextGen = simFlipGeneration + 1;
    const chosenIdx = forcedIdx !== undefined ? forcedIdx : nextGen % Math.max(1, simActiveTileCount);
    const nextScope: 'local' | 'global' = nextGen % 3 === 0 ? 'global' : 'local';
    setSimFlipGeneration(nextGen);
    setSimFlippedTileIdx(chosenIdx);
    setSimLastFlipScope(nextScope);
    setSimAutoSearchNotice(
      simMasonryLayout === 'mondrian'
        ? `Tile #${chosenIdx + 1} flipped → ${
            nextScope === 'local'
              ? 'Local group reshuffled & resized adjacent tiles (0.0% edge blur)'
              : `Escalated to full-grid reshuffle (${simActiveTileCount} active tiles within ${simTileBounds.minCount}–${simTileBounds.maxCount} target range)`
          }`
        : `Tile #${chosenIdx + 1} flipped in Rows mode → Uncropped DP row heights re-balanced (${simActiveTileCount} tiles across ${estimateRowsFromTiles(simActiveTileCount)} rows, 0% crop)`
    );
  };

  useEffect(() => {
    FILE_LIST.forEach(async (item) => {
      try {
        const res = await fetch(item.path);
        const text = await res.text();
        setFileContents((prev) => ({ ...prev, [item.key]: text }));
      } catch (e) {
        console.error(e);
      }
    });
  }, []);

  const handleCopyText = async (key: string, text: string) => {
    await navigator.clipboard.writeText(text);
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(null), 2000);
  };

  const handleDownload = (key: FileKey) => {
    const content = fileContents[key] || '';
    const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = key;
    a.click();
    URL.revokeObjectURL(url);
  };

  const isDark = uiTheme === 'dark';
  const curScreenState = simScreensState[simScreen];
  const curPosts = SAMPLE_MEDIA_POSTS[simScreen] || SAMPLE_MEDIA_POSTS.screen_1;
  const curMedia = curPosts[curScreenState.postIdx % curPosts.length];
  const sharedPoolActive =
    simScreensState.screen_1.enabled &&
    simScreensState.screen_2.enabled &&
    simScreensState.screen_1.appliedTags.trim().toLowerCase() ===
      simScreensState.screen_2.appliedTags.trim().toLowerCase();

  // Compute dynamic 1-5 line height for the Search TAGS box based on length & explicit lines
  const computeDynamicTagBoxRows = (text: string): number => {
    const raw = text || '';
    const charsPerLine = 52;
    const explicitLines = raw.split('\n');
    let totalLines = 0;
    for (const line of explicitLines) {
      totalLines += Math.max(1, Math.ceil(Math.max(1, line.length) / charsPerLine));
    }
    return Math.max(1, Math.min(5, totalLines));
  };

  const dynamicTagBoxRows = computeDynamicTagBoxRows(curScreenState.tags);
  const hasUnappliedTagEdits =
    curScreenState.tags.trim() !== curScreenState.appliedTags.trim();

  const getTagColor = (tagName: string): string => {
    const clean = tagName.replace(/^[-~]+/, '').toLowerCase();
    const cat: TagCategory = clean.includes(':')
      ? 5
      : KNOWN_TAG_CATEGORIES[clean] !== undefined
      ? KNOWN_TAG_CATEGORIES[clean]
      : 0;
    return isDark ? DANBOORU_CAT_META[cat].darkHex : DANBOORU_CAT_META[cat].lightHex;
  };

  const getCatColorById = (cat: TagCategory): string => {
    return isDark ? DANBOORU_CAT_META[cat].darkHex : DANBOORU_CAT_META[cat].lightHex;
  };

  const appendTagToSimScreen = (tag: string, applyImmediately = true) => {
    setSimScreensState((prev) => {
      const existing = prev[simScreen].tags.trim();
      const tokens = existing ? existing.split(/\s+/) : [];
      if (tokens.some((t) => t.replace(/^[-~]+/, '').toLowerCase() === tag.toLowerCase())) {
        return prev;
      }
      const nextTags = existing ? `${existing} ${tag}` : tag;
      const shouldApplyNow = applyImmediately && !simTagInputFocused;
      if (shouldApplyNow) {
        setSimAutoSearchNotice(`Auto-searched "${nextTags}" (caret not blinking in search box)`);
      }
      return {
        ...prev,
        [simScreen]: {
          ...prev[simScreen],
          tags: nextTags,
          appliedTags: shouldApplyNow ? nextTags : prev[simScreen].appliedTags,
        },
      };
    });
  };

  const handleSaveCurrentSearch = () => {
    const current = curScreenState.tags.trim().replace(/\s+/g, ' ');
    if (!current) return;
    const isDuplicate = simSavedSearches.some(
      (item) => item.trim().replace(/\s+/g, ' ').toLowerCase() === current.toLowerCase()
    );
    if (isDuplicate) {
      setSimDuplicateToast('Saved Search Tags already exists');
      setTimeout(() => {
        setSimDuplicateToast(null);
      }, 2000);
      return;
    }
    setSimSavedSearches((prev) => [...prev, current]);
    setSimAutoSearchNotice(`Saved "${current}" via Save Search Tags`);
  };

  const handleApplySavedSearch = (savedQuery: string) => {
    setSimScreensState((prev) => ({
      ...prev,
      [simScreen]: {
        ...prev[simScreen],
        tags: savedQuery,
        appliedTags: savedQuery,
        postIdx: prev[simScreen].postIdx + 1,
      },
    }));
    setSimShowSavedDropdown(false);
    setSimShowSuggest(false);
    setSimTagInputFocused(false);
    setSimAutoSearchNotice(`Applied saved search "${savedQuery}"`);
  };

  const handleDeleteSavedSearch = (savedQuery: string) => {
    setSimSavedSearches((prev) => prev.filter((item) => item !== savedQuery));
  };

  const handleTagInputBlur = () => {
    setSimTagInputFocused(false);
    setSimShowSuggest(false);
    setSimScreensState((prev) => {
      const cur = prev[simScreen];
      const normalized = cur.tags.trim().replace(/\s+/g, ' ');
      if (normalized !== cur.appliedTags.trim().replace(/\s+/g, ' ')) {
        setSimAutoSearchNotice(
          `Caret stopped blinking (FocusOut) → Auto-searched "${normalized || 'scenery no_humans'}"`
        );
        return {
          ...prev,
          [simScreen]: {
            ...cur,
            appliedTags: normalized || 'scenery no_humans',
            postIdx: cur.postIdx + 1,
          },
        };
      }
      return prev;
    });
  };

  return (
    <div
      className={`${isDark ? 'dark bg-[#0c0c0f] text-zinc-100' : 'bg-[#f6f6f8] text-zinc-900'} min-h-screen flex flex-col font-sans transition-colors`}
    >
      <header
        className={`border-b px-6 py-3.5 flex flex-wrap items-center justify-between gap-4 ${
          isDark ? 'border-zinc-800 bg-[#121217]' : 'border-zinc-300 bg-white'
        }`}
      >
        <div>
          <h1 className="text-base font-bold tracking-tight flex items-center gap-2">
            <LayoutGrid className="w-5 h-5 text-blue-500" />
            Danbooru Wallpaper Suite v2.3.13 — Clean Slideshow/Masonry Settings UI &amp; Win11 24H2+ HDMI Hotplug Watchdog
          </h1>
          <p className={`text-xs mt-0.5 ${isDark ? 'text-zinc-400' : 'text-zinc-600'}`}>
            Conditional 0x052C Probe • SHELLDLL_DefView Icon Scale Guard • Disconnected HDMI TV Auto-Hide • Glass-Pane Coexistence • Resync Displays Button
          </p>
        </div>

        <div className="flex items-center gap-2">
          <div
            className={`flex rounded border p-0.5 text-xs font-semibold ${
              isDark ? 'border-zinc-800 bg-zinc-900' : 'border-zinc-300 bg-zinc-100'
            }`}
          >
            <button
              onClick={() => setActiveTab('code')}
              className={`px-3 py-1 rounded flex items-center gap-1.5 cursor-pointer ${
                activeTab === 'code'
                  ? 'bg-blue-600 text-white'
                  : isDark
                  ? 'text-zinc-400 hover:text-zinc-200'
                  : 'text-zinc-600 hover:text-zinc-900'
              }`}
            >
              <FileCode className="w-3.5 h-3.5" />
              Updated Source Files ({FILE_LIST.length})
            </button>
            <button
              onClick={() => setActiveTab('preview')}
              className={`px-3 py-1 rounded flex items-center gap-1.5 cursor-pointer ${
                activeTab === 'preview'
                  ? 'bg-blue-600 text-white'
                  : isDark
                  ? 'text-zinc-400 hover:text-zinc-200'
                  : 'text-zinc-600 hover:text-zinc-900'
              }`}
            >
              <Monitor className="w-3.5 h-3.5" />
              Interactive Display Tab Preview
            </button>
            <button
              onClick={() => setActiveTab('audit')}
              className={`px-3 py-1 rounded flex items-center gap-1.5 cursor-pointer ${
                activeTab === 'audit'
                  ? 'bg-blue-600 text-white'
                  : isDark
                  ? 'text-zinc-400 hover:text-zinc-200'
                  : 'text-zinc-600 hover:text-zinc-900'
              }`}
            >
              <ShieldCheck className="w-3.5 h-3.5" />
              Requirements &amp; Security Audit ({FEATURE_SUMMARY_ITEMS.length + SECURITY_AUDIT_ITEMS.length})
            </button>
            <button
              onClick={() => setActiveTab('build')}
              className={`px-3 py-1 rounded flex items-center gap-1.5 cursor-pointer ${
                activeTab === 'build'
                  ? 'bg-blue-600 text-white'
                  : isDark
                  ? 'text-zinc-400 hover:text-zinc-200'
                  : 'text-zinc-600 hover:text-zinc-900'
              }`}
            >
              <Terminal className="w-3.5 h-3.5" />
              PyInstaller CLI Build
            </button>
          </div>

          <button
            onClick={() => setUiTheme(isDark ? 'light' : 'dark')}
            className={`px-3 py-1.5 rounded text-xs font-semibold flex items-center gap-1.5 border cursor-pointer ${
              isDark
                ? 'bg-zinc-800 border-zinc-700 text-zinc-100 hover:bg-zinc-700'
                : 'bg-zinc-100 border-zinc-300 text-zinc-800 hover:bg-zinc-200'
            }`}
          >
            {isDark ? <Sun className="w-3.5 h-3.5" /> : <Moon className="w-3.5 h-3.5" />}
            {isDark ? 'Light Mode' : 'Dark Mode'}
          </button>
        </div>
      </header>

      {activeTab === 'code' && (
        <div className="flex-1 flex flex-col lg:flex-row overflow-hidden">
          <aside
            className={`w-full lg:w-80 border-b lg:border-b-0 lg:border-r p-4 flex flex-col gap-3 overflow-y-auto ${
              isDark ? 'border-zinc-800 bg-[#101015]' : 'border-zinc-300 bg-zinc-50'
            }`}
          >
            <div className="text-xs font-bold uppercase tracking-wider text-zinc-500">
              Complete Updated Files
            </div>
            {FILE_LIST.map((f) => {
              const active = selectedFile === f.key;
              return (
                <div
                  key={f.key}
                  onClick={() => setSelectedFile(f.key)}
                  className={`p-3 rounded border transition cursor-pointer ${
                    active
                      ? 'border-blue-600 bg-blue-600/10'
                      : isDark
                      ? 'border-zinc-800 bg-zinc-900/50 hover:border-zinc-700'
                      : 'border-zinc-300 bg-white hover:border-zinc-400'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-sm font-bold">{f.label}</span>
                    <div className="flex items-center gap-1">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleCopyText(f.key, fileContents[f.key] || '');
                        }}
                        title="Copy file contents"
                        className="p-1.5 rounded hover:bg-blue-500/20 text-blue-500"
                      >
                        {copiedKey === f.key ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                      </button>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDownload(f.key);
                        }}
                        title="Download file"
                        className="p-1.5 rounded hover:bg-blue-500/20 text-blue-500"
                      >
                        <Download className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                  <p className={`text-xs mt-1.5 leading-relaxed ${isDark ? 'text-zinc-400' : 'text-zinc-600'}`}>
                    {f.desc}
                  </p>
                </div>
              );
            })}

            <div
              className={`p-3 rounded border transition ${
                isDark
                  ? 'border-zinc-800 bg-zinc-900/50 hover:border-zinc-700'
                  : 'border-zinc-300 bg-white hover:border-zinc-400'
              }`}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <img
                    src="/updated_files/icon.ico"
                    alt="Danbooru Cardboard Box Icon"
                    className="w-6 h-6 object-contain"
                  />
                  <span className="font-mono text-sm font-bold">icon.ico</span>
                </div>
                <a
                  href="/updated_files/icon.ico"
                  download="icon.ico"
                  title="Download icon.ico"
                  className="p-1.5 rounded hover:bg-blue-500/20 text-blue-500 flex items-center gap-1 text-xs font-semibold"
                >
                  <Download className="w-3.5 h-3.5" />
                </a>
              </div>
              <p className={`text-xs mt-1.5 leading-relaxed ${isDark ? 'text-zinc-400' : 'text-zinc-600'}`}>
                Multi-resolution Windows desktop icon (16×16 through 256×256 RGBA) matching the system tray Danbooru cardboard box icon (<code className="font-mono">create_cardboard_box_icon()</code>).
              </p>
            </div>

            <div
              className={`mt-auto p-3 rounded border text-xs space-y-1.5 ${
                isDark ? 'border-zinc-800 bg-zinc-900/40 text-zinc-400' : 'border-zinc-300 bg-white text-zinc-600'
              }`}
            >
              <div className="font-semibold flex items-center gap-1.5 text-emerald-500">
                <Wrench className="w-3.5 h-3.5" />
                Verified v2.3.13 Updates
              </div>
              <div>
                • <strong>Slideshow &amp; Masonry UI Cleanup</strong>: Removed bottom text description lines (<code>slide_note</code> &amp; <code>masonry_note</code>) from Slideshow and Masonry display settings.
              </div>
              <div>
                • <strong>Conditional 0x052C &amp; Icon Guard</strong>: Probes existing <code>WorkerW</code> without rebroadcasting <code>0x052C</code> and restores <code>SHELLDLL_DefView</code> icon metrics if HDMI DPI changes inflate them.
              </div>
              <div>
                • <strong>Disconnected TV Auto-Hide</strong>: Turning off an HDMI TV immediately hides (<code>SW_HIDE</code>) and pauses its HWND instead of clamping it into a Task View grid.
              </div>
              <div>
                • <strong>Passive Click-Through HWNDs</strong>: Enforces <code>WS_DISABLED</code> + <code>WS_EX_TRANSPARENT</code> + <code>--disable-pinch</code> so wallpaper windows never steal focus or zoom.
              </div>
              <div>
                • <strong>Hotplug Watchdog &amp; Resync Displays</strong>: Auto-detects 3rd screen hotplugs, coexists with <code>Glass-Pane</code>, and adds a <code>Resync Displays</code> button in Settings &amp; Tray.
              </div>
            </div>
          </aside>

          <main className="flex-1 flex flex-col overflow-hidden">
            <div
              className={`px-6 py-3 border-b flex items-center justify-between ${
                isDark ? 'border-zinc-800 bg-[#14141a]' : 'border-zinc-300 bg-zinc-100'
              }`}
            >
              <span className="font-mono text-sm font-semibold">{selectedFile}</span>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => handleCopyText(selectedFile, fileContents[selectedFile] || '')}
                  className="px-3 py-1.5 rounded bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold flex items-center gap-1.5 cursor-pointer"
                >
                  {copiedKey === selectedFile ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                  {copiedKey === selectedFile ? 'Copied!' : 'Copy Full Code'}
                </button>
                <button
                  onClick={() => handleDownload(selectedFile)}
                  className={`px-3 py-1.5 rounded border text-xs font-semibold flex items-center gap-1.5 cursor-pointer ${
                    isDark
                      ? 'border-zinc-700 bg-zinc-800 hover:bg-zinc-700 text-zinc-100'
                      : 'border-zinc-300 bg-white hover:bg-zinc-100 text-zinc-800'
                  }`}
                >
                  <Download className="w-3.5 h-3.5" />
                  Download {selectedFile}
                </button>
              </div>
            </div>

            <pre
              className={`flex-1 p-6 overflow-auto font-mono text-xs leading-relaxed select-all ${
                isDark ? 'bg-[#09090c] text-zinc-200' : 'bg-white text-zinc-900'
              }`}
            >
              <code>{fileContents[selectedFile] || 'Loading file contents...'}</code>
            </pre>
          </main>
        </div>
      )}

      {activeTab === 'preview' && (
        <div className="flex-1 overflow-auto p-6 max-w-4xl mx-auto w-full space-y-6">
          <div
            className={`p-4 rounded border flex flex-wrap items-center justify-between gap-4 ${
              isDark ? 'border-zinc-800 bg-[#121218]' : 'border-zinc-300 bg-white'
            }`}
          >
            <div>
              <h2 className="text-sm font-bold flex items-center gap-2">
                <Monitor className="w-4 h-4 text-blue-500" />
                Interactive Simulation of SettingsDialog &rarr; Display Tab (v2.3.3)
              </h2>
              <p className={`text-xs mt-0.5 ${isDark ? 'text-zinc-400' : 'text-zinc-600'}`}>
                Test clicking <strong>Saved Searches ▾</strong> (between Page/Pool status &amp; Refresh) to open the full-width dropdown with <strong>Save Search Tags</strong>, <strong>🗑</strong> trash-can delete buttons, continuous horizontal marquee scrolling, and the 2-second <strong>&quot;Saved Search Tags already exists&quot;</strong> toast. Also inspect the Dark Mode tabs with a <strong>1px white outline</strong> and <strong>2px gap</strong>.
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-3 text-xs font-semibold">
              {([0, 1, 3, 4, 5] as TagCategory[]).map((cid) => (
                <span key={cid} className="flex items-center gap-1.5">
                  <span
                    className="w-2.5 h-2.5 rounded-sm inline-block"
                    style={{ backgroundColor: getCatColorById(cid) }}
                  />
                  <span style={{ color: getCatColorById(cid) }}>{DANBOORU_CAT_META[cid].name}</span>
                </span>
              ))}
            </div>
          </div>

          {/* Simulated Tkinter SettingsDialog Window */}
          <div
            className={`max-w-2xl mx-auto rounded border shadow-xl overflow-hidden ${
              isDark ? 'bg-[#121214] border-[#323238]' : 'bg-[#f4f4f7] border-[#b8b8c0]'
            }`}
          >
            {/* Header */}
            <div className="px-4 py-2.5 flex items-center justify-between border-b border-zinc-700/40">
              <span className="text-xs font-bold tracking-wide">⚙ APPLICATION SETTINGS</span>
              <div className="flex items-center gap-3">
                <span className="px-2.5 py-1 rounded bg-[#0067c0] text-white text-[11px] font-bold">
                  📊 Resource Graph
                </span>
                <span className="text-xs font-bold opacity-60">✕</span>
              </div>
            </div>

            {/* Custom Theme-Aware Settings Tabs (2px gap between tabs; Dark Mode dark fill + 1px contrasting white outline) */}
            <div className="px-3 pt-2.5 pb-1 flex items-center gap-[2px] border-b border-zinc-700/40 text-xs font-bold">
              {(
                [
                  { key: 'credentials', label: 'Credentials' },
                  { key: 'display', label: 'Display' },
                  { key: 'logs', label: 'Logs' },
                ] as const
              ).map((tab) => {
                const isActive = simSettingsTab === tab.key;
                const tabBg = isActive
                  ? 'bg-[#0067c0] text-white'
                  : isDark
                  ? 'bg-[#232329] text-[#f3f3f5] hover:bg-[#2e2e36]'
                  : 'bg-[#e8e8ed] text-[#1c1c1c] hover:bg-[#dcdce2]';
                const tabOutline = isDark
                  ? 'border border-white'
                  : isActive
                  ? 'border border-[#0067c0]'
                  : 'border border-[#b8b8c0]';
                return (
                  <button
                    key={tab.key}
                    type="button"
                    onClick={() => setSimSettingsTab(tab.key)}
                    className={`px-3.5 py-1.5 cursor-pointer transition-colors ${tabBg} ${tabOutline}`}
                  >
                    {tab.label}
                  </button>
                );
              })}
            </div>

            {/* Display Tab Body */}
            <div className="p-4 space-y-3 text-xs">
              {/* 1. Select Screen Dropdown + Resync Displays Button */}
              <div className="flex items-center justify-between gap-2">
                <label className="font-bold w-44 shrink-0">Select Screen:</label>
                <select
                  value={simScreen}
                  onChange={(e) => {
                    setSimScreen(e.target.value as 'screen_1' | 'screen_2');
                    setSimShowSuggest(false);
                    setSimShowSavedDropdown(false);
                  }}
                  className={`flex-1 px-2.5 py-1.5 rounded border font-semibold ${
                    isDark ? 'bg-[#1c1c21] border-[#323238] text-zinc-100' : 'bg-white border-[#b8b8c0] text-zinc-900'
                  }`}
                >
                  <option value="screen_1">Screen 1 (2560x1440 Primary)</option>
                  <option value="screen_2">Screen 2 (1920x1080 Secondary)</option>
                </select>
                <button
                  type="button"
                  onClick={() => {
                    setSimAutoSearchNotice(
                      'Resync Displays: Probed Progman/WorkerW (no 0x052C broadcast), verified SHELLDLL_DefView icon spacing, re-anchored active HWNDs, and forced WebView2 viewport resync'
                    );
                  }}
                  title="Re-enumerate connected monitors, restore desktop icon metrics if inflated, and re-sync wallpaper HWNDs"
                  className={`px-3 py-1.5 border font-bold text-xs cursor-pointer shrink-0 transition-colors ${
                    isDark
                      ? 'bg-[#232329] border-[#323238] text-[#f3f3f5] hover:bg-[#2e2e36]'
                      : 'bg-[#e8e8ed] border-[#b8b8c0] text-[#1c1c1c] hover:bg-[#dcdce2]'
                  }`}
                >
                  Resync Displays
                </button>
              </div>

              {/* 2. Display Wallpaper On/Off Slide Switch (Left) + Pause During Full Screen Application Switch (Right) */}
              <div className="flex flex-wrap items-center justify-between gap-3 pt-0.5">
                <div
                  onClick={() => {
                    const nextEnabled = !curScreenState.enabled;
                    setSimScreensState((prev) => ({
                      ...prev,
                      [simScreen]: { ...prev[simScreen], enabled: nextEnabled },
                    }));
                    setSimAutoSearchNotice(
                      `Toggled 'Display wallpaper on this screen' slide switch on ${simScreen} to: ${nextEnabled ? 'ON' : 'OFF'}`
                    );
                  }}
                  className="flex items-center gap-2.5 font-bold cursor-pointer select-none"
                >
                  <button
                    type="button"
                    role="switch"
                    aria-checked={curScreenState.enabled}
                    className={`relative w-[42px] h-[22px] rounded-full transition-colors duration-150 border cursor-pointer shrink-0 ${
                      curScreenState.enabled
                        ? 'bg-[#0067c0] border-[#005da6]'
                        : isDark
                        ? 'bg-[#34343e] border-[#323238]'
                        : 'bg-[#c6c6ce] border-[#b8b8c0]'
                    }`}
                  >
                    <span
                      className={`block w-3.5 h-3.5 rounded-full bg-white transition-transform duration-150 ${
                        curScreenState.enabled ? 'translate-x-[21px]' : 'translate-x-[3px]'
                      }`}
                    />
                  </button>
                  <span>Display wallpaper on this screen</span>
                </div>

                {/* Right side of the same row: Pause during full screen application switch */}
                <div
                  onClick={() => {
                    const nextPauseFs = !curScreenState.pauseFullscreen;
                    setSimScreensState((prev) => ({
                      ...prev,
                      [simScreen]: { ...prev[simScreen], pauseFullscreen: nextPauseFs },
                    }));
                    setSimAutoSearchNotice(
                      `Toggled 'Pause during full screen application' on ${simScreen} to: ${
                        nextPauseFs ? 'ON (Auto-pauses during fullscreen games/videos)' : 'OFF'
                      }`
                    );
                  }}
                  className="flex items-center gap-2.5 font-bold cursor-pointer select-none"
                >
                  <button
                    type="button"
                    role="switch"
                    aria-checked={curScreenState.pauseFullscreen}
                    className={`relative w-[42px] h-[22px] rounded-full transition-colors duration-150 border cursor-pointer shrink-0 ${
                      curScreenState.pauseFullscreen
                        ? 'bg-[#0067c0] border-[#005da6]'
                        : isDark
                        ? 'bg-[#34343e] border-[#323238]'
                        : 'bg-[#c6c6ce] border-[#b8b8c0]'
                    }`}
                  >
                    <span
                      className={`block w-3.5 h-3.5 rounded-full bg-white transition-transform duration-150 ${
                        curScreenState.pauseFullscreen ? 'translate-x-[21px]' : 'translate-x-[3px]'
                      }`}
                    />
                  </button>
                  <span>Pause during full screen application</span>
                </div>
              </div>
              {sharedPoolActive && (
                <div className="text-[11px] font-semibold text-emerald-500">
                  ⚡ Shared Tag Pool Active (Screen 1 &amp; Screen 2 reuse 1 API fetch)
                </div>
              )}

              {/* 2b. Per-Screen V-Sync Button ("V-Sync On" / "V-Sync Off") & Conditional Target FPS Input Box to the Right */}
              <div className="flex items-center gap-3 pb-0.5">
                <button
                  type="button"
                  onClick={() => {
                    const nextVsync = !curScreenState.vsync;
                    setSimScreensState((prev) => ({
                      ...prev,
                      [simScreen]: { ...prev[simScreen], vsync: nextVsync },
                    }));
                    setSimAutoSearchNotice(
                      nextVsync
                        ? `Switched V-Sync on ${simScreen} to: V-Sync On (Locked to native monitor refresh rate)`
                        : `Switched V-Sync on ${simScreen} to: V-Sync Off (Paced to Target FPS: ${curScreenState.targetFps} FPS)`
                    );
                  }}
                  className={`px-3.5 py-1 font-bold text-xs cursor-pointer transition-colors shrink-0 ${
                    curScreenState.vsync
                      ? 'bg-[#0067c0] hover:bg-[#005da6] text-white'
                      : isDark
                      ? 'bg-[#232329] hover:bg-[#2e2e36] text-[#f3f3f5] border border-[#323238]'
                      : 'bg-[#e8e8ed] hover:bg-[#dcdce2] text-[#1c1c1c] border border-[#b8b8c0]'
                  }`}
                >
                  {curScreenState.vsync ? 'V-Sync On' : 'V-Sync Off'}
                </button>

                {!curScreenState.vsync && (
                  <div className="flex items-center gap-2">
                    <label className="font-bold whitespace-nowrap">Target FPS (15 – 240):</label>
                    <input
                      type="number"
                      min={15}
                      max={240}
                      value={curScreenState.targetFps}
                      onChange={(e) => {
                        const val = e.target.value;
                        setSimScreensState((prev) => ({
                          ...prev,
                          [simScreen]: { ...prev[simScreen], targetFps: val },
                        }));
                      }}
                      onBlur={() => {
                        const parsed = Number(curScreenState.targetFps);
                        const clamped = Number.isFinite(parsed)
                          ? Math.max(15, Math.min(240, Math.round(parsed)))
                          : 60;
                        setSimScreensState((prev) => ({
                          ...prev,
                          [simScreen]: { ...prev[simScreen], targetFps: String(clamped) },
                        }));
                        setSimAutoSearchNotice(
                          `Set Target FPS on ${simScreen} to ${clamped} FPS (V-Sync Off)`
                        );
                      }}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') {
                          (e.target as HTMLInputElement).blur();
                        }
                      }}
                      className={`w-16 px-2 py-1 border font-mono text-xs font-bold text-center tabular-nums outline-none focus:border-[#0067c0] ${
                        isDark
                          ? 'bg-[#1c1c21] border-[#323238] text-zinc-100'
                          : 'bg-white border-[#b8b8c0] text-zinc-900'
                      }`}
                    />
                  </div>
                )}
              </div>

              {/* 3. Per-Screen Search & Playback Sub-Panel (No Minimize Button) */}
              <div
                className={`p-3 rounded border space-y-2.5 ${
                  isDark ? 'border-[#323238] bg-[#16161a]' : 'border-[#b8b8c0] bg-[#ededf2]'
                }`}
              >
                {/* 3a. Control Row ABOVE the TAGS Search Bar (All standardized to uniform h-7 / 28px height) */}
                <div className="flex items-center gap-1.5">
                  {/* Left: Page & Pool Status Indicator (h-7) */}
                  <div
                    className={`h-7 px-2.5 border flex items-center justify-center font-bold text-[11px] shrink-0 ${
                      !curScreenState.enabled
                        ? isDark
                          ? 'bg-[#232329] border-[#323238] text-zinc-400'
                          : 'bg-[#e8e8ed] border-[#b8b8c0] text-zinc-600'
                        : curScreenState.paused
                        ? 'bg-blue-500/20 border-blue-500/40 text-blue-400'
                        : isDark
                        ? 'bg-[#18331a] border-[#323238] text-[#6ccb5f]'
                        : 'bg-[#dff6dd] border-[#b8b8c0] text-[#0f7b0f]'
                    }`}
                  >
                    {!curScreenState.enabled
                      ? '○ Screen Disabled (No Fetch)'
                      : curScreenState.paused
                      ? '⏸ Paused (BG Processes Stopped)'
                      : '✔ P:1 (84 pooled)'}
                  </div>

                  {/* Center: Saved Searches Button spanning full width between Status Indicator and Refresh Button (h-7) */}
                  <button
                    type="button"
                    onMouseDown={(e) => e.preventDefault()}
                    onClick={() => {
                      setSimShowSavedDropdown((v) => !v);
                      setSimShowSuggest(false);
                    }}
                    title="Open Saved Searches dropdown below TAGS search bar"
                    className={`h-7 flex-1 px-3 border font-bold text-xs cursor-pointer flex items-center justify-center gap-1.5 transition-colors ${
                      isDark
                        ? 'bg-[#232329] border-[#323238] text-[#f3f3f5] hover:bg-[#2e2e36]'
                        : 'bg-[#e8e8ed] border-[#b8b8c0] text-[#1c1c1c] hover:bg-[#dcdce2]'
                    }`}
                  >
                    <span>Saved Searches</span>
                    <ChevronDown className="w-3.5 h-3.5 opacity-80" />
                  </button>

                  {/* Right: Refresh (⟳), Previous (◀), Next (▶), Pause (PAUSE) — All uniform h-7 */}
                  <button
                    type="button"
                    onClick={() =>
                      setSimScreensState((prev) => ({
                        ...prev,
                        [simScreen]: {
                          ...prev[simScreen],
                          appliedTags: prev[simScreen].tags,
                          postIdx: prev[simScreen].postIdx + 1,
                        },
                      }))
                    }
                    title="Refresh selected screen tag pool"
                    className={`h-7 w-8 border font-bold cursor-pointer flex items-center justify-center shrink-0 ${
                      isDark
                        ? 'bg-[#232329] border-[#323238] hover:bg-[#2e2e36]'
                        : 'bg-[#e8e8ed] border-[#b8b8c0] hover:bg-[#dcdce2]'
                    }`}
                  >
                    <RotateCw className="w-3.5 h-3.5" />
                  </button>
                  <button
                    type="button"
                    onClick={() =>
                      setSimScreensState((prev) => ({
                        ...prev,
                        [simScreen]: {
                          ...prev[simScreen],
                          postIdx: Math.max(0, prev[simScreen].postIdx - 1),
                        },
                      }))
                    }
                    title="Previous media on selected screen"
                    className={`h-7 w-7 border font-bold cursor-pointer flex items-center justify-center shrink-0 ${
                      isDark
                        ? 'bg-[#232329] border-[#323238] hover:bg-[#2e2e36]'
                        : 'bg-[#e8e8ed] border-[#b8b8c0] hover:bg-[#dcdce2]'
                    }`}
                  >
                    <ChevronLeft className="w-3.5 h-3.5" />
                  </button>
                  <button
                    type="button"
                    onClick={() =>
                      setSimScreensState((prev) => ({
                        ...prev,
                        [simScreen]: { ...prev[simScreen], postIdx: prev[simScreen].postIdx + 1 },
                      }))
                    }
                    title="Next media on selected screen"
                    className={`h-7 w-7 border font-bold cursor-pointer flex items-center justify-center shrink-0 ${
                      isDark
                        ? 'bg-[#232329] border-[#323238] hover:bg-[#2e2e36]'
                        : 'bg-[#e8e8ed] border-[#b8b8c0] hover:bg-[#dcdce2]'
                    }`}
                  >
                    <ChevronRight className="w-3.5 h-3.5" />
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      const nextPaused = !curScreenState.paused;
                      setSimScreensState((prev) => ({
                        ...prev,
                        [simScreen]: { ...prev[simScreen], paused: nextPaused },
                      }));
                      setSimAutoSearchNotice(
                        nextPaused
                          ? `Paused ${simScreen} → Stopped background tag pool fetches, aborted in-flight preloads/decodes, and paused video & WAAPI animations`
                          : `Resumed ${simScreen} → Restarted background preloader, tag pool sync, and animations`
                      );
                    }}
                    className={`h-7 px-3 border font-bold cursor-pointer flex items-center justify-center gap-1 shrink-0 ${
                      curScreenState.paused
                        ? 'bg-[#0067c0] border-[#0067c0] text-white'
                        : isDark
                        ? 'bg-[#232329] border-[#323238] text-zinc-100 hover:bg-[#2e2e36]'
                        : 'bg-[#e8e8ed] border-[#b8b8c0] text-zinc-900 hover:bg-[#dcdce2]'
                    }`}
                  >
                    {curScreenState.paused ? (
                      <>
                        <Play className="w-3 h-3" /> PAUSED
                      </>
                    ) : (
                      <>
                        <Pause className="w-3 h-3" /> PAUSE
                      </>
                    )}
                  </button>
                </div>

                {/* 3b. TAGS Search Row with Dynamic 1-5 Line Height & Focus-Out Auto-Search (No internal right arrow) */}
                <div className="relative">
                  <div className="flex items-stretch gap-2">
                    <span className="font-bold shrink-0 pt-1.5">TAGS =</span>
                    <div className="flex-1 relative">
                      <div
                        className={`w-full flex items-stretch rounded border overflow-hidden transition-colors ${
                          simTagInputFocused
                            ? 'border-[#0067c0]'
                            : isDark
                            ? 'border-[#323238]'
                            : 'border-[#b8b8c0]'
                        } ${isDark ? 'bg-[#1c1c21]' : 'bg-white'}`}
                      >
                        <textarea
                          rows={dynamicTagBoxRows}
                          value={curScreenState.tags}
                          onFocus={() => {
                            setSimTagInputFocused(true);
                            setSimShowSavedDropdown(false);
                          }}
                          onBlur={handleTagInputBlur}
                          onChange={(e) => {
                            setSimScreensState((prev) => ({
                              ...prev,
                              [simScreen]: { ...prev[simScreen], tags: e.target.value },
                            }));
                            setSimShowSuggest(true);
                            setSimShowSavedDropdown(false);
                          }}
                          className="flex-1 px-2.5 py-1.5 bg-transparent outline-none font-mono text-xs font-bold resize-none leading-5 overflow-y-auto"
                          placeholder="Type Danbooru tags (box dynamically scales 1–5 lines)..."
                        />
                      </div>

                      {/* 2-Second Floating Toast Popup when Save Search Tags is clicked for existing tags */}
                      {simDuplicateToast && (
                        <div className="mt-1 px-3 py-1.5 rounded border border-[#d13438] bg-[#2b1618] text-[#ff9a9c] text-xs font-bold shadow-lg flex items-center justify-between">
                          <span>{simDuplicateToast}</span>
                          <span className="text-[10px] font-mono opacity-75">auto-dismiss (2s)</span>
                        </div>
                      )}

                      {/* Saved Searches Dropdown (Below TAGS search bar, spanning full search box width) */}
                      {simShowSavedDropdown && (
                        <div
                          className={`mt-1 w-full rounded border shadow-lg overflow-hidden z-30 ${
                            isDark ? 'bg-[#1c1c21] border-[#323238]' : 'bg-white border-[#b8b8c0]'
                          }`}
                        >
                          {/* First Option: Save Search Tags */}
                          <button
                            type="button"
                            onClick={handleSaveCurrentSearch}
                            className={`w-full px-3 py-2 text-left font-sans text-xs font-bold text-[#0078d4] border-b flex items-center justify-between cursor-pointer ${
                              isDark
                                ? 'border-[#323238] hover:bg-[#2a2d3e]'
                                : 'border-[#b8b8c0] hover:bg-[#e5f1fb]'
                            }`}
                          >
                            <span>Save Search Tags</span>
                            <span className="text-[10px] font-mono opacity-75">
                              Saves current search bar tags
                            </span>
                          </button>

                          {/* Saved Search Rows with Continuous Horizontal Loop Scrolling & Trash Can Delete Button */}
                          {simSavedSearches.length === 0 ? (
                            <div className="px-3 py-2 text-xs italic opacity-60">
                              No saved searches yet
                            </div>
                          ) : (
                            <div className="max-h-52 overflow-y-auto divide-y divide-zinc-700/20">
                              {simSavedSearches.map((savedQuery) => {
                                const tokens = savedQuery.trim().split(/\s+/).filter(Boolean);
                                const isLongRow = savedQuery.length > 52;
                                return (
                                  <div
                                    key={savedQuery}
                                    className={`flex items-center justify-between px-3 py-1.5 gap-2 ${
                                      isDark ? 'hover:bg-[#2a2d3e]' : 'hover:bg-[#e5f1fb]'
                                    }`}
                                  >
                                    <button
                                      type="button"
                                      onClick={() => handleApplySavedSearch(savedQuery)}
                                      className="flex-1 min-w-0 overflow-hidden text-left font-mono text-xs font-bold cursor-pointer"
                                      title={`Click to apply saved search: ${savedQuery}`}
                                    >
                                      {isLongRow ? (
                                        <div className="animate-saved-marquee">
                                          <span className="inline-flex items-center gap-1.5 pr-12">
                                            {tokens.map((tok, i) => (
                                              <span
                                                key={`a-${tok}-${i}`}
                                                style={{ color: getTagColor(tok) }}
                                              >
                                                {tok}
                                              </span>
                                            ))}
                                          </span>
                                          <span className="inline-flex items-center gap-1.5 pr-12">
                                            {tokens.map((tok, i) => (
                                              <span
                                                key={`b-${tok}-${i}`}
                                                style={{ color: getTagColor(tok) }}
                                              >
                                                {tok}
                                              </span>
                                            ))}
                                          </span>
                                        </div>
                                      ) : (
                                        <div className="inline-flex items-center gap-1.5 whitespace-nowrap">
                                          {tokens.map((tok, i) => (
                                            <span
                                              key={`${tok}-${i}`}
                                              style={{ color: getTagColor(tok) }}
                                            >
                                              {tok}
                                            </span>
                                          ))}
                                        </div>
                                      )}
                                    </button>
                                    <button
                                      type="button"
                                      onClick={() => handleDeleteSavedSearch(savedQuery)}
                                      title="Delete saved search"
                                      className="px-1.5 py-1 rounded text-[#ff6b6b] hover:bg-[#c42b1c] hover:text-white cursor-pointer shrink-0 flex items-center justify-center"
                                    >
                                      <Trash2 className="w-3.5 h-3.5" />
                                    </button>
                                  </div>
                                );
                              })}
                            </div>
                          )}
                        </div>
                      )}

                      {/* Auto-Suggestion Dropdown (Populates BELOW the TAGS search box while typing) */}
                      {simShowSuggest && !simShowSavedDropdown && (
                        <div
                          className={`mt-1 w-full rounded border shadow-lg overflow-hidden z-20 ${
                            isDark ? 'bg-[#1c1c21] border-[#323238]' : 'bg-white border-[#b8b8c0]'
                          }`}
                        >
                          <div className="px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider opacity-60 border-b border-zinc-700/30 flex justify-between">
                            <span>Auto-Suggestions (Populates Below TAGS Search Box)</span>
                            <button
                              type="button"
                              onMouseDown={(e) => e.preventDefault()}
                              onClick={() => setSimShowSuggest(false)}
                              className="cursor-pointer"
                            >
                              ✕
                            </button>
                          </div>
                          {SAMPLE_SUGGESTIONS.slice(0, 5).map((s) => (
                            <div
                              key={s.name}
                              onMouseDown={(e) => e.preventDefault()}
                              onClick={() => {
                                appendTagToSimScreen(s.name, false);
                                setSimShowSuggest(false);
                              }}
                              style={{ color: getCatColorById(s.cat) }}
                              className={`px-3 py-1.5 font-mono text-xs font-bold flex items-center justify-between cursor-pointer ${
                                isDark ? 'hover:bg-[#2a2d3e]' : 'hover:bg-[#e5f1fb]'
                              }`}
                            >
                              <span>{s.name}</span>
                              <span className="opacity-70">({s.count.toLocaleString()})</span>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Dynamic height & Focus-Out status bar + Color-coded token preview */}
                  <div className="mt-1.5 flex flex-wrap items-center justify-between gap-2 pl-14">
                    <div className="flex flex-wrap items-center gap-1.5">
                      <span className="text-[10px] opacity-60">Live Category Coloring:</span>
                      {curScreenState.tags
                        .trim()
                        .split(/\s+/)
                        .filter(Boolean)
                        .map((tok, idx) => (
                          <span
                            key={`${tok}-${idx}`}
                            style={{ color: getTagColor(tok) }}
                            className="font-mono text-xs font-bold"
                          >
                            {tok}
                          </span>
                        ))}
                    </div>
                    <div className="flex items-center gap-2 text-[10px] font-mono opacity-75">
                      <span>Box Height: {dynamicTagBoxRows} / 5 lines</span>
                      {hasUnappliedTagEdits && simTagInputFocused && (
                        <span className="text-amber-400 font-sans font-semibold">
                          (Click outside box to stop blinking caret &amp; run auto-search)
                        </span>
                      )}
                    </div>
                  </div>

                  {simAutoSearchNotice && (
                    <div className="mt-1 pl-14 text-[11px] text-emerald-400 font-semibold">
                      ⚡ {simAutoSearchNotice}
                    </div>
                  )}
                </div>

                {/* 3c. Permanent 4-Layer Scrollable Displayed Media Tags Box */}
                <div className="space-y-1 pt-1">
                  <div className="flex items-center justify-between text-xs font-bold">
                    <span className="opacity-85">DISPLAYED MEDIA TAGS (CLICK TO ADD):</span>
                    {curScreenState.enabled && (
                      <a
                        href={`https://danbooru.donmai.us/posts/${curMedia.postId}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="underline cursor-pointer text-[#0067c0] dark:text-[#4da6ff] hover:text-[#009be6]"
                        title={`Click to open https://danbooru.donmai.us/posts/${curMedia.postId} in default web browser`}
                      >
                        Post #{curMedia.postId} ({curMedia.tags.length} tags)
                      </a>
                    )}
                  </div>
                  <div
                    className={`h-24 overflow-y-auto p-2.5 rounded border font-mono text-xs leading-6 ${
                      isDark ? 'bg-[#1c1c21] border-[#323238]' : 'bg-white border-[#b8b8c0]'
                    }`}
                  >
                    {!curScreenState.enabled ? (
                      <span className="italic opacity-60 font-sans">
                        Screen display is currently unchecked — enable screen to fetch and display media tags.
                      </span>
                    ) : (
                      <div className="flex flex-wrap gap-x-3 gap-y-1">
                        {curMedia.tags.map((t) => (
                          <button
                            key={t.name}
                            onClick={() => appendTagToSimScreen(t.name, true)}
                            style={{ color: getCatColorById(t.cat) }}
                            className="font-bold hover:underline cursor-pointer text-left"
                            title={`Category: ${DANBOORU_CAT_META[t.cat].name} — Click to add '${t.name}' to ${simScreen} TAGS`}
                          >
                            {t.name}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {/* 4. Display Mode Selector & Masonry Layout Section (Mondrian vs. Uncropped Rows) */}
              <div className="pt-2 border-t border-zinc-700/30 space-y-2.5">
                <div className="flex items-center justify-between gap-4">
                  <label className="font-bold w-48">Display Mode:</label>
                  <select
                    value={curScreenState.mode}
                    onChange={(e) =>
                      setSimScreensState((prev) => ({
                        ...prev,
                        [simScreen]: { ...prev[simScreen], mode: e.target.value },
                      }))
                    }
                    className={`flex-1 px-2.5 py-1.5 rounded border font-semibold ${
                      isDark ? 'bg-[#1c1c21] border-[#323238] text-zinc-100' : 'bg-white border-[#b8b8c0] text-zinc-900'
                    }`}
                  >
                    <option value="masonry">masonry</option>
                    <option value="scroll">scroll</option>
                    <option value="polaroid">polaroid</option>
                    <option value="slideshow">slideshow</option>
                  </select>
                </div>

                {/* MASONRY LAYOUT SETTINGS */}
                <div className="pt-1 space-y-2.5">
                  <div className="text-[11px] font-bold tracking-wide opacity-70">
                    MASONRY LAYOUT SETTINGS (UNCROPPED 3D Y-AXIS FLIP &amp; ZERO-BLUR RESHUFFLE)
                  </div>

                  {/* Combined Single Row: Masonry Layout & Edge Fill Buttons */}
                  <div className="grid grid-cols-2 gap-2.5">
                    <button
                      type="button"
                      onClick={handleToggleSimMasonryLayout}
                      className="py-1.5 px-3 bg-[#0067c0] hover:bg-[#005da6] text-white font-bold rounded-none cursor-pointer text-center transition-colors"
                    >
                      {simMasonryLayout === 'rows'
                        ? 'Masonry Layout: Rows'
                        : 'Masonry Layout: Mondrian'}
                    </button>
                    <button
                      type="button"
                      onClick={handleToggleSimMasonryEdgeFill}
                      className="py-1.5 px-3 bg-[#0067c0] hover:bg-[#005da6] text-white font-bold rounded-none cursor-pointer text-center transition-colors"
                    >
                      {simMasonryEdgeFill === 'black'
                        ? 'Edge Fill: Black'
                        : 'Edge Fill: Blur'}
                    </button>
                  </div>

                  {/* Standard Target Tile Count (4 - 36) Row for BOTH Mondrian and Rows */}
                  <div className="flex items-center justify-between gap-4">
                    <label className="w-48">Target Tile Count (4 – 36):</label>
                    <div className="flex-1 flex items-center gap-2">
                      <input
                        type="number"
                        min={4}
                        max={36}
                        value={simMasonryTiles}
                        onChange={(e) => {
                          const raw = Number(e.target.value);
                          setSimMasonryTiles(Math.max(4, Math.min(36, Math.round(raw || 4))));
                        }}
                        className={`w-16 px-2 py-1 border font-mono text-xs tabular-nums ${
                          isDark ? 'bg-[#1c1c21] border-[#323238] text-zinc-100' : 'bg-white border-[#b8b8c0] text-zinc-900'
                        }`}
                      />
                      <input
                        type="range"
                        min={4}
                        max={36}
                        step={1}
                        value={simMasonryTiles}
                        onChange={(e) => {
                          setSimMasonryTiles(Number(e.target.value));
                        }}
                        className="flex-1 accent-[#0067c0] cursor-pointer"
                      />
                    </div>
                  </div>

                  {/* Gap (0 - 10 px) */}
                  <div className="flex items-center justify-between gap-4">
                    <label className="w-48">Gap (0 – 10 px):</label>
                    <div className="flex-1 flex items-center gap-2">
                      <input
                        type="number"
                        min={0}
                        max={10}
                        value={simMasonryGap}
                        onChange={(e) => setSimMasonryGap(Math.max(0, Math.min(10, Math.round(Number(e.target.value) || 0))))}
                        className={`w-16 px-2 py-1 border font-mono text-xs tabular-nums ${
                          isDark ? 'bg-[#1c1c21] border-[#323238] text-zinc-100' : 'bg-white border-[#b8b8c0] text-zinc-900'
                        }`}
                      />
                      <input
                        type="range"
                        min={0}
                        max={10}
                        step={1}
                        value={simMasonryGap}
                        onChange={(e) => setSimMasonryGap(Number(e.target.value))}
                        className="flex-1 accent-[#0067c0] cursor-pointer"
                      />
                    </div>
                  </div>

                  {/* Delay (1 - 60 s) */}
                  <div className="flex items-center justify-between gap-4">
                    <label className="w-48">Delay (1 – 60 s):</label>
                    <div className="flex-1 flex items-center gap-2">
                      <input
                        type="number"
                        min={1}
                        max={60}
                        value={simMasonryDelay}
                        onChange={(e) => setSimMasonryDelay(Math.max(1, Math.min(60, Math.round(Number(e.target.value) || 1))))}
                        className={`w-16 px-2 py-1 border font-mono text-xs tabular-nums ${
                          isDark ? 'bg-[#1c1c21] border-[#323238] text-zinc-100' : 'bg-white border-[#b8b8c0] text-zinc-900'
                        }`}
                      />
                      <input
                        type="range"
                        min={1}
                        max={60}
                        step={1}
                        value={simMasonryDelay}
                        onChange={(e) => setSimMasonryDelay(Number(e.target.value))}
                        className="flex-1 accent-[#0067c0] cursor-pointer"
                      />
                    </div>
                  </div>

                  {/* Live Uncropped Masonry Stage Geometry Preview with Interactive Flip & Reshuffle */}
                  <div
                    className={`mt-2 p-2.5 rounded border space-y-2 ${
                      isDark ? 'border-[#323238] bg-[#0b0b0d]' : 'border-[#b8b8c0] bg-[#101014]'
                    }`}
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2 text-[11px] text-zinc-300 font-semibold">
                      <div className="flex flex-wrap items-center gap-2">
                        <span>
                          Live Stage Preview:{' '}
                          {simMasonryLayout === 'rows'
                            ? `Rows Mode (${simActiveTileCount} Active Tiles [Target ${simMasonryTiles} ±25%: ${simTileBounds.minCount}–${simTileBounds.maxCount}] • Uncropped object-fit: contain • 0% Crop)`
                            : `Mondrian Mode (${simActiveTileCount} Active Tiles [Target ${simMasonryTiles} ±25%: ${simTileBounds.minCount}–${simTileBounds.maxCount}] • Edge Fill: ${
                                simMasonryEdgeFill === 'black' ? 'Black #0b0b0d' : 'Blur'
                              })`}
                        </span>
                      </div>
                      <div className="flex items-center gap-2">
                        <button
                          type="button"
                          onClick={() => triggerSimMasonryBoxLoad()}
                          className="px-2.5 py-1 bg-amber-700 hover:bg-amber-600 text-white font-bold text-[11px] cursor-pointer transition-colors"
                        >
                          Replay Cardboard Box Load
                        </button>
                        <button
                          type="button"
                          onClick={() => handleSimulateTileFlip()}
                          className="px-2.5 py-1 bg-[#0067c0] hover:bg-[#005da6] text-white font-bold text-[11px] cursor-pointer transition-colors"
                        >
                          Flip Next Tile (Reshuffle &amp; Resize)
                        </button>
                      </div>
                    </div>

                    <div
                      className="relative w-full h-60 bg-[#0b0b0d] flex flex-col overflow-hidden p-1 border border-zinc-800"
                      style={{ gap: `${simMasonryGap}px` }}
                    >
                      {simBoxLoadState !== 'done' && (
                        <div
                          className={`absolute inset-0 z-20 bg-[#0b0b0d] flex flex-col items-center justify-center transition-opacity duration-500 ${
                            simBoxLoadState === 'fading' ? 'opacity-0' : 'opacity-100'
                          }`}
                        >
                          <svg width="112" height="112" viewBox="0 0 64 64" className="overflow-visible">
                            <ellipse cx="32" cy="57.5" rx="22" ry="4.2" fill="rgba(0,0,0,0.55)" />
                            <polygon points="10,22 32,11 32,33" fill="#634121" stroke="#3d2814" strokeWidth="1" />
                            <polygon points="32,11 54,22 32,33" fill="#734e2a" stroke="#3d2814" strokeWidth="1" />
                            {simBoxLoadState === 'closed' ? (
                              <>
                                <polygon points="10,22 32,11 32,22 10,22" fill="#c9965d" stroke="#3d2814" strokeWidth="1.15" />
                                <polygon points="32,11 32,22 54,22 54,22" fill="#be8b52" stroke="#3d2814" strokeWidth="1.15" />
                                <polygon points="10,22 32,33 32,56 10,44" fill="#c28e56" stroke="#3d2814" strokeWidth="1.15" />
                                <polygon points="32,33 54,22 54,44 32,56" fill="#96693c" stroke="#3d2814" strokeWidth="1.15" />
                                <polygon points="10,22 32,33 32,22 10,22" fill="#d4a26a" stroke="#3d2814" strokeWidth="1.15" />
                                <polygon points="32,33 54,22 54,22 32,22" fill="#c28e56" stroke="#3d2814" strokeWidth="1.15" />
                                <polygon points="11,21.5 53,21.5 53,23.2 11,23.2" fill="#825832" />
                                <polygon points="30,32 34,32 34,42 30,42" fill="#825832" stroke="#3d2814" strokeWidth="0.9" />
                              </>
                            ) : (
                              <>
                                <polygon points="10,22 32,11 26,2 4,12" fill="#b9854d" stroke="#3d2814" strokeWidth="1.15" />
                                <polygon points="32,11 38,2 60,12 54,22" fill="#ad7a44" stroke="#3d2814" strokeWidth="1.15" />
                                <polygon points="10,22 32,33 32,56 10,44" fill="#c28e56" stroke="#3d2814" strokeWidth="1.15" />
                                <polygon points="32,33 54,22 54,44 32,56" fill="#96693c" stroke="#3d2814" strokeWidth="1.15" />
                                <polygon points="10,22 32,33 26,41 4,30" fill="#d4a26a" stroke="#3d2814" strokeWidth="1.15" />
                                <polygon points="32,33 54,22 60,30 38,41" fill="#c28e56" stroke="#3d2814" strokeWidth="1.15" />
                                <polygon points="30,32 34,32 34,42 30,42" fill="#825832" stroke="#3d2814" strokeWidth="0.9" />
                              </>
                            )}
                          </svg>
                        </div>
                      )}
                      {(() => {
                        const baseAspects = [
                          1.78, 0.75, 1.33, 1.5, 0.8, 1.6, 1.25, 0.7, 1.45, 1.85, 0.9, 1.38,
                          1.65, 0.78, 1.2, 1.55, 0.85, 1.4,
                        ];
                        const rotatedAspects = Array.from({ length: simActiveTileCount }, (_, idx) => {
                          const raw = baseAspects[(idx + simFlipGeneration * 2) % baseAspects.length];
                          return idx === simFlippedTileIdx ? Number((1 / raw).toFixed(2)) : raw;
                        });

                        if (simMasonryLayout === 'rows') {
                          const numRows = estimateRowsFromTiles(simActiveTileCount);
                          const rows: { idx: number; aspect: number }[][] = Array.from({ length: numRows }, () => []);
                          rotatedAspects.forEach((asp, idx) => {
                            const r = Math.min(numRows - 1, Math.floor((idx / simActiveTileCount) * numRows));
                            rows[r].push({ idx, aspect: asp });
                          });

                          return rows.map((rowTiles, rIdx) => {
                            const sumA = rowTiles.reduce((acc, t) => acc + t.aspect, 0) || 1;
                            const rowWeight = 1 / sumA;
                            return (
                              <div
                                key={rIdx}
                                className="w-full flex items-stretch overflow-hidden transition-all duration-300"
                                style={{
                                  flexGrow: rowWeight,
                                  flexBasis: 0,
                                  gap: `${simMasonryGap}px`,
                                }}
                              >
                                {rowTiles.map((t) => {
                                  const isFlipped = t.idx === simFlippedTileIdx;
                                  return (
                                    <button
                                      key={t.idx}
                                      type="button"
                                      onClick={() => handleSimulateTileFlip(t.idx)}
                                      style={{ flexGrow: t.aspect, flexBasis: 0 }}
                                      className={`bg-[#0b0b0d] border flex flex-col items-center justify-center overflow-hidden text-[10px] font-mono cursor-pointer transition-all duration-300 ${
                                        isFlipped
                                          ? 'border-emerald-400 text-emerald-300 bg-emerald-950/30'
                                          : 'border-blue-500/30 text-blue-300/90 hover:border-blue-400'
                                      }`}
                                      title={`Click to flip Tile #${t.idx + 1} (Aspect ${t.aspect.toFixed(2)}:1 — Uncropped)`}
                                    >
                                      <span className="font-bold">#{t.idx + 1}</span>
                                      {numRows <= 6 && <span className="opacity-80">{t.aspect.toFixed(2)}:1</span>}
                                    </button>
                                  );
                                })}
                              </div>
                            );
                          });
                        }

                        // Mondrian BSP Group Simulation: partition active tiles into aspect-locked groups
                        const numBands = Math.max(2, Math.min(4, Math.round(Math.sqrt(simActiveTileCount * 0.6))));
                        const bands: { idx: number; aspect: number }[][] = Array.from({ length: numBands }, () => []);
                        rotatedAspects.forEach((asp, idx) => {
                          const b = Math.min(numBands - 1, Math.floor((idx / simActiveTileCount) * numBands));
                          bands[b].push({ idx, aspect: asp });
                        });

                        return bands.map((bandTiles, bIdx) => {
                          const sumBandA = bandTiles.reduce((acc, t) => acc + t.aspect, 0) || 1;
                          const invRowH = 1 / Math.max(0.4, sumBandA);
                          return (
                            <div
                              key={bIdx}
                              className="w-full flex items-stretch overflow-hidden transition-all duration-300"
                              style={{
                                flexGrow: invRowH,
                                flexBasis: 0,
                                gap: `${simMasonryGap}px`,
                              }}
                            >
                              {bandTiles.map((t) => {
                                const isFlipped = t.idx === simFlippedTileIdx;
                                const edgeStyle =
                                  simMasonryEdgeFill === 'black'
                                    ? 'bg-[#0b0b0d]'
                                    : 'bg-gradient-to-br from-[#1b2234] via-[#121521] to-[#1e1b2e]';
                                return (
                                  <button
                                    key={t.idx}
                                    type="button"
                                    onClick={() => handleSimulateTileFlip(t.idx)}
                                    style={{ flexGrow: t.aspect, flexBasis: 0 }}
                                    className={`${edgeStyle} border flex flex-col items-center justify-center overflow-hidden text-[10px] font-mono cursor-pointer transition-all duration-300 ${
                                      isFlipped
                                        ? 'border-emerald-400 text-emerald-300'
                                        : 'border-indigo-500/35 text-indigo-200 hover:border-indigo-400'
                                    }`}
                                    title={`Click to flip Tile #${t.idx + 1} (Aspect ${t.aspect.toFixed(2)}:1 — Edge Fill: ${simMasonryEdgeFill.toUpperCase()})`}
                                  >
                                    <span className="font-bold">Tile #{t.idx + 1}</span>
                                    <span className="text-[9px] opacity-80">{t.aspect.toFixed(2)}:1</span>
                                  </button>
                                );
                              })}
                            </div>
                          );
                        });
                      })()}
                    </div>

                    <div className="flex flex-wrap items-center justify-between gap-2 text-[10px] font-mono text-zinc-400">
                      <span>
                        Last Reflow Scope:{' '}
                        <strong className="text-emerald-400">
                          {simLastFlipScope === 'local'
                            ? 'Tier 1 Local Subgroup Reorder & Resize (0.0% Edge Blur)'
                            : 'Tier 2 Full-Grid BSP Re-Partition & Resize (0.0% Edge Blur)'}
                        </strong>
                      </span>
                      <span>Click any tile above to flip it &amp; trigger a live reshuffle</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {activeTab === 'audit' && (
        <div className="flex-1 overflow-auto p-6 max-w-5xl mx-auto w-full space-y-6">
          <div
            className={`p-4 rounded border ${
              isDark ? 'border-zinc-800 bg-[#121218]' : 'border-zinc-300 bg-white'
            }`}
          >
            <h2 className="text-sm font-bold flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-blue-500" />
              v2.3.5 Security, Memory &amp; 64-Bit Ctypes Audit + Requirements Implementation Summary
            </h2>
          </div>

          <div className="space-y-3">
            {FEATURE_SUMMARY_ITEMS.map((item) => (
              <div
                key={item.id}
                className={`p-4 rounded border space-y-2 ${
                  isDark ? 'border-zinc-800 bg-[#101015]' : 'border-zinc-300 bg-white'
                }`}
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs font-bold px-2 py-0.5 rounded bg-blue-600/20 text-blue-400 border border-blue-500/30">
                      {item.id}
                    </span>
                    <span className="font-semibold text-sm">{item.issue}</span>
                  </div>
                  <span className="font-mono text-xs text-zinc-400">{item.file}</span>
                </div>
                <div className={`text-xs space-y-1.5 ${isDark ? 'text-zinc-300' : 'text-zinc-700'}`}>
                  <div>
                    <span className="font-bold text-blue-400">Requirement: </span>
                    {item.cause}
                  </div>
                  <div>
                    <span className="font-bold text-emerald-500">Implementation: </span>
                    {item.fix}
                  </div>
                </div>
              </div>
            ))}
          </div>

          <div
            className={`p-4 rounded border ${
              isDark ? 'border-zinc-800 bg-[#121218]' : 'border-zinc-300 bg-white'
            }`}
          >
            <h2 className="text-sm font-bold flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-emerald-500" />
              PHP &amp; Malware Download Vulnerability Audit (SEC-01 through SEC-05)
            </h2>
            <p className={`text-xs mt-1 ${isDark ? 'text-zinc-400' : 'text-zinc-600'}`}>
              Comprehensive security scan and remediation across <code className="font-mono">danbooru_service.py</code> and{' '}
              <code className="font-mono">index.html</code> to ensure a pulled file can never download or execute PHP payloads, scripts, or malware on the host machine.
            </p>
          </div>

          <div className="space-y-3">
            {SECURITY_AUDIT_ITEMS.map((item) => (
              <div
                key={item.id}
                className={`p-4 rounded border space-y-2 ${
                  isDark ? 'border-zinc-800 bg-[#101015]' : 'border-zinc-300 bg-white'
                }`}
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs font-bold px-2 py-0.5 rounded bg-emerald-600/20 text-emerald-400 border border-emerald-500/30">
                      {item.id}
                    </span>
                    <span className="font-semibold text-sm">{item.issue}</span>
                  </div>
                  <span className="font-mono text-xs text-zinc-400">{item.file}</span>
                </div>
                <div className={`text-xs space-y-1.5 ${isDark ? 'text-zinc-300' : 'text-zinc-700'}`}>
                  <div>
                    <span className="font-bold text-amber-500">Vulnerability Found: </span>
                    {item.cause}
                  </div>
                  <div>
                    <span className="font-bold text-emerald-500">Remediation Implemented: </span>
                    {item.fix}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {activeTab === 'build' && (
        <div className="flex-1 overflow-auto p-6 max-w-4xl mx-auto w-full space-y-4">
          <div
            className={`p-5 rounded border space-y-3 ${
              isDark ? 'border-zinc-800 bg-[#121218]' : 'border-zinc-300 bg-white'
            }`}
          >
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-bold flex items-center gap-2">
                <Terminal className="w-4 h-4 text-blue-500" />
                PyInstaller Single-File Executable Build (--onefile --noconsole)
              </h2>
              <button
                onClick={() => handleCopyText('pyinstaller', PYINSTALLER_COMMANDS)}
                className="px-3 py-1 rounded bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold flex items-center gap-1.5 cursor-pointer"
              >
                {copiedKey === 'pyinstaller' ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                {copiedKey === 'pyinstaller' ? 'Copied Commands' : 'Copy Commands'}
              </button>
            </div>
            <pre
              className={`p-4 rounded font-mono text-xs overflow-x-auto border ${
                isDark ? 'bg-[#09090c] border-zinc-800 text-zinc-200' : 'bg-zinc-50 border-zinc-300 text-zinc-900'
              }`}
            >
              <code>{PYINSTALLER_COMMANDS}</code>
            </pre>
            <p className={`text-xs leading-relaxed ${isDark ? 'text-zinc-400' : 'text-zinc-600'}`}>
              Note: Even if you build the executable without <code className="font-mono">--collect-all &quot;curl_cffi&quot;</code> or on a machine without <code className="font-mono">curl_cffi</code> installed, the updated <code className="font-mono">danbooru_service.py</code> will automatically run using the built-in <code className="font-mono">StdlibDoHSession</code> (Cloudflare 1.1.1.1 DoH + TLS 1.3 SNI).
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
