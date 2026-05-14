import numpy as np
import cv2
from skimage.color import rgb2lab


class Analyzer:
    def tonal_map(self, image_rgb: np.ndarray, n_levels: int) -> np.ndarray:
        """
        Posterize the LAB L-channel into n_levels tonal zones.
        Returns an RGB grayscale array (H, W, 3).
        """
        lab = rgb2lab(image_rgb.astype(np.float32) / 255.0)
        L = lab[:, :, 0]
        L_min, L_max = float(L.min()), float(L.max())
        n_levels = min(n_levels, max(2, int(L_max - L_min)))
        bins = np.linspace(L_min, L_max, n_levels + 1)
        level_idx = np.digitize(L, bins[1:-1])
        gray_values = (level_idx / (n_levels - 1) * 255).astype(np.uint8)
        return np.stack([gray_values] * 3, axis=-1)

    def edge_map(
        self, image_rgb: np.ndarray, masks: list[dict], strength: int, mode: str = "coloring"
    ) -> np.ndarray:
        """
        Edge rendering — four selectable styles:

          "coloring" — thin SAM boundary outlines, like a coloring-book page (default)
          "outline"  — bold marker-pen SAM boundary outlines
          "drawn"    — roughened SAM outlines, hand-sketched feel
          "cartoon"  — median blur + adaptive threshold on image pixels

        All SAM modes use morphological gradient on the mask to extract boundaries —
        no findContours, guaranteed visible output.
        strength 0 = no edges; 1–5 = increasing line weight.
        Returns black-lines-on-white RGB array (H, W, 3).
        """
        h, w = image_rgb.shape[:2]
        if strength == 0:
            return np.full((h, w, 3), 255, dtype=np.uint8)

        if mode == "outline":
            return self._outline_map(masks, strength, h, w)
        if mode == "drawn":
            return self._drawn_map(masks, strength, h, w)
        if mode == "cartoon":
            return self._cartoon_map(image_rgb, strength, h, w)
        return self._coloring_map(masks, strength, h, w)

    # ── SAM-semantic boundary methods (morphological gradient) ─────────────────
    # Pipeline for all three:
    #   seg (bool → uint8 {0,1}) → MORPH_GRADIENT → boundary ring → OR into canvas
    #   bitwise_not(canvas) → black lines on white
    # No findContours, no approxPolyDP, no drawContours: zero failure modes.

    def _coloring_map(self, masks: list[dict], strength: int, h: int, w: int) -> np.ndarray:
        """Thin SAM contours — coloring-book style."""
        canvas = np.zeros((h, w), dtype=np.uint8)
        k = 1 + strength * 2          # 3, 5, 7, 9, 11 → thin to medium
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))
        for m in masks:
            seg = m["segmentation"].astype(np.uint8)
            grad = cv2.morphologyEx(seg, cv2.MORPH_GRADIENT, kernel)
            np.maximum(canvas, grad * 255, out=canvas)
        return np.stack([cv2.bitwise_not(canvas)] * 3, axis=-1)

    def _outline_map(self, masks: list[dict], strength: int, h: int, w: int) -> np.ndarray:
        """Bold SAM contours — marker-pen / graphic-novel feel."""
        canvas = np.zeros((h, w), dtype=np.uint8)
        k = 3 + strength * 2          # 5, 7, 9, 11, 13 → medium to thick
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))
        for m in masks:
            seg = m["segmentation"].astype(np.uint8)
            grad = cv2.morphologyEx(seg, cv2.MORPH_GRADIENT, kernel)
            np.maximum(canvas, grad * 255, out=canvas)
        return np.stack([cv2.bitwise_not(canvas)] * 3, axis=-1)

    def _drawn_map(self, masks: list[dict], strength: int, h: int, w: int) -> np.ndarray:
        """Roughened SAM contours — sketchy, hand-drawn feel."""
        canvas = np.zeros((h, w), dtype=np.uint8)
        k = 1 + strength * 2
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))
        rng = np.random.default_rng(42)
        for m in masks:
            seg = m["segmentation"].astype(np.uint8)
            grad = cv2.morphologyEx(seg, cv2.MORPH_GRADIENT, kernel)
            boundary = (grad * 255).astype(np.uint8)
            # Random erosion: drop ~20% of boundary pixels to simulate an unsteady hand
            noise = rng.integers(0, 5, size=boundary.shape, dtype=np.uint8)
            boundary[noise == 0] = 0
            np.maximum(canvas, boundary, out=canvas)
        return np.stack([cv2.bitwise_not(canvas)] * 3, axis=-1)

    # ── Pixel-level edge method ────────────────────────────────────────────────

    def _cartoon_map(self, image_rgb: np.ndarray, strength: int, h: int, w: int) -> np.ndarray:
        """
        Classic cartoonizer edges: median blur + adaptive threshold.
        Responds to image contrast — folds, shadows, fine detail — not only SAM boundaries.
        """
        gray = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2GRAY)
        ksize = max(3, 9 - strength * 2)
        if ksize % 2 == 0:
            ksize += 1
        blurred = cv2.medianBlur(gray, ksize)
        C = max(2, 10 - strength * 2)
        edges = cv2.adaptiveThreshold(
            blurred, 255,
            cv2.ADAPTIVE_THRESH_MEAN_C,
            cv2.THRESH_BINARY,
            blockSize=9,
            C=C,
        )
        return np.stack([edges] * 3, axis=-1)

    # ── Full cartoon composite ─────────────────────────────────────────────────

    def cartoon_composite(self, image_rgb: np.ndarray, strength: int = 2) -> np.ndarray:
        """
        Complete cartoon transform: flat-color base with ink lines baked in.

        Base: cv2.edgePreservingFilter (RECURS_FILTER) — smooths flat areas
        while keeping hard edges crisp. Preserves image structure and texture;
        does NOT blur indiscriminately like a bilateral filter.

        Lines: adaptive threshold (same as Cartoon edge mode) multiplied over
        the base so colors show through except at the black ink lines.

        Returns RGB uint8, same shape as input.
        """
        # Edge-preserving base: flat color areas, crisp boundaries, texture kept
        base = cv2.edgePreservingFilter(
            image_rgb, flags=cv2.RECURS_FILTER, sigma_s=60, sigma_r=0.4
        )
        # Ink lines: adaptive threshold on median-blurred gray
        gray = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2GRAY)
        ksize = max(3, 9 - strength * 2)
        if ksize % 2 == 0:
            ksize += 1
        blurred = cv2.medianBlur(gray, ksize)
        C = max(2, 10 - strength * 2)
        edges = cv2.adaptiveThreshold(
            blurred, 255,
            cv2.ADAPTIVE_THRESH_MEAN_C,
            cv2.THRESH_BINARY,
            blockSize=9,
            C=C,
        )
        edges_rgb = np.stack([edges] * 3, axis=-1)
        # Multiply: white (255) = no change; black (0) = black line
        return (base.astype(np.float32) * edges_rgb.astype(np.float32) / 255).astype(np.uint8)

    # ── Analytical layers ──────────────────────────────────────────────────────

    def temperature_map(self, image_rgb: np.ndarray, masks: list[dict]) -> np.ndarray:
        """
        Per-segment warm/cool/neutral classification.
        Returns RGB array (H, W, 3).
        """
        h, w = image_rgb.shape[:2]
        result = np.full((h, w, 3), [122, 120, 117], dtype=np.uint8)
        hsv = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2HSV).astype(np.float32)

        WARM    = np.array([232, 115,  74], dtype=np.uint8)
        COOL    = np.array([ 74, 123, 232], dtype=np.uint8)
        NEUTRAL = np.array([122, 120, 117], dtype=np.uint8)

        for m in masks:
            seg = m["segmentation"]
            seg_hsv = hsv[seg]
            mean_s = seg_hsv[:, 1].mean()
            mean_h = seg_hsv[:, 0].mean() * 2.0
            if mean_s < 40:
                color = NEUTRAL
            elif mean_h <= 60 or mean_h >= 300:
                color = WARM
            elif 120 <= mean_h <= 270:
                color = COOL
            else:
                color = NEUTRAL
            result[seg] = color

        return result

    def zonal_stats(self, image_rgb: np.ndarray, masks: list[dict]) -> list[dict]:
        """Per-segment statistics (mean RGB, mean luminance)."""
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
