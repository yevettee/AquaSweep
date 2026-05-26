"""DINOv2-based fish status classifier.

Determines if a fish is alive or suspicious (dead/sick) using:
1. Sharpness variance (bimodal = water surface boundary = suspicious)
2. Saturation variance (exposed vs submerged parts)
3. Velocity from optical flow

Key insight: Dead fish floating at surface have mixed sharpness/saturation
(part above water is sharp, part below is blurry), while alive fish
underwater have uniform (low) sharpness throughout.
"""

import numpy as np
from typing import Tuple, Optional, Dict
import cv2

from aqua_detection.fish_detectors.base import BaseStatusClassifier

# DINOv2 imports (lazy loading)
_dinov2_available = None
_torch = None
_dinov2_model = None


def _load_dinov2():
    """Lazy load DINOv2 to avoid import errors."""
    global _dinov2_available, _torch, _dinov2_model
    
    if _dinov2_available is not None:
        return _dinov2_available
    
    try:
        import torch
        _torch = torch
        _dinov2_available = True
    except ImportError:
        _dinov2_available = False
    
    return _dinov2_available


class FishDINOExtractor(BaseStatusClassifier):
    """DINOv2-based fish status classifier.
    
    Analyzes visual features to determine if fish is alive or suspicious.
    Uses sharpness/saturation distribution analysis - key insight is that
    dead fish at surface have bimodal distribution (sharp above water,
    blurry below), while alive fish underwater have uniform distribution.
    """
    
    def __init__(
        self,
        model_type: str = "dinov2_vits14",
        device: str = "cuda",
        sharpness_var_threshold: float = 0.3,
        saturation_var_threshold: float = 0.25,
        mean_sharpness_threshold: float = 100.0,
        velocity_threshold: float = 0.02,
        use_dino_features: bool = True,
    ):
        """Initialize DINOv2 extractor.
        
        Args:
            model_type: DINOv2 model variant (dinov2_vits14, dinov2_vitb14, etc.)
            device: "cuda" or "cpu"
            sharpness_var_threshold: Threshold for bimodal sharpness detection
            saturation_var_threshold: Threshold for bimodal saturation detection
            mean_sharpness_threshold: Threshold for surface exposure detection
            velocity_threshold: Relative velocity threshold (suspicious if below)
            use_dino_features: Whether to use DINOv2 semantic features
        """
        self.model_type = model_type
        self.device = device
        self.sharpness_var_threshold = sharpness_var_threshold
        self.saturation_var_threshold = saturation_var_threshold
        self.mean_sharpness_threshold = mean_sharpness_threshold
        self.velocity_threshold = velocity_threshold
        self.use_dino_features = use_dino_features
        
        self._model = None
        self._transform = None
        self._initialized = False
    
    def _initialize(self) -> bool:
        """Lazy initialization of DINOv2 model."""
        if self._initialized:
            return True
        
        if not _load_dinov2():
            print("PyTorch not available for DINOv2")
            return False
        
        if not self.use_dino_features:
            self._initialized = True
            return True
        
        try:
            # Load DINOv2 from torch hub
            self._model = _torch.hub.load(
                'facebookresearch/dinov2',
                self.model_type,
                pretrained=True
            )
            self._model = self._model.to(self.device)
            self._model.eval()
            
            # Standard ImageNet normalization for DINOv2
            self._mean = _torch.tensor([0.485, 0.456, 0.406]).view(1, 3, 1, 1).to(self.device)
            self._std = _torch.tensor([0.229, 0.224, 0.225]).view(1, 3, 1, 1).to(self.device)
            
            self._initialized = True
            return True
            
        except Exception as e:
            print(f"Failed to initialize DINOv2: {e}")
            self.use_dino_features = False
            self._initialized = True
            return True
    
    def extract_features(self, fish_image: np.ndarray) -> Dict[str, float]:
        """Extract visual features from fish bbox image.
        
        Args:
            fish_image: Cropped BGR image of fish region
            
        Returns:
            Dictionary of extracted features
        """
        features = {}
        
        # 1. Sharpness analysis (Laplacian variance)
        gray = cv2.cvtColor(fish_image, cv2.COLOR_BGR2GRAY)
        sharpness_map = self._compute_sharpness_map(gray)
        features['sharpness_mean'] = float(np.mean(sharpness_map))
        features['sharpness_var'] = float(np.var(sharpness_map))
        features['sharpness_std'] = float(np.std(sharpness_map))
        
        # 2. Saturation analysis
        hsv = cv2.cvtColor(fish_image, cv2.COLOR_BGR2HSV)
        saturation = hsv[:, :, 1].astype(float) / 255.0
        features['saturation_mean'] = float(np.mean(saturation))
        features['saturation_var'] = float(np.var(saturation))
        features['saturation_std'] = float(np.std(saturation))
        
        # 3. Brightness analysis (for belly exposure detection)
        value = hsv[:, :, 2].astype(float) / 255.0
        features['brightness_mean'] = float(np.mean(value))
        features['brightness_var'] = float(np.var(value))
        
        # 4. DINOv2 semantic features (optional)
        if self.use_dino_features and self._model is not None:
            dino_features = self._extract_dino_features(fish_image)
            features.update(dino_features)
        
        return features
    
    def _compute_sharpness_map(self, gray: np.ndarray, kernel_size: int = 3) -> np.ndarray:
        """Compute per-pixel sharpness using Laplacian."""
        laplacian = cv2.Laplacian(gray, cv2.CV_64F, ksize=kernel_size)
        
        # Compute local variance as sharpness measure
        kernel = np.ones((15, 15), np.float32) / 225
        laplacian_sq = laplacian ** 2
        local_mean_sq = cv2.filter2D(laplacian_sq, -1, kernel)
        
        return local_mean_sq
    
    def _extract_dino_features(self, fish_image: np.ndarray) -> Dict[str, float]:
        """Extract DINOv2 semantic features."""
        if self._model is None:
            return {}
        
        try:
            # Resize to DINOv2 expected size (multiple of 14 for ViT)
            h, w = fish_image.shape[:2]
            new_h = (h // 14) * 14
            new_w = (w // 14) * 14
            if new_h < 14:
                new_h = 14
            if new_w < 14:
                new_w = 14
            
            resized = cv2.resize(fish_image, (new_w, new_h))
            
            # Convert to tensor
            img_rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
            img_tensor = _torch.from_numpy(img_rgb).permute(2, 0, 1).float() / 255.0
            img_tensor = img_tensor.unsqueeze(0).to(self.device)
            
            # Normalize
            img_tensor = (img_tensor - self._mean) / self._std
            
            # Extract features
            with _torch.no_grad():
                features = self._model.forward_features(img_tensor)
                patch_tokens = features['x_norm_patchtokens']  # [1, N, D]
                cls_token = features['x_norm_clstoken']  # [1, D]
            
            # Compute statistics from patch tokens
            patch_norms = _torch.norm(patch_tokens, dim=-1)  # [1, N]
            
            return {
                'dino_patch_norm_mean': float(patch_norms.mean().cpu()),
                'dino_patch_norm_var': float(patch_norms.var().cpu()),
                'dino_cls_norm': float(_torch.norm(cls_token).cpu()),
            }
            
        except Exception as e:
            print(f"DINOv2 feature extraction failed: {e}")
            return {}
    
    def classify(
        self,
        fish_image: np.ndarray,
        velocity: float = 0.0
    ) -> Tuple[str, float]:
        """Classify fish status as alive or suspicious.
        
        Args:
            fish_image: Cropped BGR image of fish region
            velocity: Computed relative velocity (0-1 range)
            
        Returns:
            (status, confidence) tuple
            status: "alive" or "suspicious"
            confidence: 0.0 to 1.0
        """
        if not self._initialize():
            return "alive", 0.5
        
        # Extract features
        features = self.extract_features(fish_image)
        
        # Compute suspicious score
        score = 0.0
        
        # 1. Sharpness variance (bimodal = water surface boundary)
        # Dead fish at surface: part sharp (above water), part blurry (below)
        sharpness_var_normalized = features['sharpness_var'] / (features['sharpness_mean'] + 1e-6)
        if sharpness_var_normalized > self.sharpness_var_threshold:
            score += 0.35
        
        # 2. Saturation variance (exposed vs submerged)
        if features['saturation_var'] > self.saturation_var_threshold:
            score += 0.25
        
        # 3. Mean sharpness (surface exposure = sharper)
        if features['sharpness_mean'] > self.mean_sharpness_threshold:
            score += 0.15
        
        # 4. Velocity (slow/stationary = suspicious)
        if velocity < self.velocity_threshold:
            score += 0.25
        
        # Determine status
        if score > 0.5:
            status = "suspicious"
            confidence = min(score, 1.0)
        else:
            status = "alive"
            confidence = 1.0 - score
        
        return status, confidence
    
    def classify_batch(
        self,
        fish_images: list,
        velocities: list
    ) -> list:
        """Classify multiple fish at once.
        
        Args:
            fish_images: List of cropped fish BGR images
            velocities: List of velocities for each fish
            
        Returns:
            List of (status, confidence) tuples
        """
        results = []
        for img, vel in zip(fish_images, velocities):
            results.append(self.classify(img, vel))
        return results


class SimpleFishStatusClassifier(BaseStatusClassifier):
    """Color-based fish status classifier.
    
    Classifies fish as alive or suspicious based on:
    1. Contrast with background: Dead fish have HIGH contrast with water
    2. Water similarity: Alive fish are similar to water color (blurry, underwater)
    3. HSV bimodal: Suspicious fish have high variance (part exposed, part submerged)
    4. Velocity (optional): Slow/stationary = suspicious
    """
    
    def __init__(
        self,
        contrast_threshold: float = 8.0,
        water_similarity_threshold: float = 0.3,
        value_std_threshold: float = 40.0,
        saturation_std_threshold: float = 30.0,
        velocity_threshold: float = 0.02,
        use_velocity: bool = True,
        velocity_weight: float = 0.20,
        # Legacy params (kept for compatibility)
        darkness_threshold: float = 0.4,
        intensity_threshold: float = 0.3,
    ):
        """Initialize classifier.
        
        Args:
            contrast_threshold: Brightness contrast threshold (higher = more different from bg)
            water_similarity_threshold: Ratio of water-like pixels below = suspicious
            value_std_threshold: Value (brightness) std threshold for bimodal
            saturation_std_threshold: Saturation std threshold for bimodal
            velocity_threshold: Relative velocity below = suspicious
            use_velocity: Whether to use velocity in classification
            velocity_weight: Weight for velocity score (0.0-1.0)
        """
        self.contrast_threshold = contrast_threshold
        self.water_similarity_threshold = water_similarity_threshold
        self.value_std_threshold = value_std_threshold
        self.saturation_std_threshold = saturation_std_threshold
        self.velocity_threshold = velocity_threshold
        self.use_velocity = use_velocity
        self.velocity_weight = velocity_weight
        self.darkness_threshold = darkness_threshold
        self.intensity_threshold = intensity_threshold
        
        # Store last context for feature extraction
        self._last_full_image = None
        self._last_bbox = None
    
    def _compute_color_features(
        self,
        fish_image: np.ndarray,
        full_image: Optional[np.ndarray] = None,
        bbox: Optional[Tuple[int, int, int, int]] = None,
    ) -> Dict[str, float]:
        """Extract color features including contrast with background.
        
        Key insight: Dead fish floating on surface have HIGH contrast with
        the blue water background. Alive fish underwater blend in.
        """
        hsv = cv2.cvtColor(fish_image, cv2.COLOR_BGR2HSV)
        h, s, v = hsv[:, :, 0], hsv[:, :, 1], hsv[:, :, 2]
        
        features = {}
        
        # 1. Fish region statistics
        features['mean_value'] = float(np.mean(v))
        features['mean_saturation'] = float(np.mean(s))
        features['mean_hue'] = float(np.mean(h))
        
        # 2. Contrast with surrounding background (KEY FEATURE)
        features['bg_contrast'] = 0.0
        if full_image is not None and bbox is not None:
            bg_features = self._compute_background_features(full_image, bbox)
            features.update(bg_features)
            
            # Contrast = difference in brightness between fish and background
            features['bg_contrast'] = abs(features['mean_value'] - features.get('bg_mean_value', features['mean_value']))
        
        # 3. Water similarity: blue-ish, low saturation, high value
        water_like_mask = (h > 90) & (h < 130) & (s < 80) & (v > 100)
        features['water_similarity'] = float(np.sum(water_like_mask) / max(water_like_mask.size, 1))
        
        # 4. HSV bimodal distribution (high variance = surface boundary)
        features['value_std'] = float(np.std(v))
        features['saturation_std'] = float(np.std(s))
        
        # 5. Vertical brightness difference
        mid_y = fish_image.shape[0] // 2
        if mid_y > 0:
            top_v = np.mean(v[:mid_y, :])
            bottom_v = np.mean(v[mid_y:, :])
            features['vertical_brightness_diff'] = float(abs(top_v - bottom_v))
        else:
            features['vertical_brightness_diff'] = 0.0
        
        return features
    
    def _compute_background_features(
        self,
        full_image: np.ndarray,
        bbox: Tuple[int, int, int, int],
        margin: int = 20,
    ) -> Dict[str, float]:
        """Compute features of the background around the fish bbox."""
        x, y, w, h = bbox
        img_h, img_w = full_image.shape[:2]
        
        # Expand bbox by margin for background sampling
        x1_bg = max(0, x - margin)
        y1_bg = max(0, y - margin)
        x2_bg = min(img_w, x + w + margin)
        y2_bg = min(img_h, y + h + margin)
        
        # Create mask: 1 for background (outside fish), 0 for fish
        bg_region = full_image[y1_bg:y2_bg, x1_bg:x2_bg].copy()
        mask = np.ones((y2_bg - y1_bg, x2_bg - x1_bg), dtype=bool)
        
        # Mark fish region as False in mask
        fish_x1 = x - x1_bg
        fish_y1 = y - y1_bg
        fish_x2 = fish_x1 + w
        fish_y2 = fish_y1 + h
        
        fish_x1 = max(0, fish_x1)
        fish_y1 = max(0, fish_y1)
        fish_x2 = min(mask.shape[1], fish_x2)
        fish_y2 = min(mask.shape[0], fish_y2)
        
        mask[fish_y1:fish_y2, fish_x1:fish_x2] = False
        
        # Extract background pixels
        if np.sum(mask) > 0:
            bg_hsv = cv2.cvtColor(bg_region, cv2.COLOR_BGR2HSV)
            bg_v = bg_hsv[:, :, 2][mask]
            bg_s = bg_hsv[:, :, 1][mask]
            bg_h = bg_hsv[:, :, 0][mask]
            
            return {
                'bg_mean_value': float(np.mean(bg_v)),
                'bg_mean_saturation': float(np.mean(bg_s)),
                'bg_mean_hue': float(np.mean(bg_h)),
            }
        
        return {'bg_mean_value': 150.0, 'bg_mean_saturation': 50.0, 'bg_mean_hue': 100.0}
    
    def classify(
        self,
        fish_image: np.ndarray,
        velocity: float = 0.0,
        full_image: Optional[np.ndarray] = None,
        bbox: Optional[Tuple[int, int, int, int]] = None,
    ) -> Tuple[str, float]:
        """Classify fish status using contrast-based analysis.
        
        Args:
            fish_image: Cropped BGR image of fish region
            velocity: Relative velocity (0-1 range)
            full_image: Full frame image (for background contrast)
            bbox: Fish bounding box in full image
            
        Returns:
            (status, confidence) tuple
        """
        if fish_image.size == 0:
            return "alive", 0.5
        
        # Store context for get_features()
        self._last_full_image = full_image
        self._last_bbox = bbox
        
        features = self._compute_color_features(fish_image, full_image, bbox)
        score = 0.0
        
        # Weight multiplier when velocity is disabled
        color_weight = 1.0 if self.use_velocity else (1.0 / (1.0 - self.velocity_weight))
        
        # 1. HIGH contrast with background -> suspicious (weight: 0.45)
        # Dead fish floating on surface stand out from blue water
        # Note: 0.45 * 1.25 (no velocity) = 0.5625 > 0.5 threshold
        if features['bg_contrast'] > self.contrast_threshold:
            score += 0.45 * color_weight
        
        # 2. Different from water color -> suspicious (weight: 0.25)
        if features['water_similarity'] < self.water_similarity_threshold:
            score += 0.25 * color_weight
        
        # 3. HSV bimodal distribution -> suspicious (weight: 0.15)
        if features['value_std'] > self.value_std_threshold or features['saturation_std'] > self.saturation_std_threshold:
            score += 0.15 * color_weight
        
        # 4. Velocity (toggleable, weight: 0.20)
        if self.use_velocity and velocity < self.velocity_threshold:
            score += self.velocity_weight
        
        # Determine status
        if score > 0.5:
            status = "suspicious"
            confidence = min(score, 1.0)
        else:
            status = "alive"
            confidence = 1.0 - score
        
        return status, confidence
    
    def get_features(self, fish_image: np.ndarray) -> Dict[str, float]:
        """Get all extracted features for debugging."""
        return self._compute_color_features(
            fish_image,
            self._last_full_image,
            self._last_bbox,
        )
