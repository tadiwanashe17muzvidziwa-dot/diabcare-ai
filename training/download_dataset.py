"""
DiabCare AI - Dataset Setup
Downloads the Kaggle DFU dataset and organizes it for YOLOv8 classification.

PREREQUISITES:
  1. Create a Kaggle account at kaggle.com
  2. Go to kaggle.com/settings -> API -> Create New Token (downloads kaggle.json)
  3. Place kaggle.json in: ~/.kaggle/kaggle.json
     (or run: pip install kaggle && kaggle config path)
  4. pip install kaggle

USAGE:
  python training/download_dataset.py
"""
import os
import sys
import shutil
import zipfile
import random
from pathlib import Path

# Config
DATASET_SLUG = "laithjj/diabetic-foot-ulcer-dfu"
RAW_DIR = Path(__file__).parent.parent / "data" / "dataset_raw"
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "dataset"
VAL_SPLIT = 0.15
TEST_SPLIT = 0.10
SEED = 42


def check_kaggle():
    try:
        import kaggle
        from kaggle.rest import KaggleApi
        api = KaggleApi()
        api.authenticate()
        print("[OK] Kaggle authenticated")
        return api
    except Exception as e:
        print(f"[ERROR] Kaggle not set up: {e}")
        print("\nTo fix:")
        print("  1. pip install kaggle")
        print("  2. Go to kaggle.com/settings -> API -> Create New Token")
        print("  3. Place kaggle.json in ~/.kaggle/kaggle.json")
        sys.exit(1)


def download_dataset(api):
    print(f"\n[DOWNLOAD] Fetching {DATASET_SLUG} ...")
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    api.dataset_download_files(
        dataset=DATASET_SLUG,
        path=str(RAW_DIR),
        force=True,
        quiet=False
    )

    # Extract zip files
    for zipf in RAW_DIR.glob("*.zip"):
        print(f"[EXTRACT] {zipf.name}")
        with zipfile.ZipFile(zipf, 'r') as z:
            z.extractall(str(RAW_DIR))
        zipf.unlink()

    print("[DONE] Downloaded to", RAW_DIR)


def find_images(directory):
    """Recursively find all image files."""
    exts = {'.jpg', '.jpeg', '.png', '.bmp', '.webp', '.tiff'}
    images = []
    for f in directory.rglob("*"):
        if f.suffix.lower() in exts and f.is_file():
            images.append(f)
    return images


