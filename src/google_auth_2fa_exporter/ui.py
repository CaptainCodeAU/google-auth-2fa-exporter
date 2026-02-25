"""Textual TUI for Google Authenticator 2FA Exporter."""

from __future__ import annotations

import time
from collections.abc import Iterable
from pathlib import Path
from typing import ClassVar

import pyotp
import pyperclip
from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import (
    Button,
    DataTable,
    DirectoryTree,
    Footer,
    Header,
    Input,
    Label,
    Static,
)

from google_auth_2fa_exporter.decoder import HASH_MAP, OtpAccount, decode_uri
from google_auth_2fa_exporter.exporter import (
    export_aegis_json,
    export_apple_passwords_csv,
    export_bitwarden_csv,
    export_qr_codes,
)
from google_auth_2fa_exporter.extractor import IMAGE_EXTENSIONS, extract_accounts

# Padding added to the widest value in each column
_COL_PAD = 2


# ---------------------------------------------------------------------------
# File picker modal (images + directories)
# ---------------------------------------------------------------------------


class _ImageDirectoryTree(DirectoryTree):
    """DirectoryTree that only shows image files and directories."""

    ALLOW_SELECT = True

    def filter_paths(self, paths: Iterable[Path]) -> Iterable[Path]:
        return [
            p
            for p in paths
            if p.is_dir() or p.suffix.lower() in IMAGE_EXTENSIONS
        ]


