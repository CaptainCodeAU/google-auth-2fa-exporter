"""google_auth_2fa_exporter package.

This package can be used both as a CLI tool and as an importable library.
"""

__version__ = "0.1.0"

from google_auth_2fa_exporter.core import run

__all__ = ["__version__", "run"]
