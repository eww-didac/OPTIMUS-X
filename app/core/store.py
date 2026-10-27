"""Persistent settings, logs and application data."""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from threading import RLock
from typing import Any

from ..i18n import tr


APP_NAME = "OptimusX"
APP_VERSION = "2.0.0"


def _local_appdata() -> Path:
    base = os.environ.get("LOCALAPPDATA")
    if base:
        return Path(base)
    return Path.home() / "AppData" / "Local"


class Store:
    DEFAULTS: dict[str, Any] = {
        "dry_run": False,
        "create_restore_point": True,
        "gaming_mode": False,
        "gaming_profile_applied": [],
        "last_optimization": None,
        "last_gain": 0,
        "window_geometry": None,
        "removed_apps": [],
        "language": "en",
        "version": APP_VERSION,
    }

    def __init__(self) -> None:
        self.root = _local_appdata() / APP_NAME
        self.logs_dir = self.root / "logs"
        self.data_dir = self.root / "data"
        self.reports_dir = self.root / "reports"
        for directory in (self.root, self.logs_dir, self.data_dir, self.reports_dir):
            directory.mkdir(parents=True, exist_ok=True)

        self.settings_path = self.data_dir / "settings.json"
        self.backup_path = self.data_dir / "backups.json"
        self.actions_log_path = self.logs_dir / "actions.log"
        self._lock = RLock()
        self._settings = dict(self.DEFAULTS)
        self._load()

        self.logger = logging.getLogger("optimusx")
        self.logger.setLevel(logging.INFO)
        self.logger.propagate = False
        if not self.logger.handlers:
            handler = RotatingFileHandler(
                self.logs_dir / "optimusx.log",
                maxBytes=1_500_000,
                backupCount=3,
                encoding="utf-8",
            )
            handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)-7s | %(message)s"))
            self.logger.addHandler(handler)

    # ------------------------------------------------------------------ settings
    def _load(self) -> None:
        try:
            if self.settings_path.exists():
                raw = json.loads(self.settings_path.read_text(encoding="utf-8"))
                if isinstance(raw, dict):
                    self._settings.update(raw)
        except Exception:
            pass

    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            return self._settings.get(key, default)

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self._settings[key] = value
            self._save_locked()

    def update(self, values: dict[str, Any]) -> None:
        with self._lock:
            self._settings.update(values)
            self._save_locked()

    def _save_locked(self) -> None:
        try:
            temp = self.settings_path.with_suffix(".tmp")
            temp.write_text(json.dumps(self._settings, indent=2), encoding="utf-8")
            temp.replace(self.settings_path)
        except Exception as exc:
            self.logger.warning("Could not save settings: %s", exc)

    # ---------------------------------------------------------------------- logs
    def log(self, message: str, level: str = "info") -> None:
        getattr(self.logger, level, self.logger.info)(message)

    def action_log(self, text: str) -> None:
        """Human readable audit trail shown in the UI."""
        try:
            stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with self.actions_log_path.open("a", encoding="utf-8") as handle:
                handle.write(f"{stamp} | {text}\n")
        except Exception:
            pass
        self.logger.info(text)

    def read_actions_log(self, limit: int = 250) -> str:
        try:
            if not self.actions_log_path.exists():
                return tr("No activity recorded yet.")
            lines = self.actions_log_path.read_text(encoding="utf-8", errors="replace").splitlines()
            return "\n".join(lines[-limit:]) or tr("No activity recorded yet.")
        except Exception as exc:
            return tr("Could not read activity log: {error}", error=exc)

    def read_runtime_log(self, limit: int = 250) -> str:
        path = self.logs_dir / "optimusx.log"
        try:
            if not path.exists():
                return tr("No technical log recorded yet.")
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
            return "\n".join(lines[-limit:])
        except Exception as exc:
            return tr("Could not read technical log: {error}", error=exc)

    # ------------------------------------------------------------------ backups
    def load_backups(self) -> dict:
        try:
            if self.backup_path.exists():
                data = json.loads(self.backup_path.read_text(encoding="utf-8"))
                return data if isinstance(data, dict) else {}
        except Exception:
            pass
        return {}

    def save_backups(self, data: dict) -> None:
        try:
            temp = self.backup_path.with_suffix(".tmp")
            temp.write_text(json.dumps(data, indent=2), encoding="utf-8")
            temp.replace(self.backup_path)
        except Exception as exc:
            self.logger.warning("Could not save backup data: %s", exc)

    def backup_count(self) -> int:
        return len(self.load_backups().get("tweaks", {}))

    def record_optimization(self, gain: int) -> None:
        self.update(
            {
                "last_optimization": datetime.now().isoformat(timespec="seconds"),
                "last_gain": int(gain),
            }
        )

    def last_optimization_text(self) -> str:
        raw = self.get("last_optimization")
        if not raw:
            return tr("Never")
        try:
            dt = datetime.fromisoformat(raw)
            today = datetime.now().date()
            if dt.date() == today:
                day = tr("Today")
            else:
                # Spanish readers expect day/month; keep the textual month for
                # English so the existing look is preserved.
                day = dt.strftime("%d/%m") if tr("Today") == "Hoy" else dt.strftime("%b %d")
            return f"{day}, {dt.strftime('%I:%M %p').lstrip('0')}"
        except Exception:
            return str(raw)


store = Store()
