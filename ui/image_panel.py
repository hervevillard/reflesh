import math
import numpy as np
from PyQt6.QtWidgets import QFrame, QLabel, QVBoxLayout, QScrollArea, QSizePolicy
from PyQt6.QtCore import Qt, QEvent
from PyQt6.QtGui import QPixmap, QImage, QPainter, QPen, QColor


class ImagePanel(QFrame):
    _ZOOM_STEP = 1.25
    _ZOOM_MIN = 0.25
    _ZOOM_MAX = 8.0

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

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(False)
        self._scroll.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setStyleSheet("background: transparent;")

        self._display = QLabel()
        self._display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._display.setStyleSheet("background: transparent;")
        self._scroll.setWidget(self._display)
        layout.addWidget(self._scroll, 1)

        self._pixmap: QPixmap | None = None
        self._rule_thirds: bool = False
        self._golden_spiral: bool = False
        self._zoom: float = 1.0

        self._scroll.viewport().installEventFilter(self)

    def eventFilter(self, obj, event):
        if obj is self._scroll.viewport() and event.type() == QEvent.Type.Wheel:
            if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                delta = event.angleDelta().y()
                self._zoom_by(self._ZOOM_STEP if delta > 0 else 1.0 / self._ZOOM_STEP)
                return True
        return super().eventFilter(obj, event)

    def set_image(self, image_rgb: np.ndarray) -> None:
        h, w, c = image_rgb.shape
        qimg = QImage(image_rgb.tobytes(), w, h, w * c, QImage.Format.Format_RGB888)
        self._pixmap = QPixmap.fromImage(qimg)
        self._refresh()

    def set_overlays(self, rule_thirds: bool, golden_spiral: bool) -> None:
        self._rule_thirds = rule_thirds
        self._golden_spiral = golden_spiral
        self._refresh()

    def clear(self) -> None:
        self._pixmap = None
        self._display.setPixmap(QPixmap())
        self._display.setText("")

    def zoom_in(self) -> None:
        self._zoom_by(self._ZOOM_STEP)

    def zoom_out(self) -> None:
        self._zoom_by(1.0 / self._ZOOM_STEP)

    def reset_zoom(self) -> None:
        self._zoom = 1.0
        self._refresh()

    @property
    def zoom(self) -> float:
        return self._zoom

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._refresh()

    def _zoom_by(self, factor: float) -> None:
        old_zoom = self._zoom
        new_zoom = max(self._ZOOM_MIN, min(self._ZOOM_MAX, self._zoom * factor))
        if new_zoom == old_zoom:
            return

        sb_h = self._scroll.horizontalScrollBar()
        sb_v = self._scroll.verticalScrollBar()
        vp = self._scroll.viewport()
        cx = sb_h.value() + vp.width() / 2
        cy = sb_v.value() + vp.height() / 2

        self._zoom = new_zoom
        self._refresh()

        scale = new_zoom / old_zoom
        sb_h.setValue(int(cx * scale - vp.width() / 2))
        sb_v.setValue(int(cy * scale - vp.height() / 2))

    def _refresh(self) -> None:
        if self._pixmap is None:
            return
        vp_size = self._scroll.viewport().size()
        fit = self._pixmap.scaled(
            vp_size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        if self._zoom != 1.0:
            scaled = self._pixmap.scaled(
                int(fit.width() * self._zoom),
                int(fit.height() * self._zoom),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        else:
            scaled = fit
        if self._rule_thirds or self._golden_spiral:
            scaled = self._paint_overlays(scaled)
        self._display.setPixmap(scaled)
        self._display.resize(scaled.size())

    def _paint_overlays(self, pixmap: QPixmap) -> QPixmap:
        out = QPixmap(pixmap)
        painter = QPainter(out)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = out.width(), out.height()

        if self._rule_thirds:
            pen = QPen(QColor(255, 255, 255, 110))
            pen.setWidth(1)
            painter.setPen(pen)
            for frac in (1 / 3, 2 / 3):
                x = int(w * frac)
                y = int(h * frac)
                painter.drawLine(x, 0, x, h)
                painter.drawLine(0, y, w, y)

        if self._golden_spiral:
            self._draw_golden_spiral(painter, w, h)

        painter.end()
        return out

    def _draw_golden_spiral(self, painter: QPainter, w: int, h: int) -> None:
        """Draw an approximated golden spiral using 4 quarter-circle arcs."""
        from PyQt6.QtCore import QRectF
        PHI = (1 + math.sqrt(5)) / 2

        pen = QPen(QColor(249, 115, 22, 140))  # orange, semi-transparent
        pen.setWidthF(1.5)
        painter.setPen(pen)

        # Start from full rect, repeatedly peel off a square in a Fibonacci spiral
        x, y = 0.0, 0.0
        fw, fh = float(w), float(h)
        for turn in range(5):
            if fw >= fh:
                sq = fh
                if turn % 4 == 0:
                    # arc in top-left square, sweeping from 270° to 0° (CW: 90° span)
                    rect = QRectF(x, y, sq * 2, sq * 2)
                    painter.drawArc(rect, 270 * 16, -90 * 16)
                    x += sq
                    fw -= sq
                elif turn % 4 == 1:
                    rect = QRectF(x - sq, y - sq, sq * 2, sq * 2)
                    painter.drawArc(rect, 0 * 16, -90 * 16)
                    y += sq
                    fw -= sq
                elif turn % 4 == 2:
                    rect = QRectF(x - sq * 2, y - sq, sq * 2, sq * 2)
                    painter.drawArc(rect, 90 * 16, -90 * 16)
                    x -= sq
                    fw -= sq
                else:
                    rect = QRectF(x - sq, y - sq * 2, sq * 2, sq * 2)
                    painter.drawArc(rect, 180 * 16, -90 * 16)
                    y -= sq
                    fw -= sq
            else:
                sq = fw
                fh -= sq
