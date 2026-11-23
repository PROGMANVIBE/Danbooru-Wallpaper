# Application Logs Glossary

This glossary explains every log prefix and message that can appear in the **Logs** tab of the Application Settings window (also accessible in-app by clicking the **Glossary** button on the **Logs** tab).

---

## Normal Operation Logs (Routine)

**`[SERVER] Service running on http://127.0.0.1:8088 (<transport_mode>)`**
- **What it means**: The local Python HTTP server and `/media` streaming proxy started on `127.0.0.1:8088`, indicating whether `curl_cffi HTTP/2 + DoH` or the `stdlib TLS 1.3 + DoH SNI fallback` transport is active.
- **When it happens**: Once, immediately when you launch the application.

**`[DOH] Resolved <hostname> -> <ip_address> via Cloudflare DoH`**
- **What it means**: Python queried Cloudflare's DNS-over-HTTPS service (`1.1.1.1`) to resolve `danbooru.donmai.us` or `cdn.donmai.us` and cached the IP for 15 minutes.
- **When it happens**: On startup and once every 15 minutes when the DoH DNS cache refreshes.

**`[AUTH] Active transport engine: <transport_mode>`**
- **What it means**: Reports whether the application is using `curl_cffi HTTP/2` or the built-in `stdlib TLS 1.3 + DoH SNI fallback`.
- **When it happens**: On startup when initializing the HTTP session.

**`[AUTH] Loaded DPAPI-protected credentials for user '<username>' (#<id>)`**
- **What it means**: The program decrypted your saved Danbooru credentials from `config.json` in `%APPDATA%\DanbooruWallpaper` and applied them to the session.
- **When it happens**: Once at startup if credentials were previously saved (otherwise logs that it is running in anonymous 2-tag mode and opens Settings).

**`[AUTH] Credentials updated from Settings for user '<username>'.`**
- **What it means**: You clicked **Save Credentials** on the Credentials tab. Your DPAPI-encrypted API key and username are now active.
- **When it happens**: Whenever you save changes on the Credentials tab.

**`[WIN32] Win11 24H2+ mode / Classic WorkerW mode: Attached '<window_title>' HWND ...`**
- **What it means**: The native Windows desktop attachment engine positioned the WebView2 wallpaper window behind your desktop icons for a connected monitor.
- **When it happens**: Once per monitor during startup.

**`[WEBVIEW] Applied display properties to <screen_id> (enabled=<True/False>).`**
- **What it means**: Synchronized the selected Display Mode (`scroll`, `polaroid`, `slideshow`, or `masonry`), sliders, and screen enable state to the target monitor's WebView2 instance.
- **When it happens**: At startup and whenever you adjust controls on the **Display** tab.

**`[API] Requesting Page <page_number> for tags: '<search_tags>' via <transport_mode>`**
- **What it means**: Python is querying `https://danbooru.donmai.us/posts.json` for a page of up to 100 posts matching your tags.
- **When it happens**: On startup, after a search refresh, or when the in-memory post buffer runs low.

**`[FETCH] Fetched and shuffled <N> media items (Page <P>) for '<search_tags>' (filtered <M> oversized MP4s).`**
- **What it means**: Python received the posts from Danbooru, filtered out unsupported/unsafe paths or MP4 videos larger than `15 MB`, rewrote all media URLs to point to `http://127.0.0.1:8088/media`, and shuffled the batch randomly.
- **When it happens**: Immediately after an `[API]` page request completes.

**`[SERVER] Client '<screen_id>' requested batch from /api`**
- **What it means**: A monitor's WebView2 wallpaper client requested the next batch of shuffled posts from Python's RAM buffer.
- **When it happens**: Periodically as your wallpaper scrolls, drops Polaroids, advances slides, or flips Masonry tiles.

**`[PING] Client polled /epoch (<count> times in last <seconds>s)`**
- **What it means**: Heartbeat summary confirming that active WebView2 wallpaper windows are polling `/epoch` every second for refresh, pause, and navigation updates (aggregated once every 60 seconds to keep logs clean).
- **When it happens**: Once every 60 seconds while the application is unpaused.

---

## User Interaction Logs (Informational)

**`[SEARCH] Queued tags: '<search_tags>'`**
- **What it means**: You updated the tags in the `TAGS =` search bar on the Display tab. The query is queued and applied to the selected screen's tag pool.
- **When it happens**: When pressing **Enter** or clicking outside the `TAGS =` search bar after editing tags.

**`[REFRESH] Immediate refresh triggered. Epoch: <E> | Tags: '<search_tags>'`**
- **What it means**: You clicked `⟳` or pressed **Shift + Enter**. The in-memory buffer was cleared, the epoch incremented, and a new API fetch started immediately for the selected screen.
- **When it happens**: When forcing an immediate refresh.

**`[NAV] Previous button clicked: requeued last shown file to the front of the queue.` / `Next button clicked: immediately playing next queued file.`**
- **What it means**: You clicked the **Previous (`◀`)** or **Next (`▶`)** button above the `TAGS =` search bar on the Display tab.
- **When it happens**: When clicking `◀` or `▶` on the Display tab.

