import cv2
import numpy as np
import logging
import threading

try:
    from ultralytics import YOLOWorld
except ImportError:
    YOLOWorld = None

from .base import BaseDetector, DetectionResult, FishDetection, DebrisDetection

class FishYOLOWorldDetector(BaseDetector):
    """
    Hybrid Detector:
    - YOLO-World for zero-shot object detection (sharks, excluding light reflection).
    - OpenCV SimpleBlobDetector for tiny, pixel-level synthetic debris (poop).
    """
    
    def __init__(self, model_id="yolov8s-world.pt", device="cuda"):
        if YOLOWorld is None:
            raise RuntimeError("ultralytics package is required for YOLO-World.")
            
        self.logger = logging.getLogger("FishYOLOWorldDetector")
        self.logger.info(f"Loading YOLO-World model {model_id} on {device}")
        
        # Load YOLO-World model
        self.model = YOLOWorld(model_id)
        self.model.to(device)
        
        # Monkey-patch BaseModel.fuse to prevent the "AttributeError: bn" crash in ultralytics
        from ultralytics.nn.tasks import BaseModel
        BaseModel.fuse = lambda self, *args, **kwargs: self
        
        # Define classes we want to detect via text prompt
        self.classes = [
            "shark", "sturgeon", "fish", "small fish", "poop", "small grayish white ball",
            "tiny dot", "speck",
            "bright light", "light reflection", "white glare"
        ]
        self.model.set_classes(self.classes)
        self._name = "YOLO-World"
        self._lock = threading.Lock()

    def detect(self, image: np.ndarray) -> DetectionResult:
        result = DetectionResult()
        
        # 1. Run YOLO-World for sharks and debris
        with self._lock:
            self.model.set_classes(self.classes)
            results = self.model(image, verbose=False, conf=0.001)
        
        if results:
            boxes = results[0].boxes
            for box in boxes:
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                conf = box.conf[0].cpu().item()
                cls_id = int(box.cls[0].cpu().item())
                
                x, y = int(x1), int(y1)
                w, h = int(x2 - x1), int(y2 - y1)
                bbox = (x, y, w, h)
                
                # Additional size filter to prevent merging two sharks into one big box
                if w > 75 and h > 75:
                    continue
                    
                try:
                    label = results[0].names[cls_id]
                except (KeyError, IndexError):
                    label = "unknown"
                
                # Exclude negative prompts (light reflections)
                if label in ["bright light", "light reflection", "white glare"]:
                    continue
                
                # If it's explicitly poop, or a tiny generic fish (< 15x15), it's Debris!
                is_poop = label in ["poop", "small grayish white ball", "tiny dot", "speck"]
                is_tiny_fish = label in ["fish", "small fish"] and (w < 20 and h < 20)
                
                if is_poop or is_tiny_fish:
                    if conf >= 0.001:  # Lowered from 0.005 to 0.001 to catch ultra-faint poop
                        det = DebrisDetection(bbox=bbox, confidence=conf)
                        result.debris_detections.append(det)
                
                elif label in ["shark", "sturgeon"]:
                    if conf >= 0.005:
                        det = FishDetection(bbox=bbox, confidence=conf, species="shark")
                        result.fish_detections.append(det)
                        
                elif label in ["fish", "small fish"]:
                    if conf >= 0.03:  # Must be larger than 20x20 (handled above) and higher conf
                        det = FishDetection(bbox=bbox, confidence=conf, species="shark")
                        result.fish_detections.append(det)
                        
        return result

    def get_name(self) -> str:
        return self._name
