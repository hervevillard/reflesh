import numpy as np
import cv2
from PIL import Image
from skimage.color import rgb2lab


class Exporter:
    def composite(
        self,
        color_layer: np.ndarray,
        tonal_layer: np.ndarray | None,
        edge_layer: np.ndarray | None,
        show_color: bool,
        show_tonal: bool,
        show_edges: bool,
        tonal_opacity: float = 0.28,
    ) -> np.ndarray:
        base = (
            color_layer.astype(np.float32)
            if show_color
            else np.full_like(color_layer, 255, dtype=np.float32)
        )
        if show_tonal and tonal_layer is not None:
            t = tonal_layer.astype(np.float32)
            base = base * (1.0 - tonal_opacity) + t * tonal_opacity

        if show_edges and edge_layer is not None:
            # Multiply blend: white (255) areas are no-op, black (0) darkens to black
            base = base * (edge_layer.astype(np.float32) / 255.0)

        return base.clip(0, 255).astype(np.uint8)

    def save_png(self, image_rgb: np.ndarray, path: str) -> None:
        Image.fromarray(image_rgb).save(path)

    def save_palette_png(self, palette: np.ndarray, path: str) -> None:
        from PIL import ImageDraw, ImageFont
        import math

        SIZE = 500
        BG = (28, 25, 23)
        LABEL_H = 22
        PAD = 6

        # Sort darkest → lightest by perceptual luminance
        lum = 0.2126 * palette[:, 0] + 0.7152 * palette[:, 1] + 0.0722 * palette[:, 2]
        palette = palette[np.argsort(lum)]

        n = len(palette)
        cols = math.ceil(math.sqrt(n))
        rows = math.ceil(n / cols)

        cell_w = SIZE // cols
        cell_h = SIZE // rows

        img = Image.new("RGB", (SIZE, SIZE), BG)
        draw = ImageDraw.Draw(img)

        try:
            font = ImageFont.load_default(size=13)
        except TypeError:
            font = ImageFont.load_default()

        for i, (r, g, b) in enumerate(palette.astype(int)):
            col = i % cols
            row = i // cols
            x0 = col * cell_w + PAD
            y0 = row * cell_h + PAD
            x1 = x0 + cell_w - PAD * 2
            y1 = y0 + cell_h - PAD * 2

            draw.rectangle([x0, y0, x1, y1 - LABEL_H], fill=(r, g, b))

            hex_str = f"#{r:02x}{g:02x}{b:02x}"
            bb = draw.textbbox((0, 0), hex_str, font=font)
            tx = x0 + (cell_w - PAD * 2 - (bb[2] - bb[0])) // 2
            ty = y1 - LABEL_H + (LABEL_H - (bb[3] - bb[1])) // 2
            draw.text((tx, ty), hex_str, fill=(250, 250, 249), font=font)

        img.save(path)

    def save_svg(
        self,
        color_layer: np.ndarray,
        masks: list[dict],
        path: str,
    ) -> None:
        """
        GDAL-inspired polygonization: export each segment as a filled SVG path.
        The artist can open this in Illustrator/Inkscape as editable vector shapes.
        """
        h, w = color_layer.shape[:2]
        lines = [
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'viewBox="0 0 {w} {h}" width="{w}" height="{h}">'
        ]

        for m in sorted(masks, key=lambda x: x["area"], reverse=True):
            seg = m["segmentation"]
            seg_pixels = color_layer[seg]
            if seg_pixels.size == 0:
                continue
            r, g, b = int(seg_pixels[0, 0]), int(seg_pixels[0, 1]), int(seg_pixels[0, 2])
            fill = f"#{r:02x}{g:02x}{b:02x}"

            contours, _ = cv2.findContours(
                seg.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )
            for contour in contours:
                if len(contour) < 3:
                    continue
                pts = contour.reshape(-1, 2)
                d = "M " + " L ".join(f"{p[0]},{p[1]}" for p in pts) + " Z"
                lines.append(f'  <path d="{d}" fill="{fill}" stroke="none"/>')

        lines.append("</svg>")
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

    def save_value_study_png(self, tonal_layer: np.ndarray, path: str) -> None:
        """Save the posterized tonal map as a grayscale PNG — a painter's value study."""
        gray = tonal_layer[:, :, 0]  # R == G == B in the tonal layer
        Image.fromarray(gray, mode="L").save(path)

    def nearest_pigments(
        self, palette: np.ndarray, pigments_data: list[dict]
    ) -> list[dict]:
        """
        For each palette color find the perceptually nearest artist paint.
        Uses CIE Lab Euclidean distance.
        Returns one result per palette entry: {"name": str, "rgb": [R,G,B], "distance": float}.
        """
        if not pigments_data:
            return []
        pig_rgb = np.array([p["rgb"] for p in pigments_data], dtype=np.float32)
        pig_lab = rgb2lab(pig_rgb[None] / 255.0)[0]  # shape (N, 3)
        pal_lab = rgb2lab(palette[None].astype(np.float32) / 255.0)[0]  # shape (K, 3)

        results = []
        for k_lab in pal_lab:
            dists = np.linalg.norm(pig_lab - k_lab, axis=1)
            idx = int(dists.argmin())
            results.append({
                "name": pigments_data[idx]["name"],
                "rgb": pigments_data[idx]["rgb"],
                "distance": float(dists[idx]),
            })
        return results

    def save_brushstroke_svg(
        self,
        color_layer: np.ndarray,
        masks: list[dict],
        path: str,
        jitter_px: int = 4,
    ) -> None:
        """
        Like save_svg but path points are randomly jittered to simulate hand-painted strokes.
        Each segment uses a reproducible seed so re-exports are identical.
        """
        h, w = color_layer.shape[:2]
        lines = [
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'viewBox="0 0 {w} {h}" width="{w}" height="{h}">'
        ]

        for seg_idx, m in enumerate(sorted(masks, key=lambda x: x["area"], reverse=True)):
            seg = m["segmentation"]
            seg_pixels = color_layer[seg]
            if seg_pixels.size == 0:
                continue
            r, g, b = int(seg_pixels[0, 0]), int(seg_pixels[0, 1]), int(seg_pixels[0, 2])
            fill = f"#{r:02x}{g:02x}{b:02x}"

            contours, _ = cv2.findContours(
                seg.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )
            rng = np.random.default_rng(seg_idx)
            for contour in contours:
                if len(contour) < 3:
                    continue
                pts = contour.reshape(-1, 2).astype(np.int32)
                jitter = rng.integers(-jitter_px, jitter_px + 1, size=pts.shape)
                pts = (pts + jitter).clip([0, 0], [w - 1, h - 1])
                d = "M " + " L ".join(f"{p[0]},{p[1]}" for p in pts) + " Z"
                lines.append(f'  <path d="{d}" fill="{fill}" stroke="none"/>')

        lines.append("</svg>")
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

    def blend_temperature(
        self, base: np.ndarray, temperature_layer: np.ndarray, opacity: float = 0.45
    ) -> np.ndarray:
        """Alpha-blend the temperature map over the base composite."""
        result = (
            base.astype(np.float32) * (1.0 - opacity)
            + temperature_layer.astype(np.float32) * opacity
        )
        return result.clip(0, 255).astype(np.uint8)
