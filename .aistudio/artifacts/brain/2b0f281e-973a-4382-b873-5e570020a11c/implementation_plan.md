# Hybrid DoH/SNI Transport Fix & Full Codebase Audit

This plan resolves the `ModuleNotFoundError: No module named 'curl_cffi'` executable crash by introducing a resilient Hybrid HTTP Transport Engine (`curl_cffi` HTTP/2 when installed, with automatic zero-dependency fallback to Python's standard-library TLS 1.3 + Cloudflare DoH + SNI socket transport) and fixes several subtle Windows PyInstaller (`--onefile --noconsole`) runtime bugs across the codebase.

## User Review & Critical Decisions

> [!IMPORTANT]
> Your confirmed preferences from Phase 1 have been incorporated into this architecture:

- **Confirmed Decision 1 (Transport Layer)**: **Hybrid `curl_cffi` + Automatic Standard-Library DoH/SNI Fallback**. If `curl_cffi` is present in the Python environment or PyInstaller bundle, the service uses `curl_cffi` with Chrome HTTP/2 impersonation. If `curl_cffi` is absent, the service seamlessly falls back to a custom Python standard-library `urllib` + `ssl` + `http.client.HTTPSConnection` transport that connects directly to Cloudflare DoH-resolved IPs while preserving TLS 1.3 Server Name Indication (`server_hostname`) and certificate validation.
- **Confirmed Decision 2 (Executable Packaging)**: **PyInstaller CLI (`--onefile --noconsole`) Compatibility**. All console I/O, bundled resource paths (`sys._MEIPASS`), and ephemeral WebView2 storage paths are hardened specifically for single-file GUI executables built via the PyInstaller CLI.

---

## 1. Overview & Core Concept

- **What It Does**: Eliminates hard crashes when launching the compiled `.exe` without `curl_cffi` bundled, while preserving 100% of the pure API authentication, Cloudflare DoH hostname resolution (`1.1.1.1`), local `/media` binary proxy streaming, 4-way continuous scroll, orientation-matched fullscreen slideshow, Light/Dark theme switching, and Logs Glossary features.
- **Target Audience / Persona**: Desktop wallpaper power users running the application either as a standalone compiled Windows `.exe` (`--onefile --noconsole`) or directly from a Python script.
- **Key Value**: The executable runs out-of-the-box in any build environment without `ModuleNotFoundError` or `--noconsole` stdout crashes, while still supporting optional `curl_cffi` Chrome TLS fingerprinting when installed.

---

## 2. User Experience & Visual Design

- **Key User Flows**:
  1. **Zero-Crash Startup**: On launch, the backend detects whether `curl_cffi` is available and logs the active transport mode (`[AUTH] Transport: curl_cffi HTTP/2` or `[AUTH] Transport: stdlib TLS 1.3 + DoH SNI`) in the Logs tab.
  2. **Settings & Theme Switching**: Users can switch between Light Mode and Dark Mode in the Credentials tab, configure per-monitor Scroll (`left`, `right`, `up`, `down`), Collage, or Fullscreen Slideshow settings in the dynamically revealed Display tab, and inspect log definitions in the Glossary window.
  3. **Web Preview & Build Inspector**: The companion web interface provides one-click copy and download for the updated Python, HTML, and JSON files, alongside ready-to-run PyInstaller CLI commands and a comprehensive audit report of all fixed issues.
- **Visual Identity & Theme**:
  - *Aesthetic Direction*: Utilitarian developer & desktop utility console with crisp structural borders and high-contrast light/dark modes.
  - *Color Palette & Mood*:
    - Dark Mode (`--background`: `#0f0f12`, `--surface`: `#1a1a20`, `--border`: `#2e2e38`, `--text`: `#ffffff`, `--accent`: `#0067c0`).
    - Light Mode (`--background`: `#f6f6f8`, `--surface`: `#ffffff`, `--border`: `#dcdce0`, `--text`: `#1c1c1c`, `--accent`: `#0067c0`).
  - *Typography & Hierarchy*: `Plus Jakarta Sans` / `Segoe UI` for UI controls and headings paired with `JetBrains Mono` / `Consolas` (`tabular-nums`) for log streams, numeric sliders, and build commands.
  - *Component Styling & Layout*: Single-elevation panels separated by 1px solid borders, 1:3 grid ratio for numeric entry + horizontal slider pairs, and dynamic section visibility based on the active display mode.
- **Interactive Feedback & Motion**:
  - Immediate 40ms debounced live preview when adjusting sliders or switching display modes.
  - Hardware-accelerated `translate3d` for 4-way infinite scroll and GPU-composited `opacity` cross-fades (`0.0s` to `1.0s`) for orientation-matched fullscreen slideshows.

---

## 3. Key Product Decisions & Trade-Offs

- **Decision 1: Hybrid HTTP Transport (`curl_cffi` + Custom Stdlib `DoHSNIHTTPSHandler`)**
  - *Chosen Approach*: Guard the `curl_cffi` import in a `try...except ImportError` block and provide a unified `UnifiedHttpClient` interface backed by either `curl_cffi.requests.Session` or a custom `urllib.request.OpenerDirector` using `DoHSNIHTTPSHandler`.
  - *Why*: Standard `urllib.request` fails when connecting to an IP URL (`https://104.x.x.x/...`) because TLS SNI and hostname verification expect `danbooru.donmai.us` or `cdn.donmai.us`. Our custom `DoHSNIHTTPSConnection` overrides `connect()` to open the TCP socket to the Cloudflare DoH-resolved IP while passing `server_hostname=original_host` to `ssl_context.wrap_socket()`, achieving true DoH + TLS 1.3 SNI in pure Python without requiring external C extensions.
  - *Alternatives Considered*: Forcing the user to manually configure PyInstaller hooks for `curl_cffi` C binaries (prone to breaking across Python/OS updates) or dropping `curl_cffi` support entirely.
- **Decision 2: Direct IP DoH Bootstrapping (`https://1.1.1.1/dns-query`)**
  - *Chosen Approach*: Query Cloudflare's DoH endpoint over `1.1.1.1` (with TLS SNI `cloudflare-dns.com`) using a dedicated bootstrapper before resolving `danbooru.donmai.us` and `cdn.donmai.us`.
  - *Why*: Avoids circular dependencies (calling `get_http2_session()` inside `resolve_hostname_doh()`) and prevents ISP DNS poisoning of `cloudflare-dns.com` itself.
- **Decision 3: Comprehensive Codebase Audit & Bug Fixes**
  - *Audit Finding 1 (`--noconsole` stdout crash)*: In PyInstaller `--noconsole` builds, `sys.stdout` and `sys.stderr` are `None`. Calling `print()` inside `log_event()` or `init_persistent_storage()` can raise an unhandled exception when the console buffer is absent. **Fix**: Guard all `print()` calls behind `if sys.stdout is not None:`.
  - *Audit Finding 2 (`SetWindowLongPtrW` 32-bit fallback typo)*: `SetWindowLongPtrW` previously fell back to `user32.GetWindowLongW` instead of `user32.SetWindowLongW`. **Fix**: Corrected to `getattr(user32, "SetWindowLongPtrW", user32.SetWindowLongW)`.
  - *Audit Finding 3 (Slideshow Orientation Starvation)*: If a user searches for a tag where an entire page of 100 posts contains zero images matching the monitor's orientation (e.g., portrait monitor with a tag containing mostly widescreen scenery), `index.html` could stall waiting for new items. **Fix**: When `slideshow` mode filters out an entire batch from `/api`, `index.html` automatically requests the next batch after a brief 400ms cooldown until matching orientation media is found.
  - *Audit Finding 4 (Relative Origin Fetch in `index.html`)*: Replaced hardcoded `http://127.0.0.1:8088` fetch prefixes in `index.html` with `window.location.origin` (with fallback to `http://127.0.0.1:8088`) so all `/api`, `/media`, `/properties`, and `/epoch` calls remain resilient even if the port is ever customized.

---

## 4. Technical Architecture & Data Strategy *(Technical Reference)*

### Architecture & Component Diagram

```
┌────────────────────────────────────────────────────────────────────────────┐
│                   Floating Tkinter UI & System Tray                        │
│  ┌──────────────────────┐  ┌──────────────────────┐  ┌──────────────────┐  │
│  │  Credentials Tab     │  │  Display Tab         │  │  Logs Tab        │  │
│  │  • DPAPI API Key     │  │  • Screen Selector   │  │  • Master Pause  │  │
│  │  • Lock Search Bar   │  │  • Dynamic Sections: │  │  • Log Glossary  │  │
│  │  • Light/Dark Toggle │  │    Scroll / Collage  │  │  • Smart Scroll  │  │
│  └──────────┬───────────┘  │    / Slideshow       │  └────────┬─────────┘  │
└─────────────┼──────────────┴──────────┬───────────┘           │            ┘
              │                         │                       │
              ▼                         ▼                       ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                Local Python Proxy Server (127.0.0.1:8088)                  │
│  • GET /api        -> Returns shuffled post batch (unique per screen)      │
│  • GET /media      -> Streams binary chunks & HTTP Range for MP4 (<=15MB)  │
│  • GET /properties -> Returns per-screen settings & pause states           │
│  • GET /epoch      -> Heartbeat & cache invalidation synchronization       │
└───────────────────────────────────────┬────────────────────────────────────┘
                                        │
                                        ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                    Hybrid DoH + SNI Transport Layer                        │
│  ┌────────────────────────────────────┐ ┌────────────────────────────────┐ │
│  │ 1. Cloudflare DoH Resolver         │ │ 2A. Primary: curl_cffi Session │ │
│  │    https://1.1.1.1/dns-query       │ │     Chrome HTTP/2 + RESOLVE IP │ │
│  │    Caches A-records (15m TTL)      │ ├────────────────────────────────┤ │
│  └────────────────────────────────────┘ │ 2B. Fallback: Stdlib DoH+SNI   │ │
│                                         │     TLS 1.3 Socket -> DoH IP   │ │
│                                         │     with server_hostname SNI   │ │
│                                         └────────────────────────────────┘ │
└───────────────────────────────────────┬────────────────────────────────────┘
                                        │
                                        ▼
┌────────────────────────────────────────────────────────────────────────────┐
│            Ephemeral Multi-Monitor WebView2 Renderers (index.html)         │
│  • Mode 1: Continuous Scroll (Left, Right, Up, Down)                       │
│  • Mode 2: Polaroid Collage (2D Coverage Grid + Canvas Baking + Fill)      │
│  • Mode 3: Fullscreen Slideshow (Orientation Filter + 0-1s Cross-Fade)     │
└────────────────────────────────────────────────────────────────────────────┘
```

### Interactive Component & State Mapping
- **Hybrid Transport Initialization (`rebuild_http2_session`)**: Checks `CURL_CFFI_AVAILABLE`. If `True`, initializes `curl_requests.Session(impersonate="chrome")`; if `False`, initializes `StdlibDoHSession` using `DoHSNIHTTPSHandler` with TLS 1.3, HTTP Basic Auth headers, and chunked `iter_content()` streaming so `/media` and `/api` work identically.
- **Display Mode Section Switching (`_update_mode_sections_visibility`)**: Selecting `scroll`, `collage`, or `slideshow` in the Display tab hides the other two frames via `pack_forget()` and reveals only the relevant controls.
- **Slideshow Orientation & Fade Engine (`updateSlideshowMode`)**: Compares `window.innerWidth >= window.innerHeight` against each post's aspect ratio (`image_width / image_height`), cross-fades incoming and outgoing `.slideshow-item` elements over `SLIDESHOW_FADE / 10.0` seconds, and holds each slide for `SLIDESHOW_DURATION` seconds.
