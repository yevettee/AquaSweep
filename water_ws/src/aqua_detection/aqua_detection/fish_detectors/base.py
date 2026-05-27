"""Base interfaces for fish detection pipeline components."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional
import numpy as np


@dataclass
class FishDetection:
    """Single fish detection result."""
    
    bbox: tuple  # (x, y, w, h)
    mask: Optional[np.ndarray] = None  # Segmentation mask (optional)
    species: str = "unknown"  # Fish species (from YOLO)
    confidence: float = 1.0
    contour: Optional[np.ndarray] = None  # OpenCV contour (optional)
    
    @property
    def center(self) -> tuple:
        x, y, w, h = self.bbox
        return (x + w // 2, y + h // 2)
    
    @property
    def area(self) -> float:
        _, _, w, h = self.bbox
        return w * h


@dataclass
class DebrisDetection:
    """Single debris detection result."""
    
    bbox: tuple  # (x, y, w, h)
    confidence: float = 1.0
    contour: Optional[np.ndarray] = None


@dataclass
class DetectionResult:
    """Complete detection result for a frame."""
    
    fish_detections: List[FishDetection] = field(default_factory=list)
    debris_detections: List[DebrisDetection] = field(default_factory=list)
    frame_id: int = 0
    
    @property
    def fish_count(self) -> int:
        return len(self.fish_detections)
    
    @property
    def debris_count(self) -> int:
        return len(self.debris_detections)


class BaseDetector(ABC):
    """Abstract base class for fish/debris detectors (FishYOLODetector)."""
    
    @abstractmethod
    def detect(self, image: np.ndarray) -> DetectionResult:
        """Detect fish and debris in the image.
        
        Args:
            image: BGR image from camera
            
        Returns:
            DetectionResult with fish and debris detections
        """
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """Return detector name for logging/config."""
        pass


@dataclass
class FishStatus:
    """Status analysis result for a single fish."""
    
    fish_id: str
    species: str  # From detector (YOLO)
    status: str  # "alive" or "suspicious" (from CV classifier)
    position: tuple  # (x, y) in image
    status_confidence: float = 1.0
    
    sharpness_variance: float = 0.0
    saturation_variance: float = 0.0


class BaseStatusClassifier(ABC):
    """Abstract base class for fish status classification (CV features only)."""
    
    @abstractmethod
    def classify(
        self,
        fish_image: np.ndarray,
        full_image: Optional[np.ndarray] = None,
        bbox: Optional[tuple] = None,
    ) -> tuple:
        """Classify fish status.
        
        Args:
            fish_image: Cropped fish region
            full_image: Full frame (optional, for background contrast)
            bbox: Fish bbox in full image (optional)
            
        Returns:
            (status, confidence) where status is "alive" or "suspicious"
        """
        pass
