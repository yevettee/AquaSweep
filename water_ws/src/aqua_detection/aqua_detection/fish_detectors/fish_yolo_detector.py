"""YOLO OBB fish detector with OpenCV debris detection.

- Fish: models/yolo26n_fish_species_v1.pt (OBB, sturgeon)
- Debris: OpenCV SimpleBlobDetector (no separate .pt)
- Alive/suspicious: fish_status_classifier (outside this module)
"""

import cv2
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


def _find_model_path(model_name: str) -> Optional[Path]:
    """Find model file in common locations."""
    direct = Path(model_name)
    if direct.exists():
        return direct

    try:
        from ament_index_python.packages import get_package_share_directory
        share_model = (
            Path(get_package_share_directory("aqua_detection"))
            / "models"
            / model_name
        )
        if share_model.exists():
            return share_model
    except Exception:
        pass

    # Common search locations
    search_paths = [
        Path(__file__).parent.parent.parent / "models" / model_name,
        Path.cwd() / "models" / model_name,
    ]
    
    # Search up directory tree
    current = Path(__file__).resolve()
    for parent in current.parents:
        candidate = parent / "models" / model_name
        if candidate.exists():
            return candidate
        src_candidate = parent / "src" / "aqua_detection" / "models" / model_name
        if src_candidate.exists():
            return src_candidate
    
    for path in search_paths:
        if path.exists():
            return path
    
    return None


