"""
Mountmind PeakOCR - Preprocessing Pipeline
This module contains standard functions for loading, cleaning, and preprocessing 
scanned documents, camera images, and handwritten texts to optimize OCR accuracy.
"""

import cv2
import numpy as np

def load_image(image_path: str) -> np.ndarray:
    """
    Loads an image from the specified path using OpenCV.
    
    Args:
        image_path (str): Path to the image file.
        
    Returns:
        np.ndarray: Loaded image in BGR color space.
        
    Raises:
        FileNotFoundError: If the image cannot be loaded.
    """
    image = cv2.imread(image_path)
    if image is None:
        raise FileNotFoundError(f"Could not load image at path: {image_path}")
    return image

def convert_bgr_to_rgb(image_bgr: np.ndarray) -> np.ndarray:
    """
    Converts a BGR image (OpenCV default) to RGB.
    
    Args:
        image_bgr (np.ndarray): Image in BGR format.
        
    Returns:
        np.ndarray: Image in RGB format.
    """
    return cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)

def convert_bgr_to_gray(image_bgr: np.ndarray) -> np.ndarray:
    """
    Converts a BGR image to a single-channel grayscale image.
    Grayscale conversion reduces dimensionality and focuses on contrast and shapes.
    
    Args:
        image_bgr (np.ndarray): Image in BGR format.
        
    Returns:
        np.ndarray: Grayscale image.
    """
    return cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)

def apply_gaussian_blur(image_gray: np.ndarray, kernel_size: tuple = (5, 5), sigma_x: float = 0) -> np.ndarray:
    """
    Applies Gaussian Blur to smooth the image and remove high-frequency noise 
    such as scanner artifacts, camera noise, or paper texture.
    
    Args:
        image_gray (np.ndarray): Single-channel grayscale image.
        kernel_size (tuple): Width and height of the Gaussian kernel (must be odd).
        sigma_x (float): Gaussian kernel standard deviation in X direction.
        
    Returns:
        np.ndarray: Blurred image.
    """
    return cv2.GaussianBlur(image_gray, kernel_size, sigma_x)

def apply_global_threshold(image_gray: np.ndarray, thresh_value: int = 150, max_value: int = 255) -> np.ndarray:
    """
    Applies standard binary thresholding. Any pixel with intensity greater than 
    thresh_value is set to max_value (white), others to 0 (black).
    
    Args:
        image_gray (np.ndarray): Single-channel grayscale image.
        thresh_value (int): Threshold level (0-255).
        max_value (int): Maximum value used with THRESH_BINARY.
        
    Returns:
        np.ndarray: Binary thresholded image.
    """
    _, thresholded = cv2.threshold(image_gray, thresh_value, max_value, cv2.THRESH_BINARY)
    return thresholded

def apply_adaptive_threshold(image_gray: np.ndarray, block_size: int = 11, c_value: int = 2, max_value: int = 255) -> np.ndarray:
    """
    Applies Adaptive Thresholding using Gaussian local neighborhood calculation.
    Highly effective for pages with non-uniform lighting, shadowing, or aging paper.
    
    Args:
        image_gray (np.ndarray): Single-channel grayscale image.
        block_size (int): Size of a pixel neighborhood that is used to calculate 
                          a threshold value (must be odd, e.g. 3, 5, 7, 11...).
        c_value (int): Constant subtracted from the mean or weighted mean.
        max_value (int): Maximum value used with binary thresholding.
        
    Returns:
        np.ndarray: Adaptive thresholded binary image.
    """
    return cv2.adaptiveThreshold(
        image_gray,
        max_value,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        block_size,
        c_value
    )