class FilePickerScreen(ModalScreen[Path | None]):
    """Modal file browser for selecting an image file or directory."""

    DEFAULT_CSS = """
    FilePickerScreen {
        align: center middle;
    }
    #picker-dialog {
        width: 80%;
        height: 80%;
        border: heavy $accent;
        background: $surface;
        padding: 1;
    }
    #picker-title {
        text-style: bold;
        margin-bottom: 1;
    }
    #picker-tree {
        height: 1fr;
    }
    #picker-buttons {
        height: auto;
        margin-top: 1;
        align-horizontal: right;
    }
    #picker-buttons Button {
        margin-left: 1;
    }
    #picker-selected {
        margin-top: 1;
        color: $text-muted;
    }
    """

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("escape", "cancel", "Cancel"),
    ]

    def __init__(self, start_path: str | Path = "~") -> None:
        super().__init__()
        self._start = Path(start_path).expanduser().resolve()
        self._selected_path: Path | None = None

    def compose(self) -> ComposeResult:
        with Vertical(id="picker-dialog"):
            yield Label(
                "Select an image file or directory:", id="picker-title"
            )
            yield _ImageDirectoryTree(self._start, id="picker-tree")
            yield Static("No selection", id="picker-selected")
            with Horizontal(id="picker-buttons"):
                yield Button(
                    "Use This Directory",
                    id="btn-pick-dir",
                    variant="default",
                )
                yield Button("Select", id="btn-pick-ok", variant="primary")
                yield Button("Cancel", id="btn-pick-cancel")

    def on_directory_tree_file_selected(
        self, event: DirectoryTree.FileSelected
    ) -> None:
        self._selected_path = event.path
        self.query_one("#picker-selected", Static).update(
            f"File: {event.path}"
        )

    def on_directory_tree_directory_selected(
        self, event: DirectoryTree.DirectorySelected
    ) -> None:
        self._selected_path = event.path
        self.query_one("#picker-selected", Static).update(
            f"Directory: {event.path}"
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-pick-ok":
            self.dismiss(self._selected_path)
        elif event.button.id == "btn-pick-dir":
            tree = self.query_one("#picker-tree", _ImageDirectoryTree)
            self.dismiss(Path(tree.path).resolve())
        elif event.button.id == "btn-pick-cancel":
            self.dismiss(None)

    def action_cancel(self) -> None:
        self.dismiss(None)


# ---------------------------------------------------------------------------
# Directory-only picker modal (for export folder)
# ---------------------------------------------------------------------------


class _DirectoryOnlyTree(DirectoryTree):
    """DirectoryTree that only shows directories (no files)."""

    ALLOW_SELECT = True

    def filter_paths(self, paths: Iterable[Path]) -> Iterable[Path]:
        return [p for p in paths if p.is_dir()]


class DirPickerScreen(ModalScreen[Path | None]):
    """Modal directory browser for selecting an export folder."""

    DEFAULT_CSS = """
    DirPickerScreen {
        align: center middle;
    }
    #dir-picker-dialog {
        width: 80%;
        height: 80%;
        border: heavy $accent;
        background: $surface;
        padding: 1;
    }
    #dir-picker-title {
        text-style: bold;
        margin-bottom: 1;
    }
    #dir-picker-tree {
        height: 1fr;
    }
    #dir-picker-buttons {
        height: auto;
        margin-top: 1;
        align-horizontal: right;
    }
    #dir-picker-buttons Button {
        margin-left: 1;
    }
    #dir-picker-selected {
        margin-top: 1;
        color: $text-muted;
    }
    """

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("escape", "cancel", "Cancel"),
    ]

    def __init__(self, start_path: str | Path = "~") -> None:
        super().__init__()
        self._start = Path(start_path).expanduser().resolve()
        self._selected_path: Path | None = None

    def compose(self) -> ComposeResult:
        with Vertical(id="dir-picker-dialog"):
            yield Label("Select export directory:", id="dir-picker-title")
            yield _DirectoryOnlyTree(self._start, id="dir-picker-tree")
            yield Static("No selection", id="dir-picker-selected")
            with Horizontal(id="dir-picker-buttons"):
                yield Button(
                    "Use This Directory",
                    id="btn-dirpick-use",
                    variant="default",
                )
                yield Button(
                    "Select", id="btn-dirpick-ok", variant="primary"
                )
                yield Button("Cancel", id="btn-dirpick-cancel")

    def on_directory_tree_directory_selected(
        self, event: DirectoryTree.DirectorySelected
    ) -> None:
        self._selected_path = event.path
        self.query_one("#dir-picker-selected", Static).update(
            f"Directory: {event.path}"
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-dirpick-ok":
            self.dismiss(self._selected_path)
        elif event.button.id == "btn-dirpick-use":
            tree = self.query_one("#dir-picker-tree", _DirectoryOnlyTree)
            self.dismiss(Path(tree.path).resolve())
        elif event.button.id == "btn-dirpick-cancel":
            self.dismiss(None)

    def action_cancel(self) -> None:
        self.dismiss(None)


# ---------------------------------------------------------------------------
# Main application
# ---------------------------------------------------------------------------


class GoogleAuthApp(App[None]):
    """TUI application for decoding and exporting Google Authenticator secrets."""

    TITLE = "Google Auth 2FA Exporter"
    CSS = """
    Toast {
        width: 80;
        max-width: 70%;
    }
    #file-row {
        height: 3;
        margin: 1 1 0 1;
    }
    #uri-row {
        height: 3;
        margin: 0 1 1 1;
    }
    #file-row Input, #uri-row Input {
        width: 1fr;
    }
    #file-row Button, #uri-row Button {
        margin-left: 1;
    }
    .input-label {
        width: 10;
        padding: 1 1 0 0;
        text-style: bold;
    }
    #timer-bar {
        height: 1;
        margin: 0 1;
        text-style: bold;
        color: $warning;
    }
    #accounts-table {
        max-height: 50%;
        min-height: 3;
        margin: 0 1;
        border: solid $accent;
    }
    #export-row {
        height: 3;
        margin: 1;
    }
    #export-row Input {
        width: 1fr;
    }
    #export-row Button {
        margin-left: 1;
    }
    """

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("ctrl+q", "quit", "Quit"),
        Binding("ctrl+l", "load_accounts", "Load"),
        Binding("ctrl+o", "browse_file", "Browse"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._accounts: list[OtpAccount] = []

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="file-row"):
            yield Static("File/Dir:", classes="input-label")
            yield Input(
                placeholder="/path/to/qr-code.png or directory",
                id="file-input",
            )
            yield Button("Browse\u2026", id="browse-btn")
            yield Button("Load", id="load-btn", variant="primary")
        with Horizontal(id="uri-row"):
            yield Static("URI:", classes="input-label")
            yield Input(
                placeholder="otpauth-migration://offline?data=\u2026",
                id="uri-input",
            )
            yield Button("Load", id="load-uri-btn", variant="primary")
        yield Static("", id="timer-bar")
        yield DataTable(id="accounts-table")
        with Horizontal(id="export-row"):
            yield Input(
                placeholder="Export directory (required)",
                id="export-dir",
            )
            yield Button("Browse\u2026", id="browse-export-btn")
            yield Button("Apple CSV", id="btn-apple")
            yield Button("Bitwarden", id="btn-bitwarden")
            yield Button("Aegis", id="btn-aegis")
            yield Button("QR Codes", id="btn-qr")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#accounts-table", DataTable)
        table.add_columns(
            ("Issuer", "issuer"),
            ("Account", "account"),
            ("Secret", "secret"),
            ("Code", "code"),
        )
        table.cursor_type = "cell"
        self.set_interval(1.0, self._refresh_codes)
        self._refresh_timer()

    def _get_export_dir(self) -> Path | None:
        raw = self.query_one("#export-dir", Input).value.strip()
        if not raw:
            return None
        return Path(raw).resolve()

    def _seconds_remaining(self) -> int:
        return 30 - int(time.time() % 30)

    def _timer_display(self) -> str:
        remaining = self._seconds_remaining()
        filled = remaining
        empty = 30 - filled
        return (
            " TOTP "
            + "\u2588" * filled
            + "\u2591" * empty
            + f" {remaining:2d}s"
        )

    def _refresh_timer(self) -> None:
        self.query_one("#timer-bar", Static).update(self._timer_display())

    def _auto_size_columns(self) -> None:
        """Resize each column to fit the widest value plus padding."""
        table = self.query_one("#accounts-table", DataTable)
        col_keys = ["issuer", "account", "secret", "code"]
        col_labels = ["Issuer", "Account", "Secret", "Code"]
        for col_key, label in zip(col_keys, col_labels, strict=True):
            max_w = len(label)
            for row_key_obj in table.rows:
                try:
                    val = table.get_cell(row_key_obj, col_key)
                    val_str = val.plain if isinstance(val, Text) else str(val)
                    max_w = max(max_w, len(val_str))
                except Exception:
                    pass
            col_obj = table.columns.get(col_key)
            if col_obj is not None:
                col_obj.width = max_w + _COL_PAD

    def _populate_table(self) -> None:
        table = self.query_one("#accounts-table", DataTable)
        table.clear()
        for acct in self._accounts:
            code_text = Text(self._generate_code(acct), style="bold cyan")
            table.add_row(
                acct.issuer,
                acct.name,
                acct.totp_secret,
                code_text,
                key=f"{acct.issuer}:{acct.name}",
            )
        self._auto_size_columns()

    def _generate_code(self, acct: OtpAccount) -> str:
        try:
            digest = HASH_MAP.get(acct.algorithm, HASH_MAP["SHA1"])
            if acct.otp_type == "hotp":
                hotp = pyotp.HOTP(
                    acct.totp_secret, digest=digest, digits=acct.digits
                )
                return hotp.at(acct.counter)
            totp = pyotp.TOTP(
                acct.totp_secret, digest=digest, digits=acct.digits
            )
            return totp.now()
        except Exception:
            return "------"

    def _refresh_codes(self) -> None:
        self._refresh_timer()
        if not self._accounts:
            return
        table = self.query_one("#accounts-table", DataTable)
        for acct in self._accounts:
            code = self._generate_code(acct)
            code_text = Text(code, style="bold cyan")
            row_key = f"{acct.issuer}:{acct.name}"
            try:
                table.update_cell(row_key, "code", code_text)
            except Exception:
                pass

    # -- cell click to copy -------------------------------------------------

    def on_data_table_cell_selected(
        self, event: DataTable.CellSelected
    ) -> None:
        val = event.value
        text = val.plain if isinstance(val, Text) else str(val)
        if text:
            pyperclip.copy(text)
            self.notify(f"Copied: {text}", severity="information")

    # -- actions & button dispatch ------------------------------------------

    def action_load_accounts(self) -> None:
        self._do_load()

    def action_browse_file(self) -> None:
        self._open_file_picker()

    def _open_file_picker(self) -> None:
        current = self.query_one("#file-input", Input).value.strip()
        start = Path(current) if current else Path.home()
        if start.is_file():
            start = start.parent
        if not start.is_dir():
            start = Path.home()
        self.push_screen(
            FilePickerScreen(start_path=start),
            callback=self._on_file_picked,
        )

    def _on_file_picked(self, path: Path | None) -> None:
        if path is not None:
            self.query_one("#file-input", Input).value = str(path)

    def _open_export_picker(self) -> None:
        current = self.query_one("#export-dir", Input).value.strip()
        start = (
            Path(current)
            if current and Path(current).is_dir()
            else Path.home()
        )
        self.push_screen(
            DirPickerScreen(start_path=start),
            callback=self._on_export_dir_picked,
        )

    def _on_export_dir_picked(self, path: Path | None) -> None:
        if path is not None:
            self.query_one("#export-dir", Input).value = str(path)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn = event.button.id
        if btn == "load-btn":
            self._do_load()
        elif btn == "load-uri-btn":
            self._do_load()
        elif btn == "browse-btn":
            self._open_file_picker()
        elif btn == "browse-export-btn":
            self._open_export_picker()
        elif btn == "btn-apple":
            self._do_export("apple")
        elif btn == "btn-bitwarden":
            self._do_export("bitwarden")
        elif btn == "btn-aegis":
            self._do_export("aegis")
        elif btn == "btn-qr":
            self._do_export("qr")

    def _do_load(self) -> None:
        file_input = self.query_one("#file-input", Input).value.strip()
        uri_input = self.query_one("#uri-input", Input).value.strip()

        try:
            if uri_input:
                self._accounts = decode_uri(uri_input)
            elif file_input:
                self._accounts = extract_accounts(Path(file_input))
            else:
                self.notify(
                    "Enter a file path or paste a URI first.",
                    severity="warning",
                )
                return
            self._populate_table()
            self.notify(
                f"Loaded {len(self._accounts)} account(s).",
                severity="information",
            )
        except Exception as e:
            self.notify(f"Error: {e}", severity="error")

    def _do_export(self, fmt: str) -> None:
        if not self._accounts:
            self.notify("No accounts loaded.", severity="warning")
            return
        export_dir = self._get_export_dir()
        if export_dir is None:
            self.notify(
                "Export directory is required. Enter a path or use Browse.",
                severity="warning",
            )
            return
        try:
            if fmt == "apple":
                path = export_apple_passwords_csv(
                    self._accounts, export_dir
                )
                self.notify(f"Exported to {path}", severity="information")
            elif fmt == "bitwarden":
                path = export_bitwarden_csv(self._accounts, export_dir)
                self.notify(f"Exported to {path}", severity="information")
            elif fmt == "aegis":
                path = export_aegis_json(self._accounts, export_dir)
                self.notify(f"Exported to {path}", severity="information")
            elif fmt == "qr":
                paths = export_qr_codes(self._accounts, export_dir)
                self.notify(
                    f"Exported {len(paths)} QR code(s) to {export_dir}",
                    severity="information",
                )
        except Exception as e:
            self.notify(f"Export error: {e}", severity="error")
