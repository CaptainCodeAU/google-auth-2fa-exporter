"""Tests for the decoder module."""

from __future__ import annotations

import base64

import pytest

from google_auth_2fa_exporter.decoder import (
    decode_migration_payload,
    decode_uri,
    extract_base64_payload,
)
from google_auth_2fa_exporter.google_auth_pb2 import MigrationPayload


def _make_payload(*otp_params: dict) -> str:
    """Build a base64-encoded MigrationPayload from dicts of OtpParameters fields."""
    payload = MigrationPayload()
    for params in otp_params:
        otp = payload.otp_parameters.add()
        otp.secret = params.get("secret", b"TESTSECRET")
        otp.name = params.get("name", "user@example.com")
        otp.issuer = params.get("issuer", "ExampleIssuer")
        otp.algorithm = params.get("algorithm", MigrationPayload.SHA1)
        otp.digits = params.get("digits", MigrationPayload.SIX)
        otp.type = params.get("type", MigrationPayload.TOTP)
        otp.counter = params.get("counter", 0)
    return base64.b64encode(payload.SerializeToString()).decode()


class TestExtractBase64Payload:
    def test_raw_base64_passthrough(self) -> None:
        assert extract_base64_payload("SGVsbG8=") == "SGVsbG8="

    def test_migration_uri(self) -> None:
        b64 = _make_payload({})
        uri = f"otpauth-migration://offline?data={b64}"
        assert extract_base64_payload(uri) == b64

    def test_strips_whitespace(self) -> None:
        assert extract_base64_payload("  SGVsbG8=  ") == "SGVsbG8="

    def test_missing_data_param(self) -> None:
        with pytest.raises(ValueError, match="No 'data' parameter"):
            extract_base64_payload("otpauth-migration://offline?foo=bar")


class TestDecodeMigrationPayload:
    def test_single_account(self) -> None:
        b64 = _make_payload({"secret": b"hello", "name": "alice", "issuer": "GitHub"})
        accounts = decode_migration_payload(b64)
        assert len(accounts) == 1
        acct = accounts[0]
        assert acct.name == "alice"
        assert acct.issuer == "GitHub"
        assert acct.algorithm == "SHA1"
        assert acct.digits == 6
        assert acct.otp_type == "totp"
        assert acct.counter == 0
        # Verify the secret is valid base32
        assert len(acct.totp_secret) > 0

    def test_multiple_accounts(self) -> None:
        b64 = _make_payload(
            {"name": "a@test.com", "issuer": "Svc1"},
            {"name": "b@test.com", "issuer": "Svc2"},
        )
        accounts = decode_migration_payload(b64)
        assert len(accounts) == 2
        assert accounts[0].name == "a@test.com"
        assert accounts[1].name == "b@test.com"

    def test_sha256_algorithm(self) -> None:
        b64 = _make_payload({"algorithm": MigrationPayload.SHA256})
        accounts = decode_migration_payload(b64)
        assert accounts[0].algorithm == "SHA256"

    def test_eight_digits(self) -> None:
        b64 = _make_payload({"digits": MigrationPayload.EIGHT})
        accounts = decode_migration_payload(b64)
        assert accounts[0].digits == 8

    def test_hotp_type(self) -> None:
        b64 = _make_payload({"type": MigrationPayload.HOTP, "counter": 42})
        accounts = decode_migration_payload(b64)
        assert accounts[0].otp_type == "hotp"
        assert accounts[0].counter == 42

    def test_unspecified_defaults(self) -> None:
        b64 = _make_payload({
            "algorithm": MigrationPayload.ALGORITHM_UNSPECIFIED,
            "digits": MigrationPayload.DIGIT_COUNT_UNSPECIFIED,
            "type": MigrationPayload.OTP_TYPE_UNSPECIFIED,
        })
        accounts = decode_migration_payload(b64)
        assert accounts[0].algorithm == "SHA1"
        assert accounts[0].digits == 6
        assert accounts[0].otp_type == "totp"

    def test_frozen_dataclass(self) -> None:
        b64 = _make_payload({})
        acct = decode_migration_payload(b64)[0]
        with pytest.raises(AttributeError):
            acct.name = "changed"  # type: ignore[misc]


