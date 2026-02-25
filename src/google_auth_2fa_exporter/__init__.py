"""google_auth_2fa_exporter package.

This package can be used both as a CLI tool and as an importable library.
"""

__version__ = "0.1.0"

from google_auth_2fa_exporter.decoder import OtpAccount, decode_uri
from google_auth_2fa_exporter.extractor import extract_accounts

__all__ = ["OtpAccount", "__version__", "decode_uri", "extract_accounts"]