def organize_dataset():
    """
    Organize raw images into YOLOv8 classification structure:
      dataset/
        train/
          normal/   (healthy feet)
          ulcer/    (diabetic foot ulcers)
        val/
          normal/
          ulcer/
        test/
          normal/
          ulcer/
    """
    print("\n[ORGANIZE] Structuring dataset for YOLOv8 classification...")

    # Find all images in raw download
    all_images = find_images(RAW_DIR)
    print(f"  Found {len(all_images)} images total")

    # Try to classify images by filename/folder hints
    normal_images = []
    ulcer_images = []

    for img in all_images:
        path_str = str(img).lower()
        # Common naming patterns in DFU datasets
        if any(kw in path_str for kw in ['ulcer', 'dfu', 'wound', 'lesion', 'abnormal',
                                           'positive', 'diabetic', 'foot_ulcer']):
            ulcer_images.append(img)
        elif any(kw in path_str for kw in ['normal', 'healthy', 'negative', 'control',
                                             'no_ulcer', 'clean', 'intact']):
            normal_images.append(img)
        else:
            # Check parent folder name
            parent = img.parent.name.lower()
            if any(kw in parent for kw in ['ulcer', 'dfu', 'wound', 'abnormal', 'positive']):
                ulcer_images.append(img)
            elif any(kw in parent for kw in ['normal', 'healthy', 'negative', 'control']):
                normal_images.append(img)
            else:
                # Default: treat as normal if can't determine
                normal_images.append(img)

    print(f"  Normal: {len(normal_images)}, Ulcer: {len(ulcer_images)}")

    if len(ulcer_images) == 0:
        print("\n[WARNING] Could not auto-detect ulcer images from filenames.")
        print("  The raw data may need manual sorting.")
        print(f"  Raw images are in: {RAW_DIR}")
        print("  Please manually move images into:")
        print(f"    {OUTPUT_DIR}/train/ulcer/")
        print(f"    {OUTPUT_DIR}/train/normal/")
        print("  Then re-run this script with --skip-download")
        return False

    if len(normal_images) == 0:
        print("\n[WARNING] No normal images found. Need both classes.")
        return False

    # Shuffle and split
    random.seed(SEED)
    random.shuffle(normal_images)
    random.shuffle(ulcer_images)

    def split_images(images):
        n = len(images)
        n_test = int(n * TEST_SPLIT)
        n_val = int(n * VAL_SPLIT)
        return {
            'test': images[:n_test],
            'val': images[n_test:n_test + n_val],
            'train': images[n_test + n_val:],
        }

    normal_split = split_images(normal_images)
    ulcer_split = split_images(ulcer_images)

    # Create output directories and copy files
    for split in ['train', 'val', 'test']:
        for cls in ['normal', 'ulcer']:
            dest = OUTPUT_DIR / split / cls
            dest.mkdir(parents=True, exist_ok=True)

            src_list = normal_split[split] if cls == 'normal' else ulcer_split[split]
            for i, src in enumerate(src_list):
                dst = dest / f"{cls}_{i:04d}{src.suffix}"
                shutil.copy2(str(src), str(dst))

    # Print summary
    print(f"\n[SUMMARY] Dataset organized at: {OUTPUT_DIR}")
    for split in ['train', 'val', 'test']:
        n_normal = len(list((OUTPUT_DIR / split / 'normal').glob('*')))
        n_ulcer = len(list((OUTPUT_DIR / split / 'ulcer').glob('*')))
        print(f"  {split:5s}: {n_normal} normal + {n_ulcer} ulcer = {n_normal + n_ulcer} total")

    return True


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Setup DiabCare AI training dataset')
    parser.add_argument('--skip-download', action='store_true',
                        help='Skip Kaggle download, just organize existing files')
    parser.add_argument('--manual-dir', type=str, default=None,
                        help='Path to folder with manually organized normal/ and ulcer/ subfolders')
    args = parser.parse_args()

    if args.manual_dir:
        # Manual mode: user already has images organized
        manual = Path(args.manual_dir)
        if not manual.exists():
            print(f"[ERROR] {manual} does not exist")
            sys.exit(1)
        normal_dir = manual / 'normal'
        ulcer_dir = manual / 'ulcer'
        if not normal_dir.exists() or not ulcer_dir.exists():
            print(f"[ERROR] Expected {manual}/normal/ and {manual}/ulcer/ subfolders")
            sys.exit(1)
        normal_images = find_images(normal_dir)
        ulcer_images = find_images(ulcer_dir)
        print(f"Found {len(normal_images)} normal, {len(ulcer_images)} ulcer images")

        random.seed(SEED)
        random.shuffle(normal_images)
        random.shuffle(ulcer_images)

        def split_and_copy(images, cls):
            n = len(images)
            n_test = int(n * TEST_SPLIT)
            n_val = int(n * VAL_SPLIT)
            splits = {
                'test': images[:n_test],
                'val': images[n_test:n_test + n_val],
                'train': images[n_test + n_val:],
            }
            for split, imgs in splits.items():
                dest = OUTPUT_DIR / split / cls
                dest.mkdir(parents=True, exist_ok=True)
                for i, src in enumerate(imgs):
                    dst = dest / f"{cls}_{i:04d}{src.suffix}"
                    shutil.copy2(str(src), str(dst))

        split_and_copy(normal_images, 'normal')
        split_and_copy(ulcer_images, 'ulcer')

        for split in ['train', 'val', 'test']:
            n_n = len(list((OUTPUT_DIR / split / 'normal').glob('*')))
            n_u = len(list((OUTPUT_DIR / split / 'ulcer').glob('*')))
            print(f"  {split}: {n_n} normal + {n_u} ulcer")
        print(f"\nDataset ready at: {OUTPUT_DIR}")

    elif args.skip_download:
        organize_dataset()
    else:
        api = check_kaggle()
        download_dataset(api)
        organize_dataset()
