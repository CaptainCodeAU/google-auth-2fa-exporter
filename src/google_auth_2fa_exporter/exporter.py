"""Export OTP accounts to various formats."""

from __future__ import annotations

import csv
import json
import re
import uuid
from pathlib import Path
from urllib.parse import quote

import qrcode

from google_auth_2fa_exporter.decoder import OtpAccount


def _build_otpauth_uri(acct: OtpAccount) -> str:
    """Build a standard otpauth:// URI from an OtpAccount."""
    otp_type = acct.otp_type
    label = quote(f"{acct.issuer}:{acct.name}", safe=":")
    params = {
        "secret": acct.totp_secret,
        "issuer": acct.issuer,
        "algorithm": acct.algorithm,
        "digits": str(acct.digits),
    }
    if otp_type == "hotp":
        params["counter"] = str(acct.counter)
    if otp_type == "totp":
        params["period"] = "30"
    query = "&".join(f"{k}={quote(v)}" for k, v in params.items())
    return f"otpauth://{otp_type}/{label}?{query}"


def _sanitize_filename(name: str) -> str:
    """Strip characters that are illegal in file paths."""
    return re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name).strip(". ")


def _display_name(acct: OtpAccount) -> str:
    """Build a display name like 'Issuer (account)'."""
    if acct.issuer:
        return f"{acct.issuer} ({acct.name})"
    return acct.name


def export_bitwarden_csv(
    accounts: list[OtpAccount], output_path: Path
) -> Path:
    """Write accounts as a Bitwarden-importable CSV."""
    output_path.mkdir(parents=True, exist_ok=True)
    filepath = output_path / "bitwarden_export.csv"
    with open(filepath, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "folder",
                "favorite",
                "type",
                "name",
                "notes",
                "fields",
                "reprompt",
                "login_uri",
                "login_username",
                "login_password",
                "login_totp",
            ]
        )
        for acct in accounts:
            uri = _build_otpauth_uri(acct)
            writer.writerow(
                [
                    "",
                    "",
                    "1",
                    _display_name(acct),
                    "",
                    "",
                    "",
                    "",
                    acct.name,
                    "",
                    uri,
                ]
            )
    return filepath


def export_apple_passwords_csv(
    accounts: list[OtpAccount], output_path: Path
) -> Path:
    """Write accounts as an Apple Passwords-importable CSV.

    Format: Title,URL,Username,Password,Notes,OTPAuth
    """
    output_path.mkdir(parents=True, exist_ok=True)
    filepath = output_path / "apple_passwords_export.csv"
    with open(filepath, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            ["Title", "URL", "Username", "Password", "Notes", "OTPAuth"]
        )
        for acct in accounts:
            uri = _build_otpauth_uri(acct)
            writer.writerow(
                [_display_name(acct), "", acct.name, "", "", uri]
            )
    return filepath


def export_aegis_json(
    accounts: list[OtpAccount], output_path: Path
) -> Path:
    """Write accounts as an Aegis-format unencrypted JSON vault."""
    output_path.mkdir(parents=True, exist_ok=True)
    filepath = output_path / "aegis_export.json"
    entries = []
    for acct in accounts:
        entry = {
            "type": acct.otp_type,
            "uuid": str(uuid.uuid4()),
            "name": acct.name,
            "issuer": acct.issuer,
            "info": {
                "secret": acct.totp_secret,
                "algo": acct.algorithm,
                "digits": acct.digits,
                "period": 30,
            },
        }
        if acct.otp_type == "hotp":
            entry["info"]["counter"] = acct.counter
        entries.append(entry)

    vault = {
        "version": 2,
        "header": {"slots": None, "params": None},
        "db": {"version": 3, "entries": entries},
    }
    with open(filepath, "w") as f:
        json.dump(vault, f, indent=2)
    return filepath


def export_qr_codes(
    accounts: list[OtpAccount], output_path: Path
) -> list[Path]:
    """Generate individual QR code PNG images for each account."""
    output_path.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for acct in accounts:
        uri = _build_otpauth_uri(acct)
        safe_name = _sanitize_filename(_display_name(acct))
        filepath = output_path / f"{safe_name}.png"
        img = qrcode.make(uri)
        img.save(filepath)
        paths.append(filepath)
    return paths
