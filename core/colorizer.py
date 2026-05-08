import numpy as np
from sklearn.cluster import MiniBatchKMeans


class Colorizer:
    def quantize(self, image_rgb: np.ndarray, n_colors: int) -> tuple[np.ndarray, np.ndarray]:
        """Global k-means quantization. Returns (palette [N,3], labels [H,W])."""
        h, w = image_rgb.shape[:2]
        pixels = image_rgb.reshape(-1, 3).astype(np.float32)
        # Subsample for speed on large images (max 100K pixels for fitting)
        step = max(1, len(pixels) // 100_000)
        sample = pixels[::step]
        km = MiniBatchKMeans(n_clusters=n_colors, n_init=3, random_state=42, batch_size=4096)
        km.fit(sample)
        palette = km.cluster_centers_.astype(np.uint8)
        labels = km.predict(pixels).reshape(h, w)
        return palette, labels

    def colorize_masks(
        self,
        masks: list[dict],
        palette: np.ndarray,
        labels: np.ndarray,
        image_shape: tuple,
        image_rgb: np.ndarray | None = None,
    ) -> np.ndarray:
        """Fill each SAM segment with its actual mean pixel color (flat solid)."""
        h, w = image_shape[:2]
        result = np.zeros((h, w, 3), dtype=np.uint8)
        covered = np.zeros((h, w), dtype=bool)

        for m in masks:  # already sorted largest-first by segmenter
            seg = m["segmentation"]
            if not seg.any():
                continue
            if image_rgb is not None:
                # Actual mean of the segment's pixels — accurate per zone
                result[seg] = image_rgb[seg].mean(axis=0).astype(np.uint8)
            else:
                seg_labels = labels[seg]
                dominant = int(np.bincount(seg_labels).argmax())
                result[seg] = palette[dominant]
            covered[seg] = True

        # Gap fill (thin boundaries between segments)
        if not covered.all():
            result[~covered] = palette[labels[~covered]]

        return result
