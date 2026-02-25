"""Tests for the extractor module (QR image scanning)."""

from __future__ import annotations

import base64
from pathlib import Path

import qrcode

from google_auth_2fa_exporter.extractor import extract_accounts, scan_image
from google_auth_2fa_exporter.google_auth_pb2 import MigrationPayload


def _make_migration_uri(name: str = "user@test.com", issuer: str = "TestCo") -> str:
    """Create an otpauth-migration:// URI with one account."""
    payload = MigrationPayload()
    otp = payload.otp_parameters.add()
    otp.secret = b"TESTSECRET12"
    otp.name = name
    otp.issuer = issuer
    otp.algorithm = MigrationPayload.SHA1
    otp.digits = MigrationPayload.SIX
    otp.type = MigrationPayload.TOTP
    b64 = base64.b64encode(payload.SerializeToString()).decode()
    return f"otpauth-migration://offline?data={b64}"


def _make_qr_image(uri: str, path: Path) -> Path:
    """Generate a QR code image file from a URI string."""
    img = qrcode.make(uri)
    img.save(path)
    return path


class TestScanImage:
    def test_round_trip(self, tmp_path: Path) -> None:
        uri = _make_migration_uri()
        img_path = _make_qr_image(uri, tmp_path / "test.png")
        results = scan_image(img_path)
        assert len(results) == 1
        assert results[0] == uri

    def test_non_otpauth_qr_ignored(self, tmp_path: Path) -> None:
        img_path = _make_qr_image("https://example.com", tmp_path / "url.png")
        results = scan_image(img_path)
        assert results == []

    def test_standard_otpauth_totp_qr(self, tmp_path: Path) -> None:
        uri = "otpauth://totp/GitHub:alice@github.com?secret=JBSWY3DPEHPK3PXP&issuer=GitHub"
        img_path = _make_qr_image(uri, tmp_path / "totp.png")
        results = scan_image(img_path)
        assert len(results) == 1
        assert results[0] == uri


class TestExtractAccounts:
    def test_single_file(self, tmp_path: Path) -> None:
        uri = _make_migration_uri(name="alice", issuer="GitHub")
        _make_qr_image(uri, tmp_path / "code.png")
        accounts = extract_accounts(tmp_path / "code.png")
        assert len(accounts) == 1
        assert accounts[0].name == "alice"
        assert accounts[0].issuer == "GitHub"

    def test_directory(self, tmp_path: Path) -> None:
        uri1 = _make_migration_uri(name="a@test.com", issuer="Svc1")
        uri2 = _make_migration_uri(name="b@test.com", issuer="Svc2")
        _make_qr_image(uri1, tmp_path / "img1.png")
        _make_qr_image(uri2, tmp_path / "img2.png")
        accounts = extract_accounts(tmp_path)
        assert len(accounts) == 2
        names = {a.name for a in accounts}
        assert "a@test.com" in names
        assert "b@test.com" in names

    def test_deduplication(self, tmp_path: Path) -> None:
        uri = _make_migration_uri(name="same@test.com", issuer="Same")
        _make_qr_image(uri, tmp_path / "dup1.png")
        _make_qr_image(uri, tmp_path / "dup2.png")
        accounts = extract_accounts(tmp_path)
        assert len(accounts) == 1

    def test_standard_otpauth_qr_file(self, tmp_path: Path) -> None:
        uri = "otpauth://totp/GitHub:alice@github.com?secret=JBSWY3DPEHPK3PXP&issuer=GitHub"
        _make_qr_image(uri, tmp_path / "totp.png")
        accounts = extract_accounts(tmp_path / "totp.png")
        assert len(accounts) == 1
        assert accounts[0].issuer == "GitHub"
        assert accounts[0].name == "alice@github.com"
        assert accounts[0].totp_secret == "JBSWY3DPEHPK3PXP"

    def test_directory_mixed_migration_and_standard(self, tmp_path: Path) -> None:
        migration_uri = _make_migration_uri(name="a@test.com", issuer="Svc1")
        standard_uri = "otpauth://totp/Svc2:b@test.com?secret=JBSWY3DPEHPK3PXP&issuer=Svc2"
        _make_qr_image(migration_uri, tmp_path / "img1.png")
        _make_qr_image(standard_uri, tmp_path / "img2.png")
        accounts = extract_accounts(tmp_path)
        assert len(accounts) == 2
        names = {a.name for a in accounts}
        assert "a@test.com" in names
        assert "b@test.com" in names

    def test_nonexistent_path(self, tmp_path: Path) -> None:
        import pytest

        with pytest.raises(FileNotFoundError):
            extract_accounts(tmp_path / "nope.png")
