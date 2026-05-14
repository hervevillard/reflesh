# Dependencies

Requires Python 3.12+ and a CUDA-capable GPU (CPU works but SAM 3.1 segmentation is very slow).
SAM 3.1 is accessed via the native `sam3` package installed from GitHub — not via `transformers`.
The model is gated on HuggingFace; users must request access and authenticate before first use.

**Critical: torch must be installed from the PyTorch CUDA index.** PyPI only distributes CPU-only torch wheels. Always use:
```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu128
```

## Key constraints

| Package | Constraint | Reason |
|---|---|---|
| `numpy` | `>=1.26,<2` | sam3 hard-pins numpy below 2.0 |
| `einops` | required | imported by sam3 model internals at runtime (listed as optional in sam3 but required) |
| `psutil` | required | imported unconditionally at the top of `sam3/model/sam3_video_predictor.py` |
| `opencv-python-headless` | `<4.12` | headless avoids Qt clash with PyQt6; `<4.12` keeps numpy<2 compatible |
| `torchvision` | `>=0.22.0` | must match torch version (2.7→0.22, 2.8→0.23, 2.9→0.24, 2.10→0.25, 2.11→0.26) |
| `triton` | NOT on Windows | no Windows wheels exist anywhere — use `patch_sam3.bat` instead |

---

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
