"""
Optional browser-based session token extraction via Playwright.

This module allows extracting the HttpOnly ``session-cookie`` directly from
a Chrome browser via the Chrome DevTools Protocol (CDP).

Usage
-----
Run with ``--browser`` to auto-launch Chrome, sign in to KodeKloud, and
extract the session token:

    kodekloud dl --browser -o . "https://kodekloud.com/courses/..."

Or start Chrome manually with remote debugging, sign in, then run:

    chrome.exe --remote-debugging-port=9222
    kodekloud dl --browser -o . "https://..."
"""

from __future__ import annotations

import logging
import os
import platform
import subprocess
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

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


def _launch_chrome_with_debugging(port: int) -> Optional[subprocess.Popen]:
    """Launch Chrome with remote debugging enabled and a temporary profile.

    Returns the process handle or None on failure.
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


def _extract_session_cookie(context) -> Optional[str]:
    """Extract the ``session-cookie`` from the Playwright browser context."""
    for cookie in context.cookies():
        if cookie["name"] == "session-cookie":
            return cookie["value"]
    return None


def get_session_token_from_browser(
    port: int = CDP_PORT,
    auto_launch: bool = False,
) -> Optional[str]:
    """Extract the ``session-cookie`` from a Chrome browser via CDP.

    Tries connecting to a running Chrome instance first. If that fails
    and ``auto_launch`` is enabled, starts a new Chrome with remote
    debugging and guides the user through sign-in.

    Parameters
    ----------
    port:
        The CDP port to connect to.
    auto_launch:
        If True, launch Chrome with remote debugging if no running
        instance is detected.

    Returns
    -------
    The ``session-cookie`` value, or None.
    """
    sp = _import_playwright()
    if sp is None:
        print(
            "Playwright is not installed. To use browser-based auth:\n"
            "  pip install kodekloud-downloader[browser]"
        )
        return None

    chrome_proc = None
    browser = None

    with sp() as pw:
        # --- Step 1: try connecting to a running Chrome ---
        try:
            browser = pw.chromium.connect_over_cdp(f"http://127.0.0.1:{port}")
            logger.info("Connected to running Chrome on port %d", port)
        except Exception:
            pass

        # --- Step 2: auto-launch if needed ---
        if browser is None and auto_launch:
            # Use a separate port so it doesn't conflict with manual Chrome
            auto_port = (
                port + 1
                if port == int(os.environ.get("KODEKLOUD_CDP_PORT", "9222"))
                else port
            )
            logger.info(
                "Launching Chrome with remote debugging on port %d...", auto_port
            )
            chrome_proc = _launch_chrome_with_debugging(auto_port)
            if chrome_proc is not None:
                for _ in range(5):  # retry up to 5 times (~10s)
                    time.sleep(2)
                    try:
                        browser = pw.chromium.connect_over_cdp(
                            f"http://127.0.0.1:{auto_port}"
                        )
                        logger.info("Chrome launched and connected")
                        break
                    except Exception:
                        logger.debug("Waiting for Chrome CDP on port %d...", auto_port)
                        continue

        if browser is None:
            print(
                "Could not connect to Chrome. Please start Chrome with:\n"
                f"  chrome.exe --remote-debugging-port={port}\n"
                "Then sign in to https://learn.kodekloud.com and try again."
            )
            return None

        # --- Step 3: navigate to KodeKloud courses ---
        try:
            context = browser.contexts[0]
        except IndexError:
            browser.close()
            return None

        page = context.pages[0] if context.pages else context.new_page()

        # Check if we already have the cookie (connecting to existing browser)
        token = _extract_session_cookie(context)
        if token:
            logger.info("Session token found in existing cookies")
            if chrome_proc is not None:
                chrome_proc.terminate()
            else:
                browser.close()
            return token

        # Navigate to KodeKloud
        logger.info("Navigating to KodeKloud...")
        try:
            page.goto(
                "https://learn.kodekloud.com/user/courses",
                wait_until="networkidle",
                timeout=30000,
            )
        except Exception:
            pass

        # Small pause for SPA redirects
        time.sleep(2)

        # Check again after navigation
        token = _extract_session_cookie(context)
        if token:
            logger.info("Session token obtained after navigation")
            if chrome_proc is not None:
                chrome_proc.terminate()
            else:
                browser.close()
            return token

        # --- Step 4: if not logged in, prompt user ---
        current_url = page.url.lower()

        if all(
            word not in current_url for word in ["sign-in", "login", "auth", "signin"]
        ):
            # If we're not on a login page, try navigating to the login page
            try:
                page.goto(
                    "https://identity.kodekloud.com/sign-in",
                    wait_until="networkidle",
                    timeout=15000,
                )
            except Exception:
                pass

        print(
            "Please sign in to KodeKloud in the opened browser window, "
            "then press Enter here..."
        )
        try:
            input()
        except (EOFError, KeyboardInterrupt):
            pass

        # Wait for redirect after login
        time.sleep(4)
        try:
            page.goto(
                "https://learn.kodekloud.com/user/courses",
                wait_until="networkidle",
                timeout=30000,
            )
        except Exception:
            pass
        time.sleep(2)

        # --- Step 5: final extraction attempt ---
        token = _extract_session_cookie(context)
        # Also try waiting a bit more for async cookie setting
        if token is None:
            time.sleep(3)
            token = _extract_session_cookie(context)

        # Cleanup
        if chrome_proc is not None:
            chrome_proc.terminate()
        else:
            browser.close()

        if token:
            logger.info("Session token extracted successfully")
        else:
            print(
                "Could not find session-cookie. Ensure you are signed in to KodeKloud."
            )

        return token

        # --- Step 4: if not logged in, prompt user ---
        current_url = page.url
        if "sign-in" in current_url.lower() or "login" in current_url.lower():
            print(
                "Please sign in to KodeKloud in the opened browser window, "
                "then press Enter here..."
            )
            try:
                input()
            except (EOFError, KeyboardInterrupt):
                pass

            # Wait a moment for redirect after login
            time.sleep(3)
            try:
                page.goto(
                    "https://learn.kodekloud.com/user/courses",
                    wait_until="networkidle",
                    timeout=30000,
                )
            except Exception:
                pass

        # --- Step 5: final extraction attempt ---
        token = _extract_session_cookie(context)

        # Cleanup
        if chrome_proc is not None:
            chrome_proc.terminate()
        else:
            browser.close()

        if token:
            logger.info("Session token extracted successfully")
        else:
            print(
                "Could not find session-cookie. Ensure you are signed in to KodeKloud."
            )

        return token