class FishYOLODetector(BaseDetector):
    """YOLO OBB fish detector + OpenCV blob debris."""
    
    FISH_CLASS_NAMES = {0: "sturgeon"}
    _IGNORED_SPECIES = frozenset({"debris", "unknown"})
    
    def __init__(
        self,
        model_path: str = "models/yolo26n_fish_species_v1.pt",
        confidence_threshold: float = 0.5,
        iou_threshold: float = 0.45,
        device: str = "cuda",
        imgsz: int = 640,
        half: bool = True,
        use_tracking: bool = True,
        debris_min_area: int = 3,
        debris_max_area: int = 8,
        debris_debug: bool = False,
    ):
        """Initialize YOLO OBB + OpenCV debris detector.
        
        Args:
            model_path: Path to fish OBB weights (yolo26n_fish_species_v1.pt)
            confidence_threshold: Detection confidence threshold
            iou_threshold: NMS IoU threshold
            device: "cuda" or "cpu"
            imgsz: Inference image size
            half: Use FP16 inference
            use_tracking: Use ByteTrack for persistent fish IDs
            debris_min_area: Minimum blob area for debris (pixels)
            debris_max_area: Maximum blob area for debris (pixels)
            debris_debug: Print debris detection details for tuning
        """
        self.model_path = model_path
        self.confidence_threshold = confidence_threshold
        self.iou_threshold = iou_threshold
        self.device = device
        self.imgsz = imgsz
        self.half = half
        self.use_tracking = use_tracking
        self.debris_min_area = debris_min_area
        self.debris_max_area = debris_max_area
        self.debris_debug = debris_debug
        
        self._fish_model = None
        self._blob_detector = None
        self._initialized = False
        self._warmed_up = False
    
    def _initialize(self) -> bool:
        """Lazy initialization of YOLO fish model and OpenCV blob detector."""
        if self._initialized:
            return True
        
        global _yolo_available
        if _yolo_available is False:
            return False
        
        if not _load_yolo():
            print("YOLO (ultralytics) not available. Install with: pip install ultralytics")
            return False
        
        # Load fish model
        fish_path = _find_model_path(Path(self.model_path).name)
        if fish_path is None:
            print(f"Fish YOLO model not found: {self.model_path}")
            return False
        
        try:
            self._fish_model = _YOLO(str(fish_path))
            self._fish_model.to(self.device)
            print(f"Loaded fish model: {fish_path}")
            
            # Initialize blob detector for debris (tuned for low contrast)
            self._blob_detector = self._create_blob_detector()
            print(f"OpenCV blob detector (area: {self.debris_min_area}-{self.debris_max_area}px)")
            
            self._initialized = True
            return True
        except Exception as e:
            print(f"Failed to initialize detector: {e}")
            return False
    
    def _create_blob_detector(self) -> cv2.SimpleBlobDetector:
        """Create blob detector for debris detection.
        
        Narrow threshold range (10-30) focuses on subtle differences.
        """
        params = cv2.SimpleBlobDetector_Params()
        
        # Threshold settings - narrow range for subtle contrast
        params.minThreshold = 10
        params.maxThreshold = 30
        params.thresholdStep = 5
        
        # Filter by area
        params.filterByArea = True
        params.minArea = self.debris_min_area
        params.maxArea = self.debris_max_area
        
        # Disable other filters
        params.filterByCircularity = False
        params.filterByConvexity = False
        params.filterByInertia = False
        params.filterByColor = False
        
        return cv2.SimpleBlobDetector_create(params)
    
    def get_name(self) -> str:
        return "yolo_obb"
    
    def warmup(self):
        """Warmup YOLO model with dummy inference."""
        if self._warmed_up:
            return
        if not self._initialize():
            return
        try:
            dummy = np.zeros((self.imgsz, self.imgsz, 3), dtype=np.uint8)
            self._fish_model(dummy, imgsz=self.imgsz, half=self.half, verbose=False)
            self._warmed_up = True
            print(f"YOLO+OpenCV hybrid detector warmed up (imgsz={self.imgsz})")
        except Exception as e:
            print(f"YOLO warmup failed: {e}")
    
    def _species_name(self, class_id: int) -> str:
        """Resolve class id to species name from checkpoint or fallback map."""
        if self._fish_model is not None and getattr(self._fish_model, "names", None):
            return str(self._fish_model.names.get(class_id, "unknown"))
        return self.FISH_CLASS_NAMES.get(class_id, "unknown")

    @staticmethod
    def _result_detections(result):
        """Return ultralytics Boxes/OBB tensor container (detect vs obb task)."""
        obb = getattr(result, "obb", None)
        if obb is not None and len(obb):
            return obb
        boxes = getattr(result, "boxes", None)
        if boxes is not None and len(boxes):
            return boxes
        return None

    def _run_fish_model(self, image: np.ndarray, tracking: bool = False, persist: bool = True) -> List[FishDetection]:
        """Run fish model and extract fish detections only."""
        fish_detections = []
        
        try:
            if tracking:
                results = self._fish_model.track(
                    image,
                    conf=self.confidence_threshold,
                    iou=self.iou_threshold,
                    imgsz=self.imgsz,
                    half=self.half,
                    persist=persist,
                    verbose=False,
                )
            else:
                results = self._fish_model(
                    image,
                    conf=self.confidence_threshold,
                    iou=self.iou_threshold,
                    imgsz=self.imgsz,
                    half=self.half,
                    verbose=False,
                )
        except Exception as e:
            print(f"Fish model inference failed: {e}")
            return fish_detections
        
        for result in results:
            detections = self._result_detections(result)
            if detections is None:
                continue
            
            for i in range(len(detections)):
                xyxy = detections.xyxy[i].cpu().numpy()
                x1, y1, x2, y2 = map(int, xyxy)
                w, h = x2 - x1, y2 - y1
                if w <= 0 or h <= 0:
                    continue
                
                class_id = int(detections.cls[i].cpu().numpy())
                confidence = float(detections.conf[i].cpu().numpy())
                class_name = self._species_name(class_id)
                
                if class_name in self._IGNORED_SPECIES:
                    continue
                
                det = FishDetection(
                    bbox=(x1, y1, w, h),
                    species=class_name,
                    confidence=confidence,
                )
                
                if tracking and getattr(detections, "id", None) is not None:
                    det._track_id = int(detections.id[i].cpu().numpy())
                
                fish_detections.append(det)
        
        return fish_detections
    
    def _run_debris_opencv(self, image: np.ndarray, debug: bool = False) -> List[DebrisDetection]:
        """Detect debris using SimpleBlobDetector.
        
        Args:
            image: BGR image from camera
            debug: If True, print keypoint details for tuning
            
        Returns:
            List of DebrisDetection objects
        """
        debris_detections = []
        
        if self._blob_detector is None:
            return debris_detections
        
        try:
            # Convert to grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Light blur to reduce noise
            blurred = cv2.GaussianBlur(gray, (3, 3), 0)
            
            # Detect blobs
            keypoints = self._blob_detector.detect(blurred)
            
            if debug and keypoints:
                print(f"[Debris] Found {len(keypoints)} blobs:")
                for i, kp in enumerate(keypoints[:10]):  # Show first 10
                    # Get pixel value at keypoint location
                    px, py = int(kp.pt[0]), int(kp.pt[1])
                    if 0 <= py < gray.shape[0] and 0 <= px < gray.shape[1]:
                        pixel_val = gray[py, px]
                        # Get local background (5x5 neighborhood mean)
                        y1, y2 = max(0, py-5), min(gray.shape[0], py+6)
                        x1, x2 = max(0, px-5), min(gray.shape[1], px+6)
                        bg_val = np.mean(gray[y1:y2, x1:x2])
                        contrast = abs(float(pixel_val) - bg_val)
                        print(f"  [{i}] pos=({px},{py}) size={kp.size:.1f} "
                              f"pixel={pixel_val} bg={bg_val:.1f} contrast={contrast:.1f}")
            
            # Convert keypoints to DebrisDetection
            for kp in keypoints:
                x, y = int(kp.pt[0]), int(kp.pt[1])
                size = max(int(kp.size), 4)  # minimum 4px for visibility
                
                # Create bounding box centered on keypoint
                x1 = max(0, x - size // 2)
                y1 = max(0, y - size // 2)
                
                debris_detections.append(DebrisDetection(
                    bbox=(x1, y1, size, size),
                    confidence=0.7,
                ))
        except Exception as e:
            print(f"OpenCV debris detection failed: {e}")
        
        return debris_detections
    
    def detect(self, image: np.ndarray) -> DetectionResult:
        """Detect fish (YOLO) and debris (OpenCV).
        
        - Fish: YOLO model for sturgeon/salmon detection
        - Debris: OpenCV blob detection for small particles
        
        Args:
            image: BGR image from camera
            
        Returns:
            DetectionResult with fish and debris detections
        """
        if self.use_tracking:
            return self.detect_with_tracking(image)
        
        if not self._initialize():
            return DetectionResult()
        
        # YOLO for fish, OpenCV for debris
        fish_detections = self._run_fish_model(image, tracking=False)
        debris_detections = self._run_debris_opencv(image, debug=self.debris_debug)
        
        return DetectionResult(
            fish_detections=fish_detections,
            debris_detections=debris_detections,
        )
    
    def detect_with_tracking(
        self,
        image: np.ndarray,
        persist: bool = True
    ) -> DetectionResult:
        """Detect with tracking for fish, OpenCV for debris.
        
        Args:
            image: BGR image
            persist: Whether to persist tracking across frames
            
        Returns:
            DetectionResult with fish IDs from tracker
        """
        if not self._initialize():
            return DetectionResult()
        
        # YOLO with tracking for fish, OpenCV for debris
        fish_detections = self._run_fish_model(image, tracking=True, persist=persist)
        debris_detections = self._run_debris_opencv(image, debug=self.debris_debug)
        
        return DetectionResult(
            fish_detections=fish_detections,
            debris_detections=debris_detections,
        )
