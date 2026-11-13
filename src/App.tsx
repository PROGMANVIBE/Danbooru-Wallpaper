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
} from 'lucide-react';

type FileKey = 'CHANGELOG.md' | 'README.md' | 'danbooru_service.py' | 'index.html' | 'project.json';
type ViewTab = 'code' | 'preview' | 'audit' | 'build';

const FILE_LIST: { key: FileKey; path: string; label: string; desc: string }[] = [
  {
    key: 'danbooru_service.py',
    path: '/updated_files/danbooru_service.py',
    label: 'danbooru_service.py',
    desc: 'v2.3.0 service with standalone search window removed, per-screen Display tab controls (⟳, ◀, ▶, PAUSE above TAGS), shared TAG_POOLS deduplication, Danbooru category color coordination, 4-layer Displayed Media Tags box, and left-click tray Settings launch.',
  },
  {
    key: 'index.html',
    path: '/updated_files/index.html',
    label: 'index.html',
    desc: 'v2.3.0 WebView2 frontend with strict unchecked-screen no-fetch guard (SCREEN_ENABLED = false until confirmed), post_id tracking across preloader & DOM nodes, and real-time /report_shown reporting of displayed media to populate the 4-layer tags box.',
  },
  {
    key: 'project.json',
    path: '/updated_files/project.json',
    label: 'project.json',
    desc: 'v2.3.0 wallpaper configuration schema updated with per-screen "searchtags" property (order: 0, default "scenery no_humans") alongside Display Mode, Scroll, Polaroid, Slideshow, and Masonry settings.',
  },
  {
    key: 'CHANGELOG.md',
    path: '/updated_files/CHANGELOG.md',
    label: 'CHANGELOG.md',
    desc: 'v2.3.0 release notes covering Display Tab Per-Screen Search integration, shared tag-pool deduplication, Danbooru category color coordination, the permanent 4-layer Displayed Media Tags box, and instant left-click tray Settings access.',
  },
  {
    key: 'README.md',
    path: '/updated_files/README.md',
    label: 'README.md',
    desc: 'Updated user & developer documentation detailing per-screen TAGS search in the Display tab, Danbooru category color codes, the 4-layer media tags box, and PyInstaller build instructions.',
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
    id: 'REQ-01..03',
    severity: 'v2.3.0 UI ARCHITECTURE',
    file: 'danbooru_service.py (SettingsDialog._build_display_tab)',
    issue: 'Removed Separate Search Window & Embedded Per-Screen Playback + TAGS Controls in Display Tab',
    cause:
      'User requested removing the standalone floating search window (`FloatingSearchBar`) and placing its features into the Display tab under the "Select Screen" dropdown and the "Display wallpaper on this screen" checkbox without a minimize button, with Refresh (⟳), Previous (◀), Next (▶), and Pause (PAUSE) placed above the new TAGS search bar.',
    fix: 'Removed `FloatingSearchBar` and the Credentials tab lock toggle. Built `self.search_subpanel` in `SettingsDialog._build_display_tab()` directly below `screen_row` and `enable_row` (no minimize button). Placed `self.search_controls_row` (status badge + `⟳`, `◀`, `▶`, `PAUSE` wired strictly to the currently selected screen) directly above `self.tag_search_row` (`TAGS =`).',
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
      'User requested auto-suggestions to populate below the TAGS search box, a permanent 4-layer scrollable box below the TAGS search box showing all tags of the selected screen\'s most recently displayed media (with click-to-append), and Danbooru category color coordination across all 3 locations.',
    fix: 'Positioned `self.suggest_dropdown` and `self.saved_dropdown` strictly below `self.search_container` (`ry = rooty + height + 2`). Added `self.media_tags_text` (`height=4, wrap="word"` + vertical `ttk.Scrollbar`) populated via `GET /report_shown?screen=<id>&post_id=<id>` from `index.html`. Configured `DANBOORU_TAG_COLORS` (0=General Blue, 1=Artist Red, 3=Copyright Purple, 4=Character Green, 5=Meta Orange) across `self.tag_input`, `self.suggest_labels`, and `self.media_tags_text`.',
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
  const [simScreen, setSimScreen] = useState<'screen_1' | 'screen_2'>('screen_1');
  const [simScreensState, setSimScreensState] = useState<{
    screen_1: { enabled: boolean; paused: boolean; tags: string; mode: string; postIdx: number };
    screen_2: { enabled: boolean; paused: boolean; tags: string; mode: string; postIdx: number };
  }>({
    screen_1: {
      enabled: true,
      paused: false,
      tags: 'scenery no_humans highres',
      mode: 'masonry',
      postIdx: 0,
    },
    screen_2: {
      enabled: true,
      paused: false,
      tags: 'genshin_impact furina_(genshin_impact) wlop',
      mode: 'slideshow',
      postIdx: 0,
    },
  });
  const [simShowSuggest, setSimShowSuggest] = useState(false);

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
    simScreensState.screen_1.tags.trim().toLowerCase() ===
      simScreensState.screen_2.tags.trim().toLowerCase();

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

  const appendTagToSimScreen = (tag: string) => {
    setSimScreensState((prev) => {
      const existing = prev[simScreen].tags.trim();
      const tokens = existing ? existing.split(/\s+/) : [];
      if (tokens.some((t) => t.replace(/^[-~]+/, '').toLowerCase() === tag.toLowerCase())) {
        return prev;
      }
      return {
        ...prev,
        [simScreen]: {
          ...prev[simScreen],
          tags: existing ? `${existing} ${tag}` : tag,
        },
      };
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
            Danbooru Wallpaper Suite v2.3.0 — Per-Screen Display Tab Search, Danbooru Tag Colors & Shared Pools
          </h1>
          <p className={`text-xs mt-0.5 ${isDark ? 'text-zinc-400' : 'text-zinc-600'}`}>
            Integrated Display Tab Search • Per-Screen ⟳ / ◀ / ▶ / PAUSE • Shared Tag-Pool Deduplication • 4-Layer Media Tags Box • Instant Left-Click Tray
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
              Requirements & Security Audit ({FEATURE_SUMMARY_ITEMS.length + SECURITY_AUDIT_ITEMS.length})
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
                Verified v2.3.0 Updates
              </div>
              <div>
                • <strong>Standalone search window removed</strong>; controls embedded in Display tab (no minimize button).
              </div>
              <div>
                • <strong>⟳, ◀, ▶, PAUSE</strong> placed above TAGS bar and below Screen Select & Display checkbox.
              </div>
              <div>
                • <strong>Per-screen TAGS & Shared Pools</strong>: unchecked screens never fetch; identical tags share one pool.
              </div>
              <div>
                • <strong>4-Layer Displayed Media Tags Box</strong> & <strong>Danbooru Category Colors</strong> across all 3 tag areas.
              </div>
              <div>
                • <strong>Instant Tray Left-Click</strong> opens Settings directly; right-click shows Exit menu.
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
                Interactive Simulation of the Updated SettingsDialog &rarr; Display Tab
              </h2>
              <p className={`text-xs mt-0.5 ${isDark ? 'text-zinc-400' : 'text-zinc-600'}`}>
                Test switching screens, unchecking display (stops media fetch), clicking color-coded tags in the 4-layer Displayed Media Tags box, or typing tags to see Danbooru category color coordination.
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

            {/* Notebook Tabs */}
            <div className="px-3 pt-2 flex gap-1 border-b border-zinc-700/40 text-xs font-bold">
              <span className={`px-3.5 py-1.5 rounded-t opacity-60 ${isDark ? 'bg-[#232329]' : 'bg-[#e8e8ed]'}`}>
                Credentials
              </span>
              <span className="px-3.5 py-1.5 rounded-t bg-[#0067c0] text-white">Display</span>
              <span className={`px-3.5 py-1.5 rounded-t opacity-60 ${isDark ? 'bg-[#232329]' : 'bg-[#e8e8ed]'}`}>
                Logs
              </span>
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
                {/* 3a. Control Row ABOVE the TAGS Search Bar */}
                <div className="flex items-center justify-between gap-2">
                  <span
                    className={`px-2.5 py-1 rounded font-bold text-[11px] ${
                      !curScreenState.enabled
                        ? isDark
                          ? 'bg-[#232329] text-zinc-400'
                          : 'bg-[#e8e8ed] text-zinc-600'
                        : curScreenState.paused
                        ? 'bg-blue-500/20 text-blue-400'
                        : isDark
                        ? 'bg-[#18331a] text-[#6ccb5f]'
                        : 'bg-[#dff6dd] text-[#0f7b0f]'
                    }`}
                  >
                    {!curScreenState.enabled
                      ? '○ Screen Disabled (No Fetch)'
                      : curScreenState.paused
                      ? '⏸ Screen Paused'
                      : '✔ P:1 (84 pooled)'}
                  </span>

                  <div className="flex items-center gap-1.5">
                    <button
                      onClick={() =>
                        setSimScreensState((prev) => ({
                          ...prev,
                          [simScreen]: { ...prev[simScreen], postIdx: prev[simScreen].postIdx + 1 },
                        }))
                      }
                      title="Refresh selected screen tag pool"
                      className={`px-2.5 py-1 rounded border font-bold cursor-pointer flex items-center gap-1 ${
                        isDark
                          ? 'bg-[#232329] border-[#323238] hover:bg-[#2e2e36]'
                          : 'bg-[#e8e8ed] border-[#b8b8c0] hover:bg-[#dcdce2]'
                      }`}
                    >
                      <RotateCw className="w-3.5 h-3.5" />
                    </button>
                    <button
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
                      className={`px-2 py-1 rounded border font-bold cursor-pointer ${
                        isDark
                          ? 'bg-[#232329] border-[#323238] hover:bg-[#2e2e36]'
                          : 'bg-[#e8e8ed] border-[#b8b8c0] hover:bg-[#dcdce2]'
                      }`}
                    >
                      <ChevronLeft className="w-3.5 h-3.5" />
                    </button>
                    <button
                      onClick={() =>
                        setSimScreensState((prev) => ({
                          ...prev,
                          [simScreen]: { ...prev[simScreen], postIdx: prev[simScreen].postIdx + 1 },
                        }))
                      }
                      title="Next media on selected screen"
                      className={`px-2 py-1 rounded border font-bold cursor-pointer ${
                        isDark
                          ? 'bg-[#232329] border-[#323238] hover:bg-[#2e2e36]'
                          : 'bg-[#e8e8ed] border-[#b8b8c0] hover:bg-[#dcdce2]'
                      }`}
                    >
                      <ChevronRight className="w-3.5 h-3.5" />
                    </button>
                    <button
                      onClick={() =>
                        setSimScreensState((prev) => ({
                          ...prev,
                          [simScreen]: { ...prev[simScreen], paused: !prev[simScreen].paused },
                        }))
                      }
                      className={`px-3 py-1 rounded font-bold cursor-pointer flex items-center gap-1 ${
                        curScreenState.paused
                          ? 'bg-[#0067c0] text-white'
                          : isDark
                          ? 'bg-[#232329] text-zinc-100 hover:bg-[#2e2e36]'
                          : 'bg-[#e8e8ed] text-zinc-900 hover:bg-[#dcdce2]'
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
                </div>

                {/* 3b. TAGS Search Row with Danbooru Category Colors & Below-Input Auto-Suggestions */}
                <div className="relative">
                  <div className="flex items-center gap-2">
                    <span className="font-bold shrink-0">TAGS =</span>
                    <div
                      className={`flex-1 flex items-center rounded border overflow-hidden ${
                        isDark ? 'bg-[#1c1c21] border-[#323238]' : 'bg-white border-[#b8b8c0]'
                      }`}
                    >
                      <input
                        type="text"
                        value={curScreenState.tags}
                        onFocus={() => setSimShowSuggest(true)}
                        onChange={(e) => {
                          setSimScreensState((prev) => ({
                            ...prev,
                            [simScreen]: { ...prev[simScreen], tags: e.target.value },
                          }));
                          setSimShowSuggest(true);
                        }}
                        className="flex-1 px-2.5 py-1.5 bg-transparent outline-none font-mono text-xs font-bold"
                        placeholder="Type Danbooru tags..."
                      />
                      <button
                        onClick={() => setSimShowSuggest((v) => !v)}
                        title="Toggle suggestions below input"
                        className={`px-2.5 py-1.5 border-l cursor-pointer ${
                          isDark ? 'bg-[#232329] border-[#323238]' : 'bg-[#ececf0] border-[#b8b8c0]'
                        }`}
                      >
                        <ChevronDown className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>

                  {/* Color-coded token preview bar matching the Tkinter Text widget coloring */}
                  <div className="mt-1.5 flex flex-wrap items-center gap-1.5 pl-14">
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

                  {/* Auto-Suggestion Dropdown (Populates BELOW the TAGS search box) */}
                  {simShowSuggest && (
                    <div
                      className={`mt-1 ml-14 rounded border shadow-lg overflow-hidden z-20 ${
                        isDark ? 'bg-[#1c1c21] border-[#323238]' : 'bg-white border-[#b8b8c0]'
                      }`}
                    >
                      <div className="px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider opacity-60 border-b border-zinc-700/30 flex justify-between">
                        <span>Auto-Suggestions (Populates Below TAGS Search Box)</span>
                        <button onClick={() => setSimShowSuggest(false)} className="cursor-pointer">
                          ✕
                        </button>
                      </div>
                      {SAMPLE_SUGGESTIONS.slice(0, 5).map((s) => (
                        <div
                          key={s.name}
                          onClick={() => {
                            appendTagToSimScreen(s.name);
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
                            onClick={() => appendTagToSimScreen(t.name)}
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
              v2.3.0 Requirements Implementation Summary (Requirements 1 through 9)
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
