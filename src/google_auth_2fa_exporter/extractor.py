"""Scan QR code images for Google Authenticator migration URIs."""

from __future__ import annotations

from pathlib import Path

import zxingcpp
from PIL import Image

from google_auth_2fa_exporter.decoder import OtpAccount, decode_uri

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp", ".tiff"}


def scan_image(path: Path) -> list[str]:
    """Read all barcodes from an image file and return URI strings."""
    img = Image.open(path)
    results = zxingcpp.read_barcodes(img)
    return [r.text for r in results if r.text.startswith(("otpauth-migration://", "otpauth://"))]


def scan_directory(directory: Path) -> list[str]:
    """Scan all image files in a directory for migration URIs, deduplicated."""
    uris: list[str] = []
    seen: set[str] = set()
    for path in sorted(directory.iterdir()):
        if path.suffix.lower() in IMAGE_EXTENSIONS and path.is_file():
            for uri in scan_image(path):
                if uri not in seen:
                    seen.add(uri)
                    uris.append(uri)
    return uris


def extract_accounts(path: Path) -> list[OtpAccount]:
    """Scan image(s) at path, decode URIs, and return deduplicated accounts."""
    if path.is_dir():
        uris = scan_directory(path)
    elif path.is_file():
        uris = scan_image(path)
    else:
        raise FileNotFoundError(f"Path not found: {path}")

    accounts: list[OtpAccount] = []
    seen: set[tuple[str, str]] = set()
    for uri in uris:
        for acct in decode_uri(uri):
            key = (acct.issuer, acct.name)
            if key not in seen:
                seen.add(key)
                accounts.append(acct)
    return accounts
