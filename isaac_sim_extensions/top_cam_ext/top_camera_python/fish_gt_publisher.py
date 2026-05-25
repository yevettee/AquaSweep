"""Fish Ground Truth Publisher for AquaSweep.

Publishes ground truth information for fish in each pool:
- Fish positions (3D pose)
- Fish species/type
- Fish status (alive/dead from isFlipped attribute)
- 2D bounding box projection for YOLO training

Integrated into top_cam_ext to synchronize GT with camera images.
"""

from __future__ import annotations

import json
import math
import traceback
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from pxr import Gf, Sdf, Usd, UsdGeom


@dataclass
class FishGroundTruth:
    """Ground truth data for a single fish."""
    
    fish_id: str
    pool_id: int
    species: str  # e.g., "sturgeon"
    is_flipped: bool  # True = dead/suspicious
    position_3d: Tuple[float, float, float]  # World coordinates
    rotation_yaw: float  # Yaw angle in radians
    bbox_2d: Optional[Tuple[int, int, int, int]] = None  # (x, y, w, h) in image
    
    @property
    def status(self) -> str:
        return "dead" if self.is_flipped else "alive"
    
    def to_dict(self) -> dict:
        return {
            "fish_id": self.fish_id,
            "pool_id": self.pool_id,
            "species": self.species,
            "status": self.status,
            "is_flipped": self.is_flipped,
            "position_3d": list(self.position_3d),
            "rotation_yaw": self.rotation_yaw,
            "bbox_2d": list(self.bbox_2d) if self.bbox_2d else None,
        }


