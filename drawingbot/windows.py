"""Windows Paint discovery, sizing, and mouse/keyboard input."""

import ctypes
import ctypes.wintypes as wt
import os
import subprocess
import tempfile
import time

from .dpi import enable_dpi_awareness

enable_dpi_awareness()

import cv2
import numpy as np
import pyautogui
from PIL import Image

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0
pyautogui.MINIMUM_DURATION = 0
pyautogui.MINIMUM_SLEEP = 0

_u32 = ctypes.windll.user32

INPUT_MOUSE = 0
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_ABSOLUTE = 0x8000
VK_ESCAPE = 0x1B
VK_SPACE = 0x20


class _MouseInput(ctypes.Structure):
    _fields_ = [
        ("dx", wt.LONG),
        ("dy", wt.LONG),
        ("mouseData", wt.DWORD),
        ("dwFlags", wt.DWORD),
        ("time", wt.DWORD),
        ("dwExtraInfo", ctypes.c_size_t),
    ]


class _InputData(ctypes.Union):
    _fields_ = [("mi", _MouseInput)]


class _Input(ctypes.Structure):
    _fields_ = [("type", wt.DWORD), ("data", _InputData)]


_u32.GetWindowThreadProcessId.argtypes = [
    wt.HWND, ctypes.POINTER(wt.DWORD)]
_u32.GetWindowThreadProcessId.restype = wt.DWORD
_u32.GetWindowTextW.argtypes = [wt.HWND, wt.LPWSTR, ctypes.c_int]
_u32.GetWindowTextW.restype = ctypes.c_int
_u32.IsWindowVisible.argtypes = [wt.HWND]
_u32.IsWindowVisible.restype = wt.BOOL
_u32.IsWindow.argtypes = [wt.HWND]
_u32.IsWindow.restype = wt.BOOL
_u32.GetWindowRect.argtypes = [wt.HWND, ctypes.POINTER(wt.RECT)]
_u32.GetWindowRect.restype = wt.BOOL
_u32.ShowWindow.argtypes = [wt.HWND, ctypes.c_int]
_u32.ShowWindow.restype = wt.BOOL
_u32.SetForegroundWindow.argtypes = [wt.HWND]
_u32.SetForegroundWindow.restype = wt.BOOL
_u32.GetForegroundWindow.restype = wt.HWND
_u32.SetWindowPos.argtypes = [
    wt.HWND, wt.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
    wt.UINT,
]
_u32.SetWindowPos.restype = wt.BOOL
_u32.SendMessageW.argtypes = [
    wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM,
]
_u32.SendMessageW.restype = wt.LPARAM
_u32.SendInput.argtypes = [
    wt.UINT, ctypes.POINTER(_Input), ctypes.c_int,
]
_u32.SendInput.restype = wt.UINT

SWP_NOZORDER = 0x0004
SWP_NOACTIVATE = 0x0010
WM_HSCROLL = 0x0114
WM_VSCROLL = 0x0115
SB_LEFT = 6
SB_TOP = 6


def screen_size():
    return _u32.GetSystemMetrics(0), _u32.GetSystemMetrics(1)


def _send_mouse_input(flags, dx=0, dy=0):
    event = _Input(
        type=INPUT_MOUSE,
        data=_InputData(mi=_MouseInput(dx, dy, 0, flags, 0, 0)),
    )
    if _u32.SendInput(
            1, ctypes.byref(event), ctypes.sizeof(_Input)) != 1:
        raise ctypes.WinError()


def mouse_move(x, y):
    pyautogui.failSafeCheck()
    screen_width, screen_height = screen_size()
    dx = round(65535 * x / max(screen_width - 1, 1))
    dy = round(65535 * y / max(screen_height - 1, 1))
    _send_mouse_input(
        MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE, dx, dy)


def mouse_down(x, y):
    mouse_move(x, y)
    _send_mouse_input(MOUSEEVENTF_LEFTDOWN)


def mouse_up():
    _send_mouse_input(MOUSEEVENTF_LEFTUP)


def set_paint_brush_size(hwnd, size, current_size):
    if not hwnd or not _u32.IsWindow(hwnd):
        raise RuntimeError("Paint is not available for brush-size selection.")
    if size < 1 or current_size < 1:
        raise ValueError("Paint brush sizes must be positive.")
    if (_u32.GetForegroundWindow() != hwnd
            and not focus_paint(hwnd, maximize=False)):
        raise RuntimeError(
            "Paint could not be brought to the foreground to change line size."
        )

    key = "add" if size > current_size else "subtract"
    for _ in range(abs(size - current_size)):
        pyautogui.hotkey("ctrl", key)
    time.sleep(0.04)


def key_down(virtual_key):
    return bool(_u32.GetAsyncKeyState(virtual_key) & 0x8000)


def _is_paint_window(title, window_pid):
    title = title.lower()
    return window_pid != os.getpid() and bool(
        title and ("paint" in title or "画图" in title))


def _matches_image_window(title, image_path):
    if not image_path:
        return True
    expected_name = os.path.splitext(os.path.basename(image_path))[0].lower()
    return bool(expected_name and expected_name in title.lower())


def find_paint_hwnd(image_path=None, process_id=None):
    """Return the HWND of MS Paint, or None."""
    result = []
    window_proc = ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)

    def callback(hwnd, _lp):
        if _u32.IsWindowVisible(hwnd):
            title_buffer = ctypes.create_unicode_buffer(300)
            _u32.GetWindowTextW(hwnd, title_buffer, 300)
            pid = wt.DWORD()
            _u32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            launched_process = (
                process_id is not None and pid.value == process_id)
            if (launched_process
                    or (_is_paint_window(title_buffer.value, pid.value)
                        and _matches_image_window(
                            title_buffer.value, image_path))):
                result.append(hwnd)
        return True

    _u32.EnumWindows(window_proc(callback), 0)
    return result[0] if result else None


