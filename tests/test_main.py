"""Tests for the CLI and package exports."""

import sys

import pytest

from google_auth_2fa_exporter import OtpAccount, __version__, decode_uri
from google_auth_2fa_exporter.cli import main


def test_version() -> None:
    """Test version is defined."""
    assert __version__ == "0.1.0"


def test_exports() -> None:
    """Test that expected symbols are exported from the package."""
    assert OtpAccount is not None
    assert decode_uri is not None


def test_cli_version(capsys: pytest.CaptureFixture[str]) -> None:
    """Test CLI version flag."""
    sys.argv = ["google-auth-2fa-exporter", "--version"]
    exit_code = main()
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "0.1.0" in captured.out


def test_cli_help(capsys: pytest.CaptureFixture[str]) -> None:
    """Test CLI help flag."""
    sys.argv = ["google-auth-2fa-exporter", "--help"]
    exit_code = main()
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Usage" in captured.out
