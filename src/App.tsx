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

type FileKey = 'CHANGELOG.md' | 'README.md' | 'GLOSSARY.md' | 'danbooru_service.py' | 'index.html' | 'project.json';
type ViewTab = 'code' | 'preview' | 'audit' | 'build';

const FILE_LIST: { key: FileKey; path: string; label: string; desc: string }[] = [
  {
    key: 'danbooru_service.py',
    path: '/updated_files/danbooru_service.py',
    label: 'danbooru_service.py',
    desc: 'v2.3.3 service with full-span "Saved Searches ▾" button between Page/Pool indicator & Refresh (uniform 28px height), full-width below-TAGS dropdown ("Save Search Tags" top option, continuous horizontal marquee for long saved searches, 🗑 trash-can delete buttons, 2s "Saved Search Tags already exists" toast), Dark Mode Settings tabs with 1px white outline & 2px tab spacing, dynamic 1–5 line TAGS box, and Focus-Out auto-search.',
  },
  {
    key: 'index.html',
    path: '/updated_files/index.html',
    label: 'index.html',
    desc: 'v2.3.3 WebView2 frontend with strict unchecked-screen no-fetch guard (SCREEN_ENABLED = false until confirmed), post_id tracking across preloader & DOM nodes, and real-time /report_shown reporting of displayed media to populate the 4-layer tags box.',
  },
  {
    key: 'project.json',
    path: '/updated_files/project.json',
    label: 'project.json',
    desc: 'v2.3.3 wallpaper configuration schema with per-screen "searchtags" property (order: 0, default "scenery no_humans") alongside Display Mode, Scroll, Polaroid, Slideshow, and Masonry settings.',
  },
  {
    key: 'README.md',
    path: '/updated_files/README.md',
    label: 'README.md',
    desc: 'Condensed, professional README with a non-technical application summary and features overview, usage instructions, requirements, PyInstaller build commands, and credential setup guide.',
  },
  {
    key: 'GLOSSARY.md',
    path: '/updated_files/GLOSSARY.md',
    label: 'GLOSSARY.md',
    desc: 'Standalone Application Logs Glossary moved out of README.md, documenting all Normal Operation, User Interaction, and Error/Security/Warning log prefixes.',
  },
  {
    key: 'CHANGELOG.md',
    path: '/updated_files/CHANGELOG.md',
    label: 'CHANGELOG.md',
    desc: 'v2.3.3 release notes documenting the root-cause fix for the clipped dropdown arrow, the new "Saved Searches ▾" bar button, "Save Search Tags" top option, 2s duplicate toast, continuous horizontal marquee, trash-can delete icon, and Dark Mode tabs with 1px white outline & 2px spacing.',
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
#    Includes index.html and project.json, and bundles curl_cffi native binaries if installed
pyinstaller --noconfirm --onefile --noconsole ^
  --name "DanbooruWallpaper" ^
  --add-data "index.html;." ^
  --add-data "project.json;." ^
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
      paused: boolean;
      tags: string;
      appliedTags: string;
      mode: string;
      postIdx: number;
    };
    screen_2: {
      enabled: boolean;
      paused: boolean;
      tags: string;
      appliedTags: string;
      mode: string;
      postIdx: number;
    };
  }>({
    screen_1: {
      enabled: true,
      paused: false,
      tags: 'scenery no_humans highres',
      appliedTags: 'scenery no_humans highres',
      mode: 'masonry',
      postIdx: 0,
    },
    screen_2: {
      enabled: true,
      paused: false,
      tags: 'genshin_impact furina_(genshin_impact) wlop',
      appliedTags: 'genshin_impact furina_(genshin_impact) wlop',
      mode: 'slideshow',
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
            Danbooru Wallpaper Suite v2.3.3 — Saved Searches Bar Button, Marquee Rows, Duplicate Toast &amp; Dark Mode Tabs
          </h1>
          <p className={`text-xs mt-0.5 ${isDark ? 'text-zinc-400' : 'text-zinc-600'}`}>
            Saved Searches ▾ Above TAGS (&quot;Save Search Tags&quot; + 🗑 Delete + Continuous Marquee + 2s Duplicate Toast) • Dark Mode Tabs w/ 1px White Outline &amp; 2px Gap
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
              className={`mt-auto p-3 rounded border text-xs space-y-1.5 ${
                isDark ? 'border-zinc-800 bg-zinc-900/40 text-zinc-400' : 'border-zinc-300 bg-white text-zinc-600'
              }`}
            >
              <div className="font-semibold flex items-center gap-1.5 text-emerald-500">
                <Wrench className="w-3.5 h-3.5" />
                Verified v2.3.3 Updates
              </div>
              <div>
                • <strong>Saved Searches ▾ Button</strong> above <code>TAGS =</code> spanning between the Page/Pool badge and Refresh button (uniform 28px height).
              </div>
              <div>
                • <strong>&quot;Save Search Tags&quot;</strong> top option + 2s <strong>&quot;Saved Search Tags already exists&quot;</strong> popup toast + <strong>🗑</strong> trash-can delete buttons + continuous horizontal marquee scrolling.
              </div>
              <div>
                • <strong>Dark Mode Settings Tabs</strong> with 1px contrasting white outline and 2px gap between tabs.
              </div>
              <div>
                • <strong>Dynamic 1–5 Line TAGS Box</strong> &amp; <strong>Focus-Out Auto-Search</strong> when caret stops blinking.
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
              {/* 1. Select Screen Dropdown */}
              <div className="flex items-center justify-between gap-4">
                <label className="font-bold w-48">Select Screen:</label>
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
              </div>

              {/* 2. Display Wallpaper Checkbox */}
              <div className="flex items-center justify-between">
                <label className="flex items-center gap-2 font-bold cursor-pointer">
                  <input
                    type="checkbox"
                    checked={curScreenState.enabled}
                    onChange={(e) =>
                      setSimScreensState((prev) => ({
                        ...prev,
                        [simScreen]: { ...prev[simScreen], enabled: e.target.checked },
                      }))
                    }
                    className="w-4 h-4 accent-[#0067c0]"
                  />
                  Display wallpaper on this screen
                </label>
                {sharedPoolActive && (
                  <span className="text-[11px] font-semibold text-emerald-500">
                    ⚡ Shared Tag Pool Active (Screen 1 &amp; Screen 2 reuse 1 API fetch)
                  </span>
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
                      ? '⏸ Screen Paused'
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
                    onClick={() =>
                      setSimScreensState((prev) => ({
                        ...prev,
                        [simScreen]: { ...prev[simScreen], paused: !prev[simScreen].paused },
                      }))
                    }
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
                  <div className="flex items-center justify-between text-[11px] font-bold opacity-75">
                    <span>DISPLAYED MEDIA TAGS (CLICK TAG TO ADD TO SEARCH):</span>
                    {curScreenState.enabled && (
                      <span>
                        Post #{curMedia.postId} ({curMedia.tags.length} tags)
                      </span>
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
              v2.3.3 Requirements Implementation Summary (Saved Searches Bar Button, Marquee Rows, Duplicate Toast &amp; Dark Mode Tabs)
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
