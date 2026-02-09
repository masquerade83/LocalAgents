#!/usr/bin/env python3
"""
Helper script to prepare images for web-based labeling tools
and to organize downloaded labels back into the dataset structure
"""

import os
import shutil
import zipfile
from pathlib import Path

DATASET_DIR = 'dataset'

def prepare_for_labeling():
    """Create zip files of images for easy upload to web tools"""
    
    print("=" * 60)
    print("Preparing images for web-based labeling")
    print("=" * 60)
    
    train_images = Path(DATASET_DIR) / 'train' / 'images'
    val_images = Path(DATASET_DIR) / 'val' / 'images'
    
    # Create zip files
    if train_images.exists():
        train_zip = 'train_images_for_labeling.zip'
        print(f"\n📦 Creating {train_zip}...")
        imgs = list(train_images.glob('*.jpg')) + list(train_images.glob('*.jpeg')) + list(train_images.glob('*.png'))
        with zipfile.ZipFile(train_zip, 'w') as zf:
            for img in imgs:
                zf.write(img, img.name)
        print(f"   ✅ Created {train_zip} ({len(imgs)} images)")
        print(f"   Upload this to makesense.ai or Roboflow")
    
    if val_images.exists():
        val_zip = 'val_images_for_labeling.zip'
        print(f"\n📦 Creating {val_zip}...")
        imgs = list(val_images.glob('*.jpg')) + list(val_images.glob('*.jpeg')) + list(val_images.glob('*.png'))
        with zipfile.ZipFile(val_zip, 'w') as zf:
            for img in imgs:
                zf.write(img, img.name)
        print(f"   ✅ Created {val_zip} ({len(imgs)} images)")
        print(f"   Upload this to makesense.ai or Roboflow")
    
    print("\n" + "=" * 60)
    print("Next steps:")
    print("  1. Go to https://www.makesense.ai/")
    print("  2. Upload train_images_for_labeling.zip")
    print("  3. Annotate and export as YOLO format")
    print("  4. Use organize_labels() function to place labels correctly")
    print("=" * 60)

def organize_labels(downloaded_zip_path, split='train'):
    """
    Organize downloaded YOLO labels into the correct dataset structure
    
    Args:
        downloaded_zip_path: Path to the zip file downloaded from labeling tool
        split: 'train' or 'val'
    """
    
    labels_dir = Path(DATASET_DIR) / split / 'labels'
    labels_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\n📁 Organizing labels for {split} set...")
    
    # Extract zip
    temp_dir = Path('temp_labels')
    with zipfile.ZipFile(downloaded_zip_path, 'r') as zf:
        zf.extractall(temp_dir)
    
    # Find all .txt files
    txt_files = list(temp_dir.rglob('*.txt'))
    
    if not txt_files:
        print(f"   ⚠️  No .txt files found in {downloaded_zip_path}")
        print(f"   Make sure you exported as YOLO format")
        return
    
    # Copy to labels directory
    copied = 0
    for txt_file in txt_files:
        # Get just the filename
        filename = txt_file.name
        dest = labels_dir / filename
        
        shutil.copy2(txt_file, dest)
        copied += 1
    
    # Cleanup
    shutil.rmtree(temp_dir)
    
    print(f"   ✅ Copied {copied} label files to {labels_dir}")
    print(f"   Labels are now ready for training!")

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1:
        # Organize labels from downloaded zip
        zip_path = sys.argv[1]
        split = sys.argv[2] if len(sys.argv) > 2 else 'train'
        organize_labels(zip_path, split)
    else:
        # Prepare images for labeling
        prepare_for_labeling()
