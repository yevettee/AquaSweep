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
    """Abstract base class for fish/debris detectors.
    
    Implementations:
    - FishOpenCVDetector: Traditional CV with adaptive threshold
    - FishSAM2Detector: Zero-shot segmentation (Track A)
    - FishYOLODetector: Learned species classification (Track B)
    """
    
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


class BaseTracker(ABC):
    """Abstract base class for fish trackers.
    
    Assigns persistent IDs to detected fish across frames.
    """
    
    @abstractmethod
    def update(self, detections: List[FishDetection]) -> List[tuple]:
        """Update tracker with new detections.
        
        Args:
            detections: List of FishDetection from current frame
            
        Returns:
            List of (fish_id, FishDetection) tuples with assigned IDs
        """
        pass
    
    @abstractmethod
    def reset(self):
        """Reset tracker state."""
        pass


@dataclass
class FishStatus:
    """Status analysis result for a single fish."""
    
    fish_id: str
    species: str  # From detector (YOLO)
    status: str  # "alive" or "suspicious" (from DINOv2)
    velocity: float  # Relative velocity
    position: tuple  # (x, y) in image
    status_confidence: float = 1.0
    
    # DINOv2 features for debugging
    sharpness_variance: float = 0.0
    saturation_variance: float = 0.0


class BaseStatusClassifier(ABC):
    """Abstract base class for fish status classification.
    
    Determines if a fish is alive or suspicious (dead/sick)
    using DINOv2 features + velocity.
    """
    
    @abstractmethod
    def classify(
        self,
        fish_image: np.ndarray,
        velocity: float
    ) -> tuple:
        """Classify fish status.
        
        Args:
            fish_image: Cropped fish region
            velocity: Computed velocity from optical flow/tracking
            
        Returns:
            (status, confidence) where status is "alive" or "suspicious"
        """
        pass
