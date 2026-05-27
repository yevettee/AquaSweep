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

    def classify_object(self, image: np.ndarray) -> str:
        """
        Classify the image crop into one of three categories: 'alive' (live shark), 'dead' (dead shark), or 'debris'.
        """
        try:
            _, buffer = cv2.imencode('.jpg', image)
            img_b64 = base64.b64encode(buffer).decode('utf-8')

            prompt = (
                "Look at this cropped image. Is this a live shark, a dead shark, or debris (poop/non-shark object)? "
                "Answer with EXACTLY ONE word: 'alive', 'dead', or 'debris'."
            )

            payload = {
                "model": self.model,
                "prompt": prompt,
                "images": [img_b64],
                "stream": False
            }

            # Increased timeout since we are now relying entirely on VLM for classification
            response = requests.post(self.endpoint, json=payload, timeout=2.0)
            if response.status_code == 200:
                result = response.json().get("response", "").strip().lower()
                print(f"[VLM] Classification result: {result}")
                
                if "alive" in result:
                    return "alive"
                elif "dead" in result:
                    return "dead"
                else:
                    return "debris"
            else:
                self.logger.warning(f"VLM classification failed with status {response.status_code}")
                return "debris"
        except Exception:
            # Fallback
            return "debris"
