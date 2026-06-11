# Mountmind PeakOCR Studio - Comprehensive Technical Guide 🏔️

This guide provides an exhaustive technical breakdown of **Mountmind PeakOCR Studio**. It describes the role of each script, the mathematical formulations under the hood, the dataset generation logic, and the interactive web visualizer. Use this guide to understand, study, and explain the codebase for research or interview preparation.

---

## 🗺️ Project Architecture & File Roles

```text
├── README.md                  # High-level developer entry point for GitHub
├── PROJECT_GUIDE.md           # This exhaustive documentation file
├── firebase.json              # Firebase Hosting configuration
├── .firebaserc                # Active Firebase target project ("mountmind-peak-ocr-studio")
├── .gitignore                 # Excludes python caches, venvs, and generated datasets from git tracking
├── src/                       # Backend pipelines (Python)
│   ├── preprocess.py          # Image processing: deskewing, bilateral denoise, adaptive binarization, projection lines
│   ├── synthetic_generator.py # Devanagari canvas rendering & distorted text image synthesis
│   ├── generate_hf_dataset.py # Automated ImageFolder datasets builder with custom CLI arguments
│   ├── upload_to_hf.py        # Programmatic Hugging Face Hub dataset uploader via HfApi
│   ├── upload_to_github.py    # Auto Git initializer & GitHub remote creation uploader
│   └── main.py                # Command Line visual comparisons runner
└── web/                       # Front-end workspace (Vanilla HTML, CSS, JavaScript)
    ├── index.html             # UI containing the visualizer slider and synthetic data gen controls
    ├── app.js                 # Frontend routing, regex section parser, & live COCO JSON renderer
    └── style.css              # Glassmorphic premium dark-mode styling
```

---

## 🔍 Pipeline 1: Scanned Document Preprocessing & Layout Analysis (`src/preprocess.py`)

Historical papers, scanner noise, and faded inks make text recognition difficult. This pipeline applies computer vision techniques using OpenCV and NumPy to restore and segment document scans.

### Step 1: Color Space Conversions
*   **BGR to RGB**: OpenCV loads images in Blue-Green-Red layout by default. We convert it to Red-Green-Blue (RGB) for correct display color spaces in matplotlib and standard libraries.
*   **Grayscale Conversion**: Eliminates chrominance channels to reduce multi-dimensional matrix operations. The luminosity formula is applied:
    $$Y = 0.299 \cdot R + 0.587 \cdot G + 0.114 \cdot B$$

### Step 2: Hough Line Deskewing (Auto-Alignment)
Scanned documents often have minor rotation errors. We align them using:
1.  **Canny Edge Detection**: Identifies sharp local intensity gradients.
2.  **Hough Line Transform**: Maps edge coordinates $(x, y)$ in the cartesian plane to curves in the polar parameter space $(\theta, \rho)$:
    $$\rho = x \cos \theta + y \sin \theta$$
    Where $\theta$ is the angle of the normal from the origin and $\rho$ is the distance. The intersections in parameter space reveal dominant straight lines (representing paragraph baseline grids).
3.  **Rotation Affine Matrix**: The average skew angle $\theta_{\text{skew}}$ is calculated. We construct a 2D rotation affine transformation matrix $M$ around the image center $(x_c, y_c)$:
    $$M = \begin{bmatrix} \alpha & \beta & (1-\alpha)x_c - \beta y_c \\ -\beta & \alpha & \beta x_c + (1-\alpha)y_c \end{bmatrix}$$
    Where $\alpha = \cos \theta_{\text{skew}}$ and $\beta = \sin \theta_{\text{skew}}$. We warp the image to restore horizontal text baseline coordinates.

