"""Native Windows chrome helpers (borderless window, DWM dark mode, dragging)."""

from __future__ import annotations

import ctypes
import tkinter as tk
from ctypes import wintypes

GWL_STYLE = -16
GWL_EXSTYLE = -20
WS_CAPTION = 0x00C00000
WS_THICKFRAME = 0x00040000
WS_MINIMIZEBOX = 0x00020000
WS_MAXIMIZEBOX = 0x00010000
WS_SYSMENU = 0x00080000
WS_EX_APPWINDOW = 0x00040000
WS_EX_TOOLWINDOW = 0x00000080
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOZORDER = 0x0004
SWP_NOACTIVATE = 0x0010
SWP_FRAMECHANGED = 0x0020
SWP_NOOWNERZORDER = 0x0200
WM_NCLBUTTONDOWN = 0x00A1
HTCAPTION = 0x0002
MONITOR_DEFAULTTONEAREST = 2

DWMWA_USE_IMMERSIVE_DARK_MODE = 20
DWMWA_WINDOW_CORNER_PREFERENCE = 33
DWMWA_BORDER_COLOR = 34
DWMWCP_ROUND = 2


class MONITORINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("rcMonitor", wintypes.RECT),
        ("rcWork", wintypes.RECT),
        ("dwFlags", wintypes.DWORD),
    ]


def hwnd_for(window: tk.Misc) -> int:
    try:
        window.update_idletasks()
        child = window.winfo_id()
        parent = ctypes.windll.user32.GetParent(child)
        return parent or child
    except Exception:
        return 0


def _set_dwm(hwnd: int, color: str, rounded: bool = True) -> None:
    try:
        dark = ctypes.c_int(1)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE, ctypes.byref(dark), 4
        )
        if rounded:
            preference = ctypes.c_int(DWMWCP_ROUND)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, DWMWA_WINDOW_CORNER_PREFERENCE, ctypes.byref(preference), 4
            )
        value = color.lstrip("#")
        if len(value) == 6:
            red, green, blue = int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)
            colorref = ctypes.c_int(blue << 16 | green << 8 | red)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, DWMWA_BORDER_COLOR, ctypes.byref(colorref), 4
            )
    except Exception:
        pass


def make_borderless(window: tk.Misc, *, border_color: str = "#1a2638", taskbar: bool = True) -> int:
    hwnd = hwnd_for(window)
    if not hwnd:
        return 0
    user32 = ctypes.windll.user32
    style = user32.GetWindowLongW(hwnd, GWL_STYLE)
    style = (style & ~WS_CAPTION) | WS_THICKFRAME | WS_MINIMIZEBOX | WS_MAXIMIZEBOX | WS_SYSMENU
    user32.SetWindowLongW(hwnd, GWL_STYLE, style)
    exstyle = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    if taskbar:
        exstyle |= WS_EX_APPWINDOW
    else:
        exstyle = (exstyle & ~WS_EX_APPWINDOW) | WS_EX_TOOLWINDOW
    user32.SetWindowLongW(hwnd, GWL_EXSTYLE, exstyle)
    user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, SWP_NOSIZE | SWP_NOMOVE | SWP_NOZORDER | SWP_NOACTIVATE | SWP_FRAMECHANGED)
    _set_dwm(hwnd, border_color)
    return hwnd


def make_dialog_borderless(window: tk.Misc, *, border_color: str = "#24344a") -> int:
    hwnd = hwnd_for(window)
    if not hwnd:
        return 0
    user32 = ctypes.windll.user32
    style = user32.GetWindowLongW(hwnd, GWL_STYLE)
    style = style & ~(WS_CAPTION | WS_MINIMIZEBOX | WS_MAXIMIZEBOX)
    style |= WS_THICKFRAME
    user32.SetWindowLongW(hwnd, GWL_STYLE, style)
    exstyle = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    exstyle = (exstyle & ~WS_EX_APPWINDOW) | WS_EX_TOOLWINDOW
    user32.SetWindowLongW(hwnd, GWL_EXSTYLE, exstyle)
    user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, SWP_NOSIZE | SWP_NOMOVE | SWP_NOZORDER | SWP_NOACTIVATE | SWP_FRAMECHANGED)
    _set_dwm(hwnd, border_color)
    return hwnd


def begin_drag(window: tk.Misc) -> bool:
    """Hand the current mouse drag to the native Windows move loop.

    Posting ``WM_NCLBUTTONDOWN`` with ``HTCAPTION`` lets Windows move the whole
    window as one composited surface, including Aero Snap.  Repainting the
    client area for every mouse event (the old geometry-based approach) makes
    the window lag behind the pointer and leaves visual trails on slower
    machines.  ``PostMessage`` is used instead of ``SendMessage`` so the Tk
    callback returns before Windows enters its modal move loop.
    """

    hwnd = hwnd_for(window)
    if not hwnd:
        return False
    try:
        user32 = ctypes.windll.user32
        user32.ReleaseCapture()
        return bool(user32.PostMessageW(hwnd, WM_NCLBUTTONDOWN, HTCAPTION, 0))
    except Exception:
        return False


def left_button_down() -> bool:
    """Return True while the physical left mouse button is held."""

    try:
        return bool(ctypes.windll.user32.GetAsyncKeyState(0x01) & 0x8000)
    except Exception:
        return False


RDW_INVALIDATE = 0x0001
RDW_UPDATENOW = 0x0100
RDW_NOERASE = 0x0020


