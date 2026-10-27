"""Dark, borderless modal dialogs for confirmations and live task output."""

from __future__ import annotations

import queue
import threading
import time
import tkinter as tk
from typing import Callable

import customtkinter as ctk

from .. import i18n, theme
from .controls import IconButton, RiskPill
from .draw import round_rect
from .icons import draw_icon
from .win32 import center_window, make_dialog_borderless, make_draggable


class BaseDialog(ctk.CTkToplevel):
    def __init__(
        self,
        parent: tk.Misc,
        title: str,
        subtitle: str = "",
        *,
        width: int = 580,
        height: int = 360,
        accent: str = theme.Color.CYAN,
    ) -> None:
        super().__init__(parent)
        self.withdraw()
        # CustomTkinter re-applies the native titlebar colour shortly after
        # creation (and again from resizable()), which would withdraw this
        # borderless dialog *after* it is shown.  Dialogs draw their own chrome,
        # so disable that native manipulation for this window.
        if hasattr(self, "_deactivate_windows_window_header_manipulation"):
            self._deactivate_windows_window_header_manipulation = True
        self.parent_window = parent
        self._accent = accent
        self._allow_close = True
        self._width = width
        self._height = height
        self.title(title)
        self.configure(fg_color=theme.Color.BG)
        self.resizable(False, False)
        self.transient(parent)

        self.shell = ctk.CTkFrame(
            self,
            fg_color=theme.Color.SHELL,
            corner_radius=14,
            border_width=1,
            border_color=theme.Color.BORDER_STRONG,
        )
        self.shell.pack(fill="both", expand=True, padx=1, pady=1)
        self.shell.grid_columnconfigure(0, weight=1)
        self.shell.grid_rowconfigure(2, weight=1)

        header = ctk.CTkFrame(self.shell, fg_color="transparent", height=54)
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=(14, 0))
        header.grid_columnconfigure(0, weight=1)
        title_label = ctk.CTkLabel(
            header, text=i18n.tr(title), text_color=theme.Color.TEXT,
            font=theme.display(16, "bold"), anchor="w",
        )
        title_label.grid(row=0, column=0, sticky="w")
        subtitle_label = ctk.CTkLabel(
            header, text=i18n.tr(subtitle), text_color=theme.Color.MUTED,
            font=theme.font(9), anchor="w",
        )
        subtitle_label.grid(row=1, column=0, sticky="w", pady=(1, 0))
        make_draggable(self, header, title_label, subtitle_label)
        self.close_button = tk.Canvas(
            header, width=30, height=30, bg=theme.Color.SHELL,
            highlightthickness=0, bd=0, cursor="hand2",
        )
        self.close_button.grid(row=0, column=1, rowspan=2, sticky="e")
        draw_icon(self.close_button, "close", 15, 15, 15, theme.Color.MUTED, 1.5)
        self.close_button.bind("<Button-1>", lambda _e: self._request_close())
        self.close_button.bind("<Enter>", lambda _e: draw_icon(self.close_button, "close", 15, 15, 15, theme.Color.RED, 1.6))
        self.close_button.bind("<Leave>", lambda _e: (
            self.close_button.delete("all"),
            draw_icon(self.close_button, "close", 15, 15, 15, theme.Color.MUTED, 1.5),
        ))

        self.body = ctk.CTkFrame(self.shell, fg_color="transparent")
        self.body.grid(row=2, column=0, sticky="nsew", padx=20, pady=(8, 0))
        self.body.grid_columnconfigure(0, weight=1)

        self.footer = ctk.CTkFrame(self.shell, fg_color="transparent", height=56)
        self.footer.grid(row=3, column=0, sticky="ew", padx=20, pady=(8, 16))
        self.footer.grid_columnconfigure(0, weight=1)

        self.bind("<Escape>", lambda _e: self._request_close())
        self.protocol("WM_DELETE_WINDOW", self._request_close)
        center_window(self, width, height, parent=parent)
        self.after(20, self._finalize)

    def _finalize(self) -> None:
        if not self.winfo_exists():
            return
        self.deiconify()
        make_dialog_borderless(self, border_color=theme.Color.BORDER_STRONG)
        self.lift()
        self.attributes("-topmost", True)
        self.after(120, lambda: self.attributes("-topmost", False))
        try:
            self.grab_set()
            self.focus_force()
        except Exception:
            pass

    def _request_close(self) -> None:
        if self._allow_close:
            self.destroy()


