# Custom YOLO Model Training Guide

Train a custom YOLO model to detect specific objects from your RTSP video stream.

## Overview

This training pipeline allows you to:
1. **Collect frames** from your RTSP stream
2. **Annotate objects** in the frames
3. **Train a custom YOLO model** on your data
4. **Use the trained model** in the RTSP viewer

## Step-by-Step Process

### Step 1: Setup Dataset Structure

```bash
cd training
python3 setup_dataset.py
```

This creates the required directory structure:
```
dataset/
├── train/
│   ├── images/
│   └── labels/
├── val/
│   ├── images/
│   └── labels/
└── test/
    ├── images/
    └── labels/
```

### Step 2: Collect Training Data

Capture frames from your RTSP stream:

```bash
python3 collect_data.py
```

**Configuration** (edit `collect_data.py`):
- `RTSP_URL` - Your RTSP stream URL
- `FRAME_INTERVAL` - Seconds between captures (default: 2)
- `MAX_FRAMES` - Maximum frames to collect (default: 1000)

Frames will be saved to `dataset/images/`

### Step 3: Split Dataset

Split collected images into train/val/test sets:

```bash
python3 split_dataset.py
```

This automatically splits your images:
- 70% training
- 20% validation
- 10% testing

### Step 4: Annotate Images

You need to annotate (label) objects in your images. Use **LabelImg**:

#### Install LabelImg:
```bash
pip install labelimg
```

Or download from: https://github.com/HumanSignal/labelImg

#### Annotate:
1. Open LabelImg
2. Open directory: `dataset/train/images`
3. Change save directory to: `dataset/train/labels`
4. Select "YOLO" format (not PascalVOC)
5. Draw bounding boxes around objects you want to detect
6. Label each object with a class name
7. Save annotations (creates .txt files)

**Repeat for validation set:**
- Open: `dataset/val/images`
- Save to: `dataset/val/labels`

#### Annotation Format:
YOLO uses normalized coordinates (0-1):
```
class_id center_x center_y width height
```

Example:
```
0 0.5 0.5 0.3 0.4
```
- Class 0, centered at (0.5, 0.5), width 30%, height 40%

### Step 5: Configure Classes

Edit `train_custom_model.py` and update the class list:

```python
classes = ['person', 'car', 'bicycle']  # Your object classes
```

Also update `dataset/dataset.yaml` after first run, or it will be auto-created.

### Step 6: Train Model

Start training:

```bash
python3 train_custom_model.py
```

**Configuration** (edit `train_custom_model.py`):
- `MODEL_SIZE` - 'n' (nano), 's' (small), 'm' (medium), 'l' (large), 'x' (xlarge)
- `EPOCHS` - Number of training epochs (default: 100)
- `IMG_SIZE` - Image size for training (default: 640)
- `BATCH_SIZE` - Batch size (default: 16, adjust based on GPU memory)

### Step 7: Use Trained Model

After training, update `server_yolo.py`:

```python
# Change line ~39 from:
yolo_model = YOLO('yolov8n.pt')

# To:
yolo_model = YOLO('runs/detect/custom_yolo/weights/best.pt')
```

Or use the last checkpoint:
```python
yolo_model = YOLO('runs/detect/custom_yolo/weights/last.pt')
```

## Training Tips

### Data Collection
- **Diversity**: Capture frames in different lighting, angles, backgrounds
- **Quality**: Ensure objects are clearly visible
- **Quantity**: Minimum 100-200 images per class recommended
- **Balance**: Try to have similar number of images per class

### Annotation
- **Accuracy**: Draw tight bounding boxes around objects
- **Consistency**: Label same objects with same class names
- **Coverage**: Annotate all instances of objects in each image
- **Quality**: Double-check annotations before training

### Training
- **Start small**: Use YOLOv8n (nano) for faster training
- **Monitor**: Watch training loss - should decrease over time
- **Early stopping**: Stop if validation loss stops improving
- **GPU**: Training is much faster with GPU (CUDA)

### Model Selection
- **YOLOv8n**: Fastest, good for real-time, less accurate
- **YOLOv8s**: Balanced speed/accuracy
- **YOLOv8m/l/x**: Better accuracy, slower inference

## Expected Training Time

- **CPU**: ~2-4 hours for 100 epochs (YOLOv8n, 100 images)
- **GPU**: ~30-60 minutes for 100 epochs (YOLOv8n, 100 images)

## Troubleshooting

### "No training images found"
- Make sure images are in `dataset/train/images/`
- Check file extensions (.jpg, .png)

### "No labels found"
- Ensure annotation files (.txt) are in `dataset/train/labels/`
- Check that annotation filenames match image filenames

### Training loss not decreasing
- Check annotations are correct
- Ensure enough training data
- Try different learning rate
- Verify dataset.yaml has correct class count

### Out of memory errors
- Reduce `BATCH_SIZE` in train_custom_model.py
- Reduce `IMG_SIZE` (try 416 instead of 640)
- Use smaller model (YOLOv8n instead of YOLOv8s)

## File Structure After Training

```
training/
├── dataset/
│   ├── train/
│   │   ├── images/
│   │   └── labels/
│   ├── val/
│   │   ├── images/
│   │   └── labels/
│   └── dataset.yaml
├── runs/
│   └── detect/
│       └── custom_yolo/
│           ├── weights/
│           │   ├── best.pt  ← Use this!
│           │   └── last.pt
│           ├── results.png
│           └── ...
└── ...
```

## Quick Start Commands

```bash
# 1. Setup
python3 setup_dataset.py

# 2. Collect data
python3 collect_data.py

# 3. Split dataset
python3 split_dataset.py

# 4. Annotate (use LabelImg)
labelimg

# 5. Train
python3 train_custom_model.py

# 6. Update server to use trained model
# Edit server_yolo.py line 39
```

## Next Steps

After training:
1. Test the model on validation images
2. Evaluate performance metrics
3. Fine-tune if needed (more epochs, different model size)
4. Deploy to production (update server_yolo.py)
