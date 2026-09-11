"""
DiabCare AI - YOLOv8 Classification Training
Trains a 2-class model (Normal vs Ulcer) for diabetic foot screening.

USAGE:
  python training/train.py
  python training/train.py --epochs 50 --imgsz 224
"""
import os
import sys
import argparse
from pathlib import Path

# Add backend to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'backend'))


def train(args):
    from ultralytics import YOLO

    dataset_dir = Path(__file__).parent.parent / 'data' / 'dataset'
    if not dataset_dir.exists():
        print(f"[ERROR] Dataset not found at {dataset_dir}")
        print("  Run: python training/download_dataset.py first")
        sys.exit(1)

    # Verify dataset structure
    for split in ['train', 'val']:
        for cls in ['normal', 'ulcer']:
            d = dataset_dir / split / cls
            if not d.exists():
                print(f"[ERROR] Missing: {d}")
                sys.exit(1)

    print("=" * 60)
    print("DiabCare AI - YOLOv8 Classification Training")
    print("=" * 60)
    print(f"  Dataset:  {dataset_dir}")
    print(f"  Model:    YOLOv8n-cls (nano)")
    print(f"  Epochs:   {args.epochs}")
    print(f"  ImgSize:  {args.imgsz}")
    print(f"  Device:   {'CUDA' if args.device != 'cpu' else 'CPU'}")
    print()

    # Train
    model = YOLO('yolov8n-cls.pt')  # pretrained nano classifier
    results = model.train(
        data=str(dataset_dir),
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        device=args.device,
        patience=args.patience,
        project=str(Path(__file__).parent.parent / 'training' / 'runs'),
        name='diabcare_cls',
        exist_ok=True,
        pretrained=True,
        optimizer='auto',
        verbose=True,
        seed=42,
    )

    # Copy best model to backend
    best_pt = Path(results.save_dir) / 'weights' / 'best.pt'
    dest = Path(__file__).parent.parent / 'backend' / 'model' / 'best.pt'
    dest.parent.mkdir(parents=True, exist_ok=True)

    if best_pt.exists():
        import shutil
        shutil.copy2(str(best_pt), str(dest))
        print(f"\n[EXPORTED] best.pt -> {dest}")
        print("  Your app will now use the trained model instead of demo mode!")
    else:
        print(f"\n[ERROR] best.pt not found at {best_pt}")

    # Print final metrics
    print("\n" + "=" * 60)
    print("Training Complete!")
    print(f"  Results:  {results.save_dir}")
    print(f"  Model:    {dest}")
    print("=" * 60)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Train DiabCare AI classifier')
    parser.add_argument('--epochs', type=int, default=30, help='Number of epochs (default: 30)')
    parser.add_argument('--imgsz', type=int, default=224, help='Image size (default: 224)')
    parser.add_argument('--batch', type=int, default=16, help='Batch size (default: 16)')
    parser.add_argument('--device', type=str, default='0', help='Device: 0 for GPU, cpu for CPU')
    parser.add_argument('--patience', type=int, default=10, help='Early stopping patience')
    args = parser.parse_args()
    train(args)
