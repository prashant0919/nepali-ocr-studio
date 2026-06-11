"""
Mountmind PeakOCR - Hugging Face Dataset Generator
Generates a structured ImageFolder dataset (train/test splits and metadata.jsonl)
of synthetic Devanagari text lines for OCR/HTR fine-tuning.
"""

import os
import random
import json
import shutil
import argparse
from PIL import Image
import sys

# Ensure we can import from the src folder
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
import synthetic_generator

# Curated lists of Devanagari/Nepali phrases to build realistic text combinations
SUBJECTS = [
    "नेपाल सरकार", "गृह मन्त्रालय", "परराष्ट्र मन्त्रालय", "स्वास्थ्य तथा जनसंख्या मन्त्रालय",
    "शिक्षा, विज्ञान तथा प्रविधि मन्त्रालय", "अर्थ मन्त्रालय", "सञ्चार तथा सूचना प्रविधि मन्त्रालय",
    "जिल्ला प्रशासन कार्यालय", "मन्त्रिपरिषद्को कार्यालय", "संघीय मामिला तथा सामान्य प्रशासन मन्त्रालय",
    "कृषि तथा पशुपन्छी विकास मन्त्रालय", "उद्योग, वाणिज्य तथा आपूर्ति मन्त्रालय", "ऊर्जा, जलस्रोत तथा सिँचाइ मन्त्रालय",
    "भौतिक पूर्वाधार तथा यातायात मन्त्रालय", "संस्कृति, पर्यटन तथा नागरिक उड्डयन मन्त्रालय", "कानून, न्याय तथा संसदीय मामिला मन्त्रालय",
    "शहरी विकास मन्त्रालय", "वन तथा वातावरण मन्त्रालय", "भूमि व्यवस्था, सहकारी तथा गरिबी निवारण मन्त्रालय",
    "प्रहरी प्रधान कार्यालय", "सैनिक मुख्यालय जङ्गी अड्डा", "राष्ट्रिय अनुसन्धान विभाग"
]

LOCATIONS = [
    "सिंहदरबार, काठमाण्डौं", "शीतल निवास, महाराजगञ्ज", "बालुवाटार, काठमाण्डौं", 
    "पोखरा, कास्की", "विराटनगर, मोरङ", "ललितपुर, नेपाल", "भक्तपुर, नेपाल",
    "हेटौँडा, मकवानपुर", "बुटवल, रुपन्देही", "जनकपुर, धनुषा", "सुर्खेत, सुर्खेत",
    "धनगढी, कैलाली", "काठमाडौँ महानगरपालिका", "ललितपुर महानगरपालिका"
]

TOPICS = [
    "वैदेशिक भ्रमण सम्बन्धी पत्र", "क्षेत्रीय सहकार्य सम्मेलन", "बजेट विनियोजन तथा अख्तियारी",
    "कर्मचारी सरुवा र पदस्थापन", "नयाँ कार्यविधि स्वीकृत गर्ने सम्बन्धमा", "वार्षिक समिक्षा बैठक",
    "आर्थिक सहायता उपलब्ध गराउने सम्बन्धमा", "द्विपक्षीय व्यापार सम्झौता नवीकरण", "सुरक्षा व्यवस्था सुदृढीकरण",
    "सूचना प्रविधि प्रणाली स्तरोन्नति", "वातावरणीय प्रभाव मूल्यांकन", "सार्वजनिक सुनुवाई कार्यक्रम",
    "विपद व्यवस्थापन तथा राहत वितरण", "राष्ट्रिय जनगणना तथ्याङ्क प्रतिवेदन", "सार्वजनिक खरिद सम्झौता सम्बन्धी"
]

ROLES = [
    "शाखा अधिकृत", "उप-सचिव", "सह-सचिव", "महानिर्देशक", "मन्त्रालय प्रवक्ता", "प्रमुख जिल्ला अधिकारी",
    "प्रशासन अधिकृत", "कम्प्युटर अधिकृत", "लेखा अधिकृत", "मुख्य सचिव", "विभागाध्यक्ष"
]

NEPALI_MONTHS = ["वैशाख", "जेठ", "असार", "साउन", "भदौ", "असोज", "कात्तिक", "मंसिर", "पुस", "माघ", "फागुन", "चैत"]

def generate_random_date():
    year = random.randint(2070, 2085)
    month = random.choice(NEPALI_MONTHS)
    day = random.randint(1, 30)
    return f"मितिः {year} {month} {day} गते"

def generate_random_ref_num():
    prefix = random.choice(["च.नं.", "चलानी नम्बरः", "पत्र संख्याः"])
    num1 = random.randint(100, 9999)
    year_short1 = random.randint(75, 85)
    year_short2 = year_short1 + 1
    return f"{prefix} {num1}/०{year_short1}/०{year_short2}"

def generate_random_sentence():
    """Generates highly randomized, realistic Nepali government document text lines."""
    structures = [
        lambda: f"{random.choice(SUBJECTS)} {random.choice(LOCATIONS)}",
        lambda: generate_random_ref_num(),
        lambda: generate_random_date(),
        lambda: f"विषय: {random.choice(TOPICS)}",
        lambda: f"श्री {random.choice(ROLES)}, {random.choice(SUBJECTS)}",
        lambda: f"कार्य विवरण तथा बाँडफाँड सम्बन्धमा",
        lambda: f"नेपाल सरकारको निर्णय बमोजिम तोकिएको मिति",
        lambda: f"क्षेत्रीय सहकार्य सम्मेलनमा भाग लिनुहुन",
        lambda: f"सादर अनुरोध गर्दछु, {random.choice(ROLES)}",
        lambda: f"प्राविधिक सहयोग तथा क्षमता अभिवृद्धि कार्यक्रम",
        lambda: f"प्रस्तुत विषयमा आवश्यक कार्यान्वयनका लागि पठाइएको छ"
    ]
    return random.choice(structures)()

def build_hf_dataset(output_dir="dataset", num_train=5000, num_test=1000):
    print("=" * 60)
    print("      Mountmind PeakOCR - Hugging Face Dataset Builder")
    print("=" * 60)
    
    # Setup directories
    train_dir = os.path.join(output_dir, "train")
    test_dir = os.path.join(output_dir, "test")
    
    # Clear existing dataset folder to ensure clean build
    if os.path.exists(output_dir):
        print(f"[*] Cleaning existing dataset directory: {output_dir}")
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
        total_count = split["count"]
        
        print(f"\n[*] Generating {split['name']} split...")
        for idx in range(total_count):
            # Log progress every 10%
            if (idx + 1) % max(1, total_count // 10) == 0 or idx == 0 or idx == total_count - 1:
                print(f"    - Progressive Generation: {idx+1}/{total_count} ({((idx+1)/total_count)*100:.1f}%)")
                
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
            file_name = f"line_{idx+1:05d}.png"
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
    parser = argparse.ArgumentParser(description="Scaled-Up Synthetic Devanagari OCR Dataset Builder")
    parser.add_argument("--num_train", type=int, default=5000, help="Number of training samples to generate")
    parser.add_argument("--num_test", type=int, default=1000, help="Number of testing samples to generate")
    parser.add_argument("--output_dir", type=str, default="dataset", help="Output directory path")
    args = parser.parse_args()
    
    build_hf_dataset(
        output_dir=args.output_dir,
        num_train=args.num_train,
        num_test=args.num_test
    )