class ConfirmDialog(BaseDialog):
    def __init__(
        self,
        parent: tk.Misc,
        *,
        title: str,
        message: str,
        confirm_text: str = "Confirm",
        cancel_text: str = "Cancel",
        items: list[str] | None = None,
        warnings: list[str] | None = None,
        risk: str = "safe",
        checkbox_text: str | None = None,
        checkbox_default: bool = True,
        require_checkbox: bool = False,
        accent: str | None = None,
        height: int = 430,
        on_result: Callable[[bool, bool], None],
    ) -> None:
        color, _bg = theme.risk_palette(risk)
        if accent:
            color = accent
        super().__init__(
            parent, title, "Review the changes before continuing.",
            width=590, height=height, accent=color,
        )
        self._on_result = on_result
        self._checkbox_text = checkbox_text
        self._checkbox = ctk.BooleanVar(value=checkbox_default)
        self.body.grid_rowconfigure(2, weight=1)

        top = ctk.CTkFrame(self.body, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew")
        top.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            top, text=i18n.tr("REVIEW CHANGES"), text_color=theme.Color.CYAN_DIM,
            font=theme.font(8, "bold"), anchor="w",
        ).grid(row=0, column=0, sticky="w")
        RiskPill(top, theme.risk_label(risk), color, "#101b27").grid(row=0, column=1, sticky="e", padx=(12, 0))

        ctk.CTkLabel(
            self.body, text=i18n.tr(message), text_color=theme.Color.TEXT_SOFT,
            font=theme.font(10), anchor="w", justify="left", wraplength=520,
        ).grid(row=1, column=0, sticky="ew", pady=(12, 8))

        if items:
            box = ctk.CTkFrame(
                self.body, fg_color=theme.Color.CARD_ALT,
                border_width=1, border_color=theme.Color.BORDER,
                corner_radius=10,
            )
            box.grid(row=2, column=0, sticky="nsew", pady=(2, 8))
            box.grid_columnconfigure(0, weight=1)
            box.grid_rowconfigure(0, weight=1)
            text = ctk.CTkTextbox(
                box, height=118, fg_color="transparent", text_color=theme.Color.TEXT_SOFT,
                font=theme.font(9), border_width=0, corner_radius=10, wrap="word",
                scrollbar_button_color=theme.Color.BORDER_STRONG,
                scrollbar_button_hover_color=theme.Color.CYAN_DIM,
            )
            text.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
            text.insert("1.0", "\n".join(f"•  {item}" for item in items))
            text.configure(state="disabled")
        else:
            spacer = ctk.CTkFrame(self.body, fg_color="transparent", height=80)
            spacer.grid(row=2, column=0, sticky="nsew")

        if warnings:
            warn = ctk.CTkFrame(
                self.body, fg_color=theme.Color.AMBER_DIM,
                border_width=1, border_color="#5b4518", corner_radius=9,
            )
            warn.grid(row=3, column=0, sticky="ew", pady=(2, 6))
            ctk.CTkLabel(
                warn, text="⚠   " + "\n⚠   ".join(i18n.tr(item) for item in warnings),
                text_color="#f3cc7c", font=theme.font(9),
                anchor="w", justify="left", wraplength=500,
            ).pack(padx=12, pady=8, anchor="w")
            self.body.grid_rowconfigure(3, weight=0)

        if checkbox_text:
            self.checkbox = ctk.CTkCheckBox(
                self.body, text=i18n.tr(checkbox_text), variable=self._checkbox,
                font=theme.font(9), text_color=theme.Color.MUTED,
                fg_color=color, hover_color=color, border_color=theme.Color.BORDER_STRONG,
                checkmark_color=theme.Color.BG, corner_radius=4, border_width=1.5,
                checkbox_width=17, checkbox_height=17,
            )
            self.checkbox.grid(row=4, column=0, sticky="w", pady=(8, 0))
            if require_checkbox:
                self.checkbox.configure(command=self._checkbox_changed)
        self._color = color
        self._require_checkbox = require_checkbox

        self.cancel_btn = IconButton(
            self.footer, text=cancel_text, command=lambda: self._finish(False),
            width=96, height=34,
        )
        self.cancel_btn.grid(row=0, column=1, padx=(8, 0))
        self._confirm_btn = IconButton(
            self.footer, text=confirm_text, command=lambda: self._finish(True),
            accent=True, width=142, height=34,
        )
        self._confirm_btn.configure(
            fg_color=self._color, hover_color=self._color,
            text_color=theme.Color.BG,
            border_color=self._color,
        )
        self._confirm_btn.grid(row=0, column=2, padx=(8, 0))
        if require_checkbox and checkbox_text:
            self._confirm_btn.configure(state="disabled")

    def _checkbox_changed(self) -> None:
        state = "normal" if self._checkbox.get() else "disabled"
        self._confirm_btn.configure(state=state)

    def _request_close(self) -> None:
        self._finish(False)

    def _finish(self, accepted: bool) -> None:
        checked = bool(self._checkbox.get()) if self._checkbox_text else False
        self._allow_close = True
        self.destroy()
        self._on_result(accepted, checked)


