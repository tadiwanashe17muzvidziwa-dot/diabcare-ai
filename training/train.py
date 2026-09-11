"""
DiabCare AI - YOLOv8 Classification Training
Trains a 2-class model (Normal vs Ulcer) for diabetic foot screening.

USAGE:
  python training/train.py
  python training/train.py --epochs 100 --imgsz 320
"""
import os
import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'backend'))


def train(args):
    from ultralytics import YOLO

    dataset_dir = Path(__file__).parent.parent / 'data' / 'dataset'
    if not dataset_dir.exists():
        print(f"[ERROR] Dataset not found at {dataset_dir}")
        print("  Run: python training/download_dataset.py first")
        sys.exit(1)

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
    print(f"  Model:    YOLOv8s-cls (small - better accuracy)")
    print(f"  Epochs:   {args.epochs}")
    print(f"  ImgSize:  {args.imgsz}")
    print(f"  Device:   {'CUDA' if args.device != 'cpu' else 'CPU'}")
    print()

    model = YOLO('yolov8s-cls.pt')
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
        optimizer='AdamW',
        lr0=0.001,
        lrf=0.01,
        momentum=0.937,
        weight_decay=0.0005,
        warmup_epochs=3,
        warmup_momentum=0.8,
        warmup_bias_lr=0.1,
        cos_lr=True,
        verbose=True,
        seed=42,
    )

    best_pt = Path(results.save_dir) / 'weights' / 'best.pt'
    dest = Path(__file__).parent.parent / 'backend' / 'model' / 'best.pt'
    dest.parent.mkdir(parents=True, exist_ok=True)

    if best_pt.exists():
        import shutil
        shutil.copy2(str(best_pt), str(dest))
        print(f"\n[EXPORTED] best.pt -> {dest}")
        print("  Your app will now use the trained model!")
    else:
        print(f"\n[ERROR] best.pt not found at {best_pt}")

    print("\n" + "=" * 60)
    print("Training Complete!")
    print(f"  Results:  {results.save_dir}")
    print(f"  Model:    {dest}")
    print("=" * 60)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Train DiabCare AI classifier')
    parser.add_argument('--epochs', type=int, default=100, help='Number of epochs')
    parser.add_argument('--imgsz', type=int, default=320, help='Image size')
    parser.add_argument('--batch', type=int, default=16, help='Batch size')
    parser.add_argument('--device', type=str, default='0', help='Device: 0 for GPU, cpu for CPU')
    parser.add_argument('--patience', type=int, default=20, help='Early stopping patience')
    args = parser.parse_args()
    train(args)
