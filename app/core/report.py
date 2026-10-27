"""Human-readable system report generation."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from . import system
from .catalog import cleaner_components, tweaks
from .executor import executor
from .store import store


def build_report() -> str:
    data = system.summary()
    applied = []
    pending = []
    for tweak in tweaks():
        state = executor.is_applied(tweak)
        if state:
            applied.append(tweak.title)
        else:
            pending.append(tweak.title)

    components = []
    for item in cleaner_components():
        state = executor.is_applied(item)
        label = "removed/disabled" if state else ("present" if state is False else "unknown")
        components.append(f"- {item.title}: {label}")

    lines = [
        "# Optimus X — System Report",
        "",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Privileges: {data['admin']}",
        "",
        "## System",
        f"- OS: {data['os']['name']} (build {data['os']['build']}, {data['os']['architecture']})",
        f"- Machine: {data['os']['hostname']} / {data['os']['user']}",
        f"- CPU: {data['cpu']['name']} ({data['cpu']['cores']}C / {data['cpu']['threads']}T)",
        f"- RAM: {data['ram_gb']:.1f} GB",
        f"- GPU: {', '.join(data['gpu'])}",
        f"- System disk: {data['disk']['path']} {system.format_bytes(data['disk']['used'])} used "
        f"of {system.format_bytes(data['disk']['total'])} ({data['disk']['percent']}%)",
        f"- Power plan: {data['power_plan']['name']}",
        f"- Uptime: {data['uptime']}",
        "",
        f"## Applied Tweaks ({len(applied)})",
    ]
    lines.extend(f"- {title}" for title in applied) if applied else lines.append("- None")
    lines.extend(
        [
            "",
            f"## Recommended / Not Applied ({len(pending)})",
        ]
    )
    lines.extend(f"- {title}" for title in pending[:20]) if pending else lines.append("- None")
    lines.extend(
        [
            "",
            "## System Components",
            *components,
            "",
            "## Safety",
            f"- Reversible backups stored: {store.backup_count()}",
            f"- Dry-run mode: {store.get('dry_run')}",
            f"- Application data: {store.root}",
            "",
            "_Generated locally by Optimus X. No data leaves this machine._",
        ]
    )
    return "\n".join(lines)


def export_report() -> Path:
    path = store.reports_dir / f"OptimusX_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    path.write_text(build_report(), encoding="utf-8")
    store.action_log(f"System report exported: {path}")
    return path