def _size_paint_window_for_image(hwnd, image_path):
    with Image.open(image_path) as image:
        image_width, image_height = image.size

    screen_width, screen_height = screen_size()
    chrome_width = min(320, max(180, int(screen_width * 0.15)))
    chrome_height = min(360, max(220, int(screen_height * 0.3)))
    window_width = image_width + chrome_width
    window_height = image_height + chrome_height

    if window_width > screen_width or window_height > screen_height:
        _u32.ShowWindow(hwnd, 3)  # SW_MAXIMIZE
        return

    _u32.ShowWindow(hwnd, 9)  # SW_RESTORE
    x = (screen_width - window_width) // 2
    y = (screen_height - window_height) // 2
    if not _u32.SetWindowPos(
            hwnd, None, x, y, window_width, window_height,
            SWP_NOZORDER | SWP_NOACTIVATE):
        raise ctypes.WinError()


def launch_paint(image_path=None):
    """Open Paint on a document, size its window, and return its HWND."""
    process = None
    if image_path:
        windows_dir = os.environ.get("WINDIR", r"C:\Windows")
        paint_exe = os.path.join(windows_dir, "System32", "mspaint.exe")
        if not os.path.isfile(paint_exe):
            paint_exe = "mspaint"
        try:
            process = subprocess.Popen(
                [paint_exe, os.path.abspath(image_path)])
        except OSError as exc:
            raise RuntimeError(
                f"Could not open the uploaded image in Microsoft Paint: {exc}"
            ) from exc
    else:
        try:
            os.startfile("mspaint")
        except OSError:
            try:
                subprocess.Popen("mspaint", shell=True)
            except OSError:
                subprocess.Popen(["cmd", "/c", "start", "", "mspaint"])

    for _ in range(60):
        time.sleep(0.2)
        hwnd = find_paint_hwnd(
            image_path, process.pid if process is not None else None)
        if hwnd:
            if image_path:
                _size_paint_window_for_image(hwnd, image_path)
            else:
                _u32.ShowWindow(hwnd, 3)  # SW_MAXIMIZE
            time.sleep(0.8)
            _u32.SetForegroundWindow(hwnd)
            time.sleep(0.4)
            return hwnd
    return None


def focus_paint(hwnd, maximize=True):
    if hwnd and _u32.IsWindow(hwnd):
        if maximize:
            _u32.ShowWindow(hwnd, 9)  # SW_RESTORE
            _u32.ShowWindow(hwnd, 3)  # SW_MAXIMIZE
        _u32.SetForegroundWindow(hwnd)
        time.sleep(0.3)
        return _u32.GetForegroundWindow() == hwnd
    return False


def prepare_paint_canvas(hwnd):
    """Reset Paint scrollbars and zoom before locating the drawing canvas."""
    if not hwnd or not _u32.IsWindow(hwnd):
        raise RuntimeError("Paint is not available for canvas preparation.")

    if not focus_paint(hwnd, maximize=False):
        raise RuntimeError(
            "Paint could not be brought to the foreground for canvas setup."
        )

    _u32.SendMessageW(hwnd, WM_HSCROLL, SB_LEFT, 0)
    _u32.SendMessageW(hwnd, WM_VSCROLL, SB_TOP, 0)

    pyautogui.hotkey("ctrl", "1")
    time.sleep(0.5)

    _u32.SendMessageW(hwnd, WM_HSCROLL, SB_LEFT, 0)
    _u32.SendMessageW(hwnd, WM_VSCROLL, SB_TOP, 0)


def create_blank_canvas(size):
    width, height = size
    screen_width, screen_height = screen_size()
    chrome_width = min(320, max(180, int(screen_width * 0.15)))
    chrome_height = min(360, max(220, int(screen_height * 0.3)))
    scale = min(
        (screen_width - chrome_width) / width,
        (screen_height - chrome_height) / height,
        1.0,
    )
    canvas_size = (
        max(1, int(width * scale)), max(1, int(height * scale)))

    with tempfile.NamedTemporaryFile(
            prefix="drawingbot_canvas_", suffix=".png", delete=False) as temp:
        path = temp.name
    try:
        Image.new("RGB", canvas_size, "white").save(path, format="PNG")
    except Exception:
        os.remove(path)
        raise
    return path, canvas_size


def paint_canvas_box(expected_size):
    screenshot = np.asarray(pyautogui.screenshot().convert("RGB"))
    white = cv2.inRange(
        screenshot,
        np.array((250, 250, 250), dtype=np.uint8),
        np.array((255, 255, 255), dtype=np.uint8),
    )
    contours, _ = cv2.findContours(
        white, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    expected_ratio = expected_size[0] / expected_size[1]
    minimum_area = max(
        3000, int(screenshot.shape[0] * screenshot.shape[1] * 0.003))
    candidates = []
    for contour in contours:
        x, y, width, height = cv2.boundingRect(contour)
        if height == 0:
            continue
        area = width * height
        ratio = width / height
        ratio_error = abs(ratio - expected_ratio) / expected_ratio
        if area >= minimum_area and ratio_error <= 0.08:
            candidates.append((area, (x, y, x + width, y + height)))

    if not candidates:
        raise RuntimeError(
            "Could not locate Paint's blank canvas. Make sure Paint is visible "
            "and not covered by another window."
        )
    return max(candidates, key=lambda candidate: candidate[0])[1]
