"""Tests for the Textual TUI."""

from __future__ import annotations

import base64
from pathlib import Path

import pytest
import qrcode

from google_auth_2fa_exporter.google_auth_pb2 import MigrationPayload
from google_auth_2fa_exporter.ui import (
    DirPickerScreen,
    FilePickerScreen,
    GoogleAuthApp,
)


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


@pytest.mark.asyncio
async def test_browse_btn_opens_file_picker(tmp_path: Path) -> None:
    """Clicking the Browse button opens the FilePickerScreen modal."""
    app = GoogleAuthApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.click("#browse-btn")
        await pilot.pause()
        assert isinstance(app.screen, FilePickerScreen)


@pytest.mark.asyncio
async def test_file_picker_select_populates_input(tmp_path: Path) -> None:
    """Selecting a file in the picker and clicking Select populates the file input."""
    img = qrcode.make("otpauth://totp/Test:u@t.com?secret=JBSWY3DPEHPK3PXP&issuer=Test")
    img_path = tmp_path / "test.png"
    img.save(img_path)

    app = GoogleAuthApp()
    async with app.run_test(size=(120, 40)) as pilot:
        # Set file input so Browse starts in our temp dir
        app.query_one("#file-input").value = str(tmp_path)

        await pilot.click("#browse-btn")
        await pilot.pause()

        screen = app.screen
        assert isinstance(screen, FilePickerScreen)

        tree = screen.query_one("#picker-tree")

        # Wait for tree to load
        for _ in range(5):
            await pilot.pause()

        # Find the test.png node and select it
        file_node = None
        for child in tree.root.children:
            if hasattr(child.data, "path") and child.data.path == img_path:
                file_node = child
                break
        assert file_node is not None, "test.png not found in tree"

        tree.select_node(file_node)
        await pilot.pause()

        # The FileSelected handler should have set _selected_path
        assert screen._selected_path == img_path

        # Click Select to dismiss
        await pilot.click("#btn-pick-ok")
        await pilot.pause()

        # Should be back on main screen with file input populated
        assert not isinstance(app.screen, FilePickerScreen)
        assert app.query_one("#file-input").value == str(img_path)


@pytest.mark.asyncio
async def test_file_picker_cancel_leaves_input_empty() -> None:
    """Clicking Cancel in the file picker does not change the file input."""
    app = GoogleAuthApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.click("#browse-btn")
        await pilot.pause()
        assert isinstance(app.screen, FilePickerScreen)

        await pilot.click("#btn-pick-cancel")
        await pilot.pause()

        assert not isinstance(app.screen, FilePickerScreen)
        assert app.query_one("#file-input").value == ""


@pytest.mark.asyncio
async def test_browse_export_btn_opens_dir_picker() -> None:
    """Clicking the export Browse button opens the DirPickerScreen modal."""
    app = GoogleAuthApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.click("#browse-export-btn")
        await pilot.pause()
        assert isinstance(app.screen, DirPickerScreen)
