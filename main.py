"""Entry point for running the TUI directly with `python main.py`."""

from google_auth_2fa_exporter.ui import GoogleAuthApp


def main() -> None:
    app = GoogleAuthApp()
    app.run()


if __name__ == "__main__":
    main()
