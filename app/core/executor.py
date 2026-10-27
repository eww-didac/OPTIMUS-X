"""Safe, auditable execution of catalog tweaks with full revert support."""

from __future__ import annotations

import base64
import subprocess
import threading
import time
import winreg
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable

from . import system
from .admin import is_admin, run_ps
from .catalog import CmdOp, Op, RegOp, SvcOp, Tweak
from .store import store

Emit = Callable[[str], None]


@dataclass
class ActionResult:
    tweak_id: str
    title: str
    success: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    dry_run: bool = False


def _encode_value(value: Any, value_type: int) -> Any:
    if value_type == winreg.REG_BINARY and isinstance(value, (bytes, bytearray)):
        return {"__bytes__": base64.b64encode(bytes(value)).decode("ascii")}
    return value


def _decode_value(value: Any) -> Any:
    if isinstance(value, dict) and "__bytes__" in value:
        return base64.b64decode(value["__bytes__"])
    return value


class Executor:
    def __init__(self) -> None:
        self._lock = threading.RLock()

    # ------------------------------------------------------------------ detection
    def is_applied(self, tweak: Tweak) -> bool | None:
        if tweak.probe is not None:
            try:
                return bool(tweak.probe())
            except Exception:
                return None
        states: list[bool] = []
        for op in tweak.ops:
            if isinstance(op, RegOp):
                states.append(system.reg_matches(op.hive, op.path, op.name, op.value))
            elif isinstance(op, SvcOp):
                if not system.service_exists(op.name):
                    continue
                states.append(system.service_start(op.name) == op.start)
        if not states:
            return None
        return all(states)

    def applied_count(self, items: list[Tweak] | tuple[Tweak, ...] | None = None) -> int:
        if items is None:
            from .catalog import tweaks

            items = tweaks()
        return sum(1 for tweak in items if self.is_applied(tweak))

    # --------------------------------------------------------------------- apply
    def apply(
        self,
        tweak: Tweak,
        *,
        emit: Emit | None = None,
        dry_run: bool = False,
    ) -> ActionResult:
        emit = emit or (lambda _text: None)
        result = ActionResult(tweak.id, tweak.title, True, dry_run=dry_run)
        with self._lock:
            if tweak.admin and not is_admin():
                result.success = False
                result.errors.append("Administrator rights are required.")
                emit(f"[!] {tweak.title}: administrator rights required.")
                return result
            if dry_run:
                emit(f"[dry] Would apply: {tweak.title}")
                store.action_log(f"DRY RUN apply: {tweak.title}")
                return result

            self._backup(tweak)
            for op in tweak.ops:
                try:
                    self._apply_op(op, tweak, emit)
                except Exception as exc:
                    message = f"{type(exc).__name__}: {exc}"
                    result.errors.append(message)
                    emit(f"[!] {tweak.title}: {message}")
            if result.errors:
                result.success = False
                store.action_log(f"PARTIAL apply: {tweak.title} ({len(result.errors)} errors)")
            else:
                store.action_log(f"Applied: {tweak.title}")
                emit(f"[ok] {tweak.title}")
            return result

    def _apply_op(self, op: Op, tweak: Tweak, emit: Emit) -> None:
        if isinstance(op, RegOp):
            self._set_reg(op)
            return
        if isinstance(op, SvcOp):
            if not system.service_exists(op.name):
                emit(f"     service {op.name} is not present - skipped")
                return
            if not system.is_admin():
                raise PermissionError("service changes require administrator rights")
            start_arg = {"manual": "demand", "auto": "auto", "disabled": "disabled"}.get(
                op.start, op.start
            )
            config = subprocess.run(
                ["sc.exe", "config", op.name, "start=", start_arg],
                capture_output=True,
                text=True,
                timeout=15,
                creationflags=0x08000000,
            )
            if config.returncode != 0:
                detail = (config.stderr or config.stdout or "").strip().splitlines()
                raise RuntimeError(detail[-1] if detail else f"sc config failed ({config.returncode})")
            if op.stop:
                subprocess.run(
                    ["sc.exe", "stop", op.name],
                    capture_output=True,
                    text=True,
                    timeout=25,
                    creationflags=0x08000000,
                )
            emit(f"     service {op.name} -> {op.start}")
            return
        if isinstance(op, CmdOp):
            label = op.label or tweak.title
            emit(f"     running: {label}")
            proc = run_ps(op.script, timeout=420)
            if proc.returncode != 0:
                detail = (proc.stderr or proc.stdout or "").strip().splitlines()
                raise RuntimeError(detail[-1] if detail else f"command failed ({proc.returncode})")
            for line in (proc.stdout or "").strip().splitlines()[-4:]:
                if line.strip():
                    emit(f"     {line.strip()[:180]}")

    # --------------------------------------------------------------------- revert
    def revert(
        self,
        tweak: Tweak,
        *,
        emit: Emit | None = None,
        dry_run: bool = False,
    ) -> ActionResult:
        emit = emit or (lambda _text: None)
        result = ActionResult(tweak.id, tweak.title, True, dry_run=dry_run)
        with self._lock:
            if tweak.admin and not is_admin():
                result.success = False
                result.errors.append("Administrator rights are required.")
                emit(f"[!] {tweak.title}: administrator rights required.")
                return result
            if dry_run:
                emit(f"[dry] Would revert: {tweak.title}")
                store.action_log(f"DRY RUN revert: {tweak.title}")
                return result

            backups = store.load_backups()
            backup = backups.get("tweaks", {}).get(tweak.id)
            if backup:
                for entry in reversed(backup.get("registry", [])):
                    try:
                        self._restore_reg(entry)
                    except Exception as exc:
                        result.errors.append(f"{entry.get('name')}: {exc}")
                        emit(f"[!] Could not restore {entry.get('name')}: {exc}")
                for entry in reversed(backup.get("services", [])):
                    try:
                        self._restore_service(entry)
                    except Exception as exc:
                        result.errors.append(f"{entry.get('name')}: {exc}")
                        emit(f"[!] Could not restore service {entry.get('name')}: {exc}")

            for op in reversed(tweak.ops):
                if isinstance(op, CmdOp) and op.undo_script:
                    try:
                        emit(f"     undoing: {op.label or tweak.title}")
                        proc = run_ps(op.undo_script, timeout=420)
                        if proc.returncode != 0:
                            detail = (proc.stderr or proc.stdout or "").strip().splitlines()
                            raise RuntimeError(detail[-1] if detail else "undo command failed")
                    except Exception as exc:
                        result.errors.append(str(exc))
                        emit(f"[!] {tweak.title}: {exc}")

            if result.errors:
                result.success = False
                store.action_log(f"PARTIAL revert: {tweak.title} ({len(result.errors)} errors)")
            else:
                backups.get("tweaks", {}).pop(tweak.id, None)
                store.save_backups(backups)
                store.action_log(f"Reverted: {tweak.title}")
                emit(f"[ok] Reverted: {tweak.title}")
            return result

    # --------------------------------------------------------------------- batch
    def apply_many(
        self,
        items: list[Tweak],
        *,
        create_restore_point: bool = True,
        dry_run: bool | None = None,
        emit: Emit | None = None,
        cancel: threading.Event | None = None,
    ) -> dict[str, Any]:
        emit = emit or (lambda _text: None)
        dry = store.get("dry_run", False) if dry_run is None else dry_run
        cancel = cancel or threading.Event()
        started = time.time()

        emit(f"Preparing {len(items)} change(s)…")
        if create_restore_point and not dry:
            if is_admin():
                emit("Creating a Windows restore point…")
                ok, message = system.create_restore_point()
                emit(("[ok] " if ok else "[!] ") + message)
            else:
                emit("[!] Restore point skipped: administrator rights required.")

        results: list[ActionResult] = []
        offsets = 0
        for index, tweak in enumerate(items, start=1):
            if cancel.is_set():
                emit("[!] Cancelled.")
                break
            emit(f"\n[{index}/{len(items)}] {tweak.title}")
            result = self.apply(tweak, emit=emit, dry_run=dry)
            results.append(result)
            if result.success:
                offsets += 1

        failed = [item for item in results if not item.success]
        reboot = any(tweak.reboot for tweak in items if tweak.id in {r.tweak_id for r in results})
        summary = {
            "ok": len(results) - len(failed),
            "failed": len(failed),
            "reboot": reboot,
            "dry_run": dry,
            "results": results,
            "seconds": round(time.time() - started, 1),
        }
        if not dry and not failed:
            ids = [tweak.id for tweak in items]
            from .catalog import estimated_gain

            store.record_optimization(estimated_gain(ids))
        store.action_log(
            f"BATCH apply complete: {summary['ok']} ok, {summary['failed']} failed, "
            f"{summary['seconds']}s{' (dry run)' if dry else ''}"
        )
        emit(
            f"\nFinished in {summary['seconds']}s — {summary['ok']} applied"
            + (f", {summary['failed']} failed" if failed else "")
        )
        return summary

    def revert_many(
        self,
        items: list[Tweak],
        *,
        emit: Emit | None = None,
        cancel: threading.Event | None = None,
        dry_run: bool | None = None,
    ) -> dict[str, Any]:
        emit = emit or (lambda _text: None)
        cancel = cancel or threading.Event()
        dry = bool(store.get("dry_run", False)) if dry_run is None else dry_run
        results: list[ActionResult] = []
        for index, tweak in enumerate(items, start=1):
            if cancel.is_set():
                emit("[!] Cancelled.")
                break
            emit(f"\n[{index}/{len(items)}] Reverting {tweak.title}")
            results.append(self.revert(tweak, emit=emit, dry_run=dry))
        failed = [item for item in results if not item.success]
        summary = {
            "ok": len(results) - len(failed),
            "failed": len(failed),
            "reboot": any(tweak.reboot for tweak in items),
            "results": results,
            "dry_run": dry,
        }
        store.action_log(f"BATCH revert complete: {summary['ok']} ok, {summary['failed']} failed")
        emit(f"\nRevert finished — {summary['ok']} restored" + (f", {summary['failed']} failed" if failed else ""))
        return summary

    def revert_all(self, emit: Emit | None = None, cancel: threading.Event | None = None) -> dict[str, Any]:
        from .catalog import cleaner_components, tweaks

        backups = store.load_backups().get("tweaks", {})
        known = {item.id: item for item in (*tweaks(), *cleaner_components())}
        items = [known[tweak_id] for tweak_id in backups.keys() if tweak_id in known]
        if not items:
            return {"ok": 0, "failed": 0, "reboot": False, "results": [], "empty": True}
        return self.revert_many(items, emit=emit, cancel=cancel)

    # ------------------------------------------------------------------ backups
    def _backup(self, tweak: Tweak) -> None:
        backups = store.load_backups()
        entries = backups.setdefault("tweaks", {})
        if tweak.id in entries:
            return
        entry: dict[str, Any] = {
            "title": tweak.title,
            "applied_at": datetime.now().isoformat(timespec="seconds"),
            "registry": [],
            "services": [],
        }
        for op in tweak.ops:
            if isinstance(op, RegOp):
                value, value_type = system.read_reg(op.hive, op.path, op.name)
                entry["registry"].append(
                    {
                        "hive": op.hive,
                        "path": op.path,
                        "name": op.name,
                        "existed": value is not None,
                        "value": _encode_value(value, value_type) if value is not None else None,
                        "value_type": value_type,
                    }
                )
            elif isinstance(op, SvcOp):
                if not system.service_exists(op.name):
                    continue
                entry["services"].append(
                    {
                        "name": op.name,
                        "start": system.service_start(op.name),
                        "running": system.service_running(op.name),
                    }
                )
        entries[tweak.id] = entry
        store.save_backups(backups)

    def _set_reg(self, op: RegOp) -> None:
        key = winreg.CreateKeyEx(
            system.HIVES[op.hive],
            op.path,
            0,
            winreg.KEY_SET_VALUE | winreg.KEY_WOW64_64KEY,
        )
        try:
            winreg.SetValueEx(key, op.name, 0, op.value_type, op.value)
        finally:
            winreg.CloseKey(key)

    def _restore_reg(self, entry: dict[str, Any]) -> None:
        key = winreg.CreateKeyEx(
            system.HIVES[entry["hive"]],
            entry["path"],
            0,
            winreg.KEY_SET_VALUE | winreg.KEY_WOW64_64KEY,
        )
        try:
            if entry.get("existed"):
                value = _decode_value(entry.get("value"))
                value_type = entry.get("value_type") or winreg.REG_SZ
                winreg.SetValueEx(key, entry["name"], 0, value_type, value)
            else:
                try:
                    winreg.DeleteValue(key, entry["name"])
                except FileNotFoundError:
                    pass
        finally:
            winreg.CloseKey(key)

    def _restore_service(self, entry: dict[str, Any]) -> None:
        name = entry.get("name")
        start = entry.get("start") or "manual"
        if not system.service_exists(name):
            return
        start_arg = {"manual": "demand", "auto": "auto", "disabled": "disabled"}.get(start, start)
        config = subprocess.run(
            ["sc.exe", "config", name, "start=", start_arg],
            capture_output=True,
            text=True,
            timeout=15,
            creationflags=0x08000000,
        )
        if config.returncode != 0:
            detail = (config.stderr or config.stdout or "").strip().splitlines()
            raise RuntimeError(detail[-1] if detail else f"sc config failed ({config.returncode})")
        if entry.get("running"):
            subprocess.run(
                ["sc.exe", "start", name],
                capture_output=True,
                text=True,
                timeout=20,
                creationflags=0x08000000,
            )


executor = Executor()
