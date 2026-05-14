from __future__ import annotations

import json
import numpy as np
from pathlib import Path

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QFrame, QSplitter,
    QHBoxLayout, QVBoxLayout, QScrollArea,
    QPushButton, QSlider, QLabel, QCheckBox, QLineEdit, QComboBox,
    QFileDialog, QSizePolicy, QStatusBar,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal as Signal, QTimer
from PyQt6.QtGui import QColor, QPainter, QKeySequence, QShortcut

try:
    from qframelesswindow import FramelessMainWindow as _FramelessBase
    _FRAMELESS = True
except ImportError:
    _FramelessBase = QMainWindow
    _FRAMELESS = False

from .image_panel import ImagePanel
from core.segmenter import Segmenter
from core.colorizer import Colorizer
from core.analyzer import Analyzer
from core.exporter import Exporter


# ── Custom title bar ───────────────────────────────────────────────────────────

class TitleBar(QFrame):
    """Draggable title bar with min / max / close window controls."""

    def __init__(self, parent: QMainWindow):
        super().__init__(parent)
        self._win = parent
        self._drag_pos = None
        self._handle_drag = True  # disabled when qframelesswindow owns drag
        self.setObjectName("appTitleBar")
        self.setFixedHeight(38)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 4, 0)
        layout.setSpacing(0)

        lbl = QLabel("ArtSegment")
        lbl.setObjectName("appTitle")
        layout.addWidget(lbl)
        layout.addSpacing(10)

        sub = QLabel("AI IMAGE SEGMENTATION FOR ARTISTS")
        sub.setObjectName("appSubtitle")
        layout.addWidget(sub)
        layout.addStretch()

        self.device_lbl = QLabel("GPU / CPU — detected on first run")
        self.device_lbl.setObjectName("dimLabel")
        layout.addWidget(self.device_lbl)
        layout.addSpacing(8)

        self._min_btn = QPushButton("—")
        self._min_btn.setObjectName("winMin")
        self._max_btn = QPushButton("□")
        self._max_btn.setObjectName("winMax")
        self._close_btn = QPushButton("✕")
        self._close_btn.setObjectName("winClose")

        for btn in (self._min_btn, self._max_btn, self._close_btn):
            btn.setFixedSize(46, 38)
            btn.setFlat(True)
            layout.addWidget(btn)

        self._min_btn.clicked.connect(parent.showMinimized)
        self._max_btn.clicked.connect(self._toggle_max)
        self._close_btn.clicked.connect(parent.close)

    def _toggle_max(self):
        if self._win.isMaximized():
            self._win.showNormal()
            self._max_btn.setText("□")
        else:
            self._win.showMaximized()
            self._max_btn.setText("❐")

    def mousePressEvent(self, event):
        if self._handle_drag and event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = (
                event.globalPosition().toPoint() - self._win.frameGeometry().topLeft()
            )
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if (self._handle_drag and self._drag_pos is not None
                and event.buttons() == Qt.MouseButton.LeftButton):
            self._win.move(event.globalPosition().toPoint() - self._drag_pos)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._toggle_max()
        super().mouseDoubleClickEvent(event)


# ── Background worker ──────────────────────────────────────────────────────────

class AnalysisWorker(QThread):
    progress = Signal(str)
    finished = Signal(dict)
    error = Signal(str)

    def __init__(self, segmenter: Segmenter, image_rgb: np.ndarray, min_area: int, prompt: str):
        super().__init__()
        self._segmenter = segmenter
        self._image = image_rgb
        self._min_area = min_area
        self._prompt = prompt

    def run(self):
        try:
            if not self._segmenter.is_loaded:
                self.progress.emit("Loading SAM 3.1 (first run: ~60 s)…")
            else:
                self.progress.emit("Preparing SAM 3.1…")
            self._segmenter.load(self._min_area)
            device = self._segmenter._device or "unknown"
            self.progress.emit(f'Segmenting "{self._prompt}" on {device.upper()}…')
            masks = self._segmenter.segment(self._image, self._prompt)
            self.progress.emit(f"Found {len(masks)} segments.")
            self.finished.emit({"masks": masks, "device": device})
        except Exception as exc:
            self.error.emit(str(exc))


# ── Palette swatch widget ──────────────────────────────────────────────────────

