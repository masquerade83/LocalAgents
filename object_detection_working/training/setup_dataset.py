#!/usr/bin/env python3
"""
Setup dataset directory structure for YOLO training
"""

import os
import shutil
from pathlib import Path

def setup_dataset_structure(base_dir='dataset'):
    """Create YOLO dataset directory structure"""
    
    directories = [
        f'{base_dir}/train/images',
        f'{base_dir}/train/labels',
        f'{base_dir}/val/images',
        f'{base_dir}/val/labels',
        f'{base_dir}/test/images',  # optional
        f'{base_dir}/test/labels',  # optional
    ]
    
    print("Setting up dataset structure...")
    print("=" * 60)
    
    for dir_path in directories:
        os.makedirs(dir_path, exist_ok=True)
        print(f"✅ Created: {dir_path}")
    
    print("\n" + "=" * 60)
    print("✅ Dataset structure ready!")
    print("\nNext steps:")
    print("1. Run collect_data.py to capture frames from RTSP stream")
    print("2. Annotate images using LabelImg or similar tool")
    print("3. Split dataset into train/val (use split_dataset.py)")
    print("4. Run train_custom_model.py to train your model")

if __name__ == '__main__':
    setup_dataset_structure()
