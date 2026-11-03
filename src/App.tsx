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
} from 'lucide-react';

type FileKey = 'CHANGELOG.md' | 'README.md' | 'danbooru_service.py' | 'index.html' | 'project.json';
type ViewTab = 'code' | 'audit' | 'build';

const FILE_LIST: { key: FileKey; path: string; label: string; desc: string }[] = [
  {
    key: 'CHANGELOG.md',
    path: '/updated_files/CHANGELOG.md',
    label: 'CHANGELOG.md',
    desc: 'Concise GitHub Release changelog summarizing the ephemeral /media proxy, Hybrid HTTP/2 + DoH transport, new display modes, UI enhancements, and bug fixes.',
  },
  {
    key: 'README.md',
    path: '/updated_files/README.md',
    label: 'README.md',
    desc: 'Updated comprehensive documentation covering the ephemeral /media proxy, Hybrid HTTP/2 + DoH transport, 3 display modes (Scroll, Collage, Slideshow), Light/Dark mode, PyInstaller CLI build, and expanded Log Glossary.',
  },
  {
    key: 'danbooru_service.py',
    path: '/updated_files/danbooru_service.py',
    label: 'danbooru_service.py',
    desc: 'Hybrid Transport Engine (curl_cffi HTTP/2 + automatic stdlib DoH/SNI fallback), PyInstaller --noconsole stdout guard, SetWindowLongPtrW fix, /media proxy, dynamic Display tab, Light/Dark mode, and Logs Glossary.',
  },
  {
    key: 'index.html',
    path: '/updated_files/index.html',
    label: 'index.html',
    desc: 'WebView2 frontend routing all img/video traffic through local /media proxy, dynamic LOCAL_ORIGIN resolution, 4-way scroll, and orientation-matched fullscreen slideshow with anti-starvation pagination.',
  },
  {
    key: 'project.json',
    path: '/updated_files/project.json',
    label: 'project.json',
    desc: 'Wallpaper schema with 4-way scroll directions (left, right, up, down), Fullscreen Slideshow mode, fade transition (0–10 [0s–1s]), and slide duration (0–600s).',
  },
];

