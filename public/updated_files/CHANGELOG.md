# Changelog — v2.0.0 (Pure API & Ephemeral Proxy Release)

## 🚀 Core Architectural Overhaul

- **Ephemeral Local `/media` Streaming Proxy**:
  - Routed all frontend `<img>` and `<video>` traffic exclusively through `http://127.0.0.1:8088/media?url=<encoded_cdn_url>` with HTTP `Range` (`206 Partial Content`) support for MP4 scrubbing/looping.
  - Eliminated direct WebView2 requests to `cdn.donmai.us`, preventing Cloudflare `403 Forbidden` blocks and completely removing the persistent `webview_profile` disk cache folder.
- **Hybrid HTTP/2 + Cloudflare DoH Transport Engine (`HybridDoHSession`)**:
  - Replaced legacy Cloudflare challenge browser windows and `cf_clearance` cookie persistence with a cookie-free, authenticated pipeline.
  - Uses `curl_cffi` HTTP/2 Chrome TLS impersonation with automatic runtime fallback to a zero-dependency standard-library `StdlibDoHSession` (`DoHSNIHTTPSConnection` over TLS 1.3 + SNI) if `curl_cffi` is absent or raises a request-time error.
  - Added direct Cloudflare DNS-over-HTTPS (`https://cloudflare-dns.com/dns-query` via `1.1.1.1` / `1.0.0.1`) resolution to bypass ISP DNS blocks and poisoning.
- **Danbooru API Compliance & DPAPI Credential Security**:
  - Enforced Danbooru API rate-limiting, compliant `User-Agent` headers, and HTTP Basic Auth (`login` + `api_key`).
  - Removed all hardcoded default credentials; credentials are loaded strictly from the Application Settings **Credentials** tab and encrypted at rest in `%APPDATA%\DanbooruWallpaper\config.json` via Windows DPAPI (`CryptProtectData`).

---

## ✨ New Wallpaper & UI Features

- **4-Way Continuous Scroll Mode**:
  - Added vertical scrolling (**Up** and **Down** with automatic multi-column calculation) alongside existing **Left** and **Right** horizontal scrolling.
  - Expanded Scroll Speed range to `0.1 – 600 px/s` (`0.1` step precision) and Image Gap range to `0 – 64 px`.
- **Fullscreen Orientation-Matched Slideshow Mode**:
  - Displays one image or video at a time in fullscreen (`object-fit: cover`), automatically filtering posts to match the target monitor's aspect ratio (Landscape vs. Portrait) with anti-starvation auto-pagination.
  - Added configurable **Fade Transition** (`0 – 10` [`0.0s – 1.0s`]) and **Slide Display Time** (`0 – 600 s`, waits for videos to finish at `0`).
- **Enhanced Polaroid Collage Mode**:
  - Expanded Spawn/Drop Delay to `0 – 600 s`.
  - Added a **Fill Screen** burst button in the Display tab with a 30-second cooldown timer and live countdown.
- **Dynamic Display Settings, Light/Dark Theme & Controls**:
  - Display tab now dynamically shows/hides sliders based on the active Display Mode (`Scroll`, `Collage`, or `Slideshow`) and resets defaults solely for the active mode and screen.
  - Added a persistent **Light Mode / Dark Mode** toggle in the Credentials tab that themes both the Floating Search Bar and Application Settings windows.
  - Added dual pause controls (**Master Application Pause** in Settings vs. **Wallpaper Motion Pause** on the Search Bar) and a Search Bar **Lock** toggle.
  - Added a **Logs Glossary** popup window documenting all `[CATEGORY]` log prefixes.
  - Enforced a strict **15 MB maximum file size filter** for `.mp4` animations across API metadata filtering and `/media` streaming.

---

## 🐛 Bug Fixes & Packaging Improvements

- **Fixed `curl_cffi` `Session.request()` Keyword Error**: Removed unsupported per-request `curl_options` arguments from `Session.get()` calls and applied `CURLOPT_RESOLVE` entries at the session level, with automatic request-time fallback to `StdlibDoHSession`.
- **Fixed PyInstaller `--onefile --noconsole` Crashes**: Guarded `curl_cffi` imports and added `safe_console_print()` to prevent `NoneType` `sys.stdout` crashes in windowed builds.
- **Fixed Win32 32-Bit Pointer Fallback**: Corrected `SetWindowLongPtrW` fallback from `GetWindowLongW` to `SetWindowLongW`.
