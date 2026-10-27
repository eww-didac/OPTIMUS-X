"""Optimus X application shell.

The window is drawn borderless and then re-styled with native Win32 frame
flags, which keeps resizing, snapping, minimize/maximize and taskbar grouping
working while still allowing a fully custom title bar.
"""

from __future__ import annotations

import re
import tkinter as tk
from concurrent.futures import Future, ThreadPoolExecutor
from queue import Empty, Queue
from typing import Callable, TypeVar

import customtkinter as ctk

from . import i18n, theme
from .core import admin as admin_helpers
from .core import catalog
from .core import metrics as metrics_module
from .core.executor import executor
from .core.store import store
from .ui.assets import ensure_icon
from .ui.chrome import StatusBar, TitleBar
from .ui.dialogs import ConfirmDialog
from .ui.flows import apply_tweak_batch
from .ui.pages.cleaner import DeepCleanerPage
from .ui.pages.dashboard import DashboardPage
from .ui.pages.gameboost import GameBoostPage
from .ui.pages.settings import SettingsPage
from .ui.pages.toolbox import ToolboxPage
from .ui.pages.tweaks import TweaksPage
from .ui.sidebar import Sidebar
from .ui.toasts import ToastManager
from .ui.win32 import center_window, make_borderless, set_app_id

T = TypeVar("T")


PROFILE_COPY: dict[str, dict] = {
    "normal": {
        "confirm_title": "Run normal optimization?",
        "message": (
            "Optimus X will apply the recommended, reversible performance profile: "
            "background services, telemetry, kernel responsiveness, input latency, "
            "network throttling and privacy. Existing values are backed up first."
        ),
        "confirm_text": "Optimize now",
        "task_title": "Normal optimization",
        "profile_name": "Normal profile",
        "admin_message": "The normal profile changes Windows services and system registry values.",
        "warnings": [],
        "risk": "advanced",
        "idle_label": "Normal optimization",
        "running_label": "Optimizing…",
        "success_label": "Optimized",
        "already": "The normal profile is already applied.",
    },
    "extreme": {
        "confirm_title": "Run extreme optimization?",
        "message": (
            "Extreme mode applies every reversible tweak in the catalog, including "
            "advanced changes such as Windows Update manual mode, print spooler, Xbox "
            "services, visual effects and hardware GPU scheduling. Every value is "
            "backed up and can be restored from Settings."
        ),
        "confirm_text": "Apply extreme",
        "task_title": "Extreme optimization",
        "profile_name": "Extreme profile",
        "admin_message": "The extreme profile changes Windows services, registry values and system policies.",
        "warnings": [
            "Extreme mode disables automatic Windows updates and printing until reverted.",
            "Conflicting hardware-scheduling alternatives are skipped; the modern option is used.",
        ],
        "risk": "extreme",
        "idle_label": "Extreme optimization",
        "running_label": "Optimizing…",
        "success_label": "Optimized",
        "already": "The extreme profile is already applied.",
    },
}