def deskew_image(image_gray: np.ndarray) -> tuple:
    """
    Detects paper rotation skew using Hough Line Transform and rotates the image to deskew it.
    
    Args:
        image_gray (np.ndarray): Single-channel grayscale image.
        
    Returns:
        tuple: (deskewed_image, detected_angle_in_degrees)
    """
    # Inverse threshold the image (black background, white text)
    _, thresh = cv2.threshold(image_gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    
    # Detect lines using HoughLinesP
    lines = cv2.HoughLinesP(thresh, 1, np.pi / 180, 100, minLineLength=100, maxLineGap=10)
    
    angles = []
    if lines is not None:
        for line in lines:
            x1, y1, x2, y2 = line[0]
            angle = np.arctan2(y2 - y1, x2 - x1) * 180 / np.pi
            # Only keep lines within a reasonable skew range (-15 to 15 degrees)
            if -15 < angle < 15:
                angles.append(angle)
                
    median_angle = np.median(angles) if len(angles) > 0 else 0.0
    
    # Rotate the image to correct the skew
    h, w = image_gray.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, median_angle, 1.0)
    rotated = cv2.warpAffine(image_gray, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    
    return rotated, median_angle

def denoise_bilateral(image_gray: np.ndarray, d: int = 9, sigma_color: float = 75, sigma_space: float = 75) -> np.ndarray:
    """
    Applies Bilateral Filter to remove noise while preserving sharp character edges.
    
    Args:
        image_gray (np.ndarray): Single-channel grayscale image.
        d (int): Diameter of each pixel neighborhood.
        sigma_color (float): Filter sigma in the color space.
        sigma_space (float): Filter sigma in the coordinate space.
        
    Returns:
        np.ndarray: Denoised image.
    """
    return cv2.bilateralFilter(image_gray, d, sigma_color, sigma_space)

def segment_layout(image_binary: np.ndarray) -> list:
    """
    Performs layout analysis using horizontal projection profiles to segment the document into lines.
    
    Args:
        image_binary (np.ndarray): Binarized image (background 255, text 0).
        
    Returns:
        list: List of bounding boxes [x, y, w, h] for each detected text line.
    """
    # Invert binary image so text pixels are 1 (or 255) and background is 0
    inverted = 255 - image_binary
    
    # Calculate horizontal projection profile (count text pixels along rows)
    row_sums = np.sum(inverted > 0, axis=1)
    
    h, w = image_binary.shape
    line_boxes = []
    
    # Segment rows where text is present
    in_line = False
    start_y = 0
    threshold = w * 0.02 # minimum pixel sum to consider text presence
    
    for y in range(h):
        if row_sums[y] > threshold and not in_line:
            in_line = True
            start_y = y
        elif row_sums[y] <= threshold and in_line:
            in_line = False
            end_y = y
            # Ignore lines that are too thin (noise)
            if (end_y - start_y) > 10:
                # Find x-bounds for this line by taking vertical projection of the line strip
                line_strip = inverted[start_y:end_y, :]
                col_sums = np.sum(line_strip > 0, axis=0)
                
                # Find left and right bounds
                non_zero_indices = np.where(col_sums > (end_y - start_y) * 0.05)[0]
                if len(non_zero_indices) > 0:
                    start_x = non_zero_indices[0]
                    end_x = non_zero_indices[-1]
                    line_boxes.append([int(start_x), int(start_y), int(end_x - start_x), int(end_y - start_y)])
                    
    return line_boxes

def clean_speckle_noise(image_binary: np.ndarray, max_area: int = 5) -> np.ndarray:
    """
    Removes isolated black speckles (noise) from a binary image (background 255, text 0).
    Uses OpenCV connected components analysis to find small objects.
    """
    # Invert image to make text/speckles white (255) and background black (0)
    inverted = 255 - image_binary
    
    # Find connected components
    num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(inverted, connectivity=8)
    
    # Identify and collect pixels belonging to small elements (noise components)
    noise_mask = np.zeros_like(inverted)
    for i in range(1, num_labels):
        area = stats[i, cv2.CC_STAT_AREA]
        if area <= max_area:
            noise_mask[labels == i] = 255
            
    # Clean those noise pixels by setting them to white (255) in the output image
    cleaned = image_binary.copy()
    cleaned[noise_mask == 255] = 255
    return cleaned

def clean_margin_shadows(image_binary: np.ndarray, margin_percent: float = 3.5) -> np.ndarray:
    """
    Fills document margins/borders with white pixels to eliminate border/scanner shadow noise.
    """
    h, w = image_binary.shape[:2]
    margin_x = int(w * (margin_percent / 100.0))
    margin_y = int(h * (margin_percent / 100.0))
    
    cleaned = image_binary.copy()
    # Fill border margins with white background
    cleaned[0:margin_y, :] = 255
    cleaned[h-margin_y:h, :] = 255
    cleaned[:, 0:margin_x] = 255
    cleaned[:, w-margin_x:w] = 255
    
    return cleaned

