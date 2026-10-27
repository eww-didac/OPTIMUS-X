"""Shared confirmation and execution flow for reversible tweak batches.

The Dashboard and Tweaks & Privacy both offer quick profiles and staged
changes.  Keeping the confirmation, restore-point and task-dialog logic in one
place guarantees that every path is backed up, reversible and reported the same
way.
"""

from __future__ import annotations

import threading
from typing import Callable

from .. import i18n, theme
from ..core import catalog
from ..core.executor import executor
from ..core.store import store
from .dialogs import ConfirmDialog, TaskDialog


def risk_for(items: list[catalog.Tweak]) -> str:
    if any(item.risk == "extreme" for item in items):
        return "extreme"
    if any(item.risk == "advanced" for item in items):
        return "advanced"
    return "safe"


def _unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            result.append(item)
    return result


def apply_tweak_batch(
    app,
    apply_items: list[catalog.Tweak],
    revert_items: list[catalog.Tweak] | None = None,
    *,
    title: str,
    message: str,
    confirm_text: str,
    admin_message: str = "",
    task_title: str | None = None,
    profile_name: str = "Staged changes",
    extra_warnings: list[str] | None = None,
    risk: str | None = None,
    height: int | None = None,
    on_start: Callable[[], None] | None = None,
    on_done: Callable[[dict], None] | None = None,
) -> bool:
    """Confirm, execute and report one batch of tweaks.

    Returns ``True`` when the confirmation dialog was opened.  The function
    never writes anything until the user confirms, and every applied value is
    backed up by the executor.
    """

    apply_items = list(apply_items)
    revert_items = list(revert_items or [])
    if not apply_items and not revert_items:
        return False

    if any(item.admin for item in apply_items + revert_items) and not app.is_admin:
        app.prompt_admin(
            admin_message
            or i18n.tr("These changes modify Windows services and system registry values.")
        )
        return False

    lines = [
        i18n.tr("ENABLE  ·  {name}", name=i18n.tr(item.title)) for item in apply_items
    ]
    lines += [
        i18n.tr("RESTORE  ·  {name}", name=i18n.tr(item.title)) for item in revert_items
    ]

    warnings = _unique(list(extra_warnings or []))
    for item in apply_items + revert_items:
        if item.warning:
            warnings.append(item.warning)
    warnings = _unique(warnings)
    if len(warnings) > 5:
        hidden = len(warnings) - 4
        warnings = warnings[:4] + [
            i18n.tr(
                "Plus {count} more warning(s) listed in the task output.", count=hidden
            )
        ]

    if risk is None:
        risk = risk_for(apply_items)

    if height is None:
        height = 470 if len(lines) < 12 else 540
        if len(warnings) >= 4:
            height = max(height, 540)

    def confirmed(accepted: bool, checked: bool) -> None:
        if not accepted:
            return
        store.set("create_restore_point", checked)
        if on_start is not None:
            on_start()

        def worker(emit, cancel: threading.Event) -> dict:
            apply_summary = {"ok": 0, "failed": 0, "reboot": False}
            revert_summary = {"ok": 0, "failed": 0}
            if apply_items:
                apply_summary = executor.apply_many(
                    apply_items,
                    create_restore_point=checked,
                    emit=emit,
                    cancel=cancel,
                )
            if revert_items and not cancel.is_set():
                emit(i18n.tr("\nRestoring selected tweaks…"))
                revert_summary = executor.revert_many(
                    revert_items, emit=emit, cancel=cancel
                )
            return {
                "ok": int(apply_summary.get("ok", 0)) + int(revert_summary.get("ok", 0)),
                "failed": int(apply_summary.get("failed", 0)) + int(revert_summary.get("failed", 0)),
                "reboot": bool(apply_summary.get("reboot") or revert_summary.get("reboot")),
                "dry_run": bool(apply_summary.get("dry_run") or revert_summary.get("dry_run")),
            }

        def done(result: dict) -> None:
            try:
                app.refresh_dashboard()
            except Exception:
                pass
            try:
                app.refresh_sidebar_identity()
            except Exception:
                pass
            failed = int(result.get("failed") or 0)
            dry = bool(result.get("dry_run"))
            applied = int(result.get("ok") or 0)
            if dry:
                app.notify(
                    i18n.tr("Dry-run complete — no changes were written."), "info"
                )
            elif failed:
                app.notify(
                    i18n.tr(
                        "Finished with {count} issue(s). Review the task output.",
                        count=failed,
                    ),
                    "warning",
                )
            else:
                app.notify(
                    i18n.tr(
                        "{count} change applied and logged."
                        if applied == 1
                        else "{count} changes applied and logged.",
                        count=applied,
                    ),
                    "success",
                )
            if result.get("reboot") and not dry:
                app.notify(
                    i18n.tr(
                        "Restart Windows to finish applying kernel and network tweaks."
                    ),
                    "info",
                )
            if on_done is not None:
                on_done(result)

        TaskDialog(
            app,
            title=task_title or title,
            subtitle=i18n.tr(
                "{count} change · {profile} · backup and restore point enabled"
                if len(lines) == 1
                else "{count} changes · {profile} · backup and restore point enabled",
                count=len(lines),
                profile=i18n.tr(profile_name).lower(),
            ),
            worker=worker,
            on_done=done,
            accent=theme.Color.AMBER if risk == "extreme" else theme.Color.CYAN,
        )

    ConfirmDialog(
        app,
        title=title,
        message=message,
        confirm_text=confirm_text,
        items=lines,
        warnings=warnings[:5],
        risk=risk,
        checkbox_text=i18n.tr("Create a Windows restore point before applying"),
        checkbox_default=bool(store.get("create_restore_point", True)),
        height=height,
        on_result=confirmed,
    )
    return True
