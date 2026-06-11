"""
Mountmind PeakOCR - Real Scan Dataset Integrator
Processes local scanned documents, segments them into text lines,
prompts for transcription, and pushes updates to the Hugging Face dataset.
"""

import os
import cv2
import json
import shutil
import sys
from PIL import Image

# Ensure we can import from the src folder
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
import preprocess
import upload_to_hf

def main():
    print("=" * 60)
    print("      Mountmind PeakOCR - Local Scan Dataset Integrator")
    print("=" * 60)
    
    # 1. Ask for Hugging Face credentials
    username = input("Enter your Hugging Face username [default: prashant0919]: ").strip()
    if not username:
        username = "prashant0919"
        
    token = input("Enter your Hugging Face Write Token: ").strip()
    if not token:
        print("[!] Error: Token is required to sync with Hugging Face.")
        return
        
    # Paths configuration
    raw_scans_dir = "raw_scans"
    dataset_dir = "dataset"
    train_dir = os.path.join(dataset_dir, "train")
    
    # Create raw scans folder if it doesn't exist
    if not os.path.exists(raw_scans_dir):
        os.makedirs(raw_scans_dir)
        print(f"[*] Created '{raw_scans_dir}/' directory.")
        print(f"[!] Please drop your raw scanned images (.png, .jpg, .jpeg) into '{raw_scans_dir}/' and run this script again.")
        return
        
    # Get scanned files
    valid_exts = (".png", ".jpg", ".jpeg", ".tiff")
    scan_files = [f for f in os.listdir(raw_scans_dir) if f.lower().endswith(valid_exts)]
    
    if not scan_files:
        print(f"[!] No scanned images found in '{raw_scans_dir}/' folder.")
        print(f"    Drop some images there (e.g. test.jpg) and run the script again.")
        return
        
    print(f"[*] Found {len(scan_files)} scanned document(s) in '{raw_scans_dir}/'.")
    
    # Ensure dataset directories exist
    os.makedirs(train_dir, exist_ok=True)
    metadata_path = os.path.join(train_dir, "metadata.jsonl")
    
    # Load existing metadata to find current image index offsets
    existing_items = []
    if os.path.exists(metadata_path):
        with open(metadata_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    existing_items.append(json.loads(line.strip()))
                    
    current_idx_start = len(existing_items) + 1
    new_records = []
    
    # Process each scan document
    for scan_file in scan_files:
        file_path = os.path.join(raw_scans_dir, scan_file)
        print(f"\n[*] Processing document: {scan_file}")
        
        # 1. Load and Preprocess
        try:
            img = preprocess.load_image(file_path)
            img_rgb = preprocess.convert_bgr_to_rgb(img)
            img_gray = preprocess.convert_bgr_to_gray(img)
            img_deskewed, _ = preprocess.deskew_image(img_gray)
            img_denoised = preprocess.denoise_bilateral(img_deskewed)
            img_binarized = preprocess.apply_adaptive_threshold(img_denoised)
            img_cleaned = preprocess.clean_speckle_noise(img_binarized)
            img_cleaned = preprocess.clean_margin_shadows(img_cleaned)
            
            # 2. Segment Layout to find lines
            line_boxes = preprocess.segment_layout(img_cleaned)
        except Exception as e:
            print(f"[!] Failed to process {scan_file}: {e}")
            continue
            
        if not line_boxes:
            print(f"[!] No text lines detected in document {scan_file}.")
            continue
            
        print(f"[+] Detected {len(line_boxes)} text lines in document.")
        
        # 3. Process each line box
        for idx, box in enumerate(line_boxes):
            x, y, w, h = box
            # Slice line crop
            line_crop = img_deskewed[y:y+h, x:x+w]
            
            # Save temporary image for visualization
            temp_crop_path = "temp_crop_preview.png"
            cv2.imwrite(temp_crop_path, line_crop)
            
            crop_name = f"scanned_line_{current_idx_start:05d}.png"
            target_crop_path = os.path.join(train_dir, crop_name)
            
            print(f"--- Line Crop {idx+1}/{len(line_boxes)} ---")
            print(f"    Line coordinates: X={x}, Y={y}, W={w}, H={h}")
            
            # Request transcription from terminal
            transcription = input(f"    Enter transcription for this line (leave blank to skip): ").strip()
            
            if not transcription:
                print("    [!] Skipped line.")
                if os.path.exists(temp_crop_path):
                    os.remove(temp_crop_path)
                continue
                
            # Copy file to dataset directory
            shutil.copy(temp_crop_path, target_crop_path)
            if os.path.exists(temp_crop_path):
                os.remove(temp_crop_path)
                
            new_records.append({
                "file_name": crop_name,
                "text": transcription
            })
            current_idx_start += 1
            
    if not new_records:
        print("\n[*] No new labeled scan lines were added.")
        return
        
    # Append new records to metadata.jsonl
    with open(metadata_path, "a", encoding="utf-8") as f:
        for record in new_records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            
    print(f"\n[+] Successfully appended {len(new_records)} new scan line crops and updated metadata.jsonl")
    
    # 4. Sync updates to Hugging Face Hub
    sync_choice = input("[*] Sync these changes with Hugging Face now? (y/n): ").strip().lower()
    if sync_choice == 'y':
        print("[*] Synchronizing dataset folder to Hugging Face...")
        # Invoke upload_to_hf utility logic
        try:
            repo_id = f"{username}/nepali-synthetic-ocr-lines"
            from huggingface_hub import HfApi
            api = HfApi(token=token)
            api.create_repo(repo_id=repo_id, repo_type="dataset", exist_ok=True, private=False)
            api.upload_folder(
                folder_path=dataset_dir,
                repo_id=repo_id,
                repo_type="dataset"
            )
            print("\n" + "=" * 60)
            print("[+] Sync complete! Access your dataset at:")
            print(f"    https://huggingface.co/datasets/{repo_id}")
            print("=" * 60 + "\n")
        except Exception as e:
            print(f"[!] Error uploading to Hugging Face: {e}")
            
if __name__ == "__main__":
    main()
