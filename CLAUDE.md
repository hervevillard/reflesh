# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Documentation rule

**Always update documentation when code changes.** After any code change, check whether `CLAUDE.md`, `README.md`, `Dockerfile`, `docker-compose.yml`, `requirements.txt`, and `.env.example` need updating and apply those updates in the same step. Do not wait to be asked.

## Architectural decisions — do NOT change unilaterally

**Never change the AI model, model family, or core architecture without explicit user instruction.** The choice of SAM 3.1 over SAM 2 or any other model is the user's decision. If a model integration fails, diagnose and fix the integration — do not silently swap the model.

## What this project is

**ArtSegment** — a desktop painting-reference tool for artists. It uses Meta's **SAM 3.1** AI model to segment an image into semantically meaningful zones via a text prompt, then analyzes each zone for dominant color, tonal structure (light/shadow), and edges. Output is a flattened PNG or a vector SVG the artist can use as a painting guide.

The core insight comes from GIS: just as satellite images are segmented into land-cover objects with zonal statistics, a painting can be broken into color zones, each with a dominant hue to mix.

## Running the app

**Prerequisite — HuggingFace authentication** (SAM 3.1 is a gated model):
```bash
# 1. Request access at https://huggingface.co/facebook/sam3.1  (free, instant approval)
# 2. Authenticate locally:
huggingface-cli login
# Or: copy .env.example → .env and set HF_TOKEN=hf_yourtoken
```

**Prerequisite — SAM3 package** (not on PyPI):
```bash
pip install git+https://github.com/facebookresearch/sam3.git
# After install, apply Windows patches (triton workaround):
python patch_sam3.py
# Or double-click patch_sam3.bat
```

**Requires Python 3.12+ and PyTorch 2.7+** (SAM3 hard dependency). SAM3 also hard-pins `numpy>=1.26,<2`.

**Windows — double-click launcher (recommended):**
```
launch.bat
```
First run creates `venv/`, installs PyTorch with CUDA, installs all pip dependencies, installs SAM3 from GitHub, and runs `patch_sam3.py`. SAM 3.1 weights (~3.5 GB) download automatically from HuggingFace on the first "Analyze" click.

**Manual (any OS):**
```bash
# PyTorch MUST come from the PyTorch CUDA index — PyPI only has CPU-only wheels:
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu128
pip install -r requirements.txt
pip install git+https://github.com/facebookresearch/sam3.git
python patch_sam3.py   # Windows only
python main.py
```

**Docker (GPU + X11):**
```bash
# Linux / WSL2 with WSLg
export HF_TOKEN=hf_your_token_here
docker compose up --build

# Or manually, passing your display
xhost +local:docker
docker run --gpus all \
  -e DISPLAY=$DISPLAY \
  -e HF_TOKEN=$HF_TOKEN \
  -v /tmp/.X11-unix:/tmp/.X11-unix \
  -v $(pwd)/output:/app/output \
  artsegment
```

SAM 3.1 weights are cached by HuggingFace hub (`~/.cache/huggingface/`). The `docker-compose.yml` mounts this as a named volume so weights survive container restarts.

## Architecture

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
   - `Analyzer.edge_map(mode=)` → seven selectable styles: **inking** (bilateral-filtered Canny + simplified SAM 3.1 contours), **sketch** (cv2.pencilSketch), **combined** (multiply-blended inking × sketch), **watercolor** (inking edges bloomed with Gaussian bleed), **hatching** (cross-hatch tonal lines at 0°/45°/90°/135°), **xdog** (eXtended Difference of Gaussians — pencil/woodcut/pastel, zero extra deps), **flow** (structure tensor coherency-weighted edges — painterly, follows image form)
   - `Exporter.composite()` → layer blend → displayed in result panel
4. **Export** → PNG (current composite) or SVG (filled vector paths per segment)

## Key design decisions

