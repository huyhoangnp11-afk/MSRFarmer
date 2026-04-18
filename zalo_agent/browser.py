from __future__ import annotations

import os
import re
import subprocess
import time
import winreg
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.edge.options import Options
from selenium.webdriver.edge.service import Service

from .config import PROFILE_DIR, PROFILE_NAME


class BrowserLaunchError(RuntimeError):
    """Raised when Edge could not be launched."""


def _parse_version(version: str) -> tuple[int, ...]:
    parts = re.findall(r"\d+", version or "")
    return tuple(int(part) for part in parts[:4]) if parts else (0,)


def get_edge_version() -> str:
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Edge\BLBeacon",
        )
        version, _ = winreg.QueryValueEx(key, "version")
        winreg.CloseKey(key)
        return str(version)
    except OSError:
        return "0.0.0.0"


def find_edge_binary() -> str:
    candidates = [
        Path(os.environ.get("PROGRAMFILES(X86)", "")) / "Microsoft/Edge/Application/msedge.exe",
        Path(os.environ.get("PROGRAMFILES", "")) / "Microsoft/Edge/Application/msedge.exe",
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    raise BrowserLaunchError("Could not locate msedge.exe on this machine.")


def find_cached_driver_path(edge_version: str) -> str | None:
    cache_root = Path.home() / ".cache" / "selenium" / "msedgedriver" / "win64"
    if not cache_root.exists():
        return None

    versions = sorted(
        [path for path in cache_root.iterdir() if path.is_dir()],
        key=lambda item: _parse_version(item.name),
        reverse=True,
    )
    edge_tuple = _parse_version(edge_version)

    for version_path in versions:
        driver_path = version_path / "msedgedriver.exe"
        if driver_path.exists() and version_path.name == edge_version:
            return str(driver_path)

    for version_path in versions:
        driver_path = version_path / "msedgedriver.exe"
        if not driver_path.exists():
            continue
        if _parse_version(version_path.name)[:1] == edge_tuple[:1]:
            return str(driver_path)

    for version_path in versions:
        driver_path = version_path / "msedgedriver.exe"
        if driver_path.exists():
            return str(driver_path)
    return None


def create_edge_driver(headless: bool = False) -> webdriver.Edge:
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    (PROFILE_DIR / PROFILE_NAME).mkdir(parents=True, exist_ok=True)
    _terminate_profile_edge_processes()
    _cleanup_stale_profile_locks()

    options = Options()
    options.binary_location = find_edge_binary()
    options.add_argument(f"user-data-dir={PROFILE_DIR}")
    options.add_argument(f"profile-directory={PROFILE_NAME}")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-infobars")
    options.add_argument("--no-first-run")
    options.add_argument("--no-default-browser-check")
    options.add_argument("--remote-debugging-port=0")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    if headless:
        options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1400,1000")
    else:
        options.add_argument("--start-maximized")

    edge_version = get_edge_version()
    service = None
    cached_driver = find_cached_driver_path(edge_version)
    if cached_driver:
        service = Service(cached_driver)

    try:
        driver = webdriver.Edge(service=service, options=options)
        driver.set_page_load_timeout(45)
        driver.set_script_timeout(30)
        return driver
    except Exception as exc:
        raise BrowserLaunchError(str(exc)) from exc


def _cleanup_stale_profile_locks() -> None:
    lock_candidates = [
        PROFILE_DIR / "lockfile",
        PROFILE_DIR / "SingletonLock",
        PROFILE_DIR / "SingletonCookie",
        PROFILE_DIR / "SingletonSocket",
        PROFILE_DIR / PROFILE_NAME / "LOCK",
    ]
    for path in lock_candidates:
        try:
            if path.exists():
                path.unlink()
        except OSError:
            continue


def _terminate_profile_edge_processes() -> None:
    profile_marker = str(PROFILE_DIR).replace("'", "''").lower()
    command = (
        f"$profileMarker = '{profile_marker}'; "
        "Get-CimInstance Win32_Process -Filter \"name = 'msedge.exe'\" -ErrorAction SilentlyContinue | "
        "Where-Object { $_.CommandLine -and $_.CommandLine.ToLower().Contains($profileMarker) } | "
        "ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
    )
    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", command],
            capture_output=True,
            timeout=15,
            check=False,
        )
        time.sleep(1.0)
    except Exception:
        pass
