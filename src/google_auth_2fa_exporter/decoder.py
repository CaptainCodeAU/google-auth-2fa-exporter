"""Decode Google Authenticator migration payloads into OTP account data."""

from __future__ import annotations

import base64
import hashlib
from dataclasses import dataclass
from urllib.parse import parse_qs, unquote, urlparse

from google_auth_2fa_exporter.google_auth_pb2 import MigrationPayload

ALGORITHM_MAP: dict[int, str] = {
    MigrationPayload.ALGORITHM_UNSPECIFIED: "SHA1",
    MigrationPayload.SHA1: "SHA1",
    MigrationPayload.SHA256: "SHA256",
    MigrationPayload.SHA512: "SHA512",
    MigrationPayload.MD5: "MD5",
}

DIGIT_COUNT_MAP: dict[int, int] = {
    MigrationPayload.DIGIT_COUNT_UNSPECIFIED: 6,
    MigrationPayload.SIX: 6,
    MigrationPayload.EIGHT: 8,
    MigrationPayload.SEVEN: 7,
}

OTP_TYPE_MAP: dict[int, str] = {
    MigrationPayload.OTP_TYPE_UNSPECIFIED: "totp",
    MigrationPayload.HOTP: "hotp",
    MigrationPayload.TOTP: "totp",
}

HASH_MAP: dict[str, type] = {
    "SHA1": hashlib.sha1,
    "SHA256": hashlib.sha256,
    "SHA512": hashlib.sha512,
    "MD5": hashlib.md5,
}


@dataclass(frozen=True)
class OtpAccount:
    name: str
    issuer: str
    totp_secret: str
    algorithm: str
    digits: int
    otp_type: str
    counter: int


def extract_base64_payload(uri: str) -> str:
    """Extract base64 payload from an otpauth-migration URI or raw base64."""
    uri = uri.strip()
    if uri.startswith("otpauth-migration://"):
        parsed = urlparse(uri)
        params = parse_qs(parsed.query)
        data_list = params.get("data")
        if not data_list:
            raise ValueError("No 'data' parameter found in migration URI")
        return unquote(data_list[0])
    return uri


def decode_migration_payload(base64_data: str) -> list[OtpAccount]:
    """Decode a base64-encoded MigrationPayload into OtpAccount objects."""
    raw = base64.b64decode(base64_data)
    payload = MigrationPayload()
    payload.ParseFromString(raw)

    accounts: list[OtpAccount] = []
    for otp in payload.otp_parameters:
        secret_b32 = base64.b32encode(otp.secret).decode("ascii").rstrip("=")
        accounts.append(
            OtpAccount(
                name=otp.name,
                issuer=otp.issuer,
                totp_secret=secret_b32,
                algorithm=ALGORITHM_MAP.get(otp.algorithm, "SHA1"),
                digits=DIGIT_COUNT_MAP.get(otp.digits, 6),
                otp_type=OTP_TYPE_MAP.get(otp.type, "totp"),
                counter=otp.counter,
            )
        )
    return accounts


def decode_uri(uri: str) -> list[OtpAccount]:
    """Decode an otpauth-migration URI (or raw base64) into OtpAccount objects."""
    b64 = extract_base64_payload(uri)
    return decode_migration_payload(b64)