class FishGTPublisher:
    """Collects and publishes fish ground truth from Isaac Sim.
    
    Usage:
        publisher = FishGTPublisher()
        gt_data = publisher.collect_all_pools()
        # gt_data is Dict[pool_id, List[FishGroundTruth]]
    """
    
    POOLS_PATH = "/World/Pools"
    FISH_PRIM_PREFIX = "Sturgeon_"
    
    def __init__(self):
        self._stage: Optional[Usd.Stage] = None
        self._camera_intrinsics: Dict[int, dict] = {}
    
    def set_stage(self, stage: Usd.Stage):
        """Set the USD stage to query."""
        self._stage = stage
    
    def set_camera_intrinsics(
        self,
        pool_id: int,
        fx: float,
        fy: float,
        cx: float,
        cy: float,
        width: int,
        height: int
    ):
        """Set camera intrinsics for 3D->2D projection."""
        self._camera_intrinsics[pool_id] = {
            "fx": fx, "fy": fy,
            "cx": cx, "cy": cy,
            "width": width, "height": height
        }
    
    def collect_pool(self, pool_id: int) -> List[FishGroundTruth]:
        """Collect ground truth for all fish in a pool."""
        if self._stage is None:
            return []
        
        pool_path = f"{self.POOLS_PATH}/Pool_{pool_id}"
        pool_prim = self._stage.GetPrimAtPath(pool_path)
        
        if not pool_prim.IsValid():
            return []
        
        fish_list = []
        
        # Iterate through children to find fish prims
        for child in pool_prim.GetChildren():
            child_name = child.GetName()
            
            if child_name.startswith(self.FISH_PRIM_PREFIX):
                fish_gt = self._extract_fish_gt(child, pool_id)
                if fish_gt:
                    fish_list.append(fish_gt)
        
        return fish_list
    
    def collect_all_pools(self, num_pools: int = 7) -> Dict[int, List[FishGroundTruth]]:
        """Collect ground truth for all pools."""
        result = {}
        for pool_id in range(1, num_pools + 1):
            result[pool_id] = self.collect_pool(pool_id)
        return result
    
    def _extract_fish_gt(self, prim: Usd.Prim, pool_id: int) -> Optional[FishGroundTruth]:
        """Extract ground truth from a fish prim."""
        try:
            fish_id = prim.GetName()
            
            # Get custom attributes
            is_flipped_attr = prim.GetAttribute("aquasweep:isFlipped")
            is_flipped = is_flipped_attr.Get() if is_flipped_attr.IsValid() else False
            
            semantic_class_attr = prim.GetAttribute("aquasweep:semanticClass")
            semantic_class = semantic_class_attr.Get() if semantic_class_attr.IsValid() else "sturgeon_alive"
            
            # Determine species from semantic class
            species = "sturgeon"  # Default
            if "sturgeon" in semantic_class.lower():
                species = "sturgeon"
            elif "salmon" in semantic_class.lower():
                species = "salmon"
            
            # Get transform
            xformable = UsdGeom.Xformable(prim)
            world_transform = xformable.ComputeLocalToWorldTransform(Usd.TimeCode.Default())
            
            # Extract position
            position = world_transform.ExtractTranslation()
            position_3d = (float(position[0]), float(position[1]), float(position[2]))
            
            # Extract yaw rotation
            rotation = world_transform.ExtractRotation()
            # Simplified yaw extraction (assuming Z-up)
            rotation_yaw = math.atan2(
                world_transform[1][0],
                world_transform[0][0]
            )
            
            fish_gt = FishGroundTruth(
                fish_id=fish_id,
                pool_id=pool_id,
                species=species,
                is_flipped=is_flipped,
                position_3d=position_3d,
                rotation_yaw=rotation_yaw,
            )
            
            # Project to 2D if camera intrinsics available
            if pool_id in self._camera_intrinsics:
                bbox_2d = self._project_to_2d(fish_gt, pool_id)
                fish_gt.bbox_2d = bbox_2d
            
            return fish_gt
            
        except Exception as e:
            traceback.print_exc()
            return None
    
    def _project_to_2d(
        self,
        fish_gt: FishGroundTruth,
        pool_id: int
    ) -> Optional[Tuple[int, int, int, int]]:
        """Project 3D fish position to 2D bounding box.
        
        Note: This is a simplified projection. For accurate results,
        need to use the actual camera extrinsics and fish bounding box.
        """
        intrinsics = self._camera_intrinsics.get(pool_id)
        if not intrinsics:
            return None
        
        # Get camera prim for extrinsics
        camera_path = f"{self.POOLS_PATH}/Pool_{pool_id}/TopCamera"
        camera_prim = self._stage.GetPrimAtPath(camera_path)
        
        if not camera_prim.IsValid():
            return None
        
        try:
            # Get camera transform
            cam_xform = UsdGeom.Xformable(camera_prim)
            cam_world = cam_xform.ComputeLocalToWorldTransform(Usd.TimeCode.Default())
            cam_world_inv = cam_world.GetInverse()
            
            # Transform fish position to camera space
            fish_pos = Gf.Vec3d(*fish_gt.position_3d)
            fish_cam = cam_world_inv.Transform(fish_pos)
            
            # Project to image (assuming camera looks down -Z)
            if fish_cam[2] >= 0:  # Behind camera
                return None
            
            fx, fy = intrinsics["fx"], intrinsics["fy"]
            cx, cy = intrinsics["cx"], intrinsics["cy"]
            
            # Perspective projection
            u = int(fx * (-fish_cam[0] / fish_cam[2]) + cx)
            v = int(fy * (-fish_cam[1] / fish_cam[2]) + cy)
            
            # Estimated bbox size (approximate based on distance)
            depth = abs(fish_cam[2])
            fish_size_world = 0.5  # Approximate fish size in meters
            bbox_size = int(fx * fish_size_world / depth)
            
            # Clamp to image bounds
            w, h = intrinsics["width"], intrinsics["height"]
            x1 = max(0, u - bbox_size // 2)
            y1 = max(0, v - bbox_size // 2)
            x2 = min(w, u + bbox_size // 2)
            y2 = min(h, v + bbox_size // 2)
            
            if x2 <= x1 or y2 <= y1:
                return None
            
            return (x1, y1, x2 - x1, y2 - y1)
            
        except Exception:
            traceback.print_exc()
            return None
    
    def to_yolo_format(
        self,
        fish_gt: FishGroundTruth,
        image_width: int,
        image_height: int,
        class_map: Dict[str, int] = None
    ) -> Optional[str]:
        """Convert to YOLO annotation format.
        
        Returns:
            YOLO format string: "class_id x_center y_center width height"
            All values normalized to [0, 1]
        """
        if fish_gt.bbox_2d is None:
            return None
        
        if class_map is None:
            class_map = {"sturgeon": 0, "salmon": 1, "debris": 2}
        
        class_id = class_map.get(fish_gt.species, 0)
        x, y, w, h = fish_gt.bbox_2d
        
        # Normalize to [0, 1]
        x_center = (x + w / 2) / image_width
        y_center = (y + h / 2) / image_height
        width = w / image_width
        height = h / image_height
        
        return f"{class_id} {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}"
    
    def to_json(self, gt_data: Dict[int, List[FishGroundTruth]]) -> str:
        """Convert all GT data to JSON string."""
        result = {}
        for pool_id, fish_list in gt_data.items():
            result[f"pool_{pool_id}"] = [f.to_dict() for f in fish_list]
        return json.dumps(result, indent=2)


def get_fish_gt_publisher() -> FishGTPublisher:
    """Factory function to get publisher instance."""
    return FishGTPublisher()
