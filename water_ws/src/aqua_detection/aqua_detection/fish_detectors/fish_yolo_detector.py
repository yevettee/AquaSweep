"""YOLOv8-based fish/debris detector.

Track B: Learned species classification.
Uses trained YOLOv8 model for fish species detection.
Does NOT classify alive/dead - that's handled by DINOv2.
"""

import numpy as np
from typing import List, Optional, Tuple
from pathlib import Path

from .base import BaseDetector, DetectionResult, FishDetection, DebrisDetection

# YOLO imports (lazy loading)
_yolo_available = None
_YOLO = None


def _load_yolo():
    """Lazy load YOLO to avoid import errors."""
    global _yolo_available, _YOLO
    
    if _yolo_available is not None:
        return _yolo_available
    
    try:
        from ultralytics import YOLO
        _YOLO = YOLO
        _yolo_available = True
    except ImportError:
        _yolo_available = False
    
    return _yolo_available


class FishYOLODetector(BaseDetector):
    """YOLOv8-based fish/debris detector.
    
    Trained to classify fish species (sturgeon, salmon, debris).
    Does NOT classify alive/dead - use DINOv2 for status.
    
    Requirements:
        pip install ultralytics
        Trained model at: models/yolov8_fish_species.pt
    """
    
    # Class mapping (must match training)
    CLASS_NAMES = {
        0: "sturgeon",
        1: "dead_sturgeon",
        2: "debris",
    }
    
    def __init__(
        self,
        model_path: str = "models/yolov8_fish_species.pt",
        confidence_threshold: float = 0.5,
        iou_threshold: float = 0.45,
        device: str = "cuda",
        imgsz: int = 640,
        half: bool = True,
        use_tracking: bool = True,
    ):
        """Initialize YOLO detector.
        
        Args:
            model_path: Path to trained YOLOv8 model
            confidence_threshold: Detection confidence threshold
            iou_threshold: NMS IoU threshold
            device: "cuda" or "cpu"
            imgsz: Inference image size (should match training)
            half: Use FP16 inference for faster speed
            use_tracking: Use ByteTrack for persistent fish IDs
        """
        self.model_path = model_path
        self.confidence_threshold = confidence_threshold
        self.iou_threshold = iou_threshold
        self.device = device
        self.imgsz = imgsz
        self.half = half
        self.use_tracking = use_tracking
        
        self._model = None
        self._initialized = False
        self._warmed_up = False
    
    def _initialize(self) -> bool:
        """Lazy initialization of YOLO model."""
        if self._initialized:
            return True
        
        global _yolo_available
        if _yolo_available is False:
            return False
        
        if not _load_yolo():
            print("YOLO (ultralytics) not available. Install with: pip install ultralytics")
            return False
        
        model_path = Path(self.model_path)
        if not model_path.exists():
            # Try alternative paths
            alt_paths = [
                Path(__file__).parent.parent.parent / "models" / "yolov8_fish_species.pt",
                Path.cwd() / "models" / "yolov8_fish_species.pt",
            ]
            
            # Search up directory tree for models folder (works from both src and install)
            current = Path(__file__).resolve()
            for parent in current.parents:
                candidate = parent / "models" / "yolov8_fish_species.pt"
                if candidate.exists():
                    alt_paths.insert(0, candidate)
                    break
                # Also check src/aqua_detection/models for ROS2 install case
                src_candidate = parent / "src" / "aqua_detection" / "models" / "yolov8_fish_species.pt"
                if src_candidate.exists():
                    alt_paths.insert(0, src_candidate)
                    break
            
            for alt in alt_paths:
                if alt.exists():
                    model_path = alt
                    break
        
        if not model_path.exists():
            print(f"YOLO model not found at {self.model_path}")
            print("Train a model first with: ./scripts/fish_one_click_train.sh")
            return False
        
        try:
            self._model = _YOLO(str(model_path))
            self._model.to(self.device)
            self._initialized = True
            return True
        except Exception as e:
            print(f"Failed to load YOLO model: {e}")
            return False
    
    def get_name(self) -> str:
        return "yolo"
    
    def warmup(self):
        """Warmup model with dummy inference to avoid first-frame latency."""
        if self._warmed_up:
            return
        if not self._initialize():
            return
        try:
            dummy = np.zeros((self.imgsz, self.imgsz, 3), dtype=np.uint8)
            self._model(dummy, imgsz=self.imgsz, half=self.half, verbose=False)
            self._warmed_up = True
            print(f"YOLO model warmed up (imgsz={self.imgsz}, half={self.half})")
        except Exception as e:
            print(f"YOLO warmup failed: {e}")
    
    def detect(self, image: np.ndarray) -> DetectionResult:
        """Detect fish and debris using YOLOv8.
        
        If use_tracking is enabled, uses ByteTrack for persistent IDs.
        
        Args:
            image: BGR image from camera
            
        Returns:
            DetectionResult with fish and debris detections
        """
        # Use tracking mode for persistent IDs
        if self.use_tracking:
            return self.detect_with_tracking(image)
        
        if not self._initialize():
            return DetectionResult()
        
        # Run inference with optimized parameters
        try:
            results = self._model(
                image,
                conf=self.confidence_threshold,
                iou=self.iou_threshold,
                imgsz=self.imgsz,
                half=self.half,
                verbose=False,
            )
        except Exception as e:
            print(f"YOLO inference failed: {e}")
            return DetectionResult()
        
        fish_detections = []
        debris_detections = []
        
        # Process results
        for result in results:
            boxes = result.boxes
            
            if boxes is None:
                continue
            
            for i in range(len(boxes)):
                # Get box coordinates (xyxy format)
                xyxy = boxes.xyxy[i].cpu().numpy()
                x1, y1, x2, y2 = map(int, xyxy)
                w, h = x2 - x1, y2 - y1
                
                # Get class and confidence
                class_id = int(boxes.cls[i].cpu().numpy())
                confidence = float(boxes.conf[i].cpu().numpy())
                
                # Map class ID to name
                class_name = self.CLASS_NAMES.get(class_id, "unknown")
                
                if class_name == "debris":
                    debris_detections.append(DebrisDetection(
                        bbox=(x1, y1, w, h),
                        confidence=confidence,
                    ))
                else:
                    # Fish detection (sturgeon, salmon, etc.)
                    fish_detections.append(FishDetection(
                        bbox=(x1, y1, w, h),
                        species=class_name,
                        confidence=confidence,
                    ))
        
        return DetectionResult(
            fish_detections=fish_detections,
            debris_detections=debris_detections,
        )
    
    def detect_with_tracking(
        self,
        image: np.ndarray,
        persist: bool = True
    ) -> DetectionResult:
        """Detect with built-in YOLO tracking.
        
        Uses ByteTrack or BoT-SORT for tracking.
        
        Args:
            image: BGR image
            persist: Whether to persist tracking across frames
            
        Returns:
            DetectionResult with fish IDs from tracker
        """
        if not self._initialize():
            return DetectionResult()
        
        try:
            results = self._model.track(
                image,
                conf=self.confidence_threshold,
                iou=self.iou_threshold,
                imgsz=self.imgsz,
                half=self.half,
                persist=persist,
                verbose=False,
            )
        except Exception as e:
            print(f"YOLO tracking failed: {e}")
            return self.detect(image)
        
        fish_detections = []
        debris_detections = []
        
        for result in results:
            boxes = result.boxes
            
            if boxes is None:
                continue
            
            for i in range(len(boxes)):
                xyxy = boxes.xyxy[i].cpu().numpy()
                x1, y1, x2, y2 = map(int, xyxy)
                w, h = x2 - x1, y2 - y1
                
                class_id = int(boxes.cls[i].cpu().numpy())
                confidence = float(boxes.conf[i].cpu().numpy())
                class_name = self.CLASS_NAMES.get(class_id, "unknown")
                
                # Get tracking ID if available
                track_id = None
                if boxes.id is not None:
                    track_id = int(boxes.id[i].cpu().numpy())
                
                if class_name == "debris":
                    debris_detections.append(DebrisDetection(
                        bbox=(x1, y1, w, h),
                        confidence=confidence,
                    ))
                else:
                    det = FishDetection(
                        bbox=(x1, y1, w, h),
                        species=class_name,
                        confidence=confidence,
                    )
                    # Store track ID in detection for later use
                    if track_id is not None:
                        det._track_id = track_id
                    fish_detections.append(det)
        
        return DetectionResult(
            fish_detections=fish_detections,
            debris_detections=debris_detections,
        )
