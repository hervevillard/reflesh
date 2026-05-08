DARK_WARM = """
/* ── Base ─────────────────────────────────────────────────────────────── */
QMainWindow, QDialog {
    background-color: #1c1917;
}
QWidget {
    background-color: #1c1917;
    color: #e7e5e4;
    font-family: 'Segoe UI', 'Inter', 'SF Pro Text', Arial, sans-serif;
    font-size: 13px;
}

/* ── Sidebar ──────────────────────────────────────────────────────────── */
QFrame#sidebar {
    background-color: #0c0a09;
    border-right: 1px solid #292524;
    min-width: 240px;
    max-width: 240px;
}

/* ── Header ───────────────────────────────────────────────────────────── */
QFrame#header {
    background-color: #0c0a09;
    border-bottom: 1px solid #292524;
    min-height: 52px;
    max-height: 52px;
}
QLabel#appTitle {
    color: #fafaf9;
    font-size: 17px;
    font-weight: 700;
    letter-spacing: 0.5px;
}
QLabel#appSubtitle {
    color: #57534e;
    font-size: 10px;
    letter-spacing: 2px;
}

/* ── Image frames ─────────────────────────────────────────────────────── */
QFrame#imageFrame {
    background-color: #0c0a09;
    border: 1px solid #292524;
    border-radius: 10px;
}
QLabel#panelTag {
    color: #57534e;
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 2.5px;
    padding: 6px 10px 0 10px;
}

/* ── Section labels ───────────────────────────────────────────────────── */
QLabel#section {
    color: #78716c;
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 1.8px;
    margin-top: 6px;
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
    color: #57534e;
    font-size: 11px;
}

/* ── Buttons ──────────────────────────────────────────────────────────── */
QPushButton {
    background-color: #292524;
    color: #d6d3d1;
    border: 1px solid #3c3734;
    border-radius: 7px;
    padding: 8px 14px;
    font-size: 13px;
}
QPushButton:hover {
    background-color: #3c3734;
    border-color: #57534e;
    color: #fafaf9;
}
QPushButton:pressed {
    background-color: #1c1917;
}
QPushButton:disabled {
    color: #44403c;
    border-color: #292524;
    background-color: #1c1917;
}

QPushButton#primaryBtn {
    background-color: #9a3412;
    color: #ffedd5;
    border: none;
    font-weight: 600;
    font-size: 13px;
}
QPushButton#primaryBtn:hover {
    background-color: #c2410c;
}
QPushButton#primaryBtn:pressed {
    background-color: #7c2d12;
}
QPushButton#primaryBtn:disabled {
    background-color: #292524;
    color: #44403c;
}

QPushButton#successBtn {
    background-color: #14532d;
    color: #dcfce7;
    border: none;
    font-weight: 600;
}
QPushButton#successBtn:hover {
    background-color: #166534;
}
QPushButton#successBtn:disabled {
    background-color: #1c1917;
    color: #44403c;
}

/* ── Sliders ──────────────────────────────────────────────────────────── */
QSlider::groove:horizontal {
    height: 3px;
    background: #3c3734;
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
    border: 2px solid #1c1917;
}
QSlider::handle:horizontal:hover {
    background: #fb923c;
    border-color: #0c0a09;
}
QSlider:disabled::groove:horizontal {
    background: #292524;
}
QSlider:disabled::handle:horizontal {
    background: #3c3734;
    border-color: #1c1917;
}

/* ── Checkboxes ───────────────────────────────────────────────────────── */
QCheckBox {
    spacing: 9px;
    color: #d6d3d1;
    padding: 3px 0;
}
QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border-radius: 4px;
    border: 1.5px solid #44403c;
    background: #292524;
}
QCheckBox::indicator:checked {
    background-color: #f97316;
    border-color: #f97316;
}
QCheckBox::indicator:hover {
    border-color: #a8a29e;
}

/* ── Separators ───────────────────────────────────────────────────────── */
QFrame[frameShape="4"] {
    border: none;
    background-color: #292524;
    max-height: 1px;
    min-height: 1px;
    margin: 4px 0;
}

/* ── Status bar ───────────────────────────────────────────────────────── */
QStatusBar {
    background-color: #0c0a09;
    color: #57534e;
    border-top: 1px solid #292524;
    font-size: 11px;
    padding: 2px 8px;
}
QStatusBar QLabel {
    color: #57534e;
}

/* ── Scrollbars ───────────────────────────────────────────────────────── */
QScrollBar:vertical {
    background: #1c1917;
    width: 5px;
    margin: 0;
    border: none;
}
QScrollBar::handle:vertical {
    background: #44403c;
    border-radius: 2px;
    min-height: 24px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }

QScrollArea {
    border: none;
    background: transparent;
}
QScrollArea > QWidget > QWidget {
    background: transparent;
}

/* ── Tooltip ──────────────────────────────────────────────────────────── */
QToolTip {
    background-color: #292524;
    color: #e7e5e4;
    border: 1px solid #44403c;
    border-radius: 4px;
    padding: 4px 8px;
    font-size: 12px;
}
"""
