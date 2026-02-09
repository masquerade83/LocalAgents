#!/usr/bin/env python3
"""
Split collected images into train/val/test sets
"""

import os
import shutil
import random
from pathlib import Path

# Configuration
SOURCE_DIR = 'dataset/images'  # Where collected images are
TRAIN_RATIO = 0.7  # 70% for training
VAL_RATIO = 0.2    # 20% for validation
TEST_RATIO = 0.1   # 10% for testing

def split_dataset():
    """Split images into train/val/test sets"""
    
    if not os.path.exists(SOURCE_DIR):
        print(f"❌ Source directory not found: {SOURCE_DIR}")
        print("Run collect_data.py first to collect images")
        return
    
    # Get all image files
    image_files = [f for f in os.listdir(SOURCE_DIR) 
                   if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
    
    if len(image_files) == 0:
        print(f"❌ No images found in {SOURCE_DIR}")
        return
    
    print("=" * 60)
    print("Splitting Dataset")
    print("=" * 60)
    print(f"Total images: {len(image_files)}")
    print(f"Train: {TRAIN_RATIO*100:.0f}%")
    print(f"Val: {VAL_RATIO*100:.0f}%")
    print(f"Test: {TEST_RATIO*100:.0f}%")
    print()
    
    # Shuffle images
    random.shuffle(image_files)
    
    # Calculate split sizes
    total = len(image_files)
    train_count = int(total * TRAIN_RATIO)
    val_count = int(total * VAL_RATIO)
    test_count = total - train_count - val_count
    
    # Split files
    train_files = image_files[:train_count]
    val_files = image_files[train_count:train_count + val_count]
    test_files = image_files[train_count + val_count:]
    
    # Copy files to respective directories
    splits = [
        ('train', train_files),
        ('val', val_files),
        ('test', test_files)
    ]
    
    for split_name, files in splits:
        dest_dir = f'dataset/{split_name}/images'
        os.makedirs(dest_dir, exist_ok=True)
        
        for filename in files:
            src = os.path.join(SOURCE_DIR, filename)
            dst = os.path.join(dest_dir, filename)
            shutil.copy2(src, dst)
        
        print(f"✅ {split_name.capitalize()}: {len(files)} images -> {dest_dir}")
    
    print("\n" + "=" * 60)
    print("✅ Dataset split complete!")
    print("\nNext steps:")
    print("1. Annotate images in dataset/train/images and dataset/val/images")
    print("2. Place annotation files (.txt) in dataset/train/labels and dataset/val/labels")
    print("3. Run train_custom_model.py to train your model")

if __name__ == '__main__':
    split_dataset()
