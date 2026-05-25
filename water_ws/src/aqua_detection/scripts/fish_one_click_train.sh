#!/bin/bash
# Fish Detection YOLO Training - One Click Script
# 
# This script automates the entire training pipeline:
# 1. Collect dataset from Isaac Sim (GT + images)
# 2. Train YOLOv8 model on fish species classification
# 3. Deploy trained model to aqua_detection package
#
# Usage:
#   ./fish_one_click_train.sh [duration_seconds]
#
# Example:
#   ./fish_one_click_train.sh 300  # Collect 5 minutes of data

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PACKAGE_DIR="$(dirname "$SCRIPT_DIR")"
DATASET_DIR="${PACKAGE_DIR}/dataset"
MODELS_DIR="${PACKAGE_DIR}/models"
DURATION=${1:-300}  # Default 5 minutes

echo "=============================================="
echo "  AquaSweep Fish Detection Training Pipeline"
echo "=============================================="
echo ""
echo "Configuration:"
echo "  Duration: ${DURATION} seconds"
echo "  Dataset: ${DATASET_DIR}"
echo "  Models:  ${MODELS_DIR}"
echo ""

# Create directories
mkdir -p "${DATASET_DIR}"
mkdir -p "${MODELS_DIR}"

# Step 1: Collect dataset
echo "[1/3] Collecting dataset from Isaac Sim..."
echo "      Make sure Isaac Sim is running with top_cam_ext enabled."
echo ""

# Check if ROS2 is available
if command -v ros2 &> /dev/null; then
    echo "Running ROS2 dataset collector..."
    python3 "${SCRIPT_DIR}/fish_collect_dataset.py" \
        --output_dir "${DATASET_DIR}" \
        --duration "${DURATION}"
else
    echo "ROS2 not available. Creating empty dataset structure..."
    python3 "${SCRIPT_DIR}/fish_collect_dataset.py" \
        --output_dir "${DATASET_DIR}" \
        --duration 0
fi

# Check if dataset was created
if [ ! -f "${DATASET_DIR}/fish_species.yaml" ]; then
    echo "Error: Dataset config not created. Check Isaac Sim connection."
    exit 1
fi

echo ""
echo "[2/3] Training YOLOv8 model..."
echo ""

# Check if ultralytics is installed
if ! python3 -c "import ultralytics" 2>/dev/null; then
    echo "Installing ultralytics (YOLOv8)..."
    pip install ultralytics
fi

# Train YOLOv8
cd "${PACKAGE_DIR}"
python3 -c "
from ultralytics import YOLO

# Load pretrained model
model = YOLO('yolov8n.pt')

# Train on fish dataset
results = model.train(
    data='${DATASET_DIR}/fish_species.yaml',
    epochs=50,
    imgsz=640,
    batch=16,
    name='fish_species',
    project='${PACKAGE_DIR}/runs',
    exist_ok=True,
    patience=10,
    verbose=True,
)

print('Training complete!')
print(f'Best model: {results.save_dir}/weights/best.pt')
"

# Step 3: Deploy model
echo ""
echo "[3/3] Deploying trained model..."
echo ""

# Find and copy best model
BEST_MODEL=$(find "${PACKAGE_DIR}/runs" -name "best.pt" -type f | sort -r | head -1)

if [ -n "${BEST_MODEL}" ]; then
    cp "${BEST_MODEL}" "${MODELS_DIR}/yolov8_fish_species.pt"
    echo "Model deployed to: ${MODELS_DIR}/yolov8_fish_species.pt"
else
    echo "Warning: Could not find trained model."
fi

echo ""
echo "=============================================="
echo "  Training Pipeline Complete!"
echo "=============================================="
echo ""
echo "Next steps:"
echo "  1. Test the model:"
echo "     ros2 run aqua_detection fish_detection_node --ros-args -p detector_type:=yolo"
echo ""
echo "  2. Compare with SAM2 zero-shot:"
echo "     ros2 run aqua_detection fish_detection_node --ros-args -p detector_type:=sam2"
echo ""
