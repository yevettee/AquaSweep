"""OpenCV-based fish/debris detector using traditional CV techniques.

This is the legacy detector extracted from the original detection_node.py.
Uses adaptive threshold + morphology + contour analysis.
"""

import cv2
import numpy as np
from typing import List, Tuple

from .base import BaseDetector, DetectionResult, FishDetection, DebrisDetection


class FishOpenCVDetector(BaseDetector):
    """Traditional CV detector using adaptive threshold and contours.
    
    Detection pipeline:
    1. Image preprocessing (resize, illumination normalization)
    2. Fish detection (large elongated objects)
    3. Debris detection (small objects, excluding fish regions)
    """
    
    def __init__(
        self,
        scale_factor: float = 3.0,
        fish_area_range: Tuple[int, int] = (1200, 45000),
        fish_aspect_ratio_min: float = 1.4,
        debris_area_range: Tuple[int, int] = (15, 500),
        pool_margin: int = 25
    ):
        self.scale_factor = scale_factor
        self.fish_area_range = fish_area_range
        self.fish_aspect_ratio_min = fish_aspect_ratio_min
        self.debris_area_range = debris_area_range
        self.pool_margin = pool_margin
    
    def get_name(self) -> str:
        return "opencv"
    
    def detect(self, image: np.ndarray) -> DetectionResult:
        """Detect fish and debris using OpenCV techniques."""
        h_orig, w_orig = image.shape[:2]
        
        # 1. Preprocessing
        resized = cv2.resize(
            image,
            (int(w_orig * self.scale_factor), int(h_orig * self.scale_factor)),
            interpolation=cv2.INTER_CUBIC
        )
        
        # Illumination normalization
        illum_bg = cv2.GaussianBlur(resized, (151, 151), 0)
        normalized = cv2.divide(resized, illum_bg, scale=255)
        
        # Grayscale and blur
        gray = cv2.cvtColor(normalized, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        
        # Pool mask (circular)
        h, w = gray.shape[:2]
        center = (w // 2, h // 2)
        radius = int(min(h, w) // 2 - self.pool_margin)
        mask_circle = np.zeros((h, w), dtype=np.uint8)
        cv2.circle(mask_circle, center, radius, 255, -1)
        
        # 2. Fish detection
        fish_detections = self._detect_fish(blurred, mask_circle, h, w)
        
        # 3. Debris detection (excluding fish regions)
        fish_contours = [d.contour for d in fish_detections if d.contour is not None]
        debris_detections = self._detect_debris(blurred, mask_circle, fish_contours, h, w)
        
        # Scale back to original coordinates
        fish_detections = self._scale_detections(fish_detections, 1.0 / self.scale_factor)
        debris_detections = self._scale_debris(debris_detections, 1.0 / self.scale_factor)
        
        return DetectionResult(
            fish_detections=fish_detections,
            debris_detections=debris_detections
        )
    
    def _detect_fish(
        self,
        blurred: np.ndarray,
        mask: np.ndarray,
        h: int,
        w: int
    ) -> List[FishDetection]:
        """Detect fish using adaptive threshold and contour analysis."""
        # Adaptive threshold
        fish_mask_raw = cv2.adaptiveThreshold(
            blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV, 101, 3
        )
        fish_mask = cv2.bitwise_and(fish_mask_raw, mask)
        
        # Morphology to connect fish body parts
        kernel_open = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        kernel_close = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 25))
        fish_mask = cv2.morphologyEx(fish_mask, cv2.MORPH_OPEN, kernel_open)
        fish_mask = cv2.morphologyEx(fish_mask, cv2.MORPH_CLOSE, kernel_close)
        
        # Find contours
        contours, _ = cv2.findContours(
            fish_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        
        detections = []
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if not (self.fish_area_range[0] <= area <= self.fish_area_range[1]):
                continue
            
            rect = cv2.minAreaRect(cnt)
            (cx, cy), (w_rect, h_rect), angle = rect
            max_dim = max(w_rect, h_rect)
            min_dim = min(w_rect, h_rect)
            
            # Filter by aspect ratio
            if min_dim == 0:
                continue
            aspect_ratio = max_dim / min_dim
            
            # Filter out abnormally large objects
            if max_dim > (min(h, w) * 0.65):
                continue
            
            if aspect_ratio >= self.fish_aspect_ratio_min:
                x, y, bw, bh = cv2.boundingRect(cnt)
                
                # Count fish (large objects may contain multiple)
                obb_area = w_rect * h_rect
                if obb_area >= 70000:
                    fish_count = 3
                elif obb_area >= 36000:
                    fish_count = 2
                else:
                    fish_count = 1
                
                # Create detection for each fish in cluster
                for _ in range(fish_count):
                    detections.append(FishDetection(
                        bbox=(x, y, bw, bh),
                        species="sturgeon",  # Default species
                        confidence=0.8,
                        contour=cnt
                    ))
        
        return detections
    
    def _detect_debris(
        self,
        blurred: np.ndarray,
        mask: np.ndarray,
        fish_contours: List[np.ndarray],
        h: int,
        w: int
    ) -> List[DebrisDetection]:
        """Detect debris (small objects), excluding fish regions."""
        # Higher sensitivity threshold for debris
        debris_mask_raw = cv2.adaptiveThreshold(
            blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV, 45, 2
        )
        debris_mask = cv2.bitwise_and(debris_mask_raw, mask)
        
        # Minimal morphology to keep debris separate
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        debris_mask = cv2.morphologyEx(debris_mask, cv2.MORPH_OPEN, kernel)
        debris_mask = cv2.morphologyEx(debris_mask, cv2.MORPH_CLOSE, kernel)
        
        # Remove fish regions
        if fish_contours:
            cv2.drawContours(debris_mask, fish_contours, -1, 0, thickness=cv2.FILLED)
        
        # Find contours
        contours, _ = cv2.findContours(
            debris_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        
        detections = []
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if not (self.debris_area_range[0] <= area <= self.debris_area_range[1]):
                continue
            
            x, y, bw, bh = cv2.boundingRect(cnt)
            
            # Filter out edge artifacts
            if bw > (w * 0.05) or bh > (h * 0.05):
                continue
            
            if bh == 0:
                continue
            aspect_ratio = bw / bh
            if 0.15 <= aspect_ratio <= 6.0:
                detections.append(DebrisDetection(
                    bbox=(x, y, bw, bh),
                    confidence=0.7,
                    contour=cnt
                ))
        
        return detections
    
    def _scale_detections(
        self,
        detections: List[FishDetection],
        scale: float
    ) -> List[FishDetection]:
        """Scale detection coordinates back to original image size."""
        scaled = []
        for d in detections:
            x, y, w, h = d.bbox
            scaled.append(FishDetection(
                bbox=(int(x * scale), int(y * scale), int(w * scale), int(h * scale)),
                species=d.species,
                confidence=d.confidence,
                contour=(d.contour * scale).astype(np.int32) if d.contour is not None else None
            ))
        return scaled
    
    def _scale_debris(
        self,
        detections: List[DebrisDetection],
        scale: float
    ) -> List[DebrisDetection]:
        """Scale debris coordinates back to original image size."""
        scaled = []
        for d in detections:
            x, y, w, h = d.bbox
            scaled.append(DebrisDetection(
                bbox=(int(x * scale), int(y * scale), int(w * scale), int(h * scale)),
                confidence=d.confidence,
                contour=(d.contour * scale).astype(np.int32) if d.contour is not None else None
            ))
        return scaled
