"""SAM2-based fish/debris detector using zero-shot segmentation.

Track A: Zero-shot detection without training data.
Uses Meta's Segment Anything Model 2 for video segmentation.
"""

import os
from pathlib import Path
import numpy as np
from typing import List, Optional, Tuple
import cv2

from .base import BaseDetector, DetectionResult, FishDetection, DebrisDetection

# Package root for resolving relative paths
_PACKAGE_ROOT = Path(__file__).parent.parent.parent  # aqua_detection/
_DEFAULT_CHECKPOINT = _PACKAGE_ROOT / "models" / "sam2.1_hiera_tiny.pt"

# SAM2 imports (lazy loading to avoid import errors if not installed)
_sam2_available = False
_SAM2VideoPredictor = None
_build_sam2_video_predictor = None


def _load_sam2():
    """Lazy load SAM2 to avoid import errors."""
    global _sam2_available, _SAM2VideoPredictor, _build_sam2_video_predictor
    
    if _sam2_available is not None and _SAM2VideoPredictor is not None:
        return _sam2_available
    
    try:
        from sam2.build_sam import build_sam2_video_predictor
        from sam2.sam2_video_predictor import SAM2VideoPredictor
        _SAM2VideoPredictor = SAM2VideoPredictor
        _build_sam2_video_predictor = build_sam2_video_predictor
        _sam2_available = True
    except ImportError:
        _sam2_available = False
    
    return _sam2_available


class FishSAM2Detector(BaseDetector):
    """SAM2-based zero-shot fish/debris detector.
    
    Uses automatic mask generation to segment all objects,
    then classifies them as fish or debris based on size/shape.
    
    Requirements:
        pip install sam2
        Download checkpoint from: https://github.com/facebookresearch/sam2
    """
    
    def __init__(
        self,
        model_cfg: str = "configs/sam2.1/sam2.1_hiera_t.yaml",
        checkpoint_path: Optional[str] = None,
        device: str = "cuda",
        fish_area_range: Tuple[int, int] = (500, 50000),
        fish_aspect_ratio_min: float = 1.3,
        debris_area_range: Tuple[int, int] = (50, 500),
        points_per_side: int = 16,  # Reduced from 32 for lower GPU memory (16x16=256 vs 32x32=1024 points)
        pred_iou_thresh: float = 0.88,
        stability_score_thresh: float = 0.95,
        use_half_precision: bool = True,  # Use fp16 for lower memory
        max_image_size: int = 640,  # Resize large images to save memory
    ):
        """Initialize SAM2 detector.
        
        Args:
            model_cfg: SAM2 config name (e.g. "sam2.1_hiera_l.yaml")
            checkpoint_path: Path to SAM2 checkpoint (auto-detected if None)
            device: "cuda" or "cpu"
            fish_area_range: (min, max) area for fish detection
            fish_aspect_ratio_min: Minimum aspect ratio for fish
            debris_area_range: (min, max) area for debris detection
            points_per_side: Grid points for automatic mask generation
            pred_iou_thresh: IoU threshold for mask filtering
            stability_score_thresh: Stability threshold for mask filtering
        """
        self.model_cfg = model_cfg
        if checkpoint_path is None:
            self.checkpoint_path = str(_DEFAULT_CHECKPOINT)
        else:
            self.checkpoint_path = checkpoint_path
        self.device = device
        self.fish_area_range = fish_area_range
        self.fish_aspect_ratio_min = fish_aspect_ratio_min
        self.debris_area_range = debris_area_range
        self.points_per_side = points_per_side
        self.pred_iou_thresh = pred_iou_thresh
        self.stability_score_thresh = stability_score_thresh
        self.use_half_precision = use_half_precision
        self.max_image_size = max_image_size
        
        self._predictor = None
        self._mask_generator = None
        self._initialized = False
    
    def _initialize(self):
        """Lazy initialization of SAM2 model."""
        if self._initialized:
            return True
        
        if not _load_sam2():
            print("SAM2 not available. Install with: pip install sam2")
            return False
        
        try:
            import torch
            # For image-based detection, we use SAM2ImagePredictor
            from sam2.build_sam import build_sam2
            from sam2.automatic_mask_generator import SAM2AutomaticMaskGenerator
            
            # Use fp16 for lower memory footprint on CUDA
            dtype = torch.float16 if (self.use_half_precision and self.device == "cuda") else torch.float32
            
            sam2_model = build_sam2(
                self.model_cfg,
                self.checkpoint_path,
                device=self.device
            )
            
            # Convert to half precision if requested
            if dtype == torch.float16:
                sam2_model = sam2_model.half()
            
            self._mask_generator = SAM2AutomaticMaskGenerator(
                model=sam2_model,
                points_per_side=self.points_per_side,
                pred_iou_thresh=self.pred_iou_thresh,
                stability_score_thresh=self.stability_score_thresh,
                crop_n_layers=0,  # Reduced from 1 for lower memory
                crop_n_points_downscale_factor=2,
                min_mask_region_area=100,
            )
            
            self._initialized = True
            return True
            
        except Exception as e:
            print(f"Failed to initialize SAM2: {e}")
            return False
    
    def get_name(self) -> str:
        return "sam2"
    
    def detect(self, image: np.ndarray) -> DetectionResult:
        """Detect fish and debris using SAM2 automatic mask generation.
        
        Args:
            image: BGR image from camera
            
        Returns:
            DetectionResult with fish and debris detections
        """
        if not self._initialize():
            return DetectionResult()
        
        # Resize image if too large to save GPU memory
        orig_h, orig_w = image.shape[:2]
        scale = 1.0
        if max(orig_h, orig_w) > self.max_image_size:
            scale = self.max_image_size / max(orig_h, orig_w)
            new_w, new_h = int(orig_w * scale), int(orig_h * scale)
            image = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
        
        # Convert BGR to RGB for SAM2
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # Generate all masks
        try:
            masks = self._mask_generator.generate(image_rgb)
        except Exception as e:
            print(f"SAM2 mask generation failed: {e}")
            return DetectionResult()
        
        fish_detections = []
        debris_detections = []
        
        for mask_data in masks:
            mask = mask_data['segmentation']
            area = mask_data['area']
            bbox = mask_data['bbox']  # XYWH format
            stability_score = mask_data['stability_score']
            
            # Convert bbox from XYWH to our format, scaling back if resized
            x, y, w, h = [int(v / scale) for v in bbox]
            area = int(area / (scale * scale))  # Scale area back to original
            
            # Resize mask back to original size if needed
            if scale != 1.0:
                mask = cv2.resize(mask.astype(np.uint8), (orig_w, orig_h), interpolation=cv2.INTER_NEAREST).astype(bool)
            
            # Calculate aspect ratio
            aspect_ratio = max(w, h) / min(w, h) if min(w, h) > 0 else 1.0
            
            # Classify as fish or debris based on size and shape
            if self.fish_area_range[0] <= area <= self.fish_area_range[1]:
                if aspect_ratio >= self.fish_aspect_ratio_min:
                    fish_detections.append(FishDetection(
                        bbox=(x, y, w, h),
                        mask=mask,
                        species="unknown",  # SAM2 doesn't classify species
                        confidence=float(stability_score),
                    ))
            elif self.debris_area_range[0] <= area <= self.debris_area_range[1]:
                debris_detections.append(DebrisDetection(
                    bbox=(x, y, w, h),
                    confidence=float(stability_score),
                ))
        
        return DetectionResult(
            fish_detections=fish_detections,
            debris_detections=debris_detections
        )
    
    def detect_with_prompts(
        self,
        image: np.ndarray,
        points: Optional[List[Tuple[int, int]]] = None,
        boxes: Optional[List[Tuple[int, int, int, int]]] = None,
    ) -> DetectionResult:
        """Detect fish using point or box prompts.
        
        This is useful when you have prior knowledge about fish locations
        (e.g., from previous frames or YOLO detection).
        
        Args:
            image: BGR image
            points: List of (x, y) points inside fish
            boxes: List of (x1, y1, x2, y2) bounding boxes
            
        Returns:
            DetectionResult with fish detections
        """
        if not self._initialize():
            return DetectionResult()
        
        # TODO: Implement prompted segmentation
        # This would use SAM2ImagePredictor with point/box prompts
        # Useful for refining YOLO detections with precise segmentation
        
        return self.detect(image)


