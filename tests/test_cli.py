from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from kodekloud_downloader.cli import kodekloud


def test_cli_help():
    runner = CliRunner()
    result = runner.invoke(kodekloud, ["--help"])
    assert result.exit_code == 0
    assert "dl" in result.output
    assert "dl-quiz" in result.output or "dl_quiz" in result.output


def test_cli_dl_help():
    runner = CliRunner()
    result = runner.invoke(kodekloud, ["dl", "--help"])
    assert result.exit_code == 0
    assert "--quality" in result.output
    assert "--cookie" in result.output
    assert "--browser" in result.output
    assert "--token" in result.output
    assert "--search" in result.output
    assert "--filter" in result.output


def test_cli_missing_auth():
    runner = CliRunner()
    result = runner.invoke(
        kodekloud, ["dl", "https://kodekloud.com/courses/test-course"]
    )
    assert result.exit_code != 0
    assert "Either --cookie, --browser, or --token must be provided" in result.output


def test_cli_forwards_cookie_to_download_course():
    runner = CliRunner()
    fake_jwt = (
        "eyJhbGciOiJSUzI1NiJ9."
        "eyJpc3MiOiJodHRwczovL3NlY3VyZXRva2VuLmdvb2dsZS5jb20vcHJvZHVjdC12MyJ9."
        "signature"
    )
    with patch("kodekloud_downloader.cli.parse_course_from_url") as mock_parse, patch(
        "kodekloud_downloader.cli.download_course"
    ) as mock_dl, patch(
        "kodekloud_downloader.helpers.parse_token", return_value=fake_jwt
    ):
        mock_course = MagicMock()
        mock_parse.return_value = mock_course

        # Invoke CLI with --cookie
        result = runner.invoke(
            kodekloud,
            [
                "dl",
                "--cookie",
                "cookies.txt",
                "https://kodekloud.com/courses/docker-basics",
            ],
        )
        assert result.exit_code == 0
        assert mock_dl.called
        call_kwargs = mock_dl.call_args[1]
        assert call_kwargs.get("cookie") == "cookies.txt"
        assert call_kwargs.get("session_token") == fake_jwt


def test_cli_cookie_triggers_exchange_when_needed():
    runner = CliRunner()
    with patch("kodekloud_downloader.cli.parse_course_from_url") as mock_parse, patch(
        "kodekloud_downloader.cli.download_course"
    ) as mock_dl, patch(
        "kodekloud_downloader.helpers.parse_token",
        return_value="_secure-user-session-val",
    ), patch(
        "kodekloud_downloader.browser.get_token_from_cookie_file",
        return_value="eyJexchanged_jwt",
    ):
        mock_course = MagicMock()
        mock_parse.return_value = mock_course

        result = runner.invoke(
            kodekloud,
            [
                "dl",
                "--cookie",
                "cookies.txt",
                "https://kodekloud.com/courses/docker-basics",
            ],
        )
        assert result.exit_code == 0
        assert mock_dl.called
        call_kwargs = mock_dl.call_args[1]
        assert call_kwargs.get("cookie") == "cookies.txt"
        assert call_kwargs.get("session_token") == "eyJexchanged_jwt"


def test_cli_supports_token_option():
    runner = CliRunner()
    with patch("kodekloud_downloader.cli.parse_course_from_url") as mock_parse, patch(
        "kodekloud_downloader.cli.download_course"
    ) as mock_dl:
        mock_course = MagicMock()
        mock_parse.return_value = mock_course

        result = runner.invoke(
            kodekloud,
            [
                "dl",
                "--token",
                "my_direct_jwt_token",
                "https://kodekloud.com/courses/docker-basics",
            ],
        )
        assert result.exit_code == 0
        assert mock_dl.called
        call_kwargs = mock_dl.call_args[1]
        assert call_kwargs.get("session_token") == "my_direct_jwt_token"


def test_cli_forwards_search_to_select_courses():
    runner = CliRunner()
    with patch("kodekloud_downloader.cli.collect_all_courses") as mock_collect, patch(
        "kodekloud_downloader.cli.select_courses"
    ) as mock_select, patch("kodekloud_downloader.cli.download_course"):
        mock_course = MagicMock()
        mock_collect.return_value = [mock_course]
        mock_select.return_value = [mock_course]

        result = runner.invoke(
            kodekloud,
            [
                "dl",
                "--token",
                "direct_token",
                "--search",
                "cnpe",
            ],
        )
        assert result.exit_code == 0
        assert mock_select.called
        assert mock_select.call_args[1].get("query") == "cnpe"


def test_cli_forwards_category_filter_to_select_courses():
    runner = CliRunner()
    with patch("kodekloud_downloader.cli.collect_all_courses") as mock_collect, patch(
        "kodekloud_downloader.cli.select_courses"
    ) as mock_select, patch("kodekloud_downloader.cli.download_course"):
        mock_course = MagicMock()
        mock_collect.return_value = [mock_course]
        mock_select.return_value = [mock_course]

        result = runner.invoke(
            kodekloud,
            [
                "dl",
                "--token",
                "direct_token",
                "-f",
                "Golden Kubestronaut",
            ],
        )
        assert result.exit_code == 0
        assert mock_select.called
        assert mock_select.call_args[1].get("category") == "Golden Kubestronaut"
