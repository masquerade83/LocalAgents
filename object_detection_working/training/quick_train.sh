#!/bin/bash
# Quick training workflow script

echo "Custom YOLO Training Workflow"
echo "=============================="
echo ""

# Step 1: Setup
echo "Step 1: Setting up dataset structure..."
python3 setup_dataset.py
echo ""

# Step 2: Collect data (optional - skip if you already have images)
read -p "Collect frames from RTSP stream? (y/n): " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Step 2: Collecting frames..."
    echo "Press Ctrl+C when you have enough frames"
    python3 collect_data.py
    echo ""
    
    # Step 3: Split dataset
    echo "Step 3: Splitting dataset..."
    python3 split_dataset.py
    echo ""
else
    echo "Skipping data collection (assuming images already exist)"
    echo ""
fi

# Step 4: Annotation reminder
echo "Step 4: ANNOTATE YOUR IMAGES"
echo "=============================="
echo "1. Install LabelImg: pip install labelimg"
echo "2. Open LabelImg"
echo "3. Open: dataset/train/images"
echo "4. Save to: dataset/train/labels"
echo "5. Select YOLO format"
echo "6. Draw bounding boxes and label objects"
echo "7. Repeat for dataset/val/images -> dataset/val/labels"
echo ""
read -p "Press Enter when annotation is complete..."

# Step 5: Train
echo ""
echo "Step 5: Training model..."
echo "=============================="
python3 train_custom_model.py

echo ""
echo "✅ Training workflow complete!"
echo ""
echo "To use your trained model:"
echo "  Update server_yolo.py to load: runs/detect/custom_yolo/weights/best.pt"
