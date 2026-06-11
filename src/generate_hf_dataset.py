"""
Mountmind PeakOCR - Hugging Face Dataset Generator
Generates a structured ImageFolder dataset (train/test splits and metadata.jsonl)
of synthetic Devanagari text lines for OCR/HTR fine-tuning.
"""

import os
import random
import json
import shutil
from PIL import Image
import sys

# Ensure we can import from the src folder
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
import synthetic_generator

# Curated lists of Devanagari/Nepali phrases to build realistic text combinations
SUBJECTS = [
    "नेपाल सरकार", "गृह मन्त्रालय", "परराष्ट्र मन्त्रालय", "स्वास्थ्य तथा जनसंख्या मन्त्रालय",
    "शिक्षा, विज्ञान तथा प्रविधि मन्त्रालय", "अर्थ मन्त्रालय", "सञ्चार तथा सूचना प्रविधि मन्त्रालय",
    "जिल्ला प्रशासन कार्यालय", "मन्त्रिपरिषद्को कार्यालय", "संघीय मामिला तथा सामान्य प्रशासन मन्त्रालय"
]

LOCATIONS = [
    "सिंहदरबार, काठमाण्डौं", "शीतल निवास, महाराजगञ्ज", "बालुवाटार, काठमाण्डौं", 
    "पोखरा, कास्की", "विराटनगर, मोरङ", "ललितपुर, नेपाल", "भक्तपुर, नेपाल"
]

METADATA_CHIPS = [
    "पत्र संख्याः २२/४१/१०००/७१", "चलानी नम्बरः १०४६", "च.नं. ९८२/०८०/०८१",
    "मितिः २०८०/११/१२", "मितिः २०८१ फागुन २२ गते", "मितिः २०८२ वैशाख १५ गते"
]

TOPICS = [
    "वैदेशिक भ्रमण सम्बन्धी पत्र", "क्षेत्रीय सहकार्य सम्मेलन", "बजेट विनियोजन तथा अख्तियारी",
    "कर्मचारी सरुवा र पदस्थापन", "नयाँ कार्यविधि स्वीकृत गर्ने सम्बन्धमा", "वार्षिक समिक्षा बैठक"
]

ROLES = [
    "शाखा अधिकृत", "उप-सचिव", "सह-सचिव", "महानिर्देशक", "मन्त्रालय प्रवक्ता", "प्रमुख जिल्ला अधिकारी"
]

def generate_random_sentence():
    """Generates a randomized, realistic Nepali government document text line."""
    structures = [
        lambda: f"{random.choice(SUBJECTS)} {random.choice(LOCATIONS)}",
        lambda: random.choice(METADATA_CHIPS),
        lambda: f"विषय: {random.choice(TOPICS)}",
        lambda: f"श्री {random.choice(ROLES)}, {random.choice(SUBJECTS)}",
        lambda: f"कार्य विवरण तथा बाँडफाँड सम्बन्धमा",
        lambda: f"नेपाल सरकारको निर्णय बमोजिम तोकिएको मिति",
        lambda: f"क्षेत्रीय सहकार्य सम्मेलनमा भाग लिनुहुन",
        lambda: f"सादर अनुरोध गर्दछु, {random.choice(ROLES)}"
    ]
    return random.choice(structures)()

def build_hf_dataset(output_dir="dataset", num_train=150, num_test=30):
    print("=" * 60)
    print("      Mountmind PeakOCR - Hugging Face Dataset Builder")
    print("=" * 60)
    
    # Setup directories
    train_dir = os.path.join(output_dir, "train")
    test_dir = os.path.join(output_dir, "test")
    
    # Clear existing dataset folder to ensure clean build
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
        
    os.makedirs(train_dir)
    os.makedirs(test_dir)
    
    print(f"[*] Target Directory: {output_dir}/")
    print(f"[*] Generating {num_train} train and {num_test} test samples...")
    
    splits = [
        {"name": "train", "dir": train_dir, "count": num_train},
        {"name": "test", "dir": test_dir, "count": num_test}
    ]
    
    for split in splits:
        metadata_lines = []
        split_dir = split["dir"]
        
        for idx in range(split["count"]):
            # Get text & generate image
            text = generate_random_sentence()
            
            # Apply random distortions to replicate old scanned paper
            rotation = random.uniform(-4.0, 4.0)
            blur = random.uniform(0.1, 0.7)
            noise_pct = random.uniform(1.0, 5.0)
            shadow_pct = random.uniform(5.0, 20.0)
            
            image, _ = synthetic_generator.generate_synthetic_line(
                text=text,
                rotation=rotation,
                blur=blur,
                noise_pct=noise_pct,
                shadow_pct=shadow_pct
            )
            
            # Save image
            file_name = f"line_{idx+1:04d}.png"
            image.save(os.path.join(split_dir, file_name))
            
            # Store in Hugging Face ImageFolder Metadata Format
            metadata_lines.append({
                "file_name": file_name,
                "text": text
            })
            
        # Write metadata.jsonl
        metadata_path = os.path.join(split_dir, "metadata.jsonl")
        with open(metadata_path, "w", encoding="utf-8") as f:
            for line in metadata_lines:
                f.write(json.dumps(line, ensure_ascii=False) + "\n")
                
        print(f"[+] Finished generating {split['name']} split and saved metadata.jsonl")
        
    print("\n" + "=" * 60)
    print("      Dataset Generation Complete!")
    print("=" * 60)
    print(f"Location: {os.path.abspath(output_dir)}")
    print("Structure:")
    print("  - dataset/train/           (Contains PNG images & metadata.jsonl)")
    print("  - dataset/test/            (Contains PNG images & metadata.jsonl)")
    print("=" * 60 + "\n")

if __name__ == "__main__":
    build_hf_dataset()
