"""OpenCV-based fish status classifier (alive vs suspicious)."""

import cv2
import numpy as np
from typing import Dict, Optional, Tuple

from aqua_detection.fish_detectors.base import BaseStatusClassifier


class SimpleFishStatusClassifier(BaseStatusClassifier):
    """Classify each YOLO bbox by background brightness contrast (C on debug overlay).

    suspicious if bg_contrast >= contrast_threshold (default 8).
    """

    def __init__(self, contrast_threshold: float = 8.0):
        self.contrast_threshold = contrast_threshold
        self._last_full_image = None
        self._last_bbox = None

    def _compute_color_features(
        self,
        fish_image: np.ndarray,
        full_image: Optional[np.ndarray] = None,
        bbox: Optional[Tuple[int, int, int, int]] = None,
    ) -> Dict[str, float]:
        hsv = cv2.cvtColor(fish_image, cv2.COLOR_BGR2HSV)
        v = hsv[:, :, 2]

        features = {
            'mean_value': float(np.mean(v)),
            'bg_contrast': 0.0,
        }

        if full_image is not None and bbox is not None:
            bg_features = self._compute_background_features(full_image, bbox)
            features.update(bg_features)
            features['bg_contrast'] = abs(
                features['mean_value'] - features.get('bg_mean_value', features['mean_value'])
            )

        return features

    def _compute_background_features(
        self,
        full_image: np.ndarray,
        bbox: Tuple[int, int, int, int],
        margin: int = 20,
    ) -> Dict[str, float]:
        x, y, w, h = bbox
        img_h, img_w = full_image.shape[:2]

        x1_bg = max(0, x - margin)
        y1_bg = max(0, y - margin)
        x2_bg = min(img_w, x + w + margin)
        y2_bg = min(img_h, y + h + margin)

        bg_region = full_image[y1_bg:y2_bg, x1_bg:x2_bg].copy()
        mask = np.ones((y2_bg - y1_bg, x2_bg - x1_bg), dtype=bool)

        fish_x1 = max(0, x - x1_bg)
        fish_y1 = max(0, y - y1_bg)
        fish_x2 = min(mask.shape[1], fish_x1 + w)
        fish_y2 = min(mask.shape[0], fish_y1 + h)
        mask[fish_y1:fish_y2, fish_x1:fish_x2] = False

        if np.sum(mask) > 0:
            bg_hsv = cv2.cvtColor(bg_region, cv2.COLOR_BGR2HSV)
            return {'bg_mean_value': float(np.mean(bg_hsv[:, :, 2][mask]))}

        return {'bg_mean_value': 150.0}

    def classify(
        self,
        fish_image: np.ndarray,
        full_image: Optional[np.ndarray] = None,
        bbox: Optional[Tuple[int, int, int, int]] = None,
    ) -> Tuple[str, float]:
        if fish_image.size == 0:
            return "alive", 0.5

        self._last_full_image = full_image
        self._last_bbox = bbox

        contrast = self._compute_color_features(fish_image, full_image, bbox)['bg_contrast']
        if contrast >= self.contrast_threshold:
            return "suspicious", min(1.0, contrast / max(self.contrast_threshold, 1.0))
        return "alive", min(1.0, 1.0 - contrast / max(self.contrast_threshold, 1.0))

    def get_features(self, fish_image: np.ndarray) -> Dict[str, float]:
        return self._compute_color_features(
            fish_image,
            self._last_full_image,
            self._last_bbox,
        )
