import numpy as np
import cv2
from skimage.color import rgb2lab


class Analyzer:
    def tonal_map(self, image_rgb: np.ndarray, n_levels: int) -> np.ndarray:
        """
        Posterize the LAB L-channel into n_levels tonal zones.
        Like isolating a single spectral band in GIS — here the 'luminance band'.
        Returns an RGB grayscale array (H, W, 3).
        """
        lab = rgb2lab(image_rgb.astype(np.float32) / 255.0)
        L = lab[:, :, 0]  # 0–100
        step = 100.0 / n_levels
        level_idx = np.floor(L / step).clip(0, n_levels - 1).astype(int)
        gray_values = (level_idx / (n_levels - 1) * 255).astype(np.uint8)
        return np.stack([gray_values] * 3, axis=-1)

    def edge_map(
        self, image_rgb: np.ndarray, masks: list[dict], strength: int
    ) -> np.ndarray:
        """
        Combine Canny detail edges with SAM semantic contours.
        Analogous to GDAL polygonize — segment boundaries become crisp vector-like lines.
        Returns black-lines-on-white RGB array (H, W, 3).
        """
        gray = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2GRAY)

        # Fine texture edges via Canny
        lo, hi = max(10, 20 * strength), max(30, 60 * strength)
        canny = cv2.Canny(gray, lo, hi) if strength > 0 else np.zeros_like(gray)

        # Semantic segment boundaries (the GDAL polygonize layer)
        semantic = np.zeros(image_rgb.shape[:2], dtype=np.uint8)
        for m in masks:
            contours, _ = cv2.findContours(
                m["segmentation"].astype(np.uint8),
                cv2.RETR_EXTERNAL,
                cv2.CHAIN_APPROX_SIMPLE,
            )
            cv2.drawContours(semantic, contours, -1, 255, 2)

        combined = cv2.bitwise_or(canny, semantic)
        inverted = cv2.bitwise_not(combined)  # black lines on white background
        return np.stack([inverted] * 3, axis=-1)

    def zonal_stats(self, image_rgb: np.ndarray, masks: list[dict]) -> list[dict]:
        """
        Per-segment statistics (mean RGB, mean luminance).
        GIS zonal statistics applied to image bands.
        """
        stats = []
        lab = rgb2lab(image_rgb.astype(np.float32) / 255.0)
        for m in masks:
            seg = m["segmentation"]
            pixels = image_rgb[seg]
            L_vals = lab[:, :, 0][seg]
            stats.append({
                "area": m["area"],
                "mean_rgb": pixels.mean(axis=0).astype(int).tolist(),
                "mean_L": float(L_vals.mean()),
            })
        return stats
