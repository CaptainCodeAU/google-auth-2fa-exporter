"""Tests for the Textual TUI."""

from __future__ import annotations

import base64

import pytest

from google_auth_2fa_exporter.google_auth_pb2 import MigrationPayload
from google_auth_2fa_exporter.ui import GoogleAuthApp


def _make_migration_uri() -> str:
    payload = MigrationPayload()
    otp = payload.otp_parameters.add()
    otp.secret = b"TESTSECRET12"
    otp.name = "testuser@example.com"
    otp.issuer = "TestService"
    otp.algorithm = MigrationPayload.SHA1
    otp.digits = MigrationPayload.SIX
    otp.type = MigrationPayload.TOTP
    b64 = base64.b64encode(payload.SerializeToString()).decode()
    return f"otpauth-migration://offline?data={b64}"


@pytest.mark.asyncio
async def test_app_starts() -> None:
    """Test that the app starts and has expected widgets."""
    app = GoogleAuthApp()
    async with app.run_test():
        assert app.query_one("#accounts-table") is not None
        assert app.query_one("#file-input") is not None
        assert app.query_one("#uri-input") is not None
        assert app.query_one("#load-btn") is not None


@pytest.mark.asyncio
async def test_load_from_uri() -> None:
    """Test loading accounts from a pasted URI."""
    uri = _make_migration_uri()
    app = GoogleAuthApp()
    async with app.run_test() as pilot:
        uri_input = app.query_one("#uri-input")
        uri_input.value = uri
        await pilot.click("#load-uri-btn")
        await pilot.pause()
        assert len(app._accounts) == 1
        assert app._accounts[0].issuer == "TestService"


@pytest.mark.asyncio
async def test_load_empty_shows_warning() -> None:
    """Test that loading with no input shows a warning."""
    app = GoogleAuthApp()
    async with app.run_test() as pilot:
        await pilot.click("#load-btn")
        await pilot.pause()
        assert len(app._accounts) == 0
