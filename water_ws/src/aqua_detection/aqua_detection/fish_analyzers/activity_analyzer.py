"""Fish status classifier based on movement activity with built-in tracking."""

import numpy as np
from collections import deque
from typing import Dict, Tuple

class ActivityFishStatusClassifier:
    """Classifies fish status based on movement activity across frames."""
    
    def __init__(self, history_size: int = 30, activity_threshold: float = 3.0, max_disappeared: int = 15):
        self.history_size = history_size
        self.activity_threshold = activity_threshold
        self.max_disappeared = max_disappeared
        
        self.next_object_id = 0
        self.objects = {} # object_id -> (cx, cy)
        self.disappeared = {} # object_id -> int
        self._history: Dict[int, deque] = {}
        self._last_activity: Dict[int, float] = {}
        self._updated_this_frame = set()
        
    def update_frame_start(self):
        """Call this before processing detections in a new frame."""
        self._updated_this_frame.clear()
        
    def classify(self, bbox: Tuple[int, int, int, int], track_id: int = None) -> Tuple[str, float, int]:
        """
        Classify fish as 'alive' or 'suspicious' based on movement history.
        Tracks objects internally using centroid distance.
        
        Args:
            bbox: Bounding box (x, y, w, h)
            track_id: Ignore this, we do internal tracking.
            
        Returns:
            status (str): "alive" or "suspicious"
            confidence (float): pseudo confidence score
            track_id (int): internal track ID assigned
        """
        x, y, w, h = bbox
        cx = x + w / 2.0
        cy = y + h / 2.0
        
        # Simple greedy centroid matching
        best_id = None
        min_dist = float('inf')
        
        for obj_id, (old_cx, old_cy) in self.objects.items():
            if obj_id in self._updated_this_frame:
                continue # Already matched in this frame
            dist = np.sqrt((cx - old_cx)**2 + (cy - old_cy)**2)
            if dist < min_dist and dist < 100: # Max tracking distance 100 pixels
                min_dist = dist
                best_id = obj_id
                
        if best_id is None:
            # Register new object
            best_id = self.next_object_id
            self.next_object_id += 1
            self._history[best_id] = deque(maxlen=self.history_size)
            self._last_activity[best_id] = 0.0
            self.disappeared[best_id] = 0
            
        # Update object
        self.objects[best_id] = (cx, cy)
        self._history[best_id].append((cx, cy))
        self.disappeared[best_id] = 0
        self._updated_this_frame.add(best_id)
        
        history = self._history[best_id]
        if len(history) < 2:
            self._last_activity[best_id] = 0.0
            return "alive", 0.5, best_id
            
        # Calculate Accumulated distance
        total_dist = 0.0
        for i in range(1, len(history)):
            prev = history[i-1]
            curr = history[i]
            dist = np.sqrt((curr[0] - prev[0])**2 + (curr[1] - prev[1])**2)
            total_dist += dist
            
        # Extrapolate to full history window if we don't have enough data
        if len(history) < self.history_size:
            projected_dist = total_dist / (len(history) - 1) * (self.history_size - 1)
        else:
            projected_dist = total_dist
            
        self._last_activity[best_id] = projected_dist
        
        if projected_dist <= self.activity_threshold:
            return "suspicious", 0.9, best_id
        else:
            return "alive", 0.9, best_id

    def update_frame_end(self):
        """Call this after processing all detections in a frame."""
        for obj_id in list(self.objects.keys()):
            if obj_id not in self._updated_this_frame:
                self.disappeared[obj_id] += 1
                if self.disappeared[obj_id] > self.max_disappeared:
                    # Deregister
                    del self.objects[obj_id]
                    del self.disappeared[obj_id]
                    if obj_id in self._history:
                        del self._history[obj_id]
                    if obj_id in self._last_activity:
                        del self._last_activity[obj_id]

    def get_features(self, track_id: int) -> dict:
        """Return calculated features for debug visualization."""
        if track_id is None:
            return {'activity': 0.0}
        return {'activity': self._last_activity.get(track_id, 0.0)}
