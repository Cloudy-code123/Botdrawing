"""Background Paint-control thread."""

import os
import random
import threading
import time

import cv2
import numpy as np
import pyautogui

from .config import EXACT_IMAGE_MODE, SPEEDS, STAGES
from .windows import (
    VK_ESCAPE,
    VK_SPACE,
    _u32,
    create_blank_canvas,
    focus_paint,
    key_down,
    launch_paint,
    mouse_down,
    mouse_move,
    mouse_up,
    paint_canvas_box,
)


class Stopped(Exception):
    """Raised when the user requests that the drawing stop."""


class Robot(threading.Thread):
    daemon = True

    def __init__(self, cfg, q):
        super().__init__()
        self.cfg = cfg
        self.q = q
        self.running = threading.Event()
        self.running.set()
        self.stopping = threading.Event()
        self._space_was_down = False
        self.paint_hwnd = None

    def msg(self, *args):
        self.q.put(args)

    def pause(self):
        self.running.clear()

    def resume(self):
        self.running.set()

    def stop(self):
        self.stopping.set()
        self.running.set()

    def _check(self, pen=False):
        while True:
            if key_down(VK_ESCAPE):
                self.stopping.set()
            space_down = key_down(VK_SPACE)
            if space_down and not self._space_was_down:
                if self.running.is_set():
                    self.pause()
                    self.msg(
                        "paused", "Paused. Press Space or Resume to continue.")
                else:
                    self.resume()
                    self.msg("resumed", "Resumed.")
            self._space_was_down = space_down

            if (self.paint_hwnd and self.running.is_set()
                    and _u32.GetForegroundWindow() != self.paint_hwnd):
                self.pause()
                self.msg(
                    "paused",
                    "Paint lost focus. Return to Paint, then Resume.")

            if self.stopping.is_set():
                if pen:
                    mouse_up()
                raise Stopped
            if self.running.is_set():
                return
            if pen:
                mouse_up()
            time.sleep(0.05)

    def run(self):
        try:
            if self.cfg["mode"] == EXACT_IMAGE_MODE:
                image_path = self.cfg["image_path"]
                self.msg("status", "Opening the original image in Paint…")
                hwnd = launch_paint(image_path)
                if not hwnd:
                    raise RuntimeError(
                        "Paint opened, but its window for the uploaded image "
                        "could not be found."
                    )
                if not focus_paint(hwnd, maximize=False):
                    raise RuntimeError(
                        "The image opened in Paint, but Paint could not be "
                        "brought to the foreground."
                    )
                self.msg("done", "Original image opened in Paint unchanged.")
                return

            strokes = self.cfg["strokes"]
            image_width, image_height = self.cfg["dim"]
            speed = self.cfg["speed"]

            self.msg("status", "Opening a blank Paint canvas for drawing…")
            canvas_path, canvas_size = create_blank_canvas(
                (image_width, image_height))
            try:
                hwnd = launch_paint(canvas_path)
                if not hwnd:
                    raise RuntimeError(
                        "Could not open the blank drawing canvas in Paint.")
                if not focus_paint(hwnd, maximize=False):
                    raise RuntimeError(
                        "Paint opened, but could not be brought to the "
                        "foreground."
                    )
                self.paint_hwnd = hwnd
                time.sleep(0.3)
                box = paint_canvas_box(canvas_size)
            finally:
                os.remove(canvas_path)

            box_left, box_top, box_right, box_bottom = box
            canvas_width = box_right - box_left
            canvas_height = box_bottom - box_top

            scale = min(
                canvas_width / image_width,
                canvas_height / image_height) * 0.95
            offset_x = box_left + (canvas_width - image_width * scale) / 2
            offset_y = box_top + (canvas_height - image_height * scale) / 2

            self.msg(
                "status",
                f"Drawing {len(strokes)} strokes. "
                "Press ESC to stop, Space to pause.")

            self._draw(
                strokes, scale, offset_x, offset_y, box, speed)

            self.msg("done", "Drawing finished!")
        except Stopped:
            self.msg("done", "Stopped by user.")
        except pyautogui.FailSafeException:
            self.msg("done", "Emergency stop (mouse hit corner).")
        except Exception as exc:
            self.msg("error", str(exc))
        finally:
            try:
                mouse_up()
                pyautogui.mouseUp()
            except Exception:
                pass

    def _draw(self, strokes, scale, offset_x, offset_y, box, speed_name):
        step, (delay_min, delay_max), (pause_min, pause_max) = (
            SPEEDS[speed_name])
        box_left, box_top, box_right, box_bottom = box
        image_width, image_height = self.cfg["dim"]
        preview_scale = min(
            500 / image_width, 320 / image_height, 1.0)
        preview_width = max(1, int(image_width * preview_scale))
        preview_height = max(1, int(image_height * preview_scale))
        preview_canvas = np.full(
            (preview_height, preview_width, 3), 255, np.uint8)
        total = sum(len(points) for _, points in strokes)
        done = 0
        start_time = time.time()
        last_preview = 0.0
        last_stage = -1

        def clamp(x, y):
            return (
                min(max(x, box_left), box_right),
                min(max(y, box_top), box_bottom),
            )

        for stage, points in strokes:
            self._check()

            if stage != last_stage:
                last_stage = stage
                self.msg("stage", STAGES[stage])

            mapped = points * scale + (offset_x, offset_y)

            dense = [mapped[0]]
            for start, end in zip(mapped[:-1], mapped[1:]):
                count = max(1, int(np.linalg.norm(end - start) // step))
                for index in range(1, count + 1):
                    dense.append(start + (end - start) * index / count)

            dense = [
                clamp(*(point + np.random.normal(0, 0.3, 2)))
                for point in dense
            ]

            start_x, start_y = dense[0]
            mouse_move(start_x, start_y)
            time.sleep(0.003)
            mouse_down(start_x, start_y)

            try:
                for x, y in dense[1:]:
                    self._check(pen=True)
                    mouse_move(x, y)
                    time.sleep(max(
                        random.uniform(delay_min, delay_max), 0.006))
            finally:
                mouse_up()

            if pause_max > 0:
                time.sleep(random.uniform(pause_min, pause_max))

            preview_points = np.rint(
                points * preview_scale).astype(np.int32)
            cv2.polylines(
                preview_canvas, [preview_points], False,
                (40, 40, 40), 1, cv2.LINE_AA)
            done += len(points)
            elapsed = time.time() - start_time
            now = time.time()
            if done > 0 and (now - last_preview >= 0.1 or done >= total):
                eta = elapsed / done * (total - done)
                self.msg(
                    "progress", done / total, eta, preview_canvas.copy())
                last_preview = now
