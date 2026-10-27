"""Background telemetry sampler for the dashboard."""

from __future__ import annotations

import threading
import time
from typing import Any

import psutil

from . import system


class MetricsService:
    def __init__(self) -> None:
        self.latest: dict[str, Any] = {
            "cpu": 0.0,
            "cpu_freq": None,
            "cpu_temp": None,
            "ram_percent": 0.0,
            "ram_used": 0.0,
            "ram_total": psutil.virtual_memory().total,
            # GPU telemetry can take a few hundred milliseconds on systems
            # where it has to ask Windows for the 3D engine counters.  Start
            # with a neutral value and let the sampler fill it in off-thread so
            # importing the app never blocks on a hardware probe.
            "gpu": {},
            "gpu_history": [],
            "latency": None,
            "processes": 0,
            "disk_percent": 0.0,
            "updated": 0.0,
        }
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, name="optimus-metrics", daemon=True)
        self.started = False

    def start(self) -> None:
        if not self.started:
            self.started = True
            self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def _run(self) -> None:
        history: list[float] = []
        cycle = 0
        psutil.cpu_percent(interval=None)
        while not self._stop.is_set():
            try:
                cpu = psutil.cpu_percent(interval=0.55)
                memory = psutil.virtual_memory()
                freq = None
                try:
                    cpu_freq = psutil.cpu_freq()
                    if cpu_freq:
                        freq = cpu_freq.current / 1000.0
                except Exception:
                    pass

                temp = None
                try:
                    temps = psutil.sensors_temperatures()
                    for entries in temps.values():
                        for entry in entries:
                            if entry.current and entry.current > 0:
                                temp = entry.current
                                break
                        if temp:
                            break
                except Exception:
                    pass

                gpu = self.latest.get("gpu") or {}
                # Sampling the GPU spawns a helper process (nvidia-smi or
                # PowerShell), so keep it on a slower cadence than CPU/RAM and
                # reuse the previous value in between.
                if not self.latest.get("_gpu_ready") or cycle % 4 == 0:
                    gpu = system.gpu_stats()
                    self.latest["_gpu_ready"] = True
                    gpu_percent = gpu.get("percent")
                    if gpu_percent is not None:
                        history.append(float(gpu_percent))
                        history = history[-40:]

                latency = self.latest.get("latency")
                if cycle % 6 == 0:
                    latency = system.network_latency()

                try:
                    disk_percent = psutil.disk_usage(system.system_drive()).percent
                except Exception:
                    disk_percent = 0.0

                self.latest.update(
                    {
                        "cpu": cpu,
                        "cpu_freq": freq,
                        "cpu_temp": temp,
                        "ram_percent": memory.percent,
                        "ram_used": memory.used,
                        "ram_total": memory.total,
                        "gpu": gpu,
                        "gpu_history": list(history),
                        "latency": latency,
                        "processes": len(psutil.pids()),
                        "disk_percent": disk_percent,
                        "updated": time.time(),
                    }
                )
            except Exception:
                pass
            cycle += 1
            self._stop.wait(1.15)


metrics = MetricsService()
