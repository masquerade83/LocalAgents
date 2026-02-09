#!/usr/bin/env python3
"""
Update server_yolo.py to use custom trained model
"""

import os
import re

def update_server_model(model_path):
    """Update server_yolo.py to use custom model"""
    
    server_file = '../server_yolo.py'
    
    if not os.path.exists(server_file):
        print(f"❌ Server file not found: {server_file}")
        return False
    
    # Read current file
    with open(server_file, 'r') as f:
        content = f.read()
    
    # Find and replace model path
    pattern = r"yolo_model = YOLO\('([^']+)'\)"
    replacement = f"yolo_model = YOLO('{model_path}')"
    
    if re.search(pattern, content):
        new_content = re.sub(pattern, replacement, content)
        
        # Write updated file
        with open(server_file, 'w') as f:
            f.write(new_content)
        
        print(f"✅ Updated server_yolo.py")
        print(f"   Model path: {model_path}")
        return True
    else:
        print("❌ Could not find model loading line in server_yolo.py")
        return False

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1:
        model_path = sys.argv[1]
    else:
        # Default to best model
        model_path = 'runs/detect/custom_yolo/weights/best.pt'
    
    # Check if model exists
    if not os.path.exists(model_path):
        print(f"⚠️  Warning: Model file not found: {model_path}")
        print("Make sure you've trained the model first!")
        response = input("Continue anyway? (y/n): ")
        if response.lower() != 'y':
            exit(1)
    
    update_server_model(model_path)
