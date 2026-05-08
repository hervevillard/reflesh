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
        # Bin across the image's actual tonal range so all N levels are always
        # visible — fixed [0,100] bins leave empty bands for images without pure
        # black/white, silently producing fewer levels than requested.
        L_min, L_max = float(L.min()), float(L.max())
        # Cap to the image's actual tonal range: a flat image can't support more
        # distinct steps than its L span (in integer units).
        n_levels = min(n_levels, max(2, int(L_max - L_min)))
        bins = np.linspace(L_min, L_max, n_levels + 1)
        level_idx = np.digitize(L, bins[1:-1])  # [0, n_levels-1]
        gray_values = (level_idx / (n_levels - 1) * 255).astype(np.uint8)
        return np.stack([gray_values] * 3, axis=-1)

    def edge_map(
        self, image_rgb: np.ndarray, masks: list[dict], strength: int, mode: str = "inking"
    ) -> np.ndarray:
        """
        Edge detection with seven selectable styles:
          "inking"    — bilateral-filtered Canny + SAM contours (clean ink strokes)
          "sketch"    — cv2.pencilSketch (naturalistic shaded strokes)
          "combined"  — both multiplied together (ink structure + sketch texture)
          "watercolor"— soft bleeding edges, like ink on wet paper
          "hatching"  — cross-hatch tonal lines at 0°/45°/90°/135°
          "xdog"      — eXtended Difference of Gaussians (pencil/woodcut, Adobe Research)
          "flow"      — structure tensor coherency-weighted edges (painterly, follows form)
        strength 0 = no edges; 1–5 = increasing sensitivity/weight.
        Returns black-lines-on-white RGB array (H, W, 3).
        """
        h, w = image_rgb.shape[:2]
        if strength == 0:
            return np.full((h, w, 3), 255, dtype=np.uint8)

        if mode == "inking":
            return self._inking_map(image_rgb, masks, strength)
        if mode == "sketch":
            return self._sketch_map(image_rgb, strength)
        if mode == "watercolor":
            return self._watercolor_map(image_rgb, masks, strength)
        if mode == "hatching":
            return self._hatching_map(image_rgb, strength)
        if mode == "xdog":
            return self._xdog_map(image_rgb, strength)
        if mode == "flow":
            return self._flow_map(image_rgb, strength)
        # combined — multiply blend
        inking = self._inking_map(image_rgb, masks, strength)
        sketch = self._sketch_map(image_rgb, strength)
        return (inking.astype(np.float32) * sketch.astype(np.float32) / 255).astype(np.uint8)

    def _inking_map(self, image_rgb: np.ndarray, masks: list[dict], strength: int) -> np.ndarray:
        h, w = image_rgb.shape[:2]

        # Bilateral filter: sigma scales down at higher strength → less smoothing → more edges
        sigma = 75 - (strength - 1) * 10  # strength 1→75, strength 5→35
        filtered = cv2.bilateralFilter(image_rgb, d=9, sigmaColor=sigma, sigmaSpace=sigma)
        gray = cv2.cvtColor(filtered, cv2.COLOR_RGB2GRAY)

        # Canny: lo range 40–115 (strict at 1, sensitive at 5); hi=2× for balanced hysteresis
        lo = 40 + (5 - strength) * 19   # strength 1→116, strength 5→40
        hi = lo * 2
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
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (strength, strength))
        combined = cv2.dilate(combined, kernel, iterations=1)

        inverted = cv2.bitwise_not(combined)
        return np.stack([inverted] * 3, axis=-1)

    def _sketch_map(self, image_rgb: np.ndarray, strength: int) -> np.ndarray:
        sigma_s = 40 + (strength - 1) * 10
        shade   = 0.03 + (strength - 1) * 0.01
        gray, _ = cv2.pencilSketch(image_rgb, sigma_s=sigma_s, sigma_r=0.07, shade_factor=shade)
        return np.stack([gray] * 3, axis=-1)

    def _watercolor_map(self, image_rgb: np.ndarray, masks: list[dict], strength: int) -> np.ndarray:
        # Start from inking edges, then bleed them like ink on wet paper
        edges = cv2.bitwise_not(self._inking_map(image_rgb, masks, strength)[:, :, 0])
        blur_k = 2 * (strength * 4 + 3) + 1   # strength 1→15px … 5→47px
        blurred = cv2.GaussianBlur(edges.astype(np.float32), (blur_k, blur_k), blur_k * 0.4)
        combined = np.clip(np.maximum(blurred, edges.astype(np.float32)), 0, 255).astype(np.uint8)
        return np.stack([cv2.bitwise_not(combined)] * 3, axis=-1)

    def _hatching_map(self, image_rgb: np.ndarray, strength: int) -> np.ndarray:
        gray = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2GRAY).astype(np.float32) / 255.0
        h, w = gray.shape
        gap = max(3, 10 - strength * 2)  # line spacing: strength 1→8 … 5→0 (clamped to 3)
        ys, xs = np.meshgrid(np.arange(h), np.arange(w), indexing="ij")
        result = np.ones((h, w), dtype=np.float32)
        # 4 hatch layers at 0°/45°/90°/135° — each activates at progressively darker tones
        for thresh, angle_deg in zip([0.85, 0.65, 0.45, 0.25], [0, 45, 90, 135]):
            a = np.deg2rad(angle_deg)
            proj = xs * np.cos(a) + ys * np.sin(a)
            stripe = (proj % gap) < 1.0
            result[stripe & (gray < thresh)] = 0.0
        return np.stack([(result * 255).astype(np.uint8)] * 3, axis=-1)

    def _xdog_map(self, image_rgb: np.ndarray, strength: int) -> np.ndarray:
        # eXtended Difference of Gaussians (Winnemöller et al., Adobe Research / SIGGRAPH).
        # DoG isolates edge frequencies; XDoG soft-thresholds with tanh for a painted quality.
        # Higher phi → sharper, crisper lines. Negative epsilon → more edges visible.
        gray = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2GRAY).astype(np.float32) / 255.0
        sigma = 0.8
        k = 1.6
        phi     = 10 + (strength - 1) * 15   # strength 1→10, 5→70 (sharper at high)
        epsilon = 0.01 - (strength - 1) * 0.005  # strength 1→0.01, 5→-0.01 (more edges at high)

        g1 = cv2.GaussianBlur(gray, (0, 0), sigma)
        g2 = cv2.GaussianBlur(gray, (0, 0), sigma * k)
        dog = g1 - g2

        # Soft thresholding: 1 where above epsilon (white / no edge), tanh blend below
        result = np.where(dog >= epsilon, 1.0, 1.0 + np.tanh(phi * (dog - epsilon)))
        result = np.clip(result, 0.0, 1.0)
        out = (result * 255).astype(np.uint8)
        return np.stack([out] * 3, axis=-1)

    def _flow_map(self, image_rgb: np.ndarray, strength: int) -> np.ndarray:
        # Structure tensor coherency-weighted edges.
        # The structure tensor J captures local gradient orientation; coherency ∈ [0,1]
        # measures how well-organized (vs. chaotic/textural) the gradient field is.
        # Weighting gradient magnitude by coherency² suppresses random texture and keeps
        # only edges that follow the form — giving a brushstroke / painterly quality.
        gray = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2GRAY).astype(np.float32)

        sigma_d = 1.0                          # derivative scale
        sigma_r = 3.0 + strength * 0.5         # integration scale: strength 1→3.5, 5→5.5

        sm = cv2.GaussianBlur(gray, (0, 0), sigma_d)
        Ix = cv2.Sobel(sm, cv2.CV_32F, 1, 0, ksize=3)
        Iy = cv2.Sobel(sm, cv2.CV_32F, 0, 1, ksize=3)

        J11 = cv2.GaussianBlur(Ix * Ix, (0, 0), sigma_r)
        J12 = cv2.GaussianBlur(Ix * Iy, (0, 0), sigma_r)
        J22 = cv2.GaussianBlur(Iy * Iy, (0, 0), sigma_r)

        disc = np.sqrt(np.maximum((J11 - J22) ** 2 + 4 * J12 ** 2, 0.0))
        coherency = disc / (J11 + J22 + 1e-8)   # 0 = isotropic texture, 1 = pure edge

        mag = np.sqrt(Ix ** 2 + Iy ** 2)
        score = mag * (coherency ** 2)
        score = cv2.GaussianBlur(score, (0, 0), 1.5)

        score_norm = cv2.normalize(score, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)

        # Percentile threshold: strength 1→88th, 5→64th (more edges at high strength)
        pct = 88 - (strength - 1) * 6
        thresh = float(np.percentile(score_norm, pct))
        edges = (score_norm > thresh).astype(np.uint8) * 255

        if strength > 1:
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (strength, strength))
            edges = cv2.dilate(edges, kernel, iterations=1)

        return np.stack([cv2.bitwise_not(edges)] * 3, axis=-1)

    def temperature_map(self, image_rgb: np.ndarray, masks: list[dict]) -> np.ndarray:
        """
        Per-segment warm/cool/neutral classification.
        Each segment is filled with a single temperature color:
          warm  (H 0-60° or 300-360°)  → #e8734a
          cool  (H 120-270°)            → #4a7be8
          neutral (low saturation)      → #7a7875
        Returns RGB array (H, W, 3).
        """
        h, w = image_rgb.shape[:2]
        result = np.full((h, w, 3), [122, 120, 117], dtype=np.uint8)  # default neutral
        hsv = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2HSV).astype(np.float32)

        WARM    = np.array([232, 115,  74], dtype=np.uint8)   # #e8734a
        COOL    = np.array([ 74, 123, 232], dtype=np.uint8)   # #4a7be8
        NEUTRAL = np.array([122, 120, 117], dtype=np.uint8)   # #7a7875

        for m in masks:
            seg = m["segmentation"]
            seg_hsv = hsv[seg]
            mean_s = seg_hsv[:, 1].mean()
            mean_h = seg_hsv[:, 0].mean() * 2.0  # OpenCV H is 0-180, scale to 0-360
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