class TestDecodeUri:
    def test_full_uri(self) -> None:
        b64 = _make_payload({"name": "test", "issuer": "TestCo"})
        uri = f"otpauth-migration://offline?data={b64}"
        accounts = decode_uri(uri)
        assert len(accounts) == 1
        assert accounts[0].issuer == "TestCo"

    def test_raw_base64(self) -> None:
        b64 = _make_payload({"name": "test"})
        accounts = decode_uri(b64)
        assert len(accounts) == 1

    def test_standard_otpauth_totp_uri(self) -> None:
        uri = "otpauth://totp/Example:alice@google.com?secret=JBSWY3DPEHPK3PXP&issuer=Example"
        accounts = decode_uri(uri)
        assert len(accounts) == 1
        acct = accounts[0]
        assert acct.issuer == "Example"
        assert acct.name == "alice@google.com"
        assert acct.totp_secret == "JBSWY3DPEHPK3PXP"
        assert acct.algorithm == "SHA1"
        assert acct.digits == 6
        assert acct.otp_type == "totp"
        assert acct.counter == 0

    def test_standard_otpauth_uri_with_encoded_label(self) -> None:
        uri = "otpauth://totp/Label%20One?secret=JBSWY3DPEHPK3PXP&issuer=Epic%20Games"
        accounts = decode_uri(uri)
        assert len(accounts) == 1
        acct = accounts[0]
        assert acct.issuer == "Epic Games"
        assert acct.name == "Label One"

    def test_standard_otpauth_uri_with_algorithm_and_digits(self) -> None:
        uri = "otpauth://totp/Issuer Alpha:alice@google.com?secret=ZBS3Y3DSEH9K31X1&issuer=Issuer Alpha&digits=8&period=30"
        accounts = decode_uri(uri)
        assert len(accounts) == 1
        acct = accounts[0]
        assert acct.digits == 8
        assert acct.issuer == "Issuer Alpha"
        assert acct.totp_secret == "ZBS3Y3DSEH9K31X1"

    def test_standard_otpauth_uri_with_explicit_sha1(self) -> None:
        uri = "otpauth://totp/acx.io:bank%40cedwqaz.com?secret=DEYCED7XZH3IA42&issuer=acxr.io&algorithm=SHA1&digits=6"
        accounts = decode_uri(uri)
        assert len(accounts) == 1
        acct = accounts[0]
        assert acct.algorithm == "SHA1"
        assert acct.digits == 6
        assert acct.name == "bank@cedwqaz.com"
        assert acct.issuer == "acxr.io"

    def test_standard_otpauth_hotp_uri(self) -> None:
        uri = "otpauth://hotp/Service:user@test.com?secret=JBSWY3DPEHPK3PXP&issuer=Service&counter=5"
        accounts = decode_uri(uri)
        assert len(accounts) == 1
        acct = accounts[0]
        assert acct.otp_type == "hotp"
        assert acct.counter == 5

    def test_standard_otpauth_uri_issuer_from_label(self) -> None:
        """When no issuer param, extract from label prefix."""
        uri = "otpauth://totp/MyService:user@example.com?secret=JBSWY3DPEHPK3PXP"
        accounts = decode_uri(uri)
        assert len(accounts) == 1
        acct = accounts[0]
        assert acct.issuer == "MyService"
        assert acct.name == "user@example.com"

    def test_standard_otpauth_uri_no_issuer(self) -> None:
        """No issuer in param or label prefix → empty issuer."""
        uri = "otpauth://totp/user@example.com?secret=JBSWY3DPEHPK3PXP"
        accounts = decode_uri(uri)
        assert len(accounts) == 1
        acct = accounts[0]
        assert acct.issuer == ""
        assert acct.name == "user@example.com"