class PaletteBar(QLabel):
    def __init__(self):
        super().__init__()
        self.setFixedHeight(22)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._colors: list[tuple] = []

    def set_colors(self, palette: np.ndarray) -> None:
        self._colors = [tuple(int(c) for c in row) for row in palette]
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if not self._colors:
            return
        w, h, n = self.width(), self.height(), len(self._colors)
        swatch_w = max(1, w // n)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        for i, (r, g, b) in enumerate(self._colors):
            painter.fillRect(i * swatch_w, 0, swatch_w, h, QColor(r, g, b))
        painter.end()


# ── Main window ────────────────────────────────────────────────────────────────

class MainWindow(_FramelessBase):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ArtSegment")
        self.setMinimumSize(1100, 680)
        self.resize(1300, 780)

        self._image_rgb: np.ndarray | None = None
        self._raw_masks: list | None = None
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

        self._pigments_data: list[dict] = self._load_pigments()

        self._render_timer = QTimer()
        self._render_timer.setSingleShot(True)
        self._render_timer.timeout.connect(self._render)

        self._anim_timer = QTimer()
        self._anim_timer.setInterval(500)
        self._anim_dots = 0
        self._anim_timer.timeout.connect(self._animate_btn)

        self._build_ui()
        if not _FRAMELESS:
            self._build_menu()
        self._register_shortcuts()

        if _FRAMELESS:
            # Let the library own window drag / resize; our bar supplies the UI.
            self._title_bar._handle_drag = False
            self.setTitleBar(self._title_bar)
            # setTitleBar places the bar at y=0 as a window-level overlay.
            # Push the central-widget content below it so nothing is hidden.
            self.setContentsMargins(0, 38, 0, 0)
            self._title_bar.raise_()

    # ── Pigments ───────────────────────────────────────────────────────────────

    def _load_pigments(self) -> list[dict]:
        try:
            p = Path(__file__).parent.parent / "data" / "pigments.json"
            with open(p, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    # ── UI construction ────────────────────────────────────────────────────────

    def _build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self._title_bar = TitleBar(self)
        if not _FRAMELESS:
            # Frameless library keeps the bar as a window-level overlay; only
            # add it to the layout when we have a standard OS window frame.
            outer.addWidget(self._title_bar)

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        outer.addLayout(body, 1)

        body.addWidget(self._build_sidebar())
        body.addWidget(self._build_canvas_area(), 1)

        self._status_bar = QStatusBar()
        self._status_bar.showMessage("Ready — load an image to begin.")
        self.setStatusBar(self._status_bar)

    def _build_menu(self):
        menu = self.menuBar()
        menu.setStyleSheet(
            "QMenuBar { background: #0d0c0b; color: #6a6865;"
            " border-bottom: 1px solid #242220; }"
            "QMenuBar::item:selected { background: #242220; color: #e8e6e3; }"
            "QMenu { background: #1e1c1a; border: 1px solid #2a2826; }"
            "QMenu::item:selected { background: #242220; color: #e8e6e3; }"
        )
        from PyQt6.QtGui import QAction
        file_menu = menu.addMenu("File")
        for label, shortcut, slot in [
            ("Open Image…",        "Ctrl+O",       self._load_image),
            ("Export PNG…",        "Ctrl+S",       self._export_png),
            ("Export SVG…",        "Ctrl+Shift+S", self._export_svg),
            ("Export Palette PNG…","Ctrl+Shift+P", self._export_palette_png),
        ]:
            act = QAction(label, self)
            act.setShortcut(shortcut)
            act.triggered.connect(slot)
            file_menu.addAction(act)

    def _build_sidebar(self) -> QFrame:
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(8)

        # ── Open + Analyze ─────────────────────────────────────────────────
        self._load_btn = QPushButton("Open Image…")
        self._load_btn.setToolTip("Ctrl+O")
        self._load_btn.clicked.connect(self._load_image)

        self._analyze_btn = QPushButton("Analyze ▶")
        self._analyze_btn.setObjectName("primaryBtn")
        self._analyze_btn.setEnabled(False)
        self._analyze_btn.setToolTip("Run SAM 3.1 segmentation")
        self._analyze_btn.clicked.connect(self._run_analysis)

        layout.addWidget(self._load_btn)
        layout.addWidget(self._analyze_btn)

        # ── Parameters card ────────────────────────────────────────────────
        layout.addWidget(self._section("PARAMETERS"))
        params_card = self._card()
        params_inner = QVBoxLayout(params_card)
        params_inner.setContentsMargins(12, 10, 12, 10)
        params_inner.setSpacing(8)

        self._color_slider, self._color_val = self._slider_row(
            "Color levels", 2, 64, 16, params_inner
        )
        params_inner.addWidget(self._thin_sep())
        self._tonal_slider, self._tonal_val = self._slider_row(
            "Tonal levels", 2, 16, 10, params_inner
        )
        params_inner.addWidget(self._thin_sep())
        self._edge_slider, self._edge_val = self._slider_row(
            "Edge strength", 0, 5, 2, params_inner
        )
        params_inner.addWidget(self._thin_sep())

        edge_row = QHBoxLayout()
        edge_row.setContentsMargins(0, 0, 0, 0)
        edge_lbl = QLabel("Edge style")
        edge_lbl.setStyleSheet("color: #6a6865; font-size: 12px; background: transparent;")
        self._edge_mode = QComboBox()
        self._edge_mode.addItems(["Coloring", "Outline", "Drawn", "Cartoon"])
        self._edge_mode.currentIndexChanged.connect(self._schedule_render)
        edge_row.addWidget(edge_lbl)
        edge_row.addStretch()
        edge_row.addWidget(self._edge_mode)
        params_inner.addLayout(edge_row)
        layout.addWidget(params_card)

        # ── Segmentation card ──────────────────────────────────────────────
        layout.addWidget(self._section("SEGMENTATION"))
        seg_card = self._card()
        seg_inner = QVBoxLayout(seg_card)
        seg_inner.setContentsMargins(12, 10, 12, 10)
        seg_inner.setSpacing(8)

        prompt_lbl = QLabel("Concept prompt")
        prompt_lbl.setStyleSheet("color: #6a6865; font-size: 12px; background: transparent;")
        seg_inner.addWidget(prompt_lbl)
        self._prompt_edit = QLineEdit("every object and its edges")
        self._prompt_edit.setPlaceholderText("sky · figure · foliage · every object…")
        seg_inner.addWidget(self._prompt_edit)
        seg_inner.addWidget(self._thin_sep())
        self._min_area_slider, self._min_area_val = self._slider_row(
            "Min area (px)", 100, 5000, 500, seg_inner, connect_render=False
        )
        seg_inner.addWidget(self._thin_sep())
        self._merge_slider, self._merge_val = self._slider_row(
            "Merge similar", 0, 50, 0, seg_inner, connect_render=True
        )
        hint = QLabel("Prompt + min area require re-analyzing")
        hint.setObjectName("dimLabel")
        seg_inner.addWidget(hint)
        layout.addWidget(seg_card)

        # ── Layers card ────────────────────────────────────────────────────
        layout.addWidget(self._section("LAYERS"))
        layers_card = self._card()
        layers_inner = QVBoxLayout(layers_card)
        layers_inner.setContentsMargins(12, 10, 12, 10)
        layers_inner.setSpacing(4)

        self._chk_color = QCheckBox("Color zones")
        self._chk_color.setChecked(True)
        self._chk_cartoon_layer = QCheckBox("Cartoonize")
        self._chk_cartoon_layer.setChecked(False)
        self._chk_cartoon_layer.setToolTip(
            "Full cartoon transform: edge-preserving flat colors + ink lines baked in.\n"
            "Edge strength slider controls line density.\n"
            "Tonal map and temperature overlays still apply on top."
        )
        self._chk_tonal = QCheckBox("Tonal map")
        self._chk_tonal.setChecked(False)
        self._chk_edges = QCheckBox("Edges")
        self._chk_edges.setChecked(True)
        self._chk_comp = QCheckBox("Complementary")
        self._chk_comp.setChecked(False)
        self._chk_comp.setToolTip("Flip hues to complementaries — plan shadow colors")
        self._chk_temp = QCheckBox("Temperature map")
        self._chk_temp.setChecked(False)
        self._chk_temp.setToolTip("Overlay warm / cool / neutral per segment")

        for chk in (self._chk_color, self._chk_cartoon_layer, self._chk_tonal,
                    self._chk_edges, self._chk_comp, self._chk_temp):
            chk.stateChanged.connect(self._schedule_render)
            layers_inner.addWidget(chk)
        layout.addWidget(layers_card)

        # ── Composition card ───────────────────────────────────────────────
        layout.addWidget(self._section("COMPOSITION"))
        comp_card = self._card()
        comp_inner = QVBoxLayout(comp_card)
        comp_inner.setContentsMargins(12, 10, 12, 10)
        comp_inner.setSpacing(4)

        self._chk_thirds = QCheckBox("Rule of thirds")
        self._chk_spiral = QCheckBox("Golden spiral")
        for chk in (self._chk_thirds, self._chk_spiral):
            chk.stateChanged.connect(self._update_overlays)
            comp_inner.addWidget(chk)
        layout.addWidget(comp_card)

        # ── Palette card ───────────────────────────────────────────────────
        layout.addWidget(self._section("PALETTE"))
        palette_card = self._card()
        palette_inner = QVBoxLayout(palette_card)
        palette_inner.setContentsMargins(12, 10, 12, 10)
        palette_inner.setSpacing(8)

        self._palette_bar = PaletteBar()
        self._palette_bar.setStyleSheet("border-radius: 4px;")
        palette_inner.addWidget(self._palette_bar)

        self._pigment_lbl = QLabel()
        self._pigment_lbl.setObjectName("pigmentNames")
        self._pigment_lbl.setWordWrap(True)
        self._pigment_lbl.hide()
        palette_inner.addWidget(self._pigment_lbl)

        self._export_palette_btn = QPushButton("Export Palette PNG")
        self._export_palette_btn.setEnabled(False)
        self._export_palette_btn.clicked.connect(self._export_palette_png)
        palette_inner.addWidget(self._export_palette_btn)
        layout.addWidget(palette_card)

        # ── Export card ────────────────────────────────────────────────────
        layout.addWidget(self._section("EXPORT"))
        export_card = self._card()
        export_inner = QVBoxLayout(export_card)
        export_inner.setContentsMargins(12, 10, 12, 10)
        export_inner.setSpacing(8)

        self._export_png_btn = QPushButton("Export PNG")
        self._export_png_btn.setObjectName("successBtn")
        self._export_png_btn.setEnabled(False)
        self._export_png_btn.clicked.connect(self._export_png)

        self._export_value_btn = QPushButton("Export Value Study PNG")
        self._export_value_btn.setObjectName("successBtn")
        self._export_value_btn.setEnabled(False)
        self._export_value_btn.setToolTip("Save grayscale tonal map for value planning")
        self._export_value_btn.clicked.connect(self._export_value_study)

        self._export_svg_btn = QPushButton("Export SVG  (vector)")
        self._export_svg_btn.setEnabled(False)
        self._export_svg_btn.setToolTip(
            "GDAL-style polygonization: segments as filled vector paths.\n"
            "Open in Illustrator or Inkscape."
        )
        self._export_svg_btn.clicked.connect(self._export_svg)

        self._export_brushstroke_btn = QPushButton("Export Brushstroke SVG")
        self._export_brushstroke_btn.setEnabled(False)
        self._export_brushstroke_btn.setToolTip(
            "SVG with randomized path jitter — hand-painted feel."
        )
        self._export_brushstroke_btn.clicked.connect(self._export_brushstroke_svg)

        export_inner.addWidget(self._export_png_btn)
        export_inner.addWidget(self._export_value_btn)
        export_inner.addWidget(self._export_svg_btn)
        export_inner.addWidget(self._export_brushstroke_btn)
        layout.addWidget(export_card)

        layout.addStretch()

        scroll.setWidget(content)

        outer = QVBoxLayout(sidebar)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(scroll)

        return sidebar

    def _build_canvas_area(self) -> QSplitter:
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(6)
        splitter.setStyleSheet("""
            QSplitter::handle { background: #242220; border-radius: 3px; }
            QSplitter::handle:hover { background: #f97316; }
        """)

        self._orig_panel = ImagePanel("Original")
        self._result_panel = ImagePanel("Result")

        splitter.addWidget(self._orig_panel)
        splitter.addWidget(self._result_panel)
        splitter.setContentsMargins(14, 14, 14, 14)
        splitter.setSizes([1, 1])
        return splitter

    def _register_shortcuts(self):
        for key, slot in [
            ("Ctrl+O",       self._load_image),
            ("Ctrl+S",       self._export_png),
            ("Ctrl+Shift+S", self._export_svg),
            ("Ctrl+Shift+P", self._export_palette_png),
            ("Ctrl++",       self._zoom_in),
            ("Ctrl+=",       self._zoom_in),
            ("Ctrl+-",       self._zoom_out),
            ("Ctrl+0",       self._zoom_reset),
            ("F11",          self._toggle_maximize),
            ("Ctrl+M",       self.showMinimized),
        ]:
            sc = QShortcut(QKeySequence(key), self)
            sc.activated.connect(slot)

    # ── Helper builders ────────────────────────────────────────────────────────

    def _section(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setObjectName("section")
        return lbl

    def _card(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("card")
        return frame

    def _thin_sep(self) -> QFrame:
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        return line

    def _slider_row(
        self, label: str, lo: int, hi: int, default: int,
        parent_layout: QVBoxLayout, connect_render: bool = True
    ) -> tuple[QSlider, QLabel]:
        row_widget = QWidget()
        row_widget.setStyleSheet("background: transparent;")
        row = QHBoxLayout(row_widget)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)

        lbl = QLabel(label)
        lbl.setStyleSheet("color: #6a6865; font-size: 12px; background: transparent;")

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

    # ── Device label helper ────────────────────────────────────────────────────

    def _set_device_label(self, text: str) -> None:
        self._title_bar.device_lbl.setText(text)

    # ── Slots ──────────────────────────────────────────────────────────────────

    def _toggle_maximize(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def _zoom_in(self):
        self._orig_panel.zoom_in()
        self._result_panel.zoom_in()
        self._status_bar.showMessage(f"Zoom: {int(self._result_panel.zoom * 100)}%")

    def _zoom_out(self):
        self._orig_panel.zoom_out()
        self._result_panel.zoom_out()
        self._status_bar.showMessage(f"Zoom: {int(self._result_panel.zoom * 100)}%")

    def _zoom_reset(self):
        self._orig_panel.reset_zoom()
        self._result_panel.reset_zoom()
        self._status_bar.showMessage("Zoom reset to fit")

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
        self._raw_masks = self._masks = None
        self._color_layer = self._tonal_layer = self._edge_layer = None
        self._current_palette = None
        self._orig_panel.reset_zoom()
        self._result_panel.reset_zoom()
        self._orig_panel.set_image(self._image_rgb)
        self._result_panel.clear()
        self._analyze_btn.setText("Analyze ▶")
        self._analyze_btn.setEnabled(True)
        self._export_png_btn.setEnabled(False)
        self._export_value_btn.setEnabled(False)
        self._export_svg_btn.setEnabled(False)
        self._export_brushstroke_btn.setEnabled(False)
        self._export_palette_btn.setEnabled(False)
        self._pigment_lbl.hide()
        h, w = self._image_rgb.shape[:2]
        optimal_min_area = max(100, min(5000, w * h // 2000))
        self._min_area_slider.setValue(optimal_min_area)
        self._status_bar.showMessage(f"Loaded: {Path(path).name}  ·  {w} × {h} px")

    def _run_analysis(self):
        if self._image_rgb is None:
            return
        prompt = self._prompt_edit.text().strip() or "every object and its edges"
        self._analyze_btn.setEnabled(False)
        self._anim_timer.start()
        self._worker = AnalysisWorker(
            self._segmenter, self._image_rgb, self._min_area_slider.value(), prompt
        )
        self._worker.progress.connect(self._status_bar.showMessage)
        self._worker.finished.connect(self._on_analysis_done)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_analysis_done(self, results: dict):
        self._anim_timer.stop()
        self._raw_masks = results["masks"]
        self._analyze_btn.setText("Re-analyze ▶")
        self._analyze_btn.setEnabled(True)
        if "device" in results:
            device_str = "GPU (CUDA)" if results["device"] == "cuda" else "CPU"
            self._set_device_label(device_str)
        self._render()
        self._export_png_btn.setEnabled(True)
        self._export_svg_btn.setEnabled(True)
        self._export_brushstroke_btn.setEnabled(True)

    def _on_error(self, msg: str):
        self._anim_timer.stop()
        self._analyze_btn.setEnabled(True)
        self._status_bar.showMessage(f"Error: {msg}")

    def _animate_btn(self):
        self._anim_dots = (self._anim_dots + 1) % 4
        self._analyze_btn.setText(f"Analyzing{'.' * self._anim_dots}")

    def _schedule_render(self):
        if self._raw_masks is not None:
            self._render_timer.start(120)

    def _update_overlays(self):
        self._result_panel.set_overlays(
            self._chk_thirds.isChecked(),
            self._chk_spiral.isChecked(),
        )

    def _render(self):
        if self._image_rgb is None or self._raw_masks is None:
            return

        self._masks = self._colorizer.merge_similar_masks(
            self._raw_masks, self._image_rgb, self._merge_slider.value()
        )

        palette, labels = self._colorizer.quantize(
            self._image_rgb, self._color_slider.value()
        )
        self._current_palette = palette

        self._color_layer = self._colorizer.colorize_masks(
            self._masks, palette, labels, self._image_rgb.shape, self._image_rgb
        )

        cartoon_on = self._chk_cartoon_layer.isChecked()

        if cartoon_on:
            # cartoon_composite bakes flat base + ink lines together; no separate edge pass
            color_for_composite = self._analyzer.cartoon_composite(
                self._image_rgb, self._edge_slider.value()
            )
        elif self._chk_comp.isChecked():
            color_for_composite = self._colorizer.complementary_layer(self._color_layer)
        else:
            color_for_composite = self._color_layer

        self._tonal_layer = self._analyzer.tonal_map(
            self._image_rgb, self._tonal_slider.value()
        )
        self._edge_layer = self._analyzer.edge_map(
            self._image_rgb, self._masks, self._edge_slider.value(),
            self._edge_mode.currentText().lower()
        )

        composite = self._exporter.composite(
            color_for_composite, self._tonal_layer, self._edge_layer,
            show_color=self._chk_color.isChecked() or cartoon_on,
            show_tonal=self._chk_tonal.isChecked(),
            # Don't add a second edge pass when cartoon already has lines baked in
            show_edges=self._chk_edges.isChecked() and not cartoon_on,
        )

        if self._chk_temp.isChecked():
            temp_layer = self._analyzer.temperature_map(self._image_rgb, self._masks)
            composite = self._exporter.blend_temperature(composite, temp_layer, opacity=0.45)

        self._result_panel.set_image(composite)
        self._result_panel.set_overlays(
            self._chk_thirds.isChecked(),
            self._chk_spiral.isChecked(),
        )

        lum = (
            0.2126 * palette[:, 0].astype(float)
            + 0.7152 * palette[:, 1].astype(float)
            + 0.0722 * palette[:, 2].astype(float)
        )
        self._palette_bar.set_colors(palette[np.argsort(lum)])
        self._export_palette_btn.setEnabled(True)
        self._export_value_btn.setEnabled(True)

        if self._pigments_data:
            matches = self._exporter.nearest_pigments(palette, self._pigments_data)
            names = ", ".join(dict.fromkeys(m["name"] for m in matches))
            self._pigment_lbl.setText(names)
            self._pigment_lbl.show()

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
        cartoon_on = self._chk_cartoon_layer.isChecked()
        if cartoon_on:
            color_for_export = self._analyzer.cartoon_composite(
                self._image_rgb, self._edge_slider.value()
            )
        elif self._chk_comp.isChecked():
            color_for_export = self._colorizer.complementary_layer(self._color_layer)
        else:
            color_for_export = self._color_layer
        composite = self._exporter.composite(
            color_for_export, self._tonal_layer, self._edge_layer,
            show_color=self._chk_color.isChecked() or cartoon_on,
            show_tonal=self._chk_tonal.isChecked(),
            show_edges=self._chk_edges.isChecked() and not cartoon_on,
        )
        if self._chk_temp.isChecked() and self._masks:
            temp_layer = self._analyzer.temperature_map(self._image_rgb, self._masks)
            composite = self._exporter.blend_temperature(composite, temp_layer)
        self._exporter.save_png(composite, path)
        self._status_bar.showMessage(f"Saved PNG: {path}")

    def _export_value_study(self):
        if self._tonal_layer is None:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Value Study", "artsegment_values.png", "PNG (*.png)"
        )
        if not path:
            return
        self._exporter.save_value_study_png(self._tonal_layer, path)
        self._status_bar.showMessage(f"Saved value study: {path}")

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

    def _export_brushstroke_svg(self):
        if self._color_layer is None or self._masks is None:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Brushstroke SVG", "artsegment_brushstroke.svg", "SVG (*.svg)"
        )
        if not path:
            return
        self._exporter.save_brushstroke_svg(self._color_layer, self._masks, path)
        self._status_bar.showMessage(f"Saved brushstroke SVG: {path}")

    def _export_palette_png(self):
        if self._current_palette is None:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Palette PNG", "artsegment_palette.png", "PNG (*.png)"
        )
        if not path:
            return
        self._exporter.save_palette_png(self._current_palette, path)
        self._status_bar.showMessage(f"Saved palette PNG: {path}")
