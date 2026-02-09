#!/usr/bin/env python3
"""
Train custom YOLO model on annotated dataset
"""

from ultralytics import YOLO
import os
import yaml

# Configuration
DATASET_DIR = 'dataset'
MODEL_SIZE = 'n'  # n, s, m, l, x (nano, small, medium, large, xlarge)
EPOCHS = 100
IMG_SIZE = 640
BATCH_SIZE = 16
PRETRAINED_MODEL = f'yolov8{MODEL_SIZE}.pt'

def create_dataset_yaml(dataset_dir):
    """Create dataset.yaml file for YOLO training"""
    
    # YOLO expects this structure:
    # dataset/
    #   train/
    #     images/
    #     labels/
    #   val/
    #     images/
    #     labels/
    
    yaml_path = os.path.join(dataset_dir, 'dataset.yaml')
    
    # From Roboflow YOLO export data.yaml (exact order = class ID 0-9)
    classes = ['ac', 'artwork', 'book', 'bottle', 'box', 'cup', 'curtain', 'fan', 'lamp', 'person']
    
    yaml_content = {
        'path': os.path.abspath(dataset_dir),
        'train': 'train/images',
        'val': 'val/images',
        'test': 'test/images',  # optional
        'nc': len(classes),
        'names': classes
    }
    
    with open(yaml_path, 'w') as f:
        import yaml as yaml_lib
        yaml_lib.dump(yaml_content, f, default_flow_style=False)
    
    print(f"✅ Created dataset.yaml at: {yaml_path}")
    return yaml_path

def train_model():
    """Train YOLO model on custom dataset"""
    
    print("=" * 60)
    print("Custom YOLO Model Training")
    print("=" * 60)
    
    # Check dataset structure
    dataset_path = os.path.join(DATASET_DIR, 'dataset.yaml')
    if not os.path.exists(dataset_path):
        print(f"Creating dataset.yaml...")
        dataset_path = create_dataset_yaml(DATASET_DIR)
    
    # Verify dataset structure
    train_images = os.path.join(DATASET_DIR, 'train', 'images')
    train_labels = os.path.join(DATASET_DIR, 'train', 'labels')
    val_images = os.path.join(DATASET_DIR, 'val', 'images')
    val_labels = os.path.join(DATASET_DIR, 'val', 'labels')
    
    required_dirs = [train_images, train_labels, val_images, val_labels]
    missing = [d for d in required_dirs if not os.path.exists(d)]
    
    if missing:
        print("\n❌ Missing required directories:")
        for d in missing:
            print(f"   - {d}")
        print("\nDataset structure should be:")
        print("  dataset/")
        print("    train/")
        print("      images/")
        print("      labels/")
        print("    val/")
        print("      images/")
        print("      labels/")
        print("\nRun collect_data.py and annotate images first!")
        return
    
    # Count images
    train_count = len([f for f in os.listdir(train_images) if f.endswith(('.jpg', '.png'))])
    val_count = len([f for f in os.listdir(val_images) if f.endswith(('.jpg', '.png'))])
    
    print(f"\nDataset info:")
    print(f"  Training images: {train_count}")
    print(f"  Validation images: {val_count}")
    print(f"  Model: YOLOv8{MODEL_SIZE}")
    print(f"  Epochs: {EPOCHS}")
    print(f"  Image size: {IMG_SIZE}")
    print(f"  Batch size: {BATCH_SIZE}")
    print()
    
    if train_count == 0:
        print("❌ No training images found!")
        return
    
    # Load pretrained model
    print(f"Loading pretrained model: {PRETRAINED_MODEL}")
    model = YOLO(PRETRAINED_MODEL)
    
    # Train the model
    print("\n🚀 Starting training...")
    print("=" * 60)
    
    results = model.train(
        data=dataset_path,
        epochs=EPOCHS,
        imgsz=IMG_SIZE,
        batch=BATCH_SIZE,
        name='custom_yolo',
        project='runs/detect',
        save=True,
        save_period=10,  # Save checkpoint every 10 epochs
        val=True,  # Validate during training
        plots=True,  # Generate training plots
    )
    
    print("\n" + "=" * 60)
    print("✅ Training complete!")
    print("=" * 60)
    print(f"\nBest model saved to: runs/detect/custom_yolo/weights/best.pt")
    print(f"Last model saved to: runs/detect/custom_yolo/weights/last.pt")
    print("\nTo use the trained model:")
    print("  Update server_yolo.py to load: 'runs/detect/custom_yolo/weights/best.pt'")

if __name__ == '__main__':
    train_model()
