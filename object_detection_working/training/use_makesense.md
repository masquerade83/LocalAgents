# Using makesense.ai for Labeling (Easiest Option!)

## Steps:

1. **Go to:** https://www.makesense.ai/

2. **Upload images:**
   - Click "Get Started"
   - Upload all images from `dataset/train/images`
   - Click "Object Detection"

3. **Create labels:**
   - Click "Add labels" and add your class names (e.g., "person", "bottle", etc.)
   - Draw bounding boxes around objects
   - Assign labels to each box

4. **Export:**
   - Click "Actions" → "Export Annotations"
   - Choose **"YOLO"** format
   - Download the zip file

5. **Extract labels:**
   ```bash
   cd /Users/shailja/clawd/object_detection_working/training
   unzip ~/Downloads/annotations.zip -d temp_labels
   # Move .txt files to the right place
   cp temp_labels/*.txt dataset/train/labels/
   ```

6. **Repeat for validation set:**
   - Upload `dataset/val/images` to makesense.ai
   - Annotate and export
   - Copy labels to `dataset/val/labels`

## Advantages:
- ✅ No installation needed
- ✅ Works in any browser
- ✅ Free
- ✅ Exports YOLO format directly
- ✅ Simple interface
