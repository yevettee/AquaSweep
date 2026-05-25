#!/usr/bin/env python3
"""
Preview YOLO annotations on images.

Usage:
    python preview_yolo_annotations.py [dataset_dir] [--num N] [--save]

Examples:
    # Preview 5 random images (default)
    python preview_yolo_annotations.py
    
    # Preview 10 images from specific dataset
    python preview_yolo_annotations.py /path/to/dataset --num 10
    
    # Save previews to file instead of displaying
    python preview_yolo_annotations.py --save
"""

import os
import sys
import random
import argparse
import cv2
import numpy as np
from pathlib import Path


# Default dataset directory
DEFAULT_DATASET = "/home/woody/AquaSweep/water_ws/src/aqua_detection/dataset_replicator"

# Class names (must match dataset.yaml)
CLASS_NAMES = {0: "sturgeon"}

# Colors for bounding boxes (BGR)
COLORS = [(0, 255, 0), (255, 0, 0), (0, 0, 255), (255, 255, 0), (0, 255, 255)]


def load_yolo_labels(label_path: str, img_w: int, img_h: int) -> list:
    """Load YOLO format labels and convert to pixel coordinates."""
    boxes = []
    
    if not os.path.exists(label_path):
        return boxes
    
    with open(label_path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            
            parts = line.split()
            if len(parts) < 5:
                continue
            
            class_id = int(parts[0])
            x_center = float(parts[1])
            y_center = float(parts[2])
            width = float(parts[3])
            height = float(parts[4])
            
            # Convert normalized coords to pixel coords
            x1 = int((x_center - width / 2) * img_w)
            y1 = int((y_center - height / 2) * img_h)
            x2 = int((x_center + width / 2) * img_w)
            y2 = int((y_center + height / 2) * img_h)
            
            boxes.append({
                "class_id": class_id,
                "class_name": CLASS_NAMES.get(class_id, f"class_{class_id}"),
                "bbox": (x1, y1, x2, y2),
                "center": (int(x_center * img_w), int(y_center * img_h))
            })
    
    return boxes


def draw_annotations(img: np.ndarray, boxes: list) -> np.ndarray:
    """Draw bounding boxes and labels on image."""
    img_draw = img.copy()
    
    for box in boxes:
        x1, y1, x2, y2 = box["bbox"]
        class_name = box["class_name"]
        color = COLORS[box["class_id"] % len(COLORS)]
        
        # Draw rectangle
        cv2.rectangle(img_draw, (x1, y1), (x2, y2), color, 2)
        
        # Draw label background
        label = f"{class_name}"
        (label_w, label_h), baseline = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
        cv2.rectangle(img_draw, (x1, y1 - label_h - 10), (x1 + label_w + 5, y1), color, -1)
        
        # Draw label text
        cv2.putText(img_draw, label, (x1 + 2, y1 - 5), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        # Draw center point
        cv2.circle(img_draw, box["center"], 4, (0, 0, 255), -1)
    
    return img_draw


def get_image_label_pairs(dataset_dir: str) -> list:
    """Get all image-label pairs from dataset."""
    pairs = []
    
    images_dir = os.path.join(dataset_dir, "images")
    labels_dir = os.path.join(dataset_dir, "labels")
    
    for split in ["train", "val"]:
        img_split_dir = os.path.join(images_dir, split)
        label_split_dir = os.path.join(labels_dir, split)
        
        if not os.path.exists(img_split_dir):
            continue
        
        for img_file in os.listdir(img_split_dir):
            if not img_file.lower().endswith(('.png', '.jpg', '.jpeg')):
                continue
            
            img_path = os.path.join(img_split_dir, img_file)
            label_file = os.path.splitext(img_file)[0] + ".txt"
            label_path = os.path.join(label_split_dir, label_file)
            
            pairs.append({
                "image": img_path,
                "label": label_path,
                "split": split,
                "name": img_file
            })
    
    return pairs


def preview_annotations(dataset_dir: str, num_samples: int = 5, save_dir: str = None):
    """Preview random annotations from dataset."""
    print(f"\n{'='*60}")
    print(f"  YOLO Annotation Preview")
    print(f"{'='*60}")
    print(f"Dataset: {dataset_dir}")
    
    # Get all pairs
    pairs = get_image_label_pairs(dataset_dir)
    
    if not pairs:
        print("ERROR: No images found in dataset!")
        return
    
    print(f"Total images: {len(pairs)}")
    
    # Sample random images
    num_samples = min(num_samples, len(pairs))
    samples = random.sample(pairs, num_samples)
    
    print(f"Previewing {num_samples} random images...")
    print(f"{'='*60}\n")
    
    if save_dir:
        os.makedirs(save_dir, exist_ok=True)
    
    for i, sample in enumerate(samples):
        img_path = sample["image"]
        label_path = sample["label"]
        
        # Load image
        img = cv2.imread(img_path)
        if img is None:
            print(f"[{i+1}] Failed to load: {img_path}")
            continue
        
        img_h, img_w = img.shape[:2]
        
        # Load labels
        boxes = load_yolo_labels(label_path, img_w, img_h)
        
        # Draw annotations
        img_annotated = draw_annotations(img, boxes)
        
        # Add info text
        info = f"{sample['name']} ({sample['split']}) - {len(boxes)} objects"
        cv2.putText(img_annotated, info, (10, 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
        
        print(f"[{i+1}/{num_samples}] {sample['name']}: {len(boxes)} objects")
        
        if save_dir:
            # Save to file
            save_path = os.path.join(save_dir, f"preview_{i+1:02d}.jpg")
            cv2.imwrite(save_path, img_annotated)
            print(f"    Saved: {save_path}")
        else:
            # Display
            cv2.imshow(f"Preview {i+1}/{num_samples} - Press any key", img_annotated)
            key = cv2.waitKey(0)
            if key == ord('q') or key == 27:  # q or ESC
                print("Exiting...")
                break
    
    if not save_dir:
        cv2.destroyAllWindows()
    
    print(f"\n{'='*60}")
    print("  Preview complete!")
    print(f"{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(description="Preview YOLO annotations")
    parser.add_argument("dataset_dir", nargs="?", default=DEFAULT_DATASET,
                        help="Path to YOLO dataset directory")
    parser.add_argument("--num", "-n", type=int, default=5,
                        help="Number of images to preview (default: 5)")
    parser.add_argument("--save", "-s", action="store_true",
                        help="Save previews instead of displaying")
    parser.add_argument("--output", "-o", type=str, default="/tmp/yolo_preview",
                        help="Output directory for saved previews")
    
    args = parser.parse_args()
    
    save_dir = args.output if args.save else None
    preview_annotations(args.dataset_dir, args.num, save_dir)


if __name__ == "__main__":
    main()
