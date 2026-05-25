"""Fish detection modules for AquaSweep."""

from .base import (
    BaseDetector,
    BaseTracker,
    BaseStatusClassifier,
    DetectionResult,
    FishDetection,
    DebrisDetection,
    FishStatus,
)
from .fish_opencv_detector import FishOpenCVDetector
from .fish_sam2_detector import FishSAM2Detector, FishSAM2VideoDetector

__all__ = [
    'BaseDetector',
    'BaseTracker', 
    'BaseStatusClassifier',
    'DetectionResult',
    'FishDetection',
    'DebrisDetection',
    'FishStatus',
    'FishOpenCVDetector',
    'FishSAM2Detector',
    'FishSAM2VideoDetector',
]
