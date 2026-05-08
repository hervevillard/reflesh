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
        Inking-style edges: bilateral-filtered Canny (structural, noise-free) +
        SAM semantic boundaries (simplified with approxPolyDP).
        Bilateral filter kills texture noise while preserving real edges, giving
        the clean 'ink stroke' look of East-Asian line art.
        strength 0 = no edges; 1–5 = increasing thickness and edge sensitivity.
        Returns black-lines-on-white RGB array (H, W, 3).
        """
        h, w = image_rgb.shape[:2]
        if strength == 0:
            return np.full((h, w, 3), 255, dtype=np.uint8)

        # Bilateral filter: preserves real edges, suppresses texture/noise
        filtered = cv2.bilateralFilter(image_rgb, d=9, sigmaColor=75, sigmaSpace=75)
        gray = cv2.cvtColor(filtered, cv2.COLOR_RGB2GRAY)

        # Canny on the clean filtered image — high thresholds keep only strong edges
        lo = 40 + (5 - strength) * 15   # 55→40 as strength rises → more edges
        hi = lo * 3
        structural = cv2.Canny(gray, lo, hi)

        # SAM semantic boundaries — blurred mask → smooth contour → simplified strokes
        semantic = np.zeros((h, w), dtype=np.uint8)
        for m in masks:
            mask = m["segmentation"].astype(np.uint8) * 255
            blurred = cv2.GaussianBlur(mask, (7, 7), 0)
            _, smooth = cv2.threshold(blurred, 127, 255, cv2.THRESH_BINARY)
            contours, _ = cv2.findContours(
                smooth, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )
            simplified = [
                cv2.approxPolyDP(c, 0.001 * cv2.arcLength(c, True), True)
                for c in contours
                if len(c) >= 3
            ]
            cv2.drawContours(semantic, simplified, -1, 255, strength)

        combined = cv2.bitwise_or(structural, semantic)
        # Slight dilation so thin structural lines reach ink-stroke weight
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (strength, strength))
        combined = cv2.dilate(combined, kernel, iterations=1)

        inverted = cv2.bitwise_not(combined)
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
