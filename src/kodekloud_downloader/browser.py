"""
Optional browser-based session token extraction via Playwright.

This module allows extracting the HttpOnly ``session-cookie`` directly from
a running Chrome browser via the Chrome DevTools Protocol (CDP).

Usage
-----
1. Close all Chrome windows.
2. Start Chrome with remote debugging enabled:

   - **Windows**: ``chrome.exe --remote-debugging-port=9222``
   - **macOS**::
       /Applications/Google Chrome.app/Contents/MacOS/Google Chrome
       --remote-debugging-port=9222
   - **Linux**: ``google-chrome --remote-debugging-port=9222``

3. Sign in at https://learn.kodekloud.com.
4. Run: ``kodekloud dl --browser -o .``
"""

from __future__ import annotations

import os
import platform
import subprocess
from pathlib import Path
from typing import Optional

BROWSER_AUTH_ENABLED = os.environ.get("KODEKLOUD_USE_BROWSER", "").lower() in (
    "1",
    "true",
    "yes",
)

CDP_PORT = int(os.environ.get("KODEKLOUD_CDP_PORT", "9222"))


def _import_playwright():
    """Lazy-import Playwright; return None if not installed."""
    try:
        from playwright.sync_api import sync_playwright as _sp

        return _sp
    except ImportError:
        return None


def _chrome_default_path() -> Optional[Path]:
    """Return the default Chrome executable path for the current platform."""
    system = platform.system()
    if system == "Windows":
        candidates = [
            Path(os.environ.get("LOCALAPPDATA", ""))
            / "Google"
            / "Chrome"
            / "Application"
            / "chrome.exe",
            Path(os.environ.get("PROGRAMFILES", ""))
            / "Google"
            / "Chrome"
            / "Application"
            / "chrome.exe",
            Path(os.environ.get("PROGRAMFILES(X86)", ""))
            / "Google"
            / "Chrome"
            / "Application"
            / "chrome.exe",
        ]
    elif system == "Darwin":
        candidates = [
            Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
        ]
    elif system == "Linux":
        candidates = [
            Path("/usr/bin/google-chrome"),
            Path("/usr/bin/chromium"),
            Path("/usr/bin/chromium-browser"),
        ]
    else:
        return None

    for path in candidates:
        if path.exists():
            return path
    return None


def launch_chrome_with_debugging(
    port: int = CDP_PORT,
) -> Optional[subprocess.Popen]:
    """Launch Chrome with remote debugging enabled.

    Returns the process handle, or None if Chrome couldn't be launched.
    """
    chrome_path = _chrome_default_path()
    if chrome_path is None:
        return None

    user_data_dir = (
        Path(os.environ.get("LOCALAPPDATA", ".")) / "Temp" / "kodekloud-chrome-profile"
    )
    user_data_dir.mkdir(parents=True, exist_ok=True)

    try:
        proc = subprocess.Popen(
            [
                str(chrome_path),
                f"--remote-debugging-port={port}",
                f"--user-data-dir={user_data_dir}",
                "--no-first-run",
                "--no-default-browser-check",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return proc
    except (OSError, subprocess.SubprocessError):
        return None


def get_session_token_from_browser(
    port: int = CDP_PORT,
    auto_launch: bool = False,
) -> Optional[str]:
    """Extract the ``session-cookie`` from a running Chrome instance via CDP.

    Parameters
    ----------
    port:
        The CDP port to connect to (default 9222).
    auto_launch:
        If True, attempt to launch Chrome with remote debugging if no
        running instance is detected.

    Returns
    -------
    The ``session-cookie`` value, or None if it couldn't be obtained.
    """
    sp = _import_playwright()
    if sp is None:
        print(
            "Playwright is not installed. To use browser-based auth, run:\n"
            "  pip install kodekloud-downloader[browser]"
        )
        return None

    chrome_proc = None

    with sp() as pw:
        # Try connecting to an already-running Chrome instance first
        browser = None
        try:
            browser = pw.chromium.connect_over_cdp(f"http://127.0.0.1:{port}")
        except Exception:
            pass

        # If connection failed and auto_launch is enabled, start Chrome
        if browser is None and auto_launch:
            chrome_proc = launch_chrome_with_debugging(port)
            if chrome_proc is not None:
                import time

                time.sleep(3)
                try:
                    browser = pw.chromium.connect_over_cdp(f"http://127.0.0.1:{port}")
                except Exception:
                    pass

        if browser is None:
            print(
                f"Could not connect to Chrome on port {port}.\n"
                "Please start Chrome with remote debugging enabled:\n"
                "  chrome.exe --remote-debugging-port=9222\n"
                "Then sign in to https://learn.kodekloud.com and try again."
            )
            return None

        # Get the default context (contains the user's existing cookies)
        try:
            context = browser.contexts[0]
        except IndexError:
            browser.close()
            return None

        # Navigate to KodeKloud to ensure the session is active
        page = context.pages[0] if context.pages else context.new_page()
        try:
            page.goto(
                "https://learn.kodekloud.com/user/courses",
                wait_until="networkidle",
                timeout=30000,
            )
        except Exception:
            # Timeout is OK — we might already be on the right page
            pass

        # Extract the session-cookie
        token: Optional[str] = None
        for cookie in context.cookies():
            if cookie["name"] == "session-cookie":
                token = cookie["value"]
                break

        # Cleanup
        if chrome_proc is not None:
            chrome_proc.terminate()
        else:
            browser.close()

        return token