**`[SEARCH] Saved query to bookmarks: '<search_tags>'` / `Removed query from bookmarks: '<search_tags>'`**
- **What it means**: You saved a tag search via **Save Search Tags** or deleted a saved search using the trash-can (`🗑`) button in the **Saved Searches ▾** dropdown.
- **When it happens**: When managing saved searches on the Display tab.

**`[UI] Switched application theme to LIGHT / DARK mode.`**
- **What it means**: You clicked the **Dark Mode** / **Light Mode** toggle button on the Credentials tab, re-theming the Settings window, Resource Graph pop-out, and Glossary dialog.
- **When it happens**: When toggling the application theme.

**`[UI] Wallpaper motion paused (GIFs and MP4 videos remain playing).` / `Wallpaper motion resumed.`**
- **What it means**: You clicked the per-screen **PAUSE** button on the Display tab to pause or resume scrolling, Polaroid drops, slideshow transitions, or Masonry flips on the selected monitor.
- **When it happens**: When toggling the Display tab `PAUSE` button.

**`[POLAROID] Triggered Fill Screen burst on <screen_id>.`**
- **What it means**: You clicked the **Fill Screen** button in Polaroid mode on the Display tab, spawning a rapid burst of Polaroids to cover the monitor and starting the 30-second button cooldown.
- **When it happens**: When clicking **Fill Screen** on the Display tab.

**`[APP] Application PAUSED (display frozen, proxy streams & API calls stopped).` / `Application RESUMED.`**
- **What it means**: You toggled the master **PAUSE APPLICATION** button on the Logs tab.
- **When it happens**: When pausing or resuming the entire application from the Logs tab.

**`[APP] Duplicate launch detected — bringing Settings window to foreground.`**
- **What it means**: You launched `DanbooruWallpaper.exe` while the application was already running. The duplicate launch signaled the running instance to open and focus the **Application Settings** window and exited cleanly without creating a second tray icon.
- **When it happens**: Whenever `DanbooruWallpaper.exe` is double-clicked or launched while an instance is already active.

**`[APP] Shutting down application...`**
- **What it means**: You clicked **Exit** in the system tray menu. All threads, sockets, and WebView2 windows are closing cleanly.
- **When it happens**: When exiting the program.

---

## Error, Security & Warning Logs

**`[API] HTTP 422 (2-tag limit on current account tier). Retrying with '<first_two_tags>'`**
- **What it means**: Anonymous and Member-tier Danbooru accounts are limited to searching 2 tags at a time. Python automatically trimmed your query to the first 2 tags and retried so your wallpaper continues streaming.
- **Action needed**: Use up to 2 tags, or enter credentials for a Gold/Platinum account on the Credentials tab.

**`[ERROR] No posts found for '<search_tags>'. Backing off <N>s...`**
- **What it means**: The tag combination returned 0 results on Danbooru (often due to a typo or incompatible tags).
- **Action needed**: Check tag spelling in the search bar or use autocomplete suggestions.

**`[ERROR] Fetch error: HTTP 401 Unauthorized: Check Username and API Key in Credentials tab. Backing off <N>s...`**
- **What it means**: Danbooru rejected the Username or API Key entered in Settings.
- **Action needed**: Open **Settings → Credentials** and verify your Danbooru Username and API Key.

**`[ERROR] Fetch error: HTTP 429 Too Many Requests: Rate limit reached, backing off. Backing off <N>s...`**
- **What it means**: Danbooru rate-limited the connection temporarily.
- **Action needed**: None. Exponential backoff will automatically wait and retry.

**`[FETCH] Multiple pages returned 0 usable items for '<tags>'. Cooling down 10s.`**
- **What it means**: Danbooru returned posts, but all of them were either already seen recently, unsupported file types, or MP4s larger than `15 MB`.
- **Action needed**: None, or try broader search tags if the query only contains long/large videos.

**`[PROXY] Filtered oversized MP4 (<bytes> bytes > 15 MB): <url>` / `Filtered oversized image (<bytes> bytes > 25 MB)`**
- **What it means**: The `/media` proxy blocked an MP4 video that exceeded the `15 MB` cap or an image that exceeded the `25 MB` cap to protect memory and bandwidth.
- **Action needed**: None.

**`[PROXY] Upstream media HTTP <status_code> for <url>` / `Proxy stream error for <url>: <error>`**
- **What it means**: An individual CDN media download timed out or dropped mid-stream.
- **Action needed**: None. The WebView preloader automatically discards the failed item and loads the next one.

**`[SECURITY] Blocked unsafe media URL (<reason>): <url>` / `Blocked media stream failing binary signature check (<reason>): <url>`**
- **What it means**: The security layer blocked a URL containing forbidden tokens (such as `.php`, double extensions, or unauthorized hosts) or aborted a download whose initial binary magic bytes did not match a valid JPEG, PNG, GIF, WEBP, or MP4 header.
- **Action needed**: None. Potential malware or non-media payload was neutralized before reaching WebView2.

**`[SUGGEST] Suggestion fetch failed: <error details>`**
- **What it means**: A live tag autocomplete request timed out.
- **Action needed**: None.

**`[CONFIG] Failed to load/save app config / project.json: <error details>`**
- **What it means**: Python encountered a filesystem error reading or writing in `%APPDATA%\DanbooruWallpaper`.
- **Action needed**: Verify your Windows user account has normal write permissions to `%APPDATA%`.
