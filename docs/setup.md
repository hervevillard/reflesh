# Setup & Running

## Prerequisites

**HuggingFace authentication** (SAM 3.1 is a gated model):
```bash
# 1. Request access at https://huggingface.co/facebook/sam3.1  (free, instant approval)
# 2. Authenticate locally:
huggingface-cli login
# Or: copy .env.example → .env and set HF_TOKEN=hf_yourtoken
```

**SAM3 package** (not on PyPI):
```bash
pip install git+https://github.com/facebookresearch/sam3.git
# After install, apply Windows patches (triton workaround):
python patch_sam3.py
# Or double-click patch_sam3.bat
```

Requires **Python 3.12+** and **PyTorch 2.7+** (SAM3 hard dependency). SAM3 also hard-pins `numpy>=1.26,<2`.

---

## Windows — double-click launcher (recommended)

```
launch.bat
```

First run creates `venv/`, installs PyTorch with CUDA, installs all pip dependencies, installs SAM3 from GitHub, and runs `patch_sam3.py`. SAM 3.1 weights (~3.5 GB) download automatically from HuggingFace on the first "Analyze" click.

---

## Manual (any OS)

```bash
# PyTorch MUST come from the PyTorch CUDA index — PyPI only has CPU-only wheels:
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu128
pip install -r requirements.txt
pip install git+https://github.com/facebookresearch/sam3.git
python patch_sam3.py   # Windows only
python main.py
```

---

## Docker (GPU + X11)

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

---

## Windows-specific notes

- **HuggingFace symlinks warning** — Windows requires Developer Mode for symlinks. The cache works correctly without them (copies instead of symlinks). `launch.bat` suppresses the warning via `HF_HUB_DISABLE_SYMLINKS_WARNING=1`. Add this to `.env` as well.
- **torch CUDA** — must be installed from `https://download.pytorch.org/whl/cu128`, not from PyPI or corporate proxies that only mirror PyPI.
- **triton** — no Windows wheels exist on PyPI or the PyTorch wheel index. Use `patch_sam3.bat` instead.
