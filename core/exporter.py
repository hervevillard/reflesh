import numpy as np
import cv2
from PIL import Image


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
