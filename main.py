import sys
import traceback
from pathlib import Path


def _load_env():
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        try:
            from dotenv import load_dotenv
            load_dotenv(env_path)
        except ImportError:
            pass


def main():
    _load_env()

    try:
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtGui import QFont
        from ui.main_window import MainWindow
        from ui.theme import DARK_WARM
    except Exception:
        print("\n[IMPORT ERROR] Failed to load UI modules:\n")
        traceback.print_exc()
        input("\nPress Enter to exit...")
        sys.exit(1)

    try:
        app = QApplication(sys.argv)
        app.setApplicationName("ArtSegment")
        app.setOrganizationName("ArtSegment")
        app.setStyle("Fusion")
        app.setStyleSheet(DARK_WARM)
        font = QFont("Segoe UI", 10)
        app.setFont(font)

        window = MainWindow()
        window.show()
        sys.exit(app.exec())
    except Exception:
        print("\n[STARTUP ERROR] ArtSegment crashed at startup:\n")
        traceback.print_exc()
        input("\nPress Enter to exit...")
        sys.exit(1)


if __name__ == "__main__":
    main()
