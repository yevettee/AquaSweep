"""Fish velocity estimation using optical flow and tracking.

Computes relative velocity for each detected fish:
- Optical Flow: Dense flow within fish bbox
- Tracking-based: Bbox center displacement between frames

Velocity is normalized by frame diagonal to get relative velocity,
making it independent of fish distance from camera.
"""

import numpy as np
from typing import Dict, List, Optional, Tuple
import cv2
from collections import deque
from dataclasses import dataclass, field


@dataclass
class FishTrack:
    """Track history for a single fish."""
    
    fish_id: str
    positions: deque = field(default_factory=lambda: deque(maxlen=30))
    velocities: deque = field(default_factory=lambda: deque(maxlen=30))
    last_bbox: Optional[Tuple[int, int, int, int]] = None
    frames_since_seen: int = 0
    
    @property
    def mean_velocity(self) -> float:
        if not self.velocities:
            return 0.0
        return float(np.mean(list(self.velocities)))
    
    @property
    def velocity_variance(self) -> float:
        if len(self.velocities) < 2:
            return 0.0
        return float(np.var(list(self.velocities)))


class FishVelocityEstimator:
    """Estimates fish velocity using optical flow and tracking.
    
    Two methods combined:
    1. Farneback Optical Flow: Dense flow within fish bbox
    2. Tracking-based: Bbox center displacement
    
    Velocity is relative (normalized by frame diagonal).
    """
    
    def __init__(
        self,
        use_optical_flow: bool = True,
        use_tracking: bool = True,
        flow_pyr_scale: float = 0.5,
        flow_levels: int = 3,
        flow_winsize: int = 15,
        flow_iterations: int = 3,
        flow_poly_n: int = 5,
        flow_poly_sigma: float = 1.2,
        max_track_age: int = 30,
    ):
        """Initialize velocity estimator.
        
        Args:
            use_optical_flow: Use Farneback optical flow
            use_tracking: Use tracking-based velocity
            flow_*: Farneback optical flow parameters
            max_track_age: Max frames to keep track without update
        """
        self.use_optical_flow = use_optical_flow
        self.use_tracking = use_tracking
        self.max_track_age = max_track_age
        
        # Farneback parameters
        self.flow_params = {
            'pyr_scale': flow_pyr_scale,
            'levels': flow_levels,
            'winsize': flow_winsize,
            'iterations': flow_iterations,
            'poly_n': flow_poly_n,
            'poly_sigma': flow_poly_sigma,
            'flags': cv2.OPTFLOW_FARNEBACK_GAUSSIAN,
        }
        
        # State
        self._prev_gray: Optional[np.ndarray] = None
        self._prev_flow: Optional[np.ndarray] = None
        self._tracks: Dict[str, FishTrack] = {}
        self._frame_diagonal: float = 1.0
        self._next_id: int = 0
    
    def update(
        self,
        image: np.ndarray,
        fish_bboxes: List[Tuple[int, int, int, int]],
        fish_ids: Optional[List[str]] = None,
    ) -> Dict[str, float]:
        """Update velocity estimates with new frame.
        
        Args:
            image: Current BGR frame
            fish_bboxes: List of (x, y, w, h) bounding boxes
            fish_ids: Optional list of fish IDs (from tracker)
            
        Returns:
            Dict mapping fish_id to relative velocity (0-1 range)
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape[:2]
        self._frame_diagonal = np.sqrt(w**2 + h**2)
        
        # Assign IDs if not provided
        if fish_ids is None:
            fish_ids = [f"fish_{i}" for i in range(len(fish_bboxes))]
        
        velocities = {}
        
        # Compute optical flow if enabled
        flow = None
        if self.use_optical_flow and self._prev_gray is not None:
            flow = cv2.calcOpticalFlowFarneback(
                self._prev_gray, gray, None, **self.flow_params
            )
            self._prev_flow = flow
        
        # Update tracks
        for fish_id, bbox in zip(fish_ids, fish_bboxes):
            velocity = self._compute_velocity(fish_id, bbox, flow)
            velocities[fish_id] = velocity
        
        # Age out old tracks
        self._age_tracks(set(fish_ids))
        
        # Store for next frame
        self._prev_gray = gray
        
        return velocities
    
    def _compute_velocity(
        self,
        fish_id: str,
        bbox: Tuple[int, int, int, int],
        flow: Optional[np.ndarray],
    ) -> float:
        """Compute velocity for a single fish."""
        x, y, w, h = bbox
        center = (x + w // 2, y + h // 2)
        
        # Get or create track
        if fish_id not in self._tracks:
            self._tracks[fish_id] = FishTrack(fish_id=fish_id)
        
        track = self._tracks[fish_id]
        track.frames_since_seen = 0
        
        velocity_flow = 0.0
        velocity_track = 0.0
        
        # 1. Optical flow based velocity
        if self.use_optical_flow and flow is not None:
            velocity_flow = self._compute_flow_velocity(bbox, flow)
        
        # 2. Tracking based velocity
        if self.use_tracking and track.last_bbox is not None:
            prev_center = (
                track.last_bbox[0] + track.last_bbox[2] // 2,
                track.last_bbox[1] + track.last_bbox[3] // 2,
            )
            displacement = np.sqrt(
                (center[0] - prev_center[0])**2 +
                (center[1] - prev_center[1])**2
            )
            velocity_track = displacement / self._frame_diagonal
        
        # Combine velocities (weighted average)
        if self.use_optical_flow and self.use_tracking:
            velocity = 0.6 * velocity_flow + 0.4 * velocity_track
        elif self.use_optical_flow:
            velocity = velocity_flow
        else:
            velocity = velocity_track
        
        # Update track
        track.positions.append(center)
        track.velocities.append(velocity)
        track.last_bbox = bbox
        
        return velocity
    
    def _compute_flow_velocity(
        self,
        bbox: Tuple[int, int, int, int],
        flow: np.ndarray,
    ) -> float:
        """Compute velocity from optical flow within bbox."""
        x, y, w, h = bbox
        
        # Clamp to image bounds
        h_img, w_img = flow.shape[:2]
        x1 = max(0, x)
        y1 = max(0, y)
        x2 = min(w_img, x + w)
        y2 = min(h_img, y + h)
        
        if x2 <= x1 or y2 <= y1:
            return 0.0
        
        # Extract flow in bbox
        flow_roi = flow[y1:y2, x1:x2]
        
        # Compute magnitude
        fx, fy = flow_roi[:, :, 0], flow_roi[:, :, 1]
        magnitude = np.sqrt(fx**2 + fy**2)
        
        # Use median to be robust to outliers
        median_magnitude = np.median(magnitude)
        
        # Normalize by frame diagonal
        relative_velocity = median_magnitude / self._frame_diagonal
        
        return float(relative_velocity)
    
    def _age_tracks(self, active_ids: set):
        """Age out tracks that haven't been seen recently."""
        to_remove = []
        
        for fish_id, track in self._tracks.items():
            if fish_id not in active_ids:
                track.frames_since_seen += 1
                if track.frames_since_seen > self.max_track_age:
                    to_remove.append(fish_id)
        
        for fish_id in to_remove:
            del self._tracks[fish_id]
    
    def get_track_stats(self, fish_id: str) -> Optional[Dict]:
        """Get tracking statistics for a fish."""
        if fish_id not in self._tracks:
            return None
        
        track = self._tracks[fish_id]
        return {
            'mean_velocity': track.mean_velocity,
            'velocity_variance': track.velocity_variance,
            'track_length': len(track.positions),
            'last_position': track.positions[-1] if track.positions else None,
        }
    
    def reset(self):
        """Reset all state."""
        self._prev_gray = None
        self._prev_flow = None
        self._tracks.clear()


