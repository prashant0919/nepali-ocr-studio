"""
Mountmind PeakOCR - Devanagari Synthetic Data Generator
Generates distorted text line images and bounding box coordinates in COCO/YOLO format
for training printed or handwritten OCR models.
"""

import os
import argparse
import json
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

def get_unicode_font(font_size=32):
    """
    Search for standard unicode/Devanagari fonts available on macOS, Linux, or Windows.
    Falls back to PIL default font if none are found.
    """
    system_fonts = [
        # macOS paths
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        "/System/Library/Fonts/Supplemental/Sanskrit2003.ttf",
        "/Library/Fonts/Arial Unicode.ttf",
        # Windows paths
        "C:\\Windows\\Fonts\\arialuni.ttf",
        "C:\\Windows\\Fonts\\mangal.ttf",
        # Linux paths
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSans.ttf"
    ]
    
    for font_path in system_fonts:
        if os.path.exists(font_path):
            try:
                return ImageFont.truetype(font_path, font_size)
            except Exception:
                continue
                
    # Fallback to default
    print("[!] Warning: Could not locate unicode Devanagari font. Using default PIL font.")
    return ImageFont.load_default()

def generate_synthetic_line(text, font_style=None, rotation=0.0, blur=0.0, noise_pct=5.0, shadow_pct=15.0):
    """
    Renders text line onto a PIL canvas, applies distortions, and computes word boundary boxes.
    """
    width = 700
    height = 160
    
    # 1. Base paper canvas
    image = Image.new("RGB", (width, height), color=(246, 241, 229)) # creamy white paper
    draw = ImageDraw.Draw(image)
    
    # 2. Render Shadow Vignette Gradient
    if shadow_pct > 0:
        gradient = Image.new("L", (width, height), color=0)
        grad_draw = ImageDraw.Draw(gradient)
        for x in range(width):
            intensity = int(x / width * (shadow_pct / 100.0) * 120)
            grad_draw.line([(x, 0), (x, height)], fill=intensity)
        # Apply shadow overlay
        shadow_layer = Image.new("RGB", (width, height), color=(0, 0, 0))
        image = Image.composite(image, shadow_layer, Image.eval(gradient, lambda x: 255 - x))
        draw = ImageDraw.Draw(image)
        
    # 3. Setup Font
    font = get_unicode_font(font_size=32)
    
    # Measure text dimensions
    try:
        # Pillow >= 8.0 text length
        text_w = draw.textlength(text, font=font)
        text_h = 36
    except AttributeError:
        # Older Pillow fallback
        text_w, text_h = draw.textsize(text, font=font)
        
    # Draw centered on virtual text canvas
    text_canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    text_draw = ImageDraw.Draw(text_canvas)
    
    start_x = (width - text_w) / 2
    start_y = (height - text_h) / 2
    text_draw.text((start_x, start_y), text, fill=(20, 20, 20, 255), font=font)
    
    # 4. Skew Rotation and Affine Transform
    if rotation != 0:
        # Skew/rotate text canvas
        text_canvas = text_canvas.rotate(rotation, resample=Image.BICUBIC, expand=False)
        
    # Composite text onto paper base
    image.paste(text_canvas, (0, 0), text_canvas)
    
    # 5. Gaussian Blur (Ink Bleed simulation)
    if blur > 0:
        image = image.filter(ImageFilter.GaussianBlur(radius=blur))
        
    # 6. Speckle Noise (Salt & Pepper)
    if noise_pct > 0:
        img_array = np.array(image)
        total_pixels = width * height
        noise_pixels = int(total_pixels * (noise_pct / 100.0))
        
        for _ in range(noise_pixels):
            y = np.random.randint(0, height)
            x = np.random.randint(0, width)
            color = 0 if np.random.rand() < 0.5 else 255
            img_array[y, x] = [color, color, color]
        image = Image.fromarray(img_array)
        
    # 7. Generate Bounding Boxes for Word Annotations
    words = text.split()
    estimated_char_width = text_w / len(text) if len(text) > 0 else 20
    
    current_x = start_x
    annotations = []
    
    for idx, word in enumerate(words):
        word_w = len(word) * estimated_char_width
        word_h = 45
        
        # Word BBox structure [x, y, width, height]
        bbox = [
            int(current_x),
            int(start_y - 4),
            int(word_w),
            int(word_h)
        ]
        
        annotations.append({
            "id": idx + 1,
            "bbox": bbox,
            "area": float(bbox[2] * bbox[3]),
            "text": word,
            "category": "text"
        })
        current_x += word_w + estimated_char_width * 0.8
        
    return image, annotations

def main():
    parser = argparse.ArgumentParser(description="Synthetic Devanagari OCR Data Generator")
    parser.add_argument("--text", type=str, default="नेपाल सरकार गृह मन्त्रालय", help="Devanagari text to render")
    parser.add_argument("--rotation", type=float, default=2.0, help="Rotation skew angle (-15 to 15)")
    parser.add_argument("--blur", type=float, default=0.5, help="Blur radius")
    parser.add_argument("--noise", type=float, default=4.0, help="Speckle noise percentage")
    parser.add_argument("--output_dir", type=str, default="outputs", help="Output artifacts directory")
    args = parser.parse_args()
    
    if not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir)
        
    image_path = os.path.join(args.output_dir, "synthetic_generated_line.png")
    json_path = os.path.join(args.output_dir, "synthetic_generated_labels.json")
    
    print("=" * 60)
    print("      Devanagari Synthetic Text Line Dataset Generator")
    print("=" * 60)
    print(f"[*] Rendering Text: '{args.text}'")
    print(f"[*] Rotation Skew:  {args.rotation}° | Blur: {args.blur}px | Noise: {args.noise}%")
    
    image, annotations = generate_synthetic_line(
        text=args.text,
        rotation=args.rotation,
        blur=args.blur,
        noise_pct=args.noise
    )
    
    # Save Image
    image.save(image_path)
    print(f"[+] Saved synthetic image sample to: {image_path}")
    
    # Save COCO Annotations
    dataset_metadata = {
        "image_file": "synthetic_generated_line.png",
        "image_dimensions": [700, 160],
        "annotations": annotations
    }
    
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(dataset_metadata, f, indent=4, ensure_ascii=False)
    print(f"[+] Saved dataset annotation labels to: {json_path}")
    print("=" * 60 + "\n")

if __name__ == "__main__":
    main()
