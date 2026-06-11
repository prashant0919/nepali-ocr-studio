# Mountmind PeakOCR Studio 🏔️

**Mountmind PeakOCR Studio** is an open-source interactive workspace, preprocessing pipeline, and synthetic corpus generator for **Nepali and Devanagari script OCR/HTR (Handwritten Text Recognition)**. 

It is designed to solve the physical deterioration challenges of historical and scanned documents by providing a high-fidelity interactive quality visualizer and a dataset building pipeline for modern deep learning models (CRNN, TrOCR, PaddleOCR, YOLOv8).

---

## 🌐 Live Deployments & Datasets

*   **Interactive Web Playground**: [mountmind-peak-ocr-studio.web.app](https://mountmind-peak-ocr-studio.web.app) (Hosted on Firebase)
*   **Open-Source Training Dataset**: [Hugging Face Datasets - nepali-synthetic-ocr-lines](https://huggingface.co/datasets/prashant0919/nepali-synthetic-ocr-lines)

---

## 🚀 Key Features

### 1. Advanced Image Preprocessing Pipeline
To maximize OCR accuracy, physical scans undergo several cleaning stages implemented in OpenCV (`src/preprocess.py`):
*   **Deskewing (Hough Lines)**: Detects text-line skew angles automatically and applies affine rotation transforms to re-align documents.
*   **Edge-Preserving Denoising**: Uses bilateral filtering to smooth out background noise/paper grain while preserving high-contrast character edges.
*   **Local Adaptive Binarization**: Converts color/grayscale scans to clean binary (black-and-white) sheets, adapting to uneven lighting and shadow artifacts.
*   **Speckle & Margin shadow Removal**: Cleans scan boundaries and tiny ink stains.

### 2. Document Layout & Text Line Segmentation
Uses horizontal and vertical projection profiles:
$$\text{Profile}(y) = \sum_{x} \text{PixelValue}(x, y)$$
to detect character density lines, drawing bounding boxes around individual sentences and paragraph lines for training dataset crop generation.

### 3. Intelligent Nepali Document Parser
Parses text blocks into standard Nepali official letter segments (Letterhead, metadata chips like पत्र संख्या / च.नं. / मिति, Subject lines, Body paragraphs, and Signatures) to reconstruct unstructured OCR outputs into structured digital documents.

### 4. Synthetic OCR Corpus Generator
Generates distorted text line images and matches them to standard layout coordinates for training deep learning models:
*   Generates word-level coordinates in **COCO Bounding Box format** and **YOLO format**.
*   Simulates real-world scan conditions (ink bleeding, random skew angle, Gaussian blur, salt & pepper scanner noise, shadow vignetting).
*   Exportable to Hugging Face **ImageFolder** datasets.

---

## 📂 Project Architecture

```text
├── README.md               # You are here
├── firebase.json           # Firebase Hosting configuration
├── src/                    # Backend Image Processing & Script Pipelines
│   ├── preprocess.py       # OpenCV Hough lines deskew, bilateral filter, projection profile segmentation
│   ├── synthetic_generator.py # Distorts text lines & generates word-level COCO/YOLO bboxes
│   ├── generate_hf_dataset.py # Generates train/test split dataset folders with metadata.jsonl
│   ├── upload_to_hf.py     # Programmatic uploader to Hugging Face Hub
│   └── main.py             # CLI runner to process local sample images
└── web/                    # Frontend Interactive Playground (HTML, CSS, JS)
    ├── index.html          # Dual workspace: Visual Playground + Data Gen studio
    ├── app.js              # Tab switcher, dynamic COCO syntax highlighter, structured renderer
    └── style.css           # Premium dark-mode workspace layout
```

---

## 🛠️ Getting Started

### 1. Installation & Environment Setup
Clone the repository:
```bash
git clone https://github.com/prashant0919/nepali-ocr-studio.git
cd nepali-ocr-studio
```

Set up a virtual environment and install Python dependencies:
```bash
python3 -m venv venv
source venv/bin/activate
pip install opencv-python pillow numpy matplotlib huggingface_hub
```

### 2. Run the Preprocessing Pipeline CLI
Process a sample image to test binarization and line segmentation:
```bash
python3 src/main.py
```
Output comparison plots and line crops will be saved to the `outputs/` directory.

### 3. Generate Hugging Face Format Dataset
To compile a dataset of 150 training lines and 30 test lines with randomized scan distortions:
```bash
python3 src/generate_hf_dataset.py
```
This writes images and their `metadata.jsonl` mappings under the `dataset/` directory.

### 4. Run the Web Interface Locally
To launch the interactive visual playground:
```bash
cd web
python3 -m http.server 8000
```
Open [http://localhost:8000](http://localhost:8000) in your browser.

---

## 🤝 Contributing

Contributions are welcome! Please open an issue or submit a pull request for:
1. Additional Devanagari handwriting font styles for the synthetic generator.
2. Layout parsing heuristics for other administrative document formats.
3. Fine-tuning notebooks for models like TrOCR or EasyOCR.
