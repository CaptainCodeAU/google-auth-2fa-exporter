# Google Auth 2FA Exporter

A terminal UI (TUI) application that decodes Google Authenticator export QR codes and lets you view live TOTP codes, then export your secrets to multiple formats.

## Features

- Scan QR code images (single file or entire directory) exported from Google Authenticator
- Paste `otpauth-migration://` URIs directly
- Built-in file browser for selecting images and export directories
- View all decoded accounts in a table with live-updating TOTP codes and countdown timer
- Click any table cell to copy its value to the system clipboard
- Export to:
  - **Apple Passwords CSV** — for import into the macOS Passwords app
  - **Bitwarden CSV** — for import into Bitwarden
  - **Aegis JSON** — for import into Aegis Authenticator
  - **Individual QR code PNGs** — scannable by any authenticator app
- Also usable as a Python library for programmatic access

## Requirements

- Python 3.12
- [uv](https://github.com/astral-sh/uv) package manager

## Installation

```bash
git clone https://github.com/CaptainCodeAU/google_auth_2fa_exporter.git
cd google_auth_2fa_exporter
uv sync
```

## Usage

### Launch the TUI

```bash
uv run google-auth-2fa-exporter
```

Or run directly:

```bash
uv run python main.py
```

### TUI Workflow

1. **Load accounts** using one of two methods:
   - **File/Dir row** — enter a path (or click Browse) to a QR code image or directory of images, then click **Load**
   - **URI row** — paste an `otpauth-migration://offline?data=...` URI, then click **Load**
2. View your accounts and live TOTP codes in the table (codes update every second with a countdown timer)
3. Click any cell to copy its value to the clipboard
4. **Export** — enter an output directory (or click Browse), then click one of:
   - **Apple CSV** — produces `apple_passwords_export.csv` (Title, URL, Username, Password, Notes, OTPAuth)
   - **Bitwarden** — produces `bitwarden_export.csv`
   - **Aegis** — produces `aegis_export.json`
   - **QR Codes** — produces one `Issuer (Account).png` per account
5. Press `Ctrl+Q` to quit

### Keyboard Shortcuts

| Key      | Action                    |
| -------- | ------------------------- |
| `Ctrl+L` | Load accounts             |
| `Ctrl+O` | Browse for file/directory |
| `Ctrl+Q` | Quit                      |

### CLI Flags

```bash
uv run google-auth-2fa-exporter --version
uv run google-auth-2fa-exporter --help
```

### Use as a Library

```python
from google_auth_2fa_exporter import decode_uri, extract_accounts

# From a migration URI
accounts = decode_uri("otpauth-migration://offline?data=...")

# From a QR code image
from pathlib import Path
accounts = extract_accounts(Path("export_qr.png"))

for acct in accounts:
    print(f"{acct.issuer}: {acct.name} — secret: {acct.totp_secret}")
```

## Development

```bash
# Install with dev dependencies
uv sync --group dev

# Run tests
uv run pytest

# Lint
uv run ruff check src/ tests/

# Format
uv run ruff format src/ tests/
```

### Regenerating Protobuf Bindings

If you modify `google_auth.proto`:

```bash
uv run python -m grpc_tools.protoc -I. --python_out=. --mypy_out=. google_auth.proto
cp google_auth_pb2.py google_auth_pb2.pyi src/google_auth_2fa_exporter/
```

## License

MIT
