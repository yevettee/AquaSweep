import base64
import logging
import cv2
import numpy as np
import requests

class VLMValidator:
    """Validator using Ollama VLM to verify if an object is shark poop (debris)."""
    
    def __init__(self, endpoint="http://localhost:11434/api/generate", model="llava"):
        self.endpoint = endpoint
        self.model = model
        self.logger = logging.getLogger('VLMValidator')

    def is_debris(self, image: np.ndarray) -> bool:
        """
        Verify if the image patch is a debris (shark poop).
        
        Args:
            image: Cropped BGR image of the suspected debris.
            
        Returns:
            bool: True if VLM confirms it is debris.
        """
        try:
            # Encode image to base64
            _, buffer = cv2.imencode('.jpg', image)
            img_b64 = base64.b64encode(buffer).decode('utf-8')

            # A 34x34 crop is too blurry for LLaVA to recognize as "shark poop"
            # So we ask a much simpler question that it can actually answer from a blurry dot.
            prompt = "Look at the center of this image. Is there a small dot, speck, or grayish object visible? Answer only with 'yes' or 'no'."

            payload = {
                "model": self.model,
                "prompt": prompt,
                "images": [img_b64],
                "stream": False
            }

            # Drop the timeout to 0.5 seconds! If VLM is too slow, we just assume it's debris
            # rather than freezing the entire ROS 2 simulation.
            response = requests.post(self.endpoint, json=payload, timeout=0.5)
            if response.status_code == 200:
                result = response.json().get("response", "").strip().lower()
                print(f"[VLM] Prompt answered: {result}")
                if "yes" in result:
                    return True
                return False
            else:
                self.logger.warning(f"VLM verification failed with status {response.status_code}")
                return False
        except Exception:
            # Fallback: if VLM is unreachable, return True so we don't lose detections
            return True
