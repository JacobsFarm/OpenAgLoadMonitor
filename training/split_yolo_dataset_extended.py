import os
import shutil
import random

# ==========================================
# CONFIGURATION
# ==========================================

# 1. Main Dataset (uncropped)
MAIN_IMAGES_FOLDER = r"/path/to/dataset_main/images"
MAIN_LABELS_FOLDER = r"/path/to/dataset_main/labels"

# 2. Extra Dataset 1 (cropped around monitor)
USE_EXTRA_1 = False
EXTRA_1_IMAGES_FOLDER = r"/path/to/dataset_extra1/images"
EXTRA_1_LABELS_FOLDER = r"/path/to/dataset_extra1/labels"

# 3. Extra Dataset 2 (cropped around LCD-screen)
USE_EXTRA_2 = False
EXTRA_2_IMAGES_FOLDER = r"/path/to/dataset_extra2/images"
EXTRA_2_LABELS_FOLDER = r"/path/to/dataset_extra2/labels"

# 4. Null Dataset (Background images - checks for empty label files)
USE_NULL_DATASET = False
NULL_IMAGES_FOLDER = r"/path/to/null_dataset/images"
NULL_LABELS_FOLDER = r"/path/to/null_dataset/labels"
NUM_NULL_IMAGES = 0  # Set to 0 to use all available images

# 5. Output Directories
OUTPUT_TRAIN_FOLDER = r"/path/to/output/train"
OUTPUT_VALID_FOLDER = r"/path/to/output/valid"
OUTPUT_TEST_FOLDER  = r"/path/to/output/test"  

# 6. Split Ratios (Must sum to 1.0)
TRAIN_RATIO = 0.70
VALID_RATIO = 0.20
TEST_RATIO  = 0.10  

# ==========================================
# END CONFIGURATION
# ==========================================

def get_image_label_pairs(images_dir, labels_dir, mode="main"):
    """Scans directories and pairs images with their label files."""
    image_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp']
    pairs = []
    
    if not os.path.exists(images_dir) or not os.path.exists(labels_dir):
        print(f"   [!] Warning: Directory not found: {images_dir}")
        return []

    print(f"   Scanning: {images_dir} (Mode: {mode})...")
    
    files = os.listdir(images_dir)
    ignored_not_empty = 0

    for filename in files:
        name, ext = os.path.splitext(filename)
        if ext.lower() not in image_extensions:
            continue

        image_path = os.path.join(images_dir, filename)
        label_file = name + '.txt'
        label_path = os.path.join(labels_dir, label_file)
        
        if os.path.exists(label_path):
            if mode == "null":
                try:
                    with open(label_path, 'r') as f:
                        content = f.read().strip()
                    if len(content) > 0:
                        ignored_not_empty += 1
                        continue 
                except Exception as e:
                    print(f"Error reading {label_file}: {e}")
                    continue

            pairs.append({
                'image_path': image_path,
                'label_path': label_path,
                'filename': filename,
                'label_name': label_file,
                'type': mode
            })
    
    if mode == "null":
        print(f"   -> {ignored_not_empty} annotated images ignored in NULL folder.")
                
    return pairs

def copy_files(data_list, dest_folder):
    """Copies the files to the destination folders."""
    if not data_list:
        return

    img_dest = os.path.join(dest_folder, "images")
    lbl_dest = os.path.join(dest_folder, "labels")
    
    os.makedirs(img_dest, exist_ok=True)
    os.makedirs(lbl_dest, exist_ok=True)
    
    for item in data_list:
        try:
            shutil.copy2(item['image_path'], os.path.join(img_dest, item['filename']))
            shutil.copy2(item['label_path'], os.path.join(lbl_dest, item['label_name']))
        except Exception as e:
            print(f"Error copying {item['filename']}: {e}")

def main():
    print("--- Start Dataset Splitter ---")
    
    # Verify Ratios
    total_ratio = TRAIN_RATIO + VALID_RATIO + TEST_RATIO
    if abs(total_ratio - 1.0) > 0.001:
        print(f"\n[!] WARNING: Ratios do not sum to 1.0 (Current sum: {total_ratio})")
        print("    Please adjust TRAIN_RATIO, VALID_RATIO, and TEST_RATIO.")
        return

    # 1. Load Main Dataset
    print("\n[1/5] Loading Main Dataset...")
    main_pairs = get_image_label_pairs(MAIN_IMAGES_FOLDER, MAIN_LABELS_FOLDER, mode="main")
    print(f"   Images found: {len(main_pairs)}")

    # 2. Load Extra Dataset 1
    extra_1_pairs = []
    if USE_EXTRA_1:
        print("\n[2/5] Loading Extra Dataset 1...")
        extra_1_pairs = get_image_label_pairs(EXTRA_1_IMAGES_FOLDER, EXTRA_1_LABELS_FOLDER, mode="main")
        print(f"   Images found: {len(extra_1_pairs)}")
    else:
        print("\n[2/5] Extra Dataset 1 skipped.")
    
    # 3. Load Extra Dataset 2
    extra_2_pairs = []
    if USE_EXTRA_2:
        print("\n[3/5] Loading Extra Dataset 2...")
        extra_2_pairs = get_image_label_pairs(EXTRA_2_IMAGES_FOLDER, EXTRA_2_LABELS_FOLDER, mode="main")
        print(f"   Images found: {len(extra_2_pairs)}")
    else:
        print("\n[3/5] Extra Dataset 2 skipped.")

    # 4. Load Null Dataset
    selected_nulls = []
    if USE_NULL_DATASET:
        print("\n[4/5] Loading Null Dataset...")
        null_pairs = get_image_label_pairs(NULL_IMAGES_FOLDER, NULL_LABELS_FOLDER, mode="null")
        
        if len(null_pairs) > NUM_NULL_IMAGES > 0:
            random.shuffle(null_pairs)
            selected_nulls = null_pairs[:NUM_NULL_IMAGES]
            print(f"   -> Randomly selected {NUM_NULL_IMAGES} images.")
        else:
            selected_nulls = null_pairs
            print(f"   -> Using all available images ({len(null_pairs)}).")
    else:
        print("\n[4/5] Null Dataset skipped.")
    
    # Merge all data
    all_data = main_pairs + extra_1_pairs + extra_2_pairs + selected_nulls
    
    if not all_data:
        print("\n[!] No data found! Please check your paths.")
        return

    print(f"\nTotal images to process: {len(all_data)}")
    
    # Shuffle and Split
    random.shuffle(all_data)
    
    total_count = len(all_data)
    train_count = int(total_count * TRAIN_RATIO)
    valid_count = int(total_count * VALID_RATIO)
    
    train_set = all_data[:train_count]
    valid_set = all_data[train_count : train_count + valid_count]
    test_set  = all_data[train_count + valid_count :]
    
    # 5. Execute Copy
    print(f"\n[5/5] Copying files...")
    
    print(f"   -> Copying TRAIN set ({len(train_set)} images)...")
    copy_files(train_set, OUTPUT_TRAIN_FOLDER)
    
    print(f"   -> Copying VALID set ({len(valid_set)} images)...")
    copy_files(valid_set, OUTPUT_VALID_FOLDER)
    
    print(f"   -> Copying TEST set ({len(test_set)} images)...")
    copy_files(test_set, OUTPUT_TEST_FOLDER)
    
    print("\n--- Summary ---")
    print(f"TRAIN set: {len(train_set)}")
    print(f"VALID set: {len(valid_set)}")
    print(f"TEST  set: {len(test_set)}")
    print("\nDone!")

if __name__ == "__main__":
    main()
