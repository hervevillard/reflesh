# ArtSegment

A desktop painting-reference tool that applies GIS spatial analysis thinking to art. Load any photo, type a concept prompt, and ArtSegment uses Meta's **SAM 3.1** AI model to break it into semantically meaningful color zones — giving you a painting guide with unlimited palette levels, tonal structure, and clean edge lines.

> Inspired by the GIS workflow of segmenting satellite imagery into land-cover objects with zonal statistics. A painting is just a different kind of raster.

---

## What it does

| Feature | Description | Painter use |
|---|---|---|
| **Color zones** | SAM 3.1 segments filled with each zone's actual mean color | What hue to mix |
| **Tonal map** | LAB L-channel posterized into N levels | Where to shade |
| **Edges** | Seven selectable styles: **Inking** · **Sketch** · **Combined** · **Watercolor** · **Hatching** · **XDoG** · **Flow** | Where to draw lines |
| **Complementary** | Flips all segment hues to their complements | Shadow color planning |
| **Temperature map** | Warm/cool/neutral fill per segment (blended overlay) | Light source direction |
| **Merge similar** | Fuses adjacent segments within a LAB distance threshold | Simplify noisy results |
| **Composition overlays** | Rule of thirds grid + golden spiral arc (painted on result) | Compositional reference |
| **Gamut matching** | Maps each palette color to the nearest of 24 artist pigments | Know which paint to buy |
| **Value study export** | Saves the tonal map as a grayscale PNG | Pure light/shadow reference |
| **Brushstroke SVG** | SVG with per-path random jitter (±4 px, seeded per segment) | Hand-painted vector guide |

All color/tonal/edge layers are independently toggleable. Export as a flat **PNG**, a **grayscale value study PNG**, or a **vector SVG** (clean or brushstroke).

The color level slider is unlimited — not capped at 8 like Photoshop's Cutout filter.

---

## Requirements