class SimpleVelocityEstimator:
    """Simple velocity estimator using only bbox tracking.
    
    Fallback when optical flow is not needed or too expensive.
    """
    
    def __init__(self, history_length: int = 10):
        self.history_length = history_length
        self._prev_bboxes: Dict[str, deque] = {}
        self._frame_diagonal: float = 1.0
    
    def update(
        self,
        frame_shape: Tuple[int, int],
        fish_bboxes: List[Tuple[int, int, int, int]],
        fish_ids: List[str],
    ) -> Dict[str, float]:
        """Update velocity estimates."""
        h, w = frame_shape[:2]
        self._frame_diagonal = np.sqrt(w**2 + h**2)
        
        velocities = {}
        
        for fish_id, bbox in zip(fish_ids, fish_bboxes):
            center = (bbox[0] + bbox[2] // 2, bbox[1] + bbox[3] // 2)
            
            if fish_id not in self._prev_bboxes:
                self._prev_bboxes[fish_id] = deque(maxlen=self.history_length)
            
            history = self._prev_bboxes[fish_id]
            
            if len(history) > 0:
                prev_center = history[-1]
                displacement = np.sqrt(
                    (center[0] - prev_center[0])**2 +
                    (center[1] - prev_center[1])**2
                )
                velocity = displacement / self._frame_diagonal
            else:
                velocity = 0.0
            
            history.append(center)
            velocities[fish_id] = velocity
        
        return velocities
    
    def reset(self):
        self._prev_bboxes.clear()
