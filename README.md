# Danbooru Wallpaper Application

A standalone Windows desktop wallpaper application that streams Danbooru artwork, animated GIFs, and silent MP4 videos directly behind your desktop icons. Designed for both single and multi-monitor setups, it provides four customizable display modes, independent per-screen tag searches and playback controls, color-coded tag suggestions and saved searches, Light and Dark interface themes, real-time performance and activity monitoring, and instant access from the Windows system tray.

---

## Features

- **Four Customizable Display Modes**:
  - **Scrolling Slideshow**: Continuously scrolls media across your desktop in four selectable directions (Left, Right, Up, or Down) with adjustable scroll speed and spacing.
  - **Polaroid**: Drops framed artwork onto the screen in a fluid, compositor-accelerated stacking animation and immediately bakes landed static Polaroids onto a fullscreen backing canvas (`#polaroidBaseCanvas`) to conserve DOM, GPU, and RAM resources—featuring a bottom-left **`By: <artist>`** red artist tag caption on each Polaroid frame, adjustable drop speed, size range, spawn delay, and a **Fill Screen** burst option.
  - **Fullscreen Slideshow**: Displays one artwork or video at a time across the entire screen, automatically matching your monitor's orientation (landscape or portrait) with configurable display duration and fade transitions.
  - **Masonry**: Arranges uncropped media into a dynamic full-screen grid with a stutter-free **Cardboard Box Loading Screen** (displaying a closed brown cardboard box while tiles preload in the background, opening the top flaps when ready, and fading smoothly from black into the complete grid), two layout styles (**Mondrian** and variable-height zero-gap **Rows**) powered by an LRU-memoized, branch-and-bound pruned, and bijection-verified tree solver (supporting exact balanced bitmask optimization across up to 10 Mondrian groups / 36 tiles), a flexible **Target Tile Count (`4 – 36`, `±25%` adaptive window)**, a combined single-row **`Masonry Layout: Mondrian` / `Masonry Layout: Rows`** and **`Edge Fill: Blur` / `Edge Fill: Black`** button pair, adjustable gap spacing, and GPU-optimized WAAPI + 2D horizontal card turns.
- **Multi-Monitor Support, Automatic HDMI Hotplug Watchdog, Fullscreen App Auto-Pause & Per-Screen V-Sync / Target FPS**: Automatically detects all connected displays—including HDMI TVs or monitors turned on or off while the app is running—so you can independently enable or disable the wallpaper using the **Display wallpaper on this screen** on/off slide switch, click **Resync Displays** next to the **Select Screen** dropdown (or in the System Tray menu) for instant on-demand display and desktop Z-order recovery, toggle **Pause during full screen application** on the right side of the same row to automatically pause wallpaper rendering and background processes whenever a fullscreen game or video application is running on that monitor, toggle **V-Sync (`V-Sync On` / `V-Sync Off`)** or set a custom **Target FPS (`15 – 240`)** when V-Sync is Off, choose different display modes, and run distinct tag searches on each monitor. Reopening the Settings window during an active session remembers your last open tab and selected monitor, while the background desktop watchdog protects desktop icon sizes during high-DPI TV transitions and coexists cleanly with companion desktop overlay tools such as **Glass-Pane**.
- **Per-Screen Search & Playback Controls**: Manage each display directly from the **Display** tab using dedicated **Refresh**, **Previous**, **Next**, and **Pause** buttons alongside an expandable tag search bar and live auto-suggestions.
- **Saved Searches**: Bookmark your favorite tag combinations via **Saved Searches ▾**, view long tag lists with automatic horizontal scrolling, and remove saved entries at any time.
- **Color-Coded Tag Categories**: Automatically highlights tags by their official Danbooru category (Blue for General, Red for Artist, Purple for Copyright, Green for Character, and Orange for Meta) across the search bar, suggestions, saved searches, and media tag viewer.
- **Displayed Media Tags Viewer & Direct Post Link**: Displays all tags belonging to the most recently shown media on the selected screen (`DISPLAYED MEDIA TAGS (CLICK TO ADD):`); click any tag to immediately add it to your search, or click the **`Post #<id>`** hyperlink in the upper-right corner to open the post directly in your default web browser.
- **Light & Dark Mode Themes**: Switch the application interface between Light Mode and Dark Mode from the **Credentials** tab.
- **Instant System Tray Access**: Left-click the system tray icon to immediately open the Application Settings window, or right-click to access **Settings**, **Resync Displays**, or **Exit**.
- **Individual, Fullscreen & Master Pause Controls**: Pressing **Pause** on a display (or when a fullscreen game/video triggers **Pause during full screen application**) stops unneeded background processes—halting background tag pool fetches, aborting in-flight media preloads and canvas decodes, and pausing video decoders and animations—or freeze the entire application from the **Logs** tab.
- **Resource Monitor & Activity Logs**: Track live application-only CPU, Memory, and GPU usage with the built-in **Resource Graph** pop-out (`📊 PERFORMANCE — RESOURCE GRAPH`), and review application events in the **Logs** tab (see [GLOSSARY.md](GLOSSARY.md) for a complete reference of log messages).
- **Private & Secure Operation**: Streams media without leaving temporary browser caches on your drive and stores your account credentials encrypted locally on your Windows PC.

