"""
Standalone YOLO Dataset Collection Script for AquaSweep.

This is a self-contained script that can be directly copied into 
Isaac Sim's Script Editor. No external imports needed.

Usage:
    1. Load AquaSweep environment in Isaac Sim
    2. Press Play to start simulation
    3. Open Window > Script Editor
    4. Copy this entire script and paste into Script Editor
    5. Press Ctrl+Enter to run
"""

#############################################
# CONFIGURATION - Edit these values as needed
#############################################

OUTPUT_DIR = "/home/woody/AquaSweep/water_ws/src/aqua_detection/dataset_replicator"
NUM_FRAMES = 50  # Number of frames to collect
RESOLUTION = (1280, 720)
TRAIN_VAL_SPLIT = 0.8  # 80% train, 20% val
POOLS_TO_COLLECT = [2, 5, 7]  # Which pools to collect from (only pools with fish)
IMAGE_FORMAT = "png"  # png for lossless

#############################################
# DO NOT EDIT BELOW THIS LINE
#############################################

import os
import random
import numpy as np
from PIL import Image

import omni.usd
import omni.replicator.core as rep
from pxr import Sdf


def get_fish_prims(stage):
    """Find all fish prims."""
    fish_prims = []
    pools_prim = stage.GetPrimAtPath("/World/Pools")
    if not pools_prim.IsValid():
        print("[collect] ERROR: /World/Pools not found!")
        return fish_prims
    
    for pool in pools_prim.GetChildren():
        if not pool.GetName().startswith("Pool_"):
            continue
        for child in pool.GetChildren():
            if child.GetName().startswith("Sturgeon_"):
                fish_prims.append(child)
    
    return fish_prims


def apply_labels(pool_ids):
    """Apply semantic labels to fish using Replicator API."""
    total_labeled = 0
    
    for pool_id in pool_ids:
        try:
            # Use rep.get.prims with path_pattern and rep.modify.semantics
            fish_group = rep.get.prims(path_pattern=f"/World/Pools/Pool_{pool_id}/Sturgeon_.*")
            with fish_group:
                rep.modify.semantics([("class", "sturgeon")])
            print(f"  Pool_{pool_id}: labeled with Replicator API")
            total_labeled += 1
        except Exception as e:
            print(f"  Pool_{pool_id}: labeling failed - {e}")
    
    return total_labeled


def save_yolo_data(frame_id, rgb_data, bbox_data, output_dir, split, img_w, img_h):
    """Save a single frame in YOLO format."""
    filename = f"frame_{frame_id:06d}"
    img_path = os.path.join(output_dir, "images", split, f"{filename}.{IMAGE_FORMAT}")
    label_path = os.path.join(output_dir, "labels", split, f"{filename}.txt")
    
    # Save image
    if isinstance(rgb_data, np.ndarray):
        # Remove alpha channel if present
        if rgb_data.shape[-1] == 4:
            rgb_data = rgb_data[:, :, :3]
        img = Image.fromarray(rgb_data.astype(np.uint8))
        img.save(img_path)
    
    # Process bboxes
    annotations = []
    if bbox_data is not None:
        try:
            data = bbox_data["data"]
            id_to_labels = bbox_data["info"]["idToLabels"]
            
            for sem_id_str, labels in id_to_labels.items():
                sem_id = int(sem_id_str)
                class_name = labels.get("class", "unknown")
                
                if class_name != "sturgeon":
                    continue
                
                class_id = 0  # sturgeon = 0
                
                # Filter bbox data for this semantic ID
                mask = data["semanticId"] == sem_id
                for i in range(len(data)):
                    if data["semanticId"][i] != sem_id:
                        continue
                    
                    x_min = float(data["x_min"][i])
                    y_min = float(data["y_min"][i])
                    x_max = float(data["x_max"][i])
                    y_max = float(data["y_max"][i])
                    
                    # Skip tiny boxes
                    if (x_max - x_min) < 10 or (y_max - y_min) < 10:
                        continue
                    
                    # Convert to YOLO format (normalized center x, y, w, h)
                    x_c = (x_min + x_max) / 2.0 / img_w
                    y_c = (y_min + y_max) / 2.0 / img_h
                    w = (x_max - x_min) / img_w
                    h = (y_max - y_min) / img_h
                    
                    # Clamp to [0, 1]
                    x_c = max(0.0, min(1.0, x_c))
                    y_c = max(0.0, min(1.0, y_c))
                    w = max(0.0, min(1.0, w))
                    h = max(0.0, min(1.0, h))
                    
                    annotations.append(f"{class_id} {x_c:.6f} {y_c:.6f} {w:.6f} {h:.6f}")
        except Exception as e:
            print(f"[collect] Bbox processing error: {e}")
    
    # Save label file
    with open(label_path, "w") as f:
        f.write("\n".join(annotations))
    
    return len(annotations)


