from pathlib import Path

import pytest
import requests

from kodekloud_downloader.browser import (
    get_token_from_cookie_file,
    parse_netscape_cookies,
)


def test_parse_netscape_cookies(tmp_path: Path):
    cookie_file = tmp_path / "cookies.txt"
    cookie_file.write_text(
        "# Netscape HTTP Cookie File\n"
        ".kodekloud.com\tTRUE\t/\tTRUE\t1750000000\t_secure-user-session\tabc123xyz\n"
        "kodekloud.com\tFALSE\t/\tFALSE\t0\tsome_cookie\tval\n"
    )
    cookies = parse_netscape_cookies(cookie_file)
    assert len(cookies) == 2
    assert cookies[0]["name"] == "_secure-user-session"
    assert cookies[0]["value"] == "abc123xyz"
    assert cookies[0]["domain"] == ".kodekloud.com"
    assert cookies[0]["secure"] is True


@pytest.mark.skipif(
    not Path("kodekloud.com_cookies.txt").exists(),
    reason="User cookie file kodekloud.com_cookies.txt not present",
)
def test_live_cookie_exchange_and_api_verification():
    """Live test using the user's available kodekloud.com_cookies.txt.

    Verifies that get_token_from_cookie_file exchanges the cookie file for
    a valid Firebase ID token and that the token successfully authenticates
    with learn-api.kodekloud.com.
    """
    token = get_token_from_cookie_file("kodekloud.com_cookies.txt")
    assert token is not None, "Failed to resolve Firebase token from cookie file"
    assert len(token) > 500, f"Token length {len(token)} is suspiciously short"
    assert token.startswith("ey"), (
        "Token does not look like a valid JWT (should start with 'ey')"
    )

    # Query lesson endpoint to verify the token is accepted by KodeKloud API
    url = "https://learn-api.kodekloud.com/api/lessons/259f1db1-29c6-4efa-bab0-2096c40fbba4"
    headers = {"Authorization": f"Bearer {token}"}
    params = {"course_id": "c4f8aa40-d06e-4731-b6bd-4221632df06c"}
    resp = requests.get(url, headers=headers, params=params, timeout=30)
    assert resp.status_code == 200, (
        f"API rejected token with {resp.status_code}: {resp.text[:200]}"
    )
    data = resp.json()
    assert "video_url" in data, f"Response missing video_url: {data}"
    assert "vimeo.com" in data["video_url"]