class TaskDialog(BaseDialog):
    def __init__(
        self,
        parent: tk.Misc,
        *,
        title: str,
        subtitle: str,
        worker: Callable[[Callable[[str], None], threading.Event], dict],
        on_done: Callable[[dict], None] | None = None,
        on_close: Callable[[], None] | None = None,
        accent: str = theme.Color.CYAN,
        width: int = 720,
        height: int = 520,
    ) -> None:
        super().__init__(
            parent, title, subtitle, width=width, height=height, accent=accent
        )
        self._worker = worker
        self._on_done = on_done
        self._on_close = on_close
        self._cancel = threading.Event()
        self._queue: queue.Queue[tuple[str, object]] = queue.Queue()
        self._running = True
        self._result: dict = {}
        self._started = time.time()
        self._allow_close = False

        self.body.grid_rowconfigure(1, weight=1)
        top = ctk.CTkFrame(self.body, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew")
        top.grid_columnconfigure(0, weight=1)
        status_row = ctk.CTkFrame(top, fg_color="transparent")
        status_row.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        status_row.grid_columnconfigure(0, weight=1)
        self.status_label = ctk.CTkLabel(
            status_row, text=i18n.tr("Starting…"), text_color=theme.Color.CYAN,
            font=theme.font(10, "bold"), anchor="w",
        )
        self.status_label.grid(row=0, column=0, sticky="w")
        self.elapsed_label = ctk.CTkLabel(
            status_row, text="0s", text_color=theme.Color.DIM,
            font=theme.font(9), anchor="e",
        )
        self.elapsed_label.grid(row=0, column=1, sticky="e")

        self.progress = ctk.CTkProgressBar(
            top, height=4, corner_radius=2,
            fg_color=theme.Color.BORDER, progress_color=theme.Color.CYAN,
            mode="indeterminate",
        )
        self.progress.grid(row=1, column=0, sticky="ew")

        self.output = ctk.CTkTextbox(
            self.body, fg_color=theme.Color.CARD_ALT,
            text_color="#a8c6d4", font=("Consolas", 9),
            border_width=1, border_color=theme.Color.BORDER,
            corner_radius=10, wrap="word",
            scrollbar_button_color=theme.Color.BORDER_STRONG,
            scrollbar_button_hover_color=theme.Color.CYAN_DIM,
        )
        self.output.grid(row=1, column=0, sticky="nsew", pady=(10, 0))
        self.output.configure(state="disabled")

        self.cancel_btn = IconButton(
            self.footer, text="Cancel", command=self._cancel_task, width=96, height=34,
        )
        self.cancel_btn.grid(row=0, column=1, padx=(8, 0))
        self.close_btn = IconButton(
            self.footer, text="Close", command=self._close, accent=True, width=96, height=34,
        )
        self.close_btn.grid(row=0, column=1, padx=(8, 0))
        self.close_btn.grid_remove()

        self._append(i18n.tr("Preparing task…"))
        self.after(150, self._start)
        self.after(250, self._poll)

    def _start(self) -> None:
        self.status_label.configure(text=i18n.tr("Running…"), text_color=theme.Color.CYAN)
        self.progress.start()

        def emit(text: str) -> None:
            self._queue.put(("line", text))

        def run() -> None:
            try:
                result = self._worker(emit, self._cancel)
                if not isinstance(result, dict):
                    result = {"success": bool(result)}
                self._queue.put(("done", result))
            except Exception as exc:
                self._queue.put(("error", f"{type(exc).__name__}: {exc}"))

        threading.Thread(target=run, name="optimus-task", daemon=True).start()

    def _poll(self) -> None:
        if not self.winfo_exists():
            return
        try:
            while True:
                kind, payload = self._queue.get_nowait()
                if kind == "line":
                    self._append(str(payload))
                elif kind == "done":
                    self._finish(dict(payload))
                    return
                elif kind == "error":
                    self._finish({"success": False, "error": str(payload)})
                    return
        except queue.Empty:
            pass
        self.elapsed_label.configure(text=f"{int(time.time() - self._started)}s")
        self.after(120, self._poll)

    def _append(self, text: str) -> None:
        self.output.configure(state="normal")
        self.output.insert("end", text + "\n")
        self.output.see("end")
        self.output.configure(state="disabled")

    def _finish(self, result: dict) -> None:
        self._running = False
        self._allow_close = True
        self._result = result
        self.progress.stop()
        failed = int(result.get("failed") or 0)
        explicit = result.get("success")
        success = explicit is not False and failed == 0
        if result.get("error"):
            success = False
        if success:
            self.status_label.configure(
                text=i18n.tr("Completed successfully"), text_color=theme.Color.GREEN
            )
            self.progress.configure(progress_color=theme.Color.GREEN)
        else:
            self.status_label.configure(
                text=i18n.tr("Completed with issues"), text_color=theme.Color.AMBER
            )
            self.progress.configure(progress_color=theme.Color.AMBER)
        self.cancel_btn.grid_remove()
        self.close_btn.grid()
        self._append("")
        self._append(
            i18n.tr("TASK COMPLETE" if success else "TASK COMPLETE WITH ISSUES")
        )
        self._result["success"] = success
        if self._on_done:
            try:
                self._on_done(self._result)
            except Exception:
                pass

    def _cancel_task(self) -> None:
        if self._running:
            self._cancel.set()
            self.cancel_btn.configure(
                state="disabled", text=i18n.tr("Cancelling…")
            )
            self.status_label.configure(
                text=i18n.tr("Cancelling…"), text_color=theme.Color.AMBER
            )

    def _close(self) -> None:
        if self._running:
            return
        self.destroy()
        if self._on_close:
            try:
                self._on_close()
            except Exception:
                pass

    def _request_close(self) -> None:
        if self._running:
            self._cancel_task()
            return
        self._close()


class InfoDialog(BaseDialog):
    def __init__(
        self,
        parent: tk.Misc,
        *,
        title: str,
        message: str,
        button_text: str = "Got it",
        accent: str = theme.Color.CYAN,
    ) -> None:
        super().__init__(parent, title, "", width=500, height=230, accent=accent)
        self.body.grid_rowconfigure(0, weight=1)
        ctk.CTkLabel(
            self.body, text=i18n.tr(message), text_color=theme.Color.TEXT_SOFT,
            font=theme.font(10), anchor="nw", justify="left", wraplength=440,
        ).grid(row=0, column=0, sticky="nw", pady=(4, 0))
        btn = IconButton(
            self.footer, text=button_text, command=self._close, accent=True, width=110, height=34,
        )
        btn.grid(row=0, column=2, sticky="e")

    def _close(self) -> None:
        self.destroy()
