# Architecture

## File tree

```
main.py                 Entry point — creates QApplication, applies theme, shows MainWindow
patch_sam3.py           Applies Windows sam3 compatibility patches after install
patch_sam3.bat          Convenience launcher for patch_sam3.py (re-run after sam3 reinstall)
patches/
  sam3_edt_windows.py   Patched sam3/model/edt.py: triton guarded with cv2.distanceTransform fallback
data/
  pigments.json         24 artist paint colors (RGB + name) for gamut matching
ui/
  theme.py              Full QSS dark-warm stylesheet (Tailwind stone + orange palette)
  image_panel.py        ImagePanel widget — scaled display + zoom (Ctrl+wheel, 25%–800%) + composition overlays (thirds/spiral)
  main_window.py        MainWindow — frameless (qframelesswindow) + sidebar + AnalysisWorker (QThread) + PaletteBar + QSplitter canvas
core/
  segmenter.py          SAM 3.1 via native sam3 package (build_sam3_image_model + Sam3Processor)
  colorizer.py          k-means quantization, per-segment color fill, complementary_layer, merge_similar_masks
  analyzer.py           Tonal map, 7 edge styles (inking/sketch/combined/watercolor/hatching/xdog/flow), temperature_map
  exporter.py           PNG composite, SVG polygonization, value study PNG, brushstroke SVG, nearest_pigments
```

## Processing pipeline

1. **Load image** → stored as `np.ndarray` (RGB uint8)
2. **Analyze** (runs in `AnalysisWorker` QThread):
   - User enters a concept prompt (e.g. "object", "sky", "figure")
   - `build_sam3_image_model()` + `Sam3Processor.set_text_prompt(prompt)` → list of mask dicts, cached
3. **Render** (main thread, debounced 120 ms on slider change):
   - `Colorizer.quantize()` → global k-means palette + per-pixel labels
   - `Colorizer.colorize_masks()` → flat solid color per segment (actual mean pixel color of each zone)
   - `Analyzer.tonal_map()` → posterized LAB L-channel
   - `Analyzer.edge_map(mode=)` → four selectable styles: **coloring** (thin antialiased SAM contours), **outline** (bold marker-pen SAM contours), **drawn** (path-jittered SAM contours), **cartoon** (`medianBlur` + `adaptiveThreshold` on image pixels)
   - `Exporter.composite()` → layer blend → displayed in result panel
4. **Export** → PNG (current composite) or SVG (filled vector paths per segment)

## Key design decisions

- **SAM 3.1 runs once per image+prompt** — masks are cached; all slider adjustments re-render from cached masks without re-running SAM 3.1. Only "Min area" or prompt changes require re-analyzing.
- **SAM 3.1 output normalization** — `segmenter._normalize()` converts the `set_text_prompt` output (masks as torch tensors) into the uniform `{"segmentation": np.bool_, "area": int, "predicted_iou": float}` dict format used throughout the codebase.
- **Text prompt drives segmentation** — SAM 3.1 is concept-based. The user types a prompt (default: "every object and its edges") in the sidebar; SAM 3.1 finds all instances of that concept in the image.
- **Per-segment mean color fill** — each segment is filled with the actual mean RGB of its own pixels (not the global k-means centroid). The k-means palette is still computed for the palette bar display (color harmony reference), but segment fill uses the locally-accurate mean to avoid centroid drift across zones.
- **SVG export is GDAL polygonization** — each mask becomes a filled `<path>` element. The artist can open the SVG in Illustrator/Inkscape as editable vector shapes.
- **LAB L-channel for tones** — identical to analyzing a single spectral band in GIS. `tonal_map` uses `np.digitize` with `np.linspace` bins across the image's actual L range (L_min–L_max). N is capped to `int(L_max - L_min)` so flat/synthetic images never produce phantom empty bands. Tonal levels slider: 2–16, default 10 (standard Munsell value scale).
- **Multiply blend for edges** — edge layer (black lines on white) is multiplied over the color layer so colored zones show through everywhere except at edges. All three edge modes output the same black-on-white format, so the blend works identically for each.
- **SAM-semantic edge modes** — three of the four modes derive lines from SAM segment boundaries using `cv2.MORPH_GRADIENT` (dilation − erosion on the boolean mask cast to uint8). No `findContours`, no `approxPolyDP`, no `drawContours` — zero failure modes. `np.maximum` OR-accumulates boundary pixels across all masks into a single canvas, then `bitwise_not` gives black-on-white. Kernel is `MORPH_ELLIPSE`. **Coloring**: k = 1 + strength×2 (3–11 px), thin outlines. **Outline**: k = 3 + strength×2 (5–13 px), bold outlines. **Drawn**: same kernel as Coloring but ~20% of boundary pixels randomly zeroed (seeded RNG 42) to simulate an unsteady hand.
- **Cartoon edge mode** — `Analyzer._cartoon_map()`: `medianBlur` (ksize 7→3 px decreasing with strength) suppresses noise; `adaptiveThreshold` (blockSize=9, C 8→2) binarizes local contrast into black edge lines. Responds to folds, shadows, and fine detail within segments unlike the SAM-boundary modes.
- **Cartoonize layer** — `Analyzer.cartoon_composite()`: (1) `cv2.edgePreservingFilter(RECURS_FILTER, sigma_s=60, sigma_r=0.4)` smooths flat areas; (2) `medianBlur + adaptiveThreshold` generates adaptive ink lines; (3) multiply-blended. When the Cartoonize checkbox is on, `_render()` uses this composite as the color base and disables the separate edge-layer pass. Tonal map and temperature overlays still apply on top.
- **Frameless window** — `MainWindow` inherits from `qframelesswindow.FramelessMainWindow` when available; graceful fallback to `QMainWindow`. Keyboard shortcuts use `QShortcut` with `.activated.connect(slot)`. **Window shortcuts:** `F11` toggles maximize/restore; `Ctrl+M` minimizes.
- **Segment merging** — `Colorizer.merge_similar_masks()` computes LAB distance between adjacent segment mean colors and union-merges those within the threshold. Runs from cached SAM output; no SAM re-run needed.
- **Complementary display** — `Colorizer.complementary_layer()` rotates HSV hue by 180°; useful for planning shadow colors.
- **Temperature map** — `Analyzer.temperature_map()` classifies each segment as warm/cool/neutral by mean HSV hue; blended at 45% opacity.
- **Gamut mapping** — `Exporter.nearest_pigments()` matches each k-means palette color to the nearest entry in `data/pigments.json` using CIE Lab distance.
- **Palette export** — `Exporter.save_palette_png()` saves swatches sorted darkest → lightest by sRGB relative luminance (L = 0.2126·R + 0.7152·G + 0.0722·B). The sidebar `PaletteBar` applies the same sort.
- **Composition overlays** — `ImagePanel.set_overlays()` paints rule-of-thirds grid and golden spiral (4-arc approximation) directly onto the scaled result pixmap.
- **Image zoom** — `ImagePanel` wraps its label in a `QScrollArea`. Range: 25%–800%, step ×1.25. `Ctrl+wheel` zooms around viewport center; `Ctrl++`/`Ctrl+-`/`Ctrl+0` zoom both panels simultaneously.
- **Value study export** — `Exporter.save_value_study_png()` saves the posterized LAB L-channel as a grayscale PNG.
- **Brushstroke SVG export** — `Exporter.save_brushstroke_svg()` adds per-segment seeded random jitter (±4 px) to all contour points.
