"""
safety_gate.py — Real-time system safety monitor.
This is what lets AegisStore override its own schedule: even a "low risk" file
will be deferred if the system is under heavy load RIGHT NOW.
"""
import psutil

CPU_BUSY_THRESHOLD = 70.0        # percent
IO_WAIT_BUSY_THRESHOLD = 15.0    # percent


def read_system_load(sample_seconds: float = 0.5):
    cpu = psutil.cpu_percent(interval=sample_seconds)
    try:
        times = psutil.cpu_times_percent(interval=None)
        io_wait = getattr(times, "iowait", 0.0)  # only present on Linux
    except Exception:
        io_wait = 0.0
    mem = psutil.virtual_memory().percent
    return {"cpu_percent": cpu, "io_wait_percent": io_wait, "memory_percent": mem}


def is_system_busy(load: dict) -> bool:
    return load["cpu_percent"] >= CPU_BUSY_THRESHOLD or load["io_wait_percent"] >= IO_WAIT_BUSY_THRESHOLD
