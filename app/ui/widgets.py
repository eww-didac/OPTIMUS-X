"""Shared page containers."""

from __future__ import annotations

import sys
import tkinter as tk
import weakref
from typing import TYPE_CHECKING

import customtkinter as ctk

from .. import theme
from . import win32

if TYPE_CHECKING:
    from ..application import OptimusXApp


class PageBase(ctk.CTkFrame):
    def __init__(self, master: tk.Misc, app: "OptimusXApp") -> None:
        super().__init__(master, fg_color="transparent", corner_radius=0)
        self.app = app


class _VirtualRow:
    """One direct child of a virtualized scroll area.

    ``x``/``y``/``width`` are the geometry the row had in the normal grid
    layout; ``relx``/``relwidth`` are the same values as fractions of the
    content frame, so window resizes keep the column layout without another
    measuring pass.
    """

    __slots__ = ("widget", "y", "height", "requested", "natural", "relx", "relwidth")

    def __init__(
        self,
        widget: tk.Misc,
        y: int,
        height: int,
        requested: int,
        natural: bool,
        relx: float,
        relwidth: float,
    ) -> None:
        self.widget = widget
        self.y = y
        self.height = height
        self.requested = requested
        self.natural = natural
        self.relx = relx
        self.relwidth = relwidth


class SmoothScrollFrame(ctk.CTkScrollableFrame):
    """Scrollable frame with reliable, smooth, artifact-free scrolling.

    CustomTkinter binds each scrollable frame to the global ``<MouseWheel>``
    event, so the last frame created receives every event and pages built
    earlier silently stop scrolling.  This subclass keeps a registry and routes
    each wheel event to the frame under the pointer.  It also accumulates
    fractional deltas, so precision wheels and touchpads (which send values
    smaller than the usual 120) still move the page instead of rounding to 0.

    The content is virtualized: the embedded frame is kept exactly one viewport
    tall and every direct child is positioned with ``place`` at
    ``row_y - offset``.  Tk 9 repaints an entire moved window, so panning a
    3764 px content window costs ~11 ms per step and visibly tears; moving the
    rows inside a 600 px window costs ~0.1 ms and repaints only the viewport.
    The canvas pan is kept as a fallback for layouts where virtualization is
    not possible.
    """

    _instances: list[weakref.ReferenceType["SmoothScrollFrame"]] = []
    WHEEL_STEP = 0.42
    FRAME_MS = 16

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._wheel_remainder = 0.0
        self._offset = 0.0
        self._pending_offset: float | None = None
        self._flush_job: str | None = None
        self._bar_driven = False
        self._syncing = False

        # Virtualized layout state.
        self._virtual = False
        self._rows: list[_VirtualRow] = []
        self._row_by_name: dict[str, _VirtualRow] = {}
        self._bound_rows: set[str] = set()
        self._virtual_height = 0
        self._virtual_width = 0
        self._rows_placed = False
        self._last_offset = 0
        self._busy = False
        self._virtual_job: str | None = None
        self._retry_job: str | None = None
        self._retry_count = 0
        self._rebuild_pending = False
        self._measure_seen: tuple | None = None
        self._cooldown = False

        SmoothScrollFrame._instances.append(weakref.ref(self))

        # The canvas is only a viewport now; the scrollbar drives our pan.
        try:
            self._scrollbar.configure(command=self._scroll_command)
            # The canvas no longer scrolls itself, but Tk still reports its
            # full view through yscrollcommand, which would reset the thumb to
            # full length.  The pan owns the scrollbar now.
            self._parent_canvas.configure(yscrollcommand=lambda *_args: None)
        except Exception:
            pass
        # CTkScrollbar.set() -> _draw() -> Canvas.update_idletasks() forces a
        # synchronous repaint of the whole window on every scroll step, which
        # costs 12-16 ms and makes fast thumb drags tear.  Tk already repaints
        # at the end of the event loop, so the forced flush only adds latency.
        try:
            self._scrollbar._canvas.update_idletasks = lambda *args, **kwargs: None
        except Exception:
            pass
        try:
            self._scrollbar._canvas.bind("<ButtonRelease-1>", self._bar_released, add="+")
        except Exception:
            pass
        # CustomTkinter updates the canvas scrollregion on every <Configure>,
        # including pure position changes caused by panning.  The scrollregion
        # is unused now and that update re-triggers a full repaint, so drop the
        # binding and only react to real size changes.
        try:
            self.unbind("<Configure>")
        except Exception:
            pass
        self._content_size = (0, 0)
        try:
            self.bind("<Configure>", self._content_configured, add="+")
            self.bind("<Map>", self._queue_sync, add="+")
            self._parent_canvas.bind("<Configure>", self._queue_sync, add="+")
        except Exception:
            pass
        self.after_idle(self._refresh_scroll)
        # The viewport and the content are still settling when the page is
        # first gridded; a couple of deferred passes make sure the thumb gets
        # its real proportion even if the first idle ran too early.
        self.after(120, self._refresh_scroll)
        self.after(420, self._refresh_scroll)

        # CustomTkinter registers one global handler per instance with add=True,
        # so every existing frame reacts to every wheel event.  Replace those
        # handlers with a single dispatcher that only moves the frame under the
        # pointer.
        try:
            if sys.platform.startswith("win"):
                self.unbind_all("<MouseWheel>")
                self.bind_all("<MouseWheel>", SmoothScrollFrame._global_wheel)
            else:
                for sequence in ("<Button-4>", "<Button-5>"):
                    self.unbind_all(sequence)
                    self.bind_all(sequence, SmoothScrollFrame._global_wheel)
        except Exception:
            pass

    # ----------------------------------------------------------------- routing
    @classmethod
    def _live_instances(cls) -> list["SmoothScrollFrame"]:
        alive: list[weakref.ReferenceType["SmoothScrollFrame"]] = []
        frames: list[SmoothScrollFrame] = []
        for reference in cls._instances:
            frame = reference()
            if frame is not None and frame.winfo_exists():
                alive.append(reference)
                frames.append(frame)
        cls._instances = alive
        return frames

    @classmethod
    def _frame_for(cls, widget: tk.Misc | None) -> "SmoothScrollFrame | None":
        if widget is None:
            return None
        node: tk.Misc | None = widget
        visited: set[int] = set()
        while node is not None and id(node) not in visited:
            visited.add(id(node))
            for frame in cls._live_instances():
                # The scrollbar is a sibling of the viewport: letting it match
                # the parent frame would scroll twice per wheel event.
                if node is frame or node is frame._parent_canvas:  # type: ignore[attr-defined]
                    return frame
            node = getattr(node, "master", None)
        return None

    def _mouse_wheel_all(self, event: tk.Event) -> None:
        # CustomTkinter binds this method during __init__; the binding is
        # replaced by _global_wheel afterwards, but keep it functional as a
        # fallback on unusual Tk builds.
        SmoothScrollFrame._global_wheel(event)

    @classmethod
    def _global_wheel(cls, event: tk.Event) -> None:
        target = cls._frame_for(getattr(event, "widget", None))
        if target is None:
            try:
                widget = getattr(event, "widget", None)
                root = widget.winfo_toplevel() if widget is not None else tk._default_root
                pointer = (
                    root.winfo_containing(event.x_root, event.y_root)
                    if root is not None
                    else None
                )
            except Exception:
                pointer = None
            target = cls._frame_for(pointer)
        if target is None or not target._parent_canvas.winfo_exists():
            return
        target._scroll_wheel(event)

    # ---------------------------------------------------------------- geometry
    def _content_height(self) -> int:
        if self._virtual and self._virtual_height > 0:
            return max(1, int(self._virtual_height))
        try:
            return max(1, self.winfo_reqheight())
        except Exception:
            return 1

    def _viewport_height(self) -> int:
        try:
            return max(1, self._parent_canvas.winfo_height())
        except Exception:
            return 1

    def _max_offset(self) -> float:
        return max(0.0, float(self._content_height() - self._viewport_height()))

    def _live_children(self) -> list[tk.Misc]:
        try:
            return [child for child in self.winfo_children() if child.winfo_exists()]
        except Exception:
            return []

    # --------------------------------------------------------------- scrolling
    def _current_target(self) -> float:
        if self._pending_offset is not None:
            return self._pending_offset
        return self._offset

    def _request_offset(self, offset: float) -> None:
        """Coalesce scroll requests to one content move per display frame.

        A mouse drag produces far more motion events than the window can
        repaint.  Applying every one of them queues partial paints and makes
        the page show several offsets at once.  Keeping only the newest target
        and moving the content once per frame keeps each paint complete.
        """

        limit = self._max_offset()
        self._pending_offset = max(0.0, min(float(offset), limit))
        if self._flush_job is None:
            try:
                self._flush_job = self.after(self.FRAME_MS, self._flush_offset)
            except Exception:
                self._flush_job = None
                self._apply_offset(self._pending_offset)

    def _flush_offset(self) -> None:
        self._flush_job = None
        target = self._pending_offset
        self._pending_offset = None
        if target is not None:
            self._apply_offset(target)

    def _apply_offset(self, offset: float, *, sync: bool | None = None) -> None:
        limit = self._max_offset()
        self._offset = max(0.0, min(float(offset), limit))
        if self._busy:
            return
        self._position_rows()
        if sync is None:
            # While the user holds the scrollbar, its thumb is already drawn
            # by CustomTkinter.  Calling set() here would overwrite the drag
            # anchor and make the page jump ahead of the pointer.
            sync = not self._bar_driven
        if sync:
            self._sync_scrollbar()

    def _position_rows(self) -> None:
        if not self._virtual or not self._rows:
            try:
                self._parent_canvas.coords(
                    self._create_window_id, 0, -int(round(self._offset))
                )
            except Exception:
                pass
            return
        offset = int(round(self._offset))
        if self._rows_placed and sys.platform.startswith("win") and self._move_rows_native(offset):
            self._last_offset = offset
            # Flush the bands the rows left behind before the compositor
            # presents this frame.
            win32.repaint_now(self)
            return
        for row in self._rows:
            widget = row.widget
            try:
                if not widget.winfo_exists():
                    self._schedule_virtualize()
                    return
                args = [
                    "place", widget._w,
                    "-relx", row.relx,
                    "-relwidth", row.relwidth,
                    "-y", row.y - offset,
                ]
                if not row.natural:
                    # Stretched grid cells keep the height the grid gave them;
                    # natural rows follow their own requested height so cards
                    # with growing lists still expand.
                    args += ["-height", row.height]
                self.tk.call(*args)
            except Exception:
                self._schedule_virtualize()
                return
        self._rows_placed = True
        self._last_offset = offset

    def _move_rows_native(self, offset: int) -> bool:
        try:
            width = max(1, int(self.winfo_width()))
            viewport = self._viewport_height()
        except Exception:
            return False
        previous = self._last_offset
        margin = 80
        moves: list[tuple[int, int, int]] = []
        for row in self._rows:
            widget = row.widget
            try:
                if not widget.winfo_exists():
                    self._schedule_virtualize()
                    return True
                new_y = row.y - offset
                old_y = row.y - previous
                on_screen = (
                    new_y + row.height > -margin and new_y < viewport + margin
                ) or (
                    old_y + row.height > -margin and old_y < viewport + margin
                )
                if not on_screen:
                    # The row is clipped by the viewport either way; moving it
                    # would only make the batch slower.
                    continue
                moves.append(
                    (widget.winfo_id(), int(round(row.relx * width)), new_y)
                )
            except Exception:
                return False
        return win32.move_windows_atomically(moves)

    def _sync_scrollbar(self) -> None:
        if self._syncing:
            return
        self._syncing = True
        try:
            total = float(self._content_height())
            view = float(self._viewport_height())
            first = self._offset / total
            last = min(1.0, (self._offset + view) / total)
            if last - first >= 0.999:
                first, last = 0.0, 1.0
            self._scrollbar.set(first, last)
        except Exception:
            pass
        finally:
            self._syncing = False

    def _scroll_command(self, *args) -> None:
        if not args:
            return
        kind = args[0]
        if kind == "moveto":
            try:
                fraction = float(args[1])
            except (IndexError, TypeError, ValueError):
                return
            self._bar_driven = True
            self._request_offset(fraction * self._content_height())
        elif kind == "scroll":
            try:
                amount = float(args[1])
            except (IndexError, TypeError, ValueError):
                return
            self._bar_driven = False
            unit = args[2] if len(args) > 2 else "units"
            if unit == "pages":
                amount *= self._viewport_height()
            else:
                amount *= 16.0
            self._request_offset(self._current_target() + amount)

    def _bar_released(self, _event: tk.Event | None = None) -> None:
        if not self._bar_driven:
            return
        self._bar_driven = False
        self._sync_scrollbar()

    def _scroll_wheel(self, event: tk.Event) -> None:
        canvas = self._parent_canvas
        delta = int(getattr(event, "delta", 0) or 0)
        if delta == 0:
            return

        # Shift+wheel is the usual shortcut for horizontal panning.
        state = int(getattr(event, "state", 0) or 0)
        shift = bool(state & 0x0001)
        horizontal = shift and canvas.xview() != (0.0, 1.0)

        # 120 units is one wheel notch; 0.42 gives a comfortable ~50 px step.
        # Tk reports a negative delta when the wheel rolls away from the user,
        # which must move the page down (positive offset).  Small touchpad
        # deltas accumulate until they make a whole pixel.
        self._wheel_remainder += -delta * self.WHEEL_STEP
        steps = int(self._wheel_remainder)
        if steps == 0:
            return
        self._wheel_remainder -= steps

        if horizontal:
            try:
                canvas.xview_scroll(steps, "units")
            except Exception:
                pass
            return
        if self._max_offset() <= 0:
            self._wheel_remainder = 0.0
            return
        self._bar_driven = False
        self._request_offset(self._current_target() + steps)

    # ----------------------------------------------------------- virtualization
    def _schedule_virtualize(self) -> None:
        if self._busy or not self._virtual or self._virtual_job is not None:
            return
        try:
            self._virtual_job = self.after_idle(self._run_virtualize)
        except Exception:
            self._virtual_job = None

    def _run_virtualize(self) -> None:
        self._virtual_job = None
        if self._busy or not self._virtual:
            return
        self._virtualize()

    def _bind_row(self, widget: tk.Misc) -> None:
        name = str(widget)
        if name in self._bound_rows:
            return
        self._bound_rows.add(name)
        try:
            widget.bind("<Configure>", self._row_configured, add="+")
            widget.bind("<Destroy>", self._row_destroyed, add="+")
        except Exception:
            pass

    def _row_configured(self, event: tk.Event) -> None:
        if self._busy or not self._virtual:
            return
        row = self._row_by_name.get(str(event.widget))
        if row is None:
            # A row was added without a full rebuild.
            self._schedule_virtualize()
            return
        # Moving a placed row also fires <Configure>; only a size change means
        # the content itself changed and the layout has to be re-measured.
        if abs(int(getattr(event, "height", 0)) - row.height) > 1:
            self._schedule_virtualize()

    def _row_destroyed(self, event: tk.Event) -> None:
        if self._busy or not self._virtual:
            return
        # A page that recreates its children needs a full measurement pass, and
        # the freshly built widgets need a few frames before their wrapped text
        # reports its final height.
        self._rebuild_pending = True
        self._schedule_virtualize()

    def _measure_rows(self) -> list[_VirtualRow]:
        width = max(1, int(self.winfo_width()))
        rows: list[_VirtualRow] = []
        for child in self._live_children():
            try:
                x = int(child.winfo_x())
                y = int(child.winfo_y())
                row_width = int(child.winfo_width())
                height = int(child.winfo_height())
                requested = int(child.winfo_reqheight())
            except Exception:
                continue
            if row_width <= 1 or height <= 0:
                continue
            natural = height <= requested + 1
            rows.append(
                _VirtualRow(
                    child,
                    y,
                    height,
                    requested,
                    natural,
                    x / width,
                    min(1.0, row_width / width),
                )
            )
        rows.sort(key=lambda row: row.y)
        return rows

    def _virtualize(self) -> bool:
        """Start a two-phase virtualization pass.

        Phase one restores the normal grid layout, panned by the current
        offset so the visible region does not change, and lets Tk compute the
        geometry on its own idle passes.  Phase two measures that layout and
        switches to a viewport-sized window with placed rows.  The split
        matters: forcing ``update_idletasks`` from inside an idle callback
        re-enters Tk's geometry loop and can hang the window.
        """
        if self._busy or self._cooldown:
            return False
        try:
            if not self.winfo_exists() or not self.winfo_ismapped():
                return False
        except Exception:
            return False
        canvas = self._parent_canvas
        if int(canvas.winfo_width()) <= 20 or int(canvas.winfo_height()) <= 20:
            self._retry_virtualize()
            return False
        children = self._live_children()
        if not children or not any(child.winfo_height() > 1 for child in children):
            self._retry_virtualize()
            return False

        self._busy = True
        self._measure_seen = None
        try:
            try:
                self.tk.call("grid", "propagate", self._w, 1)
            except Exception:
                pass
            for row in self._rows:
                if not row.widget.winfo_exists():
                    continue
                try:
                    self.tk.call("place", "forget", row.widget._w)
                except Exception:
                    pass
                try:
                    self.tk.call("grid", row.widget._w)
                except Exception:
                    pass
            try:
                canvas.itemconfigure(self._create_window_id, height=0)
                canvas.coords(self._create_window_id, 0, -int(round(self._offset)))
            except Exception:
                pass
        except Exception:
            self._busy = False
            return False
        # A rebuilt page needs longer: freshly created widgets settle their
        # wrapped text over a few frames, and measuring in between would freeze
        # the intermediate (much taller) geometry.
        settle = 240 if self._rebuild_pending else 24
        try:
            self.after(settle, self._finish_virtualize)
        except Exception:
            self._busy = False
            return False
        return True

    def _layout_plausible(self, rows: list[_VirtualRow]) -> bool:
        """Reject measurements taken while Tk is still relaying out the grid.

        A row can never be taller than its requested height once the layout is
        settled (grid may stretch it, never squash it), and it cannot extend
        past the content frame.  Both hold trivially when the grid has finished
        its pass and reliably fail in the transient frames we must not freeze.
        """

        width = max(1, int(self.winfo_width()))
        for row in rows:
            if row.height < row.requested - 1:
                return False
            if row.relx < 0.0 or row.relwidth <= 0.0:
                return False
            if (row.relx + row.relwidth) * width > width + 4:
                return False
        return True

    def _finish_virtualize(self, attempt: int = 0) -> None:
        if not self._busy:
            return
        try:
            if not self.winfo_exists():
                self._busy = False
                return
        except Exception:
            self._busy = False
            return
        children = self._live_children()
        if children and any(
            child.winfo_manager() != "grid" for child in children
        ):
            # Tk has not finished restoring the grid layout yet.
            if attempt < 12:
                self.after(4, lambda: self._finish_virtualize(attempt + 1))
            else:
                self._abandon_virtualize()
            return
        rows = self._measure_rows()
        if not rows:
            self._virtual = False
            self._rows = []
            self._row_by_name = {}
            self._rows_placed = False
            self._busy = False
            self._apply_offset(self._offset, sync=True)
            return

        signature = tuple(
            (str(row.widget), row.y, row.height, int(row.relx * 10000),
             int(row.relwidth * 10000))
            for row in rows
        )
        seen = self._measure_seen
        self._measure_seen = signature
        plausible = self._layout_plausible(rows)
        if attempt < 40 and (not plausible or seen != signature):
            # One more pass: either the geometry is invalid or it is still
            # changing, and switching now would freeze a half-settled layout.
            self.after(12, lambda: self._finish_virtualize(attempt + 1))
            return
        if not plausible:
            self._abandon_virtualize()
            return

        canvas = self._parent_canvas
        viewport_width = max(1, int(canvas.winfo_width()))
        viewport_height = max(1, int(canvas.winfo_height()))
        try:
            natural = max(1, int(self.winfo_reqheight()))
        except Exception:
            natural = 1
        for row in rows:
            try:
                self.tk.call("grid", "remove", row.widget._w)
            except Exception:
                pass
        try:
            self.tk.call("grid", "propagate", self._w, 0)
            canvas.itemconfigure(
                self._create_window_id,
                width=viewport_width,
                height=viewport_height,
            )
            canvas.coords(self._create_window_id, 0, 0)
        except Exception:
            pass

        last = rows[-1]
        content = max(natural, last.y + last.height)
        self._rows = rows
        self._row_by_name = {str(row.widget): row for row in rows}
        self._bound_rows &= set(self._row_by_name)
        for row in rows:
            self._bind_row(row.widget)
        self._virtual_height = content
        self._virtual_width = viewport_width
        self._virtual = True
        self._retry_count = 0
        self._rebuild_pending = False
        self._cooldown = False
        self._offset = max(0.0, min(self._offset, self._max_offset()))
        self._rows_placed = False
        self._busy = False
        self._position_rows()
        self._sync_scrollbar()

    def _abandon_virtualize(self) -> None:
        """Restore the normal grid layout when a measure cannot settle.

        Virtualizing is an optimisation; showing a page with the wrong geometry
        is not acceptable.  Falling back to the canvas pan keeps the layout
        correct (at the cost of the older pan cost) and retries a little later.
        """

        self._virtual = False
        self._rows = []
        self._row_by_name = {}
        self._rows_placed = False
        self._measure_seen = None
        self._busy = False
        self._cooldown = True
        try:
            self.tk.call("grid", "propagate", self._w, 1)
            self._parent_canvas.itemconfigure(self._create_window_id, height=0)
        except Exception:
            pass
        for child in self._live_children():
            try:
                if child.winfo_manager() != "grid":
                    self.tk.call("place", "forget", child._w)
                    self.tk.call("grid", child._w)
            except Exception:
                pass
        self._apply_offset(self._offset, sync=True)
        try:
            self.after(700, self._end_cooldown)
        except Exception:
            self._cooldown = False

    def _end_cooldown(self) -> None:
        self._cooldown = False
        self._refresh_scroll()

    def _retry_virtualize(self) -> None:
        if self._retry_job is not None or self._retry_count >= 40:
            return
        self._retry_count += 1
        try:
            self._retry_job = self.after(30, self._run_retry)
        except Exception:
            self._retry_job = None

    def _run_retry(self) -> None:
        self._retry_job = None
        try:
            if not self.winfo_exists():
                return
        except Exception:
            return
        self._refresh_scroll()

    # -------------------------------------------------------------- lifecycle
    def _queue_sync(self, _event: tk.Event | None = None) -> None:
        # Layout changed (rows rebuilt, window resized): re-clamp once Tk has
        # recomputed the requested size.
        try:
            self.after_idle(self._refresh_scroll)
        except Exception:
            pass

    def _content_configured(self, event: tk.Event) -> None:
        size = (int(getattr(event, "width", 0)), int(getattr(event, "height", 0)))
        if size == self._content_size:
            return
        self._content_size = size
        self._queue_sync()

    def _refresh_scroll(self) -> None:
        if self._busy:
            return
        try:
            if not self.winfo_exists():
                return
        except Exception:
            return
        if not self._virtual:
            if self._pending_offset is not None:
                self._pending_offset = min(self._pending_offset, self._max_offset())
                return
            if self._can_virtualize() and self._virtualize():
                self._sync_scrollbar()
                return
            self._apply_offset(self._offset, sync=True)
            return
        if self._pending_offset is not None:
            self._pending_offset = min(self._pending_offset, self._max_offset())
            return
        self._apply_offset(self._offset, sync=True)

    def _can_virtualize(self) -> bool:
        try:
            if self._cooldown:
                return False
            if not self.winfo_ismapped():
                return False
            if self._viewport_height() <= 20:
                return False
            return self.winfo_reqheight() > self._viewport_height() + 2
        except Exception:
            return False

    def scroll_to_top(self) -> None:
        if self._flush_job is not None:
            try:
                self.after_cancel(self._flush_job)
            except Exception:
                pass
            self._flush_job = None
        self._pending_offset = None
        self._bar_driven = False
        self._apply_offset(0.0, sync=True)


class ScrollPage(PageBase):
    """Page with a fixed header and a scrollable content area."""

    def __init__(self, master: tk.Misc, app: "OptimusXApp") -> None:
        super().__init__(master, app)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self.header = ctk.CTkFrame(self, fg_color="transparent")
        self.header.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        self.header.grid_columnconfigure(0, weight=1)
        self.body = SmoothScrollFrame(
            self,
            fg_color="transparent",
            corner_radius=0,
            scrollbar_button_color=theme.Color.BORDER_STRONG,
            scrollbar_button_hover_color=theme.Color.CYAN_DIM,
        )
        self.body.grid(row=1, column=0, sticky="nsew")
        self.body.grid_columnconfigure(0, weight=1)

    def scroll_to_top(self) -> None:
        self.body.scroll_to_top()
