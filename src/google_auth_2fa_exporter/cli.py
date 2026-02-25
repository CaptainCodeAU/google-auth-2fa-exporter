"""Command-line interface for google_auth_2fa_exporter."""

import sys

from google_auth_2fa_exporter import __version__


def main() -> int:
    """CLI entry point.

    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    if len(sys.argv) > 1 and sys.argv[1] in ("--version", "-v"):
        print(f"google-auth-2fa-exporter version {__version__}")
        return 0

    if len(sys.argv) > 1 and sys.argv[1] in ("--help", "-h"):
        print("google-auth-2fa-exporter - Google Authenticator 2FA Exporter TUI")
        print(f"Version: {__version__}")
        print("\nUsage: google-auth-2fa-exporter [options]")
        print("\nOptions:")
        print("  --version, -v    Show version")
        print("  --help, -h       Show this help message")
        return 0

    from google_auth_2fa_exporter.ui import GoogleAuthApp

    app = GoogleAuthApp()
    app.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