class OptimusXApp(ctk.CTk):
    PAGE_CLASSES = {
        "Dashboard": DashboardPage,
        "Tweaks & Privacy": TweaksPage,
        "Deep Cleaner": DeepCleanerPage,
        "Game Boost": GameBoostPage,
        "Toolbox": ToolboxPage,
        "Settings": SettingsPage,
    }

    def __init__(self) -> None:
        # Load the saved language before any widget is built: every label is
        # translated at construction time, so this must happen first.
        i18n.set_language(str(store.get("language") or "en"))
        ctk.set_appearance_mode("dark")
        super().__init__()
        set_app_id("OptimusX.SystemOptimizer.2")
        self.withdraw()

        self.is_admin = admin_helpers.is_admin()
        self._pages: dict[str, ctk.CTkFrame] = {}
        self._current: tk.Misc | None = None
        self._closing = False
        self._admin_prompt_open = False
        self._optimize_busy = False
        self._startup_geometry = ""
        self._chrome_delta: tuple[int, int] = (0, 0)
        self._chrome_measured = False
        self._background_pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="optimus-ui")
        self._background_results: Queue[
            tuple[Future, Callable, Callable[[Exception], None] | None]
        ] = Queue()
        self._preload_job: str | None = None
        self._preload_target: str | None = None

        self.title("Optimus X — System Optimizer")
        self.configure(fg_color=theme.Color.BG)
        self.minsize(1120, 720)
        self._apply_geometry()
        self._build_shell()
        self._set_icon()
        self.refresh_sidebar_identity()
        self.show_page("Dashboard")

        metrics_module.metrics.start()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(60, self._reveal)
        self.after(900, self._tick_status)
        self.after(40, self._poll_background)
        # The tweak list is the most expensive page to build.  Prepare it while
        # the user is still looking at the dashboard so the first click is an
        # instant swap instead of a visible build-up.
        self.after(450, lambda: self.preload_page("Tweaks & Privacy"))

    # -------------------------------------------------------------------- shell
    def _apply_geometry(self) -> None:
        saved = store.get("window_geometry")
        if isinstance(saved, str):
            match = re.match(r"^(\d+)x(\d+)\+(-?\d+)\+(-?\d+)$", saved.strip())
            if match:
                width, height, x, y = (int(value) for value in match.groups())
                screen_w = self.winfo_screenwidth()
                screen_h = self.winfo_screenheight()
                if (
                    width >= 1120
                    and height >= 720
                    and width <= 1420
                    and height <= 780
                    and -40 <= x <= screen_w - 220
                    and 0 <= y <= screen_h - 160
                ):
                    self._startup_geometry = f"{width}x{height}+{x}+{y}"
                    self.geometry(self._startup_geometry)
                    return
        self._startup_geometry = center_window(self, 1280, 720)

    def _build_shell(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.titlebar = TitleBar(self, on_close=self._on_close)
        self.titlebar.grid(row=0, column=0, sticky="ew")

        main = ctk.CTkFrame(self, fg_color=theme.Color.CONTENT, corner_radius=0)
        main.grid(row=1, column=0, sticky="nsew")
        main.grid_rowconfigure(0, weight=1)
        main.grid_columnconfigure(1, weight=1)

        self.sidebar = Sidebar(main, self.show_page, on_prefetch=self.preload_page)
        self.sidebar.grid(row=0, column=0, sticky="ns")

        self.page_host = ctk.CTkFrame(main, fg_color=theme.Color.CONTENT, corner_radius=0)
        self.page_host.grid(row=0, column=1, sticky="nsew")
        self.page_host.grid_rowconfigure(0, weight=1)
        self.page_host.grid_columnconfigure(0, weight=1)

        self.statusbar = StatusBar(self)
        self.statusbar.grid(row=2, column=0, sticky="ew")

        self.toasts = ToastManager(self)

    def _set_icon(self) -> None:
        try:
            icon = ensure_icon()
            self.iconbitmap(str(icon))
        except Exception:
            pass

    def _reveal(self) -> None:
        try:
            requested = self._startup_geometry or self.geometry()
            self.deiconify()
            self.update_idletasks()
            make_borderless(self, border_color=theme.Color.BORDER)
            if not self._chrome_measured:
                self.update_idletasks()
                self._chrome_delta = self._geometry_delta(requested, self.geometry())
                self._chrome_measured = True
            self.lift()
            self.focus_force()
            self.after(280, lambda: make_borderless(self, border_color=theme.Color.BORDER))
        except Exception:
            pass

    @staticmethod
    def _geometry_delta(before: str, after: str) -> tuple[int, int]:
        pattern = r"^(\d+)x(\d+)"
        first = re.match(pattern, (before or "").strip())
        second = re.match(pattern, (after or "").strip())
        if not first or not second:
            return (0, 0)
        return (
            int(second.group(1)) - int(first.group(1)),
            int(second.group(2)) - int(first.group(2)),
        )

    # --------------------------------------------------------------- navigation
    def show_page(self, name: str) -> None:
        if self._closing or name not in self.PAGE_CLASSES:
            return
        page = self._pages.get(name)
        if page is None:
            page = self._create_page(name)
            if page is None:
                return
        if page is not self._current:
            self._present_page(page)
        self.sidebar.set_active(name)
        self.titlebar.set_page(name)
        handler = getattr(page, "on_show", None)
        if callable(handler):
            try:
                handler()
            except Exception as exc:
                self.notify(i18n.tr("{name}: {error}", name=i18n.tr(name), error=exc), "warning")

    def _create_page(self, name: str) -> ctk.CTkFrame | None:
        """Build a page off-screen and cache it for an instant later swap."""

        factory = self.PAGE_CLASSES.get(name)
        if factory is None:
            return None
        try:
            page = factory(self.page_host, self)
        except Exception as exc:
            self.notify(
                i18n.tr(
                    "Could not open {name}: {error}", name=i18n.tr(name), error=exc
                ),
                "error",
            )
            return None
        page.grid(row=0, column=0, sticky="nsew", padx=22, pady=(16, 12))
        # Keep it built but unmapped until the user asks for it.  Creating the
        # whole widget tree here means the first navigation does not paint a
        # partially constructed page.
        page.grid_remove()
        self._pages[name] = page
        # Give async content a moment to land, then resolve the page geometry
        # while it is still hidden.  Otherwise Tk would do that expensive
        # CustomTkinter resize pass on the first click.
        self.after(700, lambda target=page: self.warm_page(target))
        return page

    def warm_page(self, page: ctk.CTkFrame) -> None:
        """Lay out a hidden page behind the active one.

        Tk only computes real child geometry once a widget is mapped.  Mapping
        the page underneath the current page (with a solid, invisible cover
        between them) performs that work during idle time, so the later switch
        is just a raise instead of a 100+ ms layout burst.
        """

        if self._closing or self._current is None or page is self._current:
            return
        try:
            if not page.winfo_exists():
                return
        except Exception:
            return
        revision = int(getattr(page, "_layout_revision", 0))
        if int(getattr(page, "_warmed_revision", -1)) == revision:
            return
        cover: tk.Frame | None = None
        try:
            page.grid()
            page.lower()
            cover = tk.Frame(self.page_host, bg=theme.Color.CONTENT)
            cover.grid(
                row=0, column=0, sticky="nsew", padx=22, pady=(16, 12)
            )
            self._current.tkraise()
            self.update_idletasks()
            page._warmed_revision = revision
        except Exception:
            pass
        finally:
            if cover is not None:
                try:
                    cover.destroy()
                except Exception:
                    pass
            try:
                page.grid_remove()
            except Exception:
                pass

    def _present_page(self, page: ctk.CTkFrame) -> None:
        previous = self._current
        self._current = page
        if previous is not None and previous is not page:
            previous.grid_remove()
        page.grid()
        page.tkraise()
        try:
            # Resolve the complete layout before returning to the event loop,
            # so the switch lands as one finished frame.
            self.update_idletasks()
        except Exception:
            pass

    def preload_page(self, name: str) -> None:
        """Warm a page shortly after the pointer indicates intent to open it."""

        if self._closing or name in self._pages or name not in self.PAGE_CLASSES:
            return
        if self._preload_job is not None:
            try:
                self.after_cancel(self._preload_job)
            except Exception:
                pass
        self._preload_target = name
        self._preload_job = self.after(70, self._run_preload)

    def _run_preload(self) -> None:
        self._preload_job = None
        name = self._preload_target
        self._preload_target = None
        if self._closing or not name or name in self._pages:
            return
        self._create_page(name)

    def _cancel_preload(self) -> None:
        if self._preload_job is not None:
            try:
                self.after_cancel(self._preload_job)
            except Exception:
                pass
            self._preload_job = None
        self._preload_target = None

    # ------------------------------------------------------------------- refresh
    def refresh_dashboard(self) -> None:
        page = self._pages.get("Dashboard")
        if page is not None:
            try:
                page.refresh_profile()
            except Exception as exc:
                self.notify(
                    i18n.tr("Could not refresh dashboard: {error}", error=exc), "error"
                )

    def run_background(
        self,
        task: Callable[[], T],
        on_success: Callable[[T], None],
        on_error: Callable[[Exception], None] | None = None,
    ) -> None:
        future = self._background_pool.submit(task)
        future.add_done_callback(
            lambda completed: self._background_results.put(
                (completed, on_success, on_error)
            )
        )

    def _poll_background(self) -> None:
        if self._closing:
            return
        while True:
            try:
                future, on_success, on_error = self._background_results.get_nowait()
            except Empty:
                break
            try:
                result = future.result()
            except Exception as exc:
                if on_error is not None:
                    on_error(exc)
                else:
                    self.notify(
                        i18n.tr("Background task failed: {error}", error=exc), "error"
                    )
            else:
                on_success(result)
        self.after(40, self._poll_background)

    def refresh_sidebar_identity(self) -> None:
        try:
            self.sidebar.set_identity(
                admin=self.is_admin,
                dry_run=bool(store.get("dry_run", False)),
            )
        except Exception:
            pass
        try:
            self.statusbar.update_state(metrics_module.metrics.latest, self.is_admin)
        except Exception:
            pass

    def notify(self, message: str, kind: str = "info") -> None:
        try:
            self.toasts.show(message, kind)
        except Exception:
            pass

    # ------------------------------------------------------------------ language
    def current_page_name(self) -> str:
        for name, page in self._pages.items():
            if page is self._current:
                return name
        return "Dashboard"

    def set_language(self, language: str) -> None:
        """Switch the interface language and rebuild the cached pages.

        Every page translates its labels while it is constructed, so the
        cleanest and most reliable switch is to discard the hidden cache and
        build it again.  The rebuild is deferred one event-loop turn so the
        Settings callback that triggered it can return before its own page is
        destroyed.
        """

        code = i18n.set_language(language)
        if code == str(store.get("language") or "en"):
            return
        store.set("language", code)
        # Chrome is cheap to repaint immediately.
        try:
            self.sidebar.refresh_language()
            self.titlebar.set_page(self.current_page_name())
            self.statusbar.refresh_language()
        except Exception:
            pass
        self.after(20, self._rebuild_pages_for_language)

    def _rebuild_pages_for_language(self) -> None:
        if self._closing:
            return
        name = self.current_page_name()
        self._cancel_preload()
        for page in list(self._pages.values()):
            try:
                page.destroy()
            except Exception:
                pass
        self._pages.clear()
        self._current = None
        self.show_page(name)
        # Re-warm the heaviest page after the switch so navigation stays instant.
        self.after(250, lambda: self.preload_page("Tweaks & Privacy"))

    # -------------------------------------------------------------------- admin
    def prompt_admin(self, message: str) -> None:
        if self.is_admin:
            return
        if self._admin_prompt_open:
            return
        self._admin_prompt_open = True

        def done(accepted: bool, _checked: bool) -> None:
            self._admin_prompt_open = False
            if accepted:
                self.relaunch_elevated()

        ConfirmDialog(
            self,
            title=i18n.tr("Administrator rights required"),
            message=(
                message
                + i18n.tr(
                    "\n\nRestart Optimus X as administrator? Windows will show a UAC prompt."
                )
            ),
            confirm_text=i18n.tr("Restart as admin"),
            cancel_text=i18n.tr("Not now"),
            risk="advanced",
            height=300,
            on_result=done,
        )

    def relaunch_elevated(self) -> None:
        if admin_helpers.relaunch_as_admin():
            self.notify(
                i18n.tr("Administrator launch requested. Closing this window…"), "info"
            )
            self.after(650, self._close_for_elevation)
        else:
            self.notify(
                i18n.tr("Elevation was cancelled or unavailable."), "warning"
            )

    def _close_for_elevation(self) -> None:
        if self._closing:
            return
        self._closing = True
        self._save_geometry()
        self._cancel_preload()
        metrics_module.metrics.stop()
        self._background_pool.shutdown(wait=False)
        self.destroy()

    # ------------------------------------------------------------ quick optimize
    def quick_optimize(self) -> None:
        self.optimize_profile("normal")

    def quick_optimize_extreme(self) -> None:
        self.optimize_profile("extreme")

    def optimize_profile(self, mode: str = "normal") -> None:
        if mode not in PROFILE_COPY or self._optimize_busy or self._closing:
            return
        meta = PROFILE_COPY[mode]
        dashboard = self._pages.get("Dashboard")

        pending = [
            tweak for tweak in catalog.profile_tweaks(mode) if not executor.is_applied(tweak)
        ]
        if not pending:
            self.notify(meta["already"], "success")
            if dashboard is not None:
                dashboard.set_optimize_state("success", meta["success_label"], mode)
                self.after(
                    3200,
                    lambda: dashboard.set_optimize_state("idle", meta["idle_label"], mode)
                    if dashboard.winfo_exists()
                    else None,
                )
            return

        def started() -> None:
            self._optimize_busy = True
            if dashboard is not None:
                dashboard.set_optimize_state("running", meta["running_label"], mode)

        def finished(result: dict) -> None:
            self._optimize_busy = False
            failed = int(result.get("failed") or 0)
            dry = bool(result.get("dry_run"))
            if dashboard is None:
                return
            if not failed and not dry:
                dashboard.set_optimize_state("success", meta["success_label"], mode)
                self.after(
                    4400,
                    lambda: dashboard.set_optimize_state("idle", meta["idle_label"], mode)
                    if dashboard.winfo_exists()
                    else None,
                )
            else:
                dashboard.set_optimize_state("idle", meta["idle_label"], mode)

        apply_tweak_batch(
            self,
            pending,
            [],
            title=i18n.tr(meta["confirm_title"]),
            message=i18n.tr(meta["message"]),
            confirm_text=i18n.tr(meta["confirm_text"]),
            admin_message=i18n.tr(meta["admin_message"]),
            task_title=i18n.tr(meta["task_title"]),
            profile_name=i18n.tr(meta["profile_name"]),
            extra_warnings=[i18n.tr(text) for text in meta["warnings"]],
            risk=meta["risk"],
            on_start=started,
            on_done=finished,
        )

    # ---------------------------------------------------------------------- loop
    def _tick_status(self) -> None:
        if self._closing:
            return
        try:
            self.statusbar.update_state(metrics_module.metrics.latest, self.is_admin)
        except Exception:
            pass
        self.after(2000, self._tick_status)

    # --------------------------------------------------------------------- close
    def _save_geometry(self) -> None:
        try:
            if not self.winfo_exists():
                return
            if self.titlebar.maximized and self.titlebar.restore_geometry:
                geometry = self.titlebar.restore_geometry
            else:
                geometry = self.geometry()
            match = re.match(r"^(\d+)x(\d+)([+-]\d+)([+-]\d+)$", (geometry or "").strip())
            if match:
                # Saved geometry is applied before the caption is stripped, so
                # remove the measured chrome delta and never store below the
                # effective minimum.
                width = max(1120, int(match.group(1)) - self._chrome_delta[0])
                height = max(720, int(match.group(2)) - self._chrome_delta[1])
                geometry = f"{width}x{height}{match.group(3)}{match.group(4)}"
            store.set("window_geometry", geometry)
        except Exception:
            pass

    def _on_close(self) -> None:
        if self._closing:
            return
        self._closing = True
        self._save_geometry()
        self._cancel_preload()
        metrics_module.metrics.stop()
        self._background_pool.shutdown(wait=False)
        self.destroy()
