import numpy as np
import cv2
from sklearn.cluster import MiniBatchKMeans
from skimage.color import rgb2lab


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

    def complementary_layer(self, color_layer: np.ndarray) -> np.ndarray:
        """Rotate every pixel's hue by 180° — returns the complementary color layer."""
        hsv = cv2.cvtColor(color_layer, cv2.COLOR_RGB2HSV).astype(np.int16)
        hsv[:, :, 0] = (hsv[:, :, 0] + 90) % 180  # OpenCV H range is 0-179
        return cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2RGB)

    def merge_similar_masks(
        self, masks: list[dict], image_rgb: np.ndarray, threshold_lab: int
    ) -> list[dict]:
        """
        Merge adjacent masks whose mean LAB colors are within threshold_lab distance.
        Returns a reduced mask list sorted largest-first.
        If threshold_lab == 0, returns a shallow copy unchanged.
        """
        if threshold_lab == 0 or len(masks) < 2:
            return list(masks)

        # Compute mean LAB for every mask
        lab_img = rgb2lab(image_rgb.astype(np.float32) / 255.0)
        mean_labs = []
        for m in masks:
            seg = m["segmentation"]
            mean_labs.append(lab_img[seg].mean(axis=0) if seg.any() else np.zeros(3))

        # Find adjacent pairs (share a boundary pixel using dilation overlap)
        n = len(masks)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        dilated = [
            cv2.dilate(m["segmentation"].astype(np.uint8), kernel) for m in masks
        ]
        adj = set()
        for i in range(n):
            for j in range(i + 1, n):
                if (dilated[i] & masks[j]["segmentation"].astype(np.uint8)).any():
                    dist = float(np.linalg.norm(mean_labs[i] - mean_labs[j]))
                    if dist < threshold_lab:
                        adj.add((dist, i, j))

        # Greedy union-find merge (smallest distance first)
        parent = list(range(n))

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        for dist, i, j in sorted(adj):
            ri, rj = find(i), find(j)
            if ri != rj:
                parent[ri] = rj

        # Collect groups
        groups: dict[int, list[int]] = {}
        for i in range(n):
            groups.setdefault(find(i), []).append(i)

        merged = []
        for indices in groups.values():
            if len(indices) == 1:
                merged.append(masks[indices[0]])
            else:
                combined_seg = np.zeros_like(masks[0]["segmentation"])
                for idx in indices:
                    combined_seg |= masks[idx]["segmentation"]
                merged.append({
                    "segmentation": combined_seg,
                    "area": int(combined_seg.sum()),
                    "predicted_iou": max(masks[i]["predicted_iou"] for i in indices),
                })

        merged.sort(key=lambda m: m["area"], reverse=True)
        return merged
