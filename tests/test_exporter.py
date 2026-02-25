"""Tests for the exporter module."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from google_auth_2fa_exporter.decoder import OtpAccount
from google_auth_2fa_exporter.exporter import (
    _build_otpauth_uri,
    _sanitize_filename,
    export_aegis_json,
    export_apple_passwords_csv,
    export_bitwarden_csv,
    export_qr_codes,
)

SAMPLE_ACCOUNTS = [
    OtpAccount(
        name="alice@example.com",
        issuer="GitHub",
        totp_secret="JBSWY3DPEHPK3PXP",
        algorithm="SHA1",
        digits=6,
        otp_type="totp",
        counter=0,
    ),
    OtpAccount(
        name="bob@example.com",
        issuer="Google",
        totp_secret="NBSWY3DP",
        algorithm="SHA256",
        digits=8,
        otp_type="totp",
        counter=0,
    ),
]


class TestBuildOtpauthUri:
    def test_totp_uri(self) -> None:
        uri = _build_otpauth_uri(SAMPLE_ACCOUNTS[0])
        assert uri.startswith("otpauth://totp/")
        assert "secret=JBSWY3DPEHPK3PXP" in uri
        assert "issuer=GitHub" in uri
        assert "algorithm=SHA1" in uri
        assert "digits=6" in uri
        assert "period=30" in uri

    def test_hotp_uri(self) -> None:
        acct = OtpAccount(
            name="test",
            issuer="Svc",
            totp_secret="ABCD",
            algorithm="SHA1",
            digits=6,
            otp_type="hotp",
            counter=5,
        )
        uri = _build_otpauth_uri(acct)
        assert uri.startswith("otpauth://hotp/")
        assert "counter=5" in uri
        assert "period" not in uri


class TestSanitizeFilename:
    def test_strips_illegal_chars(self) -> None:
        assert _sanitize_filename('a<b>c:d"e') == "a_b_c_d_e"

    def test_strips_leading_dots(self) -> None:
        assert _sanitize_filename("...hidden") == "hidden"


class TestExportBitwardenCsv:
    def test_writes_csv(self, tmp_path: Path) -> None:
        path = export_bitwarden_csv(SAMPLE_ACCOUNTS, tmp_path)
        assert path.exists()
        assert path.name == "bitwarden_export.csv"
        with open(path) as f:
            reader = csv.reader(f)
            rows = list(reader)
        assert rows[0][0] == "folder"
        assert len(rows) == 3  # header + 2 accounts
        assert "GitHub (alice@example.com)" == rows[1][3]
        assert "otpauth://totp/" in rows[1][10]


class TestExportApplePasswordsCsv:
    def test_writes_csv(self, tmp_path: Path) -> None:
        path = export_apple_passwords_csv(SAMPLE_ACCOUNTS, tmp_path)
        assert path.exists()
        assert path.name == "apple_passwords_export.csv"
        with open(path) as f:
            reader = csv.reader(f)
            rows = list(reader)
        assert rows[0] == [
            "Title",
            "URL",
            "Username",
            "Password",
            "Notes",
            "OTPAuth",
        ]
        assert len(rows) == 3
        assert rows[1][0] == "GitHub (alice@example.com)"
        assert rows[1][2] == "alice@example.com"
        assert "otpauth://totp/" in rows[1][5]
        assert "period=30" in rows[1][5]

    def test_no_issuer(self, tmp_path: Path) -> None:
        acct = OtpAccount(
            name="user@test.com",
            issuer="",
            totp_secret="ABCD",
            algorithm="SHA1",
            digits=6,
            otp_type="totp",
            counter=0,
        )
        path = export_apple_passwords_csv([acct], tmp_path)
        with open(path) as f:
            reader = csv.reader(f)
            rows = list(reader)
        assert rows[1][0] == "user@test.com"


class TestExportAegisJson:
    def test_writes_json(self, tmp_path: Path) -> None:
        path = export_aegis_json(SAMPLE_ACCOUNTS, tmp_path)
        assert path.exists()
        with open(path) as f:
            data = json.load(f)
        assert data["version"] == 2
        entries = data["db"]["entries"]
        assert len(entries) == 2
        assert entries[0]["issuer"] == "GitHub"
        assert entries[0]["info"]["secret"] == "JBSWY3DPEHPK3PXP"
        assert entries[1]["info"]["algo"] == "SHA256"


class TestExportQrCodes:
    def test_generates_images(self, tmp_path: Path) -> None:
        paths = export_qr_codes(SAMPLE_ACCOUNTS, tmp_path)
        assert len(paths) == 2
        for p in paths:
            assert p.exists()
            assert p.suffix == ".png"

    def test_filename_format(self, tmp_path: Path) -> None:
        paths = export_qr_codes(SAMPLE_ACCOUNTS[:1], tmp_path)
        assert paths[0].stem == "GitHub (alice@example.com)"
