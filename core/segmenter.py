import numpy as np


class Segmenter:
    """
    Wraps Meta's SAM 3.1 via the native sam3 package.

    SAM 3.1 is gated on HuggingFace; authenticate once with:
        huggingface-cli login
    or set HF_TOKEN in .env
    """

    def __init__(self):
        self._processor = None
        self._min_area = 500
        self._device: str | None = None

    @property
    def is_loaded(self) -> bool:
        return self._processor is not None

    def load(self, min_area: int = 500) -> None:
        self._min_area = min_area
        if not self.is_loaded:
            import torch
            self._device = "cuda" if torch.cuda.is_available() else "cpu"
            try:
                from sam3.model_builder import build_sam3_image_model, download_ckpt_from_hf
                from sam3.model.sam3_image_processor import Sam3Processor
                if self._device == "cuda":
                    torch.autocast("cuda", dtype=torch.bfloat16).__enter__()
                ckpt = download_ckpt_from_hf(version="sam3.1")
                model = build_sam3_image_model(
                    checkpoint_path=ckpt,
                    device=self._device,
                )
                self._processor = Sam3Processor(model, confidence_threshold=0.5)
            except ImportError as _exc:
                raise RuntimeError(
                    f"SAM3 import failed: {_exc}\n\n"
                    "Fix options:\n"
                    "  1. Keep the sam3 source folder and reinstall:\n"
                    "       pip install -e ./sam3\n"
                    "  2. Install directly from GitHub (no local folder needed):\n"
                    "       pip install git+https://github.com/facebookresearch/sam3.git"
                ) from _exc
            except Exception as exc:
                msg = str(exc)
                if "gated" in msg.lower() or "access" in msg.lower() or "401" in msg:
                    raise RuntimeError(
                        "Access denied to facebook/sam3.1.\n\n"
                        "Fix:\n"
                        "  1. Go to https://huggingface.co/facebook/sam3.1 and request access\n"
                        "  2. Run:  huggingface-cli login\n"
                        "  3. Paste a token from https://huggingface.co/settings/tokens\n"
                        "  4. Or set HF_TOKEN= in your .env file\n"
                        "  5. Click Analyze again"
                    ) from exc
                raise

    def segment(self, image_rgb: np.ndarray, prompt: str) -> list[dict]:
        if self._processor is None:
            raise RuntimeError("Call load() first.")
        from PIL import Image as PILImage
        pil_img = PILImage.fromarray(image_rgb)
        inference_state = self._processor.set_image(pil_img)
        self._processor.reset_all_prompts(inference_state)
        results = self._processor.set_text_prompt(state=inference_state, prompt=prompt)
        return self._normalize(results)

    def _normalize(self, results: dict) -> list[dict]:
        """
        Convert SAM3 set_text_prompt output to the uniform list-of-dicts format
        used throughout the rest of the codebase.
        """
        raw_masks = results.get("masks", [])
        scores = results.get("scores", [])

        masks = []
        for mask, score in zip(raw_masks, scores):
            # mask is a tensor (1, H, W) or (H, W)
            if hasattr(mask, "cpu"):
                m = mask.squeeze(0).cpu().numpy().astype(bool)
            else:
                m = np.asarray(mask, dtype=bool)
            area = int(m.sum())
            if area < self._min_area:
                continue
            s = float(score.item()) if hasattr(score, "item") else float(score)
            masks.append({"segmentation": m, "area": area, "predicted_iou": s})

        return sorted(masks, key=lambda m: m["area"], reverse=True)
