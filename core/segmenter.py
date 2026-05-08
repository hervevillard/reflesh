import numpy as np
import torch
from sam2.build_sam import build_sam2_hf
from sam2.automatic_mask_generator import SAM2AutomaticMaskGenerator


class Segmenter:
    MODEL_ID = "facebook/sam2-hiera-base-plus"

    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self._sam2 = None
        self._generator = None

    @property
    def is_loaded(self) -> bool:
        return self._sam2 is not None

    def load(self, min_area: int = 500) -> None:
        if self._sam2 is None:
            self._sam2 = build_sam2_hf(self.MODEL_ID, device=self.device)
        self._generator = SAM2AutomaticMaskGenerator(
            self._sam2,
            points_per_side=32,
            pred_iou_thresh=0.86,
            stability_score_thresh=0.92,
            min_mask_region_area=min_area,
        )

    def segment(self, image_rgb: np.ndarray) -> list[dict]:
        if self._generator is None:
            raise RuntimeError("Call load() first.")
        with torch.inference_mode():
            masks = self._generator.generate(image_rgb)
        return sorted(masks, key=lambda m: m["area"], reverse=True)