- **SAM 3.1 runs once per image+prompt** — masks are cached; all slider adjustments re-render from cached masks without re-running SAM 3.1. Only "Min area" or prompt changes require re-analyzing.
- **SAM 3.1 output normalization** — `segmenter._normalize()` converts the `set_text_prompt` output (masks as torch tensors) into the uniform `{"segmentation": np.bool_, "area": int, "predicted_iou": float}` dict format used throughout the codebase.
- **Text prompt drives segmentation** — SAM 3.1 is concept-based. The user types a prompt (default: "object") in the sidebar; SAM 3.1 finds all instances of that concept in the image.
- **Per-segment mean color fill** — each segment is filled with the actual mean RGB of its own pixels (not the global k-means centroid). The k-means palette is still computed for the palette bar display (color harmony reference), but segment fill uses the locally-accurate mean to avoid centroid drift across zones.
- **SVG export is GDAL polygonization** — each mask becomes a filled `<path>` element. The artist can open the SVG in Illustrator/Inkscape as editable vector shapes.
- **LAB L-channel for tones** — identical to analyzing a single spectral band in GIS. `tonal_map` uses `np.digitize` with `np.linspace` bins across the image's actual L range (L_min–L_max). N is capped to `int(L_max - L_min)` so flat/synthetic images never produce phantom empty bands. Tonal levels slider: 2–16, default 10 (standard Munsell value scale).
- **Multiply blend for edges** — edge layer (black lines on white) is multiplied over the color layer so colored zones show through everywhere except at edges. All seven edge modes output the same black-on-white format, so the blend works identically for each.
- **XDoG edges** — `Analyzer._xdog_map()` implements the eXtended Difference of Gaussians (Winnemöller et al., Adobe Research / SIGGRAPH NPAR 2011). Subtracts two Gaussians at σ and k·σ (k=1.6) to isolate edge frequencies, then applies a soft tanh threshold: above epsilon → white (no edge), below → `1 + tanh(φ·(D−ε))`. `φ` (sharpness) and `ε` (threshold) both scale with `strength`. Zero additional dependencies — pure numpy math. Produces pencil-shading, woodcut, and pastel looks depending on strength.
- **Flow edges** — `Analyzer._flow_map()` builds the gradient structure tensor J at each pixel (smoothed with integration scale σ_r), computes disc = √((J₁₁−J₂₂)²+4J₁₂²), and derives coherency = disc/(J₁₁+J₂₂). Coherency ∈ [0,1] measures how directionally organized the local gradient is: 1 = pure oriented edge, 0 = isotropic texture. Edge score = ‖∇I‖ · coherency²; percentile-thresholded (top 6–12% based on strength). Result: structural edges following the form of objects, with noise/texture suppressed. Zero additional dependencies — OpenCV Sobel + GaussianBlur only.
- **Frameless window** — `MainWindow` inherits from `qframelesswindow.FramelessMainWindow` (PyPI package `PyQt6-Frameless-Window`) when the library is installed. This handles DWM native resize/snap on Windows without any `nativeEvent` override. If the library is absent a graceful fallback to `QMainWindow` (native title bar + custom header) is used. Keyboard shortcuts are `QShortcut` objects connected via `.activated.connect(slot)` — not the positional 3-arg constructor form, which is unreliable across PyQt6 versions.
- **Segment merging** — `Colorizer.merge_similar_masks()` post-processes SAM masks by computing LAB distance between adjacent segment mean colors and union-merging those within the threshold. Runs from cached SAM output; no SAM re-run needed.
- **Complementary display** — `Colorizer.complementary_layer()` rotates HSV hue by 180° on the color layer; useful for planning shadow colors that mix opposite the light.
- **Temperature map** — `Analyzer.temperature_map()` classifies each segment as warm/cool/neutral by mean HSV hue; blended over the composite at 45% opacity.
- **Gamut mapping** — `Exporter.nearest_pigments()` matches each k-means palette color to the nearest entry in `data/pigments.json` using CIE Lab distance. Displayed as italic text below the palette swatch.
- **Composition overlays** — `ImagePanel.set_overlays()` paints rule-of-thirds grid (white semi-transparent lines) and golden spiral (4-arc approximation, orange) directly onto the scaled result pixmap.
- **Image zoom** — `ImagePanel` wraps its display label in a `QScrollArea`. `_zoom` (1.0 = fit) is applied as a multiplier on the fit-to-viewport size. Ctrl+wheel zooms in/out around the viewport center; `Ctrl++`/`Ctrl+-`/`Ctrl+0` zoom both panels simultaneously. Zoom is reset when a new image is loaded. Range: 25%–800%, step ×1.25.
- **Value study export** — `Exporter.save_value_study_png()` saves the posterized LAB L-channel as a grayscale PNG.
- **Brushstroke SVG export** — `Exporter.save_brushstroke_svg()` adds per-segment seeded random jitter (±4 px) to all contour points before writing SVG paths.