def write_dataset_yaml(output_dir):
    """Write YOLO dataset.yaml configuration."""
    yaml_content = f"""# AquaSweep Fish Detection Dataset
# Auto-generated by collect_yolo_standalone.py

path: {output_dir}
train: images/train
val: images/val

names:
  0: sturgeon
"""
    with open(os.path.join(output_dir, "dataset.yaml"), "w") as f:
        f.write(yaml_content)


async def main_async():
    print("\n" + "="*60)
    print("  AquaSweep YOLO Dataset Collection (Replicator)")
    print("="*60)
    
    stage = omni.usd.get_context().get_stage()
    if not stage:
        print("ERROR: No stage loaded!")
        return
    
    # Create output directories
    print(f"\n[1/5] Creating output directories...")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    for split in ["train", "val"]:
        os.makedirs(os.path.join(OUTPUT_DIR, "images", split), exist_ok=True)
        os.makedirs(os.path.join(OUTPUT_DIR, "labels", split), exist_ok=True)
    print(f"  Output: {OUTPUT_DIR}")
    
    # Apply semantic labels to fish using Replicator API
    print("\n[2/5] Applying semantic labels to fish...")
    labeled = apply_labels(POOLS_TO_COLLECT)
    print(f"  Labeled pools: {labeled}/{len(POOLS_TO_COLLECT)}")
    
    # Create render products and annotators
    print("\n[3/5] Setting up cameras and annotators...")
    render_products = []
    annotators = {}  # pool_id -> {"rgb": annotator, "bbox": annotator}
    
    for pool_id in POOLS_TO_COLLECT:
        cam_path = f"/World/Pools/Pool_{pool_id}/TopCamera"
        if not stage.GetPrimAtPath(cam_path).IsValid():
            print(f"  Pool_{pool_id}: Camera not found, skipping")
            continue
        
        # Create render product
        rp = rep.create.render_product(cam_path, RESOLUTION)
        render_products.append(rp)
        
        # Create and attach annotators
        rgb_annot = rep.AnnotatorRegistry.get_annotator("rgb")
        bbox_annot = rep.AnnotatorRegistry.get_annotator(
            "bounding_box_2d_tight",
            init_params={"semanticTypes": ["class"]}
        )
        
        rgb_annot.attach([rp])
        bbox_annot.attach([rp])
        
        annotators[pool_id] = {"rgb": rgb_annot, "bbox": bbox_annot, "rp": rp}
        print(f"  Pool_{pool_id}: OK")
    
    if not annotators:
        print("ERROR: No cameras found!")
        return
    
    # Collect data
    print(f"\n[4/5] Collecting {NUM_FRAMES} frames...")
    print("  Progress updates every 20 frames. Please wait...")
    
    frame_id = 0
    total_objects = 0
    
    for i in range(NUM_FRAMES):
        # Step the orchestrator to render a new frame
        await rep.orchestrator.step_async()
        
        # Collect from all cameras
        for pool_id, annot_dict in annotators.items():
            rgb_annot = annot_dict["rgb"]
            bbox_annot = annot_dict["bbox"]
            
            # Get data
            rgb_data = rgb_annot.get_data()
            bbox_data = bbox_annot.get_data()
            
            if rgb_data is None:
                continue
            
            # Determine train/val split
            split = "val" if random.random() > TRAIN_VAL_SPLIT else "train"
            
            # Save
            img_h, img_w = RESOLUTION[1], RESOLUTION[0]
            num_obj = save_yolo_data(
                frame_id, rgb_data, bbox_data, 
                OUTPUT_DIR, split, img_w, img_h
            )
            total_objects += num_obj
            frame_id += 1
        
        # Progress
        if (i + 1) % 20 == 0:
            print(f"  Frame {i+1}/{NUM_FRAMES}, total images: {frame_id}, objects: {total_objects}")
    
    # Write dataset.yaml
    print("\n[5/5] Finalizing...")
    write_dataset_yaml(OUTPUT_DIR)
    
    # Cleanup annotators
    for pool_id, annot_dict in annotators.items():
        annot_dict["rgb"].detach()
        annot_dict["bbox"].detach()
    
    print("\n" + "="*60)
    print("  COLLECTION COMPLETE!")
    print("="*60)
    print(f"  Total frames: {frame_id}")
    print(f"  Total objects: {total_objects}")
    print(f"  Output: {OUTPUT_DIR}")
    print(f"\n  To train YOLO:")
    print(f"  yolo train data={OUTPUT_DIR}/dataset.yaml model=yolov8n.pt epochs=50")
    print("="*60 + "\n")


# Run
import asyncio
asyncio.ensure_future(main_async())