### Step 3: Bilateral Filtering (Edge-Preserving Denoise)
Standard filters (e.g., Gaussian Blur) smooth out scanner noise by averaging pixel neighborhoods, which blurs the sharp boundaries of characters. We apply a **Bilateral Filter** that averages pixels based on both spatial distance and intensity similarity:
$$I^{\text{filtered}}(x) = \frac{1}{W_p} \sum_{x_i \in \Omega} I(x_i) f_r(\|I(x_i) - I(x)\|) g_s(\|x_i - x\|)$$
*   $g_s$: Spatial kernel (Gaussian distribution of distance $\|x_i - x\|$).
*   $f_r$: Range kernel (Gaussian distribution of intensity differences $\|I(x_i) - I(x)\|$).
This preserves character strokes (high intensity difference) while smoothing out paper background fiber noise (low intensity differences).

### Step 4: Local Adaptive Thresholding (Adaptive Binarization)
Uneven room lighting or page bends create gradients of shadows across a document. A global threshold (e.g., Otsu's binarization) would turn shadowed portions completely black. 

We resolve this by calculating a local threshold $T(x,y)$ for every pixel dynamically based on a Gaussian-weighted sum of its local $11 \times 11$ pixel block neighborhood, offset by a constant $C = 2$:
$$T(x, y) = \text{Mean}_{\text{local}}(x, y) - C$$
*   If $\text{Pixel}(x,y) < T(x,y)$, it is set to $0$ (Black / Ink).
*   If $\text{Pixel}(x,y) \geq T(x,y)$, it is set to $255$ (White / Background).

### Step 5: Speckle Noise Filtering (Despeckling)
Small ink splatters, mold, or scanner dust form tiny black islands. We scan the binarized image to detect all connected pixel components.
*   If the area of a component is less than $5$ pixels, it is classified as speckle noise.
*   The system wipes it by overwriting those coordinates to $255$ (White).

### Step 6: Margin shadow Erasure
Old paper sheets often have dark, wrinkled outer edges or scanner boundary shadows. We blank a configurable boundary border margin (defaulting to $3.5\%$ of width and height) to white, preventing false character detections at the margins.

### Step 7: Layout Segmentation using Projection Profiles
To crop lines of text automatically:
1.  **Horizontal Projection Profile (HPP)**: Sums black pixels horizontally along each row $y$:
    $$\text{HPP}(y) = \sum_{x=0}^{\text{Width}} (255 - \text{Image}(x, y))$$
2.  **Valley Cutting**: High $\text{HPP}(y)$ indicates text presence; valleys ($\text{HPP}(y) \approx 0$) represent row spacing. We segment lines at these valleys.
3.  **Vertical Projection Profile (VPP)**: Applied within segmented rows to separate individual words:
    $$\text{VPP}(x) = \sum_{y=y_{\text{start}}}^{y_{\text{end}}} (255 - \text{Image}(x, y))$$
    We segment words at the zero-valleys of $\text{VPP}(x)$ to compute coordinates and crops.

---

## ✍️ Pipeline 2: Synthetic Devanagari OCR Corpus Builder (`src/synthetic_generator.py` & `src/generate_hf_dataset.py`)

Training deep learning models like TrOCR (Vision Transformers) or CRNN (CNN+LSTM+CTC) requires thousands of images with ground truth transcriptions. The synthetic generator builds this training set programmatically.

### Step 1: Text Line Rendering
A phrase is generated by combining administrative dictionary arrays (Ministries, locations, document ID formats, and Nepali dates). Using Pillow's `ImageDraw.text()`, the script renders the text using system-available Devanagari TrueType/OpenType fonts (`Arial Unicode.ttf` or `Sanskrit2003.ttf`).

### Step 2: Scan Artifact Distortions
To make the synthetic images mimic real physical document conditions, several distortions are applied:
*   **Shadow Vignette Vignetting**: Blends a dark gradient overlay dynamically to simulate uneven overhead light conditions:
    $$\text{Vignette}(x) = I(x) \times \left(1 - \frac{x}{\text{width}} \cdot \text{shadow\_pct}\right)$$
*   **Rotational Skew**: Spans a rotational coordinate transform matrix to rotate the canvas randomly within $[-4.0^{\circ}, +4.0^{\circ}]$.
*   **Gaussian Ink Bleed**: Applies a mild Gaussian Blur to simulate how ink bleeds and dilutes along porous organic paper fibers.
*   **Salt & Pepper Noise**: Iterates random pixel indexes to solid white or solid black to replicate scanner dust.

### Step 3: Word Bounding Box Geometry
The script calculates the bounding boxes of individual words:
1.  Measures the estimated width per character based on text rendering spans.
2.  Slices coordinate offsets using the spaces between words.
3.  Outputs coordinates in **COCO JSON Format** (`[x, y, width, height]`) and **YOLO format** (relative normalized center coordinates).

---

## 💻 Pipeline 3: Frontend Interactive Visualizer (`web/`)

Provides an interface for testing, configuring, and verifying results.

### real-time Comparison Slider
Allows users to upload their own images, rendering the processed binarized image side-by-side with a drag-slider split.

### Intelligent Document Restructurer (Section Parser in `app.js`)
When raw OCR output is fetched (which is often unstructured text), the app uses a rule-based parser (`parseDocumentSections(text)`) to identify sections of standard Nepali government letters:
1.  **Letterhead**: Text containing administrative entities (`नेपाल सरकार`, `मन्त्रालय`, `विभाग`).
2.  **Metadata**: Finds lines containing dates (`मितिः`) or letter tracking reference IDs (`पत्र संख्या`, `चलानी नम्बर`, `च.नं.`) and parses them into styled chips.
3.  **Subject**: Matches patterns starting with `विषय:`.
4.  **Body**: Extracts general text blocks as paragraph chunks.
5.  **Signature**: Detects names, designations, and signoff text (`भवदीय`, `शाखा अधिकृत`, `सचिव`) and positions them in a signature block on the bottom right.

### Dynamic JSON Syntax Highlighter
Renders the generated COCO JSON annotations. To make it human-readable, `app.js` runs a regex formatter that tokenizes the JSON string and wraps components in color-coded spans:
*   **Keys**: Blue (`#93c5fd`)
*   **String Values**: Green (`#86efac`)
*   **Numeric Values**: Amber (`#fcd34d`)

---

## 🚀 Deployment & Open-Source Publishing Workflow

### 1. Codebase Control (Git & GitHub)
The project includes automated script commands to publish code. `upload_to_github.py` performs the following steps:
1.  Sets up a `.gitignore` to exclude large generated datasets and Python build caches.
2.  Initializes local Git control: `git init -b main`.
3.  Stages and commits files.
4.  Calls the **GitHub REST API** via an authorized personal access token (`ghp_...`) to register the remote repository `nepali-ocr-studio`.
5.  Pushes the code to `https://github.com/prashant0919/nepali-ocr-studio`.

### 2. Dataset Publishing (Hugging Face Hub)
`upload_to_hf.py` connects to Hugging Face Hub using your token (`hf_...`):
1.  Creates a dataset repository `prashant0919/nepali-synthetic-ocr-lines`.
2.  Uploads the generated `dataset/` folder containing splits (`train/` and `test/`) along with `metadata.jsonl` files mapping image files to their ground truth text.
3.  Creates a dataset card `README.md` containing YAML metadata front matter, making the dataset immediately indexable on Hugging Face:
    ```yaml
    task_categories:
    - image-to-text
    tags:
    - ocr
    - htr
    - devanagari
    - nepali
    - synthetic
    language:
    - ne
    ```

### 3. Static Web Application (Firebase)
The frontend playground is deployed live using **Firebase Hosting**.
*   `firebase.json` points `"public": "web"`.
*   `.firebaserc` binds the deployment targets to the project ID `mountmind-peak-ocr-studio`.
*   Deployed globally using `firebase deploy --only hosting` to make the workspace live at [mountmind-peak-ocr-studio.web.app](https://mountmind-peak-ocr-studio.web.app).