const AUDIT_ITEMS = [
  {
    id: 'ERR-01',
    severity: 'CRITICAL (Reported Crash)',
    file: 'danbooru_service.py (Line 49)',
    issue: "ModuleNotFoundError: No module named 'curl_cffi' on executable startup",
    cause:
      'Top-level unguarded import `from curl_cffi import requests as curl_requests` crashed immediately when the Python environment used to run PyInstaller did not have curl_cffi installed or when its native libcurl CFFI binary extensions were omitted from the bundle.',
    fix: 'Wrapped `curl_cffi` import in a guarded `try/except ImportError` and engineered a complete standard-library fallback (`DoHSNIHTTPSConnection`, `DoHSNIHTTPSHandler`, `StdlibDoHSession`) that connects TCP sockets directly to Cloudflare DoH-resolved IPs while passing `server_hostname=target_host` for TLS 1.3 SNI and certificate verification.',
  },
  {
    id: 'ERR-02',
    severity: 'HIGH',
    file: 'danbooru_service.py',
    issue: 'Circular dependency & DNS poisoning risk in resolve_hostname_doh()',
    cause:
      'Previously, `resolve_hostname_doh()` called `get_http2_session()` and connected to `https://cloudflare-dns.com/dns-query` via system DNS, which risked ISP DNS blocking on `cloudflare-dns.com` or recursion during session initialization.',
    fix: 'Implemented `_query_cloudflare_doh_direct()` which connects a raw TLS 1.3 socket directly to Cloudflare anycast IPs (`1.1.1.1` / `1.0.0.1` port 443) with `server_hostname="cloudflare-dns.com"`, bypassing system DNS completely.',
  },
  {
    id: 'ERR-03',
    severity: 'HIGH',
    file: 'danbooru_service.py',
    issue: 'PyInstaller --noconsole / --windowed crash on print()',
    cause:
      'When packaged with PyInstaller `--noconsole` (`-w`), `sys.stdout` and `sys.stderr` are `None` on Windows. Unchecked `print()` calls in `log_event()` or `init_persistent_storage()` can raise `AttributeError` or `OSError: [Errno 9] Bad file descriptor`.',
    fix: 'Added `safe_console_print(msg)` which checks `if sys.stdout is not None` and wraps `print(..., flush=True)` in a `try/except Exception` block.',
  },
  {
    id: 'ERR-04',
    severity: 'MEDIUM',
    file: 'danbooru_service.py',
    issue: 'Win32 SetWindowLongPtrW 32-bit fallback bug',
    cause:
      '`SetWindowLongPtrW = getattr(user32, "SetWindowLongPtrW", user32.GetWindowLongW)` mistakenly fell back to `GetWindowLongW` instead of `SetWindowLongW` on 32-bit Python builds.',
    fix: 'Corrected fallback to `getattr(user32, "SetWindowLongPtrW", user32.SetWindowLongW)`.',
  },
  {
    id: 'ERR-05',
    severity: 'MEDIUM',
    file: 'index.html',
    issue: 'Slideshow orientation filter starvation on single-orientation batches',
    cause:
      'In Fullscreen Slideshow mode, if an entire `/api` batch contained only opposite-orientation posts (e.g. 40 portrait images on a 16:9 landscape monitor), `filtered` was empty and the slideshow waited until the next user interaction or slow backoff.',
    fix: 'Added automatic fast follow-up pagination (`setTimeout(() => fetchNextPage(), 420)`) whenever `filtered.length === 0` in `slideshow` mode, plus dynamic `LOCAL_ORIGIN` resolution.',
  },
  {
    id: 'ERR-06',
    severity: 'CRITICAL (Runtime Request Error & Fallback Bypass)',
    file: 'danbooru_service.py',
    issue: "Fetch error: Session.request() got an unexpected keyword argument 'curl_options' & Fallback Did Not Trigger",
    cause:
      "1) In curl_cffi, `curl_options` is a Session.__init__() argument (stored on `session._curl_options`), NOT a per-request keyword argument on `Session.get()` / `Session.request()`. Passing `curl_options` to `sess.get()` raised a `TypeError`. 2) The fallback did not trigger because `rebuild_http2_session()` only caught exceptions during `import curl_cffi` and `Session()` initialization. Once `Session()` succeeded, `HTTP2_SESSION` was a raw `curl_cffi.requests.Session` object—so request-time errors inside `sess.get()` escaped directly to `fill_post_buffer()`'s retry loop instead of switching to `StdlibDoHSession`.",
    fix: 'Created `HybridDoHSession`, which wraps both `curl_cffi.requests.Session` and `StdlibDoHSession`. Removed `curl_options` from `sess.get()`, applied `CURLOPT_RESOLVE` directly onto `session._curl_options`, and added a request-time try/except fallback inside `HybridDoHSession.get()` that immediately switches to `StdlibDoHSession` on any curl_cffi runtime error without failing the request.',
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
            <FileCode className="w-5 h-5 text-blue-500" />
            Danbooru Ephemeral HTTP/2 Wallpaper Suite — Crash Fix & Codebase Audit
          </h1>
          <p className={`text-xs mt-0.5 ${isDark ? 'text-zinc-400' : 'text-zinc-600'}`}>
            Hybrid Transport (curl_cffi HTTP/2 + Stdlib DoH/SNI Fallback) • PyInstaller --onefile --noconsole Ready
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
              Updated Source Files (4)
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
              Codebase Audit & Fixes ({AUDIT_ITEMS.length})
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
            className={`w-full lg:w-80 border-b lg:border-b-0 lg:border-r p-4 flex flex-col gap-3 ${
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
                Zero-Crash Hybrid Transport
              </div>
              <div>
                • Automatically uses <code className="font-mono">curl_cffi</code> HTTP/2 Chrome impersonation when installed.
              </div>
              <div>
                • Seamlessly falls back to Python stdlib <code className="font-mono">DoHSNIHTTPSConnection</code> (Cloudflare 1.1.1.1 DoH + TLS 1.3 SNI) if <code className="font-mono">curl_cffi</code> is absent in the PyInstaller executable.
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
        <div className="flex-1 overflow-auto p-6 max-w-5xl mx-auto w-full space-y-4">
          <div
            className={`p-4 rounded border ${
              isDark ? 'border-zinc-800 bg-[#121218]' : 'border-zinc-300 bg-white'
            }`}
          >
            <h2 className="text-sm font-bold flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-amber-500" />
              Diagnostic & Codebase Audit Report
            </h2>
            <p className={`text-xs mt-1 ${isDark ? 'text-zinc-400' : 'text-zinc-600'}`}>
              All 5 potential runtime and packaging issues across <code className="font-mono">danbooru_service.py</code>,{' '}
              <code className="font-mono">index.html</code>, and <code className="font-mono">project.json</code> have been resolved.
            </p>
          </div>

          <div className="space-y-3">
            {AUDIT_ITEMS.map((item) => (
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
                    <span className="font-bold text-amber-500">Root Cause: </span>
                    {item.cause}
                  </div>
                  <div>
                    <span className="font-bold text-emerald-500">Implemented Fix: </span>
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
              Note: Even if you build the executable without <code className="font-mono">--collect-all &quot;curl_cffi&quot;</code> or on a machine without <code className="font-mono">curl_cffi</code> installed, the updated <code className="font-mono">danbooru_service.py</code> will no longer crash—it will automatically run using the built-in <code className="font-mono">StdlibDoHSession</code> (Cloudflare 1.1.1.1 DoH + TLS 1.3 SNI).
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
