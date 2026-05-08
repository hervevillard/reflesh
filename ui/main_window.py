from __future__ import annotations

import numpy as np
from pathlib import Path

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QFrame,
    QHBoxLayout, QVBoxLayout, QScrollArea,
    QPushButton, QSlider, QLabel, QCheckBox,
    QFileDialog, QSizePolicy, QStatusBar,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal as Signal, QTimer
from PyQt6.QtGui import QAction, QColor, QPainter, QPixmap

from .image_panel import ImagePanel
from core.segmenter import Segmenter
from core.colorizer import Colorizer
from core.analyzer import Analyzer
from core.exporter import Exporter


# ── Background worker ──────────────────────────────────────────────────────────

class AnalysisWorker(QThread):
    progress = Signal(str)
    finished = Signal(dict)
    error = Signal(str)

    def __init__(self, segmenter: Segmenter, image_rgb: np.ndarray, min_area: int):
        super().__init__()
        self._segmenter = segmenter
        self._image = image_rgb
        self._min_area = min_area

    def run(self):
        try:
            if not self._segmenter.is_loaded:
                self.progress.emit("Downloading SAM2 model (first run only)…")
            else:
                self.progress.emit("Preparing SAM2…")
            self._segmenter.load(self._min_area)
            self.progress.emit("Segmenting image…")
            masks = self._segmenter.segment(self._image)
            self.progress.emit(f"Found {len(masks)} segments.")
            self.finished.emit({"masks": masks})
        except Exception as exc:
            self.error.emit(str(exc))


# ── Palette swatch widget ──────────────────────────────────────────────────────

