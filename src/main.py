"""
Mountmind PeakOCR - Main Pipeline Runner and Visualizer
Runs the preprocessing pipeline stages on the sample Nepali document 
and generates comparative visualization plots saved in the outputs/ folder.
"""

import os
import cv2
# Configure Matplotlib to use the 'Agg' non-interactive backend
# This ensures it runs without requiring a GUI server/display on Mac/Linux
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

import preprocess

def main():
    print("=" * 60)
    print("         Mountmind PeakOCR Preprocessing & HTR Pipeline - Starting")
    print("=" * 60)
    
    # Path configuration
    input_path = "sample_images/test.jpg"
    output_dir = "outputs"
    output_comparison_path = os.path.join(output_dir, "preprocessing_comparison.png")
    output_segmentation_path = os.path.join(output_dir, "layout_segmentation.png")
    line_crops_dir = os.path.join(output_dir, "line_crops")
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"[*] Created output directory: {output_dir}")
    if not os.path.exists(line_crops_dir):
        os.makedirs(line_crops_dir)
        print(f"[*] Created line crops directory: {line_crops_dir}")
        
    print(f"[*] Loading sample image: {input_path}")
    try:
        img_bgr = preprocess.load_image(input_path)
    except FileNotFoundError as e:
        # Check test.png if test.jpg isn't there
        input_path = "sample_images/test.png"
        try:
            img_bgr = preprocess.load_image(input_path)
        except FileNotFoundError:
            print("[!] Error: Could not find any test images.")
            return
        
    height, width, channels = img_bgr.shape
    print(f"    - NumPy Array Shape: {img_bgr.shape} (Height: {height}px, Width: {width}px)")
    
    # Stage 1: RGB Conversion
    print("[*] Stage 1: Converting BGR to RGB...")
    img_rgb = preprocess.convert_bgr_to_rgb(img_bgr)
    
    # Stage 2: Grayscale Conversion
    print("[*] Stage 2: Converting BGR to Grayscale...")
    img_gray = preprocess.convert_bgr_to_gray(img_bgr)
    
    # Stage 3: Deskewing (Hough Lines)
    print("[*] Stage 3: Performing deskewing rotation alignment...")
    img_deskewed, angle = preprocess.deskew_image(img_gray)
    print(f"    - Detected Rotation Skew: {angle:.2f} degrees (correcting alignment)")
    
    # Stage 4: Denoising (Bilateral filter to preserve character borders)
    print("[*] Stage 4: Applying bilateral filtering for edge-preserving denoising...")
    img_denoised = preprocess.denoise_bilateral(img_deskewed)
    
    # Stage 5: Gaussian Blur
    print("[*] Stage 5: Applying Gaussian Blur to reduce high-frequency scanner noise...")
    img_blur = preprocess.apply_gaussian_blur(img_denoised, kernel_size=(5, 5))
    
    # Stage 6: Adaptive Thresholding & Noise Removal
    print("[*] Stage 6: Applying Adaptive Thresholding (Gaussian C local neighborhoods)...")
    img_binarized = preprocess.apply_adaptive_threshold(img_denoised, block_size=11, c_value=2)
    
    print("[*] Stage 6.1: Removing speckle noise...")
    img_despeckled = preprocess.clean_speckle_noise(img_binarized, max_area=5)
    
    print("[*] Stage 6.2: Erasing margin boundary shadows...")
    img_cleaned = preprocess.clean_margin_shadows(img_despeckled, margin_percent=3.5)
    
    # Stage 7: Layout Analysis & Line Segmentation
    print("[*] Stage 7: Performing layout analysis (projection profile segmenter)...")
    line_boxes = preprocess.segment_layout(img_cleaned)
    print(f"    - Detected {len(line_boxes)} line segments inside document.")
    
    # Draw line boxes on the color deskewed image for visual verification
    img_layout_draw = cv2.cvtColor(img_deskewed, cv2.COLOR_GRAY2BGR)
    
    # Crop and save individual lines to simulate HTR input datasets
    for idx, box in enumerate(line_boxes):
        x, y, w, h = box
        cv2.rectangle(img_layout_draw, (x, y), (x + w, y + h), (16, 185, 129), 2)
        # Add labels
        cv2.putText(img_layout_draw, f"L{idx+1}", (x + 2, y + 15), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (96, 165, 250), 1)
        
        # Save cropped line
        line_crop = img_deskewed[y:y+h, x:x+w]
        cv2.imwrite(os.path.join(line_crops_dir, f"line_{idx+1:03d}.png"), line_crop)
        
    print(f"    - Segmented lines saved to: {line_crops_dir}")
    
    # Save Layout Analysis visual report
    print(f"[*] Saving Layout Analysis outline to: {output_segmentation_path}")
    cv2.imwrite(output_segmentation_path, img_layout_draw)
    
    # Save standard preprocessing comparison grid
    print("[*] Generating comparative visualization grid...")
    fig, axs = plt.subplots(2, 3, figsize=(18, 12), dpi=150)
    fig.patch.set_facecolor('#f7f9fa')
    
    axs[0, 0].imshow(img_bgr)
    axs[0, 0].set_title("1. BGR Raw (OpenCV Default)", fontsize=13, fontweight='bold', color='#2c3e50')
    axs[0, 0].axis("on")
    
    axs[0, 1].imshow(img_rgb)
    axs[0, 1].set_title("2. RGB Converted", fontsize=13, fontweight='bold', color='#2c3e50')
    axs[0, 1].axis("off")
    
    axs[0, 2].imshow(img_gray, cmap="gray")
    axs[0, 2].set_title("3. Grayscale Conversion", fontsize=13, fontweight='bold', color='#2c3e50')
    axs[0, 2].axis("off")
    
    axs[1, 0].imshow(img_deskewed, cmap="gray")
    axs[1, 0].set_title(f"4. Deskewed (Angle: {angle:.1f}°)", fontsize=13, fontweight='bold', color='#2c3e50')
    axs[1, 0].axis("off")
    
    axs[1, 1].imshow(img_denoised, cmap="gray")
    axs[1, 1].set_title("5. Bilateral Denoised", fontsize=13, fontweight='bold', color='#2c3e50')
    axs[1, 1].axis("off")
    
    axs[1, 2].imshow(img_cleaned, cmap="gray")
    axs[1, 2].set_title("6. Cleaned & Binarized Output", fontsize=13, fontweight='bold', color='#2980b9')
    axs[1, 2].axis("off")
    
    fig.suptitle("Mountmind PeakOCR - Advanced Preprocessing & Segmentation Pipeline", fontsize=18, fontweight='bold', color='#2c3e50', y=0.98)
    plt.tight_layout()
    plt.savefig(output_comparison_path, facecolor=fig.get_facecolor(), edgecolor='none', bbox_inches='tight')
    plt.close()
    
    print("\n" + "=" * 60)
    print("         Pipeline Execution Successfully Completed!")
    print("=" * 60)
    print(f"Saved artifacts:")
    print(f" - Comparison Grid:    {output_comparison_path}")
    print(f" - Layout Outlines:    {output_segmentation_path}")
    print(f" - Line crops count:   {len(line_boxes)} lines saved to outputs/line_crops/")
    print("=" * 60 + "\n")

if __name__ == "__main__":
    main()