- Python **3.12+**
- PyTorch **2.7+** with CUDA (CPU works but segmentation takes several minutes)
- A CUDA-capable NVIDIA GPU
- A free [HuggingFace account](https://huggingface.co/join) with access to [`facebook/sam3.1`](https://huggingface.co/facebook/sam3.1)

---

## HuggingFace token setup (one-time)

SAM 3.1 is a gated model — free to use, but requires an account and a token.

**Step 1 — Request access**
Go to [huggingface.co/facebook/sam3.1](https://huggingface.co/facebook/sam3.1) and click **Request access**. Approval is usually instant.

**Step 2 — Create a token**
Go to [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens) → **New token**:

| Field | Value |
|---|---|
| Name | anything (e.g. `artsegment`) |
| Type | **Read** ← simplest, recommended |

Click **Create token** and copy it.

**Step 3 — Authenticate**

Option A — CLI (stored permanently, recommended for local use):
```bash
huggingface-cli login   # paste token when prompted
```

Option B — `.env` file (also works for Docker):
```bash
cp .env.example .env
# edit .env and set HF_TOKEN=hf_yourtoken
```

---

## Installation

### Windows — one double-click (recommended)

```
launch.bat
```

What it does on first run:
1. Creates a local `venv/`
2. Installs PyTorch with CUDA support from `download.pytorch.org/whl/cu128`
3. Installs all other pip dependencies from `requirements.txt`
4. Installs the SAM3 package from GitHub
5. Applies Windows compatibility patches (`patch_sam3.py`)

SAM 3.1 weights (~3.5 GB) download automatically from HuggingFace on the first "Analyze" click.

> Authenticate with HuggingFace before the first run (see token setup above).

If you reinstall SAM3 manually at any point, re-apply the Windows patches:
```
patch_sam3.bat
```

### Manual (any OS)

```bash
# 1. Install PyTorch with CUDA — MUST use the PyTorch index, not PyPI:
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu128

# 2. Install remaining dependencies:
pip install -r requirements.txt

# 3. Install SAM3 (not on PyPI):
pip install git+https://github.com/facebookresearch/sam3.git

# 4. Apply Windows patches (Windows only):
python patch_sam3.py

# 5. Run:
python main.py
```

### Docker (GPU + X11)

```bash
# 1. Get a HuggingFace token and export it
export HF_TOKEN=hf_your_token_here

# 2. Allow Docker to use your display (Linux; not needed on WSL2 + WSLg)
xhost +local:docker

# 3. Build and run
docker compose up --build
```

To avoid re-downloading SAM 3.1 weights on every container start, `docker-compose.yml` persists the HuggingFace cache in a named volume (`hf_cache`).

---

## Dependency notes

| Issue | Fix |
|---|---|
| `torch` from PyPI is CPU-only | Always install torch via `--index-url https://download.pytorch.org/whl/cu128` |
| `numpy>=2` breaks sam3 | sam3 hard-requires `numpy<2`; `requirements.txt` pins this |
| `opencv-python` clashes with PyQt6 | Use `opencv-python-headless<4.12` instead |
| `triton` has no Windows wheels | `patch_sam3.bat` patches `sam3/model/edt.py` with a cv2 fallback |

---

## Usage

1. Click **Open Image** and load a photo (PNG, JPG, TIFF, WebP supported)
2. Type a **Concept prompt** in the sidebar (e.g. `sky`, `figure`, `foliage`, `object`)
3. Optionally adjust **Min area** to filter out noise, then click **Analyze**
4. SAM 3.1 segments the image (GPU: ~10–30 s · CPU: several minutes)
5. Adjust controls live — no re-analyzing needed:
   - **Color levels** — number of palette colors (2–64)
   - **Tonal levels** — number of light/shadow steps (2–12)
   - **Edge strength** — how prominent the edge lines are (0–5)
   - **Edge style** — Inking / Sketch / Combined / Watercolor / Hatching
   - **Merge similar** — fuse adjacent segments within this LAB distance (0 = off)
6. Toggle layers: **Color zones / Tonal map / Edges / Complementary / Temperature map**
7. Enable **Composition** overlays: Rule of thirds / Golden spiral
8. Read the palette swatches and nearest artist pigment names below them
9. Export:
   - **Export PNG** — current composite
   - **Export Value Study PNG** — grayscale tonal map
   - **Export SVG** — filled vector paths per segment
   - **Export Brushstroke SVG** — same with hand-painted path jitter

> Changing the **Concept prompt** or **Min area** requires clicking Analyze again. All other controls re-render instantly from cached masks.

---

## Architecture

```
main.py               App entry point
patch_sam3.py         Applies Windows sam3 compatibility patches after install
patches/
  sam3_edt_windows.py  Patched edt.py: triton guarded with cv2 fallback
data/
  pigments.json       24 artist paint colors (RGB + name) for gamut matching
ui/
  theme.py            QSS dark-warm stylesheet (Tailwind stone + orange palette)
  image_panel.py      Scaled image canvas + composition overlays (thirds/spiral)
  main_window.py      Frameless main window, sidebar, QThread worker, palette bar
core/
  segmenter.py        SAM 3.1 via native sam3 package
  colorizer.py        k-means quantization, per-segment fill, complementary layer, mask merging
  analyzer.py         LAB tonal map, 5 edge styles, temperature map
  exporter.py         PNG/value-study/SVG/brushstroke export, pigment matching
```

### GDAL concepts borrowed

| GIS concept | Implementation |
|---|---|
| Zonal statistics | Dominant palette color extracted per SAM 3.1 segment |
| Band analysis | LAB L-channel treated as a standalone luminance band |
| Polygonize | SVG export — each mask becomes a filled `<path>` element |
| Reclassify | k-means maps pixel values to N discrete color categories |

---

## SAM 3.1

[SAM 3](https://ai.meta.com/blog/segment-anything-model-3/) (Meta, November 2025 · updated SAM 3.1 March 2026) is Meta's latest segmentation model. It uses text prompts to exhaustively find all instances of an open-vocabulary concept in an image. ArtSegment passes the user's concept prompt (e.g. "object", "figure", "sky") to SAM 3.1 via its native Python package.

Model: [`facebook/sam3.1`](https://huggingface.co/facebook/sam3.1) — gated, free to access after approval.

---

## License

MIT
