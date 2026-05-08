import sys
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont
from ui.main_window import MainWindow
from ui.theme import DARK_WARM


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


if __name__ == "__main__":
    main()
