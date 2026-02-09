#!/bin/bash
# Remove large files/dirs from entire git history so push to GitHub succeeds.
# Run from repo root: bash scripts/strip_large_from_history.sh
set -e
export FILTER_BRANCH_SQUELCH_WARNING=1

git filter-branch --force --index-filter '
  git rm -rf --cached --ignore-unmatch \
    object_detection_working/training/runs \
    object_detection_working/training/dataset/images \
    object_detection_working/training/dataset/train \
    object_detection_working/training/dataset/test \
    object_detection_working/training/test/annotated \
    object_detection_working/training/test/captured_frames \
    object_detection_working/training/yolov8n.pt \
    object_detection_working/yolov8n.pt \
    object_detection_working/analytics/analytics.db \
    2>/dev/null || true
' --prune-empty HEAD

echo "Done. Next: rm -rf .git/refs/original && git reflog expire --expire=now --all && git gc --prune=now --aggressive"
echo "Then: git push -f origin master"
