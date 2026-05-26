import cv2
import numpy as np
import logging

try:
    from ultralytics import YOLOWorld
except ImportError:
    YOLOWorld = None

from .base import BaseDetector, DetectionResult, FishDetection, DebrisDetection

class FishYOLOWorldDetector(BaseDetector):
    """
    Detector using YOLO-World for zero-shot object detection.
    Separates sharks and general objects (debris candidates).
    """
    
    def __init__(self, model_id="yolov8s-world.pt", device="cuda"):
        if YOLOWorld is None:
            raise RuntimeError("ultralytics package is required for YOLO-World.")
            
        self.logger = logging.getLogger("FishYOLOWorldDetector")
        self.logger.info(f"Loading YOLO-World model {model_id} on {device}")
        
        # Load YOLO-World model
        self.model = YOLOWorld(model_id)
        self.model.to(device)
        
        # Define classes we want to detect via text prompt
        self.classes = ["shark", "object"]
        self.model.set_classes(self.classes)
        self._name = "YOLO-World"

    def detect(self, image: np.ndarray) -> DetectionResult:
        result = DetectionResult()
        
        # Run inference
        results = self.model(image, verbose=False)
        
        if not results:
            return result
            
        boxes = results[0].boxes
        
        for box in boxes:
            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
            conf = box.conf[0].cpu().item()
            cls_id = int(box.cls[0].cpu().item())
            
            x, y = int(x1), int(y1)
            w, h = int(x2 - x1), int(y2 - y1)
            bbox = (x, y, w, h)
            
            label = self.classes[cls_id]
            
            if label == "shark":
                # Ensure confidence threshold is met
                if conf > 0.4:
                    det = FishDetection(bbox=bbox, confidence=conf, species="shark")
                    result.fish_detections.append(det)
            elif label == "object":
                # Debris candidates might have lower confidence
                if conf > 0.1:
                    det = DebrisDetection(bbox=bbox, confidence=conf)
                    result.debris_detections.append(det)
                
        return result

    def get_name(self) -> str:
        return self._name
