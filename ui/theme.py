DARK_WARM = """
/* ── Base ─────────────────────────────────────────────────────────────── */
QMainWindow, QDialog {
    background-color: #161514;
}
QWidget {
    background-color: #161514;
    color: #e8e6e3;
    font-family: 'Inter', 'SF Pro Text', 'Segoe UI', Arial, sans-serif;
    font-size: 13px;
}

/* ── Menu bar ─────────────────────────────────────────────────────────── */
QMenuBar {
    background: #0d0c0b;
    color: #6a6865;
    border-bottom: 1px solid #242220;
}
QMenuBar::item:selected { background: #242220; color: #e8e6e3; }
QMenu {
    background: #1e1c1a;
    border: 1px solid #2a2826;
}
QMenu::item:selected { background: #242220; color: #e8e6e3; }

/* ── Title bar ────────────────────────────────────────────────────────── */
QFrame#appTitleBar {
    background-color: #0d0c0b;
    border-bottom: 1px solid #242220;
    min-height: 38px;
    max-height: 38px;
}
QLabel#appTitle {
    color: #f0eeec;
    font-size: 15px;
    font-weight: 700;
    letter-spacing: 0.3px;
}
QLabel#appSubtitle {
    color: #3a3836;
    font-size: 9px;
    letter-spacing: 2px;
}

/* Window control buttons (min / max / close) */
QPushButton#winMin, QPushButton#winMax, QPushButton#winClose {
    background: transparent;
    border: none;
    border-radius: 0;
    color: #6a6865;
    font-size: 15px;
    padding: 0;
}
QPushButton#winMin:hover, QPushButton#winMax:hover {
    background: #242220;
    color: #f0eeec;
}
QPushButton#winClose:hover {
    background: #c42b1c;
    color: #ffffff;
}
QPushButton#winMin:pressed, QPushButton#winMax:pressed {
    background: #2e2c29;
    color: #f0eeec;
}
QPushButton#winClose:pressed {
    background: #a32215;
    color: #ffffff;
}

/* Legacy header strip (non-frameless fallback) */
QFrame#header {
    background-color: #0d0c0b;
    border-bottom: 1px solid #242220;
    min-height: 44px;
    max-height: 44px;
}

/* ── Sidebar ──────────────────────────────────────────────────────────── */
QFrame#sidebar {
    background-color: #0d0c0b;
    border-right: 1px solid #242220;
    min-width: 256px;
    max-width: 256px;
}

/* ── Sidebar cards ────────────────────────────────────────────────────── */
QFrame#card {
    background-color: #1e1c1a;
    border: 1px solid #2a2826;
    border-radius: 10px;
}

/* ── Section labels ───────────────────────────────────────────────────── */
QLabel#section {
    color: #5a5754;
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 1.4px;
    margin-top: 2px;
    margin-bottom: 2px;
}

/* ── Value labels ─────────────────────────────────────────────────────── */
QLabel#value {
    color: #f97316;
    font-size: 12px;
    font-weight: 600;
    min-width: 28px;
}

/* ── General labels ───────────────────────────────────────────────────── */
QLabel#dimLabel {
    color: #44403c;
    font-size: 11px;
}

/* ── Pigment names label ──────────────────────────────────────────────── */
QLabel#pigmentNames {
    color: #5a5754;
    font-size: 11px;
    font-style: italic;
    background: transparent;
}

/* ── Image frames ─────────────────────────────────────────────────────── */
QFrame#imageFrame {
    background-color: #0d0c0b;
    border: 1px solid #242220;
    border-radius: 14px;
}
QLabel#panelTag {
    color: #3a3836;
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 2.5px;
    padding: 8px 12px 0 12px;
}

/* ── Buttons ──────────────────────────────────────────────────────────── */
QPushButton {
    background-color: #242220;
    color: #c8c5c2;
    border: 1px solid #343230;
    border-radius: 8px;
    padding: 9px 14px;
    font-size: 13px;
}
QPushButton:hover {
    background-color: #2e2c2a;
    border-color: #4a4845;
    color: #f0eeec;
}
QPushButton:pressed {
    background-color: #161514;
}
QPushButton:disabled {
    color: #353330;
    border-color: #222120;
    background-color: #181716;
}

QPushButton#primaryBtn {
    background-color: #9a3412;
    color: #ffedd5;
    border: none;
    font-weight: 600;
    font-size: 13px;
    border-radius: 8px;
    padding: 10px 14px;
}
QPushButton#primaryBtn:hover   { background-color: #b84015; }
QPushButton#primaryBtn:pressed { background-color: #7c2d12; }
QPushButton#primaryBtn:disabled {
    background-color: #242220;
    color: #353330;
}

QPushButton#successBtn {
    background-color: #14532d;
    color: #dcfce7;
    border: none;
    font-weight: 600;
    border-radius: 8px;
    padding: 9px 14px;
}
QPushButton#successBtn:hover   { background-color: #186534; }
QPushButton#successBtn:pressed { background-color: #0f3d22; }
QPushButton#successBtn:disabled {
    background-color: #181716;
    color: #353330;
}

/* ── Sliders ──────────────────────────────────────────────────────────── */
QSlider::groove:horizontal {
    height: 3px;
    background: #323030;
    border-radius: 2px;
}
QSlider::sub-page:horizontal {
    background: #f97316;
    border-radius: 2px;
}
QSlider::handle:horizontal {
    background: #f97316;
    width: 14px;
    height: 14px;
    margin: -6px 0;
    border-radius: 7px;
    border: 2px solid #161514;
}
QSlider::handle:horizontal:hover {
    background: #fb923c;
    border-color: #0d0c0b;
}
QSlider:disabled::groove:horizontal { background: #242220; }
QSlider:disabled::handle:horizontal {
    background: #343230;
    border-color: #161514;
}

/* ── Checkboxes ───────────────────────────────────────────────────────── */
QCheckBox {
    spacing: 9px;
    color: #c8c5c2;
    padding: 3px 0;
}
QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border-radius: 4px;
    border: 1.5px solid #3a3836;
    background: #242220;
}
QCheckBox::indicator:checked {
    background-color: #f97316;
    border-color: #f97316;
}
QCheckBox::indicator:hover { border-color: #7a7875; }

/* ── ComboBox ─────────────────────────────────────────────────────────── */
QComboBox {
    background: #242220;
    color: #e8e6e3;
    border: 1px solid #343230;
    border-radius: 6px;
    padding: 5px 8px;
    font-size: 12px;
}
QComboBox:focus { border-color: #f97316; }
QComboBox::drop-down { border: none; width: 18px; }
QComboBox QAbstractItemView {
    background: #1e1c1a;
    color: #e8e6e3;
    border: 1px solid #2a2826;
    selection-background-color: #2a2826;
}

/* ── LineEdit ─────────────────────────────────────────────────────────── */
QLineEdit {
    background: #242220;
    color: #e8e6e3;
    border: 1px solid #343230;
    border-radius: 6px;
    padding: 5px 8px;
    font-size: 12px;
}
QLineEdit:focus { border-color: #f97316; }

/* ── Separators ───────────────────────────────────────────────────────── */
QFrame[frameShape="4"] {
    border: none;
    background-color: #242220;
    max-height: 1px;
    min-height: 1px;
    margin: 3px 0;
}

/* ── Status bar ───────────────────────────────────────────────────────── */
QStatusBar {
    background-color: #0d0c0b;
    color: #4a4845;
    border-top: 1px solid #242220;
    font-size: 11px;
    padding: 2px 10px;
}
QStatusBar QLabel { color: #4a4845; }

/* ── Scrollbars ───────────────────────────────────────────────────────── */
QScrollBar:vertical {
    background: transparent;
    width: 4px;
    margin: 0;
    border: none;
}
QScrollBar::handle:vertical {
    background: #3a3836;
    border-radius: 2px;
    min-height: 24px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }

QScrollArea {
    border: none;
    background: transparent;
}
QScrollArea > QWidget > QWidget { background: transparent; }

/* ── Tooltip ──────────────────────────────────────────────────────────── */
QToolTip {
    background-color: #2a2826;
    color: #e8e6e3;
    border: 1px solid #3a3836;
    border-radius: 6px;
    padding: 4px 8px;
    font-size: 12px;
}
"""
