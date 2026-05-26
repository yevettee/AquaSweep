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

            prompt = "This is an image of the bottom of an aquarium. Is the object in the center a shark poop (mud ball)? Answer only with 'Yes' or 'No'."

            payload = {
                "model": self.model,
                "prompt": prompt,
                "images": [img_b64],
                "stream": False
            }

            response = requests.post(self.endpoint, json=payload, timeout=5.0)
            if response.status_code == 200:
                result = response.json().get("response", "").strip().lower()
                if "yes" in result:
                    return True
                return False
            else:
                self.logger.warning(f"VLM verification failed with status {response.status_code}")
                return False
        except Exception as e:
            self.logger.error(f"VLM verification error: {e}")
            # Fallback: if VLM is unreachable, return True so we don't lose detections
            return True
