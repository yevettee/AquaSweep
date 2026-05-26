"""Visualization utilities for fish detection results."""

import cv2
import numpy as np
from typing import List, Optional

from aqua_detection.fish_detectors.base import DetectionResult, FishDetection, DebrisDetection, FishStatus


def draw_fish_detections(
    image: np.ndarray,
    detections: List[FishDetection],
    color: tuple = (0, 0, 255),
    thickness: int = 2
) -> np.ndarray:
    """Draw fish bounding boxes on image."""
    result = image.copy()
    
    for det in detections:
        x, y, w, h = det.bbox
        cv2.rectangle(result, (x, y), (x + w, y + h), color, thickness)
        
        label = det.species
        if det.confidence < 1.0:
            label = f"{label} ({det.confidence:.2f})"
        
        cv2.putText(
            result, label,
            (x, y - 10),
            cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, thickness
        )
    
    return result


def draw_debris_detections(
    image: np.ndarray,
    detections: List[DebrisDetection],
    color: tuple = (0, 255, 0),
    thickness: int = 2
) -> np.ndarray:
    """Draw debris bounding boxes on image."""
    result = image.copy()
    
    for det in detections:
        x, y, w, h = det.bbox
        cv2.rectangle(result, (x, y), (x + w, y + h), color, thickness)
    
    return result


def draw_fish_status(
    image: np.ndarray,
    fish_statuses: List[FishStatus],
    normal_color: tuple = (0, 255, 0),
    suspicious_color: tuple = (0, 0, 255),
    thickness: int = 2
) -> np.ndarray:
    """Draw fish with status indicators."""
    result = image.copy()
    
    for status in fish_statuses:
        x, y = status.position
        color = suspicious_color if status.status == "suspicious" else normal_color
        
        # Draw marker at fish position
        cv2.circle(result, (int(x), int(y)), 10, color, thickness)
        
        # Draw status text
        label = f"{status.fish_id}: {status.status}"
        if status.velocity > 0:
            label += f" v={status.velocity:.2f}"
        
        cv2.putText(
            result, label,
            (int(x) + 15, int(y)),
            cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, thickness
        )
    
    return result


def draw_detection_result(
    image: np.ndarray,
    result: DetectionResult,
    fish_color: tuple = (0, 0, 255),
    debris_color: tuple = (0, 255, 0),
    show_stats: bool = True
) -> np.ndarray:
    """Draw complete detection result with stats overlay."""
    output = image.copy()
    
    # Draw fish detections
    for det in result.fish_detections:
        x, y, w, h = det.bbox
        cv2.rectangle(output, (x, y), (x + w, y + h), fish_color, 2)
        cv2.putText(
            output, det.species,
            (x, y - 5),
            cv2.FONT_HERSHEY_SIMPLEX, 0.5, fish_color, 2
        )
    
    # Draw debris detections
    for det in result.debris_detections:
        x, y, w, h = det.bbox
        cv2.rectangle(output, (x, y), (x + w, y + h), debris_color, 1)
    
    # Stats overlay
    if show_stats:
        stats_text = f"Fish: {result.fish_count} | Debris: {result.debris_count}"
        cv2.putText(
            output, stats_text,
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2
        )
    
    return output
