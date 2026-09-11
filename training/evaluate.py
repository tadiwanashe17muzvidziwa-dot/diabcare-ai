"""
Quick evaluation after training.
Usage: python training/evaluate.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'backend'))

from ultralytics import YOLO

model_path = Path(__file__).parent.parent / 'backend' / 'model' / 'best.pt'
dataset_dir = Path(__file__).parent.parent / 'data' / 'dataset'

if not model_path.exists():
    print(f"No trained model at {model_path}")
    sys.exit(1)

model = YOLO(str(model_path))
metrics = model.val(data=str(dataset_dir / 'val'))
print(f"Top-1 Accuracy: {metrics.top1:.4f}")
print(f"Top-5 Accuracy: {metrics.top5:.4f}")
