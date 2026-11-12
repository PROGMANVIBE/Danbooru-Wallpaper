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
} from 'lucide-react';

type FileKey = 'CHANGELOG.md' | 'README.md' | 'danbooru_service.py' | 'index.html' | 'project.json';
type ViewTab = 'code' | 'audit' | 'build';

const FILE_LIST: { key: FileKey; path: string; label: string; desc: string }[] = [
  {
    key: 'CHANGELOG.md',
    path: '/updated_files/CHANGELOG.md',
    label: 'CHANGELOG.md',
    desc: 'v2.2.0 release notes covering the Mondrian vs. Rows toggle, removal of blurred sections in Rows mode, layout toggle freeze fix, background pre-rendering/pre-organization of the next Masonry switch, and the Windows Task Manager Resource Graph pop-out.',
  },
  {
    key: 'README.md',
    path: '/updated_files/README.md',
    label: 'README.md',
    desc: 'Comprehensive documentation covering the 4 display modes (Scroll, Polaroid, Slideshow, Masonry with Mondrian ⇄ Rows), the Task Manager Resource Graph pop-out, Previous (◀) & Next (▶) search bar buttons, and anti-malware /media proxy.',
  },
  {
    key: 'danbooru_service.py',
    path: '/updated_files/danbooru_service.py',
    label: 'danbooru_service.py',
    desc: 'Updated service with the top-bar "📊 Resource Graph" Task Manager Performance pop-out (CPU, RAM, GPU telemetry across Python + WebView2), "Mondrian ⇄" / "Rows ⇄" toggle button, and single-flight async property synchronization eliminating cross-thread GUI freezes.',
  },
  {
    key: 'index.html',
    path: '/updated_files/index.html',
    label: 'index.html',
    desc: 'WebView2 frontend featuring Mondrian vs. Rows (with all blurred sections removed in Rows mode), background pre-rendering & pre-organization of the next media switch 1.2s before flip initiation, 1280px bounded texture downscaling with zero memory bloat, and group re-indexing.',
  },
  {
    key: 'project.json',
    path: '/updated_files/project.json',
    label: 'project.json',
    desc: 'Wallpaper configuration schema updated with Masonry Layout options relabeled to "Mondrian" (mondrian) and "Rows" (rows), plus Tile Count (4–36), Gap (0–10 px), and Delay (1–60 s).',
  },
];

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
    id: 'FEAT-01',
    severity: 'CRITICAL BUG FIX (Fatal Freeze on >3 Layout Toggles)',
    file: 'danbooru_service.py & index.html',
    issue: 'Cross-Thread Win32 & WebView2 IPC Deadlock When Toggling Between Mondrian and Rows (>3 Times)',
    cause:
      'Clicking the Masonry layout toggle button called `push_properties_to_webview(sid)` synchronously on the Tkinter UI thread, which ran blocking Win32 `SetWindowPos(..., SWP_FRAMECHANGED)`, `SendMessageW(WM_SIZE)`, and `RedrawWindow(..., RDW_UPDATENOW)` calls on the WebView2 HWND followed by a synchronous `win.evaluate_js(...)` semaphore wait and a redundant `window.dispatchEvent(new Event(\'resize\'))`. Rapidly toggling >3 times deadlocked the Tkinter GUI thread against the WebView2 WinForms UI thread with zero Python exceptions or log messages. In addition, `solveAspectLockedSubtree()` in `index.html` reordered `masonryGroups` when `numGroups >= 3` without re-indexing `group.index` and `tile.groupIndex`.',
    fix: 'Replaced synchronous property pushes with a coalesced single-flight background worker (`_property_push_worker`), restricted Win32 geometry sync strictly to screen `enabled` state changes with `SWP_ASYNCWINDOWPOS = 0x4000`, added `prop_seq` in `/epoch` as a lock-free poll fallback, removed the redundant `resize` dispatch, and re-indexed `masonryGroups` after BSP solving.',
  },
  {
    id: 'FEAT-02',
    severity: 'PERFORMANCE & VISUAL UPDATE',
    file: 'index.html, danbooru_service.py, project.json',
    issue: 'Removed Blurred Sections in Rows Mode, Relabeled Mondrian vs. Rows & Pre-Staged Next Masonry Switch Without Memory Bloat',
    cause:
      'User requested removing the blurred/ambient sections when the Google Photos (Rows) option is selected, relabeling the toggle button and config to "Mondrian" vs. "Rows", and implementing background pre-rendering/pre-organization of the next media switch while preventing continuous memory bloat.',
    fix: 'Added `#stage.rows-mode` CSS and JS guards so `Rows` mode removes all ambient/blurred backgrounds (`background-image: none`) and fills each justified row tile (`object-fit: cover`). Relabeled the toggle button and schema to `Mondrian` (`mondrian`) vs. `Rows` (`rows`). Implemented `preStageNextMasonrySwitch()` + `precomputeGroupReflowPlan()` 1.2s prior to flip initiation to pre-decode the next media node in a single hidden `.masonry-prestage-slot` and pre-calculate all FLIP matrices ahead of time, paired with 1280px static image downscaling on a reusable 1×1-reset canvas and immediate Blob URL revocation.',
  },
  {
    id: 'FEAT-03',
    severity: 'NEW TELEMETRY POP-OUT & 100% SYSTEM RAM SCALING',
    file: 'danbooru_service.py (AppResourceMonitor & ResourceGraphDialog)',
    issue: 'Windows Task Manager Performance-Style "Resource Graph" Pop-Out with True 0%–100% Total Physical RAM Scaling',
    cause:
      'User requested a "Resource Graph" pop-out styled like Windows Task Manager Performance graphs, and reported that the Memory graph previously scaled against a 4096 MB dynamic ceiling—making 6.9% RAM usage (2215.2 MB of 32 GB) look like ~70% utilization.',
    fix: 'Added the `📊 Resource Graph` button in `SettingsDialog` and updated `ResourceGraphDialog` so the Memory graph (in the left sidebar mini sparkline, single Memory view, and All Graphs 3x stacked view) plots `ram_pct_history` against `100.0` (0%–100% of total physical system memory) so 6.9% RAM usage renders at its true 6.9% vertical height.',
  },
  {
    id: 'FEAT-04',
    severity: 'HIGH-STRESS STABILITY FIX (36-Tile Masonry Rapid Next Clicks)',
    file: 'danbooru_service.py & index.html',
    issue: 'Prevent Application Freeze & ~50% GPU Spike When Rapidly Clicking "Next" in 36-Tile Masonry Mode',
    cause:
      'Pressing "Next" (~6 times/sec) with 36 Masonry tiles spawned dozens of concurrent `_async_evaluate_js` threads in Python and bypassed `busyGroups` in `triggerNextMasonryFlip(true)`, launching overlapping 3D GPU card flips, mid-reflow geometry recalculations, and concurrent scratch-canvas downscales.',
    fix: 'Implemented a 1.0-second internal cooldown (`NAV_BUTTON_COOLDOWN_SEC = 1.0` in Python with button visual state + `MANUAL_NAV_COOLDOWN_MS = 1000` in JS), replaced per-call thread spawning in `_async_evaluate_js` with a single-flight queue worker (`_js_eval_worker`), added `isAnyMasonryTileBusy()` so strictly 1 tile flips/reflows at a time, serialized `downscaleScratchCanvas`, and capped steady-state `readyImageQueue` to 10 items once all 36 tiles are populated.',
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
            Danbooru Wallpaper Suite v2.1 — Polaroid, Masonry, Queue Controls & Security Hardening
          </h1>
          <p className={`text-xs mt-0.5 ${isDark ? 'text-zinc-400' : 'text-zinc-600'}`}>
            4 Display Modes (Scroll • Polaroid • Slideshow • Masonry) • Prev/Next Search Controls • Anti-Malware Binary Magic-Byte Proxy
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
              Security Audit & Feature Report ({SECURITY_AUDIT_ITEMS.length + FEATURE_SUMMARY_ITEMS.length})
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
                Verified Security & Feature Updates
              </div>
              <div>
                • <strong>Polaroid</strong> rename applied across all UI controls, properties, and documentation.
              </div>
              <div>
                • <strong>Masonry</strong> mode with 4–36 tiles, 0–10px gap, 1–60s delay, 3D Y-flip, neighbor reflow, and full GIF/MP4 playthrough verification.
              </div>
              <div>
                • <strong>Previous (◀) & Next (▶)</strong> vertical rectangle search bar buttons.
              </div>
              <div>
                • <strong>Anti-Malware / PHP Inspection</strong> via binary magic-byte verification and strict URL path filtering.
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

      {activeTab === 'audit' && (
        <div className="flex-1 overflow-auto p-6 max-w-5xl mx-auto w-full space-y-6">
          <div
            className={`p-4 rounded border ${
              isDark ? 'border-zinc-800 bg-[#121218]' : 'border-zinc-300 bg-white'
            }`}
          >
            <h2 className="text-sm font-bold flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-emerald-500" />
              PHP & Malware Download Vulnerability Audit (SEC-01 through SEC-05)
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

          <div
            className={`p-4 rounded border ${
              isDark ? 'border-zinc-800 bg-[#121218]' : 'border-zinc-300 bg-white'
            }`}
          >
            <h2 className="text-sm font-bold flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-blue-500" />
              Feature & Display Mode Implementation Summary
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
