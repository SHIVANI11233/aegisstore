"""
safety_gate.py — Real-time system safety monitor.
This is what lets AegisStore override its own schedule: even a "low risk" file
will be deferred if the system is under heavy load RIGHT NOW.
"""
import time

import psutil

CPU_BUSY_THRESHOLD = 75.0
CPU_CRITICAL_THRESHOLD = 90.0
RAM_BUSY_THRESHOLD = 80.0
RAM_CRITICAL_THRESHOLD = 90.0
IO_WAIT_BUSY_THRESHOLD = 10.0
IO_WAIT_CRITICAL_THRESHOLD = 20.0


def _calculate_disk_rate(sample_seconds: float = 0.25):
    try:
        before = psutil.disk_io_counters()
        if before is None:
            return 0.0, 0.0
    except Exception:
        return 0.0, 0.0

    time.sleep(max(0.05, min(sample_seconds, 0.5)))
    try:
        after = psutil.disk_io_counters()
    except Exception:
        return 0.0, 0.0
    if after is None:
        return 0.0, 0.0

    elapsed = max(0.05, min(sample_seconds, 0.5))
    read_mb_s = ((after.read_bytes - before.read_bytes) / elapsed) / (1024 * 1024)
    write_mb_s = ((after.write_bytes - before.write_bytes) / elapsed) / (1024 * 1024)
    return max(0.0, read_mb_s), max(0.0, write_mb_s)


def _resolve_io_wait():
    try:
        times = psutil.cpu_times_percent(interval=None)
        return float(getattr(times, "iowait", 0.0) or 0.0)
    except Exception:
        return 0.0


def classify_system_state(cpu_percent: float, memory_percent: float, io_wait_percent: float) -> str:
    if cpu_percent >= CPU_CRITICAL_THRESHOLD or memory_percent >= RAM_CRITICAL_THRESHOLD or io_wait_percent >= IO_WAIT_CRITICAL_THRESHOLD:
        return "CRITICAL"
    if cpu_percent >= CPU_BUSY_THRESHOLD or memory_percent >= RAM_BUSY_THRESHOLD or io_wait_percent >= IO_WAIT_BUSY_THRESHOLD:
        return "BUSY"
    return "NORMAL"


def read_system_load(sample_seconds: float = 0.3):
    cpu = float(psutil.cpu_percent(interval=max(0.0, min(sample_seconds, 1.0))))
    mem = float(psutil.virtual_memory().percent)
    io_wait = _resolve_io_wait()
    disk_read_mb_s, disk_write_mb_s = _calculate_disk_rate(sample_seconds=max(0.1, min(sample_seconds, 0.5)))
    state = classify_system_state(cpu, mem, io_wait)
    return {
        "cpu_percent": cpu,
        "memory_percent": mem,
        "io_wait_percent": io_wait,
        "disk_read_mb_s": disk_read_mb_s,
        "disk_write_mb_s": disk_write_mb_s,
        "state": state,
    }


def is_system_busy(load: dict) -> bool:
    state = str(load.get("state") or classify_system_state(
        float(load.get("cpu_percent", 0.0)),
        float(load.get("memory_percent", 0.0)),
        float(load.get("io_wait_percent", 0.0)),
    ))
    return state in {"BUSY", "CRITICAL"}
