#!/bin/bash
# Setup Label Studio for YOLO annotation

echo "Setting up Label Studio for YOLO labeling..."
echo ""

# Create a separate venv for Label Studio
python3 -m venv .labelstudio_env
source .labelstudio_env/bin/activate

# Install Label Studio
pip install label-studio

echo ""
echo "✅ Label Studio installed!"
echo ""
echo "To start Label Studio:"
echo "  1. Activate the environment: source .labelstudio_env/bin/activate"
echo "  2. Run: label-studio"
echo "  3. Open http://localhost:8080 in your browser"
echo ""
echo "Then:"
echo "  - Create a new project"
echo "  - Import images from: dataset/train/images and dataset/val/images"
echo "  - Annotate with bounding boxes"
echo "  - Export as YOLO format"
echo "  - Copy labels to dataset/train/labels and dataset/val/labels"
