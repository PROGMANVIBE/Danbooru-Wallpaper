# Danbooru Wallpaper Application

A standalone Windows desktop wallpaper application that streams Danbooru artwork, animated GIFs, and silent MP4 videos directly behind your desktop icons. Designed for both single and multi-monitor setups, it provides four customizable display modes, independent per-screen tag searches and playback controls, color-coded tag suggestions and saved searches, Light and Dark interface themes, real-time performance and activity monitoring, and instant access from the Windows system tray.

---

## Features

- **Four Customizable Display Modes**:
  - **Scrolling Slideshow**: Continuously scrolls media across your desktop in four directions (Left, Right, Up, or Down) with adjustable speed and spacing.
  - **Polaroid**: Drops framed artwork with a bottom-left **`By: <artist>`** caption in a smooth stacking animation, automatically baking landed static cards onto a backing canvas to conserve DOM, GPU, and RAM resources.
  - **Fullscreen Slideshow**: Displays one artwork or video at a time matched to your monitor's orientation (landscape or portrait) with configurable duration and fade transitions.
  - **Masonry**: Arranges uncropped media into a dynamic full-screen grid (**Mondrian** or zero-gap **Rows**) with a smooth **Cardboard Box Loading Screen**, adaptive tile counts (`4 – 36`), **Blur** or **Black** edge fills, and GPU-optimized 2D card turns.
- **Multi-Monitor & Display Management**: Independently configure each connected display with its own display mode, tag search, hardware **V-Sync** or custom **Target FPS (`15 – 240`)**, and automatic **HDMI hotplug recovery** that preserves desktop icon scaling and coexists cleanly with desktop overlay tools like **Glass-Pane**.
- **Color-Coded Tag Search, Saved Searches & Post Discovery**: Features live auto-suggestions, bookmarked tag combinations, and an interactive **Displayed Media Tags** viewer—all color-coded by official Danbooru tag categories (General, Artist, Copyright, Character, and Meta) with a direct **`Post #<id>`** link to open the source post in your browser.
- **Smart Pause & Resource Conservation**: Pause individual screens, freeze the entire application, or enable automatic pause when a fullscreen game or video runs on a monitor—immediately halting background fetches, media preloads, video decoders, and animations.
- **Live Telemetry & Activity Logs**: Includes a real-time **Resource Graph** for tracking application-only CPU, Memory, and GPU usage alongside a categorized event log with a built-in glossary (see [GLOSSARY.md](GLOSSARY.md)).
- **System Tray Integration, Themes & Security**: Runs quietly in the Windows system tray with single-instance protection, Light and Dark interface themes, ephemeral cache-free media streaming, and local Windows DPAPI encryption for your Danbooru credentials.

---

## How to Use

1. **Open Application Settings**: Left-click the cardboard box icon in the Windows system tray (or double-click `DanbooruWallpaper.exe` while it is already running) to open and focus the Settings window, or right-click the tray icon for **Settings**, **Resync Displays**, and **Exit**. While the application is running, reopening Settings automatically restores your last active tab and selected screen.
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