## Theme / styling

All styling is in `ui/theme.py` as a single QSS string `DARK_WARM`. Color tokens:
- `#0d0c0b` — deepest background (sidebar, header, status bar)
- `#161514` — base background
- `#1e1c1a` — sidebar card surfaces
- `#f97316` — accent orange (slider handles, value labels, checked checkboxes)
- `#9a3412` — primary button (Analyze)
- `#14532d` — success button (Export PNG)

## Dependencies

Requires Python 3.12+ and a CUDA-capable GPU (CPU works but SAM 3.1 segmentation is very slow).
SAM 3.1 is accessed via the native `sam3` package installed from GitHub — not via `transformers`.
The model is gated on HuggingFace; users must request access and authenticate before first use.

**Critical: torch must be installed from the PyTorch CUDA index.** PyPI only distributes CPU-only torch wheels. Always use:
```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu128
```

Key constraints discovered through integration (reflected in `requirements.txt`):
- **`numpy>=1.26,<2`** — sam3 hard-pins numpy below 2.0; this rules out numpy 2.x across the whole env
- **`einops`** — imported by sam3 model internals at runtime (listed as optional in sam3 but required)
- **`psutil`** — imported unconditionally at the top of `sam3/model/sam3_video_predictor.py`
- **`opencv-python-headless<4.12`** — use headless to avoid Qt clash with PyQt6; <4.12 keeps numpy<2 compatible
- **`torchvision>=0.22.0`** — must match torch (2.7→0.22, 2.8→0.23, 2.9→0.24, 2.10→0.25, 2.11→0.26)
- **`triton`** — NOT installable on Windows (no Windows wheels exist anywhere). `patch_sam3.py` patches `sam3/model/edt.py` to fall back to `cv2.distanceTransform`, which is semantically identical.

## SAM3 Windows patch system

`patch_sam3.py` / `patch_sam3.bat` apply compatibility patches to the installed sam3 package. **Re-run after every sam3 reinstall.**

```
patch_sam3.bat           ← double-click after reinstalling sam3
patch_sam3.py            ← called by the bat (and by launch.bat on first setup)
patches/
  sam3_edt_windows.py   ← patched edt.py: try/except around triton import + cv2 fallback
```

`launch.bat` calls `patch_sam3.py` automatically on first setup. If you reinstall sam3 manually, run `patch_sam3.bat` again.

To add new patches: add a file to `patches/` and add an entry to the `PATCHES` list in `patch_sam3.py`.

## Windows-specific notes

- **HuggingFace symlinks warning** — Windows requires Developer Mode for symlinks. The cache works correctly without them (copies instead of symlinks). `launch.bat` suppresses the warning via `HF_HUB_DISABLE_SYMLINKS_WARNING=1`. Add this to `.env` as well.
- **torch CUDA** — must be installed from `https://download.pytorch.org/whl/cu128`, not from PyPI or corporate proxies that only mirror PyPI.
- **triton** — no Windows wheels exist on PyPI or the PyTorch wheel index. Use `patch_sam3.bat` instead.
