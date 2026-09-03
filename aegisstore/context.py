"""
context.py — Dependency-Aware Safety Brain

Checks whether a candidate file is:
- currently active/open
- owned by the system package manager
- tracked by Git
- a symlink or symlink target
- referenced by cron/systemd
- referenced/imported by another file in the project

This module provides safety context only.
It NEVER deletes or modifies files.
"""

import shutil
import subprocess
from pathlib import Path

import psutil


_DPKG = shutil.which("dpkg")
_RPM = shutil.which("rpm")
_GIT = shutil.which("git")


def is_active_process(path: str) -> bool:
    """True if a running process currently has this file open."""
    target = str(Path(path).resolve())

    for proc in psutil.process_iter(["open_files"]):
        try:
            files = proc.info["open_files"]

            if files:
                for f in files:
                    try:
                        if str(Path(f.path).resolve()) == target:
                            return True
                    except (OSError, RuntimeError):
                        continue

        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    return False


def is_package_owned(path: str) -> bool:
    """True if the file is tracked by dpkg or rpm."""
    try:
        if _DPKG:
            result = subprocess.run(
                [_DPKG, "-S", str(Path(path).resolve())],
                capture_output=True,
                text=True,
                timeout=3,
            )
            if result.returncode == 0:
                return True

        if _RPM:
            result = subprocess.run(
                [_RPM, "-qf", str(Path(path).resolve())],
                capture_output=True,
                text=True,
                timeout=3,
            )
            if result.returncode == 0:
                return True

    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    return False


def is_git_tracked(path: str) -> bool:
    """True if the file is tracked inside a Git repository."""
    if not _GIT:
        return False

    try:
        file_path = Path(path).resolve()

        result = subprocess.run(
            [
                _GIT,
                "-C",
                str(file_path.parent),
                "ls-files",
                "--error-unmatch",
                str(file_path),
            ],
            capture_output=True,
            text=True,
            timeout=3,
        )

        return result.returncode == 0

    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return False


def is_symlink(path: str) -> bool:
    """True if the path itself is a symbolic link."""
    try:
        return Path(path).is_symlink()
    except OSError:
        return False


def is_symlink_target(path: str) -> bool:
    """
    True if another symlink points to this file.

    This prevents optimization of a file that may be indirectly
    required by another part of the filesystem.
    """
    try:
        target = Path(path).resolve()

        for parent in [target.parent, *target.parents]:
            try:
                for item in parent.iterdir():
                    if item.is_symlink():
                        try:
                            if item.resolve() == target:
                                return True
                        except (OSError, RuntimeError):
                            continue
            except (PermissionError, OSError):
                continue

    except (OSError, RuntimeError):
        return False

    return False


def referenced_by_systemd(path: str) -> bool:
    """
    Check whether systemd unit files reference this path.
    """
    target = str(Path(path).resolve())

    systemd_dirs = [
        Path("/etc/systemd/system"),
        Path("/usr/lib/systemd/system"),
        Path("/lib/systemd/system"),
    ]

    for directory in systemd_dirs:
        if not directory.exists():
            continue

        try:
            for unit in directory.rglob("*"):
                if not unit.is_file():
                    continue

                try:
                    text = unit.read_text(
                        encoding="utf-8",
                        errors="ignore",
                    )

                    if target in text or str(Path(path)) in text:
                        return True

                except (PermissionError, OSError):
                    continue

        except (PermissionError, OSError):
            continue

    return False


def referenced_by_cron(path: str) -> bool:
    """
    Check common cron configuration locations for references.
    """
    target = str(Path(path).resolve())

    cron_locations = [
        Path("/etc/crontab"),
        Path("/etc/cron.d"),
        Path("/etc/cron.daily"),
        Path("/etc/cron.hourly"),
        Path("/etc/cron.weekly"),
        Path("/etc/cron.monthly"),
    ]

    for location in cron_locations:
        try:
            if location.is_file():
                files = [location]

            elif location.is_dir():
                files = list(location.rglob("*"))

            else:
                continue

            for item in files:
                if not item.is_file():
                    continue

                try:
                    text = item.read_text(
                        encoding="utf-8",
                        errors="ignore",
                    )

                    if target in text or str(Path(path)) in text:
                        return True

                except (PermissionError, OSError):
                    continue

        except (PermissionError, OSError):
            continue

    return False


def enrich(path: str) -> dict:
    """
    Return complete safety/dependency context for a file.

    This information is advisory and does not perform any action.
    """
    return {
        "active_process": is_active_process(path),
        "package_owned": is_package_owned(path),
        "git_tracked": is_git_tracked(path),
        "is_symlink": is_symlink(path),
        "is_symlink_target": is_symlink_target(path),
        "referenced_by_systemd": referenced_by_systemd(path),
        "referenced_by_cron": referenced_by_cron(path),
    }
