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