def repaint_now(window: tk.Misc) -> None:
    """Repaint a window's exposed bands immediately.

    Moving rows natively leaves the pixels they covered in the content frame
    until Tk handles the paint messages.  During fast scrolling that can show a
    stale band for a frame.  Forcing the parent to repaint right after the batch
    keeps every presented frame coherent.
    """

    try:
        ctypes.windll.user32.RedrawWindow(
            window.winfo_id(),
            None,
            None,
            RDW_INVALIDATE | RDW_UPDATENOW | RDW_NOERASE,
        )
    except Exception:
        pass


def move_windows_atomically(moves: list[tuple[int, int, int]]) -> bool:
    """Reposition several child windows in one deferred-position batch.

    ``moves`` holds ``(hwnd, x, y)`` in parent-client coordinates.  Scrolling
    has to move every visible row of the page; moving them one by one lets the
    compositor present a frame where some rows are already at the new offset
    and others are not, which is exactly the tearing that made fast wheel spins
    and scrollbar drags look broken.  ``BeginDeferWindowPos`` applies the whole
    set in a single operation, so the window is only ever presented at one
    offset.
    """

    if not moves:
        return True
    try:
        user32 = ctypes.windll.user32
        user32.BeginDeferWindowPos.restype = ctypes.c_void_p
        user32.BeginDeferWindowPos.argtypes = [ctypes.c_int]
        user32.DeferWindowPos.restype = ctypes.c_void_p
        user32.DeferWindowPos.argtypes = [
            ctypes.c_void_p,
            wintypes.HWND,
            wintypes.HWND,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_uint,
        ]
        user32.EndDeferWindowPos.argtypes = [ctypes.c_void_p]
        handle = user32.BeginDeferWindowPos(len(moves))
        if not handle:
            return False
        for hwnd, x, y in moves:
            handle = user32.DeferWindowPos(
                handle,
                hwnd,
                0,
                x,
                y,
                0,
                0,
                SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE | SWP_NOOWNERZORDER,
            )
            if not handle:
                return False
        return bool(user32.EndDeferWindowPos(handle))
    except Exception:
        return False


def make_draggable(window: tk.Misc, *widgets: tk.Misc, allow_maximized: bool = False) -> None:
    """Move a borderless window with the mouse, without native re-entrancy."""

    state = {"dx": 0, "dy": 0, "active": False, "native": False, "press": (0, 0)}

    def press(event: tk.Event) -> None:
        if max_button_state(window) and not allow_maximized:
            return
        state["dx"] = event.x_root - window.winfo_x()
        state["dy"] = event.y_root - window.winfo_y()
        state["press"] = (event.x_root, event.y_root)
        state["active"] = True
        state["native"] = False

    def motion(event: tk.Event) -> None:
        if not state["active"] or state["native"]:
            return
        press_x, press_y = state["press"]
        if abs(event.x_root - press_x) + abs(event.y_root - press_y) < 3:
            return
        if begin_drag(window):
            state["native"] = True
            return
        x = event.x_root - int(state["dx"])
        y = event.y_root - int(state["dy"])
        window.geometry(f"+{x}+{y}")

    def release(_event: tk.Event) -> None:
        state["active"] = False
        state["native"] = False

    for widget in widgets:
        widget.bind("<ButtonPress-1>", press, add="+")
        widget.bind("<B1-Motion>", motion, add="+")
        widget.bind("<ButtonRelease-1>", release, add="+")


def max_button_state(window: tk.Misc) -> bool:
    try:
        return bool(ctypes.windll.user32.IsZoomed(hwnd_for(window)))
    except Exception:
        return False


def work_area(window: tk.Misc) -> tuple[int, int, int, int] | None:
    """Return the monitor work area (excluding the taskbar) in Tk units.

    The values describe the client size that makes the outer window fit the
    work area, so the resize frame never overlaps the taskbar.
    """

    try:
        hwnd = hwnd_for(window)
        user32 = ctypes.windll.user32
        monitor = user32.MonitorFromWindow(hwnd, MONITOR_DEFAULTTONEAREST)
        info = MONITORINFO()
        info.cbSize = ctypes.sizeof(MONITORINFO)
        if not user32.GetMonitorInfoW(monitor, ctypes.byref(info)):
            return None
        rect = info.rcWork
        outer = wintypes.RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(outer))
        client = wintypes.RECT()
        user32.GetClientRect(hwnd, ctypes.byref(client))
        inset_x = max(0, (outer.right - outer.left) - client.right)
        inset_y = max(0, (outer.bottom - outer.top) - client.bottom)
        physical_width = user32.GetSystemMetrics(0) or 1
        logical_width = window.winfo_screenwidth() or physical_width
        scale = physical_width / logical_width
        width = round((rect.right - rect.left - inset_x) / scale)
        height = round((rect.bottom - rect.top - inset_y) / scale)
        x = round(rect.left / scale)
        y = round(rect.top / scale)
        return width, height, x, y
    except Exception:
        return None


def center_window(window: tk.Misc, width: int, height: int, *, parent: tk.Misc | None = None) -> str:
    window.update_idletasks()
    if parent is not None:
        try:
            px = parent.winfo_rootx()
            py = parent.winfo_rooty()
            pw = parent.winfo_width()
            ph = parent.winfo_height()
            x = px + (pw - width) // 2
            y = py + (ph - height) // 2
            geometry = f"{width}x{height}+{max(0, x)}+{max(0, y)}"
            window.geometry(geometry)
            return geometry
        except Exception:
            pass
    screen_w = window.winfo_screenwidth()
    screen_h = window.winfo_screenheight()
    x = (screen_w - width) // 2
    y = (screen_h - height) // 2
    geometry = f"{width}x{height}+{max(0, x)}+{max(0, y)}"
    window.geometry(geometry)
    return geometry


def set_app_id(app_id: str) -> None:
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
    except Exception:
        pass
