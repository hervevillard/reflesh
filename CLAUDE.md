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
ui/
  theme.py              Full QSS dark-warm stylesheet (Tailwind stone + orange palette)
  image_panel.py        ImagePanel widget — scaled image display with label tag
  main_window.py        MainWindow — sidebar layout, AnalysisWorker (QThread), PaletteBar
core/
  segmenter.py          SAM 3.1 via native sam3 package (build_sam3_image_model + Sam3Processor)
  colorizer.py          Global k-means (MiniBatchKMeans) → per-segment dominant color
  analyzer.py           LAB L-channel tonal map + Canny/semantic edge map
  exporter.py           PNG composite + SVG polygonization (GDAL-inspired)
```

## Processing pipeline

1. **Load image** → stored as `np.ndarray` (RGB uint8)
2. **Analyze** (runs in `AnalysisWorker` QThread):
   - User enters a concept prompt (e.g. "object", "sky", "figure")
   - `build_sam3_image_model()` + `Sam3Processor.set_text_prompt(prompt)` → list of mask dicts, cached
3. **Render** (main thread, debounced 120 ms on slider change):
   - `Colorizer.quantize()` → global k-means palette + per-pixel labels
   - `Colorizer.colorize_masks()` → flat solid color per segment
   - `Analyzer.tonal_map()` → posterized LAB L-channel
   - `Analyzer.edge_map()` → Canny + SAM 3.1 contours combined
   - `Exporter.composite()` → layer blend → displayed in result panel
4. **Export** → PNG (current composite) or SVG (filled vector paths per segment)

## Key design decisions

- **SAM 3.1 runs once per image+prompt** — masks are cached; all slider adjustments re-render from cached masks without re-running SAM 3.1. Only "Min area" or prompt changes require re-analyzing.
- **SAM 3.1 output normalization** — `segmenter._normalize()` converts the `set_text_prompt` output (masks as torch tensors) into the uniform `{"segmentation": np.bool_, "area": int, "predicted_iou": float}` dict format used throughout the codebase.
- **Text prompt drives segmentation** — SAM 3.1 is concept-based. The user types a prompt (default: "object") in the sidebar; SAM 3.1 finds all instances of that concept in the image.
- **Global k-means, per-segment fill** — k-means runs on the whole image to build a coherent palette; each segment then takes its dominant palette color. This ensures color harmony across zones.
- **SVG export is GDAL polygonization** — each mask becomes a filled `<path>` element. The artist can open the SVG in Illustrator/Inkscape as editable vector shapes.
- **LAB L-channel for tones** — identical to analyzing a single spectral band in GIS. L ∈ [0,100] is divided into N equal steps, producing a posterized tonal map independent of hue.
- **Multiply blend for edges** — edge layer (black lines on white) is multiplied over the color layer so colored zones show through everywhere except at edges.

## Theme / styling

All styling is in `ui/theme.py` as a single QSS string `DARK_WARM`. Color tokens:
- `#0c0a09` — deepest background (sidebar, header)
- `#1c1917` — base background
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