class PaletteBar(QLabel):
    def __init__(self):
        super().__init__()
        self.setFixedHeight(24)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._colors: list[tuple] = []

    def set_colors(self, palette: np.ndarray) -> None:
        self._colors = [tuple(int(c) for c in row) for row in palette]
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if not self._colors:
            return
        w = self.width()
        h = self.height()
        n = len(self._colors)
        swatch_w = max(1, w // n)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        for i, (r, g, b) in enumerate(self._colors):
            x = i * swatch_w
            painter.fillRect(x, 0, swatch_w, h, QColor(r, g, b))
        painter.end()


# ── Main window ────────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ArtSegment")
        self.setMinimumSize(1100, 680)
        self.resize(1280, 760)

        self._image_rgb: np.ndarray | None = None
        self._masks: list | None = None
        self._color_layer: np.ndarray | None = None
        self._tonal_layer: np.ndarray | None = None
        self._edge_layer: np.ndarray | None = None
        self._current_palette: np.ndarray | None = None

        self._segmenter = Segmenter()
        self._colorizer = Colorizer()
        self._analyzer = Analyzer()
        self._exporter = Exporter()
        self._worker: AnalysisWorker | None = None

        # Debounce slider re-renders
        self._render_timer = QTimer()
        self._render_timer.setSingleShot(True)
        self._render_timer.timeout.connect(self._render)

        # Animate analyze button while running
        self._anim_timer = QTimer()
        self._anim_timer.setInterval(500)
        self._anim_dots = 0
        self._anim_timer.timeout.connect(self._animate_btn)

        self._build_ui()
        self._build_menu()

    # ── UI construction ────────────────────────────────────────────────────────

    def _build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Header
        header = self._build_header()
        outer.addWidget(header)

        # Body: sidebar + canvases
        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        outer.addLayout(body, 1)

        body.addWidget(self._build_sidebar())
        body.addLayout(self._build_canvas_area(), 1)

        # Status bar
        self._status_bar = QStatusBar()
        self._status_bar.showMessage("Ready — load an image to begin.")
        self.setStatusBar(self._status_bar)

    def _build_header(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("header")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(20, 0, 20, 0)

        title = QLabel("ArtSegment")
        title.setObjectName("appTitle")
        sub = QLabel("AI IMAGE SEGMENTATION FOR ARTISTS")
        sub.setObjectName("appSubtitle")

        layout.addWidget(title)
        layout.addSpacing(12)
        layout.addWidget(sub)
        layout.addStretch()

        device_lbl = QLabel()
        device_lbl.setObjectName("dimLabel")
        import torch
        device = "GPU (CUDA)" if torch.cuda.is_available() else "CPU"
        device_lbl.setText(device)
        layout.addWidget(device_lbl)

        return frame

    def _build_sidebar(self) -> QFrame:
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(6)

        # ── Action buttons
        self._load_btn = QPushButton("  Open Image…")
        self._load_btn.setToolTip("Ctrl+O")
        self._load_btn.clicked.connect(self._load_image)

        self._analyze_btn = QPushButton("  Analyze ▶")
        self._analyze_btn.setObjectName("primaryBtn")
        self._analyze_btn.setEnabled(False)
        self._analyze_btn.setToolTip("Run SAM2 segmentation")
        self._analyze_btn.clicked.connect(self._run_analysis)

        layout.addWidget(self._load_btn)
        layout.addWidget(self._analyze_btn)
        layout.addWidget(self._separator())

        # ── Parameters
        layout.addWidget(self._section("PARAMETERS"))
        self._color_slider, self._color_val = self._slider_row(
            "Color levels", 2, 64, 16, layout
        )
        self._tonal_slider, self._tonal_val = self._slider_row(
            "Tonal levels", 2, 12, 4, layout
        )
        self._edge_slider, self._edge_val = self._slider_row(
            "Edge strength", 0, 5, 2, layout
        )
        layout.addWidget(self._separator())

        layout.addWidget(self._section("SEGMENTATION"))
        self._min_area_slider, self._min_area_val = self._slider_row(
            "Min area (px)", 100, 5000, 500, layout, connect_render=False
        )
        hint = QLabel("Requires re-analyzing")
        hint.setObjectName("dimLabel")
        hint.setStyleSheet("color: #44403c; font-size: 10px; margin-left: 2px;")
        layout.addWidget(hint)
        layout.addWidget(self._separator())

        # ── Layer toggles
        layout.addWidget(self._section("LAYERS"))
        self._chk_color = QCheckBox("Color zones")
        self._chk_color.setChecked(True)
        self._chk_tonal = QCheckBox("Tonal map")
        self._chk_tonal.setChecked(False)
        self._chk_edges = QCheckBox("Edges")
        self._chk_edges.setChecked(True)
        for chk in (self._chk_color, self._chk_tonal, self._chk_edges):
            chk.stateChanged.connect(self._schedule_render)
            layout.addWidget(chk)
        layout.addWidget(self._separator())

        # ── Palette
        layout.addWidget(self._section("EXTRACTED PALETTE"))
        self._palette_bar = PaletteBar()
        self._palette_bar.setStyleSheet("border-radius: 4px;")
        layout.addWidget(self._palette_bar)
        layout.addWidget(self._separator())

        # ── Export buttons
        layout.addWidget(self._section("EXPORT"))
        self._export_png_btn = QPushButton("  Export PNG")
        self._export_png_btn.setObjectName("successBtn")
        self._export_png_btn.setEnabled(False)
        self._export_png_btn.clicked.connect(self._export_png)

        self._export_svg_btn = QPushButton("  Export SVG  (vector)")
        self._export_svg_btn.setEnabled(False)
        self._export_svg_btn.setToolTip(
            "GDAL-style polygonization: segments as filled vector paths.\n"
            "Open in Illustrator or Inkscape."
        )
        self._export_svg_btn.clicked.connect(self._export_svg)

        layout.addWidget(self._export_png_btn)
        layout.addWidget(self._export_svg_btn)
        layout.addStretch()

        scroll.setWidget(content)

        outer = QVBoxLayout(sidebar)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(scroll)

        return sidebar

    def _build_canvas_area(self) -> QHBoxLayout:
        layout = QHBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        self._orig_panel = ImagePanel("Original")
        self._result_panel = ImagePanel("Result")

        layout.addWidget(self._orig_panel)
        layout.addWidget(self._result_panel)
        return layout

    # ── Helper builders ────────────────────────────────────────────────────────

    def _section(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setObjectName("section")
        return lbl

    def _separator(self) -> QFrame:
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        return line

    def _slider_row(
        self, label: str, lo: int, hi: int, default: int,
        parent_layout: QVBoxLayout, connect_render: bool = True
    ) -> tuple[QSlider, QLabel]:
        row_widget = QWidget()
        row = QHBoxLayout(row_widget)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)

        lbl = QLabel(label)
        lbl.setStyleSheet("color: #a8a29e; font-size: 12px;")

        val_lbl = QLabel(str(default))
        val_lbl.setObjectName("value")
        val_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)

        row.addWidget(lbl)
        row.addStretch()
        row.addWidget(val_lbl)
        parent_layout.addWidget(row_widget)

        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(lo, hi)
        slider.setValue(default)
        slider.valueChanged.connect(lambda v, l=val_lbl: l.setText(str(v)))
        if connect_render:
            slider.valueChanged.connect(self._schedule_render)
        parent_layout.addWidget(slider)

        return slider, val_lbl

    def _build_menu(self):
        menu = self.menuBar()
        menu.setStyleSheet(
            "QMenuBar { background: #0c0a09; color: #a8a29e; border-bottom: 1px solid #292524; }"
            "QMenuBar::item:selected { background: #292524; color: #fafaf9; }"
            "QMenu { background: #1c1917; border: 1px solid #292524; }"
            "QMenu::item:selected { background: #292524; }"
        )
        file_menu = menu.addMenu("File")
        open_act = QAction("Open Image…", self)
        open_act.setShortcut("Ctrl+O")
        open_act.triggered.connect(self._load_image)
        export_png_act = QAction("Export PNG…", self)
        export_png_act.setShortcut("Ctrl+S")
        export_png_act.triggered.connect(self._export_png)
        export_svg_act = QAction("Export SVG…", self)
        export_svg_act.setShortcut("Ctrl+Shift+S")
        export_svg_act.triggered.connect(self._export_svg)
        for act in (open_act, export_png_act, export_svg_act):
            file_menu.addAction(act)

    # ── Slots ──────────────────────────────────────────────────────────────────

    def _load_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Image", "",
            "Images (*.png *.jpg *.jpeg *.bmp *.tiff *.tif *.webp)"
        )
        if not path:
            return
        from PIL import Image
        img = Image.open(path).convert("RGB")
        self._image_rgb = np.array(img)
        self._masks = self._color_layer = self._tonal_layer = self._edge_layer = None
        self._current_palette = None
        self._orig_panel.set_image(self._image_rgb)
        self._result_panel.clear()
        self._analyze_btn.setEnabled(True)
        self._export_png_btn.setEnabled(False)
        self._export_svg_btn.setEnabled(False)
        h, w = self._image_rgb.shape[:2]
        self._status_bar.showMessage(f"Loaded: {Path(path).name}  ·  {w} × {h} px")

    def _run_analysis(self):
        if self._image_rgb is None:
            return
        self._analyze_btn.setEnabled(False)
        self._anim_timer.start()
        self._worker = AnalysisWorker(
            self._segmenter, self._image_rgb, self._min_area_slider.value()
        )
        self._worker.progress.connect(self._status_bar.showMessage)
        self._worker.finished.connect(self._on_analysis_done)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_analysis_done(self, results: dict):
        self._anim_timer.stop()
        self._masks = results["masks"]
        self._analyze_btn.setText("  Re-analyze ▶")
        self._analyze_btn.setEnabled(True)
        self._render()
        self._export_png_btn.setEnabled(True)
        self._export_svg_btn.setEnabled(True)

    def _on_error(self, msg: str):
        self._anim_timer.stop()
        self._analyze_btn.setEnabled(True)
        self._status_bar.showMessage(f"Error: {msg}")

    def _animate_btn(self):
        self._anim_dots = (self._anim_dots + 1) % 4
        dots = "." * self._anim_dots
        self._analyze_btn.setText(f"  Analyzing{dots}")

    def _schedule_render(self):
        if self._masks is not None:
            self._render_timer.start(120)

    def _render(self):
        if self._image_rgb is None or self._masks is None:
            return

        palette, labels = self._colorizer.quantize(
            self._image_rgb, self._color_slider.value()
        )
        self._current_palette = palette
        self._color_layer = self._colorizer.colorize_masks(
            self._masks, palette, labels, self._image_rgb.shape
        )
        self._tonal_layer = self._analyzer.tonal_map(
            self._image_rgb, self._tonal_slider.value()
        )
        self._edge_layer = self._analyzer.edge_map(
            self._image_rgb, self._masks, self._edge_slider.value()
        )

        composite = self._exporter.composite(
            self._color_layer, self._tonal_layer, self._edge_layer,
            self._chk_color.isChecked(),
            self._chk_tonal.isChecked(),
            self._chk_edges.isChecked(),
        )
        self._result_panel.set_image(composite)
        self._palette_bar.set_colors(palette)

        n = len(self._masks)
        k = self._color_slider.value()
        self._status_bar.showMessage(
            f"{n} segments  ·  {k} colors  ·  {self._tonal_slider.value()} tonal levels"
        )

    def _export_png(self):
        if self._color_layer is None:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export PNG", "artsegment_output.png", "PNG (*.png)"
        )
        if not path:
            return
        composite = self._exporter.composite(
            self._color_layer, self._tonal_layer, self._edge_layer,
            self._chk_color.isChecked(), self._chk_tonal.isChecked(), self._chk_edges.isChecked(),
        )
        self._exporter.save_png(composite, path)
        self._status_bar.showMessage(f"Saved PNG: {path}")

    def _export_svg(self):
        if self._color_layer is None or self._masks is None:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export SVG (vector layers)", "artsegment_output.svg", "SVG (*.svg)"
        )
        if not path:
            return
        self._exporter.save_svg(self._color_layer, self._masks, path)
        self._status_bar.showMessage(f"Saved SVG: {path}")
