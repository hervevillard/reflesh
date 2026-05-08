import numpy as np
from PyQt6.QtWidgets import QFrame, QLabel, QVBoxLayout, QSizePolicy
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QImage


class ImagePanel(QFrame):
    """
    A labeled image display panel that scales its content to fit while
    preserving aspect ratio. Used for both the original and result views.
    """

    def __init__(self, tag: str):
        super().__init__()
        self.setObjectName("imageFrame")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._tag = QLabel(tag.upper())
        self._tag.setObjectName("panelTag")
        self._tag.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self._tag)

        self._display = QLabel()
        self._display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._display.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._display.setStyleSheet("background: transparent;")
        layout.addWidget(self._display, 1)

        self._pixmap: QPixmap | None = None

    def set_image(self, image_rgb: np.ndarray) -> None:
        h, w, c = image_rgb.shape
        fmt = QImage.Format.Format_RGB888
        qimg = QImage(image_rgb.tobytes(), w, h, w * c, fmt)
        self._pixmap = QPixmap.fromImage(qimg)
        self._refresh()

    def clear(self) -> None:
        self._pixmap = None
        self._display.setPixmap(QPixmap())
        self._display.setText("")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._refresh()

    def _refresh(self) -> None:
        if self._pixmap is None:
            return
        scaled = self._pixmap.scaled(
            self._display.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._display.setPixmap(scaled)