class FishSAM2VideoDetector(BaseDetector):
    """SAM2-based video detector with temporal consistency.
    
    Uses SAM2's video predictor to maintain object identity across frames.
    Better for tracking fish over time.
    """
    
    def __init__(
        self,
        model_cfg: str = "configs/sam2.1/sam2.1_hiera_t.yaml",
        checkpoint_path: Optional[str] = None,
        device: str = "cuda",
    ):
        self.model_cfg = model_cfg
        if checkpoint_path is None:
            self.checkpoint_path = str(_DEFAULT_CHECKPOINT)
        else:
            self.checkpoint_path = checkpoint_path
        self.device = device
        
        self._predictor = None
        self._initialized = False
        self._inference_state = None
        self._frame_idx = 0
    
    def _initialize(self):
        """Lazy initialization of SAM2 video predictor."""
        if self._initialized:
            return True
        
        if not _load_sam2():
            return False
        
        try:
            self._predictor = _build_sam2_video_predictor(
                self.model_cfg,
                self.checkpoint_path,
                device=self.device
            )
            self._initialized = True
            return True
        except Exception as e:
            print(f"Failed to initialize SAM2 video predictor: {e}")
            return False
    
    def get_name(self) -> str:
        return "sam2_video"
    
    def detect(self, image: np.ndarray) -> DetectionResult:
        """Detect fish in video frame with temporal consistency."""
        # TODO: Implement video-based detection
        # This requires managing inference state across frames
        return DetectionResult()
    
    def reset(self):
        """Reset video state for new video sequence."""
        self._inference_state = None
        self._frame_idx = 0