---

## How to Use

1. **Open Application Settings**: Left-click the cardboard box icon in the Windows system tray to open the Settings window (or right-click the tray icon for **Settings**, **Resync Displays**, and **Exit**). While the application is running, reopening Settings automatically restores your last active tab and selected screen.
2. **Configure a Monitor (Display Tab)**:
   - Choose a monitor from the **Select Screen** dropdown (or click **Resync Displays** next to the dropdown after turning on/off an HDMI TV or monitor), toggle the **Display wallpaper on this screen** on/off slide switch on the left, and toggle **Pause during full screen application** on the right side of the same row to automatically pause the screen when a game or fullscreen video runs on that display.
   - Directly below the slide switch row, click **`V-Sync On`** / **`V-Sync Off`** to toggle hardware V-Sync for the selected screen. When **`V-Sync Off`** is active, enter your desired frame rate in the **`Target FPS (15 – 240):`** input box to the right of the button.
   - Enter Danbooru tags in the **`TAGS =`** search box. Tag suggestions appear automatically below the input box as you type.
   - Click outside the search box or press **Enter** to apply your search, or click **Refresh (`⟳`)** / press **Shift + Enter** for an immediate refresh.
   - Use **Previous (`◀`)**, **Next (`▶`)**, and **Pause (`PAUSE`)** above the search box to control playback on the selected screen.
3. **Use Saved Searches & Displayed Media Tags**:
   - Click **Saved Searches ▾** above the search box and select **Save Search Tags** to bookmark the current query, click a saved row to load it, or click the trash-can (`🗑`) icon to delete it.
   - Click any tag in the **Displayed Media Tags** box below the search bar to append it to your current search, or click **`Post #<id>`** in the top-right corner of the header to open that Danbooru post in your default browser.
4. **Choose a Display Mode**: Select `scroll`, `polaroid`, `slideshow`, or `masonry` in the **Display** tab and adjust the mode-specific sliders in real time. In **Masonry** mode, use the side-by-side **`Masonry Layout: Mondrian` / `Masonry Layout: Rows`** and **`Edge Fill: Blur` / `Edge Fill: Black`** buttons on the same row, and adjust **Target Tile Count (`4 – 36`)** (`±25%` adaptive range).
5. **Manage Credentials, Theme & Logs**:
   - **Credentials Tab**: Enter your Danbooru **Username**, **User ID**, and **API Key**, and toggle between **Light Mode** and **Dark Mode**.
   - **Top Header `📊 Resource Graph`**: Open the live CPU, Memory, and GPU performance monitor.
   - **Logs Tab**: Pause or resume the entire application, clear logs, or open the built-in log glossary (also available in [GLOSSARY.md](GLOSSARY.md)).

---

## Requirements

### Runtime Requirements
- **Operating System**: Windows 10 or Windows 11 (64-bit)
- **WebView2 Runtime**: Microsoft Edge WebView2 Evergreen Runtime (pre-installed on Windows 11 and modern Windows 10 systems)
- **Internet Connection**: Active broadband connection

### Build / Source Requirements
- **Python**: 3.10 or higher
- **Packages**: `pywebview`, `pystray`, `Pillow`, `curl_cffi`, `pyinstaller`

---

## Installation & Building the Executable

### 1. Install Dependencies
```powershell
pip install pyinstaller pywebview pystray pillow curl_cffi
```

### 2. Compile the Standalone Executable (`.exe`)
Run the following command in PowerShell from the project directory:

```powershell
python -m PyInstaller --noconfirm --onefile --noconsole `
  --name "DanbooruWallpaper" `
  --icon "icon.ico" `
  --add-data "index.html;." `
  --add-data "project.json;." `
  --add-data "icon.ico;." `
  --hidden-import "webview" `
  --hidden-import "pystray" `
  --hidden-import "PIL" `
  --hidden-import "curl_cffi" `
  --collect-all "curl_cffi" `
  danbooru_service.py
```

Launch the compiled executable from `dist\DanbooruWallpaper.exe`.

---

## Finding Your Danbooru Credentials

While the application works anonymously (limited by Danbooru to 2 search tags at a time), adding your account credentials unlocks higher rate limits and multi-tag searches for Gold/Platinum accounts:

1. Log in to [https://danbooru.donmai.us/](https://danbooru.donmai.us/) and open **My Account**.
2. Copy your **Username** and numeric **User ID** from your profile page.
3. Scroll to **API Key** at the bottom of your profile settings, click **View** (or generate a new key), and copy the key.
4. Paste your **Username**, **User ID**, and **API Key** into the **Credentials** tab in Application Settings and click **Save Credentials**.

> **Security Notice**: Treat your API key like your password and never share it publicly. Your API key is encrypted locally using the Windows Data Protection API (DPAPI) in `%APPDATA%\DanbooruWallpaper`. For more details on Danbooru's API policies, visit [https://danbooru.donmai.us/wiki_pages/help:api](https://danbooru.donmai.us/wiki_pages/help:api).
