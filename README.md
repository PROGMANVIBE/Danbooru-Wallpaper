# Danbooru Wallpaper Application

A standalone Windows desktop wallpaper application that streams Danbooru artwork, animated GIFs, and silent MP4 videos directly behind your desktop icons. Designed for both single and multi-monitor setups, it provides four customizable display modes, independent per-screen tag searches and playback controls, color-coded tag suggestions and saved searches, Light and Dark interface themes, real-time performance and activity monitoring, and instant access from the Windows system tray.

---

## Features

- **Four Customizable Display Modes**:
  - **Scrolling Slideshow**: Continuously scrolls media across your desktop in four selectable directions (Left, Right, Up, or Down) with adjustable scroll speed and spacing.
  - **Polaroid**: Drops framed artwork onto the screen in a continuous stacking animation with adjustable drop speed, size range, spawn delay, and a **Fill Screen** burst option.
  - **Fullscreen Slideshow**: Displays one artwork or video at a time across the entire screen, automatically matching your monitor's orientation (landscape or portrait) with configurable display duration and fade transitions.
  - **Masonry**: Arranges media into a dynamic full-screen grid with two layout styles (**Mondrian** and **Rows**), adjustable tile count, gap spacing, and smooth animated tile transitions.
- **Multi-Monitor Support**: Automatically detects all connected displays so you can independently enable or disable the wallpaper, choose different display modes, and run distinct tag searches on each monitor.
- **Per-Screen Search & Playback Controls**: Manage each display directly from the **Display** tab using dedicated **Refresh**, **Previous**, **Next**, and **Pause** buttons alongside an expandable tag search bar and live auto-suggestions.
- **Saved Searches**: Bookmark your favorite tag combinations via **Saved Searches ▾**, view long tag lists with automatic horizontal scrolling, and remove saved entries at any time.
- **Color-Coded Tag Categories**: Automatically highlights tags by their official Danbooru category (Blue for General, Red for Artist, Purple for Copyright, Green for Character, and Orange for Meta) across the search bar, suggestions, saved searches, and media tag viewer.
- **Displayed Media Tags Viewer**: Displays all tags belonging to the most recently shown media on the selected screen; click any tag to immediately add it to your search.
- **Light & Dark Mode Themes**: Switch the application interface between Light Mode and Dark Mode from the **Credentials** tab.
- **Instant System Tray Access**: Left-click the system tray icon to immediately open the Application Settings window, or right-click to access settings or exit the application.
- **Individual & Master Pause Controls**: Pause motion on a single monitor from the **Display** tab while keeping animated media playing, or freeze the entire application from the **Logs** tab.
- **Resource Monitor & Activity Logs**: Track live CPU, Memory, and GPU usage with the built-in **Resource Graph** pop-out, and review application events in the **Logs** tab (see [GLOSSARY.md](GLOSSARY.md) for a complete reference of log messages).
- **Private & Secure Operation**: Streams media without leaving temporary browser caches on your drive and stores your account credentials encrypted locally on your Windows PC.

---

## How to Use

1. **Open Application Settings**: Left-click the cardboard box icon in the Windows system tray to open the Settings window (or right-click the tray icon for **Settings** and **Exit**).
2. **Configure a Monitor (Display Tab)**:
   - Choose a monitor from the **Select Screen** dropdown and check or uncheck **Display wallpaper on this screen**.
   - Enter Danbooru tags in the **`TAGS =`** search box. Tag suggestions appear automatically below the input box as you type.
   - Click outside the search box or press **Enter** to apply your search, or click **Refresh (`⟳`)** / press **Shift + Enter** for an immediate refresh.
   - Use **Previous (`◀`)**, **Next (`▶`)**, and **Pause (`PAUSE`)** above the search box to control playback on the selected screen.
3. **Use Saved Searches & Displayed Media Tags**:
   - Click **Saved Searches ▾** above the search box and select **Save Search Tags** to bookmark the current query, click a saved row to load it, or click the trash-can (`🗑`) icon to delete it.
   - Click any tag in the **Displayed Media Tags** box below the search bar to append it to your current search.
4. **Choose a Display Mode**: Select `scroll`, `polaroid`, `slideshow`, or `masonry` in the **Display** tab and adjust the mode-specific sliders in real time.
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
  --add-data "index.html;." `
  --add-data "project.json;." `
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
