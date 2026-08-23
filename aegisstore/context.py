"""
context.py — Pillar 1 (part 2) / the "Don't Break My System" Brain.
Checks whether a candidate file is in active use, package-owned, or part of a Git repo
before it is ever allowed to be optimized.
"""
import shutil
import subprocess
from pathlib import Path

import psutil

_DPKG = shutil.which("dpkg")
_RPM = shutil.which("rpm")
_GIT = shutil.which("git")


def is_active_process(path: str) -> bool:
    """True if any running process currently has this file open."""
    target = str(Path(path).resolve())
    for proc in psutil.process_iter(["open_files"]):
        try:
            files = proc.info["open_files"]
            if files:
                for f in files:
                    if f.path == target:
                        return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    return False


def is_package_owned(path: str) -> bool:
    """True if the file is tracked by the system package manager (dpkg/rpm)."""
    try:
        if _DPKG:
            r = subprocess.run([_DPKG, "-S", str(path)], capture_output=True, text=True, timeout=3)
            return r.returncode == 0
        if _RPM:
            r = subprocess.run([_RPM, "-qf", str(path)], capture_output=True, text=True, timeout=3)
            return r.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return False


def is_git_tracked(path: str) -> bool:
    """True if the file sits inside a Git working tree and is tracked (or the repo has uncommitted changes)."""
    if not _GIT:
        return False
    try:
        folder = str(Path(path).parent)
        r = subprocess.run([_GIT, "-C", folder, "ls-files", "--error-unmatch", str(path)],
                            capture_output=True, text=True, timeout=3)
        return r.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def enrich(path: str) -> dict:
    return {
        "active_process": is_active_process(path),
        "package_owned": is_package_owned(path),
        "git_tracked": is_git_tracked(path),
    }
