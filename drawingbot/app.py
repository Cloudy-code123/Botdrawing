"""Tkinter interface for Auto Paint Robot."""

from .dpi import enable_dpi_awareness

enable_dpi_awareness()

import queue
import tkinter as tk
from tkinter import filedialog, ttk

from PIL import Image, ImageOps, ImageTk

from .config import (
    QUALITY,
    SPEEDS,
    STYLES,
)
from .planning import plan_drawing, render_preview
from .robot import Robot
from .windows import focus_paint


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Auto Sketch Robot")
        self.geometry("600x760")
        self.minsize(520, 640)

        self.q = queue.Queue()
        self.robot = None
        self.image_path = None
        self.strokes = None
        self.stroke_dim = None
        self._closing = False
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        padding = dict(padx=12, pady=5)

        ttk.Button(
            self, text="Upload Image (JPG / PNG / BMP / WebP)",
            command=self._pick).pack(fill="x", **padding)

        self.preview = ttk.Label(
            self, text="No image loaded", anchor="center", relief="groove")
        self.preview.pack(fill="both", expand=True, **padding)
        self._tkimg = None

        self.info_l = ttk.Label(self, text="")
        self.info_l.pack(anchor="w", padx=12)

        options = ttk.Frame(self)
        options.pack(fill="x", **padding)
        self.style_v = tk.StringVar(value="Realistic Pencil Portrait")
        self.speed_v = tk.StringVar(value="Normal")
        self.quality_v = tk.StringVar(value="Standard")
        for row, (label, variable, values) in enumerate([
            ("Style", self.style_v, list(STYLES)),
            ("Speed", self.speed_v, list(SPEEDS)),
            ("Quality", self.quality_v, list(QUALITY)),
        ]):
            ttk.Label(options, text=label, width=8).grid(
                row=row, column=0, sticky="w", pady=2)
            combo = ttk.Combobox(
                options, textvariable=variable, values=values,
                state="readonly")
            combo.grid(row=row, column=1, sticky="ew")
            combo.bind(
                "<<ComboboxSelected>>",
                lambda event: self._replan())
        options.columnconfigure(1, weight=1)

        buttons = ttk.Frame(self)
        buttons.pack(fill="x", **padding)
        self.b_start = ttk.Button(
            buttons, text="▶  Start Drawing", command=self._start)
        self.b_pause = ttk.Button(
            buttons, text="⏸  Pause", command=self._pause, state="disabled")
        self.b_resume = ttk.Button(
            buttons, text="⏵  Resume", command=self._resume, state="disabled")
        self.b_stop = ttk.Button(
            buttons, text="⏹  STOP (ESC)", command=self._stop,
            state="disabled")
        for button in (
                self.b_start, self.b_pause, self.b_resume, self.b_stop):
            button.pack(side="left", expand=True, fill="x", padx=2)

        self.bar = ttk.Progressbar(self, maximum=1.0)
        self.bar.pack(fill="x", **padding)
        self.stage_l = ttk.Label(self, text="Stage: —")
        self.stage_l.pack(anchor="w", padx=12)
        self.eta_l = ttk.Label(self, text="Remaining: —")
        self.eta_l.pack(anchor="w", padx=12)
        self.status_l = ttk.Label(
            self,
            text="Upload a photo, then click Start Drawing.\n"
            "The robot will open Paint and draw automatically.",
            wraplength=560)
        self.status_l.pack(anchor="w", padx=12, pady=(0, 10))

        self.after(80, self._poll)

    def _ask_yes_no(self, title, prompt):
        result = {"value": False}
        dialog = tk.Toplevel(self)
        dialog.title(title)
        dialog.transient(self)
        dialog.resizable(False, False)
        dialog.configure(padx=18, pady=14)

        ttk.Label(
            dialog,
            text=prompt,
            wraplength=430,
            justify="left",
        ).pack(fill="x", pady=(0, 16))

        buttons = ttk.Frame(dialog)
        buttons.pack(fill="x", pady=(4, 0))

        def accept():
            result["value"] = True
            dialog.destroy()

        def decline():
            result["value"] = False
            dialog.destroy()

        ttk.Button(buttons, text="Yes", width=10, command=accept).pack(
            side="left")
        ttk.Button(buttons, text="No", width=10, command=decline).pack(
            side="right")

        dialog.bind("<Return>", lambda event: accept())
        dialog.bind("<Escape>", lambda event: decline())
        dialog.protocol("WM_DELETE_WINDOW", decline)

        dialog.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width() - dialog.winfo_width()) // 2
        y = self.winfo_rooty() + (self.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{max(0, x)}+{max(0, y)}")
        dialog.grab_set()
        dialog.focus_force()
        self.wait_window(dialog)
        return result["value"]

    def _show_message(self, title, prompt, kind="error"):
        dialog = tk.Toplevel(self)
        dialog.title(title)
        dialog.transient(self)
        dialog.resizable(False, False)
        dialog.configure(padx=18, pady=14)

        ttk.Label(
            dialog,
            text=prompt,
            wraplength=430,
            justify="left",
        ).pack(fill="x", pady=(0, 16))

        def close():
            dialog.destroy()

        ttk.Button(dialog, text="OK", width=10, command=close).pack(anchor="e")
        dialog.bind("<Return>", lambda event: close())
        dialog.bind("<Escape>", lambda event: close())
        dialog.protocol("WM_DELETE_WINDOW", close)

        dialog.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width() - dialog.winfo_width()) // 2
        y = self.winfo_rooty() + (self.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{max(0, x)}+{max(0, y)}")
        dialog.grab_set()
        dialog.focus_force()
        self.wait_window(dialog)

    def _pick(self):
        path = filedialog.askopenfilename(
            filetypes=[("Images", "*.jpg *.jpeg *.png *.bmp *.webp")])
        if not path:
            return
        try:
            with Image.open(path) as source:
                image = ImageOps.exif_transpose(source)
                image.load()
        except Exception as exc:
            self._show_message("Error", f"Cannot open image:\n{exc}")
            return
        self.image_path = path
        image.thumbnail((500, 320))
        self._tkimg = ImageTk.PhotoImage(image)
        self.preview.config(image=self._tkimg, text="")
        self._replan()

    def _replan(self):
        if not self.image_path:
            return

        self.status_l.config(text="Analysing photo…")
        self.update_idletasks()
        try:
            strokes, dimensions = plan_drawing(
                self.image_path, self.style_v.get(), self.quality_v.get())
            self.strokes = strokes
            self.stroke_dim = dimensions

            preview = render_preview(strokes, *dimensions)
            self._tkimg = ImageTk.PhotoImage(preview)
            self.preview.config(image=self._tkimg, text="")

            total_points = sum(len(stroke[-1]) for stroke in strokes)
            self.info_l.config(
                text=f"{len(strokes)} strokes  •  {total_points:,} points  "
                f"•  {dimensions[0]}×{dimensions[1]} px")
            self.status_l.config(text="Ready — click Start Drawing.")
        except Exception as exc:
            self.status_l.config(text=f"Error: {exc}")

    def _start(self):
        if not self.image_path:
            self._show_message("No image", "Upload a photo first.", "warning")
            return
        if not self.strokes:
            self._replan()
            if not self.strokes:
                return

        prompt = (
            "The robot will open Paint and draw an approximate pencil "
            "sketch with mouse strokes.\n\n"
            "Press ESC at any time to stop. Press SPACE to pause or "
            "resume."
        )
        if not self._ask_yes_no("Start", prompt):
            return

        config = dict(
            strokes=self.strokes,
            dim=self.stroke_dim,
            speed=self.speed_v.get(),
        )
        width, height = self.stroke_dim
        preview_scale = min(500 / width, 320 / height, 1.0)
        blank = Image.new(
            "RGB",
            (max(1, int(width * preview_scale)),
             max(1, int(height * preview_scale))),
            "white",
        )
        self._tkimg = ImageTk.PhotoImage(blank)
        self.preview.config(image=self._tkimg, text="")
        self.stage_l.config(text="Stage: Preparing…")
        self.eta_l.config(text="Remaining: calculating…")
        self.status_l.config(
            text="Drawing strokes live in Paint and updating the preview.")
        self.robot = Robot(config, self.q)
        self.robot.start()
        self.b_start.config(state="disabled")
        self.b_pause.config(state="normal")
        self.b_stop.config(state="normal")
        self.bar["value"] = 0

    def _pause(self):
        if self.robot and self.robot.is_alive():
            self.robot.pause()
            self.b_pause.config(state="disabled")
            self.b_resume.config(state="normal")
            self.status_l.config(
                text="Paused. Press Resume or SPACE to continue.")

    def _resume(self):
        if self.robot and self.robot.is_alive():
            if (self.robot.paint_hwnd
                    and not focus_paint(self.robot.paint_hwnd)):
                self._show_message(
                    "Paint not focused",
                    "Could not return to Paint. Bring it to the foreground "
                    "and try Resume again.",
                )
                return
            self.robot.resume()
            self.b_pause.config(state="normal")
            self.b_resume.config(state="disabled")
            self.status_l.config(text="Resumed.")

    def _stop(self):
        if self.robot and self.robot.is_alive():
            self.robot.stop()
            self.status_l.config(text="Stopping…")
            self.b_stop.config(state="disabled")

    def _finish(self):
        self.b_start.config(state="normal")
        for button in (self.b_pause, self.b_resume, self.b_stop):
            button.config(state="disabled")

    def _poll(self):
        try:
            while True:
                message = self.q.get_nowait()
                kind = message[0]
                if kind in ("status", "paused", "resumed"):
                    self.status_l.config(text=message[1])
                    if kind == "paused":
                        self.b_pause.config(state="disabled")
                        self.b_resume.config(state="normal")
                    elif kind == "resumed":
                        self.b_pause.config(state="normal")
                        self.b_resume.config(state="disabled")
                elif kind == "stage":
                    self.stage_l.config(text=f"Stage: {message[1]}")
                elif kind == "progress":
                    self.bar["value"] = message[1]
                    seconds = int(message[2])
                    self.eta_l.config(
                        text=f"Remaining: {seconds // 3600}h "
                        f"{seconds % 3600 // 60}m {seconds % 60}s")
                    if len(message) > 3:
                        self._tkimg = ImageTk.PhotoImage(
                            Image.fromarray(message[3]))
                        self.preview.config(image=self._tkimg, text="")
                elif kind == "done":
                    self.status_l.config(text=message[1])
                    self._finish()
                elif kind == "error":
                    self.status_l.config(text=f"Error: {message[1]}")
                    self._finish()
                    self._show_message("Error", message[1])
        except queue.Empty:
            pass
        self.after(80, self._poll)

    def _on_close(self):
        if self.robot and self.robot.is_alive():
            if self._closing:
                return
            self._closing = True
            self.robot.stop()
            self.after(100, self._wait_close)
            return
        self.destroy()

    def _wait_close(self):
        if self.robot and self.robot.is_alive():
            self.after(100, self._wait_close)
        else:
            self.destroy()
