import os
import sys

# Configure WebView2 Chromium flags BEFORE importing webview:
# - Ephemeral in-memory operation: zero persistent "webview_profile" disk cache or telemetry folders
# - Prevents GPU occlusion/background throttling when reparented behind SHELLDLL_DefView
# - Strictly mutes all audio (--mute-audio)
os.environ.setdefault(
    "WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS",
    "--disable-features=CalculateNativeWinOcclusion,WinUseBrowserSpellChecker,msSmartScreenProtection "
    "--disable-background-timer-throttling "
    "--disable-renderer-backgrounding "
    "--disable-backgrounding-occluded-windows "
    "--autoplay-policy=no-user-gesture-required "
    "--disable-pinch "
    "--mute-audio "
    "--inprivate "
    "--incognito "
    "--disk-cache-size=1 "
    "--media-cache-size=1 "
    "--disable-gpu-shader-disk-cache "
    "--disable-application-cache "
    "--disable-offline-load-stale-cache "
    "--disable-component-update "
    "--disable-domain-reliability "
    "--disable-breakpad "
    "--disable-crash-reporter "
    "--disable-sync "
    "--disable-translate "
    "--disable-extensions "
    "--disable-file-system "
    "--disable-background-networking",
)

import re
import urllib.request
import urllib.parse
import urllib.error
import http.client
import ssl
import gzip
import zlib
import json
import threading
import random
import shutil
import time
import base64
import socket
import ipaddress
import webbrowser
import ctypes
from ctypes import wintypes

# =============================================================================
# 0. PRE-IMPORT WIN32 NAMED MUTEX SINGLE-INSTANCE LOCK & UX HANDOFF (PYINSTALLER)
# =============================================================================
# Acquired BEFORE heavy third-party imports (webview, curl_cffi, pystray, PIL, tkinter)
# so rapid double-clicks on the compiled PyInstaller --onefile .exe never race during
# the ~400-900ms module import window.
#
# Why Win32 Named Mutex instead of process-name counting:
# - In PyInstaller --onefile mode, the outer C bootloader .exe and the unpacked Python
#   child .exe share the exact same image name (DanbooruWallpaper.exe). Because the C
#   bootloader never runs Python code, only the active Python runtime calls CreateMutexW,
#   eliminating false-positive parent/child collisions.
# - Global references (_SINGLE_INSTANCE_MUTEX_HANDLE, _SINGLE_INSTANCE_EVENT_HANDLE)
#   are retained at module scope for the entire process lifetime so Python's garbage
#   collector never closes the kernel handles prematurely.
_SINGLE_INSTANCE_MUTEX_NAME = "Local\\DanbooruWallpaper_SingleInstance_Mutex_v1"
_SINGLE_INSTANCE_EVENT_NAME = "Local\\DanbooruWallpaper_ShowSettings_Event_v1"
_SINGLE_INSTANCE_PORT = 8088
_SINGLE_INSTANCE_MUTEX_HANDLE = None
_SINGLE_INSTANCE_EVENT_HANDLE = None

ERROR_ALREADY_EXISTS = 183
ERROR_ACCESS_DENIED = 5
EVENT_MODIFY_STATE = 0x0002
WAIT_OBJECT_0 = 0x00000000

if os.name == "nt":
    _KERNEL32_SINGLE_INST = ctypes.WinDLL("kernel32", use_last_error=True)

    _KERNEL32_SINGLE_INST.CreateMutexW.argtypes = [
        wintypes.LPVOID,
        wintypes.BOOL,
        wintypes.LPCWSTR,
    ]
    _KERNEL32_SINGLE_INST.CreateMutexW.restype = wintypes.HANDLE

    _KERNEL32_SINGLE_INST.CreateEventW.argtypes = [
        wintypes.LPVOID,
        wintypes.BOOL,
        wintypes.BOOL,
        wintypes.LPCWSTR,
    ]
    _KERNEL32_SINGLE_INST.CreateEventW.restype = wintypes.HANDLE

    _KERNEL32_SINGLE_INST.OpenEventW.argtypes = [
        wintypes.DWORD,
        wintypes.BOOL,
        wintypes.LPCWSTR,
    ]
    _KERNEL32_SINGLE_INST.OpenEventW.restype = wintypes.HANDLE

    _KERNEL32_SINGLE_INST.SetEvent.argtypes = [wintypes.HANDLE]
    _KERNEL32_SINGLE_INST.SetEvent.restype = wintypes.BOOL

    _KERNEL32_SINGLE_INST.WaitForSingleObject.argtypes = [
        wintypes.HANDLE,
        wintypes.DWORD,
    ]
    _KERNEL32_SINGLE_INST.WaitForSingleObject.restype = wintypes.DWORD

    _KERNEL32_SINGLE_INST.ReleaseMutex.argtypes = [wintypes.HANDLE]
    _KERNEL32_SINGLE_INST.ReleaseMutex.restype = wintypes.BOOL

    _KERNEL32_SINGLE_INST.CloseHandle.argtypes = [wintypes.HANDLE]
    _KERNEL32_SINGLE_INST.CloseHandle.restype = wintypes.BOOL
else:
    _KERNEL32_SINGLE_INST = None


def _signal_existing_instance_to_show_settings() -> None:
    """
    Signals the already-running primary instance to open and focus the Settings window:
    1. Kernel Named Event (CreateEventW / OpenEventW + SetEvent): works immediately even
       if the user rapidly double-clicked the .exe while the first instance is still
       importing webview/curl_cffi before port 8088 is bound.
    2. Fast loopback HTTP fallback (GET http://127.0.0.1:8088/show_settings).
    """
    if _KERNEL32_SINGLE_INST is not None:
        evt_handle = None
        try:
            evt_handle = _KERNEL32_SINGLE_INST.OpenEventW(
                EVENT_MODIFY_STATE, False, _SINGLE_INSTANCE_EVENT_NAME
            )
            if not evt_handle:
                evt_handle = _KERNEL32_SINGLE_INST.CreateEventW(
                    None, False, False, _SINGLE_INSTANCE_EVENT_NAME
                )
            if evt_handle:
                _KERNEL32_SINGLE_INST.SetEvent(evt_handle)
        except Exception:
            pass
        finally:
            if evt_handle:
                try:
                    _KERNEL32_SINGLE_INST.CloseHandle(evt_handle)
                except Exception:
                    pass

    try:
        req = urllib.request.Request(
            f"http://127.0.0.1:{_SINGLE_INSTANCE_PORT}/show_settings",
            headers={"Origin": f"http://127.0.0.1:{_SINGLE_INSTANCE_PORT}"},
            method="GET",
        )
        with urllib.request.urlopen(req, timeout=0.35) as resp:
            resp.read(64)
    except Exception:
        pass


def enforce_single_instance_or_exit() -> None:
    """
    Acquires the session-scoped Win32 Named Mutex before any third-party GUI or network
    libraries are imported. If another instance already holds the mutex, signals it to
    bring its Settings window to the foreground and terminates immediately via os._exit(0).
    """
    global _SINGLE_INSTANCE_MUTEX_HANDLE, _SINGLE_INSTANCE_EVENT_HANDLE
    if _KERNEL32_SINGLE_INST is None or _SINGLE_INSTANCE_MUTEX_HANDLE is not None:
        return

    ctypes.set_last_error(0)
    mutex_handle = _KERNEL32_SINGLE_INST.CreateMutexW(
        None, False, _SINGLE_INSTANCE_MUTEX_NAME
    )
    last_err = ctypes.get_last_error()

    if not mutex_handle or last_err in (ERROR_ALREADY_EXISTS, ERROR_ACCESS_DENIED):
        _signal_existing_instance_to_show_settings()
        if mutex_handle:
            try:
                _KERNEL32_SINGLE_INST.CloseHandle(mutex_handle)
            except Exception:
                pass
        os._exit(0)

    _SINGLE_INSTANCE_MUTEX_HANDLE = mutex_handle
    _SINGLE_INSTANCE_EVENT_HANDLE = _KERNEL32_SINGLE_INST.CreateEventW(
        None, False, False, _SINGLE_INSTANCE_EVENT_NAME
    )


if __name__ == "__main__":
    enforce_single_instance_or_exit()

from queue import Queue, Empty
from collections import deque, OrderedDict
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
import tkinter as tk
from tkinter import ttk

# Optional curl_cffi import with automatic stdlib DoH + TLS 1.3 SNI fallback
try:
    from curl_cffi import requests as curl_requests
    try:
        from curl_cffi.const import CurlOpt, CurlHttpVersion
    except ImportError:
        CurlOpt = None
        CurlHttpVersion = None
    CURL_CFFI_AVAILABLE = True
except ImportError:
    curl_requests = None
    CurlOpt = None
    CurlHttpVersion = None
    CURL_CFFI_AVAILABLE = False

import pystray
from PIL import Image, ImageDraw, ImageTk
import webview


def safe_console_print(msg: str):
    """Safely prints to stdout when a console is attached (prevents PyInstaller --noconsole crashes)."""
    if sys.stdout is not None:
        try:
            print(msg, flush=True)
        except Exception:
            pass


# =============================================================================
# 1. DPI AWARENESS, DPAPI ENCRYPTION & 64-BIT SAFE WIN32 CTYPES DEFINITIONS
# =============================================================================
def enable_dpi_awareness():
    try:
        ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
    except Exception:
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass


enable_dpi_awareness()

user32 = ctypes.windll.user32
crypt32 = ctypes.windll.crypt32
kernel32 = ctypes.windll.kernel32
LONG_PTR = ctypes.c_ssize_t


class DATA_BLOB(ctypes.Structure):
    _fields_ = [
        ("cbData", wintypes.DWORD),
        ("pbData", ctypes.POINTER(ctypes.c_char)),
    ]


crypt32.CryptProtectData.argtypes = [
    ctypes.POINTER(DATA_BLOB),
    wintypes.LPCWSTR,
    ctypes.POINTER(DATA_BLOB),
    ctypes.c_void_p,
    ctypes.c_void_p,
    wintypes.DWORD,
    ctypes.POINTER(DATA_BLOB),
]
crypt32.CryptProtectData.restype = wintypes.BOOL

crypt32.CryptUnprotectData.argtypes = [
    ctypes.POINTER(DATA_BLOB),
    ctypes.POINTER(wintypes.LPWSTR),
    ctypes.POINTER(DATA_BLOB),
    ctypes.c_void_p,
    ctypes.c_void_p,
    wintypes.DWORD,
    ctypes.POINTER(DATA_BLOB),
]
crypt32.CryptUnprotectData.restype = wintypes.BOOL

kernel32.LocalFree.argtypes = [wintypes.HLOCAL]
kernel32.LocalFree.restype = wintypes.HLOCAL

CRYPTPROTECT_UI_FORBIDDEN = 0x1


def dpapi_encrypt(plaintext: str) -> str:
    """Encrypts a plaintext string using Windows DPAPI tied to the current Windows user."""
    if not plaintext:
        return ""
    if plaintext.startswith("dpapi:"):
        return plaintext
    raw = plaintext.encode("utf-8")
    buf = ctypes.create_string_buffer(raw, len(raw))
    blob_in = DATA_BLOB(len(raw), buf)
    blob_out = DATA_BLOB()
    if crypt32.CryptProtectData(
        ctypes.byref(blob_in),
        "DanbooruWallpaperConfig",
        None,
        None,
        None,
        CRYPTPROTECT_UI_FORBIDDEN,
        ctypes.byref(blob_out),
    ):
        try:
            encrypted_bytes = ctypes.string_at(blob_out.pbData, blob_out.cbData)
            return "dpapi:" + base64.b64encode(encrypted_bytes).decode("ascii")
        finally:
            kernel32.LocalFree(ctypes.cast(blob_out.pbData, wintypes.HLOCAL))
    return ""


def dpapi_decrypt(ciphertext: str) -> str:
    """Decrypts a DPAPI-protected string, supporting transparent fallback for legacy plaintext."""
    if not ciphertext:
        return ""
    if not ciphertext.startswith("dpapi:"):
        return ciphertext
    try:
        raw = base64.b64decode(ciphertext[6:])
        buf = ctypes.create_string_buffer(raw, len(raw))
        blob_in = DATA_BLOB(len(raw), buf)
        blob_out = DATA_BLOB()
        if crypt32.CryptUnprotectData(
            ctypes.byref(blob_in),
            None,
            None,
            None,
            None,
            CRYPTPROTECT_UI_FORBIDDEN,
            ctypes.byref(blob_out),
        ):
            try:
                return ctypes.string_at(blob_out.pbData, blob_out.cbData).decode("utf-8")
            finally:
                kernel32.LocalFree(ctypes.cast(blob_out.pbData, wintypes.HLOCAL))
    except Exception:
        pass
    return ""


SMTO_NORMAL = 0x0000
GWL_STYLE = -16
GWL_EXSTYLE = -20

WS_CAPTION = 0x00C00000
WS_THICKFRAME = 0x00040000
WS_MINIMIZEBOX = 0x00020000
WS_MAXIMIZEBOX = 0x00010000
WS_SYSMENU = 0x00080000
WS_POPUP = 0x80000000
WS_CHILD = 0x40000000
WS_VISIBLE = 0x10000000
WS_DISABLED = 0x08000000
WS_CLIPSIBLINGS = 0x04000000
WS_CLIPCHILDREN = 0x02000000
WS_MAXIMIZE = 0x01000000

WS_EX_APPWINDOW = 0x00040000
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_LAYERED = 0x00080000
WS_EX_NOACTIVATE = 0x08000000
WS_EX_NOREDIRECTIONBITMAP = 0x00200000
WS_EX_TRANSPARENT = 0x00000020

DWMWA_CLOAKED = 14

LWA_ALPHA = 0x00000002

SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOZORDER = 0x0004
SWP_NOACTIVATE = 0x0010
SWP_FRAMECHANGED = 0x0020
SWP_SHOWWINDOW = 0x0040
SWP_HIDEWINDOW = 0x0080
SWP_ASYNCWINDOWPOS = 0x4000

HWND_TOP = 0
HWND_BOTTOM = 1

RDW_INVALIDATE = 0x0001
RDW_UPDATENOW = 0x0100
RDW_ALLCHILDREN = 0x0080
RDW_FRAME = 0x0400

WM_SIZE = 0x0005
SIZE_RESTORED = 0

SM_CXSCREEN = 0
SM_CYSCREEN = 1
SM_XVIRTUALSCREEN = 76
SM_YVIRTUALSCREEN = 77
SM_CXVIRTUALSCREEN = 78
SM_CYVIRTUALSCREEN = 79

LVM_FIRST = 0x1000
LVM_GETITEMSPACING = LVM_FIRST + 51
LVM_SETICONSPACING = LVM_FIRST + 53
LVM_SETVIEW = LVM_FIRST + 142
LVM_GETVIEW = LVM_FIRST + 143

WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
MONITORENUMPROC = ctypes.WINFUNCTYPE(
    wintypes.BOOL, wintypes.HMONITOR, wintypes.HDC, ctypes.POINTER(wintypes.RECT), wintypes.LPARAM
)


class MONITORINFOEXW(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("rcMonitor", wintypes.RECT),
        ("rcWork", wintypes.RECT),
        ("dwFlags", wintypes.DWORD),
        ("szDevice", wintypes.WCHAR * 32),
    ]


user32.FindWindowW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR]
user32.FindWindowW.restype = wintypes.HWND

user32.FindWindowExW.argtypes = [wintypes.HWND, wintypes.HWND, wintypes.LPCWSTR, wintypes.LPCWSTR]
user32.FindWindowExW.restype = wintypes.HWND

user32.EnumWindows.argtypes = [WNDENUMPROC, wintypes.LPARAM]
user32.EnumWindows.restype = wintypes.BOOL

user32.EnumChildWindows.argtypes = [wintypes.HWND, WNDENUMPROC, wintypes.LPARAM]
user32.EnumChildWindows.restype = wintypes.BOOL

user32.EnumDisplayMonitors.argtypes = [
    wintypes.HDC, ctypes.POINTER(wintypes.RECT), MONITORENUMPROC, wintypes.LPARAM
]
user32.EnumDisplayMonitors.restype = wintypes.BOOL

user32.GetMonitorInfoW.argtypes = [wintypes.HMONITOR, ctypes.POINTER(MONITORINFOEXW)]
user32.GetMonitorInfoW.restype = wintypes.BOOL

user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetClassNameW.restype = ctypes.c_int

user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetWindowTextW.restype = ctypes.c_int

user32.IsWindowVisible.argtypes = [wintypes.HWND]
user32.IsWindowVisible.restype = wintypes.BOOL

user32.IsWindow.argtypes = [wintypes.HWND]
user32.IsWindow.restype = wintypes.BOOL

user32.EnableWindow.argtypes = [wintypes.HWND, wintypes.BOOL]
user32.EnableWindow.restype = wintypes.BOOL

user32.ScreenToClient.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.POINT)]
user32.ScreenToClient.restype = wintypes.BOOL

user32.RedrawWindow.argtypes = [wintypes.HWND, ctypes.c_void_p, wintypes.HRGN, wintypes.UINT]
user32.RedrawWindow.restype = wintypes.BOOL

user32.SendMessageTimeoutW.argtypes = [
    wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM,
    wintypes.UINT, wintypes.UINT, ctypes.POINTER(ctypes.c_size_t)
]
user32.SendMessageTimeoutW.restype = wintypes.LPARAM

user32.SendMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.SendMessageW.restype = wintypes.LPARAM

user32.SetParent.argtypes = [wintypes.HWND, wintypes.HWND]
user32.SetParent.restype = wintypes.HWND

user32.GetParent.argtypes = [wintypes.HWND]
user32.GetParent.restype = wintypes.HWND

user32.SetWindowPos.argtypes = [
    wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int,
    ctypes.c_int, ctypes.c_int, wintypes.UINT
]
user32.SetWindowPos.restype = wintypes.BOOL

user32.SetLayeredWindowAttributes.argtypes = [
    wintypes.HWND, wintypes.COLORREF, wintypes.BYTE, wintypes.DWORD
]
user32.SetLayeredWindowAttributes.restype = wintypes.BOOL

user32.GetSystemMetrics.argtypes = [ctypes.c_int]
user32.GetSystemMetrics.restype = ctypes.c_int

user32.GetForegroundWindow.argtypes = []
user32.GetForegroundWindow.restype = wintypes.HWND

user32.GetDesktopWindow.argtypes = []
user32.GetDesktopWindow.restype = wintypes.HWND

user32.GetShellWindow.argtypes = []
user32.GetShellWindow.restype = wintypes.HWND

user32.IsIconic.argtypes = [wintypes.HWND]
user32.IsIconic.restype = wintypes.BOOL

user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
user32.ShowWindow.restype = wintypes.BOOL

user32.SetForegroundWindow.argtypes = [wintypes.HWND]
user32.SetForegroundWindow.restype = wintypes.BOOL

user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
user32.GetWindowRect.restype = wintypes.BOOL

user32.GetClientRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
user32.GetClientRect.restype = wintypes.BOOL

user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
user32.GetWindowThreadProcessId.restype = wintypes.DWORD

try:
    dwmapi = ctypes.windll.dwmapi
    dwmapi.DwmGetWindowAttribute.argtypes = [
        wintypes.HWND, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD
    ]
    dwmapi.DwmGetWindowAttribute.restype = ctypes.c_long
except Exception:
    dwmapi = None

GetWindowLongPtrW = getattr(user32, "GetWindowLongPtrW", user32.GetWindowLongW)
GetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int]
GetWindowLongPtrW.restype = LONG_PTR

# Fixed 32-bit fallback to SetWindowLongW (previously GetWindowLongW)
SetWindowLongPtrW = getattr(user32, "SetWindowLongPtrW", user32.SetWindowLongW)
SetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int, LONG_PTR]
SetWindowLongPtrW.restype = LONG_PTR


def to_signed_long_ptr(val32) -> LONG_PTR:
    """Safely converts a 32-bit unsigned Win32 style/LPARAM mask into a signed LONG_PTR for 32-bit and 64-bit Python."""
    u = int(val32) & 0xFFFFFFFF
    signed_32 = (u - 0x100000000) if (u & 0x80000000) else u
    return LONG_PTR(signed_32)


INJECTION_LOCK = threading.Lock()
TOPOLOGY_LOCK = threading.RLock()
_RESYNC_LOCK = threading.Lock()
_KNOWN_DEVICE_TO_SCREEN_ID = {}
_LAST_INITIALIZED_PROGMAN_HWND = None
_BASELINE_DESKTOP_ICON_METRICS = None


def enumerate_connected_monitors():
    """Enumerates all physical displays via Win32 EnumDisplayMonitors."""
    raw_monitors = []

    def _monitor_enum_proc(hMonitor, hdcMonitor, lprcMonitor, dwData):
        info = MONITORINFOEXW()
        info.cbSize = ctypes.sizeof(MONITORINFOEXW)
        if user32.GetMonitorInfoW(hMonitor, ctypes.byref(info)):
            r = info.rcMonitor
            w = r.right - r.left
            h = r.bottom - r.top
            is_primary = bool(info.dwFlags & 1)
            raw_monitors.append({
                "x": int(r.left),
                "y": int(r.top),
                "width": int(w),
                "height": int(h),
                "is_primary": is_primary,
                "device": info.szDevice,
            })
        return True

    cb = MONITORENUMPROC(_monitor_enum_proc)
    try:
        user32.EnumDisplayMonitors(None, None, cb, 0)
    except Exception:
        pass

    if not raw_monitors:
        sw = user32.GetSystemMetrics(SM_CXSCREEN)
        sh = user32.GetSystemMetrics(SM_CYSCREEN)
        raw_monitors.append({
            "x": 0, "y": 0, "width": sw, "height": sh, "is_primary": True, "device": "DISPLAY1"
        })

    raw_monitors.sort(key=lambda m: (0 if m["is_primary"] else 1, m["x"], m["y"]))

    screens = []
    for idx, m in enumerate(raw_monitors, start=1):
        screen_id = f"screen_{idx}"
        primary_tag = " (Primary)" if m["is_primary"] else ""
        screens.append({
            "id": screen_id,
            "index": idx,
            "name": f"Screen {idx}",
            "label": f"Screen {idx}: {m['width']}x{m['height']}{primary_tag}",
            "x": m["x"],
            "y": m["y"],
            "width": m["width"],
            "height": m["height"],
            "is_primary": m["is_primary"],
            "device": m["device"],
        })
    return screens


def get_display_topology_signature():
    """
    Computes a lightweight, deterministic fingerprint of the current Windows Virtual Screen
    and all active physical monitors so HDMI TV hotplugs, resolution changes, or DPI coordinate
    shifts are detected immediately in the background.
    """
    vx = int(user32.GetSystemMetrics(SM_XVIRTUALSCREEN))
    vy = int(user32.GetSystemMetrics(SM_YVIRTUALSCREEN))
    vw = int(user32.GetSystemMetrics(SM_CXVIRTUALSCREEN))
    vh = int(user32.GetSystemMetrics(SM_CYVIRTUALSCREEN))
    monitors = enumerate_connected_monitors()
    mon_sig = tuple(
        (m.get("device", ""), int(m["x"]), int(m["y"]), int(m["width"]), int(m["height"]), bool(m["is_primary"]))
        for m in monitors
    )
    return (vx, vy, vw, vh, mon_sig)


def get_connected_screens_snapshot() -> list:
    """Returns a thread-safe shallow copy of CONNECTED_SCREENS under TOPOLOGY_LOCK."""
    with TOPOLOGY_LOCK:
        return [dict(s) for s in (CONNECTED_SCREENS or [])]


def refresh_connected_screens_preserving_ids():
    """
    Refreshes CONNECTED_SCREENS while preserving existing screen_id assignments
    across HDMI hotplugs (power-on / power-off cycles) via a two-pass device-name
    registry so newly connected displays never collide with existing screen_ids.
    """
    global CONNECTED_SCREENS
    fresh = enumerate_connected_monitors()

    with TOPOLOGY_LOCK:
        for s in (CONNECTED_SCREENS or []):
            dev = s.get("device")
            sid = s.get("id")
            if dev and sid:
                _KNOWN_DEVICE_TO_SCREEN_ID[dev] = sid

        if not _KNOWN_DEVICE_TO_SCREEN_ID:
            for m in fresh:
                dev = m.get("device")
                if dev:
                    _KNOWN_DEVICE_TO_SCREEN_ID[dev] = m["id"]
            CONNECTED_SCREENS = fresh
            return [dict(s) for s in CONNECTED_SCREENS]

        used_ids = set()
        unmatched = []
        updated = []

        # Pass 1: Assign preserved screen_ids to all known monitor devices
        for m in fresh:
            dev = m.get("device")
            matched_id = _KNOWN_DEVICE_TO_SCREEN_ID.get(dev) if dev else None
            if matched_id and matched_id not in used_ids:
                used_ids.add(matched_id)
                idx_num = int(matched_id.split("_")[-1]) if matched_id.split("_")[-1].isdigit() else m["index"]
                primary_tag = " (Primary)" if m["is_primary"] else ""
                m["id"] = matched_id
                m["index"] = idx_num
                m["name"] = f"Screen {idx_num}"
                m["label"] = f"Screen {idx_num}: {m['width']}x{m['height']}{primary_tag}"
                updated.append(m)
            else:
                unmatched.append(m)

        # Pass 2: Assign strictly collision-free screen_ids to newly connected monitors (e.g., HDMI TV turning on)
        reserved_ids = set(used_ids) | set(_KNOWN_DEVICE_TO_SCREEN_ID.values())
        for m in unmatched:
            next_idx = 1
            while f"screen_{next_idx}" in reserved_ids:
                next_idx += 1
            new_id = f"screen_{next_idx}"
            reserved_ids.add(new_id)
            used_ids.add(new_id)
            dev = m.get("device")
            if dev:
                _KNOWN_DEVICE_TO_SCREEN_ID[dev] = new_id
            primary_tag = " (Primary)" if m["is_primary"] else ""
            m["id"] = new_id
            m["index"] = next_idx
            m["name"] = f"Screen {next_idx}"
            m["label"] = f"Screen {next_idx}: {m['width']}x{m['height']}{primary_tag}"
            updated.append(m)

        updated.sort(key=lambda s: s["index"])
        CONNECTED_SCREENS = updated
        return [dict(s) for s in CONNECTED_SCREENS]


def find_desktop_listview_hwnd(progman=None):
    """Locates (SHELLDLL_DefView, SysListView32) across Windows 11 24H2+ Progman and Classic WorkerW."""
    if not progman:
        progman = user32.FindWindowW("Progman", None)
    if progman:
        shell_view = user32.FindWindowExW(progman, 0, "SHELLDLL_DefView", None)
        if shell_view:
            listview = user32.FindWindowExW(shell_view, 0, "SysListView32", None)
            return shell_view, listview

    found = [0, 0]

    def _enum_proc(top_hwnd, lparam):
        sv = user32.FindWindowExW(top_hwnd, 0, "SHELLDLL_DefView", None)
        if sv:
            lv = user32.FindWindowExW(sv, 0, "SysListView32", None)
            found[0] = sv
            found[1] = lv
            return False
        return True

    cb = WNDENUMPROC(_enum_proc)
    try:
        user32.EnumWindows(cb, 0)
    except Exception:
        pass
    return found[0], found[1]


def capture_desktop_icon_metrics(progman=None):
    """
    Snapshots the user's current desktop icon view mode (LVM_GETVIEW) and icon cell spacing
    (LVM_GETITEMSPACING) from Explorer's SysListView32 before desktop topology initialization.
    """
    global _BASELINE_DESKTOP_ICON_METRICS
    _, listview = find_desktop_listview_hwnd(progman)
    if not listview or not user32.IsWindow(listview):
        return _BASELINE_DESKTOP_ICON_METRICS

    view_res = ctypes.c_size_t(0)
    spacing_large = ctypes.c_size_t(0)
    spacing_small = ctypes.c_size_t(0)

    ok1 = user32.SendMessageTimeoutW(
        listview, LVM_GETVIEW, 0, 0, SMTO_NORMAL, 150, ctypes.byref(view_res)
    )
    ok2 = user32.SendMessageTimeoutW(
        listview, LVM_GETITEMSPACING, 0, 0, SMTO_NORMAL, 150, ctypes.byref(spacing_large)
    )
    user32.SendMessageTimeoutW(
        listview, LVM_GETITEMSPACING, 1, 0, SMTO_NORMAL, 150, ctypes.byref(spacing_small)
    )
    if ok1 and ok2 and spacing_large.value > 0:
        cx = int(spacing_large.value) & 0xFFFF
        cy = (int(spacing_large.value) >> 16) & 0xFFFF
        if 32 <= cx <= 512 and 32 <= cy <= 512:
            metrics = {
                "listview_hwnd": int(listview),
                "view_mode": int(view_res.value),
                "spacing_large": int(spacing_large.value),
                "spacing_small": int(spacing_small.value),
                "cx": cx,
                "cy": cy,
            }
            if _BASELINE_DESKTOP_ICON_METRICS is None:
                _BASELINE_DESKTOP_ICON_METRICS = metrics
            return metrics
    return _BASELINE_DESKTOP_ICON_METRICS


def restore_desktop_icon_metrics_if_inflated(progman=None):
    """
    Checks whether an HDMI hotplug / DPI transition caused Explorer's SHELLDLL_DefView
    to inflate desktop icon spacing or view mode, and restores the baseline metrics if altered.
    """
    if not _BASELINE_DESKTOP_ICON_METRICS:
        return False
    _, listview = find_desktop_listview_hwnd(progman)
    if not listview or not user32.IsWindow(listview):
        return False

    cur_view = ctypes.c_size_t(0)
    cur_spacing = ctypes.c_size_t(0)
    ok1 = user32.SendMessageTimeoutW(
        listview, LVM_GETVIEW, 0, 0, SMTO_NORMAL, 150, ctypes.byref(cur_view)
    )
    ok2 = user32.SendMessageTimeoutW(
        listview, LVM_GETITEMSPACING, 0, 0, SMTO_NORMAL, 150, ctypes.byref(cur_spacing)
    )
    if not (ok1 and ok2 and cur_spacing.value > 0):
        return False

    cur_cx = int(cur_spacing.value) & 0xFFFF
    cur_cy = (int(cur_spacing.value) >> 16) & 0xFFFF
    base_cx = _BASELINE_DESKTOP_ICON_METRICS["cx"]
    base_cy = _BASELINE_DESKTOP_ICON_METRICS["cy"]
    base_view = _BASELINE_DESKTOP_ICON_METRICS["view_mode"]
    base_spacing = _BASELINE_DESKTOP_ICON_METRICS["spacing_large"]

    # Detect unintended icon inflation (>4px spacing jump or view mode switch triggered by HDMI DPI change)
    if abs(cur_cx - base_cx) > 4 or abs(cur_cy - base_cy) > 4 or int(cur_view.value) != base_view:
        dummy = ctypes.c_size_t(0)
        if int(cur_view.value) != base_view:
            user32.SendMessageTimeoutW(
                listview, LVM_SETVIEW, base_view, 0, SMTO_NORMAL, 150, ctypes.byref(dummy)
            )
        user32.SendMessageTimeoutW(
            listview,
            LVM_SETICONSPACING,
            0,
            to_signed_long_ptr(base_spacing),
            SMTO_NORMAL,
            150,
            ctypes.byref(dummy),
        )
        user32.RedrawWindow(
            listview, None, None, RDW_INVALIDATE | RDW_ALLCHILDREN | RDW_FRAME
        )
        log_event(
            "win32",
            f"Restored desktop icon metrics after display DPI transition (spacing {cur_cx}x{cur_cy} -> {base_cx}x{base_cy}).",
        )
        return True
    return False


def has_webview_render_child(hwnd):
    """Checks whether WebView2 has created its internal Chrome_WidgetWin_0/1 child surface."""
    found = [False]
    class_buf = ctypes.create_unicode_buffer(256)

    def _check_child(child_hwnd, lparam):
        if user32.GetClassNameW(child_hwnd, class_buf, 256) > 0:
            cname = class_buf.value
            if cname.startswith("Chrome_WidgetWin_") or cname == "Intermediate D3D Window":
                found[0] = True
                return False
        return True

    cb = WNDENUMPROC(_check_child)
    user32.EnumChildWindows(hwnd, cb, 0)
    return found[0]


def get_webview_hwnd(window, window_title):
    """Retrieves the native Win32 HWND once the nested WebView2 rendering surface is initialized."""
    hwnd = None

    if window is not None and hasattr(window, "native") and window.native is not None:
        try:
            hwnd_val = window.native.Handle.ToInt64()
            if hwnd_val:
                hwnd = hwnd_val
        except Exception:
            pass

    if not hwnd:
        hwnd = user32.FindWindowW(None, window_title)

    if hwnd and has_webview_render_child(hwnd):
        return hwnd
    return None


def _probe_existing_desktop_topology(progman):
    """
    Non-destructively inspects Progman and WorkerW without sending 0x052C so active
    Windows 11 24H2+ child attachments, SHELLDLL_DefView icon metrics, and sibling
    overlays (such as Glass-Pane) are never reset during routine geometry syncs.
    """
    progman_ex = GetWindowLongPtrW(progman, GWL_EXSTYLE) & 0xFFFFFFFF
    is_noref_bitmap = bool(progman_ex & WS_EX_NOREDIRECTIONBITMAP)

    shell_view_in_progman = user32.FindWindowExW(progman, 0, "SHELLDLL_DefView", None)
    workerw_in_progman = user32.FindWindowExW(progman, 0, "WorkerW", None)

    classic_workerw = []

    def _enum_proc(top_hwnd, lparam):
        shell_view = user32.FindWindowExW(top_hwnd, 0, "SHELLDLL_DefView", None)
        if shell_view:
            sibling = user32.FindWindowExW(0, top_hwnd, "WorkerW", None)
            if sibling:
                classic_workerw.append(sibling)
                return False
        return True

    enum_cb = WNDENUMPROC(_enum_proc)
    user32.EnumWindows(enum_cb, 0)

    is_win11_24h2 = (
        is_noref_bitmap
        and bool(shell_view_in_progman)
        and bool(workerw_in_progman)
        and not classic_workerw
    )

    has_valid_workerw = bool(workerw_in_progman) or bool(classic_workerw)

    return {
        "is_win11_24h2": is_win11_24h2,
        "shell_view_in_progman": shell_view_in_progman,
        "workerw_in_progman": workerw_in_progman,
        "classic_workerw": classic_workerw[0] if classic_workerw else None,
        "has_valid_workerw": has_valid_workerw,
    }


def enumerate_desktop_topology(progman, force_init=False):
    """
    Resolves the desktop window topology across Windows 10, Windows 11 (21H2-23H2),
    and Windows 11 24H2+. Sends 0x052C to Progman ONLY when WorkerW has not been
    spawned yet (initial startup or after an explorer.exe restart), preventing
    SHELLDLL_DefView desktop icon inflation and sibling overlay disruption.
    """
    global _LAST_INITIALIZED_PROGMAN_HWND
    capture_desktop_icon_metrics(progman)

    topo = _probe_existing_desktop_topology(progman)
    needs_052c = (
        force_init
        or not topo["has_valid_workerw"]
        or (_LAST_INITIALIZED_PROGMAN_HWND != int(progman))
    )

    if needs_052c:
        # Only send 0x052C if WorkerW truly does not exist yet or force_init was requested
        if not topo["has_valid_workerw"] or force_init:
            result = ctypes.c_size_t(0)
            user32.SendMessageTimeoutW(progman, 0x052C, 0, 0, SMTO_NORMAL, 1000, ctypes.byref(result))
            user32.SendMessageTimeoutW(progman, 0x052C, 0xD, 0x1, SMTO_NORMAL, 1000, ctypes.byref(result))
            time.sleep(0.05)
            topo = _probe_existing_desktop_topology(progman)
        _LAST_INITIALIZED_PROGMAN_HWND = int(progman)
        restore_desktop_icon_metrics_if_inflated(progman)

    return topo


def _apply_passive_wallpaper_window_styles(hwnd, is_win11_24h2: bool):
    """
    Configures the wallpaper host HWND as a strictly passive, disabled, click-through child surface
    (WS_CHILD | WS_DISABLED + WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE | WS_EX_TRANSPARENT) so Windows 11
    Snap Assist / Task View, Glass-Pane hooks, and mouse-wheel DPI zoom events completely ignore it.
    """
    user32.EnableWindow(hwnd, False)
    style = GetWindowLongPtrW(hwnd, GWL_STYLE) & 0xFFFFFFFF
    clear_mask = WS_CAPTION | WS_THICKFRAME | WS_MINIMIZEBOX | WS_MAXIMIZEBOX | WS_SYSMENU | WS_POPUP
    style = (style & ~clear_mask) | WS_CHILD | WS_VISIBLE | WS_CLIPSIBLINGS | WS_CLIPCHILDREN | WS_DISABLED
    SetWindowLongPtrW(hwnd, GWL_STYLE, to_signed_long_ptr(style))

    ex_style = GetWindowLongPtrW(hwnd, GWL_EXSTYLE) & 0xFFFFFFFF
    if is_win11_24h2:
        ex_style = (
            (ex_style & ~WS_EX_APPWINDOW)
            | WS_EX_TOOLWINDOW
            | WS_EX_NOACTIVATE
            | WS_EX_LAYERED
            | WS_EX_TRANSPARENT
        )
        SetWindowLongPtrW(hwnd, GWL_EXSTYLE, to_signed_long_ptr(ex_style))
        user32.SetLayeredWindowAttributes(hwnd, 0, 255, LWA_ALPHA)
    else:
        ex_style = (
            (ex_style & ~(WS_EX_APPWINDOW | WS_EX_LAYERED))
            | WS_EX_TOOLWINDOW
            | WS_EX_NOACTIVATE
            | WS_EX_TRANSPARENT
        )
        SetWindowLongPtrW(hwnd, GWL_EXSTYLE, to_signed_long_ptr(ex_style))


def resize_webview_child_containers(hwnd, screen_w, screen_h):
    """
    Forces all inner WinForms and Chromium host controls to fill (0, 0, screen_w, screen_h)
    and disables direct hit-testing on child containers so wheel/gesture events never leak.
    """
    safe_w = max(1, int(screen_w)) & 0xFFFF
    safe_h = max(1, int(screen_h)) & 0xFFFF
    lparam_size = (safe_h << 16) | safe_w
    user32.SendMessageTimeoutW(
        hwnd, WM_SIZE, SIZE_RESTORED, to_signed_long_ptr(lparam_size),
        SMTO_NORMAL, 150, ctypes.byref(ctypes.c_size_t(0))
    )

    class_buf = ctypes.create_unicode_buffer(256)

    def _resize_child(child_hwnd, lparam):
        child_style = GetWindowLongPtrW(child_hwnd, GWL_STYLE) & 0xFFFFFFFF
        if not (child_style & WS_VISIBLE):
            return True
        if user32.GetClassNameW(child_hwnd, class_buf, 256) > 0:
            cname = class_buf.value
            if (
                cname.startswith("WindowsForms10.")
                or cname.startswith("Chrome_WidgetWin_")
                or cname == "Chrome_RenderWidgetHostHWND"
                or cname == "Intermediate D3D Window"
            ):
                user32.EnableWindow(child_hwnd, False)
                user32.SetWindowPos(
                    child_hwnd, 0, 0, 0, screen_w, screen_h,
                    SWP_NOZORDER | SWP_NOACTIVATE | SWP_FRAMECHANGED | SWP_ASYNCWINDOWPOS
                )
                user32.SendMessageTimeoutW(
                    child_hwnd, WM_SIZE, SIZE_RESTORED, to_signed_long_ptr(lparam_size),
                    SMTO_NORMAL, 150, ctypes.byref(ctypes.c_size_t(0))
                )
        return True

    child_cb = WNDENUMPROC(_resize_child)
    user32.EnumChildWindows(hwnd, child_cb, 0)


def sync_all_screens_z_order_and_geometry(target_screen_id=None, force_reattach=False):
    """
    Synchronizes geometry, parent attachment, visibility, and desktop Z-order across ALL monitor HWNDs.
    - Hides and pauses HWNDs belonging to disconnected monitors (e.g. when an HDMI TV is turned off)
      so they never ghost onto remaining displays as Task View-like tiles.
    - Verifies GetParent(hwnd) and GetWindowRect(hwnd) to automatically heal WinForms DPI auto-scaling
      or Explorer reparenting after HDMI hotplug events.
    """
    disconnected_pause_updates = []
    with INJECTION_LOCK:
        progman = user32.FindWindowW("Progman", None)
        if not progman:
            return
        topo = enumerate_desktop_topology(progman, force_init=False)
        target_parent = (
            progman
            if topo["is_win11_24h2"]
            else (topo["classic_workerw"] or topo["workerw_in_progman"] or progman)
        )
        insert_after = (
            topo["shell_view_in_progman"]
            if (topo["is_win11_24h2"] and topo["shell_view_in_progman"])
            else HWND_TOP
        )

        screens_by_id = {s["id"]: s for s in get_connected_screens_snapshot()}

        for sid, hwnd in list(DESKTOP_HWNDS.items()):
            if not hwnd or not user32.IsWindow(hwnd):
                DESKTOP_HWNDS.pop(sid, None)
                DESKTOP_INJECTED_SET.discard(sid)
                continue

            # If this screen is currently disconnected (e.g. HDMI TV turned off), hide its HWND immediately
            # and mark it disconnected_paused so it cannot render over remaining monitors.
            if sid not in screens_by_id:
                style = GetWindowLongPtrW(hwnd, GWL_STYLE) & 0xFFFFFFFF
                if style & WS_VISIBLE:
                    style &= ~WS_VISIBLE
                    SetWindowLongPtrW(hwnd, GWL_STYLE, to_signed_long_ptr(style))
                user32.SetWindowPos(
                    hwnd, 0, -32000, -32000, 1, 1,
                    SWP_NOZORDER | SWP_NOACTIVATE | SWP_HIDEWINDOW | SWP_ASYNCWINDOWPOS
                )
                disconnected_pause_updates.append((sid, True))
                continue

            disconnected_pause_updates.append((sid, False))
            s_info = screens_by_id[sid]
            sc_cfg = get_screen_config(sid)
            enabled = sc_cfg["enabled"]

            screen_w = s_info["width"]
            screen_h = s_info["height"]

            current_parent = user32.GetParent(hwnd)
            style = GetWindowLongPtrW(hwnd, GWL_STYLE) & 0xFFFFFFFF
            parent_drifted = (
                force_reattach
                or (current_parent != target_parent)
                or not bool(style & WS_CHILD)
                or bool(style & WS_POPUP)
            )
            if parent_drifted:
                _apply_passive_wallpaper_window_styles(hwnd, topo["is_win11_24h2"])
                user32.SetParent(hwnd, target_parent)
                style = GetWindowLongPtrW(hwnd, GWL_STYLE) & 0xFFFFFFFF

            pt = wintypes.POINT(s_info["x"], s_info["y"])
            user32.ScreenToClient(target_parent, ctypes.byref(pt))

            was_visible = bool(style & WS_VISIBLE)
            rect_drifted = False
            if enabled and was_visible:
                rc = wintypes.RECT()
                if user32.GetWindowRect(hwnd, ctypes.byref(rc)):
                    cur_w = rc.right - rc.left
                    cur_h = rc.bottom - rc.top
                    if (
                        abs(rc.left - s_info["x"]) > 2
                        or abs(rc.top - s_info["y"]) > 2
                        or abs(cur_w - screen_w) > 2
                        or abs(cur_h - screen_h) > 2
                    ):
                        rect_drifted = True

            is_target = (
                target_screen_id is None
                or target_screen_id == sid
                or not was_visible
                or parent_drifted
                or rect_drifted
            )
            if enabled:
                if not was_visible:
                    style |= WS_VISIBLE
                    SetWindowLongPtrW(hwnd, GWL_STYLE, to_signed_long_ptr(style))

                if is_target:
                    user32.SetWindowPos(
                        hwnd, insert_after, pt.x, pt.y, screen_w - 1, screen_h - 1,
                        SWP_NOACTIVATE | SWP_FRAMECHANGED | SWP_SHOWWINDOW | SWP_ASYNCWINDOWPOS
                    )
                    user32.SetWindowPos(
                        hwnd, insert_after, pt.x, pt.y, screen_w, screen_h,
                        SWP_NOACTIVATE | SWP_FRAMECHANGED | SWP_SHOWWINDOW | SWP_ASYNCWINDOWPOS
                    )
                    resize_webview_child_containers(hwnd, screen_w, screen_h)
                    user32.RedrawWindow(
                        hwnd, None, None,
                        RDW_INVALIDATE | RDW_ALLCHILDREN | RDW_FRAME
                    )
                else:
                    user32.SetWindowPos(
                        hwnd, insert_after, pt.x, pt.y, screen_w, screen_h,
                        SWP_NOACTIVATE | SWP_ASYNCWINDOWPOS
                    )
                insert_after = hwnd
            else:
                style &= ~WS_VISIBLE
                SetWindowLongPtrW(hwnd, GWL_STYLE, to_signed_long_ptr(style))
                user32.SetWindowPos(
                    hwnd, 0, pt.x, pt.y, screen_w, screen_h,
                    SWP_NOZORDER | SWP_NOACTIVATE | SWP_HIDEWINDOW | SWP_ASYNCWINDOWPOS
                )

        if topo["is_win11_24h2"] and topo["workerw_in_progman"]:
            user32.SetWindowPos(
                topo["workerw_in_progman"],
                wintypes.HWND(HWND_BOTTOM),
                0, 0, 0, 0,
                SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_ASYNCWINDOWPOS
            )

        restore_desktop_icon_metrics_if_inflated(progman)

    # Synchronize disconnected_paused runtime state outside INJECTION_LOCK to preserve lock hierarchy
    for sid, is_disc in disconnected_pause_updates:
        changed = False
        with DATA_LOCK:
            st = get_screen_runtime_state(sid)
            if bool(st.get("disconnected_paused", False)) != is_disc:
                st["disconnected_paused"] = is_disc
                changed = True
        if changed:
            push_pause_states_to_webviews(sid)
            if not is_disc and is_screen_enabled(sid) and not is_screen_effectively_paused(sid):
                ensure_screen_tag_pool_populated_async(sid, force_reset=False)


def attach_window_to_desktop(window, window_title, mon_x=0, mon_y=0, mon_w=None, mon_h=None):
    """
    Injects a pywebview window behind desktop icons at the target monitor's coordinates.
    """
    hwnd = None
    for _ in range(80):
        hwnd = get_webview_hwnd(window, window_title)
        if hwnd:
            break
        time.sleep(0.1)

    if not hwnd:
        log_event("win32", f"Failed to locate initialized WebView2 HWND for '{window_title}'")
        return None

    with INJECTION_LOCK:
        progman = user32.FindWindowW("Progman", None)
        if not progman:
            log_event("win32", "Failed to locate Progman window.")
            return None

        topo = enumerate_desktop_topology(progman, force_init=False)
        screen_w = mon_w if mon_w is not None else user32.GetSystemMetrics(SM_CXSCREEN)
        screen_h = mon_h if mon_h is not None else user32.GetSystemMetrics(SM_CYSCREEN)

        _apply_passive_wallpaper_window_styles(hwnd, topo["is_win11_24h2"])

        if topo["is_win11_24h2"]:
            target_parent = progman
            user32.SetParent(hwnd, target_parent)

            pt = wintypes.POINT(mon_x, mon_y)
            user32.ScreenToClient(target_parent, ctypes.byref(pt))

            insert_after = topo["shell_view_in_progman"] if topo["shell_view_in_progman"] else HWND_TOP
            user32.SetWindowPos(
                hwnd, insert_after, pt.x, pt.y, screen_w - 1, screen_h - 1,
                SWP_NOACTIVATE | SWP_FRAMECHANGED | SWP_SHOWWINDOW
            )
            user32.SetWindowPos(
                hwnd, insert_after, pt.x, pt.y, screen_w, screen_h,
                SWP_NOACTIVATE | SWP_FRAMECHANGED | SWP_SHOWWINDOW
            )

            if topo["workerw_in_progman"]:
                user32.SetWindowPos(
                    topo["workerw_in_progman"],
                    wintypes.HWND(HWND_BOTTOM),
                    0, 0, 0, 0,
                    SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE
                )

            log_event(
                "win32",
                f"Win11 24H2+ mode: Attached '{window_title}' HWND {hex(hwnd)} to Progman {hex(progman)} "
                f"at ({pt.x},{pt.y}) {screen_w}x{screen_h}"
            )
        else:
            target_parent = topo["classic_workerw"] or topo["workerw_in_progman"] or progman
            user32.SetParent(hwnd, target_parent)

            pt = wintypes.POINT(mon_x, mon_y)
            user32.ScreenToClient(target_parent, ctypes.byref(pt))

            user32.SetWindowPos(
                hwnd, HWND_TOP, pt.x, pt.y, screen_w - 1, screen_h - 1,
                SWP_NOACTIVATE | SWP_FRAMECHANGED | SWP_SHOWWINDOW
            )
            user32.SetWindowPos(
                hwnd, HWND_TOP, pt.x, pt.y, screen_w, screen_h,
                SWP_NOACTIVATE | SWP_FRAMECHANGED | SWP_SHOWWINDOW
            )
            log_event(
                "win32",
                f"Classic WorkerW mode: Attached '{window_title}' HWND {hex(hwnd)} to WorkerW {hex(target_parent)} "
                f"at ({pt.x},{pt.y}) {screen_w}x{screen_h}"
            )

        resize_webview_child_containers(hwnd, screen_w, screen_h)
        user32.RedrawWindow(
            hwnd, None, None,
            RDW_INVALIDATE | RDW_UPDATENOW | RDW_ALLCHILDREN | RDW_FRAME
        )
        restore_desktop_icon_metrics_if_inflated(progman)
        return hwnd


# =============================================================================
# 2. PATH ROUTING & EPHEMERAL CONFIGURATION STORAGE (NO WEBVIEW_PROFILE DISK CACHE)
# =============================================================================
def get_resource_path(relative_path):
    base_path = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)


APPDATA_ROOT = os.getenv("APPDATA") or os.path.expanduser("~")
PERSISTENT_DIR = os.path.join(APPDATA_ROOT, "DanbooruWallpaper")
os.makedirs(PERSISTENT_DIR, exist_ok=True)

SAVED_SEARCHES_FILE = os.path.join(PERSISTENT_DIR, "saved_searches.json")
CONFIG_FILE = os.path.join(PERSISTENT_DIR, "config.json")
PROJECT_JSON_FILE = os.path.join(PERSISTENT_DIR, "project.json")

BUNDLED_HTML_FILE = get_resource_path("index.html")
BUNDLED_PROJECT_JSON = get_resource_path("project.json")


def cleanup_legacy_webview_profile():
    """Removes any leftover legacy webview_profile disk directory from previous versions."""
    legacy_profile = os.path.join(PERSISTENT_DIR, "webview_profile")
    if os.path.exists(legacy_profile):
        try:
            shutil.rmtree(legacy_profile, ignore_errors=True)
        except Exception:
            pass


def get_default_properties_dict():
    return {
        "searchtags": {"order": 0, "text": "Search Tags", "type": "textinput", "value": "scenery no_humans"},
        "schemecolor": {"order": 1, "text": "ui_browse_properties_scheme_color", "type": "color", "value": "0.04 0.04 0.05"},
        "vsync": {
            "order": 2,
            "text": "V-Sync",
            "type": "bool",
            "value": True,
        },
        "targetfps": {
            "condition": "vsync.value == false",
            "order": 3,
            "text": "Target FPS (15 – 240)",
            "type": "slider",
            "min": 15,
            "max": 240,
            "step": 1,
            "value": 60,
            "editable": True,
        },
        "displaymode": {
            "order": 4,
            "text": "Display Mode",
            "type": "combo",
            "value": "scroll",
            "options": [
                {"label": "Scrolling Slideshow", "value": "scroll"},
                {"label": "Polaroid", "value": "polaroid"},
                {"label": "Fullscreen Slideshow", "value": "slideshow"},
                {"label": "Masonry", "value": "masonry"},
            ],
        },
        "scrolldirection": {
            "condition": "displaymode.value == 'scroll'",
            "order": 5,
            "text": "Scroll Direction",
            "type": "combo",
            "value": "left",
            "options": [
                {"label": "Scroll Left (←)", "value": "left"},
                {"label": "Scroll Right (→)", "value": "right"},
                {"label": "Scroll Up (↑)", "value": "up"},
                {"label": "Scroll Down (↓)", "value": "down"},
            ],
        },
        "scrollspeed": {
            "condition": "displaymode.value == 'scroll'",
            "order": 6,
            "text": "Scroll Speed (0.1 – 600 px/s)",
            "type": "slider",
            "min": 0.1,
            "max": 600,
            "step": 0.1,
            "precision": 2,
            "value": 120,
            "editable": True,
        },
        "gapsize": {
            "condition": "displaymode.value == 'scroll'",
            "order": 7,
            "text": "Image Gap (0 – 64 px)",
            "type": "slider",
            "min": 0,
            "max": 64,
            "step": 1,
            "value": 12,
            "editable": True,
        },
        "dropspeed": {
            "condition": "displaymode.value == 'polaroid'",
            "order": 8,
            "text": "Drop Speed (0.2 – 4.0)",
            "type": "slider",
            "min": 0.2,
            "max": 4.0,
            "step": 0.1,
            "precision": 2,
            "value": 1.0,
            "editable": True,
        },
        "minsize": {
            "condition": "displaymode.value == 'polaroid'",
            "order": 9,
            "text": "Minimum Size (120 – 600 px)",
            "type": "slider",
            "min": 120,
            "max": 600,
            "step": 1,
            "value": 220,
            "editable": True,
        },
        "maxsize": {
            "condition": "displaymode.value == 'polaroid'",
            "order": 10,
            "text": "Maximum Size (150 – 900 px)",
            "type": "slider",
            "min": 150,
            "max": 900,
            "step": 1,
            "value": 440,
            "editable": True,
        },
        "dropdelay": {
            "condition": "displaymode.value == 'polaroid'",
            "order": 11,
            "text": "Spawn/Drop Delay (0 – 600 s)",
            "type": "slider",
            "min": 0,
            "max": 600,
            "step": 1,
            "value": 0,
            "editable": True,
        },
        "slideshowfade": {
            "condition": "displaymode.value == 'slideshow'",
            "order": 12,
            "text": "Fade Transition (0 – 10 [0s – 1.0s])",
            "type": "slider",
            "min": 0,
            "max": 10,
            "step": 0.1,
            "precision": 1,
            "value": 5,
            "editable": True,
        },
        "slideshowduration": {
            "condition": "displaymode.value == 'slideshow'",
            "order": 13,
            "text": "Slide Display Time (0 – 600 s)",
            "type": "slider",
            "min": 0,
            "max": 600,
            "step": 1,
            "value": 10,
            "editable": True,
        },
        "masonrylayout": {
            "condition": "displaymode.value == 'masonry'",
            "order": 14,
            "text": "Masonry Layout",
            "type": "combo",
            "value": "mondrian",
            "options": [
                {"label": "Mondrian", "value": "mondrian"},
                {"label": "Rows", "value": "rows"},
            ],
        },
        "masonryedgefill": {
            "condition": "displaymode.value == 'masonry'",
            "order": 15,
            "text": "Edge Fill",
            "type": "combo",
            "value": "blur",
            "options": [
                {"label": "Blur", "value": "blur"},
                {"label": "Black", "value": "black"},
            ],
        },
        "masonrytiles": {
            "condition": "displaymode.value == 'masonry'",
            "order": 16,
            "text": "Target Tile Count (4 – 36)",
            "type": "slider",
            "min": 4,
            "max": 36,
            "step": 1,
            "value": 12,
            "editable": True,
        },
        "masonrygap": {
            "condition": "displaymode.value == 'masonry'",
            "order": 17,
            "text": "Gap (0 – 10 px)",
            "type": "slider",
            "min": 0,
            "max": 10,
            "step": 1,
            "value": 4,
            "editable": True,
        },
        "masonrydelay": {
            "condition": "displaymode.value == 'masonry'",
            "order": 18,
            "text": "Delay (1 – 60 s)",
            "type": "slider",
            "min": 1,
            "max": 60,
            "step": 1,
            "value": 5,
            "editable": True,
        },
        "pausefullscreen": {
            "order": 19,
            "text": "Pause during full screen application",
            "type": "bool",
            "value": True,
        },
    }


DEFAULT_PROJECT_SCHEMA = {
    "file": "index.html",
    "general": {
        "properties": get_default_properties_dict()
    },
    "screens": {
        "screen_1": {
            "enabled": True,
            "properties": get_default_properties_dict()
        }
    },
    "title": "Danbooru Infinite Scroll, Polaroid, Fullscreen Slideshow & Masonry",
    "type": "web",
    "version": 2,
}


def init_persistent_storage():
    cleanup_legacy_webview_profile()

    if not os.path.exists(PROJECT_JSON_FILE):
        try:
            if os.path.exists(BUNDLED_PROJECT_JSON):
                shutil.copyfile(BUNDLED_PROJECT_JSON, PROJECT_JSON_FILE)
            else:
                with open(PROJECT_JSON_FILE, "w", encoding="utf-8") as f:
                    json.dump(DEFAULT_PROJECT_SCHEMA, f, indent=2)
        except Exception as e:
            safe_console_print(f"[INIT] Failed to initialize project.json in APPDATA: {e}")

    if not os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump({}, f, indent=2)
        except Exception:
            pass

    if not os.path.exists(SAVED_SEARCHES_FILE):
        try:
            with open(SAVED_SEARCHES_FILE, "w", encoding="utf-8") as f:
                json.dump([], f, indent=2)
        except Exception:
            pass


init_persistent_storage()

# =============================================================================
# 3. HYBRID TRANSPORT ENGINE (curl_cffi HTTP/2 + STDLIB DoH/SNI TLS 1.3 FALLBACK)
# =============================================================================
DEFAULT_TAGS = "scenery no_humans"
PORT = 8088
WEBVIEW_WINDOW_TITLE_PREFIX = "DanbooruWallpaperRendererHost"

# Danbooru API Guidelines rate-limit interval
MIN_API_INTERVAL = 2.0

# Max MP4 file size allowed through API metadata & Proxy stream (15 MB = 15,728,640 bytes)
MAX_MP4_FILE_SIZE_BYTES = 15 * 1024 * 1024
# Max static/animated image stream size allowed through Proxy stream (25 MB)
MAX_IMAGE_FILE_SIZE_BYTES = 25 * 1024 * 1024
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp", "gif", "mp4"}

# Strict path pattern: must end with a single allowed extension and contain no path traversal or executable/PHP tokens
SAFE_MEDIA_PATH_RE = re.compile(r"^/[A-Za-z0-9/_\-\.~%]+\.(jpg|jpeg|png|webp|gif|mp4)$", re.IGNORECASE)
FORBIDDEN_URL_TOKENS = (
    ".php", ".phtml", ".php3", ".php4", ".php5", ".php7", ".phps", ".phar", ".inc",
    ".exe", ".dll", ".bat", ".cmd", ".ps1", ".vbs", ".wsf", ".scr", ".msi", ".com",
    ".hta", ".jar", ".py", ".sh", ".svg", ".html", ".htm", ".xhtml", ".js", ".jsp", ".asp", ".aspx",
    "..", "%2e%2e", "%00", "\x00",
)

# Forbidden payload prefixes/signatures that must never appear in a media stream
FORBIDDEN_PAYLOAD_SIGNATURES = (
    b"<?php",
    b"<?=",
    b"<html",
    b"<!doctype html",
    b"<script",
    b"<svg",
    b"<?xml",
    b"#!",
    b"MZ",              # Windows PE executable / DLL header
    b"\x7fELF",         # Linux ELF binary
    b"\xca\xfe\xba\xbe",  # Mach-O binary header
    b"PK\x03\x04",      # ZIP / JAR / PHAR archive header
    b"Rar!\x1a\x07",    # RAR archive
)

ALLOWED_MEDIA_HOSTS = {
    "danbooru.donmai.us",
    "cdn.donmai.us",
}

ALLOWED_LOCAL_ORIGINS = {
    f"http://127.0.0.1:{PORT}",
    f"http://localhost:{PORT}",
}


def validate_safe_media_url(media_url: str, ext_hint: str = "") -> tuple[bool, str, str]:
    """
    Validates that a candidate media URL points strictly to an allowed HTTPS Danbooru CDN host,
    contains no PHP/executable double extensions or path traversal tokens, and ends in a clean
    whitelisted media extension.
    Returns (is_valid, normalized_ext, reason_if_invalid).
    """
    if not media_url or not isinstance(media_url, str):
        return False, "", "Empty media URL"
    try:
        parsed = urllib.parse.urlparse(media_url.strip())
    except Exception:
        return False, "", "Malformed URL"

    if parsed.scheme != "https":
        return False, "", f"Disallowed scheme '{parsed.scheme}'"

    hostname = (parsed.hostname or "").lower()
    if hostname not in ALLOWED_MEDIA_HOSTS:
        return False, "", f"Unauthorized host '{hostname}'"

    raw_path = urllib.parse.unquote(parsed.path or "")
    lower_path = raw_path.lower()
    lower_query = urllib.parse.unquote(parsed.query or "").lower()

    for token in FORBIDDEN_URL_TOKENS:
        if token in lower_path or token in lower_query:
            return False, "", f"Forbidden path/query token '{token}' detected"

    if not SAFE_MEDIA_PATH_RE.match(parsed.path or ""):
        return False, "", "URL path does not match strict single-extension media pattern"

    path_ext = lower_path.rsplit(".", 1)[-1] if "." in lower_path else ""
    if path_ext not in ALLOWED_EXTENSIONS:
        return False, "", f"Disallowed path extension '.{path_ext}'"

    norm_hint = str(ext_hint or "").lower().lstrip(".")
    if norm_hint and norm_hint not in ALLOWED_EXTENSIONS:
        return False, "", f"Disallowed file_ext metadata '.{norm_hint}'"

    if norm_hint and norm_hint != path_ext:
        # Allow jpg/jpeg equivalence
        if not ({norm_hint, path_ext} <= {"jpg", "jpeg"}):
            return False, "", f"Extension mismatch between metadata ('.{norm_hint}') and URL path ('.{path_ext}')"

    return True, path_ext, "OK"


def verify_media_magic_bytes(header_bytes: bytes, is_range_continuation: bool = False) -> tuple[bool, str, str]:
    """
    Inspects the initial binary bytes of an upstream media response to verify authentic
    JPEG, PNG, GIF87a/89a, WEBP, or ISO-BMFF MP4 magic signatures and block disguised
    PHP scripts, HTML/SVG polyglots, or PE/archive binaries.
    Returns (is_valid, canonical_mime_type, reason).
    """
    if not header_bytes:
        return False, "", "Empty response stream"

    head_probe = header_bytes[:512]
    head_lower = head_probe.lower()
    head_stripped = head_lower.lstrip()

    # Enforce all FORBIDDEN_PAYLOAD_SIGNATURES against polyglot scripts, markup, and binary executables
    for sig in FORBIDDEN_PAYLOAD_SIGNATURES:
        if sig in (b"<?php", b"<script", b"<!doctype html"):
            if sig in head_lower:
                return False, "", f"Malicious script/markup signature ({sig.decode('ascii', errors='ignore')}) detected in header"
        elif sig in (b"<?=", b"<html", b"<svg", b"<?xml", b"#!"):
            if head_stripped.startswith(sig.lower()):
                return False, "", f"Disallowed markup/script prefix ({sig.decode('ascii', errors='ignore')}) detected at start of stream"
        elif head_probe.startswith(sig):
            return False, "", f"Forbidden binary executable/archive header ({sig[:4]!r}) detected"

    if is_range_continuation:
        return True, "video/mp4", "MP4-Range"

    if len(header_bytes) < 8:
        return False, "", "Insufficient header bytes (minimum 8 bytes required)"

    # 1. JPEG: FF D8 FF
    if head_probe.startswith(b"\xff\xd8\xff"):
        return True, "image/jpeg", "JPEG"

    # 2. PNG: 89 50 4E 47 0D 0A 1A 0A
    if head_probe.startswith(b"\x89PNG\r\n\x1a\n"):
        return True, "image/png", "PNG"

    # 3. GIF: GIF87a or GIF89a
    if head_probe.startswith((b"GIF87a", b"GIF89a")):
        return True, "image/gif", "GIF"

    # 4. WEBP: RIFF....WEBP
    if len(head_probe) >= 12 and head_probe[:4] == b"RIFF" and head_probe[8:12] == b"WEBP":
        return True, "image/webp", "WEBP"

    # 5. MP4 (ISO Base Media File Format): bytes 4..8 == b'ftyp' (or b'moov' / b'mdat' / b'wide' / b'free' / b'styp' / b'skip' / b'uuid')
    if len(head_probe) >= 12 and head_probe[4:8] in (b"ftyp", b"moov", b"mdat", b"wide", b"free", b"styp", b"skip", b"uuid"):
        return True, "video/mp4", "MP4"

    return False, "", "Unrecognized binary magic-byte signature"


VERIFIED_MP4_BYTE0_URLS = OrderedDict()
MAX_VERIFIED_MP4_URLS = 512
VERIFIED_MP4_LOCK = threading.Lock()


def mark_mp4_url_verified(url: str):
    """Records that an MP4 URL has passed byte-0 magic-byte inspection so subsequent HTTP Range seeks are permitted."""
    if not url:
        return
    with VERIFIED_MP4_LOCK:
        if url in VERIFIED_MP4_BYTE0_URLS:
            VERIFIED_MP4_BYTE0_URLS.move_to_end(url)
        else:
            VERIFIED_MP4_BYTE0_URLS[url] = True
            while len(VERIFIED_MP4_BYTE0_URLS) > MAX_VERIFIED_MP4_URLS:
                VERIFIED_MP4_BYTE0_URLS.popitem(last=False)


def is_mp4_url_verified(url: str) -> bool:
    """Checks whether an MP4 URL has previously passed byte-0 magic-byte verification."""
    if not url:
        return False
    with VERIFIED_MP4_LOCK:
        if url in VERIFIED_MP4_BYTE0_URLS:
            VERIFIED_MP4_BYTE0_URLS.move_to_end(url)
            return True
        return False


def is_public_unicast_ipv4(ip_str: str) -> bool:
    """Strictly verifies that an IPv4 address is globally routable and not private/loopback/link-local."""
    try:
        ip_obj = ipaddress.ip_address(str(ip_str or "").strip())
        return (
            isinstance(ip_obj, ipaddress.IPv4Address)
            and ip_obj.is_global
            and not ip_obj.is_private
            and not ip_obj.is_loopback
            and not ip_obj.is_link_local
            and not ip_obj.is_multicast
            and not ip_obj.is_reserved
            and not ip_obj.is_unspecified
        )
    except ValueError:
        return False


CLOUDFLARE_DOH_IPS = ("1.1.1.1", "1.0.0.1")
DOH_CACHE_TTL = 900  # 15 minutes
MAX_DOH_CACHE_ENTRIES = 128
DOH_CACHE = OrderedDict()  # hostname -> (ip_str, expires_at)
DOH_LOCK = threading.Lock()

# Credentials are never hardcoded; pulled strictly from the Credentials tab (config.json)
USERNAME = ""
USER_ID = ""
API_KEY = ""

HTTP2_SESSION = None
SESSION_LOCK = threading.Lock()

# Theme Palettes for Light Mode & Dark Mode (Credentials tab toggle)
THEME_PALETTES = {
    "light": {
        "bg_base": "#f6f6f8",
        "input_bg": "#ffffff",
        "border_col": "#dcdce0",
        "text_dark": "#1c1c1c",
        "text_muted": "#5c5c5c",
        "btn_bg": "#e8e8ed",
        "btn_active": "#dcdce0",
        "hover_bg": "#f0f7ff",
        "row_hover": "#f0f0f3",
        "min_bar": "#cfcfd4",
        "arrow_bg": "#f0f0f3",
        "flash_bg": "#e8f0fe",
    },
    "dark": {
        "bg_base": "#0f0f12",
        "input_bg": "#1a1a20",
        "border_col": "#2e2e38",
        "text_dark": "#ffffff",
        "text_muted": "#b0b0be",
        "btn_bg": "#25252e",
        "btn_active": "#343442",
        "hover_bg": "#1e2a3a",
        "row_hover": "#25252e",
        "min_bar": "#343442",
        "arrow_bg": "#25252e",
        "flash_bg": "#1f3252",
    },
}

CURRENT_THEME = "light"

# Official Danbooru Tag Category Color Coordination (Light Mode & Dark Mode)
# Categories: 0 = General (Blue), 1 = Artist (Red), 3 = Copyright (Purple), 4 = Character (Green), 5 = Meta (Orange)
DANBOORU_TAG_COLORS = {
    "light": {
        0: "#0075f8",  # General (Danbooru Blue)
        1: "#c00004",  # Artist (Danbooru Red)
        3: "#a800aa",  # Copyright (Danbooru Purple)
        4: "#00ab2c",  # Character (Danbooru Green)
        5: "#fd9200",  # Meta (Danbooru Orange)
    },
    "dark": {
        0: "#009be6",  # General (Danbooru Dark Sky Blue)
        1: "#ff8a8b",  # Artist (Danbooru Dark Coral Red)
        3: "#c797ff",  # Copyright (Danbooru Dark Violet)
        4: "#35c64a",  # Character (Danbooru Dark Green)
        5: "#ead084",  # Meta (Danbooru Dark Gold/Amber)
    },
}

# Global Tag Category Cache: tag_name (lowercase) -> category int (0, 1, 3, 4, 5)
# Bounded at MAX_TAG_CATEGORY_CACHE entries via LRU eviction (preserving SEEDED_TAG_CATEGORIES)
SEEDED_TAG_CATEGORIES = {
    "scenery": 0,
    "no_humans": 0,
    "1girl": 0,
    "1boy": 0,
    "solo": 0,
    "outdoors": 0,
    "sky": 0,
    "cloud": 0,
    "water": 0,
    "night": 0,
    "highres": 5,
    "absurdres": 5,
    "animated": 5,
    "video": 5,
    "original": 3,
}
MAX_TAG_CATEGORY_CACHE = 10000
TAG_CATEGORY_CACHE = OrderedDict(SEEDED_TAG_CATEGORIES)

# Post ID -> list of (tag_name, category_id) tuples ordered by Copyright -> Character -> Artist -> Meta -> General
# Bounded at MAX_POST_TAGS_CACHE entries via OrderedDict LRU eviction to prevent unbounded memory cycling
MAX_POST_TAGS_CACHE = 2500
POST_TAGS_CACHE = OrderedDict()

# Glossary Definitions for Logs Tab
LOG_GLOSSARY_ENTRIES = [
    ("[SERVER]", "Local Python HTTP proxy server lifecycle events, port binding (127.0.0.1:8088), and client batch dispatches."),
    ("[DOH]", "Cloudflare DNS-over-HTTPS (https://cloudflare-dns.com/dns-query via 1.1.1.1) hostname resolutions for danbooru.donmai.us and cdn.donmai.us."),
    ("[API]", "Authenticated requests sent to Danbooru's REST API (/posts.json) including page numbers, tags, and rate-limit fallbacks."),
    ("[FETCH]", "Shared tag-pool population, media deduplication across screens sharing identical tags, MP4 size filtering (>15 MB), and shuffling statistics."),
    ("[PROXY]", "Binary media streaming (/media) over the authenticated transport pipeline, magic-byte inspection, Range requests, and stream errors."),
    ("[AUTH]", "Credential loading, DPAPI encryption/decryption status, active transport engine (curl_cffi vs. stdlib DoH+SNI), and HTTP Basic Auth updates."),
    ("[CONFIG]", "Reading and writing persistent configuration files (config.json, project.json, saved_searches.json) in %APPDATA%."),
    ("[UI]", "Application Settings window, Display tab per-screen controls, Light/Dark mode theme switches, and pause interactions."),
    ("[SEARCH]", "Per-screen tag queries updated in the Display tab and saved/removed bookmark entries."),
    ("[SUGGEST]", "Live tag autocomplete and Danbooru category lookups executed against Danbooru's /tags.json endpoint."),
    ("[REFRESH]", "Immediate per-screen cache epoch increments triggered by pressing the refresh button or Shift+Enter."),
    ("[NAV]", "Display tab Previous (◀) and Next (▶) media queue actions dispatched to the selected wallpaper monitor."),
    ("[WEBVIEW]", "Synchronization of per-screen display properties, modes (Scroll, Polaroid, Slideshow, Masonry), and enabled states to WebView2."),
    ("[WIN32]", "Native Windows API desktop window attachment (Progman / WorkerW / SHELLDLL_DefView) and multi-monitor Z-order management."),
    ("[POLAROID]", "Polaroid mode actions such as triggering the 30-second cooldown Fill Screen burst."),
    ("[APP]", "Application-wide master pause/resume state changes, single-instance duplicate-launch Settings window handoff, and clean shutdown sequences."),
    ("[PING]", "Periodic heartbeat summary confirming active WebView2 wallpaper clients are polling /epoch."),
    ("[SECURITY]", "Localhost origin verification, URL path/PHP filtering, redirect host pinning, and binary magic-byte signature enforcement."),
    ("[PERF]", "Real-time CPU, RAM, and GPU telemetry events from the Resource Graph performance monitor."),
    ("[ERROR]", "Network timeouts, upstream HTTP errors, or unexpected exceptions with automatic exponential backoff."),
]

NAV_BUTTON_COOLDOWN_SEC = 1.0
PROP_SEQ = 1

MAX_POOL_POSTS = 600
MAX_SEEN_IDS = 1800
MAX_TAG_POOLS = 16

# Shared Tag Pools: canonical_pool_key -> {
#   "raw_tags": str, "page": int, "posts": list[dict], "seen_post_ids": set[int],
#   "seen_post_order": deque, "is_fetching": bool, "consecutive_failures": int,
#   "consecutive_empty_pages": int, "next_allowed_fetch_time": float,
#   "last_status": {"status": str, "page": int, "count": int}
# }
TAG_POOLS = OrderedDict()

# Per-Screen Runtime State: screen_id -> {
#   "epoch": int, "wallpaper_paused": bool, "nav_seq": int, "nav_action": str,
#   "last_nav_time": float, "seen_post_ids": set[int], "queued_tags": str | None,
#   "last_displayed_post_id": int, "last_displayed_tags": list[tuple[str, int]]
# }
SCREEN_RUNTIME_STATE = {}

LOG_HISTORY = deque(maxlen=500)

DATA_LOCK = threading.Lock()
FETCH_CONDITION = threading.Condition(DATA_LOCK)
LAST_API_CALL_TIME = 0.0

APP_PAUSED = False        # Master application pause (freezes display, stops proxy & API calls)

EPOCH_POLL_COUNT = 0
LAST_EPOCH_LOG_TIME = 0.0

IS_RUNNING = True

SUGGESTION_QUEUE = Queue(maxsize=1)
TAG_LOOKUP_QUEUE = Queue(maxsize=16)

TRAY_ICON = None
TK_ROOT = None
HTTP_SERVER = None
SETTINGS_DIALOG_INSTANCE = None
GLOSSARY_DIALOG_INSTANCE = None
RESOURCE_GRAPH_DIALOG_INSTANCE = None

# Runtime-only session memory for Application Settings tab and selected screen:
# Starts as None when the application first launches, and remembers the last tab/display
# whenever Application Settings is closed and reopened while the application is running.
_RUNTIME_LAST_SETTINGS_TAB = None
_RUNTIME_LAST_SELECTED_SCREEN_ID = None

CONNECTED_SCREENS = enumerate_connected_monitors()
WEBVIEW_WINDOWS = {}       # screen_id -> webview.Window
DESKTOP_HWNDS = {}         # screen_id -> int HWND
DESKTOP_INJECTED_SET = set()
_PROP_PUSH_LOCK = threading.Lock()
_PENDING_PROP_SCREENS = set()
_PENDING_SYNC_GEOMETRY = False
_PROP_PUSH_WORKER_ACTIVE = False
_LAST_SCREEN_ENABLED_STATE = {}
_JS_EVAL_LOCK = threading.Lock()
_JS_EVAL_QUEUE = deque(maxlen=128)
_JS_EVAL_WORKER_ACTIVE = False


def log_event(category, message):
    timestamp = time.strftime("%H:%M:%S")
    formatted_msg = f"[{timestamp}] [{category.upper()}] {message}"
    safe_console_print(formatted_msg)
    LOG_HISTORY.append(formatted_msg)
    if TK_ROOT and SETTINGS_DIALOG_INSTANCE and getattr(SETTINGS_DIALOG_INSTANCE, "is_open", False):
        try:
            TK_ROOT.after(0, lambda msg=formatted_msg: SETTINGS_DIALOG_INSTANCE.append_log(msg))
        except (tk.TclError, RuntimeError):
            pass


def build_danbooru_user_agent() -> str:
    """
    Constructs a compliant, descriptive User-Agent header following
    https://danbooru.donmai.us/wiki_pages/help:api
    """
    if USERNAME and USER_ID:
        return f"DanbooruWallpaperService/2.0 (by {USERNAME}; user #{USER_ID})"
    if USERNAME:
        return f"DanbooruWallpaperService/2.0 (by {USERNAME})"
    return "DanbooruWallpaperService/2.0 (Anonymous Client)"


def create_modern_tls_context() -> ssl.SSLContext:
    """Creates a hardened TLS 1.2/1.3 SSLContext with modern cipher suites for stdlib connections."""
    ctx = ssl.create_default_context()
    try:
        ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    except Exception:
        pass
    try:
        ctx.set_alpn_protocols(["http/1.1"])
    except Exception:
        pass
    return ctx


STDLIB_SSL_CONTEXT = create_modern_tls_context()


def _query_cloudflare_doh_direct(hostname: str) -> str:
    """
    Queries Cloudflare's public DoH endpoint (https://cloudflare-dns.com/dns-query)
    by connecting directly to Cloudflare's anycast IP (1.1.1.1 / 1.0.0.1) over TLS 1.3
    with SNI 'cloudflare-dns.com'. Works with zero third-party dependencies and cannot recurse.
    """
    query_path = f"/dns-query?{urllib.parse.urlencode({'name': hostname, 'type': 'A'})}"
    for cf_ip in CLOUDFLARE_DOH_IPS:
        raw_sock = None
        tls_sock = None
        try:
            raw_sock = socket.create_connection((cf_ip, 443), timeout=4.0)
            tls_sock = STDLIB_SSL_CONTEXT.wrap_socket(raw_sock, server_hostname="cloudflare-dns.com")
            req_lines = (
                f"GET {query_path} HTTP/1.1\r\n"
                f"Host: cloudflare-dns.com\r\n"
                f"Accept: application/dns-json\r\n"
                f"User-Agent: {build_danbooru_user_agent()}\r\n"
                f"Connection: close\r\n\r\n"
            )
            tls_sock.sendall(req_lines.encode("utf-8"))
            response_chunks = []
            total_read = 0
            max_doh_bytes = 65536
            while total_read < max_doh_bytes:
                data = tls_sock.recv(16384)
                if not data:
                    break
                response_chunks.append(data)
                total_read += len(data)
            raw_response = b"".join(response_chunks)
            if b"\r\n\r\n" in raw_response:
                header_bytes, body_bytes = raw_response.split(b"\r\n\r\n", 1)
                first_line = header_bytes.split(b"\r\n", 1)[0].decode("latin-1", errors="ignore")
                if " 200 " in first_line:
                    # Handle chunked transfer encoding if present
                    if b"transfer-encoding: chunked" in header_bytes.lower():
                        decoded_body = bytearray()
                        idx = 0
                        while idx < len(body_bytes):
                            crlf_pos = body_bytes.find(b"\r\n", idx)
                            if crlf_pos == -1:
                                break
                            chunk_len_hex = body_bytes[idx:crlf_pos].split(b";", 1)[0].strip()
                            if not chunk_len_hex:
                                break
                            try:
                                chunk_len = int(chunk_len_hex, 16)
                            except ValueError:
                                break
                            if chunk_len <= 0 or chunk_len > max_doh_bytes:
                                break
                            start_data = crlf_pos + 2
                            if start_data + chunk_len > len(body_bytes):
                                break
                            decoded_body.extend(body_bytes[start_data:start_data + chunk_len])
                            idx = start_data + chunk_len + 2
                        body_bytes = bytes(decoded_body)

                    payload = json.loads(body_bytes.decode("utf-8", errors="replace"))
                    for ans in payload.get("Answer", []):
                        if ans.get("type") == 1 and ans.get("data"):
                            candidate_ip = str(ans["data"]).strip()
                            if is_public_unicast_ipv4(candidate_ip):
                                return candidate_ip
        except Exception:
            pass
        finally:
            if tls_sock is not None:
                try:
                    tls_sock.close()
                except Exception:
                    pass
            elif raw_sock is not None:
                try:
                    raw_sock.close()
                except Exception:
                    pass
    return ""


def resolve_hostname_doh(hostname: str) -> str:
    """
    Resolves Danbooru and CDN hostnames via Cloudflare DNS-over-HTTPS (DoH)
    (https://cloudflare-dns.com/dns-query) to bypass ISP plain-text DNS blocks/poisoning.
    Strictly validates that resolved IPs are globally routable public IPv4 addresses.
    """
    if not hostname:
        return ""

    now = time.time()
    with DOH_LOCK:
        cached = DOH_CACHE.get(hostname)
        if cached and cached[1] > now and is_public_unicast_ipv4(cached[0]):
            DOH_CACHE.move_to_end(hostname)
            return cached[0]
        elif cached:
            DOH_CACHE.pop(hostname, None)

    resolved_ip = _query_cloudflare_doh_direct(hostname)
    if not resolved_ip:
        try:
            fallback_ip = socket.gethostbyname(hostname)
            if is_public_unicast_ipv4(fallback_ip):
                resolved_ip = fallback_ip
        except Exception:
            resolved_ip = ""

    if resolved_ip and is_public_unicast_ipv4(resolved_ip):
        with DOH_LOCK:
            expired_hosts = [h for h, (_, exp) in DOH_CACHE.items() if exp <= now]
            for h in expired_hosts:
                DOH_CACHE.pop(h, None)
            DOH_CACHE[hostname] = (resolved_ip, now + DOH_CACHE_TTL)
            DOH_CACHE.move_to_end(hostname)
            while len(DOH_CACHE) > MAX_DOH_CACHE_ENTRIES:
                DOH_CACHE.popitem(last=False)
        log_event("doh", f"Resolved {hostname} -> {resolved_ip} via Cloudflare DoH")
        return resolved_ip

    return ""


def build_curl_resolve_list(hostnames=None) -> list:
    """
    Builds libcurl CURLOPT_RESOLVE list entries (["host:443:ip", "host:80:ip"])
    using Cloudflare DoH resolution so TLS SNI, certificate verification, and
    HTTP/2 multiplexing work natively over the DoH IP.
    """
    targets = hostnames if hostnames is not None else ALLOWED_MEDIA_HOSTS
    entries = []
    for host in targets:
        if not host:
            continue
        ip_addr = resolve_hostname_doh(host)
        if ip_addr:
            entries.append(f"{host}:443:{ip_addr}")
            entries.append(f"{host}:80:{ip_addr}")
    return entries


# =============================================================================
# 3B. STANDARD-LIBRARY DoH + TLS SNI FALLBACK & UNIFIED HYBRID SESSION
# =============================================================================
class DoHSNIHTTPSConnection(http.client.HTTPSConnection):
    """
    Custom HTTPSConnection that connects the TCP socket to the Cloudflare DoH-resolved IP
    while passing the original hostname to `server_hostname` during the TLS handshake.
    """
    def __init__(self, host, port=None, **kwargs):
        super().__init__(host, port=port, **kwargs)

    def connect(self):
        target_host = (self._tunnel_host if self._tunnel_host else self.host or "").lower()
        target_port = self._tunnel_port if self._tunnel_host else self.port

        if target_host not in ALLOWED_MEDIA_HOSTS:
            raise PermissionError(f"Blocked outbound connection to unauthorized host: {target_host}")

        connect_ip = resolve_hostname_doh(target_host)
        if not connect_ip or not is_public_unicast_ipv4(connect_ip):
            raise OSError(f"Secure DoH/DNS resolution failed or returned non-public IPv4 for {target_host}")

        self.sock = socket.create_connection(
            (connect_ip, target_port),
            self.timeout,
            self.source_address,
        )
        if self._tunnel_host:
            self._tunnel()

        self.sock = self._context.wrap_socket(
            self.sock,
            server_hostname=target_host,
        )


class DoHSNIHTTPSHandler(urllib.request.HTTPSHandler):
    def __init__(self, context=None):
        super().__init__(context=context or STDLIB_SSL_CONTEXT)

    def https_open(self, req):
        return self.do_open(DoHSNIHTTPSConnection, req, context=self._context)


class SafeDoHRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Validates redirect targets against ALLOWED_MEDIA_HOSTS and FORBIDDEN_URL_TOKENS while preserving DoH+SNI routing."""
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        parsed = urllib.parse.urlparse(newurl)
        host = (parsed.hostname or "").lower()
        if parsed.scheme != "https" or host not in ALLOWED_MEDIA_HOSTS:
            raise urllib.error.HTTPError(
                newurl, 403, f"Redirect to unauthorized host blocked: {host}", headers, fp
            )
        lower_path_and_query = f"{parsed.path or ''}?{parsed.query or ''}".lower()
        for bad_tok in FORBIDDEN_URL_TOKENS:
            if bad_tok in lower_path_and_query:
                raise urllib.error.HTTPError(
                    newurl, 403, f"Redirect contains forbidden token ({bad_tok})", headers, fp
                )
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class StdlibResponseAdapter:
    """Provides a curl_cffi / requests-compatible Response interface over a urllib response."""
    def __init__(self, status_code: int, headers: dict, raw_fp=None, body_bytes: bytes = None):
        self.status_code = status_code
        self.headers = headers or {}
        self._raw_fp = raw_fp
        self._body_bytes = body_bytes

    def _read_all(self) -> bytes:
        if self._body_bytes is None:
            if self._raw_fp is not None:
                try:
                    self._body_bytes = self._raw_fp.read()
                finally:
                    self.close()
            else:
                self._body_bytes = b""
            enc = (self.headers.get("Content-Encoding") or self.headers.get("content-encoding") or "").lower()
            if "gzip" in enc and self._body_bytes:
                try:
                    self._body_bytes = gzip.decompress(self._body_bytes)
                except Exception:
                    pass
            elif "deflate" in enc and self._body_bytes:
                try:
                    self._body_bytes = zlib.decompress(self._body_bytes)
                except Exception:
                    pass
        return self._body_bytes

    @property
    def content(self) -> bytes:
        return self._read_all()

    def json(self):
        raw = self._read_all()
        return json.loads(raw.decode("utf-8", errors="replace"))

    def iter_content(self, chunk_size: int = 65536):
        if self._raw_fp is not None:
            try:
                while True:
                    chunk = self._raw_fp.read(chunk_size)
                    if not chunk:
                        break
                    yield chunk
            finally:
                self.close()
        elif self._body_bytes:
            for i in range(0, len(self._body_bytes), chunk_size):
                yield self._body_bytes[i:i + chunk_size]

    def close(self):
        if self._raw_fp is not None:
            try:
                self._raw_fp.close()
            except Exception:
                pass
            self._raw_fp = None


def iter_response_chunks(resp, chunk_size: int = 65536):
    """
    Safely yields binary chunks from either a curl_cffi Response or a StdlibResponseAdapter
    without buffering the entire media stream into RAM at once.
    """
    if isinstance(resp, StdlibResponseAdapter):
        for chunk in resp.iter_content(chunk_size=chunk_size):
            if chunk:
                yield chunk
        return

    if hasattr(resp, "iter_content"):
        try:
            for chunk in resp.iter_content(chunk_size=chunk_size):
                if chunk:
                    yield chunk
        except TypeError:
            for chunk in resp.iter_content():
                if chunk:
                    yield chunk
        return

    content = getattr(resp, "content", None)
    if content:
        for i in range(0, len(content), chunk_size):
            yield content[i:i + chunk_size]


class StdlibDoHSession:
    """
    Drop-in fallback session when `curl_cffi` is not installed or fails at runtime.
    Routes all HTTPS traffic over Cloudflare DoH IPs with proper TLS 1.3 SNI and HTTP Basic Auth.
    """
    def __init__(self):
        self.headers = {}
        self.auth = None
        self._opener = urllib.request.build_opener(
            DoHSNIHTTPSHandler(STDLIB_SSL_CONTEXT),
            SafeDoHRedirectHandler(),
        )

    def get(self, url: str, params: dict = None, headers: dict = None, stream: bool = False, timeout: float = 15.0, auth: tuple = None, **kwargs):
        if params:
            qs = urllib.parse.urlencode(params)
            sep = "&" if "?" in url else "?"
            url = f"{url}{sep}{qs}"

        merged_headers = dict(self.headers)
        if headers:
            merged_headers.update(headers)

        effective_auth = auth if auth is not None else self.auth
        parsed_host = (urllib.parse.urlparse(url).hostname or "").lower()
        if effective_auth and parsed_host == "danbooru.donmai.us" and isinstance(effective_auth, tuple) and len(effective_auth) == 2:
            user, key = effective_auth
            if user and key:
                token = base64.b64encode(f"{user}:{key}".encode("utf-8")).decode("ascii")
                merged_headers["Authorization"] = f"Basic {token}"

        req = urllib.request.Request(url, headers=merged_headers, method="GET")
        try:
            res = self._opener.open(req, timeout=timeout)
            status = getattr(res, "status", 200) or 200
            resp_headers = {k: v for k, v in res.headers.items()}
            if stream:
                return StdlibResponseAdapter(status, resp_headers, raw_fp=res)
            body = res.read()
            res.close()
            return StdlibResponseAdapter(status, resp_headers, body_bytes=body)
        except urllib.error.HTTPError as e:
            err_headers = {k: v for k, v in e.headers.items()} if e.headers else {}
            try:
                err_body = e.read()
            except Exception:
                err_body = b""
            finally:
                try:
                    e.close()
                except Exception:
                    pass
            return StdlibResponseAdapter(e.code or 500, err_headers, body_bytes=err_body)

    def close(self):
        pass


class HybridDoHSession:
    """
    Unified transport wrapper that uses `curl_cffi` (Chrome HTTP/2 + DoH) when available
    and automatically falls back at runtime to `StdlibDoHSession` (TLS 1.3 + DoH SNI)
    if `curl_cffi` raises any initialization or per-request error.
    """
    def __init__(self, headers: dict = None, auth: tuple = None):
        self._lock = threading.RLock()
        self.headers = dict(headers or {})
        self.auth = auth
        self._stdlib_session = StdlibDoHSession()
        self._stdlib_session.headers.update(self.headers)
        self._stdlib_session.auth = self.auth
        self._curl_session = None
        self._last_resolve_tuple = ()
        self._init_curl_session()

    def _init_curl_session(self):
        global CURL_CFFI_AVAILABLE
        if not CURL_CFFI_AVAILABLE or curl_requests is None:
            return
        with self._lock:
            try:
                base_kwargs = {"impersonate": "chrome"}
                if CurlHttpVersion is not None:
                    base_kwargs["http_version"] = CurlHttpVersion.V2_0

                c_sess = None
                if CurlOpt is not None:
                    with DOH_LOCK:
                        now = time.time()
                        cached_entries = [
                            f"{h}:{p}:{ip}"
                            for h, (ip, exp) in DOH_CACHE.items()
                            if exp > now and ip and is_public_unicast_ipv4(ip)
                            for p in (443, 80)
                        ]
                    if cached_entries:
                        try:
                            c_sess = curl_requests.Session(
                                **base_kwargs,
                                curl_options={CurlOpt.RESOLVE: cached_entries},
                            )
                            self._last_resolve_tuple = tuple(sorted(cached_entries))
                        except TypeError:
                            c_sess = None

                if c_sess is None:
                    c_sess = curl_requests.Session(**base_kwargs)

                c_sess.headers.update(self.headers)
                self._curl_session = c_sess
            except Exception as e:
                log_event("auth", f"curl_cffi session init failed ({e}); falling back to stdlib DoH+SNI transport.")
                CURL_CFFI_AVAILABLE = False
                self._curl_session = None

    def _apply_doh_to_curl_session(self, target_host: str):
        """Resolves target_host via Cloudflare DoH and attaches CURLOPT_RESOLVE to the session in a thread-safe manner."""
        if not target_host or target_host not in ALLOWED_MEDIA_HOSTS:
            return
        ip_addr = resolve_hostname_doh(target_host)
        if not ip_addr or not is_public_unicast_ipv4(ip_addr):
            raise OSError(f"Secure DoH/DNS resolution failed or returned non-public IPv4 for {target_host}")
        if self._curl_session is None or CurlOpt is None:
            return
        resolve_entries = build_curl_resolve_list(ALLOWED_MEDIA_HOSTS)
        if not resolve_entries:
            return
        resolve_sig = tuple(sorted(resolve_entries))
        with self._lock:
            if self._curl_session is None:
                return
            try:
                if hasattr(self._curl_session, "_curl_options") and isinstance(self._curl_session._curl_options, dict):
                    self._curl_session._curl_options[CurlOpt.RESOLVE] = resolve_entries
                elif hasattr(self._curl_session, "curl_options") and isinstance(self._curl_session.curl_options, dict):
                    self._curl_session.curl_options[CurlOpt.RESOLVE] = resolve_entries
                self._last_resolve_tuple = resolve_sig
            except Exception:
                pass

    def get(
        self,
        url: str,
        params: dict = None,
        headers: dict = None,
        stream: bool = False,
        timeout: float = 15.0,
        allow_redirects: bool = True,
    ):
        global CURL_CFFI_AVAILABLE
        current_url = url
        current_params = params
        max_hops = 3 if allow_redirects else 0

        for _ in range(max_hops + 1):
            parsed = urllib.parse.urlparse(current_url)
            target_host = (parsed.hostname or "").lower()
            if parsed.scheme != "https" or target_host not in ALLOWED_MEDIA_HOSTS:
                raise PermissionError(f"Blocked outbound request to unauthorized host: {target_host}")

            # Only send Danbooru Basic Auth to the primary API host, never to public CDN nodes
            req_auth = self.auth if target_host == "danbooru.donmai.us" else None
            merged_req_headers = dict(self.headers)
            if headers:
                merged_req_headers.update(headers)

            resp = None
            with self._lock:
                c_sess = self._curl_session if CURL_CFFI_AVAILABLE else None
            if c_sess is not None:
                try:
                    self._apply_doh_to_curl_session(target_host)

                    # Disable unchecked automatic redirects; validate each hop manually
                    resp = c_sess.get(
                        current_url,
                        params=current_params,
                        headers=merged_req_headers,
                        auth=req_auth,
                        stream=stream,
                        timeout=timeout,
                        allow_redirects=False,
                    )
                except Exception as e:
                    log_event(
                        "auth",
                        f"curl_cffi request failed ({e}); automatically switching to stdlib TLS 1.3 + DoH SNI fallback."
                    )
                    with self._lock:
                        CURL_CFFI_AVAILABLE = False
                        old_sess = self._curl_session
                        self._curl_session = None
                    if old_sess is not None:
                        try:
                            old_sess.close()
                        except Exception:
                            pass

            if resp is None:
                resp = self._stdlib_session.get(
                    current_url,
                    params=current_params,
                    headers=merged_req_headers,
                    auth=req_auth,
                    stream=stream,
                    timeout=timeout,
                    allow_redirects=allow_redirects,
                )
                return resp

            status = getattr(resp, "status_code", 200) or 200
            if allow_redirects and status in (301, 302, 303, 307, 308):
                loc = resp.headers.get("Location") or resp.headers.get("location")
                try:
                    resp.close()
                except Exception:
                    pass
                if not loc:
                    return resp
                next_url = urllib.parse.urljoin(current_url, loc)
                next_parsed = urllib.parse.urlparse(next_url)
                next_host = (next_parsed.hostname or "").lower()
                if next_parsed.scheme != "https" or next_host not in ALLOWED_MEDIA_HOSTS:
                    log_event("security", f"Blocked redirect to unauthorized host: {next_url}")
                    raise PermissionError(f"Redirect to unauthorized host blocked: {next_host}")
                lower_path_and_query = f"{next_parsed.path or ''}?{next_parsed.query or ''}".lower()
                for bad_tok in FORBIDDEN_URL_TOKENS:
                    if bad_tok in lower_path_and_query:
                        log_event("security", f"Blocked redirect containing forbidden token ({bad_tok}): {next_url}")
                        raise PermissionError(f"Redirect contains forbidden token ({bad_tok})")
                current_url = next_url
                current_params = None
                continue

            return resp

        raise RuntimeError("Maximum redirect hops exceeded")

    def close(self):
        with self._lock:
            old_curl = self._curl_session
            self._curl_session = None
            old_stdlib = self._stdlib_session
        if old_curl is not None:
            try:
                old_curl.close()
            except Exception:
                pass
        if old_stdlib is not None:
            try:
                old_stdlib.close()
            except Exception:
                pass


def rebuild_http2_session():
    """
    Creates/recreates the cookie-free HybridDoHSession (curl_cffi HTTP/2 with automatic
    runtime fallback to StdlibDoHSession).
    """
    global HTTP2_SESSION
    with SESSION_LOCK:
        if HTTP2_SESSION is not None:
            try:
                HTTP2_SESSION.close()
            except Exception:
                pass

        default_headers = {
            "User-Agent": build_danbooru_user_agent(),
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Accept-Language": "en-US,en;q=0.9",
        }
        auth_tuple = (USERNAME, API_KEY) if (USERNAME and API_KEY) else None
        HTTP2_SESSION = HybridDoHSession(headers=default_headers, auth=auth_tuple)
        return HTTP2_SESSION


def get_http2_session():
    with SESSION_LOCK:
        if HTTP2_SESSION is None:
            return rebuild_http2_session()
        return HTTP2_SESSION


def apply_credentials(user: str, uid: str, key: str):
    """
    Applies credentials entered in the Credentials tab of the Application Settings window.
    No default credentials are ever embedded in code.
    """
    global USERNAME, USER_ID, API_KEY
    USERNAME = (user or "").strip()
    USER_ID = (uid or "").strip()
    API_KEY = (key or "").strip()
    rebuild_http2_session()


def load_saved_searches():
    if os.path.exists(SAVED_SEARCHES_FILE):
        try:
            with open(SAVED_SEARCHES_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return [str(item).strip() for item in data if str(item).strip()]
        except Exception as e:
            log_event("config", f"Failed to load saved searches: {e}")
    return []


def store_saved_searches(searches):
    try:
        with open(SAVED_SEARCHES_FILE, "w", encoding="utf-8") as f:
            json.dump(searches, f, ensure_ascii=False, indent=2)
    except Exception as e:
        log_event("config", f"Failed to save searches: {e}")


def load_app_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                return {}
            if "CF_COOKIE" in data:
                data.pop("CF_COOKIE", None)
            raw_key = data.get("API_KEY", "")
            if raw_key:
                was_plaintext = not str(raw_key).startswith("dpapi:")
                data["API_KEY"] = dpapi_decrypt(str(raw_key))
                if was_plaintext and data["API_KEY"]:
                    store_app_config(data)
            return data
        except Exception as e:
            log_event("config", f"Failed to load app config: {e}")
    return {}


def store_app_config(config_data):
    try:
        to_save = dict(config_data)
        to_save.pop("CF_COOKIE", None)
        if to_save.get("API_KEY"):
            encrypted_key = dpapi_encrypt(str(to_save["API_KEY"]))
            if encrypted_key:
                to_save["API_KEY"] = encrypted_key
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(to_save, f, indent=2)
    except Exception as e:
        log_event("config", f"Failed to save app config: {e}")


def _normalize_display_mode_value(val: str) -> str:
    v = str(val or "scroll").strip().lower()
    if v in ("polaroid", "slideshow", "masonry", "scroll"):
        return v
    # Automatically migrate legacy primary mode name to "polaroid"
    if v.startswith("col"):
        return "polaroid"
    return "scroll"


def _normalize_masonry_layout_value(val: str) -> str:
    v = str(val or "mondrian").strip().lower()
    if v in ("rows", "row", "google_photos", "googlephotos", "google", "google photos"):
        return "rows"
    return "mondrian"


def _normalize_masonry_edge_fill_value(val: str) -> str:
    v = str(val or "blur").strip().lower()
    if v in ("black", "none", "off", "solid"):
        return "black"
    return "blur"


def _normalize_scroll_direction_value(val: str) -> str:
    v = str(val or "left").strip().lower()
    if v in ("left", "right", "up", "down"):
        return v
    return "left"


def _normalize_vsync_value(val) -> bool:
    if isinstance(val, bool):
        return val
    if isinstance(val, (int, float)):
        return bool(val)
    v = str(val if val is not None else "true").strip().lower()
    if v in ("false", "0", "off", "no", "disabled"):
        return False
    return True


PROJECT_CONFIG_LOCK = threading.RLock()
_CACHED_PROJECT_DATA = None


def _coerce_and_clamp_props_dict(props_dict: dict, def_props: dict):
    """Validates numeric slider ranges, boolean flags, and enforces the minsize <= maxsize invariant."""
    for k, schema in def_props.items():
        if k not in props_dict or not isinstance(props_dict[k], dict):
            continue
        val = props_dict[k].get("value", schema["value"])
        if schema.get("type") == "slider":
            try:
                num = float(val)
                num = max(float(schema["min"]), min(float(schema["max"]), num))
                prec = int(schema.get("precision", 0) or 0)
                is_float_slider = prec > 0 or isinstance(schema.get("step"), float) or isinstance(schema["value"], float)
                if is_float_slider:
                    rounded = round(num, max(1, prec))
                    props_dict[k]["value"] = int(rounded) if rounded.is_integer() and isinstance(schema["value"], int) else rounded
                else:
                    props_dict[k]["value"] = int(round(num))
            except (ValueError, TypeError):
                props_dict[k]["value"] = schema["value"]
        elif schema.get("type") == "bool":
            props_dict[k]["value"] = _normalize_vsync_value(val)
    min_s = props_dict.get("minsize", {}).get("value", 220)
    max_s = props_dict.get("maxsize", {}).get("value", 440)
    if isinstance(min_s, (int, float)) and isinstance(max_s, (int, float)) and min_s > max_s:
        props_dict["minsize"]["value"], props_dict["maxsize"]["value"] = max_s, min_s


def _normalize_project_dict_in_place(data: dict) -> dict:
    def_props = get_default_properties_dict()
    general_props = data.setdefault("general", {}).setdefault("properties", {})
    for k, v in def_props.items():
        if k not in general_props or not isinstance(general_props[k], dict):
            general_props[k] = json.loads(json.dumps(v))
        else:
            saved_val = general_props[k].get("value", v["value"])
            if k == "displaymode":
                saved_val = _normalize_display_mode_value(saved_val)
            elif k == "scrolldirection":
                saved_val = _normalize_scroll_direction_value(saved_val)
            elif k == "masonrylayout":
                saved_val = _normalize_masonry_layout_value(saved_val)
            elif k == "masonryedgefill":
                saved_val = _normalize_masonry_edge_fill_value(saved_val)
            elif k in ("vsync", "pausefullscreen"):
                saved_val = _normalize_vsync_value(saved_val)
            elif k == "searchtags":
                saved_val = str(saved_val if saved_val is not None else v["value"]).strip() or v["value"]
            merged_meta = json.loads(json.dumps(v))
            merged_meta["value"] = saved_val
            general_props[k] = merged_meta
    _coerce_and_clamp_props_dict(general_props, def_props)

    screens_dict = data.setdefault("screens", {})
    for s_id, s_cfg in list(screens_dict.items()):
        if not isinstance(s_cfg, dict):
            screens_dict[s_id] = {
                "enabled": (s_id == "screen_1"),
                "properties": json.loads(json.dumps(general_props)),
            }
            continue
        s_cfg["enabled"] = bool(s_cfg.get("enabled", s_id == "screen_1"))
        s_props = s_cfg.get("properties")
        if not isinstance(s_props, dict):
            s_props = {}
        for k, v in def_props.items():
            base_default = general_props.get(k, v)
            if k not in s_props or not isinstance(s_props[k], dict):
                s_props[k] = json.loads(json.dumps(base_default))
            else:
                saved_val = s_props[k].get("value", base_default["value"])
                if k == "displaymode":
                    saved_val = _normalize_display_mode_value(saved_val)
                elif k == "scrolldirection":
                    saved_val = _normalize_scroll_direction_value(saved_val)
                elif k == "masonrylayout":
                    saved_val = _normalize_masonry_layout_value(saved_val)
                elif k == "masonryedgefill":
                    saved_val = _normalize_masonry_edge_fill_value(saved_val)
                elif k in ("vsync", "pausefullscreen"):
                    saved_val = _normalize_vsync_value(saved_val)
                elif k == "searchtags":
                    saved_val = str(saved_val if saved_val is not None else base_default["value"]).strip() or base_default["value"]
                merged_meta = json.loads(json.dumps(v))
                merged_meta["value"] = saved_val
                s_props[k] = merged_meta
        _coerce_and_clamp_props_dict(s_props, def_props)
        s_cfg["properties"] = s_props
    return data


def load_project_json():
    global _CACHED_PROJECT_DATA
    with PROJECT_CONFIG_LOCK:
        if _CACHED_PROJECT_DATA is not None:
            return json.loads(json.dumps(_CACHED_PROJECT_DATA))
        if os.path.exists(PROJECT_JSON_FILE):
            try:
                with open(PROJECT_JSON_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    _normalize_project_dict_in_place(data)
                    _CACHED_PROJECT_DATA = json.loads(json.dumps(data))
                    return data
            except Exception as e:
                log_event("config", f"Failed to read project.json: {e}")
        default_copy = json.loads(json.dumps(DEFAULT_PROJECT_SCHEMA))
        _CACHED_PROJECT_DATA = json.loads(json.dumps(default_copy))
        return default_copy


def store_project_json(project_data):
    global _CACHED_PROJECT_DATA
    with PROJECT_CONFIG_LOCK:
        try:
            if isinstance(project_data, dict):
                _normalize_project_dict_in_place(project_data)
                _CACHED_PROJECT_DATA = json.loads(json.dumps(project_data))
            tmp_file = PROJECT_JSON_FILE + ".tmp"
            with open(tmp_file, "w", encoding="utf-8") as f:
                json.dump(project_data, f, indent=2)
            os.replace(tmp_file, PROJECT_JSON_FILE)
        except Exception as e:
            try:
                with open(PROJECT_JSON_FILE, "w", encoding="utf-8") as f:
                    json.dump(project_data, f, indent=2)
            except Exception as inner_e:
                log_event("config", f"Failed to save project.json: {e} / {inner_e}")


def is_screen_enabled(screen_id="screen_1") -> bool:
    """Fast-path read of a screen's enabled boolean without deep-copying the full project schema."""
    s_id = str(screen_id or "screen_1")
    with PROJECT_CONFIG_LOCK:
        if _CACHED_PROJECT_DATA is not None:
            screens_dict = _CACHED_PROJECT_DATA.get("screens", {})
            if s_id in screens_dict and isinstance(screens_dict[s_id], dict):
                return bool(screens_dict[s_id].get("enabled", s_id == "screen_1"))
            return s_id == "screen_1"
    sc_cfg = get_screen_config(s_id)
    return bool(sc_cfg.get("enabled", s_id == "screen_1"))


def get_screen_config(screen_id="screen_1"):
    """Returns {'enabled': bool, 'properties': dict} for the specified screen_id."""
    proj = load_project_json()
    base_props = proj.get("general", {}).get("properties", get_default_properties_dict())
    screens_dict = proj.get("screens", {})

    if screen_id in screens_dict and isinstance(screens_dict[screen_id], dict):
        sc = screens_dict[screen_id]
        enabled = bool(sc.get("enabled", screen_id == "screen_1"))
        merged_props = json.loads(json.dumps(base_props))
        for k, v in sc.get("properties", {}).items():
            if k in merged_props and isinstance(v, dict) and "value" in v:
                if k == "displaymode":
                    val = _normalize_display_mode_value(v["value"])
                elif k == "masonrylayout":
                    val = _normalize_masonry_layout_value(v["value"])
                elif k == "masonryedgefill":
                    val = _normalize_masonry_edge_fill_value(v["value"])
                else:
                    val = v["value"]
                merged_props[k]["value"] = val
            else:
                merged_props[k] = v
        return {"enabled": enabled, "properties": merged_props}

    return {
        "enabled": (screen_id == "screen_1"),
        "properties": json.loads(json.dumps(base_props)),
    }


def normalize_tag_query(raw_tags: str) -> str:
    """Normalizes whitespace on a tag query string while preserving tag tokens."""
    cleaned = " ".join(str(raw_tags or "").strip().split())
    return cleaned if cleaned else DEFAULT_TAGS


def canonical_pool_key(raw_tags: str) -> str:
    """Returns a case-insensitive canonical key so screens with identical tags share the same fetch pool."""
    tokens = [t.lower() for t in normalize_tag_query(raw_tags).split() if t]
    return " ".join(tokens) if tokens else DEFAULT_TAGS.lower()


def get_danbooru_tag_color(category_id: int, theme: str = None) -> str:
    """Returns the official Danbooru hex color for a tag category in the active theme."""
    active_theme = theme or CURRENT_THEME
    pal = DANBOORU_TAG_COLORS.get(active_theme, DANBOORU_TAG_COLORS["light"])
    return pal.get(int(category_id or 0), pal[0])


def cache_tag_category_locked(tag_name: str, category_id: int):
    """Thread-safely caches a tag's Danbooru category with bounded LRU eviction (requires DATA_LOCK)."""
    clean = str(tag_name or "").strip().lstrip("-~").lower()
    if not clean:
        return
    cat = int(category_id or 0)
    if cat not in (0, 1, 3, 4, 5):
        cat = 0
    TAG_CATEGORY_CACHE[clean] = cat
    TAG_CATEGORY_CACHE.move_to_end(clean)
    while len(TAG_CATEGORY_CACHE) > MAX_TAG_CATEGORY_CACHE:
        oldest_key, _ = TAG_CATEGORY_CACHE.popitem(last=False)
        if oldest_key in SEEDED_TAG_CATEGORIES:
            TAG_CATEGORY_CACHE[oldest_key] = SEEDED_TAG_CATEGORIES[oldest_key]


def cache_post_tags_locked(post_id: int, tags_list: list):
    """Thread-safely caches categorized post tags with bounded LRU eviction (requires DATA_LOCK)."""
    pid = int(post_id or 0)
    if pid <= 0 or not tags_list:
        return
    POST_TAGS_CACHE[pid] = list(tags_list)
    POST_TAGS_CACHE.move_to_end(pid)
    while len(POST_TAGS_CACHE) > MAX_POST_TAGS_CACHE:
        POST_TAGS_CACHE.popitem(last=False)


def _lookup_cached_tag_category_unlocked(raw_token: str, default=None):
    """Internal helper for callers that already hold DATA_LOCK."""
    clean = str(raw_token or "").strip().lstrip("-~").lower()
    if not clean:
        return 0
    if clean.startswith(("rating:", "order:", "ordfav:", "score:", "width:", "height:", "mpixels:", "filesize:", "filetype:", "id:", "date:", "pool:", "parent:", "child:", "source:", "status:")):
        return 5
    return TAG_CATEGORY_CACHE.get(clean, default)


def lookup_cached_tag_category(raw_token: str, default=None):
    """Thread-safely looks up a tag token's Danbooru category (stripping leading '-' or '~' operators)."""
    clean = str(raw_token or "").strip().lstrip("-~").lower()
    if not clean:
        return 0
    if clean.startswith(("rating:", "order:", "ordfav:", "score:", "width:", "height:", "mpixels:", "filesize:", "filetype:", "id:", "date:", "pool:", "parent:", "child:", "source:", "status:")):
        return 5
    with DATA_LOCK:
        return TAG_CATEGORY_CACHE.get(clean, default)


def get_screen_runtime_state(screen_id: str) -> dict:
    """Returns or initializes the per-screen runtime state dictionary (must be called under DATA_LOCK or thread-safely)."""
    st = SCREEN_RUNTIME_STATE.get(screen_id)
    if st is None:
        st = {
            "epoch": 1,
            "wallpaper_paused": False,
            "fullscreen_paused": False,
            "disconnected_paused": False,
            "nav_seq": 0,
            "nav_action": "",
            "last_nav_time": 0.0,
            "seen_post_ids": set(),
            "queued_tags": None,
            "last_displayed_post_id": 0,
            "last_displayed_tags": [],
        }
        SCREEN_RUNTIME_STATE[screen_id] = st
    return st


def is_screen_effectively_paused(screen_id: str) -> bool:
    """Returns True if the application is globally paused or the specified screen is paused (manually, fullscreen, or disconnected)."""
    if APP_PAUSED:
        return True
    with DATA_LOCK:
        st = get_screen_runtime_state(screen_id)
        return bool(
            st.get("wallpaper_paused", False)
            or st.get("fullscreen_paused", False)
            or st.get("disconnected_paused", False)
        )


def get_or_create_tag_pool_locked(raw_tags: str) -> tuple[str, dict]:
    """Returns (pool_key, pool_dict) for the normalized tag query with bounded pool eviction (must be called with DATA_LOCK held)."""
    norm_tags = normalize_tag_query(raw_tags)
    pkey = canonical_pool_key(norm_tags)
    pool = TAG_POOLS.get(pkey)
    if pool is None:
        while len(TAG_POOLS) >= MAX_TAG_POOLS:
            evicted = False
            for old_key, old_pool in list(TAG_POOLS.items()):
                if not old_pool.get("is_fetching", False):
                    TAG_POOLS.pop(old_key, None)
                    evicted = True
                    break
            if not evicted:
                break
        pool = {
            "raw_tags": norm_tags,
            "page": 1,
            "posts": [],
            "seen_post_ids": set(),
            "seen_post_order": deque(),
            "is_fetching": False,
            "consecutive_failures": 0,
            "consecutive_empty_pages": 0,
            "next_allowed_fetch_time": 0.0,
            "last_status": {"status": "idle", "page": 0, "count": 0},
        }
        TAG_POOLS[pkey] = pool
    else:
        pool["raw_tags"] = norm_tags
        TAG_POOLS.move_to_end(pkey)
    return pkey, pool


def get_screen_tags(screen_id="screen_1") -> str:
    """Returns the configured search tags for the specified screen."""
    sc_cfg = get_screen_config(screen_id)
    raw = sc_cfg.get("properties", {}).get("searchtags", {}).get("value", DEFAULT_TAGS)
    return normalize_tag_query(raw)


def set_screen_tags_in_project_json(screen_id: str, new_tags: str):
    """Persists the screen's searchtags value into project.json."""
    norm_tags = normalize_tag_query(new_tags)
    proj = load_project_json()
    base_props = proj.setdefault("general", {}).setdefault("properties", get_default_properties_dict())
    screens_dict = proj.setdefault("screens", {})
    sc_entry = screens_dict.setdefault(screen_id, {
        "enabled": (screen_id == "screen_1"),
        "properties": json.loads(json.dumps(base_props)),
    })
    s_props = sc_entry.setdefault("properties", json.loads(json.dumps(base_props)))
    s_props.setdefault("searchtags", {"order": 0, "text": "Search Tags", "type": "textinput", "value": norm_tags})[
        "value"
    ] = norm_tags
    if screen_id == "screen_1":
        base_props.setdefault("searchtags", {"order": 0, "text": "Search Tags", "type": "textinput", "value": norm_tags})[
            "value"
        ] = norm_tags
    store_project_json(proj)


def is_any_enabled_screen_using_pool(pool_key: str) -> bool:
    """Returns True if at least one enabled and unpaused screen is currently configured with tags matching pool_key."""
    for s in get_connected_screens_snapshot():
        sid = s["id"]
        sc_cfg = get_screen_config(sid)
        if not sc_cfg.get("enabled", False):
            continue
        if is_screen_effectively_paused(sid):
            continue
        with DATA_LOCK:
            st = get_screen_runtime_state(sid)
            q_tags = st.get("queued_tags")
        active_tags = q_tags if q_tags else sc_cfg.get("properties", {}).get("searchtags", {}).get("value", DEFAULT_TAGS)
        if canonical_pool_key(active_tags) == pool_key:
            return True
    return False


def _js_eval_worker():
    """
    Single-flight background worker that executes queued win.evaluate_js calls sequentially
    so rapid UI interactions never spawn competing threads on the WinForms Control.Invoke semaphore.
    """
    global _JS_EVAL_WORKER_ACTIVE
    while True:
        with _JS_EVAL_LOCK:
            if not _JS_EVAL_QUEUE:
                _JS_EVAL_WORKER_ACTIVE = False
                return
            win, js_code, log_cat, log_msg = _JS_EVAL_QUEUE.popleft()

        if win:
            try:
                win.evaluate_js(js_code)
                if log_cat and log_msg:
                    log_event(log_cat, log_msg)
            except Exception as e:
                if log_cat:
                    log_event(log_cat, f"JS evaluation warning: {e}")


def _async_evaluate_js(win, js_code: str, log_cat: str = None, log_msg: str = None):
    """Queues win.evaluate_js onto the single-flight daemon worker so the Tkinter UI thread never blocks."""
    global _JS_EVAL_WORKER_ACTIVE
    if not win:
        return
    with _JS_EVAL_LOCK:
        # Coalesce consecutive identical JS evaluations for the same window to preserve queue capacity
        if _JS_EVAL_QUEUE and _JS_EVAL_QUEUE[-1][0] is win and _JS_EVAL_QUEUE[-1][1] == js_code:
            _JS_EVAL_QUEUE[-1] = (win, js_code, log_cat, log_msg)
        else:
            _JS_EVAL_QUEUE.append((win, js_code, log_cat, log_msg))
        if not _JS_EVAL_WORKER_ACTIVE:
            _JS_EVAL_WORKER_ACTIVE = True
            threading.Thread(target=_js_eval_worker, daemon=True).start()


def _property_push_worker():
    """
    Single-flight background worker that coalesces rapid property updates and applies them
    without blocking the Tkinter mainloop or firing redundant synchronous Win32 SetWindowPos calls.
    """
    global _PROP_PUSH_WORKER_ACTIVE, _PENDING_SYNC_GEOMETRY
    while True:
        with _PROP_PUSH_LOCK:
            if not _PENDING_PROP_SCREENS:
                _PROP_PUSH_WORKER_ACTIVE = False
                return
            if "__ALL__" in _PENDING_PROP_SCREENS:
                batch_sids = list(WEBVIEW_WINDOWS.keys())
                target_geom_sid = None
            else:
                batch_sids = list(_PENDING_PROP_SCREENS)
                target_geom_sid = batch_sids[0] if len(batch_sids) == 1 else None
            _PENDING_PROP_SCREENS.clear()
            do_geom = _PENDING_SYNC_GEOMETRY
            _PENDING_SYNC_GEOMETRY = False

        if do_geom:
            try:
                sync_all_screens_z_order_and_geometry(target_geom_sid)
            except Exception as e:
                log_event("win32", f"Geometry sync warning: {e}")

        for sid in batch_sids:
            win = WEBVIEW_WINDOWS.get(sid)
            if not win:
                continue
            try:
                sc_cfg = get_screen_config(sid)
                enabled = sc_cfg["enabled"]
                props = sc_cfg["properties"]
                payload = json.dumps(props)
                enabled_js = "true" if enabled else "false"
                js_code = (
                    f"if (window.setScreenEnabled) {{ window.setScreenEnabled({enabled_js}); }} "
                    f"if (window.wallpaperPropertyListener && window.wallpaperPropertyListener.applyUserProperties) {{ "
                    f"window.wallpaperPropertyListener.applyUserProperties({payload}); }}"
                )
                win.evaluate_js(js_code)
                log_event("webview", f"Applied display properties to {sid} (enabled={enabled}).")
                if enabled:
                    ensure_screen_tag_pool_populated_async(sid)
            except Exception as e:
                log_event("webview", f"Failed to push properties to {sid}: {e}")


def push_properties_to_webview(target_screen_id=None, sync_geometry=False):
    """
    Coalesces and asynchronously pushes per-screen properties to WebView2 instances
    on a single-flight background thread, preventing cross-thread deadlocks between
    Tkinter and WebView2 when rapidly toggling Masonry layouts or sliders.
    """
    global PROP_SEQ, _PROP_PUSH_WORKER_ACTIVE, _PENDING_SYNC_GEOMETRY
    with DATA_LOCK:
        PROP_SEQ += 1

    with _PROP_PUSH_LOCK:
        if target_screen_id:
            _PENDING_PROP_SCREENS.add(target_screen_id)
        else:
            _PENDING_PROP_SCREENS.add("__ALL__")
        if sync_geometry:
            _PENDING_SYNC_GEOMETRY = True
        if not _PROP_PUSH_WORKER_ACTIVE:
            _PROP_PUSH_WORKER_ACTIVE = True
            threading.Thread(target=_property_push_worker, daemon=True).start()


def push_pause_states_to_webviews(target_screen_id=None):
    """Immediately synchronizes master APP_PAUSED and effective per-screen pause state (manual, fullscreen, or disconnected) to target or all screens."""
    app_p = "true" if APP_PAUSED else "false"
    target_items = (
        [(target_screen_id, WEBVIEW_WINDOWS.get(target_screen_id))]
        if target_screen_id
        else list(WEBVIEW_WINDOWS.items())
    )
    for sid, win in target_items:
        if not win:
            continue
        with DATA_LOCK:
            st = get_screen_runtime_state(sid)
            wp_paused = bool(
                st.get("wallpaper_paused", False)
                or st.get("fullscreen_paused", False)
                or st.get("disconnected_paused", False)
            )
        wp_p = "true" if wp_paused else "false"
        js_code = f"if (window.applyPauseStates) {{ window.applyPauseStates({app_p}, {wp_p}); }}"
        _async_evaluate_js(win, js_code)


def trigger_fill_screen_on_webview(screen_id):
    """Triggers the Polaroid Fill Screen burst on the specified screen."""
    win = WEBVIEW_WINDOWS.get(screen_id)
    if win:
        _async_evaluate_js(
            win,
            "if (window.triggerFillPolaroidScreen) { window.triggerFillPolaroidScreen(); }",
            log_cat="polaroid",
            log_msg=f"Triggered Fill Screen burst on {screen_id}.",
        )


def trigger_navigation_on_screen(screen_id: str, action: str) -> bool:
    """
    Triggers 'prev' (requeue last shown file to front of queue) or 'next' (immediately play next queued file)
    strictly on the specified screen. Enforces a 1.0-second per-screen cooldown so rapid button presses
    under high-stress 36-tile Masonry layouts never flood WebView2 IPC or overlap 3D transitions.
    """
    if action not in ("prev", "next"):
        return False
    sc_cfg = get_screen_config(screen_id)
    if not sc_cfg.get("enabled", False):
        return False
    now = time.monotonic()
    with DATA_LOCK:
        st = get_screen_runtime_state(screen_id)
        if (now - st["last_nav_time"]) < NAV_BUTTON_COOLDOWN_SEC:
            return False
        st["last_nav_time"] = now
        st["nav_seq"] += 1
        st["nav_action"] = action
        seq_val = st["nav_seq"]

    win = WEBVIEW_WINDOWS.get(screen_id)
    js_fn = "triggerPreviousMedia" if action == "prev" else "triggerNextMedia"
    js_code = f"if (window.{js_fn}) {{ window.{js_fn}({seq_val}); }}"
    if win:
        _async_evaluate_js(win, js_code)
    if action == "prev":
        log_event("nav", f"[{screen_id}] Requeued last shown file to the front of the display queue (Previous).")
    else:
        log_event("nav", f"[{screen_id}] Immediately triggered next queued file (Next).")
    return True


_initial_cfg = load_app_config()
CURRENT_THEME = "dark" if _initial_cfg.get("theme") == "dark" else "light"
apply_credentials(
    _initial_cfg.get("USERNAME", ""),
    _initial_cfg.get("USER_ID", ""),
    _initial_cfg.get("API_KEY", ""),
)


# =============================================================================
# 4. ICON GENERATION & DANBOORU API LOGIC (HYBRID HTTP/2 + DoH + SHARED TAG POOLS)
# =============================================================================
def create_cardboard_box_icon():
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    box_base = (194, 142, 86, 255)
    box_dark = (150, 105, 60, 255)
    box_interior = (115, 78, 42, 255)
    flap_color = (212, 162, 106, 255)
    tape_color = (130, 88, 50, 255)

    draw.polygon([(14, 25), (32, 33), (50, 25), (32, 18)], fill=box_interior)
    draw.polygon([(14, 25), (32, 33), (32, 57), (14, 49)], fill=box_dark)
    draw.polygon([(32, 33), (50, 25), (50, 49), (32, 57)], fill=box_base)
    draw.line([(32, 33), (32, 57)], fill=tape_color, width=2)
    draw.polygon([(14, 25), (32, 33), (25, 23), (8, 17)], fill=flap_color)
    draw.line([(14, 25), (8, 17)], fill=box_dark, width=1)
    draw.polygon([(32, 33), (50, 25), (56, 17), (39, 23)], fill=flap_color)
    draw.line([(50, 25), (56, 17)], fill=box_dark, width=1)
    draw.polygon([(14, 25), (32, 18), (28, 11), (11, 16)], fill=flap_color)
    draw.polygon([(32, 18), (50, 25), (53, 16), (36, 11)], fill=flap_color)
    return img


def apply_app_icon(root):
    try:
        box_img = create_cardboard_box_icon()
        tk_icon = ImageTk.PhotoImage(box_img)
        root._app_icon = tk_icon
        root.iconphoto(True, tk_icon)
    except Exception as e:
        log_event("ui", f"Could not set window icon: {e}")


def track_pool_post_id_locked(pool: dict, post_id: int):
    seen_set = pool["seen_post_ids"]
    seen_order = pool["seen_post_order"]
    if post_id not in seen_set:
        seen_set.add(post_id)
        seen_order.append(post_id)
        if len(seen_order) > MAX_SEEN_IDS:
            oldest = seen_order.popleft()
            seen_set.discard(oldest)


def extract_and_cache_post_tags_locked(post_dict: dict) -> list[tuple[str, int]]:
    """
    Extracts categorized tags from a Danbooru post dictionary in standard Danbooru hierarchy:
    Copyright (3) -> Character (4) -> Artist (1) -> Meta (5) -> General (0).
    Updates TAG_CATEGORY_CACHE and POST_TAGS_CACHE.
    """
    pid = int(post_dict.get("id") or 0)
    categorized = []
    seen_tags = set()

    field_Category_pairs = (
        ("tag_string_copyright", 3),
        ("tag_string_character", 4),
        ("tag_string_artist", 1),
        ("tag_string_meta", 5),
        ("tag_string_general", 0),
    )
    for field_name, cat_id in field_Category_pairs:
        raw_str = post_dict.get(field_name) or ""
        if isinstance(raw_str, str) and raw_str.strip():
            for t in raw_str.strip().split():
                t_clean = t.strip()
                if not t_clean:
                    continue
                t_lower = t_clean.lower()
                cache_tag_category_locked(t_lower, cat_id)
                if t_lower not in seen_tags:
                    seen_tags.add(t_lower)
                    categorized.append((t_clean, cat_id))

    unknown_fallback_tags = []
    if not categorized:
        fallback_str = post_dict.get("tag_string") or ""
        if isinstance(fallback_str, str) and fallback_str.strip():
            for t in fallback_str.strip().split():
                t_clean = t.strip()
                if not t_clean:
                    continue
                t_lower = t_clean.lower()
                cat_id = TAG_CATEGORY_CACHE.get(t_lower, None)
                if cat_id is None:
                    cat_id = 0
                    if len(unknown_fallback_tags) < 60:
                        unknown_fallback_tags.append(t_lower)
                if t_lower not in seen_tags:
                    seen_tags.add(t_lower)
                    categorized.append((t_clean, cat_id))

    if pid > 0 and categorized:
        cache_post_tags_locked(pid, categorized)

    if unknown_fallback_tags:
        try:
            TAG_LOOKUP_QUEUE.put_nowait(unknown_fallback_tags)
        except Exception:
            pass

    return categorized


def _execute_danbooru_request(tags: str, page_num: int):
    if APP_PAUSED:
        raise RuntimeError("Application is currently paused.")

    params = {
        "tags": tags,
        "limit": 100,
        "page": page_num,
    }
    if USERNAME and API_KEY:
        params["login"] = USERNAME
        params["api_key"] = API_KEY

    url = "https://danbooru.donmai.us/posts.json"
    transport_label = "curl_cffi HTTP/2 + DoH" if CURL_CFFI_AVAILABLE else "stdlib TLS 1.3 + DoH SNI"
    log_event("api", f"Requesting Page {page_num} for tags: '{tags}' via {transport_label}")

    sess = get_http2_session()
    resp = sess.get(
        url,
        params=params,
        headers={
            "User-Agent": build_danbooru_user_agent(),
            "Accept": "application/json",
        },
        timeout=15,
    )
    if resp.status_code == 422:
        raise ValueError("HTTP_422_TAG_LIMIT")
    if resp.status_code == 401:
        raise PermissionError("HTTP 401 Unauthorized: Check Username and API Key in Credentials tab.")
    if resp.status_code == 429:
        raise RuntimeError("HTTP 429 Too Many Requests: Rate limit reached, backing off.")
    if resp.status_code >= 400:
        raise RuntimeError(f"Danbooru API HTTP {resp.status_code}")

    return resp.json()


def fetch_danbooru_page(tags, page_num):
    global LAST_API_CALL_TIME

    if APP_PAUSED:
        return []

    with DATA_LOCK:
        now = time.time()
        wait_for = max(0.0, (LAST_API_CALL_TIME + MIN_API_INTERVAL) - now)
        LAST_API_CALL_TIME = now + wait_for

    if wait_for > 0:
        time.sleep(wait_for)

    if APP_PAUSED:
        return []

    try:
        data = _execute_danbooru_request(tags, page_num)
    except ValueError as e:
        tokens = [t for t in tags.split() if t]
        if str(e) == "HTTP_422_TAG_LIMIT" and len(tokens) > 2:
            fallback_tags = " ".join(tokens[:2])
            log_event(
                "api",
                f"HTTP 422 (2-tag limit on current account tier). Retrying with '{fallback_tags}'"
            )
            time.sleep(1.0)
            data = _execute_danbooru_request(fallback_tags, page_num)
        else:
            raise

    if isinstance(data, dict):
        error_msg = data.get("message", data.get("error", "API Error"))
        raise ValueError(f"Danbooru error: {error_msg}")
    if not isinstance(data, list):
        raise ValueError("Invalid format received from Danbooru.")
    return data


def fetch_tag_suggestions(query_prefix):
    """Queries Danbooru's /tags.json endpoint and returns (name, post_count, category) tuples."""
    if APP_PAUSED:
        return []
    clean_prefix = str(query_prefix or "").strip().lstrip("-~")
    if not clean_prefix:
        return []
    params = {
        "search[name_matches]": f"*{clean_prefix}*",
        "search[order]": "count",
        "limit": 6,
    }
    if USERNAME and API_KEY:
        params["login"] = USERNAME
        params["api_key"] = API_KEY

    url = "https://danbooru.donmai.us/tags.json"
    try:
        sess = get_http2_session()
        resp = sess.get(
            url,
            params=params,
            headers={
                "User-Agent": build_danbooru_user_agent(),
                "Accept": "application/json",
            },
            timeout=5,
        )
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, list):
                results = []
                with DATA_LOCK:
                    for item in data:
                        name = item.get("name")
                        if not name:
                            continue
                        cat = int(item.get("category", 0) or 0)
                        if cat not in DANBOORU_TAG_COLORS["light"]:
                            cat = 0
                        cache_tag_category_locked(name, cat)
                        results.append((name, int(item.get("post_count", 0) or 0), cat))
                return results[:5]
    except Exception as e:
        log_event("suggest", f"Suggestion fetch failed: {e}")
    return []


def resolve_unknown_tag_categories(tag_names: list[str]) -> bool:
    """Resolves Danbooru tag categories in batch for tags typed into the search bar that are not yet cached."""
    if APP_PAUSED or not tag_names:
        return False
    clean_list = []
    with DATA_LOCK:
        for t in tag_names:
            c = str(t or "").strip().lstrip("-~").lower()
            if c and c not in TAG_CATEGORY_CACHE and not c.startswith(("rating:", "order:", "ordfav:", "score:", "width:", "height:")):
                clean_list.append(c)
    if not clean_list:
        return False

    params = {
        "search[name_comma]": ",".join(clean_list[:15]),
        "limit": 20,
    }
    if USERNAME and API_KEY:
        params["login"] = USERNAME
        params["api_key"] = API_KEY

    url = "https://danbooru.donmai.us/tags.json"
    updated_any = False
    try:
        sess = get_http2_session()
        resp = sess.get(
            url,
            params=params,
            headers={
                "User-Agent": build_danbooru_user_agent(),
                "Accept": "application/json",
            },
            timeout=5,
        )
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, list):
                with DATA_LOCK:
                    for item in data:
                        name = (item.get("name") or "").strip().lower()
                        if name:
                            cat = int(item.get("category", 0) or 0)
                            if cat not in DANBOORU_TAG_COLORS["light"]:
                                cat = 0
                            cache_tag_category_locked(name, cat)
                            updated_any = True
    except Exception:
        pass
    return updated_any


def suggestion_worker_loop():
    while IS_RUNNING:
        try:
            item = SUGGESTION_QUEUE.get(timeout=0.4)
            if item:
                fragment, req_id = item
                if not APP_PAUSED:
                    results = fetch_tag_suggestions(fragment)
                    if IS_RUNNING and TK_ROOT and SETTINGS_DIALOG_INSTANCE and getattr(SETTINGS_DIALOG_INSTANCE, "is_open", False):
                        if req_id == getattr(SETTINGS_DIALOG_INSTANCE, "_suggest_req_id", -1):
                            try:
                                TK_ROOT.after(0, lambda r=results, q=req_id: SETTINGS_DIALOG_INSTANCE.display_suggestions(r, q))
                            except (tk.TclError, RuntimeError):
                                pass
                SUGGESTION_QUEUE.task_done()
        except Empty:
            pass

        try:
            unknown_tokens = TAG_LOOKUP_QUEUE.get_nowait()
            if unknown_tokens and not APP_PAUSED:
                if resolve_unknown_tag_categories(unknown_tokens):
                    if IS_RUNNING and TK_ROOT and SETTINGS_DIALOG_INSTANCE and getattr(SETTINGS_DIALOG_INSTANCE, "is_open", False):
                        try:
                            TK_ROOT.after(
                                0,
                                lambda: (
                                    SETTINGS_DIALOG_INSTANCE._recolor_search_input_tags(),
                                    SETTINGS_DIALOG_INSTANCE._render_displayed_media_tags_box(force=True),
                                )
                                if SETTINGS_DIALOG_INSTANCE and getattr(SETTINGS_DIALOG_INSTANCE, "is_open", False)
                                else None,
                            )
                        except (tk.TclError, RuntimeError):
                            pass
            TAG_LOOKUP_QUEUE.task_done()
        except Empty:
            pass


def fill_tag_pool(raw_tags: str, wait_if_busy: bool = False, force_reset: bool = False):
    """
    Populates the shared TAG_POOLS entry for raw_tags.
    - If multiple enabled screens share the same tags, they share this single pool and never issue duplicate requests.
    - If no enabled screen uses this pool, does not fetch media.
    """
    if APP_PAUSED:
        return

    norm_tags = normalize_tag_query(raw_tags)
    pkey = canonical_pool_key(norm_tags)

    if not is_any_enabled_screen_using_pool(pkey):
        return

    with FETCH_CONDITION:
        _, pool = get_or_create_tag_pool_locked(norm_tags)
        if force_reset:
            pool["page"] = 1
            pool["posts"].clear()
            pool["seen_post_ids"].clear()
            pool["seen_post_order"].clear()
            pool["consecutive_failures"] = 0
            pool["consecutive_empty_pages"] = 0
            pool["next_allowed_fetch_time"] = 0.0

        if pool["is_fetching"]:
            if wait_if_busy:
                FETCH_CONDITION.wait(timeout=20.0)
            return

        now = time.time()
        if not force_reset and now < pool["next_allowed_fetch_time"]:
            return

        pool["is_fetching"] = True
        target_tags = pool["raw_tags"]
        target_page = pool["page"]

    try:
        if not is_any_enabled_screen_using_pool(pkey) or APP_PAUSED:
            return

        posts = fetch_danbooru_page(target_tags, target_page)

        if APP_PAUSED:
            return

        if not posts:
            if target_page == 1:
                with DATA_LOCK:
                    _, pool = get_or_create_tag_pool_locked(target_tags)
                    pool["consecutive_failures"] += 1
                    backoff = min(30, max(5, 2 ** pool["consecutive_failures"]))
                    pool["next_allowed_fetch_time"] = time.time() + backoff
                    pool["last_status"] = {"status": "error", "page": 1, "count": 0}
                log_event("error", f"No posts found for '{target_tags}'. Backing off {backoff}s...")
                return

            with DATA_LOCK:
                _, pool = get_or_create_tag_pool_locked(target_tags)
                pool["page"] = 1
                pool["consecutive_empty_pages"] = 0
                pool["seen_post_ids"].clear()
                pool["seen_post_order"].clear()
            target_page = 1
            posts = fetch_danbooru_page(target_tags, target_page)
            if APP_PAUSED:
                return
            if not posts:
                with DATA_LOCK:
                    _, pool = get_or_create_tag_pool_locked(target_tags)
                    pool["consecutive_failures"] += 1
                    backoff = min(30, max(5, 2 ** pool["consecutive_failures"]))
                    pool["next_allowed_fetch_time"] = time.time() + backoff
                    pool["last_status"] = {"status": "error", "page": 1, "count": 0}
                log_event("error", f"No posts found on wrap-around Page 1 for '{target_tags}'. Backing off {backoff}s...")
                return

        new_items = []
        skipped_large_mp4 = 0
        with DATA_LOCK:
            _, pool = get_or_create_tag_pool_locked(target_tags)
            for p in posts:
                if not isinstance(p, dict):
                    continue
                pid = p.get("id")
                file_url = p.get("file_url")
                ext = p.get("file_ext", "").lower()
                file_size = int(p.get("file_size") or 0)

                if not pid or pid in pool["seen_post_ids"] or not file_url or ext not in ALLOWED_EXTENSIONS:
                    continue

                is_safe_url, verified_ext, _ = validate_safe_media_url(file_url, ext)
                if not is_safe_url:
                    continue

                if verified_ext == "mp4" and (file_size <= 0 or file_size > MAX_MP4_FILE_SIZE_BYTES):
                    skipped_large_mp4 += 1
                    continue
                if verified_ext != "mp4" and file_size > MAX_IMAGE_FILE_SIZE_BYTES:
                    continue

                track_pool_post_id_locked(pool, pid)
                extract_and_cache_post_tags_locked(p)

                safe_url = urllib.parse.quote(file_url, safe="")
                local_media_endpoint = (
                    f"http://127.0.0.1:{PORT}/media?url={safe_url}&ext={verified_ext}&size={file_size}"
                )
                p["media_url"] = local_media_endpoint
                p["proxy_url"] = local_media_endpoint
                new_items.append(p)

            random.shuffle(new_items)
            pool["posts"].extend(new_items)
            if len(pool["posts"]) > MAX_POOL_POSTS:
                pool["posts"] = pool["posts"][-MAX_POOL_POSTS:]

            pool["page"] = target_page + 1
            pool["last_status"] = {"status": "ok", "page": target_page, "count": len(new_items)}
            pool["consecutive_failures"] = 0

            if len(new_items) == 0:
                pool["consecutive_empty_pages"] += 1
                if pool["consecutive_empty_pages"] >= 2:
                    pool["next_allowed_fetch_time"] = time.time() + 10.0
                    log_event("fetch", f"Multiple pages returned 0 usable items for '{target_tags}'. Cooling down 10s.")
                else:
                    pool["next_allowed_fetch_time"] = time.time() + MIN_API_INTERVAL
            else:
                pool["consecutive_empty_pages"] = 0
                pool["next_allowed_fetch_time"] = time.time() + MIN_API_INTERVAL

        extra_msg = f" (filtered {skipped_large_mp4} oversized MP4s)" if skipped_large_mp4 else ""
        log_event(
            "fetch",
            f"Fetched and shuffled {len(new_items)} media items (Page {target_page}) into shared pool '{target_tags}'{extra_msg}."
        )
    except Exception as e:
        with DATA_LOCK:
            _, pool = get_or_create_tag_pool_locked(norm_tags)
            pool["consecutive_failures"] += 1
            backoff = min(30, max(4, 2 ** pool["consecutive_failures"]))
            pool["next_allowed_fetch_time"] = time.time() + backoff
            pool["last_status"] = {"status": "error", "page": pool["page"], "count": 0}
        log_event("error", f"Fetch error for '{norm_tags}': {e}. Backing off {backoff}s...")
    finally:
        with FETCH_CONDITION:
            _, pool = get_or_create_tag_pool_locked(norm_tags)
            pool["is_fetching"] = False
            FETCH_CONDITION.notify_all()


def ensure_screen_tag_pool_populated_async(screen_id: str, force_reset: bool = False):
    """Spawns a background fetch for screen_id's tag pool only if screen_id is enabled, unpaused (or force_reset), and its pool is empty."""
    if APP_PAUSED:
        return
    sc_cfg = get_screen_config(screen_id)
    if not sc_cfg.get("enabled", False):
        return
    if not force_reset and is_screen_effectively_paused(screen_id):
        return
    tags = sc_cfg.get("properties", {}).get("searchtags", {}).get("value", DEFAULT_TAGS)
    with DATA_LOCK:
        st = get_screen_runtime_state(screen_id)
        _, pool = get_or_create_tag_pool_locked(tags)
        if force_reset:
            st["epoch"] += 1
            st["seen_post_ids"].clear()
            pool["next_allowed_fetch_time"] = 0.0
            should_fetch = not pool["is_fetching"]
        else:
            should_fetch = (len(pool["posts"]) == 0 and not pool["is_fetching"])
    if should_fetch and not is_screen_effectively_paused(screen_id):
        threading.Thread(target=fill_tag_pool, args=(tags, False, force_reset), daemon=True).start()


def ensure_all_enabled_screen_pools_populated(force_reset: bool = False):
    """Starts background fetches for unique tag pools used by enabled, unpaused screens (deduplicating shared tags)."""
    if APP_PAUSED:
        return
    seen_pools = set()
    for s in get_connected_screens_snapshot():
        sid = s["id"]
        sc_cfg = get_screen_config(sid)
        if not sc_cfg.get("enabled", False):
            continue
        if is_screen_effectively_paused(sid):
            continue
        tags = sc_cfg.get("properties", {}).get("searchtags", {}).get("value", DEFAULT_TAGS)
        pkey = canonical_pool_key(tags)
        with DATA_LOCK:
            st = get_screen_runtime_state(sid)
            if force_reset:
                st["epoch"] += 1
                st["seen_post_ids"].clear()
        if pkey in seen_pools:
            continue
        seen_pools.add(pkey)
        with DATA_LOCK:
            _, pool = get_or_create_tag_pool_locked(tags)
            if force_reset:
                pool["next_allowed_fetch_time"] = 0.0
                should_fetch = not pool["is_fetching"]
            else:
                should_fetch = (len(pool["posts"]) == 0 and not pool["is_fetching"])
        if should_fetch:
            threading.Thread(target=fill_tag_pool, args=(tags, False, force_reset), daemon=True).start()


# =============================================================================
# 5. HTTP SERVER & LOCAL /media STREAMING PROXY (HYBRID HTTP/2 + DoH)
# =============================================================================
class ReusableThreadingHTTPServer(ThreadingHTTPServer):
    """
    Multi-threaded local HTTP proxy server bound exclusively to 127.0.0.1:8088.
    - On Windows, sets allow_reuse_address = False and applies SO_EXCLUSIVEADDRUSE
      before binding so a second OS process can never silently bind over port 8088.
    - All connected monitors (screen_1, screen_2, etc.) inside the running process
      connect concurrently as HTTP clients to this single server and share the
      deduplicated in-memory TAG_POOLS dictionary without extra API fetches.
    """
    allow_reuse_address = (os.name != "nt")

    def server_bind(self):
        if os.name == "nt" and hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            try:
                self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            except OSError:
                pass
        super().server_bind()


class ProxyHandler(BaseHTTPRequestHandler):
    def _is_authorized_local_request(self):
        origin = self.headers.get("Origin")
        sec_site = self.headers.get("Sec-Fetch-Site")
        if origin and origin not in ALLOWED_LOCAL_ORIGINS:
            log_event("security", f"Blocked unauthorized cross-origin request from Origin: {origin}")
            return False
        if sec_site and sec_site not in ("same-origin", "none"):
            log_event("security", f"Blocked external browser request (Sec-Fetch-Site: {sec_site})")
            return False
        return True

    def do_OPTIONS(self):
        if not self._is_authorized_local_request():
            self.send_response(403)
            self.send_header("Connection", "close")
            self.end_headers()
            return
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", f"http://127.0.0.1:{PORT}")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Range")
        self.send_header("Connection", "close")
        self.end_headers()

    def do_GET(self):
        global EPOCH_POLL_COUNT, LAST_EPOCH_LOG_TIME

        if not self._is_authorized_local_request():
            self.send_response(403)
            self.send_header("Connection", "close")
            self.end_headers()
            return

        parsed_url = urllib.parse.urlparse(self.path)
        path_only = parsed_url.path
        query_params = urllib.parse.parse_qs(parsed_url.query)
        screen_id = query_params.get("screen", ["screen_1"])[0]

        if path_only == "/show_settings":
            if self.client_address[0] in ("127.0.0.1", "::1") and TK_ROOT:
                try:
                    TK_ROOT.after(0, open_settings_dialog_window)
                except Exception:
                    pass
            try:
                ok_body = b'{"ok":true}'
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(ok_body)))
                self.send_header("Cache-Control", "no-store")
                self.send_header("Connection", "close")
                self.end_headers()
                self.wfile.write(ok_body)
            except Exception:
                pass
            return

        if path_only in ("/", "/index.html"):
            try:
                with open(BUNDLED_HTML_FILE, "rb") as f:
                    html_bytes = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(html_bytes)))
                self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
                self.send_header("Referrer-Policy", "no-referrer")
                self.send_header("X-Frame-Options", "DENY")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.send_header("Cross-Origin-Resource-Policy", "same-origin")
                self.send_header(
                    "Content-Security-Policy",
                    "default-src 'self'; img-src 'self' blob: data:; media-src 'self' blob:; "
                    "script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; "
                    "connect-src 'self'; object-src 'none'; frame-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none';"
                )
                self.send_header("Connection", "close")
                self.end_headers()
                self.wfile.write(html_bytes)
            except Exception as e:
                log_event("server", f"Error serving index.html: {e}")
                self.send_response(500)
                self.end_headers()
            return

        if path_only == "/report_shown":
            post_id_str = query_params.get("post_id", ["0"])[0]
            try:
                post_id = int(post_id_str or 0)
            except ValueError:
                post_id = 0
            raw_tags = query_params.get("tags", [""])[0]

            tags_list = []
            unknown_for_lookup = []
            with DATA_LOCK:
                st = get_screen_runtime_state(screen_id)
                if post_id > 0:
                    tags_list = list(POST_TAGS_CACHE.get(post_id, []))
                if not tags_list and raw_tags:
                    seen_t = set()
                    for tok in raw_tags.split():
                        clean_t = tok.strip()
                        if not clean_t or clean_t in seen_t:
                            continue
                        seen_t.add(clean_t)
                        cat = _lookup_cached_tag_category_unlocked(clean_t, default=None)
                        if cat is None:
                            cat = 0
                            unknown_for_lookup.append(clean_t)
                        tags_list.append((clean_t, cat))
                    if post_id > 0 and tags_list:
                        cache_post_tags_locked(post_id, tags_list)

                if post_id > 0 or tags_list:
                    st["last_displayed_post_id"] = post_id
                    if tags_list:
                        st["last_displayed_tags"] = tags_list

            if unknown_for_lookup:
                try:
                    TAG_LOOKUP_QUEUE.put_nowait(unknown_for_lookup)
                except Exception:
                    pass

            if (post_id > 0 or tags_list) and TK_ROOT and SETTINGS_DIALOG_INSTANCE and getattr(SETTINGS_DIALOG_INSTANCE, "is_open", False):
                try:
                    TK_ROOT.after(
                        0,
                        lambda sid=screen_id, pid=post_id, tl=tags_list: SETTINGS_DIALOG_INSTANCE.on_screen_media_displayed(
                            sid, pid, tl
                        ),
                    )
                except (tk.TclError, RuntimeError):
                    pass

            try:
                ok_body = b'{"ok":true}'
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(ok_body)))
                self.send_header("Cache-Control", "no-store")
                self.send_header("Connection", "close")
                self.end_headers()
                self.wfile.write(ok_body)
            except Exception:
                pass
            return

        if path_only == "/properties":
            try:
                sc_cfg = get_screen_config(screen_id)
                with DATA_LOCK:
                    st = get_screen_runtime_state(screen_id)
                    wp_paused = bool(
                        st.get("wallpaper_paused", False)
                        or st.get("fullscreen_paused", False)
                        or st.get("disconnected_paused", False)
                    )
                payload = {
                    "enabled": sc_cfg["enabled"],
                    "properties": sc_cfg["properties"],
                    "app_paused": APP_PAUSED,
                    "wallpaper_paused": wp_paused,
                }
                props_body = json.dumps(payload).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(props_body)))
                self.send_header("X-Content-Type-Options", "nosniff")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Connection", "close")
                self.end_headers()
                self.wfile.write(props_body)
            except Exception:
                pass
            return

        if path_only == "/epoch":
            now = time.time()
            should_log_ping = False
            poll_count_snapshot = 0
            elapsed_snapshot = 0
            enabled_flag = is_screen_enabled(screen_id)

            with DATA_LOCK:
                if LAST_EPOCH_LOG_TIME == 0.0:
                    LAST_EPOCH_LOG_TIME = now

                st = get_screen_runtime_state(screen_id)
                effective_wp_paused = bool(
                    st.get("wallpaper_paused", False)
                    or st.get("fullscreen_paused", False)
                    or st.get("disconnected_paused", False)
                )
                EPOCH_POLL_COUNT += 1
                res_body = json.dumps({
                    "epoch": st["epoch"],
                    "enabled": enabled_flag,
                    "app_paused": APP_PAUSED,
                    "wallpaper_paused": effective_wp_paused,
                    "nav_seq": st["nav_seq"],
                    "nav_action": st["nav_action"],
                    "prop_seq": PROP_SEQ,
                }).encode("utf-8")

                elapsed = now - LAST_EPOCH_LOG_TIME
                if elapsed >= 60.0:
                    should_log_ping = True
                    poll_count_snapshot = EPOCH_POLL_COUNT
                    elapsed_snapshot = int(elapsed)
                    EPOCH_POLL_COUNT = 0
                    LAST_EPOCH_LOG_TIME = now

            if should_log_ping and not APP_PAUSED:
                log_event("ping", f"Client polled /epoch ({poll_count_snapshot} times in last {elapsed_snapshot}s)")

            try:
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Connection", "close")
                self.end_headers()
                self.wfile.write(res_body)
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, OSError):
                pass
            return

        if path_only == "/api":
            sc_cfg = get_screen_config(screen_id)
            if is_screen_effectively_paused(screen_id) or not sc_cfg.get("enabled", False):
                try:
                    empty_body = b"[]"
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(empty_body)))
                    self.send_header("X-Content-Type-Options", "nosniff")
                    self.send_header("Connection", "close")
                    self.end_headers()
                    self.wfile.write(empty_body)
                except Exception:
                    pass
                return

            # Promote any queued tags for this screen if its unseen pool is exhausted
            configured_tags = sc_cfg.get("properties", {}).get("searchtags", {}).get("value", DEFAULT_TAGS)
            promoted_tags = None
            with DATA_LOCK:
                st = get_screen_runtime_state(screen_id)
                if st.get("queued_tags"):
                    promoted_tags = st["queued_tags"]
                    st["queued_tags"] = None
                    st["seen_post_ids"].clear()

            if promoted_tags:
                configured_tags = promoted_tags
                set_screen_tags_in_project_json(screen_id, configured_tags)

            norm_tags = normalize_tag_query(configured_tags)
            log_event("server", f"Client '{screen_id}' requested batch from /api (tags: '{norm_tags}')")

            try:
                with DATA_LOCK:
                    _, pool = get_or_create_tag_pool_locked(norm_tags)
                    st = get_screen_runtime_state(screen_id)
                    screen_seen = st["seen_post_ids"]
                    unseen_available = [p for p in pool["posts"] if p.get("id") and p.get("id") not in screen_seen]
                    needs_blocking_fill = (len(unseen_available) == 0)

                if needs_blocking_fill:
                    fill_tag_pool(norm_tags, wait_if_busy=True, force_reset=False)

                batch = []
                batch_target = 30
                seed_first_post = None

                with DATA_LOCK:
                    _, pool = get_or_create_tag_pool_locked(norm_tags)
                    st = get_screen_runtime_state(screen_id)
                    screen_seen = st["seen_post_ids"]
                    unseen_candidates = [p for p in pool["posts"] if p.get("id") and p.get("id") not in screen_seen]

                    # If this screen has seen all currently cached posts in the shared pool and a fetch didn't add more,
                    # cycle screen_seen so playback remains continuous while background pagination continues.
                    if not unseen_candidates and pool["posts"]:
                        screen_seen.clear()
                        unseen_candidates = list(pool["posts"])

                    for candidate in unseen_candidates[:batch_target]:
                        cid = candidate.get("id")
                        if cid:
                            screen_seen.add(cid)
                            if len(screen_seen) > 1400:
                                screen_seen.clear()
                                screen_seen.add(cid)
                        batch.append(candidate)

                    random.shuffle(batch)
                    if batch and not st["last_displayed_tags"]:
                        first_pid = int(batch[0].get("id") or 0)
                        first_tags = list(POST_TAGS_CACHE.get(first_pid, []))
                        if first_pid > 0 and first_tags:
                            st["last_displayed_post_id"] = first_pid
                            st["last_displayed_tags"] = first_tags
                            seed_first_post = (first_pid, first_tags)

                    active_epoch = st["epoch"]
                    remaining_unseen = sum(1 for p in pool["posts"] if p.get("id") and p.get("id") not in screen_seen)
                    now = time.time()
                    needs_background_refill = (
                        remaining_unseen < 25
                        and not pool["is_fetching"]
                        and now >= pool["next_allowed_fetch_time"]
                    )

                if seed_first_post and TK_ROOT and SETTINGS_DIALOG_INSTANCE and getattr(SETTINGS_DIALOG_INSTANCE, "is_open", False):
                    f_pid, f_tags = seed_first_post
                    try:
                        TK_ROOT.after(
                            0,
                            lambda sid=screen_id, pid=f_pid, tl=f_tags: SETTINGS_DIALOG_INSTANCE.on_screen_media_displayed(
                                sid, pid, tl
                            ),
                        )
                    except (tk.TclError, RuntimeError):
                        pass

                if needs_background_refill and not APP_PAUSED:
                    threading.Thread(target=fill_tag_pool, args=(norm_tags, False, False), daemon=True).start()

                response_body = json.dumps(batch).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(response_body)))
                self.send_header("X-Danbooru-Epoch", str(active_epoch))
                self.send_header("X-Content-Type-Options", "nosniff")
                self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
                self.send_header("Connection", "close")
                self.end_headers()
                self.wfile.write(response_body)

            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, OSError):
                pass
            except Exception as e:
                log_event("error", f"API dispatch error: {e}")
                try:
                    err_payload = json.dumps([]).encode("utf-8")
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Connection", "close")
                    self.end_headers()
                    self.wfile.write(err_payload)
                except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, OSError):
                    pass
            return

        if path_only in ("/media", "/image"):
            if APP_PAUSED:
                self.send_response(503)
                self.send_header("Connection", "close")
                self.end_headers()
                return

            target_url = query_params.get("url", [None])[0]
            ext_hint = query_params.get("ext", [""])[0].lower()
            size_hint_str = query_params.get("size", ["0"])[0]

            if not target_url:
                self.send_response(400)
                self.send_header("Connection", "close")
                self.end_headers()
                return

            is_safe_url, verified_ext, reject_reason = validate_safe_media_url(target_url, ext_hint)
            if not is_safe_url:
                log_event("security", f"Blocked unsafe /media URL ({reject_reason}): {target_url}")
                self.send_response(403)
                self.send_header("Connection", "close")
                self.end_headers()
                return

            is_mp4 = verified_ext == "mp4"
            max_allowed_bytes = MAX_MP4_FILE_SIZE_BYTES if is_mp4 else MAX_IMAGE_FILE_SIZE_BYTES

            try:
                if int(size_hint_str) > max_allowed_bytes:
                    log_event("proxy", f"Filtered oversized media ({size_hint_str} bytes > {max_allowed_bytes}): {target_url}")
                    self.send_response(413)
                    self.send_header("Connection", "close")
                    self.end_headers()
                    return
            except ValueError:
                pass

            req_headers = {
                "User-Agent": build_danbooru_user_agent(),
                "Referer": "https://danbooru.donmai.us/",
                "Accept": "image/avif,image/webp,image/apng,image/*,video/mp4,video/*;q=0.9,*/*;q=0.8",
            }
            forwarded_range = None
            range_start = 0
            client_requested_short_end = None
            if is_mp4:
                client_range = (self.headers.get("Range") or "").strip()
                m_range = re.match(r"^bytes=(\d+)-(\d*)$", client_range)
                if m_range:
                    range_start = int(m_range.group(1))
                    range_end_str = m_range.group(2)
                    if range_start == 0:
                        if range_end_str and int(range_end_str) < 63:
                            client_requested_short_end = int(range_end_str)
                            forwarded_range = "bytes=0-65535"
                        else:
                            forwarded_range = client_range
                        req_headers["Range"] = forwarded_range
                    else:
                        if not is_mp4_url_verified(target_url):
                            # Preflight byte-0 magic-byte verification so mid-stream Range requests stay 206 Partial Content
                            probe_resp = None
                            try:
                                probe_headers = dict(req_headers)
                                probe_headers["Range"] = "bytes=0-63"
                                probe_resp = get_http2_session().get(
                                    target_url,
                                    headers=probe_headers,
                                    stream=True,
                                    timeout=10,
                                    allow_redirects=True,
                                )
                                if probe_resp.status_code in (200, 206):
                                    probe_buf = bytearray()
                                    for p_chunk in iter_response_chunks(probe_resp, chunk_size=64):
                                        if p_chunk:
                                            probe_buf.extend(p_chunk)
                                            if len(probe_buf) >= 32:
                                                break
                                    p_ok, p_mime, _ = verify_media_magic_bytes(bytes(probe_buf), is_range_continuation=False)
                                    if p_ok and p_mime == "video/mp4":
                                        mark_mp4_url_verified(target_url)
                            except Exception:
                                pass
                            finally:
                                if probe_resp is not None:
                                    try:
                                        probe_resp.close()
                                    except Exception:
                                        pass
                        if is_mp4_url_verified(target_url):
                            forwarded_range = client_range
                            req_headers["Range"] = forwarded_range
                        else:
                            range_start = 0

            headers_sent = False
            resp = None
            try:
                sess = get_http2_session()
                resp = sess.get(
                    target_url,
                    headers=req_headers,
                    stream=True,
                    timeout=20,
                    allow_redirects=True,
                )
                status_code = resp.status_code or 200

                if status_code >= 400:
                    log_event("proxy", f"Upstream media HTTP {status_code} for {target_url}")
                    self.send_response(status_code)
                    self.send_header("Connection", "close")
                    self.end_headers()
                    return

                content_len_str = resp.headers.get("Content-Length") or resp.headers.get("content-length")
                content_range = resp.headers.get("Content-Range") or resp.headers.get("content-range")

                total_res_bytes = None
                if content_range:
                    m_total = re.search(r"/(\d+)$", content_range.strip())
                    if m_total:
                        try:
                            total_res_bytes = int(m_total.group(1))
                            if total_res_bytes > max_allowed_bytes:
                                log_event(
                                    "proxy",
                                    f"Filtered oversized Content-Range resource ({total_res_bytes:,} bytes > {max_allowed_bytes:,}): {target_url}"
                                )
                                self.send_response(413)
                                self.send_header("Connection", "close")
                                self.end_headers()
                                return
                        except ValueError:
                            pass

                if content_len_str:
                    try:
                        if int(content_len_str) > max_allowed_bytes:
                            log_event(
                                "proxy",
                                f"Filtered oversized stream ({int(content_len_str):,} bytes > {max_allowed_bytes:,}): {target_url}"
                            )
                            self.send_response(413)
                            self.send_header("Connection", "close")
                            self.end_headers()
                            return
                    except ValueError:
                        pass

                chunk_iter = iter(iter_response_chunks(resp, chunk_size=65536))
                first_buf = bytearray()
                for candidate_chunk in chunk_iter:
                    if candidate_chunk:
                        first_buf.extend(candidate_chunk)
                        if len(first_buf) >= 32:
                            break
                first_chunk = bytes(first_buf)

                if not first_chunk:
                    self.send_response(502)
                    self.send_header("Connection", "close")
                    self.end_headers()
                    return

                is_range_cont = bool(
                    status_code == 206
                    and forwarded_range
                    and range_start > 0
                    and is_mp4_url_verified(target_url)
                )
                magic_ok, verified_mime, magic_reason = verify_media_magic_bytes(
                    first_chunk, is_range_continuation=is_range_cont
                )
                if not magic_ok:
                    log_event("security", f"Blocked suspicious file payload ({magic_reason}) from {target_url}")
                    self.send_response(415)
                    self.send_header("Connection", "close")
                    self.end_headers()
                    return

                if (is_mp4 and verified_mime != "video/mp4") or (not is_mp4 and verified_mime == "video/mp4"):
                    log_event(
                        "security",
                        f"Blocked media stream due to extension/MIME mismatch (ext={verified_ext}, mime={verified_mime}): {target_url}"
                    )
                    self.send_response(415)
                    self.send_header("Connection", "close")
                    self.end_headers()
                    return

                if not is_range_cont and range_start == 0 and len(first_chunk) >= 32 and verified_mime == "video/mp4":
                    mark_mp4_url_verified(target_url)

                # If the client sent a tiny byte-0 probe (e.g. bytes=0-1) that we expanded to bytes=0-65535
                # for magic-byte verification, slice the response back to the exact range requested by the client.
                slice_to_short_probe = False
                if client_requested_short_end is not None and status_code in (200, 206):
                    desired_len = client_requested_short_end + 1
                    first_chunk = first_chunk[:desired_len]
                    actual_end = max(0, len(first_chunk) - 1)
                    if total_res_bytes is None and content_len_str and status_code == 200:
                        try:
                            total_res_bytes = int(content_len_str)
                        except ValueError:
                            total_res_bytes = None
                    if total_res_bytes is not None:
                        status_code = 206
                        content_range = f"bytes 0-{actual_end}/{total_res_bytes}"
                        content_len_str = str(len(first_chunk))
                        slice_to_short_probe = True

                self.send_response(status_code)
                self.send_header("Content-Type", verified_mime)
                self.send_header("Content-Disposition", "inline")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.send_header("X-Frame-Options", "DENY")
                self.send_header("Cross-Origin-Resource-Policy", "same-origin")
                self.send_header("Content-Security-Policy", "default-src 'none'; img-src 'self' data: blob:; media-src 'self' blob:; style-src 'unsafe-inline'; object-src 'none'; frame-src 'none'; frame-ancestors 'none'")
                if content_len_str:
                    self.send_header("Content-Length", content_len_str)
                if content_range:
                    self.send_header("Content-Range", content_range)
                self.send_header("Accept-Ranges", "bytes")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Connection", "close")
                self.end_headers()
                headers_sent = True

                bytes_streamed = len(first_chunk)
                if bytes_streamed > max_allowed_bytes:
                    log_event("proxy", f"Aborted stream exceeding size cap ({max_allowed_bytes:,} bytes): {target_url}")
                    return
                self.wfile.write(first_chunk)
                if slice_to_short_probe:
                    return

                for chunk in chunk_iter:
                    if APP_PAUSED or not chunk:
                        break
                    bytes_streamed += len(chunk)
                    if bytes_streamed > max_allowed_bytes:
                        log_event("proxy", f"Aborted stream exceeding size cap ({max_allowed_bytes:,} bytes): {target_url}")
                        break
                    self.wfile.write(chunk)

            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                pass
            except Exception as e:
                log_event("proxy", f"Proxy stream error for {target_url}: {e}")
                if not headers_sent:
                    try:
                        self.send_response(502)
                        self.send_header("Connection", "close")
                        self.end_headers()
                    except Exception:
                        pass
            finally:
                if resp is not None:
                    try:
                        resp.close()
                    except Exception:
                        pass
            return

        self.send_response(404)
        self.send_header("Connection", "close")
        self.end_headers()

    def log_message(self, format, *args):
        pass


# =============================================================================
# 6. GLOSSARY WINDOW, TABBED SETTINGS DIALOG & FLOATING SEARCH BAR (LIGHT/DARK)
# =============================================================================
class GlossaryDialog(tk.Toplevel):
    """
    Modal/Floating window triggered by the 'Glossary' button on the Logs tab.
    Displays every log output category and what it means, styled with the active theme.
    """
    def __init__(self, parent):
        super().__init__(parent)
        self.is_open = True
        self._drag_x = 0
        self._drag_y = 0

        self.overrideredirect(True)
        self.attributes("-alpha", 0.98)
        self.attributes("-topmost", True)

        width = 560
        height = 440
        parent.update_idletasks()
        px = parent.winfo_x()
        py = parent.winfo_y()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()

        x = max(20, min(px + 30, sw - width - 20))
        y = max(20, min(py + 40, sh - height - 20))
        self.geometry(f"{width}x{height}+{x}+{y}")

        self.container = tk.Frame(self, highlightthickness=1)
        self.container.pack(fill="both", expand=True, padx=1, pady=1)

        self.header = tk.Frame(self.container)
        self.header.pack(fill="x", padx=14, pady=(10, 6))

        self.title_lbl = tk.Label(
            self.header, text="📖 LOG OUTPUT GLOSSARY", font=("Segoe UI", 10, "bold")
        )
        self.title_lbl.pack(side="left")

        self.close_btn = tk.Label(
            self.header, text="✕", font=("Segoe UI", 10, "bold"), cursor="hand2"
        )
        self.close_btn.pack(side="right")
        self.close_btn.bind("<Button-1>", lambda e: self.close_glossary())

        self.header.bind("<Button-1>", self.start_move)
        self.header.bind("<B1-Motion>", self.do_move)
        self.title_lbl.bind("<Button-1>", self.start_move)
        self.title_lbl.bind("<B1-Motion>", self.do_move)

        self.body_frame = tk.Frame(self.container)
        self.body_frame.pack(fill="both", expand=True, padx=14, pady=(4, 14))

        self.text_box_frame = tk.Frame(self.body_frame, highlightthickness=1)
        self.text_box_frame.pack(fill="both", expand=True)

        self.glossary_text = tk.Text(
            self.text_box_frame, wrap="word", font=("Segoe UI", 9),
            bd=0, relief="flat", padx=10, pady=8
        )
        scrollbar = ttk.Scrollbar(self.text_box_frame, orient="vertical", command=self.glossary_text.yview)
        self.glossary_text.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="right", fill="y")
        self.glossary_text.pack(side="left", fill="both", expand=True)

        self.glossary_text.tag_configure("tag_name", font=("Consolas", 9, "bold"), foreground="#0067c0")
        for tag_label, desc in LOG_GLOSSARY_ENTRIES:
            self.glossary_text.insert(tk.END, f"{tag_label}\n", ("tag_name",))
            self.glossary_text.insert(tk.END, f"  {desc}\n\n")
        self.glossary_text.configure(state="disabled")

        self.apply_theme()
        self.bind("<Escape>", lambda e: self.close_glossary())

    def apply_theme(self):
        pal = THEME_PALETTES[CURRENT_THEME]
        self.configure(bg=pal["border_col"])
        self.container.configure(bg=pal["bg_base"], highlightbackground=pal["border_col"])
        self.header.configure(bg=pal["bg_base"])
        self.title_lbl.configure(bg=pal["bg_base"], fg=pal["text_dark"])
        self.close_btn.configure(bg=pal["bg_base"], fg=pal["text_muted"])
        self.body_frame.configure(bg=pal["bg_base"])
        self.text_box_frame.configure(bg=pal["input_bg"], highlightbackground=pal["border_col"])
        self.glossary_text.configure(bg=pal["input_bg"], fg=pal["text_dark"])
        self.glossary_text.tag_configure(
            "tag_name",
            font=("Consolas", 9, "bold"),
            foreground="#4da3ff" if CURRENT_THEME == "dark" else "#0067c0",
        )

    def start_move(self, event):
        self._drag_x = event.x
        self._drag_y = event.y

    def do_move(self, event):
        x = self.winfo_x() + (event.x - self._drag_x)
        y = self.winfo_y() + (event.y - self._drag_y)
        self.geometry(f"+{x}+{y}")

    def close_glossary(self):
        self.is_open = False
        self.destroy()


# =============================================================================
# 6B. WINDOWS TASK MANAGER PERFORMANCE RESOURCE MONITOR & GRAPH POP-OUT DIALOG
# =============================================================================
TH32CS_SNAPPROCESS = 0x00000002
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
PDH_FMT_DOUBLE = 0x00000200
PDH_MORE_DATA = 0x800007D2


class PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD),
        ("cntUsage", wintypes.DWORD),
        ("th32ProcessID", wintypes.DWORD),
        ("th32DefaultHeapID", ctypes.c_size_t),
        ("th32ModuleID", wintypes.DWORD),
        ("cntThreads", wintypes.DWORD),
        ("th32ParentProcessID", wintypes.DWORD),
        ("pcPriClassBase", wintypes.LONG),
        ("dwFlags", wintypes.DWORD),
        ("szExeFile", wintypes.WCHAR * 260),
    ]


class FILETIME(ctypes.Structure):
    _fields_ = [
        ("dwLowDateTime", wintypes.DWORD),
        ("dwHighDateTime", wintypes.DWORD),
    ]


class PROCESS_MEMORY_COUNTERS_EX(ctypes.Structure):
    _fields_ = [
        ("cb", wintypes.DWORD),
        ("PageFaultCount", wintypes.DWORD),
        ("PeakWorkingSetSize", ctypes.c_size_t),
        ("WorkingSetSize", ctypes.c_size_t),
        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
        ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
        ("PagefileUsage", ctypes.c_size_t),
        ("PeakPagefileUsage", ctypes.c_size_t),
        ("PrivateUsage", ctypes.c_size_t),
    ]


class MEMORYSTATUSEX(ctypes.Structure):
    _fields_ = [
        ("dwLength", wintypes.DWORD),
        ("dwMemoryLoad", wintypes.DWORD),
        ("ullTotalPhys", ctypes.c_uint64),
        ("ullAvailPhys", ctypes.c_uint64),
        ("ullTotalPageFile", ctypes.c_uint64),
        ("ullAvailPageFile", ctypes.c_uint64),
        ("ullTotalVirtual", ctypes.c_uint64),
        ("ullAvailVirtual", ctypes.c_uint64),
        ("ullAvailExtendedVirtual", ctypes.c_uint64),
    ]


class PDH_FMT_COUNTERVALUE_DOUBLE(ctypes.Structure):
    _fields_ = [
        ("CStatus", wintypes.DWORD),
        ("doubleValue", ctypes.c_double),
    ]


class PDH_FMT_COUNTERVALUE_ITEM_W(ctypes.Structure):
    _fields_ = [
        ("szName", wintypes.LPWSTR),
        ("FmtValue", PDH_FMT_COUNTERVALUE_DOUBLE),
    ]


class DISPLAY_DEVICEW(ctypes.Structure):
    _fields_ = [
        ("cb", wintypes.DWORD),
        ("DeviceName", wintypes.WCHAR * 32),
        ("DeviceString", wintypes.WCHAR * 128),
        ("StateFlags", wintypes.DWORD),
        ("DeviceID", wintypes.WCHAR * 128),
        ("DeviceKey", wintypes.WCHAR * 128),
    ]


INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value

# Explicit 64-bit safe argtypes/restype declarations for Win32 Telemetry APIs
user32.EnumDisplayDevicesW.argtypes = [
    wintypes.LPCWSTR,
    wintypes.DWORD,
    ctypes.POINTER(DISPLAY_DEVICEW),
    wintypes.DWORD,
]
user32.EnumDisplayDevicesW.restype = wintypes.BOOL

kernel32.GlobalMemoryStatusEx.argtypes = [ctypes.POINTER(MEMORYSTATUSEX)]
kernel32.GlobalMemoryStatusEx.restype = wintypes.BOOL

kernel32.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
kernel32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE

kernel32.Process32FirstW.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
kernel32.Process32FirstW.restype = wintypes.BOOL

kernel32.Process32NextW.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
kernel32.Process32NextW.restype = wintypes.BOOL

kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
kernel32.OpenProcess.restype = wintypes.HANDLE

kernel32.GetProcessTimes.argtypes = [
    wintypes.HANDLE,
    ctypes.POINTER(FILETIME),
    ctypes.POINTER(FILETIME),
    ctypes.POINTER(FILETIME),
    ctypes.POINTER(FILETIME),
]
kernel32.GetProcessTimes.restype = wintypes.BOOL

kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
kernel32.CloseHandle.restype = wintypes.BOOL

if hasattr(kernel32, "K32GetProcessMemoryInfo"):
    kernel32.K32GetProcessMemoryInfo.argtypes = [
        wintypes.HANDLE,
        ctypes.POINTER(PROCESS_MEMORY_COUNTERS_EX),
        wintypes.DWORD,
    ]
    kernel32.K32GetProcessMemoryInfo.restype = wintypes.BOOL
elif hasattr(ctypes.windll, "psapi") and hasattr(ctypes.windll.psapi, "GetProcessMemoryInfo"):
    ctypes.windll.psapi.GetProcessMemoryInfo.argtypes = [
        wintypes.HANDLE,
        ctypes.POINTER(PROCESS_MEMORY_COUNTERS_EX),
        wintypes.DWORD,
    ]
    ctypes.windll.psapi.GetProcessMemoryInfo.restype = wintypes.BOOL


def _detect_primary_gpu_name() -> str:
    try:
        dd = DISPLAY_DEVICEW()
        dd.cb = ctypes.sizeof(DISPLAY_DEVICEW)
        if user32.EnumDisplayDevicesW(None, 0, ctypes.byref(dd), 0):
            name = (dd.DeviceString or "").strip()
            if name:
                return name
    except Exception:
        pass
    return "Direct3D / WebView2 GPU Engine"


class AppResourceMonitor:
    """
    Collects real-time CPU (%), RAM (Working Set & Private Commit MB / %), and GPU (%)
    utilization across the wallpaper application's entire process tree
    (Python host + child msedgewebview2.exe processes) using native Win32 APIs.
    """
    HISTORY_LEN = 60

    def __init__(self):
        self.root_pid = os.getpid()
        self.logical_cpus = max(1, os.cpu_count() or 1)
        self.total_phys_mb = self._query_total_physical_ram_mb()
        self.gpu_name = _detect_primary_gpu_name()
        self.start_time = time.time()

        self.cpu_history = deque([0.0] * self.HISTORY_LEN, maxlen=self.HISTORY_LEN)
        self.ram_mb_history = deque([0.0] * self.HISTORY_LEN, maxlen=self.HISTORY_LEN)
        self.ram_pct_history = deque([0.0] * self.HISTORY_LEN, maxlen=self.HISTORY_LEN)
        self.gpu_history = deque([0.0] * self.HISTORY_LEN, maxlen=self.HISTORY_LEN)

        self.current_cpu_pct = 0.0
        self.current_ram_mb = 0.0
        self.current_private_mb = 0.0
        self.current_ram_pct = 0.0
        self.current_gpu_pct = 0.0

        self.peak_cpu_pct = 0.0
        self.peak_ram_mb = 0.0
        self.peak_gpu_pct = 0.0

        self.process_count = 1
        self.thread_count = 1

        self._prev_proc_times = {}      # pid -> int (100-ns kernel+user ticks)
        self._prev_sample_ts = time.perf_counter()

        self._pdh_dll = None
        self._pdh_query = ctypes.c_void_p(0)
        self._pdh_gpu_counter = ctypes.c_void_p(0)
        self._pdh_available = False
        self._init_pdh_gpu_counter()

        # Prime baseline process times so the first visible tick has a valid delta
        self.sample()

    def _query_total_physical_ram_mb(self) -> float:
        try:
            ms = MEMORYSTATUSEX()
            ms.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            if kernel32.GlobalMemoryStatusEx(ctypes.byref(ms)) and ms.ullTotalPhys > 0:
                return float(ms.ullTotalPhys) / (1024.0 * 1024.0)
        except Exception:
            pass
        return 16384.0

    def _init_pdh_gpu_counter(self):
        try:
            self._pdh_dll = ctypes.windll.pdh
            self._pdh_dll.PdhOpenQueryW.argtypes = [wintypes.LPCWSTR, ctypes.c_size_t, ctypes.POINTER(ctypes.c_void_p)]
            self._pdh_dll.PdhOpenQueryW.restype = wintypes.LONG
            self._pdh_dll.PdhCollectQueryData.argtypes = [ctypes.c_void_p]
            self._pdh_dll.PdhCollectQueryData.restype = wintypes.LONG
            self._pdh_dll.PdhCloseQuery.argtypes = [ctypes.c_void_p]
            self._pdh_dll.PdhCloseQuery.restype = wintypes.LONG
            self._pdh_dll.PdhGetFormattedCounterArrayW.argtypes = [
                ctypes.c_void_p,
                wintypes.DWORD,
                ctypes.POINTER(wintypes.DWORD),
                ctypes.POINTER(wintypes.DWORD),
                ctypes.c_void_p,
            ]
            self._pdh_dll.PdhGetFormattedCounterArrayW.restype = wintypes.LONG

            q = ctypes.c_void_p(0)
            if self._pdh_dll.PdhOpenQueryW(None, 0, ctypes.byref(q)) != 0:
                return
            c = ctypes.c_void_p(0)
            path = "\\GPU Engine(*)\\Utilization Percentage"
            add_fn = getattr(self._pdh_dll, "PdhAddEnglishCounterW", self._pdh_dll.PdhAddCounterW)
            add_fn.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR, ctypes.c_size_t, ctypes.POINTER(ctypes.c_void_p)]
            add_fn.restype = wintypes.LONG
            if add_fn(q, wintypes.LPCWSTR(path), 0, ctypes.byref(c)) != 0:
                self._pdh_dll.PdhCloseQuery(q)
                return
            self._pdh_dll.PdhCollectQueryData(q)
            self._pdh_query = q
            self._pdh_gpu_counter = c
            self._pdh_available = True
        except Exception:
            self._pdh_available = False

    def close(self):
        if getattr(self, "_pdh_available", False) and getattr(self, "_pdh_dll", None) and getattr(self, "_pdh_query", None):
            try:
                self._pdh_dll.PdhCloseQuery(self._pdh_query)
            except Exception:
                pass
            self._pdh_available = False
            self._pdh_query = ctypes.c_void_p(0)

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass

    def _enumerate_app_process_tree(self) -> tuple[set[int], int]:
        """
        Returns (set_of_pids_in_app_tree, total_threads_in_tree) strictly restricted
        to this wallpaper application's process tree (root Python/PyInstaller host +
        its child msedgewebview2.exe processes), excluding external browsers or OS utilities.
        """
        parent_map = {}
        threads_map = {}
        exe_map = {}
        snap = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
        if not snap or snap == INVALID_HANDLE_VALUE or snap == -1:
            return {self.root_pid}, 1

        try:
            pe = PROCESSENTRY32W()
            pe.dwSize = ctypes.sizeof(PROCESSENTRY32W)
            ok = kernel32.Process32FirstW(snap, ctypes.byref(pe))
            while ok:
                pid = int(pe.th32ProcessID)
                ppid = int(pe.th32ParentProcessID)
                parent_map[pid] = ppid
                threads_map[pid] = int(pe.cntThreads)
                exe_map[pid] = str(pe.szExeFile or "").strip().lower()
                ok = kernel32.Process32NextW(snap, ctypes.byref(pe))
        except Exception:
            pass
        finally:
            kernel32.CloseHandle(snap)

        own_exe = os.path.basename(sys.executable or "").strip().lower()
        allowed_child_exes = {
            "msedgewebview2.exe",
            "python.exe",
            "pythonw.exe",
            "danbooruwallpaper.exe",
            "danbooru_service.exe",
        }
        if own_exe:
            allowed_child_exes.add(own_exe)

        tree_pids = {self.root_pid}
        added = True
        while added:
            added = False
            for pid, ppid in parent_map.items():
                if pid not in tree_pids and ppid in tree_pids:
                    child_exe = exe_map.get(pid, "")
                    if child_exe in allowed_child_exes:
                        tree_pids.add(pid)
                        added = True

        total_threads = sum(threads_map.get(p, 1) for p in tree_pids)
        return tree_pids, max(1, total_threads)

    def _query_process_ticks_and_ram(self, pid: int) -> tuple[int, int, int]:
        """Returns (cpu_100ns_ticks, working_set_bytes, private_bytes) for a single PID."""
        h_proc = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, wintypes.DWORD(pid))
        if not h_proc or h_proc == INVALID_HANDLE_VALUE or h_proc == -1:
            return 0, 0, 0
        ticks = 0
        ws_bytes = 0
        priv_bytes = 0
        try:
            ft_create = FILETIME()
            ft_exit = FILETIME()
            ft_kernel = FILETIME()
            ft_user = FILETIME()
            if kernel32.GetProcessTimes(
                h_proc,
                ctypes.byref(ft_create),
                ctypes.byref(ft_exit),
                ctypes.byref(ft_kernel),
                ctypes.byref(ft_user),
            ):
                k_val = (ft_kernel.dwHighDateTime << 32) | ft_kernel.dwLowDateTime
                u_val = (ft_user.dwHighDateTime << 32) | ft_user.dwLowDateTime
                ticks = k_val + u_val

            pmc = PROCESS_MEMORY_COUNTERS_EX()
            pmc.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS_EX)
            mem_ok = False
            if hasattr(kernel32, "K32GetProcessMemoryInfo"):
                mem_ok = bool(kernel32.K32GetProcessMemoryInfo(h_proc, ctypes.byref(pmc), pmc.cb))
            elif hasattr(ctypes.windll, "psapi"):
                mem_ok = bool(ctypes.windll.psapi.GetProcessMemoryInfo(h_proc, ctypes.byref(pmc), pmc.cb))
            if mem_ok:
                ws_bytes = int(pmc.WorkingSetSize)
                priv_bytes = int(pmc.PrivateUsage or pmc.PagefileUsage)
        except Exception:
            pass
        finally:
            kernel32.CloseHandle(h_proc)
        return ticks, ws_bytes, priv_bytes

    def _query_pdh_gpu_utilization(self, tree_pids: set[int]) -> tuple[bool, float]:
        """
        Queries Windows PDH \\GPU Engine(*)\\Utilization Percentage strictly for PIDs in tree_pids.
        Follows Task Manager's per-process GPU methodology by summing across the application's PIDs
        per GPU engine type (3D, Compute, VideoDecode, Copy, etc.) and taking the highest utilized
        engine plane for the application so orthogonal engine planes are never double-counted.
        """
        if not self._pdh_available or not self._pdh_dll or not self._pdh_query:
            return False, 0.0
        try:
            if self._pdh_dll.PdhCollectQueryData(self._pdh_query) != 0:
                return False, 0.0

            buf_size = wintypes.DWORD(0)
            item_count = wintypes.DWORD(0)
            status = self._pdh_dll.PdhGetFormattedCounterArrayW(
                self._pdh_gpu_counter,
                PDH_FMT_DOUBLE,
                ctypes.byref(buf_size),
                ctypes.byref(item_count),
                None,
            )
            if status not in (0, PDH_MORE_DATA, -2147481646) or buf_size.value == 0:
                return False, 0.0

            raw_buf = ctypes.create_string_buffer(buf_size.value)
            status = self._pdh_dll.PdhGetFormattedCounterArrayW(
                self._pdh_gpu_counter,
                PDH_FMT_DOUBLE,
                ctypes.byref(buf_size),
                ctypes.byref(item_count),
                ctypes.cast(raw_buf, ctypes.c_void_p),
            )
            if status != 0 or item_count.value == 0:
                return False, 0.0

            items_ptr = ctypes.cast(raw_buf, ctypes.POINTER(PDH_FMT_COUNTERVALUE_ITEM_W))
            pid_tokens = tuple(f"pid_{p}_" for p in tree_pids)
            engine_totals = {}

            for i in range(item_count.value):
                item = items_ptr[i]
                name = (item.szName or "").lower()
                if not any(tok in name for tok in pid_tokens):
                    continue
                val = float(item.FmtValue.doubleValue or 0.0)
                if val <= 0.0 or val > 100.0:
                    continue
                luid_match = re.search(r"(luid_0x[0-9a-f]+_0x[0-9a-f]+_phys_\d+)", name)
                luid_key = luid_match.group(1) if luid_match else "gpu0"
                eng_idx = name.find("engtype_")
                eng_type = name[eng_idx:] if eng_idx >= 0 else "engtype_default"
                eng_key = f"{luid_key}_{eng_type}"
                engine_totals[eng_key] = engine_totals.get(eng_key, 0.0) + val

            if engine_totals:
                app_gpu_pct = max(engine_totals.values())
                return True, max(0.0, min(100.0, app_gpu_pct))
            return True, 0.0
        except Exception:
            return False, 0.0

    def sample(self) -> dict:
        now_ts = time.perf_counter()
        dt = max(0.05, now_ts - self._prev_sample_ts)
        self._prev_sample_ts = now_ts

        tree_pids, total_threads = self._enumerate_app_process_tree()
        self.process_count = len(tree_pids)
        self.thread_count = total_threads

        new_proc_times = {}
        delta_ticks = 0
        child_ticks_delta = 0
        total_ws_bytes = 0
        total_priv_bytes = 0

        for pid in tree_pids:
            ticks, ws_b, priv_b = self._query_process_ticks_and_ram(pid)
            total_ws_bytes += ws_b
            total_priv_bytes += priv_b
            if ticks > 0:
                new_proc_times[pid] = ticks
                prev_t = self._prev_proc_times.get(pid)
                if prev_t is not None and ticks >= prev_t:
                    d = ticks - prev_t
                    delta_ticks += d
                    if pid != self.root_pid:
                        child_ticks_delta += d

        self._prev_proc_times = new_proc_times

        # 10,000,000 ticks = 1.0 second of 1 logical processor core
        wall_capacity_ticks = dt * 10_000_000.0 * self.logical_cpus
        cpu_pct = (delta_ticks / wall_capacity_ticks) * 100.0 if wall_capacity_ticks > 0 else 0.0
        cpu_pct = max(0.0, min(100.0, cpu_pct))

        ws_mb = float(total_ws_bytes) / (1024.0 * 1024.0)
        priv_mb = float(total_priv_bytes) / (1024.0 * 1024.0)
        ram_pct = max(0.0, min(100.0, (ws_mb / max(1.0, self.total_phys_mb)) * 100.0))

        pdh_ok, gpu_pct = self._query_pdh_gpu_utilization(tree_pids)
        if not pdh_ok and child_ticks_delta > 0 and wall_capacity_ticks > 0:
            # Strictly only if Windows PDH is unavailable on the system, estimate app GPU activity
            # proportional to the app's own child WebView2 CPU share (never inflating single-core ticks)
            est_gpu = (child_ticks_delta / wall_capacity_ticks) * 100.0
            gpu_pct = max(0.0, min(100.0, est_gpu))

        self.current_cpu_pct = round(cpu_pct, 1)
        self.current_ram_mb = round(ws_mb, 1)
        self.current_private_mb = round(priv_mb, 1)
        self.current_ram_pct = round(ram_pct, 1)
        self.current_gpu_pct = round(gpu_pct, 1)

        self.peak_cpu_pct = max(self.peak_cpu_pct, self.current_cpu_pct)
        self.peak_ram_mb = max(self.peak_ram_mb, self.current_ram_mb)
        self.peak_gpu_pct = max(self.peak_gpu_pct, self.current_gpu_pct)

        self.cpu_history.append(self.current_cpu_pct)
        self.ram_mb_history.append(self.current_ram_mb)
        self.ram_pct_history.append(self.current_ram_pct)
        self.gpu_history.append(self.current_gpu_pct)

        return {
            "cpu_pct": self.current_cpu_pct,
            "ram_mb": self.current_ram_mb,
            "private_mb": self.current_private_mb,
            "ram_pct": self.current_ram_pct,
            "gpu_pct": self.current_gpu_pct,
        }


class ResourceGraphDialog(tk.Toplevel):
    """
    Windows Task Manager Performance-style pop-out window triggered by the 'Resource Graph'
    button at the top of the Settings dialog. Displays real-time scrolling 60-second graphs
    and telemetry readouts for CPU, Memory (RAM), and GPU utilization of the wallpaper app.
    """
    RESOURCE_SPECS = {
        "cpu": {
            "title": "CPU",
            "unit_label": "% Utilization",
            "max_label": "100%",
            "stroke_dark": "#2899f5",
            "fill_dark": "#113255",
            "grid_dark": "#1b2e44",
            "stroke_light": "#0078d4",
            "fill_light": "#cfe8fc",
            "grid_light": "#bbd9f5",
        },
        "ram": {
            "title": "Memory",
            "unit_label": "% of Total System Memory",
            "max_label": "100%",
            "stroke_dark": "#b4009e",
            "fill_dark": "#3b1238",
            "grid_dark": "#3f1d3d",
            "stroke_light": "#881798",
            "fill_light": "#f0d3f4",
            "grid_light": "#dec0e3",
        },
        "gpu": {
            "title": "GPU 0",
            "unit_label": "% Utilization (3D / WebView2)",
            "max_label": "100%",
            "stroke_dark": "#00cc6a",
            "fill_dark": "#0e3a24",
            "grid_dark": "#18422c",
            "stroke_light": "#107c10",
            "fill_light": "#d2f4dc",
            "grid_light": "#b6e3c4",
        },
    }

    def __init__(self, parent):
        super().__init__(parent)
        self.is_open = True
        self._drag_x = 0
        self._drag_y = 0
        self._tick_job = None
        self._grid_scroll_step = 0
        self._graph_paused = False
        self.selected_tab = "cpu"  # 'cpu' | 'ram' | 'gpu' | 'all'

        self.monitor = AppResourceMonitor()

        self.overrideredirect(True)
        self.attributes("-alpha", 0.98)
        self.attributes("-topmost", True)

        width = 780
        height = 500
        anchor_win = (
            SETTINGS_DIALOG_INSTANCE
            if (SETTINGS_DIALOG_INSTANCE is not None and getattr(SETTINGS_DIALOG_INSTANCE, "is_open", False))
            else parent
        )
        anchor_win.update_idletasks()
        px = anchor_win.winfo_x()
        py = anchor_win.winfo_y()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()

        x = max(20, min(px + 36, sw - width - 20))
        y = max(20, min(py + 28, sh - height - 20))
        self.geometry(f"{width}x{height}+{x}+{y}")

        self.container = tk.Frame(self, highlightthickness=1)
        self.container.pack(fill="both", expand=True, padx=1, pady=1)

        # Window Title Bar
        self.header = tk.Frame(self.container)
        self.header.pack(fill="x", padx=14, pady=(9, 6))

        self.title_lbl = tk.Label(
            self.header,
            text="📊 PERFORMANCE — RESOURCE GRAPH",
            font=("Segoe UI", 10, "bold"),
        )
        self.title_lbl.pack(side="left")

        self.close_btn = tk.Label(
            self.header, text="✕", font=("Segoe UI", 10, "bold"), cursor="hand2", padx=4
        )
        self.close_btn.pack(side="right")
        self.close_btn.bind("<Button-1>", lambda e: self.close_resource_graph())

        self.pause_graph_btn = tk.Button(
            self.header,
            text="⏸ Pause Graph",
            font=("Segoe UI", 8, "bold"),
            bd=0,
            relief="flat",
            padx=10,
            pady=2,
            cursor="hand2",
            command=self._toggle_pause_graph,
        )
        self.pause_graph_btn.pack(side="right", padx=(0, 10))

        self.header.bind("<Button-1>", self.start_move)
        self.header.bind("<B1-Motion>", self.do_move)
        self.title_lbl.bind("<Button-1>", self.start_move)
        self.title_lbl.bind("<B1-Motion>", self.do_move)

        self.sep_top = tk.Frame(self.container, height=1)
        self.sep_top.pack(fill="x")

        # Main Task Manager Split Layout: Left Selector Sidebar + Right Graph Viewport
        self.body = tk.Frame(self.container)
        self.body.pack(fill="both", expand=True, padx=12, pady=10)

        self.sidebar = tk.Frame(self.body, width=215)
        self.sidebar.pack(side="left", fill="y", padx=(0, 12))
        self.sidebar.pack_propagate(False)

        self.main_pane = tk.Frame(self.body)
        self.main_pane.pack(side="left", fill="both", expand=True)

        # Build Left Sidebar Resource Cards (CPU, Memory, GPU, All Combined)
        self.nav_cards = {}
        for key, label_title in (
            ("cpu", "CPU"),
            ("ram", "Memory"),
            ("gpu", "GPU 0"),
            ("all", "All Graphs (3x)"),
        ):
            card = tk.Frame(self.sidebar, highlightthickness=1, cursor="hand2")
            card.pack(fill="x", pady=(0, 6))

            accent_bar = tk.Frame(card, width=4)
            accent_bar.pack(side="left", fill="y")

            mini_canvas = tk.Canvas(
                card, width=62, height=44, bd=0, highlightthickness=1, cursor="hand2"
            )
            mini_canvas.pack(side="left", padx=(6, 8), pady=6)

            txt_frame = tk.Frame(card, cursor="hand2")
            txt_frame.pack(side="left", fill="both", expand=True, pady=6)

            t_lbl = tk.Label(
                txt_frame, text=label_title, font=("Segoe UI", 9, "bold"), anchor="w", cursor="hand2"
            )
            t_lbl.pack(fill="x")

            sub_lbl = tk.Label(
                txt_frame, text="0%", font=("Segoe UI", 8), anchor="w", cursor="hand2"
            )
            sub_lbl.pack(fill="x", pady=(1, 0))

            for w in (card, accent_bar, mini_canvas, txt_frame, t_lbl, sub_lbl):
                w.bind("<Button-1>", lambda e, k=key: self.select_resource_tab(k))

            self.nav_cards[key] = {
                "card": card,
                "accent": accent_bar,
                "canvas": mini_canvas,
                "txt_frame": txt_frame,
                "title": t_lbl,
                "sub": sub_lbl,
            }

        # Right Main Pane Header (Big Title on Left, Process/Hardware Name on Right)
        self.pane_header = tk.Frame(self.main_pane)
        self.pane_header.pack(fill="x", pady=(0, 2))

        self.pane_title_lbl = tk.Label(
            self.pane_header, text="CPU", font=("Segoe UI", 16, "bold"), anchor="w"
        )
        self.pane_title_lbl.pack(side="left")

        self.pane_hw_lbl = tk.Label(
            self.pane_header,
            text=f"Danbooru Wallpaper Process Tree ({self.monitor.logical_cpus} Logical Processors)",
            font=("Segoe UI", 9),
            anchor="e",
        )
        self.pane_hw_lbl.pack(side="right", pady=(6, 0))

        # Top Axis Labels above Graph
        self.axis_top_row = tk.Frame(self.main_pane)
        self.axis_top_row.pack(fill="x", pady=(2, 2))

        self.axis_top_left_lbl = tk.Label(
            self.axis_top_row, text="% Utilization", font=("Segoe UI", 8)
        )
        self.axis_top_left_lbl.pack(side="left")

        self.axis_top_right_lbl = tk.Label(
            self.axis_top_row, text="100%", font=("Segoe UI", 8)
        )
        self.axis_top_right_lbl.pack(side="right")

        # Main Task Manager Scrolling Graph Canvas
        self.graph_canvas = tk.Canvas(
            self.main_pane, bd=0, highlightthickness=1, height=235
        )
        self.graph_canvas.pack(fill="both", expand=True)

        # Bottom Axis Labels ("60 seconds" ... "0")
        self.axis_bot_row = tk.Frame(self.main_pane)
        self.axis_bot_row.pack(fill="x", pady=(2, 8))

        self.axis_bot_left_lbl = tk.Label(
            self.axis_bot_row, text="60 seconds", font=("Segoe UI", 8)
        )
        self.axis_bot_left_lbl.pack(side="left")

        self.axis_bot_right_lbl = tk.Label(
            self.axis_bot_row, text="0", font=("Segoe UI", 8)
        )
        self.axis_bot_right_lbl.pack(side="right")

        # Bottom Telemetry Readout Columns (Windows Task Manager style with vertical colored bars)
        self.stats_row = tk.Frame(self.main_pane)
        self.stats_row.pack(fill="x", pady=(2, 0))

        self.stat_blocks = {}
        stat_defs = [
            ("primary", "Utilization", "0.0%"),
            ("secondary", "Wallpaper Memory", "0.0 MB"),
            ("peak", "Peak Recorded", "0.0%"),
            ("procs", "Processes / Threads", "1 / 1"),
        ]
        for s_key, s_title, s_init in stat_defs:
            blk = tk.Frame(self.stats_row)
            blk.pack(side="left", fill="x", expand=True, padx=(0, 8))

            bar = tk.Frame(blk, width=3)
            bar.pack(side="left", fill="y", padx=(0, 6), pady=2)

            inner = tk.Frame(blk)
            inner.pack(side="left", fill="x", expand=True)

            k_lbl = tk.Label(inner, text=s_title, font=("Segoe UI", 8), anchor="w")
            k_lbl.pack(fill="x")

            v_lbl = tk.Label(inner, text=s_init, font=("Segoe UI", 13, "bold"), anchor="w")
            v_lbl.pack(fill="x")

            self.stat_blocks[s_key] = {
                "frame": blk,
                "bar": bar,
                "inner": inner,
                "k_lbl": k_lbl,
                "v_lbl": v_lbl,
            }

        self.apply_theme()
        self.bind("<Escape>", lambda e: self.close_resource_graph())
        self.bind("<Destroy>", self._on_widget_destroy)
        self.graph_canvas.bind("<Configure>", lambda e: self._redraw_all_graphs())
        self._tick_telemetry()

    def _on_widget_destroy(self, event=None):
        if event is not None and event.widget is self:
            self.is_open = False
            try:
                self.monitor.close()
            except Exception:
                pass

    def select_resource_tab(self, tab_key: str):
        self.selected_tab = tab_key
        self.apply_theme()
        self._redraw_all_graphs()

    def _toggle_pause_graph(self):
        self._graph_paused = not self._graph_paused
        self.pause_graph_btn.configure(
            text="▶ Resume Graph" if self._graph_paused else "⏸ Pause Graph"
        )

    def apply_theme(self):
        is_dark = (CURRENT_THEME == "dark")
        pal = THEME_PALETTES[CURRENT_THEME]
        bg_base = pal["bg_base"]
        card_bg = "#18181f" if is_dark else "#ffffff"
        card_sel_bg = "#232733" if is_dark else "#e6f2fc"
        border_col = pal["border_col"]
        text_dark = pal["text_dark"]
        text_muted = pal["text_muted"]
        graph_bg = "#0c0d12" if is_dark else "#ffffff"

        self.configure(bg=border_col)
        self.container.configure(bg=bg_base, highlightbackground=border_col)
        self.header.configure(bg=bg_base)
        self.title_lbl.configure(bg=bg_base, fg=text_dark)
        self.close_btn.configure(bg=bg_base, fg=text_muted)
        self.pause_graph_btn.configure(
            bg=pal["btn_bg"],
            fg=text_dark,
            activebackground=pal["btn_active"],
            activeforeground=text_dark,
        )
        self.sep_top.configure(bg=border_col)
        self.body.configure(bg=bg_base)
        self.sidebar.configure(bg=bg_base)
        self.main_pane.configure(bg=bg_base)

        for key, item in self.nav_cards.items():
            is_sel = (key == self.selected_tab)
            c_bg = card_sel_bg if is_sel else card_bg
            spec_key = "cpu" if key == "all" else key
            spec = self.RESOURCE_SPECS[spec_key]
            stroke_col = spec["stroke_dark"] if is_dark else spec["stroke_light"]

            item["card"].configure(
                bg=c_bg,
                highlightbackground=stroke_col if is_sel else border_col,
            )
            item["accent"].configure(bg=stroke_col if is_sel else c_bg)
            item["canvas"].configure(bg=graph_bg, highlightbackground=stroke_col)
            item["txt_frame"].configure(bg=c_bg)
            item["title"].configure(bg=c_bg, fg=text_dark)
            item["sub"].configure(bg=c_bg, fg=text_muted)

        self.pane_header.configure(bg=bg_base)
        self.pane_title_lbl.configure(bg=bg_base, fg=text_dark)
        self.pane_hw_lbl.configure(bg=bg_base, fg=text_muted)

        self.axis_top_row.configure(bg=bg_base)
        self.axis_top_left_lbl.configure(bg=bg_base, fg=text_muted)
        self.axis_top_right_lbl.configure(bg=bg_base, fg=text_muted)

        active_spec = self.RESOURCE_SPECS.get(self.selected_tab, self.RESOURCE_SPECS["cpu"])
        active_stroke = active_spec["stroke_dark"] if is_dark else active_spec["stroke_light"]
        self.graph_canvas.configure(bg=graph_bg, highlightbackground=active_stroke)

        self.axis_bot_row.configure(bg=bg_base)
        self.axis_bot_left_lbl.configure(bg=bg_base, fg=text_muted)
        self.axis_bot_right_lbl.configure(bg=bg_base, fg=text_muted)

        self.stats_row.configure(bg=bg_base)
        for s_key, blk in self.stat_blocks.items():
            blk["frame"].configure(bg=bg_base)
            blk["bar"].configure(bg=active_stroke)
            blk["inner"].configure(bg=bg_base)
            blk["k_lbl"].configure(bg=bg_base, fg=text_muted)
            blk["v_lbl"].configure(bg=bg_base, fg=text_dark)

    def _draw_task_manager_series(
        self,
        canvas: tk.Canvas,
        x0: float,
        y0: float,
        w: float,
        h: float,
        values: list[float],
        max_val: float,
        stroke_col: str,
        fill_col: str,
        grid_col: str,
        draw_grid: bool = True,
        label_overlay: str = "",
    ):
        if w <= 4 or h <= 4:
            return
        max_val = max(1.0, float(max_val))

        if draw_grid:
            # Horizontal 10% subdivisions
            rows = 10 if h >= 120 else 4
            for r in range(1, rows):
                gy = y0 + (h * r / rows)
                canvas.create_line(x0, gy, x0 + w, gy, fill=grid_col, width=1)

            # Vertical scrolling time gridlines (Task Manager style)
            cols = 12 if w >= 240 else 4
            col_spacing = w / cols
            offset_px = (self._grid_scroll_step % 6) * (col_spacing / 6.0)
            gx = x0 + w - offset_px
            while gx > x0:
                canvas.create_line(gx, y0, gx, y0 + h, fill=grid_col, width=1)
                gx -= col_spacing

        n = len(values)
        if n >= 2:
            step_x = w / float(self.monitor.HISTORY_LEN - 1)
            start_idx_offset = self.monitor.HISTORY_LEN - n
            pts = []
            for idx, v in enumerate(values):
                clamped = max(0.0, min(max_val, float(v)))
                px = x0 + (start_idx_offset + idx) * step_x
                py = y0 + h - (clamped / max_val) * (h - 2.0) - 1.0
                pts.append((px, py))

            poly_coords = [pts[0][0], y0 + h]
            for px, py in pts:
                poly_coords.extend([px, py])
            poly_coords.extend([pts[-1][0], y0 + h])
            canvas.create_polygon(poly_coords, fill=fill_col, outline="")

            line_coords = []
            for px, py in pts:
                line_coords.extend([px, py])
            canvas.create_line(line_coords, fill=stroke_col, width=2, smooth=False)

        canvas.create_rectangle(x0, y0, x0 + w - 1, y0 + h - 1, outline=stroke_col, width=1)
        if label_overlay:
            is_dark = (CURRENT_THEME == "dark")
            txt_col = "#e8e8f0" if is_dark else "#1c1c1c"
            canvas.create_text(
                x0 + 8, y0 + 8, text=label_overlay, anchor="nw",
                fill=txt_col, font=("Segoe UI", 8, "bold")
            )

    def _redraw_all_graphs(self):
        if not self.is_open:
            return
        is_dark = (CURRENT_THEME == "dark")
        total_phys_mb = max(1024.0, float(self.monitor.total_phys_mb))
        total_phys_gb = total_phys_mb / 1024.0

        # 1. Update Left Sidebar Mini Sparklines & Subtitles (All scaled 0% - 100% of total capacity)
        self.nav_cards["cpu"]["sub"].configure(text=f"{self.monitor.current_cpu_pct:.1f}%")
        self.nav_cards["ram"]["sub"].configure(
            text=f"{self.monitor.current_ram_mb:.1f} MB ({self.monitor.current_ram_pct:.1f}%)"
        )
        self.nav_cards["gpu"]["sub"].configure(text=f"{self.monitor.current_gpu_pct:.1f}%")
        self.nav_cards["all"]["sub"].configure(
            text=f"CPU {self.monitor.current_cpu_pct:.0f}% | GPU {self.monitor.current_gpu_pct:.0f}%"
        )

        mini_series_map = {
            "cpu": (list(self.monitor.cpu_history), 100.0, "cpu"),
            "ram": (list(self.monitor.ram_pct_history), 100.0, "ram"),
            "gpu": (list(self.monitor.gpu_history), 100.0, "gpu"),
            "all": (list(self.monitor.cpu_history), 100.0, "cpu"),
        }
        for key, (vals, m_val, s_key) in mini_series_map.items():
            mc = self.nav_cards[key]["canvas"]
            mc.delete("all")
            mw = max(60, mc.winfo_width())
            mh = max(42, mc.winfo_height())
            spec = self.RESOURCE_SPECS[s_key]
            self._draw_task_manager_series(
                mc,
                0,
                0,
                mw,
                mh,
                vals,
                m_val,
                spec["stroke_dark"] if is_dark else spec["stroke_light"],
                spec["fill_dark"] if is_dark else spec["fill_light"],
                spec["grid_dark"] if is_dark else spec["grid_light"],
                draw_grid=False,
            )

        # 2. Update Main Graph Canvas & Header Readouts
        self.graph_canvas.delete("all")
        cw = max(200, self.graph_canvas.winfo_width())
        ch = max(140, self.graph_canvas.winfo_height())

        if self.selected_tab == "all":
            self.pane_title_lbl.configure(text="CPU / Memory / GPU")
            self.pane_hw_lbl.configure(
                text=f"Wallpaper App Process Tree ({self.monitor.process_count} Processes)"
            )
            self.axis_top_left_lbl.configure(text="Stacked Real-Time Telemetry (60s Window)")
            self.axis_top_right_lbl.configure(
                text=f"100% Scale ({total_phys_gb:.1f} GB Total System RAM)"
            )

            gap = 8
            band_h = (ch - gap * 2) / 3.0
            bands = [
                (
                    "cpu",
                    list(self.monitor.cpu_history),
                    100.0,
                    f"CPU — {self.monitor.current_cpu_pct:.1f}%",
                ),
                (
                    "ram",
                    list(self.monitor.ram_pct_history),
                    100.0,
                    f"Memory — {self.monitor.current_ram_mb:.1f} MB / {int(total_phys_mb):,} MB ({self.monitor.current_ram_pct:.1f}%)",
                ),
                (
                    "gpu",
                    list(self.monitor.gpu_history),
                    100.0,
                    f"GPU 0 — {self.monitor.current_gpu_pct:.1f}% ({self.monitor.gpu_name})",
                ),
            ]
            for idx, (s_key, vals, m_val, overlay_txt) in enumerate(bands):
                spec = self.RESOURCE_SPECS[s_key]
                y_top = idx * (band_h + gap)
                self._draw_task_manager_series(
                    self.graph_canvas,
                    0,
                    y_top,
                    cw,
                    band_h,
                    vals,
                    m_val,
                    spec["stroke_dark"] if is_dark else spec["stroke_light"],
                    spec["fill_dark"] if is_dark else spec["fill_light"],
                    spec["grid_dark"] if is_dark else spec["grid_light"],
                    draw_grid=True,
                    label_overlay=overlay_txt,
                )
        else:
            spec = self.RESOURCE_SPECS[self.selected_tab]
            if self.selected_tab == "cpu":
                vals = list(self.monitor.cpu_history)
                m_val = 100.0
                self.pane_title_lbl.configure(text="CPU")
                self.pane_hw_lbl.configure(
                    text=f"Danbooru Wallpaper Process Tree ({self.monitor.logical_cpus} Logical Processors)"
                )
                self.axis_top_left_lbl.configure(text="% Utilization")
                self.axis_top_right_lbl.configure(text="100%")
            elif self.selected_tab == "ram":
                vals = list(self.monitor.ram_pct_history)
                m_val = 100.0
                self.pane_title_lbl.configure(text="Memory")
                self.pane_hw_lbl.configure(
                    text=f"Working Set + WebView2 Buffers ({total_phys_gb:.1f} GB / {int(total_phys_mb):,} MB System RAM)"
                )
                self.axis_top_left_lbl.configure(
                    text=f"% of Total System Memory ({self.monitor.current_ram_mb:.1f} MB / {int(total_phys_mb):,} MB)"
                )
                self.axis_top_right_lbl.configure(text=f"100% ({total_phys_gb:.1f} GB)")
            else:
                vals = list(self.monitor.gpu_history)
                m_val = 100.0
                self.pane_title_lbl.configure(text="GPU 0")
                self.pane_hw_lbl.configure(text=self.monitor.gpu_name)
                self.axis_top_left_lbl.configure(text="% Utilization (3D / Compositor / Video Decode)")
                self.axis_top_right_lbl.configure(text="100%")

            self._draw_task_manager_series(
                self.graph_canvas,
                0,
                0,
                cw,
                ch,
                vals,
                m_val,
                spec["stroke_dark"] if is_dark else spec["stroke_light"],
                spec["fill_dark"] if is_dark else spec["fill_light"],
                spec["grid_dark"] if is_dark else spec["grid_light"],
                draw_grid=True,
            )

        # 3. Update Bottom Task Manager Telemetry Readout Labels
        if self.selected_tab == "ram":
            self.stat_blocks["primary"]["k_lbl"].configure(text="Working Set (RAM)")
            self.stat_blocks["primary"]["v_lbl"].configure(
                text=f"{self.monitor.current_ram_mb:.1f} MB ({self.monitor.current_ram_pct:.1f}%)"
            )
            self.stat_blocks["secondary"]["k_lbl"].configure(text="Private Commit")
            self.stat_blocks["secondary"]["v_lbl"].configure(
                text=f"{self.monitor.current_private_mb:.1f} MB"
            )
            self.stat_blocks["peak"]["k_lbl"].configure(text="Peak Working Set")
            self.stat_blocks["peak"]["v_lbl"].configure(text=f"{self.monitor.peak_ram_mb:.1f} MB")
        elif self.selected_tab == "gpu":
            self.stat_blocks["primary"]["k_lbl"].configure(text="GPU Utilization")
            self.stat_blocks["primary"]["v_lbl"].configure(text=f"{self.monitor.current_gpu_pct:.1f}%")
            self.stat_blocks["secondary"]["k_lbl"].configure(text="Wallpaper Memory")
            self.stat_blocks["secondary"]["v_lbl"].configure(text=f"{self.monitor.current_ram_mb:.1f} MB")
            self.stat_blocks["peak"]["k_lbl"].configure(text="Peak GPU Load")
            self.stat_blocks["peak"]["v_lbl"].configure(text=f"{self.monitor.peak_gpu_pct:.1f}%")
        else:
            self.stat_blocks["primary"]["k_lbl"].configure(text="CPU Utilization")
            self.stat_blocks["primary"]["v_lbl"].configure(text=f"{self.monitor.current_cpu_pct:.1f}%")
            self.stat_blocks["secondary"]["k_lbl"].configure(text="Wallpaper Memory")
            self.stat_blocks["secondary"]["v_lbl"].configure(
                text=f"{self.monitor.current_ram_mb:.1f} MB"
            )
            self.stat_blocks["peak"]["k_lbl"].configure(text="Peak CPU / GPU")
            self.stat_blocks["peak"]["v_lbl"].configure(
                text=f"{self.monitor.peak_cpu_pct:.1f}% / {self.monitor.peak_gpu_pct:.1f}%"
            )

        self.stat_blocks["procs"]["k_lbl"].configure(text="Processes / Threads")
        self.stat_blocks["procs"]["v_lbl"].configure(
            text=f"{self.monitor.process_count} / {self.monitor.thread_count}"
        )

    def _tick_telemetry(self):
        if not self.is_open:
            return
        if not self._graph_paused:
            self.monitor.sample()
            self._grid_scroll_step += 1
            self._redraw_all_graphs()
        self._tick_job = self.after(1000, self._tick_telemetry)

    def start_move(self, event):
        self._drag_x = event.x
        self._drag_y = event.y

    def do_move(self, event):
        x = self.winfo_x() + (event.x - self._drag_x)
        y = self.winfo_y() + (event.y - self._drag_y)
        self.geometry(f"+{x}+{y}")

    def close_resource_graph(self):
        self.is_open = False
        if self._tick_job is not None:
            try:
                self.after_cancel(self._tick_job)
            except Exception:
                pass
            self._tick_job = None
        try:
            self.monitor.close()
        except Exception:
            pass
        self.destroy()


class SettingsDialog(tk.Toplevel):
    """
    Unified tabbed settings dialog containing:
    - Top Header: 'Resource Graph' button launching the Windows Task Manager Performance pop-out
    - Tab 1: Credentials (account credentials, Light/Dark Mode toggle)
    - Tab 2: Display (per-screen selector, enable checkbox, per-screen Refresh/Prev/Next/Pause controls,
             Danbooru category-colored TAGS search box with below-input suggestions & saved searches,
             permanent 4-layer scrollable box showing all tags of the selected screen's most recently
             displayed media, and dynamic mode-specific section visibility)
    - Tab 3: Logs (PAUSE APPLICATION master button, Glossary button, Clear Logs button, smart log history)
    """
    NUMERIC_SPECS = {
        "targetfps": {
            "label": "Target FPS (15 – 240):",
            "min": 15,
            "max": 240,
            "default": 60,
            "is_float": False,
            "precision": 0,
        },
        "scrollspeed": {
            "label": "Scroll Speed (0.1 – 600 px/s):",
            "min": 0.1,
            "max": 600.0,
            "default": 120,
            "is_float": True,
            "precision": 2,
        },
        "gapsize": {
            "label": "Image Gap (0 – 64 px):",
            "min": 0,
            "max": 64,
            "default": 12,
            "is_float": False,
            "precision": 0,
        },
        "dropspeed": {
            "label": "Drop Speed (0.2 – 4.0):",
            "min": 0.2,
            "max": 4.0,
            "default": 1.0,
            "is_float": True,
            "precision": 2,
        },
        "minsize": {
            "label": "Minimum Size (120 – 600 px):",
            "min": 120,
            "max": 600,
            "default": 220,
            "is_float": False,
            "precision": 0,
        },
        "maxsize": {
            "label": "Maximum Size (150 – 900 px):",
            "min": 150,
            "max": 900,
            "default": 440,
            "is_float": False,
            "precision": 0,
        },
        "dropdelay": {
            "label": "Spawn/Drop Delay (0 – 600 s):",
            "min": 0,
            "max": 600,
            "default": 0,
            "is_float": False,
            "precision": 0,
        },
        "slideshowfade": {
            "label": "Fade Transition (0 – 10 [0s – 1.0s]):",
            "min": 0.0,
            "max": 10.0,
            "default": 5.0,
            "is_float": True,
            "precision": 1,
        },
        "slideshowduration": {
            "label": "Slide Display Time (0 – 600 s):",
            "min": 0,
            "max": 600,
            "default": 10,
            "is_float": False,
            "precision": 0,
        },
        "masonrytiles": {
            "label": "Target Tile Count (4 – 36):",
            "min": 4,
            "max": 36,
            "default": 12,
            "is_float": False,
            "precision": 0,
        },
        "masonrygap": {
            "label": "Gap (0 – 10 px):",
            "min": 0,
            "max": 10,
            "default": 4,
            "is_float": False,
            "precision": 0,
        },
        "masonrydelay": {
            "label": "Delay (1 – 60 s):",
            "min": 1,
            "max": 60,
            "default": 5,
            "is_float": False,
            "precision": 0,
        },
    }

    def __init__(self, parent, on_save_credentials_callback, initial_values=None):
        super().__init__(parent)
        self.on_save_credentials_callback = on_save_credentials_callback
        self.is_open = True
        self._drag_x = 0
        self._drag_y = 0
        self._fill_cooldown_remaining = 0
        self._fill_timer_job = None
        self._live_apply_job = None
        self._status_poll_job = None
        self._debounce_timer = None
        self._auto_tag_refresh_job = None
        self._saved_marquee_job = None
        self._saved_marquee_items = []
        self._toast_hide_job = None
        self._nav_cooldown_job = None
        self._tag_flash_job = None
        self._last_applied_tags_by_screen = {}
        self._suggest_req_id = 0
        self._nav_cooldown_active = False
        self._syncing_controls = False
        self._last_rendered_post_id = None
        self._last_rendered_screen_id = None
        self._last_rendered_tags_sig = None
        self._current_displayed_post_id = None

        self._themed_frames = []
        self._themed_borders = []
        self._themed_labels_dark = []
        self._themed_labels_muted = []
        self._themed_entries = []
        self._themed_neutral_btns = []

        self.overrideredirect(True)
        self.attributes("-alpha", 0.97)
        self.attributes("-topmost", True)

        pal = THEME_PALETTES[CURRENT_THEME]
        self.bg_base = pal["bg_base"]
        self.input_bg = pal["input_bg"]
        self.border_col = pal["border_col"]
        self.text_dark = pal["text_dark"]
        self.text_muted = pal["text_muted"]

        self.configure(bg=self.border_col)

        width = 650
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        height = min(760, max(700, sh - 40))

        cfg = load_app_config()
        default_x = max(20, (sw - width) // 2)
        default_y = max(20, (sh - height) // 2)
        x = max(20, min(int(cfg.get("settings_pos_x", default_x)), sw - width - 20))
        y = max(20, min(int(cfg.get("settings_pos_y", default_y)), sh - height - 20))
        self.geometry(f"{width}x{height}+{x}+{y}")

        self.container = tk.Frame(self, bg=self.bg_base, highlightthickness=1, highlightbackground=self.border_col)
        self.container.pack(fill="both", expand=True, padx=1, pady=1)
        self._themed_borders.append(self.container)

        self.header = tk.Frame(self.container, bg=self.bg_base)
        self.header.pack(fill="x", padx=14, pady=(10, 6))
        self._themed_frames.append(self.header)

        self.title_lbl = tk.Label(
            self.header, text="⚙ APPLICATION SETTINGS", font=("Segoe UI", 10, "bold"),
            fg=self.text_dark, bg=self.bg_base
        )
        self.title_lbl.pack(side="left")
        self._themed_labels_dark.append(self.title_lbl)

        self.close_btn = tk.Label(
            self.header, text="✕", font=("Segoe UI", 10, "bold"),
            fg=self.text_muted, bg=self.bg_base, cursor="hand2"
        )
        self.close_btn.pack(side="right")
        self.close_btn.bind("<Button-1>", lambda e: self.close_dialog())
        self._themed_labels_muted.append(self.close_btn)

        self.resource_graph_btn = tk.Button(
            self.header,
            text="📊 Resource Graph",
            bg="#0067c0",
            fg="#ffffff",
            activebackground="#005da6",
            activeforeground="#ffffff",
            font=("Segoe UI", 8, "bold"),
            bd=0,
            relief="flat",
            padx=12,
            pady=3,
            cursor="hand2",
            command=self.open_resource_graph_dialog,
        )
        self.resource_graph_btn.pack(side="right", padx=(0, 12))

        self.header.bind("<Button-1>", self.start_move)
        self.header.bind("<B1-Motion>", self.do_move)
        self.title_lbl.bind("<Button-1>", self.start_move)
        self.title_lbl.bind("<B1-Motion>", self.do_move)

        self.style = ttk.Style(self)

        # Custom Theme-Aware Tab Bar (replaces Windows uxtheme white TNotebook tabs;
        # adds a 1px contrasting white outline in Dark Mode and a 2px gap between each tab)
        self.tab_bar_frame = tk.Frame(self.container, bg=self.bg_base)
        self.tab_bar_frame.pack(fill="x", padx=12, pady=(4, 0))
        self._themed_frames.append(self.tab_bar_frame)

        self.tab_content_holder = tk.Frame(
            self.container,
            bg=self.bg_base,
            highlightthickness=1,
            highlightbackground=self.border_col,
        )
        self.tab_content_holder.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        self._themed_frames.append(self.tab_content_holder)
        self._themed_borders.append(self.tab_content_holder)

        self.tab_credentials = tk.Frame(self.tab_content_holder, bg=self.bg_base)
        self.tab_display = tk.Frame(self.tab_content_holder, bg=self.bg_base)
        self.tab_logs = tk.Frame(self.tab_content_holder, bg=self.bg_base)
        self._themed_frames.extend([self.tab_credentials, self.tab_display, self.tab_logs])

        self._tab_frames_by_key = {
            "credentials": self.tab_credentials,
            "display": self.tab_display,
            "logs": self.tab_logs,
        }
        self._tab_header_widgets = {}
        if _RUNTIME_LAST_SETTINGS_TAB in ("credentials", "display", "logs"):
            self.active_settings_tab = _RUNTIME_LAST_SETTINGS_TAB
        else:
            self.active_settings_tab = "display" if (USERNAME and API_KEY) else "credentials"

        for tab_key, tab_title in (
            ("credentials", "Credentials"),
            ("display", "Display"),
            ("logs", "Logs"),
        ):
            tab_border = tk.Frame(
                self.tab_bar_frame,
                bg=pal["btn_bg"],
                highlightthickness=1,
                highlightbackground="#ffffff" if CURRENT_THEME == "dark" else self.border_col,
                highlightcolor="#ffffff" if CURRENT_THEME == "dark" else self.border_col,
            )
            # 2px space between each tab so they are never smashed together
            tab_border.pack(side="left", padx=(0, 2), pady=(0, 2))

            tab_lbl = tk.Label(
                tab_border,
                text=tab_title,
                font=("Segoe UI", 9, "bold"),
                padx=16,
                pady=5,
                cursor="hand2",
            )
            tab_lbl.pack(fill="both", expand=True)
            tab_lbl.bind("<Button-1>", lambda e, k=tab_key: self._select_settings_tab(k))
            tab_border.bind("<Button-1>", lambda e, k=tab_key: self._select_settings_tab(k))
            self._tab_header_widgets[tab_key] = (tab_border, tab_lbl)

        self.saved_list = load_saved_searches()
        self.suggest_labels = []
        self.suggest_items = []
        self.selected_index = -1

        self._build_credentials_tab(initial_values or {})
        self._build_display_tab()
        self._build_logs_tab()

        self._select_settings_tab(self.active_settings_tab)
        self.apply_theme()
        self.bind("<Escape>", self._on_escape_pressed)
        self.bind("<FocusOut>", self._on_dialog_focus_out)
        self._poll_display_status()

    def _select_settings_tab(self, tab_key: str):
        """Switches the active Application Settings tab, records it for runtime reopen, and refreshes tab styling."""
        global _RUNTIME_LAST_SETTINGS_TAB
        if tab_key not in self._tab_frames_by_key:
            return
        self.active_settings_tab = tab_key
        _RUNTIME_LAST_SETTINGS_TAB = tab_key
        self._hide_all_popups()
        for k, frm in self._tab_frames_by_key.items():
            if k != tab_key:
                frm.pack_forget()
        self._tab_frames_by_key[tab_key].pack(fill="both", expand=True)
        self._update_settings_tabs_theme()

    def _update_settings_tabs_theme(self):
        """
        Styles the Application Settings tabs to match the active theme (Light or Dark Mode).
        In Dark Mode, tabs use dark backgrounds (#232329 inactive / #0067c0 active) with a
        1px contrasting white outline (#ffffff) and 2px spacing between tabs.
        """
        is_dark = (CURRENT_THEME == "dark")
        pal = THEME_PALETTES[CURRENT_THEME]
        for tab_key, (tab_border, tab_lbl) in self._tab_header_widgets.items():
            is_active = (tab_key == self.active_settings_tab)
            if is_dark:
                outline_col = "#ffffff"
                bg_col = "#0067c0" if is_active else pal["btn_bg"]
                fg_col = "#ffffff" if is_active else self.text_dark
            else:
                outline_col = "#005da6" if is_active else self.border_col
                bg_col = "#0067c0" if is_active else pal["btn_bg"]
                fg_col = "#ffffff" if is_active else self.text_dark
            try:
                tab_border.configure(
                    bg=bg_col,
                    highlightthickness=1,
                    highlightbackground=outline_col,
                    highlightcolor=outline_col,
                )
                tab_lbl.configure(bg=bg_col, fg=fg_col)
            except tk.TclError:
                pass

    # -------------------------------------------------------------------------
    # TAB 1: CREDENTIALS (PURE API AUTH + LIGHT/DARK MODE BUTTON)
    # -------------------------------------------------------------------------
    def _build_credentials_tab(self, vals):
        pad_frame = tk.Frame(self.tab_credentials, bg=self.bg_base)
        pad_frame.pack(fill="both", expand=True, padx=16, pady=14)
        self._themed_frames.append(pad_frame)

        sec_lbl = tk.Label(
            pad_frame, text="DANBOORU API CREDENTIALS (HTTP/2 + DoH)",
            font=("Segoe UI", 8, "bold"), fg=self.text_muted, bg=self.bg_base
        )
        sec_lbl.pack(anchor="w", pady=(0, 8))
        self._themed_labels_muted.append(sec_lbl)

        self.cred_entries = {}
        fields = [
            ("USERNAME", "Username:"),
            ("USER_ID", "User ID:"),
            ("API_KEY", "API Key (DPAPI):"),
        ]

        for key, label_text in fields:
            row = tk.Frame(pad_frame, bg=self.bg_base)
            row.pack(fill="x", pady=5)
            self._themed_frames.append(row)

            lbl = tk.Label(
                row, text=label_text, width=16, anchor="w",
                font=("Segoe UI", 9), fg=self.text_dark, bg=self.bg_base
            )
            lbl.pack(side="left")
            self._themed_labels_dark.append(lbl)

            entry_box = tk.Frame(row, bg=self.input_bg, highlightthickness=1, highlightbackground=self.border_col)
            entry_box.pack(side="right", fill="x", expand=True)
            self._themed_borders.append(entry_box)

            entry = tk.Entry(
                entry_box, bg=self.input_bg, fg=self.text_dark, insertbackground=self.text_dark,
                bd=0, font=("Segoe UI", 9), relief="flat"
            )
            entry.pack(fill="x", padx=6, pady=4)
            if key == "API_KEY":
                entry.configure(show="•")
            if vals.get(key):
                entry.insert(0, vals[key])
            self.cred_entries[key] = entry
            self._themed_entries.append((entry_box, entry))

        self.cred_sep = tk.Frame(pad_frame, bg=self.border_col, height=1)
        self.cred_sep.pack(fill="x", pady=14)

        # Light Mode / Dark Mode switch button on Credentials tab
        theme_row = tk.Frame(pad_frame, bg=self.bg_base)
        theme_row.pack(fill="x", pady=8)
        self._themed_frames.append(theme_row)

        theme_lbl = tk.Label(
            theme_row, text="Application Theme:", width=16, anchor="w",
            font=("Segoe UI", 9), fg=self.text_dark, bg=self.bg_base
        )
        theme_lbl.pack(side="left")
        self._themed_labels_dark.append(theme_lbl)

        self.theme_btn = tk.Button(
            theme_row,
            text="Dark Mode" if CURRENT_THEME == "light" else "Light Mode",
            fg=self.text_dark, bg="#e8e8ed", activebackground="#dcdce0",
            bd=0, relief="flat", font=("Segoe UI", 9, "bold"), cursor="hand2",
            padx=14, pady=4, command=self.toggle_theme_mode
        )
        self.theme_btn.pack(side="left")
        self._themed_neutral_btns.append(self.theme_btn)

        btn_row = tk.Frame(pad_frame, bg=self.bg_base)
        btn_row.pack(fill="x", side="bottom", pady=(10, 0))
        self._themed_frames.append(btn_row)

        save_cred_btn = tk.Button(
            btn_row, text="Save Credentials", bg="#0067c0", fg="#ffffff",
            activebackground="#005da6", activeforeground="#ffffff",
            font=("Segoe UI", 9, "bold"), bd=0, relief="flat",
            padx=20, pady=6, cursor="hand2", command=self.save_credentials_only
        )
        save_cred_btn.pack(side="right")

    def toggle_theme_mode(self):
        global CURRENT_THEME
        CURRENT_THEME = "dark" if CURRENT_THEME == "light" else "light"
        cfg = load_app_config()
        cfg["theme"] = CURRENT_THEME
        store_app_config(cfg)
        self.apply_theme()
        if GLOSSARY_DIALOG_INSTANCE and getattr(GLOSSARY_DIALOG_INSTANCE, "is_open", False):
            try:
                GLOSSARY_DIALOG_INSTANCE.apply_theme()
            except Exception:
                pass
        if RESOURCE_GRAPH_DIALOG_INSTANCE and getattr(RESOURCE_GRAPH_DIALOG_INSTANCE, "is_open", False):
            try:
                RESOURCE_GRAPH_DIALOG_INSTANCE.apply_theme()
                RESOURCE_GRAPH_DIALOG_INSTANCE._redraw_all_graphs()
            except Exception:
                pass
        log_event("ui", f"Switched application theme to {CURRENT_THEME.upper()} mode.")

    def save_credentials_only(self):
        user = self.cred_entries["USERNAME"].get().strip()
        uid = self.cred_entries["USER_ID"].get().strip()
        key = self.cred_entries["API_KEY"].get().strip()
        self.on_save_credentials_callback(user, uid, key)

    # -------------------------------------------------------------------------
    # TAB 2: DISPLAY (PER-SCREEN SEARCH, PLAYBACK CONTROLS, 4-LAYER MEDIA TAGS,
    #                 AND DYNAMIC PER-MODE SECTIONS)
    # -------------------------------------------------------------------------
    def _build_display_tab(self):
        self.prop_entries = {}
        self.prop_sliders = {}
        self.prop_vars = {}

        pad_frame = tk.Frame(self.tab_display, bg=self.bg_base)
        pad_frame.pack(fill="both", expand=True, padx=16, pady=10)
        self._themed_frames.append(pad_frame)

        global _RUNTIME_LAST_SELECTED_SCREEN_ID
        screens_snap = refresh_connected_screens_preserving_ids()
        self.screen_map = {s["label"]: s["id"] for s in screens_snap}
        id_to_label = {s["id"]: s["label"] for s in screens_snap}
        screen_labels = [s["label"] for s in screens_snap]

        initial_screen_label = screen_labels[0]
        if _RUNTIME_LAST_SELECTED_SCREEN_ID and _RUNTIME_LAST_SELECTED_SCREEN_ID in id_to_label:
            initial_screen_label = id_to_label[_RUNTIME_LAST_SELECTED_SCREEN_ID]
        else:
            _RUNTIME_LAST_SELECTED_SCREEN_ID = self.screen_map.get(initial_screen_label, "screen_1")

        # 1. Screen Selector Dropdown + Resync Displays Action
        screen_row = tk.Frame(pad_frame, bg=self.bg_base)
        screen_row.pack(fill="x", pady=2)
        self._themed_frames.append(screen_row)

        scr_lbl = tk.Label(
            screen_row, text="Select Screen:", width=26, anchor="w",
            font=("Segoe UI", 9, "bold"), fg=self.text_dark, bg=self.bg_base
        )
        scr_lbl.pack(side="left")
        self._themed_labels_dark.append(scr_lbl)

        self.resync_displays_btn = tk.Button(
            screen_row,
            text="Resync Displays",
            fg=self.text_dark,
            bg=THEME_PALETTES[CURRENT_THEME]["btn_bg"],
            activebackground=THEME_PALETTES[CURRENT_THEME]["btn_active"],
            activeforeground=self.text_dark,
            font=("Segoe UI", 8, "bold"),
            bd=0,
            relief="flat",
            padx=10,
            pady=3,
            cursor="hand2",
            command=self._on_resync_displays_clicked,
        )
        self.resync_displays_btn.pack(side="right", padx=(6, 0))
        self._themed_neutral_btns.append(self.resync_displays_btn)

        self.selected_screen_label = tk.StringVar(self, value=initial_screen_label)
        self.screen_combo = ttk.Combobox(
            screen_row, textvariable=self.selected_screen_label,
            values=screen_labels, state="readonly"
        )
        self.screen_combo.pack(side="right", fill="x", expand=True)
        self.screen_combo.bind("<<ComboboxSelected>>", self._on_screen_selection_changed)

        # 2. Display Wallpaper Slide Switch (Left) & Pause During Full Screen Application Slide Switch (Right)
        enable_row = tk.Frame(pad_frame, bg=self.bg_base)
        enable_row.pack(fill="x", pady=(3, 2))
        self._themed_frames.append(enable_row)

        self.screen_enabled_var = tk.BooleanVar(self, value=True)
        self.screen_enable_switch = tk.Canvas(
            enable_row,
            width=42,
            height=22,
            bg=self.bg_base,
            bd=0,
            highlightthickness=0,
            cursor="hand2",
        )
        self.screen_enable_switch.pack(side="left", padx=(0, 8))
        self.screen_enable_switch.bind("<Button-1>", self._on_toggle_screen_enable_switch)

        self.screen_enable_lbl = tk.Label(
            enable_row,
            text="Display wallpaper on this screen",
            font=("Segoe UI", 9, "bold"),
            fg=self.text_dark,
            bg=self.bg_base,
            cursor="hand2",
            anchor="w",
        )
        self.screen_enable_lbl.pack(side="left")
        self.screen_enable_lbl.bind("<Button-1>", self._on_toggle_screen_enable_switch)
        self._themed_labels_dark.append(self.screen_enable_lbl)
        self._draw_screen_enable_switch()

        # Right side of enable_row: "Pause during full screen application" On/Off Switch + Title
        self.fullscreen_pause_wrap = tk.Frame(enable_row, bg=self.bg_base)
        self.fullscreen_pause_wrap.pack(side="right")
        self._themed_frames.append(self.fullscreen_pause_wrap)

        self.pause_fullscreen_var = tk.BooleanVar(self, value=True)
        self.fullscreen_pause_switch = tk.Canvas(
            self.fullscreen_pause_wrap,
            width=42,
            height=22,
            bg=self.bg_base,
            bd=0,
            highlightthickness=0,
            cursor="hand2",
        )
        self.fullscreen_pause_switch.pack(side="left", padx=(0, 8))
        self.fullscreen_pause_switch.bind("<Button-1>", self._on_toggle_fullscreen_pause_switch)

        self.fullscreen_pause_lbl = tk.Label(
            self.fullscreen_pause_wrap,
            text="Pause during full screen application",
            font=("Segoe UI", 9, "bold"),
            fg=self.text_dark,
            bg=self.bg_base,
            cursor="hand2",
            anchor="w",
        )
        self.fullscreen_pause_lbl.pack(side="left")
        self.fullscreen_pause_lbl.bind("<Button-1>", self._on_toggle_fullscreen_pause_switch)
        self._themed_labels_dark.append(self.fullscreen_pause_lbl)
        self._draw_fullscreen_pause_switch()

        # 2b. Per-Screen V-Sync Button ("V-Sync On" / "V-Sync Off") & Conditional Target FPS Input Box
        self.vsync_row = tk.Frame(pad_frame, bg=self.bg_base)
        self.vsync_row.pack(fill="x", pady=(1, 4))
        self._themed_frames.append(self.vsync_row)

        self.vsync_var = tk.BooleanVar(self, value=True)
        self.vsync_btn = tk.Button(
            self.vsync_row,
            text="V-Sync On",
            bg="#0067c0",
            fg="#ffffff",
            activebackground="#005da6",
            activeforeground="#ffffff",
            font=("Segoe UI", 9, "bold"),
            bd=0,
            relief="flat",
            padx=14,
            pady=3,
            cursor="hand2",
            command=self._on_toggle_vsync,
        )
        self.vsync_btn.pack(side="left")

        self.target_fps_subframe = tk.Frame(self.vsync_row, bg=self.bg_base)
        self._themed_frames.append(self.target_fps_subframe)

        self.target_fps_lbl = tk.Label(
            self.target_fps_subframe,
            text="Target FPS (15 – 240):",
            font=("Segoe UI", 9, "bold"),
            fg=self.text_dark,
            bg=self.bg_base,
        )
        self.target_fps_lbl.pack(side="left", padx=(12, 6))
        self._themed_labels_dark.append(self.target_fps_lbl)

        fps_box = tk.Frame(
            self.target_fps_subframe,
            bg=self.input_bg,
            highlightthickness=1,
            highlightbackground=self.border_col,
        )
        fps_box.pack(side="left")
        self._themed_borders.append(fps_box)

        fps_entry = tk.Entry(
            fps_box,
            bg=self.input_bg,
            fg=self.text_dark,
            insertbackground=self.text_dark,
            bd=0,
            width=6,
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            justify="center",
        )
        fps_entry.pack(fill="x", padx=6, pady=2)
        fps_entry.insert(0, "60")
        self._themed_entries.append((fps_box, fps_entry))

        fps_var = tk.DoubleVar(self, value=60.0)
        fps_entry.bind("<KeyRelease>", lambda e, k="targetfps": self._on_entry_key_release(k, e))
        fps_entry.bind("<FocusOut>", lambda e, k="targetfps": self._on_entry_commit(k, e))
        fps_entry.bind("<Return>", lambda e, k="targetfps": self._on_entry_commit(k, e))

        self.prop_entries["targetfps"] = fps_entry
        self.prop_vars["targetfps"] = fps_var
        self._update_vsync_ui_state()

        # 3. Per-Screen Search & Playback Sub-Panel (No Minimize Button)
        pal = THEME_PALETTES[CURRENT_THEME]
        self.search_subpanel = tk.Frame(
            pad_frame, bg=self.bg_base, highlightthickness=1, highlightbackground=self.border_col
        )
        self.search_subpanel.pack(fill="x", pady=(2, 6))
        self._themed_frames.append(self.search_subpanel)
        self._themed_borders.append(self.search_subpanel)

        search_inner = tk.Frame(self.search_subpanel, bg=self.bg_base)
        search_inner.pack(fill="x", padx=10, pady=8)
        self._themed_frames.append(search_inner)

        # 3a. Control Row ABOVE the TAGS Search Bar
        # Standardized 28px height across Status Indicator, Saved Searches button, Refresh, Previous, Next, and Pause
        self.search_controls_row = tk.Frame(search_inner, bg=self.bg_base, height=28)
        self.search_controls_row.pack(fill="x", pady=(0, 6))
        self._themed_frames.append(self.search_controls_row)

        # Left: Page & Pool Indicator (standardized 28px height)
        self.status_frame = tk.Frame(
            self.search_controls_row,
            bg=pal["btn_bg"],
            highlightthickness=1,
            highlightbackground=self.border_col,
            width=148,
            height=28,
        )
        self.status_frame.pack(side="left", padx=(0, 4))
        self.status_frame.pack_propagate(False)
        self._themed_borders.append(self.status_frame)

        self.status_label = tk.Label(
            self.status_frame,
            text="● Ready",
            fg=self.text_muted,
            bg=pal["btn_bg"],
            font=("Segoe UI", 8, "bold"),
            padx=8,
        )
        self.status_label.pack(fill="both", expand=True)

        # Right: Pause, Next, Previous, Refresh (packed right-to-left, all standardized to 28px height)
        self.pause_btn_frame = tk.Frame(
            self.search_controls_row,
            bg=pal["btn_bg"],
            highlightthickness=1,
            highlightbackground=self.border_col,
            width=68,
            height=28,
        )
        self.pause_btn_frame.pack(side="right", padx=(2, 0))
        self.pause_btn_frame.pack_propagate(False)
        self._themed_borders.append(self.pause_btn_frame)

        self.pause_btn = tk.Button(
            self.pause_btn_frame,
            text="PAUSE",
            fg=self.text_dark,
            bg=pal["btn_bg"],
            activebackground=pal["btn_active"],
            bd=0,
            relief="flat",
            font=("Segoe UI", 8, "bold"),
            cursor="hand2",
            command=self.toggle_selected_screen_pause,
        )
        self.pause_btn.pack(fill="both", expand=True)

        self.next_btn_frame = tk.Frame(
            self.search_controls_row,
            bg=pal["btn_bg"],
            highlightthickness=1,
            highlightbackground=self.border_col,
            width=28,
            height=28,
        )
        self.next_btn_frame.pack(side="right", padx=(2, 2))
        self.next_btn_frame.pack_propagate(False)
        self._themed_borders.append(self.next_btn_frame)

        self.next_btn = tk.Button(
            self.next_btn_frame,
            text="▶",
            fg=self.text_dark,
            bg=pal["btn_bg"],
            activebackground=pal["btn_active"],
            activeforeground="#0067c0",
            bd=0,
            relief="flat",
            font=("Segoe UI", 8, "bold"),
            cursor="hand2",
            command=self.next_media_for_selected_screen,
        )
        self.next_btn.pack(fill="both", expand=True)

        self.prev_btn_frame = tk.Frame(
            self.search_controls_row,
            bg=pal["btn_bg"],
            highlightthickness=1,
            highlightbackground=self.border_col,
            width=28,
            height=28,
        )
        self.prev_btn_frame.pack(side="right", padx=(2, 2))
        self.prev_btn_frame.pack_propagate(False)
        self._themed_borders.append(self.prev_btn_frame)

        self.prev_btn = tk.Button(
            self.prev_btn_frame,
            text="◀",
            fg=self.text_dark,
            bg=pal["btn_bg"],
            activebackground=pal["btn_active"],
            activeforeground="#0067c0",
            bd=0,
            relief="flat",
            font=("Segoe UI", 8, "bold"),
            cursor="hand2",
            command=self.previous_media_for_selected_screen,
        )
        self.prev_btn.pack(fill="both", expand=True)

        self.refresh_btn_frame = tk.Frame(
            self.search_controls_row,
            bg=pal["btn_bg"],
            highlightthickness=1,
            highlightbackground=self.border_col,
            width=32,
            height=28,
        )
        self.refresh_btn_frame.pack(side="right", padx=(4, 2))
        self.refresh_btn_frame.pack_propagate(False)
        self._themed_borders.append(self.refresh_btn_frame)

        self.refresh_btn = tk.Button(
            self.refresh_btn_frame,
            text="⟳",
            fg=self.text_dark,
            bg=pal["btn_bg"],
            activebackground=pal["btn_active"],
            activeforeground="#0067c0",
            bd=0,
            relief="flat",
            font=("Segoe UI", 10, "bold"),
            cursor="hand2",
            command=self.immediate_refresh_selected_screen,
        )
        self.refresh_btn.pack(fill="both", expand=True)

        # Center: Saved Searches button filling all width between Page/Pool indicator and Refresh button
        self.saved_searches_btn_frame = tk.Frame(
            self.search_controls_row,
            bg=pal["btn_bg"],
            highlightthickness=1,
            highlightbackground=self.border_col,
            height=28,
        )
        self.saved_searches_btn_frame.pack(side="left", fill="x", expand=True, padx=(2, 2))
        self.saved_searches_btn_frame.pack_propagate(False)
        self._themed_borders.append(self.saved_searches_btn_frame)

        self.saved_searches_btn = tk.Button(
            self.saved_searches_btn_frame,
            text="Saved Searches  ▾",
            fg=self.text_dark,
            bg=pal["btn_bg"],
            activebackground=pal["btn_active"],
            activeforeground=self.text_dark,
            bd=0,
            relief="flat",
            font=("Segoe UI", 8, "bold"),
            cursor="hand2",
            command=self.toggle_saved_dropdown,
        )
        self.saved_searches_btn.pack(fill="both", expand=True)

        # 3b. TAGS Search Row (Color-coded per-token Text widget with dynamic 1-5 line height scaling)
        self.tag_search_row = tk.Frame(search_inner, bg=self.bg_base)
        self.tag_search_row.pack(fill="x", pady=(0, 6))
        self._themed_frames.append(self.tag_search_row)

        self.tag_label = tk.Label(
            self.tag_search_row,
            text="TAGS =",
            fg=self.text_dark,
            bg=self.bg_base,
            font=("Segoe UI", 9, "bold"),
        )
        self.tag_label.pack(side="left", anchor="n", padx=(0, 6), pady=(5, 0))
        self._themed_labels_dark.append(self.tag_label)

        self.search_container = tk.Frame(
            self.tag_search_row,
            bg=self.input_bg,
            highlightthickness=1,
            highlightbackground=self.border_col,
        )
        self.search_container.pack(side="left", fill="x", expand=True)
        self._themed_borders.append(self.search_container)

        self.tag_input = tk.Text(
            self.search_container,
            bg=self.input_bg,
            fg=self.text_dark,
            insertbackground=self.text_dark,
            bd=0,
            width=20,
            height=1,
            wrap="word",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            padx=6,
            pady=4,
            undo=True,
        )
        self.tag_input.pack(side="left", fill="both", expand=True)

        self.tag_input.bind("<KeyRelease>", self._on_tag_input_key_release)
        self.tag_input.bind("<<Paste>>", lambda e: self.after(10, self._on_tag_input_clipboard_modified))
        self.tag_input.bind("<<Cut>>", lambda e: self.after(10, self._on_tag_input_clipboard_modified))
        self.tag_input.bind("<Configure>", lambda e: self._update_tag_input_height())
        self.tag_input.bind("<FocusIn>", self._on_tag_input_focus_in)
        self.tag_input.bind("<FocusOut>", self._on_tag_input_focus_out)
        self.tag_input.bind("<Down>", self._focus_suggestion_down)
        self.tag_input.bind("<Up>", self._focus_suggestion_up)
        self.tag_input.bind("<Return>", self._on_tag_input_enter)
        self.tag_input.bind("<Shift-Return>", self._on_tag_input_shift_enter)
        self.tag_input.bind("<Tab>", self._on_tag_input_tab)

        # Popups for Auto-Suggestions, Saved Searches, and 2s Toast Notification (below self.search_container)
        self.suggest_dropdown = tk.Toplevel(self)
        self.suggest_dropdown.overrideredirect(True)
        self.suggest_dropdown.attributes("-alpha", 0.96)
        self.suggest_dropdown.attributes("-topmost", True)
        self.suggest_dropdown.configure(bg=self.border_col)
        self.suggest_dropdown.withdraw()

        for i in range(5):
            lbl = tk.Label(
                self.suggest_dropdown,
                text="",
                anchor="w",
                fg=self.text_dark,
                bg=self.input_bg,
                font=("Segoe UI", 9, "bold"),
                padx=10,
                pady=5,
                cursor="hand2",
            )
            lbl.pack(fill="x", padx=1, pady=1)
            lbl.bind("<Enter>", lambda e, idx=i: self._highlight_suggestion_index(idx))
            lbl.bind("<Button-1>", lambda e, idx=i: self._select_suggestion(idx))
            self.suggest_labels.append(lbl)

        self.saved_dropdown = tk.Toplevel(self)
        self.saved_dropdown.overrideredirect(True)
        self.saved_dropdown.attributes("-alpha", 0.96)
        self.saved_dropdown.attributes("-topmost", True)
        self.saved_dropdown.configure(bg=self.border_col)
        self.saved_dropdown.withdraw()

        self.toast_popup = tk.Toplevel(self)
        self.toast_popup.overrideredirect(True)
        self.toast_popup.attributes("-alpha", 0.98)
        self.toast_popup.attributes("-topmost", True)
        self.toast_popup.configure(bg="#ffffff" if CURRENT_THEME == "dark" else "#005da6")
        self.toast_popup.withdraw()
        self.toast_label = tk.Label(
            self.toast_popup,
            text="",
            fg="#ffffff",
            bg="#d13438",
            font=("Segoe UI", 9, "bold"),
            padx=14,
            pady=6,
        )
        self.toast_label.pack(fill="both", expand=True, padx=1, pady=1)

        # 3c. Permanent 4-Layer Scrollable Displayed Media Tags Box below TAGS search box
        self.media_tags_hdr_row = tk.Frame(search_inner, bg=self.bg_base)
        self.media_tags_hdr_row.pack(fill="x", pady=(2, 2))
        self._themed_frames.append(self.media_tags_hdr_row)

        self.media_tags_hdr_lbl = tk.Label(
            self.media_tags_hdr_row,
            text="DISPLAYED MEDIA TAGS (CLICK TO ADD):",
            font=("Segoe UI", 9, "bold"),
            fg=self.text_muted,
            bg=self.bg_base,
        )
        self.media_tags_hdr_lbl.pack(side="left")
        self._themed_labels_muted.append(self.media_tags_hdr_lbl)

        post_link_fg = "#4da3ff" if CURRENT_THEME == "dark" else "#0067c0"
        self.media_tags_post_lbl = tk.Label(
            self.media_tags_hdr_row,
            text="",
            font=("Segoe UI", 9, "bold", "underline"),
            fg=post_link_fg,
            bg=self.bg_base,
            cursor="arrow",
        )
        self.media_tags_post_lbl.pack(side="right")
        self.media_tags_post_lbl.bind("<Button-1>", self._on_post_link_clicked)
        self.media_tags_post_lbl.bind("<Enter>", self._on_post_link_hover_enter)
        self.media_tags_post_lbl.bind("<Leave>", self._on_post_link_hover_leave)

        self.media_tags_box_frame = tk.Frame(
            search_inner,
            bg=self.input_bg,
            highlightthickness=1,
            highlightbackground=self.border_col,
        )
        self.media_tags_box_frame.pack(fill="x", expand=False)
        self._themed_borders.append(self.media_tags_box_frame)

        self.media_tags_text = tk.Text(
            self.media_tags_box_frame,
            bg=self.input_bg,
            fg=self.text_dark,
            wrap="word",
            height=4,
            font=("Segoe UI", 9, "bold"),
            bd=0,
            relief="flat",
            padx=6,
            pady=4,
            state="disabled",
            cursor="arrow",
        )
        self.media_tags_scrollbar = ttk.Scrollbar(
            self.media_tags_box_frame,
            orient="vertical",
            command=self.media_tags_text.yview,
        )
        self.media_tags_text.configure(yscrollcommand=self.media_tags_scrollbar.set)
        self.media_tags_scrollbar.pack(side="right", fill="y")
        self.media_tags_text.pack(side="left", fill="both", expand=True)

        self._configure_danbooru_color_tags()

        self.disp_sep = tk.Frame(pad_frame, bg=self.border_col, height=1)
        self.disp_sep.pack(fill="x", pady=4)

        mode_row = tk.Frame(pad_frame, bg=self.bg_base)
        mode_row.pack(fill="x", pady=3)
        self._themed_frames.append(mode_row)

        mode_lbl = tk.Label(
            mode_row, text="Display Mode:", width=26, anchor="w",
            font=("Segoe UI", 9, "bold"), fg=self.text_dark, bg=self.bg_base
        )
        mode_lbl.pack(side="left")
        self._themed_labels_dark.append(mode_lbl)

        self.mode_var = tk.StringVar(self, value="scroll")
        self.mode_combo = ttk.Combobox(
            mode_row,
            textvariable=self.mode_var,
            values=["scroll", "polaroid", "slideshow", "masonry"],
            state="readonly",
        )
        self.mode_combo.pack(side="right", fill="x", expand=True)
        self.mode_combo.bind(
            "<<ComboboxSelected>>",
            lambda e: (
                self._update_mode_sections_visibility(),
                self._update_fill_btn_state(),
                self._schedule_live_apply(),
            ),
        )

        # Container holding the mode-specific sections (only active mode is visible)
        self.mode_sections_holder = tk.Frame(pad_frame, bg=self.bg_base)
        self.mode_sections_holder.pack(fill="both", expand=True, pady=(6, 4))
        self._themed_frames.append(self.mode_sections_holder)

        # 1. SCROLL MODE SECTION
        self.scroll_section_frame = tk.Frame(self.mode_sections_holder, bg=self.bg_base)
        self._themed_frames.append(self.scroll_section_frame)

        scroll_hdr = tk.Label(
            self.scroll_section_frame, text="CONTINUOUS SCROLL SETTINGS",
            font=("Segoe UI", 8, "bold"), fg=self.text_muted, bg=self.bg_base
        )
        scroll_hdr.pack(anchor="w", pady=(4, 4))
        self._themed_labels_muted.append(scroll_hdr)

        dir_row = tk.Frame(self.scroll_section_frame, bg=self.bg_base)
        dir_row.pack(fill="x", pady=3)
        self._themed_frames.append(dir_row)

        dir_lbl = tk.Label(
            dir_row, text="Scroll Direction:", width=26, anchor="w",
            font=("Segoe UI", 9), fg=self.text_dark, bg=self.bg_base
        )
        dir_lbl.pack(side="left")
        self._themed_labels_dark.append(dir_lbl)

        self.dir_var = tk.StringVar(self, value="left")
        dir_combo = ttk.Combobox(
            dir_row,
            textvariable=self.dir_var,
            values=["left", "right", "up", "down"],
            state="readonly",
        )
        dir_combo.pack(side="right", fill="x", expand=True)
        dir_combo.bind("<<ComboboxSelected>>", lambda e: self._schedule_live_apply())

        for pkey in ("scrollspeed", "gapsize"):
            self._create_numeric_row(self.scroll_section_frame, pkey, self.NUMERIC_SPECS[pkey])

        # 2. POLAROID MODE SECTION
        self.polaroid_section_frame = tk.Frame(self.mode_sections_holder, bg=self.bg_base)
        self._themed_frames.append(self.polaroid_section_frame)

        polaroid_hdr = tk.Label(
            self.polaroid_section_frame, text="POLAROID SETTINGS",
            font=("Segoe UI", 8, "bold"), fg=self.text_muted, bg=self.bg_base
        )
        polaroid_hdr.pack(anchor="w", pady=(4, 4))
        self._themed_labels_muted.append(polaroid_hdr)

        for pkey in ("dropspeed", "minsize", "maxsize", "dropdelay"):
            self._create_numeric_row(self.polaroid_section_frame, pkey, self.NUMERIC_SPECS[pkey])

        fill_row = tk.Frame(self.polaroid_section_frame, bg=self.bg_base)
        fill_row.pack(fill="x", pady=(8, 4))
        self._themed_frames.append(fill_row)

        fill_lbl = tk.Label(
            fill_row, text="Polaroid Action:", width=26, anchor="w",
            font=("Segoe UI", 9), fg=self.text_dark, bg=self.bg_base
        )
        fill_lbl.pack(side="left")
        self._themed_labels_dark.append(fill_lbl)

        self.fill_screen_btn = tk.Button(
            fill_row, text="Fill Screen", bg="#0067c0", fg="#ffffff",
            activebackground="#005da6", activeforeground="#ffffff",
            disabledforeground="#a0a0a5",
            font=("Segoe UI", 9, "bold"), bd=0, relief="flat",
            padx=14, pady=4, cursor="hand2", command=self._on_fill_screen_clicked
        )
        self.fill_screen_btn.pack(side="left")

        self.fill_timer_lbl = tk.Label(
            fill_row, text="", font=("Segoe UI", 9, "bold"),
            fg="#d13438", bg=self.bg_base
        )
        self.fill_timer_lbl.pack(side="left", padx=(10, 0))
        self._themed_frames.append(self.fill_timer_lbl)

        # 3. SLIDESHOW MODE SECTION
        self.slideshow_section_frame = tk.Frame(self.mode_sections_holder, bg=self.bg_base)
        self._themed_frames.append(self.slideshow_section_frame)

        slide_hdr = tk.Label(
            self.slideshow_section_frame,
            text="FULLSCREEN SLIDESHOW SETTINGS (ORIENTATION-MATCHED)",
            font=("Segoe UI", 8, "bold"), fg=self.text_muted, bg=self.bg_base
        )
        slide_hdr.pack(anchor="w", pady=(4, 4))
        self._themed_labels_muted.append(slide_hdr)

        for pkey in ("slideshowfade", "slideshowduration"):
            self._create_numeric_row(self.slideshow_section_frame, pkey, self.NUMERIC_SPECS[pkey])

        # 4. MASONRY MODE SECTION
        self.masonry_section_frame = tk.Frame(self.mode_sections_holder, bg=self.bg_base)
        self._themed_frames.append(self.masonry_section_frame)

        masonry_hdr = tk.Label(
            self.masonry_section_frame,
            text="MASONRY LAYOUT SETTINGS (UNCROPPED 2D SCALEX FLIP & REFLOW)",
            font=("Segoe UI", 8, "bold"), fg=self.text_muted, bg=self.bg_base
        )
        masonry_hdr.pack(anchor="w", pady=(4, 4))
        self._themed_labels_muted.append(masonry_hdr)

        layout_row = tk.Frame(self.masonry_section_frame, bg=self.bg_base)
        layout_row.pack(fill="x", pady=(2, 5))
        layout_row.columnconfigure(0, weight=1, uniform="masonry_dual_btns")
        layout_row.columnconfigure(1, weight=1, uniform="masonry_dual_btns")
        self.masonry_layout_row = layout_row
        self._themed_frames.append(layout_row)

        self.masonry_layout_var = tk.StringVar(self, value="mondrian")
        self.masonry_edge_fill_var = tk.StringVar(self, value="blur")

        self.masonry_layout_btn = tk.Button(
            layout_row,
            text="Masonry Layout: Mondrian",
            bg="#0067c0",
            fg="#ffffff",
            activebackground="#005da6",
            activeforeground="#ffffff",
            font=("Segoe UI", 9, "bold"),
            bd=0,
            relief="flat",
            padx=12,
            pady=5,
            cursor="hand2",
            command=self._on_toggle_masonry_layout,
        )
        self.masonry_layout_btn.grid(row=0, column=0, sticky="ew", padx=(0, 4))

        self.masonry_edge_fill_btn = tk.Button(
            layout_row,
            text="Edge Fill: Blur",
            bg="#0067c0",
            fg="#ffffff",
            activebackground="#005da6",
            activeforeground="#ffffff",
            font=("Segoe UI", 9, "bold"),
            bd=0,
            relief="flat",
            padx=12,
            pady=5,
            cursor="hand2",
            command=self._on_toggle_masonry_edge_fill,
        )
        self.masonry_edge_fill_btn.grid(row=0, column=1, sticky="ew", padx=(4, 0))

        for pkey in ("masonrytiles", "masonrygap", "masonrydelay"):
            self._create_numeric_row(self.masonry_section_frame, pkey, self.NUMERIC_SPECS[pkey])

        btn_row = tk.Frame(pad_frame, bg=self.bg_base)
        btn_row.pack(fill="x", side="bottom", pady=(6, 0))
        self._themed_frames.append(btn_row)

        save_disp_btn = tk.Button(
            btn_row, text="Save & Apply Display Settings", bg="#0067c0", fg="#ffffff",
            activebackground="#005da6", activeforeground="#ffffff",
            font=("Segoe UI", 9, "bold"), bd=0, relief="flat",
            padx=18, pady=6, cursor="hand2", command=self.save_display_settings
        )
        save_disp_btn.pack(side="right")

        # Bind click-outside on Display tab background surfaces so clicking outside the Search TAGS box
        # removes focus from self.tag_input (stops the vertical pipe cursor blinking) and triggers auto-search.
        for bg_w in (
            pad_frame,
            screen_row,
            scr_lbl,
            enable_row,
            self.fullscreen_pause_wrap,
            self.vsync_row,
            self.target_fps_subframe,
            self.target_fps_lbl,
            self.search_subpanel,
            search_inner,
            self.search_controls_row,
            self.status_label,
            self.tag_search_row,
            self.tag_label,
            self.media_tags_hdr_row,
            self.media_tags_hdr_lbl,
            mode_row,
            mode_lbl,
            self.mode_sections_holder,
            self.scroll_section_frame,
            scroll_hdr,
            dir_row,
            dir_lbl,
            self.polaroid_section_frame,
            polaroid_hdr,
            fill_row,
            fill_lbl,
            self.slideshow_section_frame,
            slide_hdr,
            self.masonry_section_frame,
            masonry_hdr,
            layout_row,
            btn_row,
        ):
            try:
                bg_w.bind("<Button-1>", self._defocus_tag_input_on_outside_click, add="+")
            except Exception:
                pass

        try:
            self._load_screen_values_into_form(self._get_current_selected_screen_id())
        except Exception as e:
            log_event("ui", f"Warning loading initial screen values into SettingsDialog: {e}")
            self._update_mode_sections_visibility()

    # -------------------------------------------------------------------------
    # DANBOORU TAG COLORING, DYNAMIC HEIGHT SCALING, FOCUS-OUT AUTO-SEARCH,
    # SAVED SEARCHES DROPDOWN & 4-LAYER DISPLAYED MEDIA TAGS BOX
    # -------------------------------------------------------------------------
    def _defocus_tag_input_on_outside_click(self, event=None):
        """Moves keyboard focus away from self.tag_input when clicking outside so the blinking caret stops and <FocusOut> triggers."""
        if not self.is_open:
            return
        try:
            if self.focus_get() == self.tag_input:
                self.focus_set()
            if self.saved_dropdown.winfo_viewable():
                self._hide_saved_dropdown()
            if self.suggest_dropdown.winfo_viewable():
                self.hide_dropdown()
        except tk.TclError:
            pass

    def _is_tag_input_focused(self) -> bool:
        """Returns True if the vertical pipe cursor is currently active/blinking inside self.tag_input."""
        if not self.is_open:
            return False
        try:
            return self.focus_get() == self.tag_input
        except tk.TclError:
            return False

    def _on_tag_input_focus_in(self, event=None):
        """Called when the Search TAGS box gains focus (vertical pipe cursor starts blinking)."""
        self._cancel_auto_tag_refresh_timer()
        try:
            if self.saved_dropdown.winfo_viewable():
                self._hide_saved_dropdown()
        except tk.TclError:
            pass

    def _on_tag_input_focus_out(self, event=None):
        """
        Called when the Search TAGS box loses focus (vertical pipe cursor stops blinking).
        Waits briefly (120ms) to allow suggestion or saved-search clicks to complete, then
        immediately runs the automatic search if tags were added or deleted.
        """
        if not self.is_open:
            return
        self._schedule_auto_tag_refresh(delay_ms=120)

    def _update_tag_input_height(self):
        """
        Dynamically scales the height of the Search TAGS box (from 1 to 5 lines)
        when there are many search tags or very long tags so typed tags are never hidden.
        """
        if not self.is_open:
            return
        try:
            content = self.tag_input.get("1.0", "end-1c")
            display_lines = 1
            if content:
                try:
                    counted = self.tag_input.count("1.0", "end-1c", "displaylines")
                    if counted:
                        val = counted[0] if isinstance(counted, (tuple, list)) else int(counted)
                        display_lines = int(val) + 1
                except Exception:
                    display_lines = 1

                # Fallback character-wrap estimation when widget width is not yet mapped
                w_px = self.tag_input.winfo_width()
                chars_per_line = max(28, (w_px - 16) // 7) if w_px > 60 else 58
                est_lines = max(1, (len(content) + chars_per_line - 1) // chars_per_line)
                display_lines = max(display_lines, est_lines)

            target_lines = max(1, min(5, display_lines))
            current_height = int(self.tag_input.cget("height") or 1)
            if current_height != target_lines:
                self.tag_input.configure(height=target_lines)
                base_h = 760
                extra_h = (target_lines - 1) * 19
                cur_w = max(650, self.winfo_width())
                sh = self.winfo_screenheight()
                target_h = min(max(700, sh - 32), base_h + extra_h)
                self.geometry(f"{cur_w}x{target_h}")

                # Keep open dropdowns anchored cleanly below the resized Search TAGS box
                self.update_idletasks()
                rx = self.search_container.winfo_rootx()
                rw = self.search_container.winfo_width()
                ry = self.search_container.winfo_rooty() + self.search_container.winfo_height() + 2
                if self.suggest_dropdown.winfo_viewable():
                    sh = self.suggest_dropdown.winfo_height()
                    self.suggest_dropdown.geometry(f"{rw}x{sh}+{rx}+{ry}")
                if self.saved_dropdown.winfo_viewable():
                    svh = self.saved_dropdown.winfo_height()
                    self.saved_dropdown.geometry(f"{rw}x{svh}+{rx}+{ry}")
        except tk.TclError:
            pass

    def _configure_danbooru_color_tags(self):
        """Configures Danbooru category text tags (0=General, 1=Artist, 3=Copyright, 4=Character, 5=Meta) on both Text widgets."""
        for cat_id in (0, 1, 3, 4, 5):
            col = get_danbooru_tag_color(cat_id, CURRENT_THEME)
            tag_key = f"cat_{cat_id}"
            try:
                self.tag_input.tag_configure(tag_key, foreground=col, font=("Segoe UI", 9, "bold"))
                self.media_tags_text.tag_configure(tag_key, foreground=col, font=("Segoe UI", 9, "bold"))
            except tk.TclError:
                pass
        try:
            self.media_tags_text.tag_configure(
                "empty_hint",
                foreground=self.text_muted,
                font=("Segoe UI", 8, "italic"),
            )
        except tk.TclError:
            pass

    def _get_tag_input_value(self):
        try:
            raw = self.tag_input.get("1.0", "end-1c")
            return raw.replace("\r", " ").replace("\n", " ")
        except tk.TclError:
            return ""

    def _set_tag_input_value(self, text):
        clean = str(text or "").replace("\r", " ").replace("\n", " ").strip()
        try:
            self.tag_input.delete("1.0", tk.END)
            self.tag_input.insert("1.0", clean)
            self._recolor_search_input_tags()
            self._update_tag_input_height()
        except tk.TclError:
            pass

    def _recolor_search_input_tags(self):
        """Colors every tag token in the TAGS search input according to its Danbooru category."""
        if not self.is_open:
            return
        try:
            content = self.tag_input.get("1.0", "end-1c")
        except tk.TclError:
            return

        for cat_id in (0, 1, 3, 4, 5):
            self.tag_input.tag_remove(f"cat_{cat_id}", "1.0", tk.END)

        unknown_tokens = []
        for match in re.finditer(r"\S+", content):
            start_idx = match.start()
            end_idx = match.end()
            token = match.group(0)
            core = token.lstrip("-~").lower()
            if not core:
                continue

            if ":" in core:
                cat = 5
            else:
                cached_cat = lookup_cached_tag_category(core)
                if cached_cat is None:
                    cat = 0
                    unknown_tokens.append(core)
                else:
                    cat = cached_cat

            self.tag_input.tag_add(
                f"cat_{cat}",
                f"1.0 + {start_idx} chars",
                f"1.0 + {end_idx} chars",
            )

        if unknown_tokens:
            try:
                TAG_LOOKUP_QUEUE.put_nowait(unknown_tokens)
            except Exception:
                pass

    def _update_pause_btn_appearance(self):
        sid = self._get_current_selected_screen_id()
        with DATA_LOCK:
            st = get_screen_runtime_state(sid)
            is_paused = bool(st.get("wallpaper_paused", False))
        pal = THEME_PALETTES[CURRENT_THEME]
        if is_paused:
            self.pause_btn_frame.configure(bg="#0067c0", highlightbackground=self.border_col)
            self.pause_btn.configure(
                text="PAUSED",
                bg="#0067c0",
                fg="#ffffff",
                activebackground="#005da6",
                activeforeground="#ffffff",
            )
        else:
            self.pause_btn_frame.configure(bg=pal["btn_bg"], highlightbackground=self.border_col)
            self.pause_btn.configure(
                text="PAUSE",
                bg=pal["btn_bg"],
                fg=self.text_dark,
                activebackground=pal["btn_active"],
                activeforeground=self.text_dark,
            )

    def toggle_selected_screen_pause(self):
        sid = self._get_current_selected_screen_id()
        with DATA_LOCK:
            st = get_screen_runtime_state(sid)
            st["wallpaper_paused"] = not bool(st.get("wallpaper_paused", False))
            now_paused = st["wallpaper_paused"]
            fs_paused = bool(st.get("fullscreen_paused", False))
        self._update_pause_btn_appearance()
        push_pause_states_to_webviews(sid)
        if now_paused:
            log_event(
                "ui",
                f"Wallpaper paused on {sid} (stopped background preloader, tag pool workers, video decode & animations to conserve resources).",
            )
        else:
            log_event("ui", f"Wallpaper resumed on {sid}.")
            if not fs_paused and self.screen_enabled_var.get():
                ensure_screen_tag_pool_populated_async(sid, force_reset=False)

    def _restore_nav_buttons_after_cooldown(self):
        self._nav_cooldown_job = None
        self._nav_cooldown_active = False
        if not self.is_open:
            return
        try:
            pal = THEME_PALETTES[CURRENT_THEME]
            self.prev_btn.configure(fg=self.text_dark, bg=pal["btn_bg"], cursor="hand2")
            self.next_btn.configure(fg=self.text_dark, bg=pal["btn_bg"], cursor="hand2")
        except tk.TclError:
            pass

    def previous_media_for_selected_screen(self):
        """Requeues the last shown file on the currently selected screen with a 1.0s stress-protection cooldown."""
        if self._nav_cooldown_active:
            return
        sid = self._get_current_selected_screen_id()
        if not trigger_navigation_on_screen(sid, "prev"):
            return
        self._nav_cooldown_active = True
        pal = THEME_PALETTES[CURRENT_THEME]
        self.prev_btn.configure(fg="#0067c0", bg=pal["flash_bg"], cursor="arrow")
        self.next_btn.configure(fg=self.text_muted, cursor="arrow")
        if self._nav_cooldown_job is not None:
            try:
                self.after_cancel(self._nav_cooldown_job)
            except Exception:
                pass
        self._nav_cooldown_job = self.after(1000, self._restore_nav_buttons_after_cooldown)

    def next_media_for_selected_screen(self):
        """Immediately plays the next queued file on the currently selected screen with a 1.0s stress-protection cooldown."""
        if self._nav_cooldown_active:
            return
        sid = self._get_current_selected_screen_id()
        if not trigger_navigation_on_screen(sid, "next"):
            return
        self._nav_cooldown_active = True
        pal = THEME_PALETTES[CURRENT_THEME]
        self.next_btn.configure(fg="#0067c0", bg=pal["flash_bg"], cursor="arrow")
        self.prev_btn.configure(fg=self.text_muted, cursor="arrow")
        if self._nav_cooldown_job is not None:
            try:
                self.after_cancel(self._nav_cooldown_job)
            except Exception:
                pass
        self._nav_cooldown_job = self.after(1000, self._restore_nav_buttons_after_cooldown)

    def _cancel_auto_tag_refresh_timer(self):
        if self._auto_tag_refresh_job is not None:
            try:
                self.after_cancel(self._auto_tag_refresh_job)
            except Exception:
                pass
            self._auto_tag_refresh_job = None

    def _schedule_auto_tag_refresh(self, delay_ms=120):
        """
        Schedules an automatic search check ONLY when the Search TAGS box is no longer being typed in
        (i.e. when the vertical pipe cursor is no longer blinking inside self.tag_input).
        """
        self._cancel_auto_tag_refresh_timer()
        if not self.is_open:
            return
        self._auto_tag_refresh_job = self.after(delay_ms, self._execute_auto_tag_refresh)

    def _execute_auto_tag_refresh(self):
        self._auto_tag_refresh_job = None
        if not self.is_open:
            return
        # Do not perform automatic search while the user's cursor is still blinking in the search box
        if self._is_tag_input_focused():
            return
        sid = self._get_current_selected_screen_id()
        current_query = normalize_tag_query(self._get_tag_input_value())
        last_applied = self._last_applied_tags_by_screen.get(sid, "")
        if canonical_pool_key(current_query) != canonical_pool_key(last_applied):
            self.apply_selected_screen_tags(force_refresh=False, is_auto=True)

    def apply_selected_screen_tags(self, force_refresh=False, is_auto=False):
        """Saves the TAGS input for the selected screen and populates/reuses its shared tag pool if the screen is enabled."""
        self._cancel_auto_tag_refresh_timer()
        if self._debounce_timer:
            try:
                self.after_cancel(self._debounce_timer)
            except Exception:
                pass
            self._debounce_timer = None
        self._suggest_req_id += 1
        self._hide_all_popups()

        raw_input_val = self._get_tag_input_value()
        query = normalize_tag_query(raw_input_val)
        if not raw_input_val.strip() and not is_auto:
            self._set_tag_input_value(query)
        else:
            self._recolor_search_input_tags()
            self._update_tag_input_height()

        sid = self._get_current_selected_screen_id()
        self._last_applied_tags_by_screen[sid] = query
        self.save_display_settings(clamp_entries=False)

        pal = THEME_PALETTES[CURRENT_THEME]
        try:
            if force_refresh or is_auto:
                self.refresh_btn.configure(fg="#0067c0")
            self.tag_input.configure(bg=pal["flash_bg"])
            if self._tag_flash_job is not None:
                try:
                    self.after_cancel(self._tag_flash_job)
                except Exception:
                    pass
            self._tag_flash_job = self.after(
                180,
                lambda: (
                    setattr(self, "_tag_flash_job", None),
                    self.refresh_btn.configure(fg=self.text_dark),
                    self.tag_input.configure(bg=self.input_bg),
                )
                if self.is_open
                else None,
            )
        except tk.TclError:
            pass

        if self.screen_enabled_var.get():
            ensure_screen_tag_pool_populated_async(sid, force_reset=force_refresh)
            if is_auto:
                action_lbl = "Auto-searched tags on focus-out (cursor stopped blinking)"
            elif force_refresh:
                action_lbl = "Immediate refresh"
            else:
                action_lbl = "Applied search tags"
            log_event("search", f"{action_lbl} on {sid}: '{query}'")
        else:
            log_event("search", f"Saved search tags for disabled {sid} (no media fetch while unchecked): '{query}'")

    def immediate_refresh_selected_screen(self, event=None):
        self.apply_selected_screen_tags(force_refresh=True)
        return "break"

    def _on_tag_input_enter(self, event=None):
        if self.suggest_dropdown.winfo_viewable() and self.selected_index >= 0:
            self._select_suggestion(self.selected_index)
            return "break"
        self.apply_selected_screen_tags(force_refresh=False)
        return "break"

    def _on_tag_input_shift_enter(self, event=None):
        self.apply_selected_screen_tags(force_refresh=True)
        return "break"

    def _on_tag_input_tab(self, event=None):
        if self.suggest_dropdown.winfo_viewable() and self.selected_index >= 0:
            self._select_suggestion(self.selected_index)
            return "break"
        return None

    def _get_current_tag_fragment(self):
        try:
            text_before = self.tag_input.get("1.0", tk.INSERT).replace("\r", " ").replace("\n", " ")
            parts = text_before.split(" ")
            return parts[-1] if parts else ""
        except tk.TclError:
            return ""

    def _on_tag_input_clipboard_modified(self):
        if not self.is_open:
            return
        self._recolor_search_input_tags()
        self._update_tag_input_height()
        if not self._is_tag_input_focused():
            self._schedule_auto_tag_refresh(120)

    def _on_tag_input_key_release(self, event):
        if event.keysym in (
            "Up", "Down", "Return", "Shift_L", "Shift_R",
            "Control_L", "Control_R", "Alt_L", "Alt_R",
            "Escape", "Left", "Right", "Tab",
        ):
            return

        self._recolor_search_input_tags()
        self._update_tag_input_height()

        if self._debounce_timer:
            try:
                self.after_cancel(self._debounce_timer)
            except Exception:
                pass
            self._debounce_timer = None

        fragment = self._get_current_tag_fragment().strip()
        if len(fragment) < 2:
            self.hide_dropdown()
            return

        self._suggest_req_id += 1
        current_req = self._suggest_req_id
        self._debounce_timer = self.after(350, lambda: self._request_suggestions(fragment, current_req))

    def _request_suggestions(self, fragment, req_id):
        while not SUGGESTION_QUEUE.empty():
            try:
                SUGGESTION_QUEUE.get_nowait()
            except Empty:
                break
        SUGGESTION_QUEUE.put((fragment, req_id))

    def display_suggestions(self, results, req_id):
        """Displays auto-suggestions directly BELOW the TAGS search box with Danbooru category colors."""
        if not self.is_open or req_id != self._suggest_req_id:
            return

        self.suggest_items = results
        self.selected_index = -1

        if not results:
            self.hide_dropdown()
            return

        self.saved_dropdown.withdraw()
        self.update_idletasks()
        rx = self.search_container.winfo_rootx()
        rw = self.search_container.winfo_width()
        ry = self.search_container.winfo_rooty() + self.search_container.winfo_height() + 2

        for i in range(5):
            if i < len(results):
                item = results[i]
                tag_name = item[0]
                count = item[1]
                cat = item[2] if len(item) > 2 else lookup_cached_tag_category(tag_name) or 0
                count_str = f"({count:,})" if count else ""
                tag_col = get_danbooru_tag_color(cat, CURRENT_THEME)
                self.suggest_labels[i].configure(
                    text=f"{tag_name}  {count_str}",
                    bg=self.input_bg,
                    fg=tag_col,
                )
                self.suggest_labels[i].pack(fill="x", padx=1, pady=1)
            else:
                self.suggest_labels[i].pack_forget()

        calc_height = len(results) * 28 + 4
        self.suggest_dropdown.geometry(f"{rw}x{calc_height}+{rx}+{ry}")
        self.suggest_dropdown.deiconify()
        self.suggest_dropdown.lift()

    def hide_dropdown(self):
        try:
            self.suggest_dropdown.withdraw()
        except tk.TclError:
            pass
        self.selected_index = -1

    def _stop_saved_dropdown_marquee(self):
        if self._saved_marquee_job is not None:
            try:
                self.after_cancel(self._saved_marquee_job)
            except Exception:
                pass
            self._saved_marquee_job = None
        self._saved_marquee_items = []

    def _hide_saved_dropdown(self):
        self._stop_saved_dropdown_marquee()
        try:
            self.saved_dropdown.withdraw()
        except tk.TclError:
            pass

    def _hide_toast_popup(self):
        if self._toast_hide_job is not None:
            try:
                self.after_cancel(self._toast_hide_job)
            except Exception:
                pass
            self._toast_hide_job = None
        try:
            self.toast_popup.withdraw()
        except tk.TclError:
            pass

    def _show_saved_search_toast(self, message="Saved Search Tags already exists", duration_ms=2000):
        """Displays a brief floating popup toast for 2 seconds when Save Search Tags is pressed for an existing query."""
        if not self.is_open:
            return
        if self._toast_hide_job is not None:
            try:
                self.after_cancel(self._toast_hide_job)
            except Exception:
                pass
            self._toast_hide_job = None

        try:
            self.toast_popup.configure(bg="#ffffff" if CURRENT_THEME == "dark" else "#005da6")
            self.toast_label.configure(
                text=f"⚠  {message}",
                fg="#ffffff",
                bg="#2b2b36" if CURRENT_THEME == "dark" else "#0067c0",
            )
            self.update_idletasks()
            btn_rx = self.saved_searches_btn_frame.winfo_rootx()
            btn_ry = self.saved_searches_btn_frame.winfo_rooty()
            btn_rw = self.saved_searches_btn_frame.winfo_width()
            req_w = max(240, self.toast_label.winfo_reqwidth() + 8)
            req_h = max(30, self.toast_label.winfo_reqheight() + 4)
            tx = btn_rx + max(0, (btn_rw - req_w) // 2)
            ty = max(10, btn_ry - req_h - 4)
            self.toast_popup.geometry(f"{req_w}x{req_h}+{tx}+{ty}")
            self.toast_popup.deiconify()
            self.toast_popup.lift()
            self._toast_hide_job = self.after(duration_ms, self._hide_toast_popup)
        except tk.TclError:
            pass

    def _hide_all_popups(self):
        self.hide_dropdown()
        self._hide_saved_dropdown()
        self._hide_toast_popup()

    def _highlight_suggestion_index(self, index):
        self.selected_index = index
        pal = THEME_PALETTES[CURRENT_THEME]
        for i, lbl in enumerate(self.suggest_labels):
            if i < len(self.suggest_items):
                item = self.suggest_items[i]
                cat = item[2] if len(item) > 2 else lookup_cached_tag_category(item[0]) or 0
                tag_col = get_danbooru_tag_color(cat, CURRENT_THEME)
                if i == index:
                    lbl.configure(bg=pal["hover_bg"], fg=tag_col)
                else:
                    lbl.configure(bg=self.input_bg, fg=tag_col)

    def _focus_suggestion_down(self, event):
        if not self.suggest_items or not self.suggest_dropdown.winfo_viewable():
            return "break"
        new_idx = self.selected_index + 1
        if new_idx >= len(self.suggest_items):
            new_idx = 0
        self._highlight_suggestion_index(new_idx)
        return "break"

    def _focus_suggestion_up(self, event):
        if not self.suggest_items or not self.suggest_dropdown.winfo_viewable():
            return "break"
        new_idx = self.selected_index - 1
        if new_idx < 0:
            new_idx = len(self.suggest_items) - 1
        self._highlight_suggestion_index(new_idx)
        return "break"

    def _select_suggestion(self, index):
        if index < 0 or index >= len(self.suggest_items):
            return
        chosen_tag = self.suggest_items[index][0]

        try:
            before_cursor = self.tag_input.get("1.0", tk.INSERT).replace("\r", " ").replace("\n", " ")
            after_cursor = self.tag_input.get(tk.INSERT, "end-1c").replace("\r", " ").replace("\n", " ")
        except tk.TclError:
            return

        words = before_cursor.split(" ")
        last_word = words[-1] if words else ""
        prefix = ""
        if last_word.startswith("-") or last_word.startswith("~"):
            prefix = last_word[0]
        words[-1] = prefix + chosen_tag
        new_before = " ".join(words) + " "
        combined = new_before + after_cursor.lstrip(" ")

        self.tag_input.delete("1.0", tk.END)
        self.tag_input.insert("1.0", combined)
        self.tag_input.mark_set(tk.INSERT, f"1.0 + {len(new_before)} chars")
        self.tag_input.focus_set()
        self._recolor_search_input_tags()
        self._update_tag_input_height()
        self.hide_dropdown()

    def toggle_saved_dropdown(self):
        if self.saved_dropdown.winfo_viewable():
            self._hide_saved_dropdown()
            return
        self.hide_dropdown()
        self.render_saved_dropdown()

    def _render_tokens_on_saved_canvas(self, canvas_widget, query_text, start_x):
        """Draws each space-separated tag token onto canvas_widget with its Danbooru category color and returns the ending x coordinate."""
        cur_x = start_x
        tokens = [t for t in str(query_text or "").split(" ") if t]
        for tok in tokens:
            core = tok.lstrip("-~").lower()
            if ":" in core:
                cat = 5
            else:
                cat = lookup_cached_tag_category(core, default=0)
            col = get_danbooru_tag_color(cat if cat in (0, 1, 3, 4, 5) else 0, CURRENT_THEME)
            item_id = canvas_widget.create_text(
                cur_x,
                13,
                text=tok,
                anchor="w",
                fill=col,
                font=("Segoe UI", 9, "bold"),
                tags=("marquee_tok",),
            )
            bbox = canvas_widget.bbox(item_id)
            tok_w = (bbox[2] - bbox[0]) if bbox else (len(tok) * 7)
            cur_x += tok_w + 8
        return max(cur_x - 8, start_x)

    def _tick_saved_dropdown_marquee(self):
        """Continuously loop-scrolls long saved search rows horizontally while the Saved Searches dropdown is open."""
        self._saved_marquee_job = None
        if not self.is_open or not self.saved_dropdown.winfo_viewable():
            return

        step_px = 1.4
        active_items = []
        for entry in self._saved_marquee_items:
            cv = entry["canvas"]
            cycle_px = entry["cycle_px"]
            try:
                if not cv.winfo_exists():
                    continue
                cv.move("marquee_tok", -step_px, 0)
                entry["offset"] += step_px
                if entry["offset"] >= cycle_px:
                    cv.move("marquee_tok", cycle_px, 0)
                    entry["offset"] -= cycle_px
                active_items.append(entry)
            except tk.TclError:
                continue

        self._saved_marquee_items = active_items
        if self._saved_marquee_items:
            self._saved_marquee_job = self.after(35, self._tick_saved_dropdown_marquee)

    def render_saved_dropdown(self):
        self._stop_saved_dropdown_marquee()
        for widget in self.saved_dropdown.winfo_children():
            widget.destroy()

        self.update_idletasks()
        rx = self.search_container.winfo_rootx()
        rw = max(320, self.search_container.winfo_width())
        ry = self.search_container.winfo_rooty() + self.search_container.winfo_height() + 2

        pal = THEME_PALETTES[CURRENT_THEME]
        accent_fg = "#4da3ff" if CURRENT_THEME == "dark" else "#0067c0"

        # 1d) First option at top of Saved Searches dropdown: "Save Search Tags"
        save_btn = tk.Label(
            self.saved_dropdown,
            text="Save Search Tags",
            anchor="w",
            fg=accent_fg,
            bg=self.input_bg,
            font=("Segoe UI", 9, "bold"),
            padx=10,
            pady=6,
            cursor="hand2",
        )
        save_btn.pack(fill="x", padx=1, pady=(1, 2))
        save_btn.bind("<Enter>", lambda e: save_btn.configure(bg=pal["hover_bg"]))
        save_btn.bind("<Leave>", lambda e: save_btn.configure(bg=self.input_bg))
        save_btn.bind("<Button-1>", lambda e: self.save_current_search())

        if not self.saved_list:
            empty_lbl = tk.Label(
                self.saved_dropdown,
                text="(No saved searches)",
                anchor="w",
                fg=self.text_muted,
                bg=self.bg_base,
                font=("Segoe UI", 8, "italic"),
                padx=10,
                pady=5,
            )
            empty_lbl.pack(fill="x", padx=1, pady=1)
        else:
            avail_text_w = max(180, rw - 52)
            for item in self.saved_list:
                row = tk.Frame(self.saved_dropdown, bg=self.input_bg, height=28)
                row.pack(fill="x", padx=1, pady=1)
                row.pack_propagate(False)

                # 1c) Small trash-can delete button on the right of each saved search row (packed FIRST so never clipped)
                del_btn = tk.Label(
                    row,
                    text="🗑",
                    fg="#ff5f5f" if CURRENT_THEME == "dark" else "#d83b01",
                    bg=self.input_bg,
                    font=("Segoe UI", 10, "bold"),
                    padx=8,
                    cursor="hand2",
                )
                del_btn.pack(side="right", fill="y")

                text_canvas = tk.Canvas(
                    row,
                    bg=self.input_bg,
                    height=26,
                    bd=0,
                    highlightthickness=0,
                    cursor="hand2",
                )
                text_canvas.pack(side="left", fill="both", expand=True, padx=(8, 2))

                end_x = self._render_tokens_on_saved_canvas(text_canvas, item, 2)
                text_w = end_x - 2

                # If the saved search tags are too long to fit on the line, continuously loop-scroll
                if text_w > avail_text_w:
                    gap_px = 56
                    cycle_px = text_w + gap_px
                    sep_col = self.text_muted
                    text_canvas.create_text(
                        2 + text_w + (gap_px // 2),
                        13,
                        text="•",
                        anchor="center",
                        fill=sep_col,
                        font=("Segoe UI", 9, "bold"),
                        tags=("marquee_tok",),
                    )
                    self._render_tokens_on_saved_canvas(text_canvas, item, 2 + cycle_px)
                    self._saved_marquee_items.append(
                        {
                            "canvas": text_canvas,
                            "cycle_px": float(cycle_px),
                            "offset": 0.0,
                        }
                    )

                text_canvas.bind(
                    "<Enter>",
                    lambda e, r=row, d=del_btn, cv=text_canvas: (
                        r.configure(bg=pal["row_hover"]),
                        cv.configure(bg=pal["row_hover"]),
                        d.configure(bg=pal["row_hover"]),
                    ),
                )
                text_canvas.bind(
                    "<Leave>",
                    lambda e, r=row, d=del_btn, cv=text_canvas: (
                        r.configure(bg=self.input_bg),
                        cv.configure(bg=self.input_bg),
                        d.configure(bg=self.input_bg),
                    ),
                )
                text_canvas.bind("<Button-1>", lambda e, text=item: self.apply_saved_search(text))

                del_btn.bind(
                    "<Enter>",
                    lambda e, d=del_btn: d.configure(
                        bg="#c42b1c",
                        fg="#ffffff",
                    ),
                )
                del_btn.bind(
                    "<Leave>",
                    lambda e, d=del_btn: d.configure(
                        bg=self.input_bg,
                        fg="#ff5f5f" if CURRENT_THEME == "dark" else "#d83b01",
                    ),
                )
                del_btn.bind("<Button-1>", lambda e, text=item: self.delete_saved_search(text))

        item_count = max(1, len(self.saved_list))
        calc_height = 36 + (item_count * 30) + 4

        self.saved_dropdown.geometry(f"{rw}x{calc_height}+{rx}+{ry}")
        self.saved_dropdown.deiconify()
        self.saved_dropdown.lift()

        if self._saved_marquee_items:
            self._saved_marquee_job = self.after(35, self._tick_saved_dropdown_marquee)

    def save_current_search(self):
        query = normalize_tag_query(self._get_tag_input_value())
        if not query:
            return
        already_exists = any(
            canonical_pool_key(existing) == canonical_pool_key(query)
            or existing.strip().lower() == query.strip().lower()
            for existing in self.saved_list
        )
        if already_exists:
            self._show_saved_search_toast("Saved Search Tags already exists", duration_ms=2000)
            log_event("search", f"Save Search Tags skipped (already exists): '{query}'")
            return

        self.saved_list.insert(0, query)
        store_saved_searches(self.saved_list)
        log_event("search", f"Saved search to bookmarks via Save Search Tags: '{query}'")
        self.render_saved_dropdown()

    def apply_saved_search(self, saved_tags):
        self._set_tag_input_value(saved_tags)
        self._hide_saved_dropdown()
        self.apply_selected_screen_tags(force_refresh=False)

    def delete_saved_search(self, target_tags):
        if target_tags in self.saved_list:
            self.saved_list.remove(target_tags)
            store_saved_searches(self.saved_list)
            log_event("search", f"Removed query from bookmarks: '{target_tags}'")
        self.render_saved_dropdown()

    def _append_tag_to_search_input(self, tag_name):
        """
        Appends a clicked tag from the permanent 4-layer Displayed Media Tags box into the selected screen's TAGS search bar.
        If the Search TAGS box is not currently being typed in (cursor not blinking inside it), triggers auto-search immediately;
        otherwise waits until the cursor stops blinking in the Search TAGS box.
        """
        clean_tag = str(tag_name or "").strip()
        if not clean_tag:
            return
        current = normalize_tag_query(self._get_tag_input_value())
        existing_tokens = [t.lstrip("-~").lower() for t in current.split() if t.strip()]
        if clean_tag.lower() not in existing_tokens:
            updated = f"{current} {clean_tag}".strip() if current else clean_tag
            self._set_tag_input_value(updated)
            if not self._is_tag_input_focused():
                self.apply_selected_screen_tags(force_refresh=False, is_auto=True)
            else:
                log_event(
                    "search",
                    f"Added media tag '{clean_tag}' to {self._get_current_selected_screen_id()} search bar (waiting for focus-out to auto-search).",
                )

    def _on_post_link_clicked(self, event=None):
        """Opens the currently displayed Danbooru post in the user's default web browser when 'Post #' is clicked."""
        post_id = getattr(self, "_current_displayed_post_id", None)
        try:
            pid = int(post_id or 0)
        except (ValueError, TypeError):
            pid = 0
        if pid <= 0:
            return
        post_url = f"https://danbooru.donmai.us/posts/{pid}"
        log_event("ui", f"Opening Post #{pid} in default web browser: {post_url}")
        threading.Thread(
            target=lambda u=post_url: webbrowser.open(u, new=2),
            daemon=True,
        ).start()

    def _on_post_link_hover_enter(self, event=None):
        if getattr(self, "_current_displayed_post_id", None):
            hover_fg = "#80c2ff" if CURRENT_THEME == "dark" else "#004580"
            try:
                self.media_tags_post_lbl.configure(fg=hover_fg)
            except tk.TclError:
                pass

    def _on_post_link_hover_leave(self, event=None):
        base_fg = "#4da3ff" if CURRENT_THEME == "dark" else "#0067c0"
        try:
            self.media_tags_post_lbl.configure(fg=base_fg)
        except tk.TclError:
            pass

    def on_screen_media_displayed(self, screen_id, post_id, tags_list=None):
        """Called immediately when a screen WebView reports a newly displayed media item."""
        if not self.is_open:
            return
        if screen_id == self._get_current_selected_screen_id():
            self._render_displayed_media_tags_box(force=True)

    def _render_displayed_media_tags_box(self, force=False):
        """Renders all tags of the selected screen's most recently displayed media in the permanent 4-layer scrollable box."""
        if not self.is_open:
            return
        sid = self._get_current_selected_screen_id()
        with DATA_LOCK:
            st = get_screen_runtime_state(sid)
            post_id = st.get("last_displayed_post_id")
            tags_list = list(st.get("last_displayed_tags") or [])
            if not tags_list and post_id and post_id in POST_TAGS_CACHE:
                tags_list = list(POST_TAGS_CACHE[post_id])

        resolved_tags = []
        for t_name, t_cat in tags_list:
            cat = t_cat if t_cat in (0, 1, 3, 4, 5) else 0
            if cat == 0:
                cached = lookup_cached_tag_category(t_name, default=0)
                if cached in (1, 3, 4, 5):
                    cat = cached
            resolved_tags.append((t_name, cat))

        tags_sig = (len(resolved_tags), tuple(resolved_tags[:25]))
        if (
            not force
            and sid == self._last_rendered_screen_id
            and post_id == self._last_rendered_post_id
            and tags_sig == self._last_rendered_tags_sig
        ):
            return

        self._last_rendered_screen_id = sid
        self._last_rendered_post_id = post_id
        self._last_rendered_tags_sig = tags_sig

        try:
            self.media_tags_text.configure(state="normal")
            self.media_tags_text.delete("1.0", tk.END)

            post_link_fg = "#4da3ff" if CURRENT_THEME == "dark" else "#0067c0"
            if post_id and int(post_id) > 0:
                self._current_displayed_post_id = int(post_id)
                self.media_tags_post_lbl.configure(
                    text=f"Post #{int(post_id)} ({len(resolved_tags)} tags)",
                    fg=post_link_fg,
                    cursor="hand2",
                )
            else:
                self._current_displayed_post_id = None
                self.media_tags_post_lbl.configure(
                    text="",
                    fg=post_link_fg,
                    cursor="arrow",
                )

            if not resolved_tags:
                msg = (
                    "Screen display is currently unchecked — enable screen to fetch and display media tags."
                    if not self.screen_enabled_var.get()
                    else "Waiting for media to display on this screen..."
                )
                self.media_tags_text.insert(tk.END, msg, ("empty_hint",))
            else:
                for idx, (t_name, t_cat) in enumerate(resolved_tags):
                    click_tag = f"media_tag_click_{idx}"
                    cat_tag = f"cat_{t_cat if t_cat in (0, 1, 3, 4, 5) else 0}"
                    self.media_tags_text.insert(tk.END, t_name, (cat_tag, click_tag))
                    self.media_tags_text.tag_bind(
                        click_tag,
                        "<Button-1>",
                        lambda e, tn=t_name: self._append_tag_to_search_input(tn),
                    )
                    self.media_tags_text.tag_bind(
                        click_tag,
                        "<Enter>",
                        lambda e: self.media_tags_text.configure(cursor="hand2"),
                    )
                    self.media_tags_text.tag_bind(
                        click_tag,
                        "<Leave>",
                        lambda e: self.media_tags_text.configure(cursor="arrow"),
                    )
                    if idx < len(resolved_tags) - 1:
                        self.media_tags_text.insert(tk.END, "   ")

            self.media_tags_text.configure(state="disabled")
        except tk.TclError:
            pass

    def _poll_display_status(self):
        if not self.is_open or not IS_RUNNING:
            return

        sid = self._get_current_selected_screen_id()
        sc_enabled = bool(self.screen_enabled_var.get())
        applied_raw = self._last_applied_tags_by_screen.get(sid)
        if applied_raw is None:
            applied_raw = get_screen_tags(sid)
        query = normalize_tag_query(applied_raw)
        pkey = canonical_pool_key(query)

        with DATA_LOCK:
            st = get_screen_runtime_state(sid)
            scr_paused = bool(st.get("wallpaper_paused", False))
            fs_paused = bool(st.get("fullscreen_paused", False))
            pool = TAG_POOLS.get(pkey)
            p_status = dict(pool.get("last_status") or {}) if pool else {}
            buf_len = len(pool.get("posts") or []) if pool else 0
            is_fetching = bool(pool.get("is_fetching", False)) if pool else False

        try:
            pal = THEME_PALETTES[CURRENT_THEME]
            if APP_PAUSED:
                bg_c = "#3d1a1e" if CURRENT_THEME == "dark" else "#fde7e9"
                fg_c = "#ff8080" if CURRENT_THEME == "dark" else "#a80000"
                txt = "⏸ App Paused"
            elif not sc_enabled:
                bg_c = pal["btn_bg"]
                fg_c = self.text_muted
                txt = "○ Screen Disabled"
            elif scr_paused:
                bg_c = pal["btn_bg"]
                fg_c = "#4da3ff" if CURRENT_THEME == "dark" else "#0067c0"
                txt = "⏸ Screen Paused"
            elif fs_paused:
                bg_c = pal["btn_bg"]
                fg_c = "#4da3ff" if CURRENT_THEME == "dark" else "#0067c0"
                txt = "⏸ Fullscreen App"
            elif is_fetching and buf_len == 0:
                bg_c = pal["btn_bg"]
                fg_c = "#4da3ff" if CURRENT_THEME == "dark" else "#0067c0"
                txt = "⟳ Fetching tags..."
            elif p_status.get("status") == "ok" or buf_len > 0:
                page = p_status.get("page", 1)
                bg_c = "#18331a" if CURRENT_THEME == "dark" else "#dff6dd"
                fg_c = "#6ccb5f" if CURRENT_THEME == "dark" else "#0f7b0f"
                txt = f"✔ P:{page} ({buf_len} pooled)"
            elif p_status.get("status") == "error":
                bg_c = "#3d1a1e" if CURRENT_THEME == "dark" else "#fde7e9"
                fg_c = "#ff8080" if CURRENT_THEME == "dark" else "#a80000"
                txt = "✖ API Error"
            else:
                bg_c = pal["btn_bg"]
                fg_c = self.text_muted
                txt = "● Ready"

            self.status_frame.configure(bg=bg_c)
            self.status_label.configure(text=txt, fg=fg_c, bg=bg_c)

            self._render_displayed_media_tags_box(force=False)
        except tk.TclError:
            return

        self._status_poll_job = self.after(400, self._poll_display_status)

    def _update_mode_sections_visibility(self):
        """Hides all display mode settings sections except the currently selected display mode."""
        self.scroll_section_frame.pack_forget()
        self.polaroid_section_frame.pack_forget()
        self.slideshow_section_frame.pack_forget()
        self.masonry_section_frame.pack_forget()

        active_mode = _normalize_display_mode_value(self.mode_var.get())
        if active_mode == "scroll":
            self.scroll_section_frame.pack(fill="both", expand=True)
        elif active_mode == "polaroid":
            self.polaroid_section_frame.pack(fill="both", expand=True)
        elif active_mode == "slideshow":
            self.slideshow_section_frame.pack(fill="both", expand=True)
        elif active_mode == "masonry":
            self.masonry_section_frame.pack(fill="both", expand=True)

    def _get_active_numeric_spec(self, pkey):
        return self.NUMERIC_SPECS[pkey]

    def _format_numeric_value(self, pkey, val):
        spec = self._get_active_numeric_spec(pkey)
        if not spec["is_float"]:
            return str(int(round(float(val))))
        rounded = round(float(val), spec["precision"])
        if pkey in ("scrollspeed", "slideshowfade") and rounded.is_integer():
            return str(int(rounded))
        text = f"{rounded:.{spec['precision']}f}".rstrip("0").rstrip(".")
        if pkey == "dropspeed" and "." not in text:
            text += ".0"
        return text

    def _clamp_numeric_value(self, pkey, raw_val):
        spec = self._get_active_numeric_spec(pkey)
        clamped = max(float(spec["min"]), min(float(spec["max"]), float(raw_val)))
        if spec["is_float"]:
            res = round(clamped, spec["precision"])
            if pkey in ("scrollspeed", "slideshowfade") and res.is_integer():
                return int(res)
            return res
        return int(round(clamped))

    def _create_numeric_row(self, parent_frame, pkey, spec):
        prow = tk.Frame(parent_frame, bg=self.bg_base)
        prow.pack(fill="x", pady=3)
        self._themed_frames.append(prow)

        lbl = tk.Label(
            prow, text=spec["label"], width=26, anchor="w",
            font=("Segoe UI", 9), fg=self.text_dark, bg=self.bg_base
        )
        lbl.pack(side="left")
        self._themed_labels_dark.append(lbl)

        ctrl_container = tk.Frame(prow, bg=self.bg_base)
        ctrl_container.pack(side="right", fill="x", expand=True)
        ctrl_container.columnconfigure(0, weight=1, uniform="dual_ctrl")
        ctrl_container.columnconfigure(1, weight=3, uniform="dual_ctrl")
        self._themed_frames.append(ctrl_container)

        pbox = tk.Frame(
            ctrl_container, bg=self.input_bg,
            highlightthickness=1, highlightbackground=self.border_col
        )
        pbox.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self._themed_borders.append(pbox)

        pentry = tk.Entry(
            pbox, bg=self.input_bg, fg=self.text_dark, insertbackground=self.text_dark,
            bd=0, width=6, font=("Segoe UI", 9), relief="flat"
        )
        pentry.pack(fill="x", padx=6, pady=2)
        pentry.insert(0, self._format_numeric_value(pkey, spec["default"]))
        self._themed_entries.append((pbox, pentry))

        slider_var = tk.DoubleVar(self, value=float(spec["default"]))
        slider = ttk.Scale(
            ctrl_container,
            from_=float(spec["min"]),
            to=float(spec["max"]),
            orient="horizontal",
            variable=slider_var,
            style="Display.Horizontal.TScale",
            command=lambda val, k=pkey: self._on_slider_moved(k, val),
        )
        slider.grid(row=0, column=1, sticky="ew")

        pentry.bind("<KeyRelease>", lambda e, k=pkey: self._on_entry_key_release(k, e))
        pentry.bind("<FocusOut>", lambda e, k=pkey: self._on_entry_commit(k, e))
        pentry.bind("<Return>", lambda e, k=pkey: self._on_entry_commit(k, e))

        self.prop_entries[pkey] = pentry
        self.prop_sliders[pkey] = slider
        self.prop_vars[pkey] = slider_var

    def _enforce_size_bounds(self, changed_key):
        if changed_key not in ("minsize", "maxsize"):
            return
        try:
            min_v = int(round(float(self.prop_vars["minsize"].get())))
            max_v = int(round(float(self.prop_vars["maxsize"].get())))
        except (ValueError, KeyError):
            return

        if changed_key == "minsize" and min_v > max_v:
            new_max = self._clamp_numeric_value("maxsize", min_v)
            self.prop_vars["maxsize"].set(float(new_max))
            self.prop_entries["maxsize"].delete(0, tk.END)
            self.prop_entries["maxsize"].insert(0, str(new_max))
        elif changed_key == "maxsize" and max_v < min_v:
            new_min = self._clamp_numeric_value("minsize", max_v)
            self.prop_vars["minsize"].set(float(new_min))
            self.prop_entries["minsize"].delete(0, tk.END)
            self.prop_entries["minsize"].insert(0, str(new_min))

    def _on_slider_moved(self, pkey, raw_val):
        if self._syncing_controls:
            return
        try:
            clamped = self._clamp_numeric_value(pkey, float(raw_val))
        except ValueError:
            return

        self._syncing_controls = True
        try:
            self.prop_vars[pkey].set(float(clamped))
            entry = self.prop_entries[pkey]
            entry.delete(0, tk.END)
            entry.insert(0, self._format_numeric_value(pkey, clamped))
            self._enforce_size_bounds(pkey)
        finally:
            self._syncing_controls = False

        self._schedule_live_apply()

    def _on_entry_key_release(self, pkey, event):
        if self._syncing_controls:
            return
        if event and event.keysym in (
            "Left", "Right", "Up", "Down", "Home", "End",
            "Tab", "Shift_L", "Shift_R", "Control_L", "Control_R", "Return"
        ):
            return

        raw_text = self.prop_entries[pkey].get().strip()
        if not raw_text or raw_text in ("-", ".", "-."):
            return
        try:
            typed_val = float(raw_text)
        except ValueError:
            return

        spec = self._get_active_numeric_spec(pkey)
        slider_pos = max(float(spec["min"]), min(float(spec["max"]), typed_val))

        self._syncing_controls = True
        try:
            self.prop_vars[pkey].set(slider_pos)
        finally:
            self._syncing_controls = False

        if float(spec["min"]) <= typed_val <= float(spec["max"]):
            self._schedule_live_apply()

    def _on_entry_commit(self, pkey, event=None):
        if self._syncing_controls:
            return
        spec = self._get_active_numeric_spec(pkey)
        raw_text = self.prop_entries[pkey].get().strip()
        try:
            parsed = float(raw_text)
        except ValueError:
            parsed = float(self.prop_vars[pkey].get() if pkey in self.prop_vars else spec["default"])

        clamped = self._clamp_numeric_value(pkey, parsed)

        self._syncing_controls = True
        try:
            self.prop_vars[pkey].set(float(clamped))
            entry = self.prop_entries[pkey]
            entry.delete(0, tk.END)
            entry.insert(0, self._format_numeric_value(pkey, clamped))
            self._enforce_size_bounds(pkey)
        finally:
            self._syncing_controls = False

        self.save_display_settings()

    def _schedule_live_apply(self):
        if self._live_apply_job is not None:
            try:
                self.after_cancel(self._live_apply_job)
            except Exception:
                pass
        self._live_apply_job = self.after(40, self._execute_live_apply)

    def _execute_live_apply(self):
        self._live_apply_job = None
        if self.is_open:
            self.save_display_settings(clamp_entries=False)

    def _get_current_selected_screen_id(self):
        lbl = self.selected_screen_label.get()
        return self.screen_map.get(lbl, "screen_1")

    def refresh_screen_selector_from_topology(self):
        """
        Live-updates the Select Screen combobox when an HDMI TV or display is connected
        or disconnected while the Settings window is open.
        """
        global _RUNTIME_LAST_SELECTED_SCREEN_ID
        if not self.is_open or not hasattr(self, "screen_combo"):
            return
        prev_sid = self._get_current_selected_screen_id()
        screens_snap = get_connected_screens_snapshot()
        self.screen_map = {s["label"]: s["id"] for s in screens_snap}
        id_to_label = {s["id"]: s["label"] for s in screens_snap}
        screen_labels = [s["label"] for s in screens_snap]
        if not screen_labels:
            return
        self.screen_combo.configure(values=screen_labels)
        if prev_sid in id_to_label:
            self.selected_screen_label.set(id_to_label[prev_sid])
            _RUNTIME_LAST_SELECTED_SCREEN_ID = prev_sid
        else:
            new_label = screen_labels[0]
            new_sid = self.screen_map.get(new_label, "screen_1")
            self.selected_screen_label.set(new_label)
            _RUNTIME_LAST_SELECTED_SCREEN_ID = new_sid
            self._load_screen_values_into_form(new_sid)

    def _on_resync_displays_clicked(self):
        self._defocus_tag_input_on_outside_click()
        threading.Thread(
            target=resync_all_displays_and_desktop,
            kwargs={"reason": "Manual Resync Displays button in Settings"},
            daemon=True,
        ).start()

    def _on_screen_selection_changed(self, event=None):
        global _RUNTIME_LAST_SELECTED_SCREEN_ID
        self._cancel_auto_tag_refresh_timer()
        self._hide_all_popups()
        sid = self._get_current_selected_screen_id()
        _RUNTIME_LAST_SELECTED_SCREEN_ID = sid
        self._load_screen_values_into_form(sid)

    def _update_masonry_edge_fill_btn_label(self):
        cur_fill = _normalize_masonry_edge_fill_value(self.masonry_edge_fill_var.get())
        if cur_fill == "black":
            self.masonry_edge_fill_btn.configure(text="Edge Fill: Black")
        else:
            self.masonry_edge_fill_btn.configure(text="Edge Fill: Blur")

    def _on_toggle_masonry_edge_fill(self):
        cur_fill = _normalize_masonry_edge_fill_value(self.masonry_edge_fill_var.get())
        new_fill = "black" if cur_fill == "blur" else "blur"
        self.masonry_edge_fill_var.set(new_fill)
        self._update_masonry_edge_fill_btn_label()
        readable = "Black (Solid Gap-Matched Space)" if new_fill == "black" else "Blur (Ambient Tile Edge Blur)"
        log_event("ui", f"Switched Edge Fill setting to: {readable}")
        self._schedule_live_apply()

    def _update_masonry_layout_btn_label(self):
        cur = _normalize_masonry_layout_value(self.masonry_layout_var.get())
        if cur == "rows":
            self.masonry_layout_btn.configure(text="Masonry Layout: Rows")
        else:
            self.masonry_layout_btn.configure(text="Masonry Layout: Mondrian")
        self._update_masonry_edge_fill_btn_label()

    def _draw_pill_switch_canvas(self, canvas_widget, is_on: bool):
        if not canvas_widget:
            return
        try:
            canvas_widget.configure(bg=self.bg_base)
            canvas_widget.delete("all")
            if is_on:
                track_fill = "#0067c0"
                track_outline = "#005da6"
                thumb_fill = "#ffffff"
            else:
                track_fill = "#34343e" if CURRENT_THEME == "dark" else "#c6c6ce"
                track_outline = self.border_col
                thumb_fill = "#dcdce4" if CURRENT_THEME == "dark" else "#ffffff"

            # Pill track (x1=2, y1=2, x2=40, y2=20, radius=9)
            canvas_widget.create_oval(2, 2, 20, 20, fill=track_fill, outline=track_outline, width=1)
            canvas_widget.create_oval(22, 2, 40, 20, fill=track_fill, outline=track_outline, width=1)
            canvas_widget.create_rectangle(11, 2, 31, 20, fill=track_fill, outline="")
            canvas_widget.create_line(11, 2, 31, 2, fill=track_outline, width=1)
            canvas_widget.create_line(11, 20, 31, 20, fill=track_outline, width=1)

            # Sliding circular thumb (radius=7)
            thumb_cx = 31 if is_on else 11
            thumb_cy = 11
            canvas_widget.create_oval(
                thumb_cx - 7,
                thumb_cy - 7,
                thumb_cx + 7,
                thumb_cy + 7,
                fill=thumb_fill,
                outline="",
            )
        except Exception:
            pass

    def _draw_screen_enable_switch(self):
        if hasattr(self, "screen_enable_switch"):
            self._draw_pill_switch_canvas(self.screen_enable_switch, bool(self.screen_enabled_var.get()))

    def _draw_fullscreen_pause_switch(self):
        if hasattr(self, "fullscreen_pause_switch"):
            self._draw_pill_switch_canvas(self.fullscreen_pause_switch, bool(self.pause_fullscreen_var.get()))

    def _on_toggle_screen_enable_switch(self, event=None):
        self._defocus_tag_input_on_outside_click(event)
        new_val = not bool(self.screen_enabled_var.get())
        self.screen_enabled_var.set(new_val)
        self._draw_screen_enable_switch()
        sid = self._get_current_selected_screen_id()
        log_event("ui", f"Toggled 'Display wallpaper on this screen' slide switch on {sid} to: {'ON' if new_val else 'OFF'}")
        self._schedule_live_apply()

    def _on_toggle_fullscreen_pause_switch(self, event=None):
        self._defocus_tag_input_on_outside_click(event)
        new_val = not bool(self.pause_fullscreen_var.get())
        self.pause_fullscreen_var.set(new_val)
        self._draw_fullscreen_pause_switch()
        sid = self._get_current_selected_screen_id()
        log_event("ui", f"Toggled 'Pause during full screen application' slide switch on {sid} to: {'ON' if new_val else 'OFF'}")
        self._schedule_live_apply()

    def _update_vsync_ui_state(self):
        if not hasattr(self, "vsync_btn") or not hasattr(self, "target_fps_subframe"):
            return
        is_vsync_on = bool(self.vsync_var.get())
        pal = THEME_PALETTES[CURRENT_THEME]
        if is_vsync_on:
            self.vsync_btn.configure(
                text="V-Sync On",
                bg="#0067c0",
                fg="#ffffff",
                activebackground="#005da6",
                activeforeground="#ffffff",
            )
            self.target_fps_subframe.pack_forget()
        else:
            self.vsync_btn.configure(
                text="V-Sync Off",
                bg=pal["btn_bg"],
                fg=self.text_dark,
                activebackground=pal["btn_active"],
                activeforeground=self.text_dark,
            )
            self.target_fps_subframe.pack(side="left", padx=(4, 0))

    def _on_toggle_vsync(self):
        self._defocus_tag_input_on_outside_click()
        new_vsync = not bool(self.vsync_var.get())
        self.vsync_var.set(new_vsync)
        self._update_vsync_ui_state()
        sid = self._get_current_selected_screen_id()
        fps_val = int(round(float(self.prop_vars.get("targetfps", tk.DoubleVar(value=60.0)).get())))
        log_event(
            "ui",
            f"Switched V-Sync on {sid} to: {'V-Sync On (Native Refresh)' if new_vsync else f'V-Sync Off (Target FPS: {fps_val})'}",
        )
        self._schedule_live_apply()

    def _on_toggle_masonry_layout(self):
        cur = _normalize_masonry_layout_value(self.masonry_layout_var.get())
        new_layout = "rows" if cur == "mondrian" else "mondrian"
        self.masonry_layout_var.set(new_layout)
        self._update_masonry_layout_btn_label()
        readable = "Rows" if new_layout == "rows" else "Mondrian"
        log_event("ui", f"Switched Masonry layout setting to: {readable}")
        self._schedule_live_apply()

    def _load_screen_values_into_form(self, screen_id):
        sc_cfg = get_screen_config(screen_id)
        enabled_val = bool(sc_cfg.get("enabled", screen_id == "screen_1"))
        _LAST_SCREEN_ENABLED_STATE[screen_id] = enabled_val
        self.screen_enabled_var.set(enabled_val)
        self._draw_screen_enable_switch()
        props = sc_cfg["properties"]

        pause_fs_val = _normalize_vsync_value(props.get("pausefullscreen", {}).get("value", True))
        self.pause_fullscreen_var.set(pause_fs_val)
        self._draw_fullscreen_pause_switch()

        vsync_val = _normalize_vsync_value(props.get("vsync", {}).get("value", True))
        self.vsync_var.set(vsync_val)
        self._update_vsync_ui_state()

        tags_val = normalize_tag_query(props.get("searchtags", {}).get("value", DEFAULT_TAGS))
        self._last_applied_tags_by_screen[screen_id] = tags_val
        self._set_tag_input_value(tags_val)

        mode_val = _normalize_display_mode_value(props.get("displaymode", {}).get("value", "scroll"))
        self.mode_var.set(mode_val)

        dir_val = props.get("scrolldirection", {}).get("value", "left")
        if dir_val not in ("left", "right", "up", "down"):
            dir_val = "left"
        self.dir_var.set(dir_val)

        mef_val = _normalize_masonry_edge_fill_value(props.get("masonryedgefill", {}).get("value", "blur"))
        self.masonry_edge_fill_var.set(mef_val)
        self._update_masonry_edge_fill_btn_label()

        ml_val = _normalize_masonry_layout_value(props.get("masonrylayout", {}).get("value", "mondrian"))
        self.masonry_layout_var.set(ml_val)
        self._update_masonry_layout_btn_label()

        self._syncing_controls = True
        try:
            for key, spec in self.NUMERIC_SPECS.items():
                raw_val = props.get(key, {}).get("value", spec["default"])
                try:
                    clamped = self._clamp_numeric_value(key, raw_val)
                except (ValueError, TypeError):
                    clamped = spec["default"]

                entry = self.prop_entries.get(key)
                if entry:
                    entry.delete(0, tk.END)
                    entry.insert(0, self._format_numeric_value(key, clamped))
                slider_w = self.prop_sliders.get(key)
                if slider_w is not None:
                    slider_w.configure(command="")
                if key in self.prop_vars:
                    self.prop_vars[key].set(float(clamped))
                if slider_w is not None:
                    slider_w.configure(command=lambda val, k=key: self._on_slider_moved(k, val))
        finally:
            self._syncing_controls = False

        self._update_pause_btn_appearance()
        self._render_displayed_media_tags_box(force=True)
        self._update_mode_sections_visibility()
        self._update_fill_btn_state()

    def _update_fill_btn_state(self):
        is_polaroid = (_normalize_display_mode_value(self.mode_var.get()) == "polaroid")
        if is_polaroid and self._fill_cooldown_remaining <= 0:
            self.fill_screen_btn.configure(state="normal", bg="#0067c0", cursor="hand2")
        else:
            self.fill_screen_btn.configure(state="disabled", bg="#555560" if CURRENT_THEME == "dark" else "#c8c8d0", cursor="arrow")

    def _on_fill_screen_clicked(self):
        if _normalize_display_mode_value(self.mode_var.get()) != "polaroid" or self._fill_cooldown_remaining > 0:
            return
        self.save_display_settings()
        sid = self._get_current_selected_screen_id()
        trigger_fill_screen_on_webview(sid)

        self._fill_cooldown_remaining = 30
        self._update_fill_btn_state()
        self._tick_fill_cooldown()

    def _tick_fill_cooldown(self):
        if not self.is_open:
            return
        if self._fill_cooldown_remaining > 0:
            self.fill_timer_lbl.configure(text=f"{self._fill_cooldown_remaining}s")
            self._fill_cooldown_remaining -= 1
            self._fill_timer_job = self.after(1000, self._tick_fill_cooldown)
        else:
            self.fill_timer_lbl.configure(text="")
            self._update_fill_btn_state()

    def save_display_settings(self, clamp_entries=True):
        sid = self._get_current_selected_screen_id()
        project_data = load_project_json()

        base_props = project_data.setdefault("general", {}).setdefault(
            "properties", get_default_properties_dict()
        )
        screens_dict = project_data.setdefault("screens", {})
        screen_entry = screens_dict.setdefault(sid, {
            "enabled": True,
            "properties": json.loads(json.dumps(base_props)),
        })

        prev_enabled = _LAST_SCREEN_ENABLED_STATE.get(sid, screen_entry.get("enabled", True))
        new_enabled = bool(self.screen_enabled_var.get())
        _LAST_SCREEN_ENABLED_STATE[sid] = new_enabled
        enabled_changed = (prev_enabled != new_enabled)

        screen_entry["enabled"] = new_enabled
        s_props = screen_entry.setdefault("properties", json.loads(json.dumps(base_props)))

        prev_tags = normalize_tag_query(s_props.get("searchtags", {}).get("value", DEFAULT_TAGS))
        new_tags = normalize_tag_query(self._get_tag_input_value())
        tags_changed = (canonical_pool_key(prev_tags) != canonical_pool_key(new_tags))
        s_props.setdefault("searchtags", {})["value"] = new_tags

        active_vsync = bool(self.vsync_var.get())
        active_pause_fs = bool(self.pause_fullscreen_var.get())
        active_ml = _normalize_masonry_layout_value(self.masonry_layout_var.get())
        active_mef = _normalize_masonry_edge_fill_value(self.masonry_edge_fill_var.get())
        s_props.setdefault("vsync", {})["value"] = active_vsync
        s_props.setdefault("pausefullscreen", {})["value"] = active_pause_fs
        s_props.setdefault("displaymode", {})["value"] = self.mode_var.get()
        s_props.setdefault("scrolldirection", {})["value"] = self.dir_var.get()
        s_props.setdefault("masonrylayout", {})["value"] = active_ml
        s_props.setdefault("masonryedgefill", {})["value"] = active_mef

        self._syncing_controls = True
        try:
            for key, spec in self.NUMERIC_SPECS.items():
                raw_str = self.prop_entries[key].get().strip()
                try:
                    parsed = float(raw_str)
                except ValueError:
                    parsed = float(self.prop_vars[key].get())

                clamped = self._clamp_numeric_value(key, parsed)
                s_props.setdefault(key, {})["value"] = clamped
                self.prop_vars[key].set(float(clamped))

                if clamp_entries:
                    self.prop_entries[key].delete(0, tk.END)
                    self.prop_entries[key].insert(0, self._format_numeric_value(key, clamped))

            min_val = s_props.get("minsize", {}).get("value", 220)
            max_val = s_props.get("maxsize", {}).get("value", 440)
            if isinstance(min_val, (int, float)) and isinstance(max_val, (int, float)) and min_val > max_val:
                reconciled_min = self._clamp_numeric_value("minsize", max_val)
                reconciled_max = self._clamp_numeric_value("maxsize", min_val)
                if reconciled_min > reconciled_max:
                    reconciled_min = reconciled_max
                s_props["minsize"]["value"] = reconciled_min
                s_props["maxsize"]["value"] = reconciled_max
                self.prop_vars["minsize"].set(float(reconciled_min))
                self.prop_vars["maxsize"].set(float(reconciled_max))
                if clamp_entries:
                    self.prop_entries["minsize"].delete(0, tk.END)
                    self.prop_entries["minsize"].insert(0, self._format_numeric_value("minsize", reconciled_min))
                    self.prop_entries["maxsize"].delete(0, tk.END)
                    self.prop_entries["maxsize"].insert(0, self._format_numeric_value("maxsize", reconciled_max))
        finally:
            self._syncing_controls = False

        if sid == "screen_1":
            for k, val_obj in s_props.items():
                if k in base_props and isinstance(val_obj, dict) and "value" in val_obj:
                    base_props[k]["value"] = val_obj["value"]

        fs_Pause_cleared = False
        with DATA_LOCK:
            st = get_screen_runtime_state(sid)
            st["queued_tags"] = None
            get_or_create_tag_pool_locked(new_tags)
            if tags_changed:
                st["epoch"] += 1
                st["seen_post_ids"].clear()
            if (not active_pause_fs or not new_enabled) and st.get("fullscreen_paused", False):
                st["fullscreen_paused"] = False
                fs_Pause_cleared = True

        self._last_applied_tags_by_screen[sid] = new_tags
        store_project_json(project_data)
        push_properties_to_webview(sid, sync_geometry=enabled_changed)
        if fs_Pause_cleared:
            push_pause_states_to_webviews(sid)
        if new_enabled and (enabled_changed or tags_changed or fs_Pause_cleared):
            ensure_screen_tag_pool_populated_async(sid, force_reset=False)
        self._render_displayed_media_tags_box(force=True)
        self._update_fill_btn_state()

    # -------------------------------------------------------------------------
    # TAB 3: LOGS (PAUSE APPLICATION + GLOSSARY BUTTON + CLEAR LOGS)
    # -------------------------------------------------------------------------
    def _build_logs_tab(self):
        pad_frame = tk.Frame(self.tab_logs, bg=self.bg_base)
        pad_frame.pack(fill="both", expand=True, padx=12, pady=10)
        self._themed_frames.append(pad_frame)

        top_bar = tk.Frame(pad_frame, bg=self.bg_base)
        top_bar.pack(fill="x", pady=(0, 8))
        self._themed_frames.append(top_bar)

        self.pause_app_btn = tk.Button(
            top_bar,
            text="PAUSE APPLICATION",
            bg="#d13438" if APP_PAUSED else "#107c10",
            fg="#ffffff",
            activebackground="#b02a2e" if APP_PAUSED else "#0e6b0e",
            activeforeground="#ffffff",
            font=("Segoe UI", 9, "bold"),
            bd=0, relief="flat", padx=16, pady=5, cursor="hand2",
            command=self.toggle_application_pause
        )
        self.pause_app_btn.pack(side="left")

        self.clear_btn = tk.Button(
            top_bar, text="Clear Logs", fg="#0067c0", bg="#e8e8ed",
            activebackground="#dcdce0", font=("Segoe UI", 8, "bold"),
            bd=0, relief="flat", padx=10, pady=4, cursor="hand2",
            command=self.clear_logs
        )
        self.clear_btn.pack(side="right")

        self.glossary_btn = tk.Button(
            top_bar, text="Glossary", fg=self.text_dark, bg="#e8e8ed",
            activebackground="#dcdce0", font=("Segoe UI", 8, "bold"),
            bd=0, relief="flat", padx=12, pady=4, cursor="hand2",
            command=self.open_glossary_dialog
        )
        self.glossary_btn.pack(side="right", padx=(0, 8))
        self._themed_neutral_btns.append(self.glossary_btn)

        self.log_box_frame = tk.Frame(pad_frame, bg=self.input_bg, highlightthickness=1, highlightbackground=self.border_col)
        self.log_box_frame.pack(fill="both", expand=True)
        self._themed_borders.append(self.log_box_frame)

        self.log_text = tk.Text(
            self.log_box_frame, bg=self.input_bg, fg=self.text_dark, wrap="word",
            font=("Consolas", 8), bd=0, relief="flat", state="disabled"
        )
        scrollbar = ttk.Scrollbar(self.log_box_frame, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="right", fill="y")
        self.log_text.pack(side="left", fill="both", expand=True, padx=4, pady=4)

        if LOG_HISTORY:
            self.log_text.configure(state="normal")
            self.log_text.insert(tk.END, "\n".join(LOG_HISTORY) + "\n")
            self.log_text.see(tk.END)
            self.log_text.configure(state="disabled")

    def open_resource_graph_dialog(self):
        global RESOURCE_GRAPH_DIALOG_INSTANCE
        if RESOURCE_GRAPH_DIALOG_INSTANCE and getattr(RESOURCE_GRAPH_DIALOG_INSTANCE, "is_open", False):
            try:
                RESOURCE_GRAPH_DIALOG_INSTANCE.lift()
                return
            except tk.TclError:
                pass
        RESOURCE_GRAPH_DIALOG_INSTANCE = ResourceGraphDialog(self.master)
        log_event("perf", "Opened Task Manager Resource Graph pop-out window.")

    def open_glossary_dialog(self):
        global GLOSSARY_DIALOG_INSTANCE
        if GLOSSARY_DIALOG_INSTANCE and getattr(GLOSSARY_DIALOG_INSTANCE, "is_open", False):
            try:
                GLOSSARY_DIALOG_INSTANCE.lift()
                return
            except tk.TclError:
                pass
        GLOSSARY_DIALOG_INSTANCE = GlossaryDialog(self)

    def apply_theme(self):
        pal = THEME_PALETTES[CURRENT_THEME]
        self.bg_base = pal["bg_base"]
        self.input_bg = pal["input_bg"]
        self.border_col = pal["border_col"]
        self.text_dark = pal["text_dark"]
        self.text_muted = pal["text_muted"]

        self.configure(bg=self.border_col)
        try:
            self.style.configure("Display.Horizontal.TScale", background=self.bg_base)
        except Exception:
            pass

        self._update_settings_tabs_theme()

        for frm in self._themed_frames:
            try:
                frm.configure(bg=self.bg_base)
            except Exception:
                pass

        for brd in self._themed_borders:
            try:
                brd.configure(highlightbackground=self.border_col)
            except Exception:
                pass

        self.container.configure(bg=self.bg_base, highlightbackground=self.border_col)
        self.tab_content_holder.configure(bg=self.bg_base, highlightbackground=self.border_col)
        self.cred_sep.configure(bg=self.border_col)
        self.disp_sep.configure(bg=self.border_col)

        for lbl in self._themed_labels_dark:
            try:
                lbl.configure(bg=self.bg_base, fg=self.text_dark)
            except Exception:
                pass

        for lbl in self._themed_labels_muted:
            try:
                lbl.configure(bg=self.bg_base, fg=self.text_muted)
            except Exception:
                pass

        for box, ent in self._themed_entries:
            try:
                box.configure(bg=self.input_bg, highlightbackground=self.border_col)
                ent.configure(bg=self.input_bg, fg=self.text_dark, insertbackground=self.text_dark)
            except Exception:
                pass

        for btn in self._themed_neutral_btns:
            try:
                btn.configure(
                    bg=pal["btn_bg"],
                    fg=self.text_dark,
                    activebackground=pal["btn_active"],
                    activeforeground=self.text_dark,
                )
            except Exception:
                pass

        self.theme_btn.configure(text="Dark Mode" if CURRENT_THEME == "light" else "Light Mode")
        self._draw_screen_enable_switch()
        self._draw_fullscreen_pause_switch()
        self._update_vsync_ui_state()

        # Update Display tab search & playback controls theme (all standardized height=28)
        self.status_frame.configure(highlightbackground=self.border_col)
        self.saved_searches_btn_frame.configure(bg=pal["btn_bg"], highlightbackground=self.border_col)
        self.saved_searches_btn.configure(
            bg=pal["btn_bg"],
            fg=self.text_dark,
            activebackground=pal["btn_active"],
            activeforeground=self.text_dark,
        )
        self.refresh_btn_frame.configure(bg=pal["btn_bg"], highlightbackground=self.border_col)
        self.refresh_btn.configure(bg=pal["btn_bg"], fg=self.text_dark, activebackground=pal["btn_active"])
        self.prev_btn_frame.configure(bg=pal["btn_bg"], highlightbackground=self.border_col)
        self.prev_btn.configure(bg=pal["btn_bg"], fg=self.text_dark, activebackground=pal["btn_active"])
        self.next_btn_frame.configure(bg=pal["btn_bg"], highlightbackground=self.border_col)
        self.next_btn.configure(bg=pal["btn_bg"], fg=self.text_dark, activebackground=pal["btn_active"])
        self.pause_btn_frame.configure(highlightbackground=self.border_col)
        self._update_pause_btn_appearance()

        self.search_container.configure(bg=self.input_bg, highlightbackground=self.border_col)
        self.tag_input.configure(bg=self.input_bg, fg=self.text_dark, insertbackground=self.text_dark)
        self.suggest_dropdown.configure(bg=self.border_col)
        self.saved_dropdown.configure(bg=self.border_col)
        if self.saved_dropdown.winfo_viewable():
            self.render_saved_dropdown()

        self.media_tags_box_frame.configure(bg=self.input_bg, highlightbackground=self.border_col)
        self.media_tags_text.configure(bg=self.input_bg, fg=self.text_dark)
        self.media_tags_post_lbl.configure(
            bg=self.bg_base,
            fg="#4da3ff" if CURRENT_THEME == "dark" else "#0067c0",
        )
        self._configure_danbooru_color_tags()
        self._recolor_search_input_tags()
        self._render_displayed_media_tags_box(force=True)

        self.clear_btn.configure(
            bg=pal["btn_bg"],
            fg="#4da3ff" if CURRENT_THEME == "dark" else "#0067c0",
            activebackground=pal["btn_active"],
        )
        self.log_box_frame.configure(bg=self.input_bg, highlightbackground=self.border_col)
        self.log_text.configure(bg=self.input_bg, fg=self.text_dark)
        self._update_fill_btn_state()

    def toggle_application_pause(self):
        global APP_PAUSED
        APP_PAUSED = not APP_PAUSED
        if APP_PAUSED:
            self.pause_app_btn.configure(bg="#d13438", activebackground="#b02a2e")
            log_event("app", "Application PAUSED (display frozen, proxy streams & API calls stopped).")
        else:
            self.pause_app_btn.configure(bg="#107c10", activebackground="#0e6b0e")
            log_event("app", "Application RESUMED.")
            ensure_all_enabled_screen_pools_populated(force_reset=False)

        push_pause_states_to_webviews()

    def append_log(self, message):
        try:
            _, bottom_fraction = self.log_text.yview()
            was_at_bottom = (bottom_fraction >= 0.99)

            self.log_text.configure(state="normal")
            self.log_text.insert(tk.END, message + "\n")
            line_count = int(self.log_text.index("end-1c").split(".")[0])
            if line_count > 500:
                self.log_text.delete("1.0", f"{line_count - 500 + 1}.0")

            if was_at_bottom:
                self.log_text.see(tk.END)
            self.log_text.configure(state="disabled")
        except tk.TclError:
            pass

    def clear_logs(self):
        LOG_HISTORY.clear()
        try:
            self.log_text.configure(state="normal")
            self.log_text.delete("1.0", tk.END)
            self.log_text.configure(state="disabled")
        except tk.TclError:
            pass

    def _on_escape_pressed(self, event=None):
        if self.saved_dropdown.winfo_viewable():
            self._hide_saved_dropdown()
            return "break"
        if self.suggest_dropdown.winfo_viewable():
            self.hide_dropdown()
            return "break"
        self.close_dialog()
        return "break"

    def _on_dialog_focus_out(self, event=None):
        if event and event.widget == self:
            self.after(150, self._check_focus_and_hide_popups)

    def _check_focus_and_hide_popups(self):
        if not self.is_open:
            return
        try:
            focus_widget = self.focus_get()
            if focus_widget is None:
                self._hide_all_popups()
        except tk.TclError:
            pass

    def start_move(self, event):
        self._drag_x = event.x
        self._drag_y = event.y

    def do_move(self, event):
        x = self.winfo_x() + (event.x - self._drag_x)
        y = self.winfo_y() + (event.y - self._drag_y)
        self.geometry(f"+{x}+{y}")
        self._hide_all_popups()

    def close_dialog(self):
        global _RUNTIME_LAST_SETTINGS_TAB, _RUNTIME_LAST_SELECTED_SCREEN_ID
        self.is_open = False
        try:
            _RUNTIME_LAST_SETTINGS_TAB = self.active_settings_tab
            _RUNTIME_LAST_SELECTED_SCREEN_ID = self._get_current_selected_screen_id()
        except Exception:
            pass
        try:
            cfg = load_app_config()
            cfg["settings_pos_x"] = self.winfo_x()
            cfg["settings_pos_y"] = self.winfo_y()
            store_app_config(cfg)
        except Exception:
            pass
        self._cancel_auto_tag_refresh_timer()
        self._stop_saved_dropdown_marquee()
        self._hide_toast_popup()
        if getattr(self, "_live_apply_job", None):
            try:
                self.after_cancel(self._live_apply_job)
            except Exception:
                pass
        if getattr(self, "_status_poll_job", None):
            try:
                self.after_cancel(self._status_poll_job)
            except Exception:
                pass
        if getattr(self, "_debounce_timer", None):
            try:
                self.after_cancel(self._debounce_timer)
            except Exception:
                pass
        if self._fill_timer_job:
            try:
                self.after_cancel(self._fill_timer_job)
            except Exception:
                pass
        if getattr(self, "_nav_cooldown_job", None):
            try:
                self.after_cancel(self._nav_cooldown_job)
            except Exception:
                pass
            self._nav_cooldown_job = None
        if getattr(self, "_tag_flash_job", None):
            try:
                self.after_cancel(self._tag_flash_job)
            except Exception:
                pass
            self._tag_flash_job = None
        self._hide_all_popups()
        try:
            self.suggest_dropdown.destroy()
            self.saved_dropdown.destroy()
            self.toast_popup.destroy()
        except Exception:
            pass
        if GLOSSARY_DIALOG_INSTANCE and getattr(GLOSSARY_DIALOG_INSTANCE, "is_open", False):
            try:
                GLOSSARY_DIALOG_INSTANCE.close_glossary()
            except Exception:
                pass
        self.destroy()


# =============================================================================
# 7. SYSTEM TRAY, TKINTER THREAD & EPHEMERAL MULTI-SCREEN PYWEBVIEW LIFECYCLE
# =============================================================================
def save_credentials_from_settings(user, uid, key):
    cfg = load_app_config()
    old_creds = (cfg.get("USERNAME", ""), cfg.get("USER_ID", ""), cfg.get("API_KEY", ""))
    new_creds = (user, uid, key)

    cfg["USERNAME"] = user
    cfg["USER_ID"] = uid
    cfg["API_KEY"] = key
    store_app_config(cfg)
    apply_credentials(user, uid, key)
    log_event("auth", f"Credentials updated from Settings for user '{user or 'anonymous'}'.")

    if old_creds != new_creds:
        ensure_all_enabled_screen_pools_populated(force_reset=True)


def _bring_tk_window_to_win32_foreground(tk_win) -> None:
    """
    Elevates a Tkinter Toplevel window above Windows Explorer when triggered by the
    system tray or a duplicate .exe launch handoff.
    """
    if not tk_win:
        return
    try:
        tk_win.deiconify()
        tk_win.attributes("-topmost", True)
        tk_win.lift()
        tk_win.focus_force()
        tk_win.update_idletasks()
        if os.name == "nt":
            hwnd = tk_win.winfo_id()
            if hwnd:
                if user32.IsIconic(hwnd):
                    user32.ShowWindow(hwnd, 9)  # SW_RESTORE
                user32.SetForegroundWindow(hwnd)
    except Exception:
        pass


def open_settings_dialog_window():
    global SETTINGS_DIALOG_INSTANCE
    if not TK_ROOT:
        return
    if SETTINGS_DIALOG_INSTANCE and getattr(SETTINGS_DIALOG_INSTANCE, "is_open", False):
        try:
            _bring_tk_window_to_win32_foreground(SETTINGS_DIALOG_INSTANCE)
            return
        except tk.TclError:
            pass

    cfg = load_app_config()
    initial = {
        "USERNAME": cfg.get("USERNAME", USERNAME),
        "USER_ID": cfg.get("USER_ID", USER_ID),
        "API_KEY": cfg.get("API_KEY", API_KEY),
    }
    SETTINGS_DIALOG_INSTANCE = SettingsDialog(
        TK_ROOT, save_credentials_from_settings, initial_values=initial
    )
    _bring_tk_window_to_win32_foreground(SETTINGS_DIALOG_INSTANCE)


def single_instance_signal_worker_loop():
    """
    Daemon thread that listens on the kernel Named Event (_SINGLE_INSTANCE_EVENT_HANDLE)
    signaled whenever the user launches a duplicate DanbooruWallpaper.exe instance.
    Immediately opens and focuses the Settings window on the primary instance.
    """
    if _KERNEL32_SINGLE_INST is None or not _SINGLE_INSTANCE_EVENT_HANDLE:
        return

    while IS_RUNNING:
        try:
            wait_res = _KERNEL32_SINGLE_INST.WaitForSingleObject(
                _SINGLE_INSTANCE_EVENT_HANDLE, 400
            )
            if not IS_RUNNING:
                break
            if wait_res == WAIT_OBJECT_0:
                # If the user rapidly double-clicked at cold startup, wait briefly for TK_ROOT to initialize
                wait_deadline = time.time() + 5.0
                while TK_ROOT is None and IS_RUNNING and time.time() < wait_deadline:
                    time.sleep(0.05)
                log_event(
                    "app",
                    "Duplicate launch detected — bringing Settings window to foreground.",
                )
                if TK_ROOT is not None:
                    try:
                        TK_ROOT.after(0, open_settings_dialog_window)
                    except Exception:
                        pass
        except Exception:
            time.sleep(0.4)


def on_tray_settings(icon=None, item=None):
    """Instantly opens the Application Settings window on left-click (default action) or right-click menu."""
    if TK_ROOT:
        TK_ROOT.after(0, open_settings_dialog_window)


def on_tray_resync_displays(icon=None, item=None):
    """Triggers a non-destructive multi-monitor topology & desktop Z-order recovery from the system tray."""
    threading.Thread(
        target=resync_all_displays_and_desktop,
        kwargs={"reason": "Manual Resync Displays from System Tray"},
        daemon=True,
    ).start()


def shutdown_app(icon=None, item=None):
    global IS_RUNNING, _SINGLE_INSTANCE_MUTEX_HANDLE, _SINGLE_INSTANCE_EVENT_HANDLE
    if not IS_RUNNING:
        return
    IS_RUNNING = False
    log_event("app", "Shutting down application...")

    if TRAY_ICON:
        try:
            TRAY_ICON.stop()
        except Exception:
            pass
    if TK_ROOT:
        try:
            TK_ROOT.after(0, TK_ROOT.destroy)
        except Exception:
            pass
    if HTTP_SERVER:
        try:
            HTTP_SERVER.server_close()
        except Exception:
            pass
    with SESSION_LOCK:
        if HTTP2_SESSION is not None:
            try:
                HTTP2_SESSION.close()
            except Exception:
                pass
    for win in list(WEBVIEW_WINDOWS.values()):
        try:
            win.destroy()
        except Exception:
            pass

    cleanup_legacy_webview_profile()

    if _KERNEL32_SINGLE_INST is not None:
        if _SINGLE_INSTANCE_EVENT_HANDLE:
            try:
                _KERNEL32_SINGLE_INST.CloseHandle(_SINGLE_INSTANCE_EVENT_HANDLE)
            except Exception:
                pass
            _SINGLE_INSTANCE_EVENT_HANDLE = None
        if _SINGLE_INSTANCE_MUTEX_HANDLE:
            try:
                _KERNEL32_SINGLE_INST.ReleaseMutex(_SINGLE_INSTANCE_MUTEX_HANDLE)
                _KERNEL32_SINGLE_INST.CloseHandle(_SINGLE_INSTANCE_MUTEX_HANDLE)
            except Exception:
                pass
            _SINGLE_INSTANCE_MUTEX_HANDLE = None

    os._exit(0)


def setup_tray():
    """
    Configures the system tray icon:
    - Left-click (default=True) immediately opens the Application Settings window.
    - Right-click opens the context menu with Settings, Resync Displays, and Exit.
    """
    global TRAY_ICON
    box_icon = create_cardboard_box_icon()
    menu = pystray.Menu(
        pystray.MenuItem("Settings", on_tray_settings, default=True),
        pystray.MenuItem("Resync Displays", on_tray_resync_displays),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Exit", shutdown_app),
    )
    TRAY_ICON = pystray.Icon("DanbooruService", box_icon, "Danbooru Wallpaper Service", menu)
    TRAY_ICON.run()


def initialize_startup_credentials_and_pools():
    cfg = load_app_config()
    user = cfg.get("USERNAME", "")
    uid = cfg.get("USER_ID", "")
    key = cfg.get("API_KEY", "")

    apply_credentials(user, uid, key)
    transport_mode = "curl_cffi HTTP/2" if CURL_CFFI_AVAILABLE else "stdlib TLS 1.3 + DoH SNI fallback"
    log_event("auth", f"Active transport engine: {transport_mode}")

    # Always start fetching media pools for enabled screens immediately so primary display begins playing right away
    ensure_all_enabled_screen_pools_populated(force_reset=False)

    if user and key:
        log_event("auth", f"Loaded DPAPI-protected credentials for user '{user}'" + (f" (#{uid})" if uid else ""))
    else:
        log_event("auth", "No credentials configured yet; running in anonymous API mode (2-tag limit).")
        try:
            open_settings_dialog_window()
        except Exception as e:
            log_event("ui", f"Failed to open startup settings window: {e}")


def run_tkinter_ui():
    global TK_ROOT
    TK_ROOT = tk.Tk()
    TK_ROOT.withdraw()
    apply_app_icon(TK_ROOT)
    TK_ROOT.after(200, initialize_startup_credentials_and_pools)
    try:
        TK_ROOT.mainloop()
    except Exception as e:
        log_event("ui", f"Tkinter loop exited: {e}")


def inject_and_sync_screen(screen_info, window, win_title):
    sid = screen_info["id"]
    with INJECTION_LOCK:
        if sid in DESKTOP_INJECTED_SET:
            return
        DESKTOP_INJECTED_SET.add(sid)

    hwnd = attach_window_to_desktop(
        window,
        win_title,
        mon_x=screen_info["x"],
        mon_y=screen_info["y"],
        mon_w=screen_info["width"],
        mon_h=screen_info["height"],
    )
    if hwnd:
        with INJECTION_LOCK:
            DESKTOP_HWNDS[sid] = hwnd
    else:
        with INJECTION_LOCK:
            DESKTOP_INJECTED_SET.discard(sid)
        return

    push_properties_to_webview(sid, sync_geometry=True)
    push_pause_states_to_webviews(sid)


def ensure_webview_windows_for_connected_screens():
    """
    Dynamically creates and injects pywebview windows for any newly connected monitors
    (e.g., when an HDMI TV is powered on after the application has already started).
    """
    for screen_info in get_connected_screens_snapshot():
        sid = screen_info["id"]
        win = WEBVIEW_WINDOWS.get(sid)
        win_title = f"{WEBVIEW_WINDOW_TITLE_PREFIX}_{sid}"
        if win is None:
            try:
                log_event(
                    "win32",
                    f"Creating WebView2 wallpaper surface for newly connected {screen_info['label']} ({sid}).",
                )
                win = webview.create_window(
                    title=win_title,
                    url=f"http://127.0.0.1:{PORT}/?screen={sid}",
                    x=screen_info["x"],
                    y=screen_info["y"],
                    width=screen_info["width"],
                    height=screen_info["height"],
                    frameless=True,
                    easy_drag=False,
                    background_color="#0b0b0d",
                )
                WEBVIEW_WINDOWS[sid] = win
                win.events.loaded += (
                    lambda s=screen_info, w=win, t=win_title: threading.Thread(
                        target=inject_and_sync_screen, args=(s, w, t), daemon=True
                    ).start()
                )
            except Exception as e:
                log_event("win32", f"Failed to create hotplug WebView2 window for {sid}: {e}")
        elif sid not in DESKTOP_INJECTED_SET:
            threading.Thread(
                target=inject_and_sync_screen, args=(screen_info, win, win_title), daemon=True
            ).start()


def resync_all_displays_and_desktop(reason: str = "Display topology change"):
    """
    Non-destructively re-enumerates connected monitors, provisions any newly connected HDMI displays,
    hides disconnected displays, repairs parent/style/rect drift inside Progman/WorkerW, restores
    desktop icon metrics if perturbed by DPI switches, and updates the Settings dropdown live.
    """
    if not _RESYNC_LOCK.acquire(blocking=False):
        return
    try:
        screens = refresh_connected_screens_preserving_ids()
        summary = ", ".join(f"{s['id']}={s['width']}x{s['height']}@({s['x']},{s['y']})" for s in screens)
        log_event("win32", f"{reason}: Synchronizing {len(screens)} active display(s) [{summary}].")

        ensure_webview_windows_for_connected_screens()
        sync_all_screens_z_order_and_geometry(target_screen_id=None, force_reattach=True)

        for s in list(screens):
            sid = s["id"]
            win = WEBVIEW_WINDOWS.get(sid)
            if win:
                push_properties_to_webview(sid, sync_geometry=False)
                push_pause_states_to_webviews(sid)
                _async_evaluate_js(
                    win,
                    "if (window.forceViewportResync) { window.forceViewportResync(); } else { window.dispatchEvent(new Event('resize')); }",
                )

        if TK_ROOT and SETTINGS_DIALOG_INSTANCE and getattr(SETTINGS_DIALOG_INSTANCE, "is_open", False):
            try:
                TK_ROOT.after(0, SETTINGS_DIALOG_INSTANCE.refresh_screen_selector_from_topology)
            except Exception:
                pass
    except Exception as e:
        log_event("win32", f"Display topology resync warning: {e}")
    finally:
        _RESYNC_LOCK.release()


def verify_and_heal_desktop_hwnds():
    """
    Periodic lightweight self-healing check that verifies every connected enabled screen's HWND
    still resides inside the proper Progman/WorkerW parent and matches its monitor's exact pixel
    rectangle. Automatically repairs WinForms DPI auto-scaling shrinkage or Z-order drift.
    """
    progman = user32.FindWindowW("Progman", None)
    if not progman:
        return
    topo = _probe_existing_desktop_topology(progman)
    target_parent = (
        progman
        if topo["is_win11_24h2"]
        else (topo["classic_workerw"] or topo["workerw_in_progman"] or progman)
    )
    if not target_parent:
        return

    screens_by_id = {s["id"]: s for s in get_connected_screens_snapshot()}
    needs_heal_sids = []

    with INJECTION_LOCK:
        for sid, hwnd in list(DESKTOP_HWNDS.items()):
            if not hwnd or not user32.IsWindow(hwnd):
                continue
            if sid not in screens_by_id:
                style = GetWindowLongPtrW(hwnd, GWL_STYLE) & 0xFFFFFFFF
                if style & WS_VISIBLE:
                    needs_heal_sids.append(sid)
                continue

            s_info = screens_by_id[sid]
            enabled = is_screen_enabled(sid)
            style = GetWindowLongPtrW(hwnd, GWL_STYLE) & 0xFFFFFFFF
            is_vis = bool(style & WS_VISIBLE)

            if enabled != is_vis:
                needs_heal_sids.append(sid)
                continue
            if not enabled:
                continue

            if user32.GetParent(hwnd) != target_parent or not (style & WS_CHILD) or (style & WS_POPUP):
                needs_heal_sids.append(sid)
                continue

            rc = wintypes.RECT()
            if user32.GetWindowRect(hwnd, ctypes.byref(rc)):
                cur_w = rc.right - rc.left
                cur_h = rc.bottom - rc.top
                if (
                    abs(rc.left - s_info["x"]) > 2
                    or abs(rc.top - s_info["y"]) > 2
                    or abs(cur_w - s_info["width"]) > 2
                    or abs(cur_h - s_info["height"]) > 2
                ):
                    needs_heal_sids.append(sid)

    if needs_heal_sids:
        log_event(
            "win32",
            f"Watchdog detected desktop HWND geometry/parent drift on {needs_heal_sids} — auto-repairing.",
        )
        sync_all_screens_z_order_and_geometry(target_screen_id=None, force_reattach=True)
        for sid in needs_heal_sids:
            win = WEBVIEW_WINDOWS.get(sid)
            if win:
                _async_evaluate_js(
                    win,
                    "if (window.forceViewportResync) { window.forceViewportResync(); } else { window.dispatchEvent(new Event('resize')); }",
                )
    else:
        restore_desktop_icon_metrics_if_inflated(progman)


_IGNORED_FULLSCREEN_CLASS_NAMES = {
    "Progman",
    "WorkerW",
    "SHELLDLL_DefView",
    "Shell_TrayWnd",
    "Shell_SecondaryTrayWnd",
    "NotifyIconOverflowWindow",
    "XamlExplorerHostIslandWindow",
    "ForegroundStaging",
    "MultitaskingViewFrame",
    "Windows.UI.Core.CoreWindow",
    "Windows.UI.Composition.DesktopWindowContentBridge",
    "DesktopWindowXamlSource",
    "GlassPane",
    "Glass-Pane",
    "GlassPaneWindow",
}

_IGNORED_FULLSCREEN_TITLE_TOKENS = (
    "glass-pane",
    "glasspane",
    "danbooruwallpaper",
    "task view",
    "snap assist",
)


def is_window_cloaked(hwnd) -> bool:
    """Returns True if DWM reports the window as cloaked (e.g., suspended UWP app or on another Virtual Desktop)."""
    if not dwmapi or not hwnd:
        return False
    try:
        cloaked = ctypes.c_int(0)
        hr = dwmapi.DwmGetWindowAttribute(
            hwnd, DWMWA_CLOAKED, ctypes.byref(cloaked), ctypes.sizeof(cloaked)
        )
        return bool(hr == 0 and cloaked.value != 0)
    except Exception:
        return False


def detect_fullscreen_monitors(screens_to_check: list) -> dict:
    """
    Inspects visible, non-minimized, non-cloaked top-level Win32 windows in Z-order to detect
    whether a full screen application (such as a game or fullscreen video player) is covering each monitor.
    """
    result = {s["id"]: False for s in screens_to_check}
    if not screens_to_check:
        return result

    own_pid = os.getpid()
    desktop_hwnd = user32.GetDesktopWindow()
    shell_hwnd = user32.GetShellWindow()
    progman_hwnd = user32.FindWindowW("Progman", None)
    with INJECTION_LOCK:
        own_hwnds = set(DESKTOP_HWNDS.values())

    excluded_hwnds = {0, desktop_hwnd, shell_hwnd, progman_hwnd} | own_hwnds
    unresolved_screens = {s["id"]: s for s in screens_to_check}
    class_buf = ctypes.create_unicode_buffer(256)
    title_buf = ctypes.create_unicode_buffer(256)

    def _enum_top_windows(hwnd, lparam):
        if not unresolved_screens:
            return False
        if hwnd in excluded_hwnds:
            return True
        if not user32.IsWindowVisible(hwnd) or user32.IsIconic(hwnd):
            return True

        pid = wintypes.DWORD(0)
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value == own_pid:
            return True

        style = GetWindowLongPtrW(hwnd, GWL_STYLE) & 0xFFFFFFFF
        if style & WS_CHILD:
            return True

        ex_style = GetWindowLongPtrW(hwnd, GWL_EXSTYLE) & 0xFFFFFFFF
        # Ignore click-through transparent HUD overlays (e.g., Discord/Steam/GPU/Glass-Pane overlays)
        if (ex_style & WS_EX_TRANSPARENT) and (ex_style & WS_EX_LAYERED):
            return True

        if user32.GetClassNameW(hwnd, class_buf, 256) > 0:
            cname = class_buf.value
            if cname in _IGNORED_FULLSCREEN_CLASS_NAMES or "glasspane" in cname.lower():
                return True

        if user32.GetWindowTextW(hwnd, title_buf, 256) > 0:
            wtitle = title_buf.value.lower()
            if any(tok in wtitle for tok in _IGNORED_FULLSCREEN_TITLE_TOKENS):
                return True

        if is_window_cloaked(hwnd):
            return True

        rc = wintypes.RECT()
        if not user32.GetWindowRect(hwnd, ctypes.byref(rc)):
            return True

        win_w = rc.right - rc.left
        win_h = rc.bottom - rc.top
        if win_w < 240 or win_h < 180:
            return True

        client_rc = wintypes.RECT()
        has_client = bool(user32.GetClientRect(hwnd, ctypes.byref(client_rc)))
        client_w = (client_rc.right - client_rc.left) if has_client else win_w
        client_h = (client_rc.bottom - client_rc.top) if has_client else win_h

        for sid, s_info in list(unresolved_screens.items()):
            mx = int(s_info["x"])
            my = int(s_info["y"])
            mw = int(s_info["width"])
            mh = int(s_info["height"])

            covers_monitor_bounds = (
                rc.left <= mx + 2
                and rc.top <= my + 2
                and rc.right >= mx + mw - 2
                and rc.bottom >= my + mh - 2
            )
            if covers_monitor_bounds:
                # Distinguish true fullscreen applications (borderless games, F11 browsers, fullscreen video players)
                # from standard captioned maximized desktop windows when the taskbar is auto-hidden
                has_full_caption = ((style & WS_CAPTION) == WS_CAPTION)
                is_maximized_desktop_win = bool(style & WS_MAXIMIZE) and has_full_caption
                is_fullscreen_style = (
                    not is_maximized_desktop_win
                    and (
                        not has_full_caption
                        or (client_w >= mw and client_h >= mh)
                    )
                )
                if is_fullscreen_style:
                    result[sid] = True
                    unresolved_screens.pop(sid, None)

        return bool(unresolved_screens)

    cb = WNDENUMPROC(_enum_top_windows)
    try:
        user32.EnumWindows(cb, 0)
    except Exception:
        pass

    return result


def fullscreen_monitor_worker_loop():
    """
    Background watchdog daemon that:
    1. Polls display topology fingerprints every 0.75s to detect HDMI TV hotplugs (power-on/off),
       virtual desktop origin shifts, or resolution/DPI changes, debouncing the EDID handshake and
       automatically resynchronizing all wallpaper HWNDs and desktop icon metrics.
    2. Periodically verifies and self-heals desktop HWND parent/geometry integrity every ~2.25s.
    3. Polls connected displays for fullscreen applications on screens where 'pausefullscreen' is enabled.
    """
    last_committed_sig = None
    pending_sig = None
    pending_stable_ticks = 0
    heal_tick_counter = 0

    try:
        last_committed_sig = get_display_topology_signature()
    except Exception:
        pass

    while IS_RUNNING:
        time.sleep(0.75)
        if not IS_RUNNING:
            continue
        try:
            current_sig = get_display_topology_signature()
            if last_committed_sig is None:
                last_committed_sig = current_sig
            elif current_sig != last_committed_sig:
                if current_sig == pending_sig:
                    pending_stable_ticks += 1
                else:
                    pending_sig = current_sig
                    pending_stable_ticks = 1

                # Wait 1 settle tick (~0.75s) for Windows HDMI EDID/DPI negotiation to finish
                if pending_stable_ticks >= 2:
                    last_committed_sig = current_sig
                    pending_sig = None
                    pending_stable_ticks = 0
                    resync_all_displays_and_desktop(
                        reason="HDMI / Display topology change detected by watchdog"
                    )
            else:
                pending_sig = None
                pending_stable_ticks = 0
                heal_tick_counter = (heal_tick_counter + 1) % 3
                if heal_tick_counter == 0:
                    verify_and_heal_desktop_hwnds()

            if APP_PAUSED:
                continue

            screens_to_check = []
            disabled_fs_screens = []
            for s in get_connected_screens_snapshot():
                sid = s["id"]
                sc_cfg = get_screen_config(sid)
                enabled = bool(sc_cfg.get("enabled", False))
                pause_fs = _normalize_vsync_value(
                    sc_cfg.get("properties", {}).get("pausefullscreen", {}).get("value", True)
                )
                if enabled and pause_fs:
                    screens_to_check.append(s)
                else:
                    disabled_fs_screens.append(sid)

            # Clear fullscreen_paused on any screen where pausefullscreen or screen display was turned off
            for sid in disabled_fs_screens:
                changed_clear = False
                with DATA_LOCK:
                    st = get_screen_runtime_state(sid)
                    if st.get("fullscreen_paused", False):
                        st["fullscreen_paused"] = False
                        changed_clear = True
                if changed_clear:
                    push_pause_states_to_webviews(sid)
                    if is_screen_enabled(sid) and not is_screen_effectively_paused(sid):
                        ensure_screen_tag_pool_populated_async(sid, force_reset=False)

            if not screens_to_check:
                continue

            fs_map = detect_fullscreen_monitors(screens_to_check)
            for s in screens_to_check:
                sid = s["id"]
                is_fs_now = bool(fs_map.get(sid, False))
                state_changed = False
                manual_paused = False
                with DATA_LOCK:
                    st = get_screen_runtime_state(sid)
                    prev_fs = bool(st.get("fullscreen_paused", False))
                    manual_paused = bool(st.get("wallpaper_paused", False))
                    if prev_fs != is_fs_now:
                        st["fullscreen_paused"] = is_fs_now
                        state_changed = True

                if state_changed:
                    push_pause_states_to_webviews(sid)
                    if is_fs_now:
                        log_event(
                            "perf",
                            f"Full screen application detected on {sid} — automatically paused wallpaper & background workers to conserve resources.",
                        )
                    else:
                        log_event(
                            "perf",
                            f"Full screen application exited on {sid} — automatically resumed wallpaper.",
                        )
                        if not manual_paused:
                            ensure_screen_tag_pool_populated_async(sid, force_reset=False)
        except Exception:
            pass


def on_webview_started():
    for screen_info in CONNECTED_SCREENS:
        sid = screen_info["id"]
        win = WEBVIEW_WINDOWS.get(sid)
        win_title = f"{WEBVIEW_WINDOW_TITLE_PREFIX}_{sid}"
        if win:
            win.events.loaded += (
                lambda s=screen_info, w=win, t=win_title: threading.Thread(
                    target=inject_and_sync_screen, args=(s, w, t), daemon=True
                ).start()
            )
    time.sleep(2.0)
    for screen_info in CONNECTED_SCREENS:
        sid = screen_info["id"]
        if sid not in DESKTOP_INJECTED_SET and sid in WEBVIEW_WINDOWS:
            win_title = f"{WEBVIEW_WINDOW_TITLE_PREFIX}_{sid}"
            inject_and_sync_screen(screen_info, WEBVIEW_WINDOWS[sid], win_title)

    sync_all_screens_z_order_and_geometry()


if __name__ == "__main__":
    enforce_single_instance_or_exit()

    try:
        HTTP_SERVER = ReusableThreadingHTTPServer(("127.0.0.1", PORT), ProxyHandler)
    except OSError as bind_err:
        # Secondary safeguard if port 8088 is already exclusively bound
        _signal_existing_instance_to_show_settings()
        safe_console_print(f"[APP] Port {PORT} is already exclusively bound ({bind_err}). Exiting duplicate instance.")
        os._exit(0)

    server_thread = threading.Thread(target=HTTP_SERVER.serve_forever, daemon=True)
    server_thread.start()
    transport_summary = "curl_cffi HTTP/2 + DoH" if CURL_CFFI_AVAILABLE else "stdlib TLS 1.3 + DoH SNI fallback"
    log_event("server", f"Service running on http://127.0.0.1:{PORT} ({transport_summary})")

    single_instance_thread = threading.Thread(
        target=single_instance_signal_worker_loop, daemon=True
    )
    single_instance_thread.start()

    suggestion_thread = threading.Thread(target=suggestion_worker_loop, daemon=True)
    suggestion_thread.start()

    fullscreen_thread = threading.Thread(target=fullscreen_monitor_worker_loop, daemon=True)
    fullscreen_thread.start()

    tray_thread = threading.Thread(target=setup_tray, daemon=True)
    tray_thread.start()

    tk_thread = threading.Thread(target=run_tkinter_ui, daemon=True)
    tk_thread.start()

    CONNECTED_SCREENS = enumerate_connected_monitors()
    for screen_info in CONNECTED_SCREENS:
        sid = screen_info["id"]
        win_title = f"{WEBVIEW_WINDOW_TITLE_PREFIX}_{sid}"
        win = webview.create_window(
            title=win_title,
            url=f"http://127.0.0.1:{PORT}/?screen={sid}",
            x=screen_info["x"],
            y=screen_info["y"],
            width=screen_info["width"],
            height=screen_info["height"],
            frameless=True,
            easy_drag=False,
            background_color="#0b0b0d",
        )
        WEBVIEW_WINDOWS[sid] = win

    try:
        # Run WebView2 in ephemeral private_mode without a persistent storage_path folder
        webview.start(
            on_webview_started,
            debug=False,
            private_mode=True,
        )
    except KeyboardInterrupt:
        pass
    finally:
        shutdown_app()
