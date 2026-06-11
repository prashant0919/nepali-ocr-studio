"""
Mountmind PeakOCR - Devanagari CRNN + CTC Sequence Model Trainer
Implements a complete training pipeline for Handwritten Text Recognition (HTR) 
using PyTorch, Convolutional Recurrent Neural Network (CRNN), and CTC Loss.
"""

import os
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
import numpy as np

# Vocabulary Definition for Devanagari Script (Consonants, Vowels, Conjuncts, Diacritics)
DEVANAGARI_VOCAB = [
    '-',  # CTC blank token (index 0)
    ' ', '।', '०', '१', '२', '३', '४', '५', '६', '७', '८', '९',
    'अ', 'आ', 'इ', 'ई', 'उ', 'ऊ', 'ऋ', 'ए', 'ऐ', 'ओ', 'औ', 'अं', 'अः',
    'क', 'ख', 'ग', 'घ', 'ङ', 'च', 'छ', 'ज', 'झ', 'ञ', 'ट', 'ठ', 'ड', 'ढ', 'ण',
    'त', 'थ', 'द', 'ध', 'न', 'प', 'फ', 'ब', 'भ', 'म', 'य', 'र', 'ल', 'व', 'श', 'ष', 'स', 'ह',
    'ा', 'ि', 'ी', 'ु', 'ू', 'ृ', 'े', 'ै', 'ो', 'ौ', '्', 'ं', 'ः'
]
VOCAB_SIZE = len(DEVANAGARI_VOCAB)
CHAR_TO_INDEX = {char: idx for idx, char in enumerate(DEVANAGARI_VOCAB)}
INDEX_TO_CHAR = {idx: char for idx, char in enumerate(DEVANAGARI_VOCAB)}

# --- 1. CRNN Model Architecture ---
class CRNN(nn.Module):
    def __init__(self, img_channel=1, num_classes=VOCAB_SIZE, hidden_size=256):
        super(CRNN, self).__init__()
        
        # Convolutional Feature Extractor (VGG-like CNN block)
        self.cnn = nn.Sequential(
            # Conv block 1
            nn.Conv2d(img_channel, 64, kernel_size=3, stride=1, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(kernel_size=2, stride=2),  # Output H/2, W/2
            
            # Conv block 2
            nn.Conv2d(64, 128, kernel_size=3, stride=1, padding=1),
            nn.BatchNorm2d(128),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(kernel_size=2, stride=2),  # Output H/4, W/4
            
            # Conv block 3
            nn.Conv2d(128, 256, kernel_size=3, stride=1, padding=1),
            nn.BatchNorm2d(256),
            nn.ReLU(inplace=True),
            # Maxpool with non-symmetric strides to preserve horizontal width for text
            nn.MaxPool2d(kernel_size=(2, 1), stride=(2, 1)),  # Output H/8, W/4
            
            # Conv block 4
            nn.Conv2d(256, 512, kernel_size=3, stride=1, padding=1),
            nn.BatchNorm2d(512),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(kernel_size=(2, 1), stride=(2, 1)),  # Output H/16, W/4
            
            # Conv block 5 (squeeze height to 1)
            nn.Conv2d(512, 512, kernel_size=2, stride=1, padding=0),
            nn.BatchNorm2d(512),
            nn.ReLU(inplace=True)  # Final Output Shape: (512, 1, SeqLen)
        )
        
        # Recurrent Sequence Modeler (Bidirectional LSTM)
        self.rnn = nn.Sequential(
            BidirectionalLSTM(512, hidden_size, hidden_size),
            BidirectionalLSTM(hidden_size, hidden_size, num_classes)
        )
        
    def forward(self, x):
        # Input shape: [Batch, Channels, Height (e.g. 32), Width (e.g. 256)]
        features = self.cnn(x)
        
        # Reshape for sequence: squeeze height dimension and transpose
        # Features shape: [Batch, Channels (512), Height (1), Width (SeqLen)]
        features = features.squeeze(2)  # Shape: [Batch, Channels, SeqLen]
        features = features.permute(2, 0, 1)  # Shape: [SeqLen, Batch, Channels]
        
        # Recurrent classification output
        out = self.rnn(features)  # Shape: [SeqLen, Batch, NumClasses]
        return out


class BidirectionalLSTM(nn.Module):
    def __init__(self, input_size, hidden_size, output_size):
        super(BidirectionalLSTM, self).__init__()
        self.lstm = nn.LSTM(input_size, hidden_size, bidirectional=True)
        self.linear = nn.Linear(hidden_size * 2, output_size)
        
    def forward(self, x):
        recurrent, _ = self.lstm(x)
        T, B, H = recurrent.size()
        t_rec = recurrent.view(T * B, H)
        output = self.linear(t_rec)  # [T * B, output_size]
        output = output.view(T, B, -1)
        return output

# --- 2. HTR Simulated Dataset for Instant Execution ---
class DevanagariHTRDataset(Dataset):
    """
    Mock dataset that generates synthetic handwritten textline-like arrays 
    to enable instant validation of the training script.
    """
    def __init__(self, size=100, img_height=32, img_width=256):
        self.size = size
        self.img_height = img_height
        self.img_width = img_width
        
        # Preset labels representing handwritten phrases mapped to indices dynamically
        raw_phrases = [
            "नेपाल सरकार गृह मन्त्रालय",
            "सिंहदरबार काठमाण्डौं",
            "परराष्ट्र मन्त्रालय सम्बद्ध"
        ]
        self.samples = []
        for text in raw_phrases:
            indices = [CHAR_TO_INDEX[c] for c in text if c in CHAR_TO_INDEX]
            self.samples.append((text, indices))
        
    def __len__(self):
        return self.size
        
    def __getitem__(self, idx):
        # Retrieve sample
        text, label = self.samples[idx % len(self.samples)]
        
        # Generate mock text image (background noise + character strokes)
        img = np.random.normal(240, 5, (self.img_height, self.img_width)).astype(np.float32)
        # Simulate simple word stroke lines
        for offset in range(30, 220, 15):
            h_start = 8 + np.random.randint(-2, 3)
            h_end = 24 + np.random.randint(-2, 3)
            img[h_start:h_end, offset:offset+4] = np.random.normal(50, 10, (h_end-h_start, 4))
            # draw shirorekha head line
            img[8:10, offset-2:offset+12] = 40
            
        img = (img / 255.0) - 0.5  # Normalize [-0.5, 0.5]
        img_tensor = torch.tensor(img).unsqueeze(0)  # Shape: [1, Height, Width]
        
        label_tensor = torch.tensor(label, dtype=torch.long)
        label_length = torch.tensor(len(label), dtype=torch.long)
        
        return img_tensor, label_tensor, label_length

# --- 3. CTC Decoder Helper ---
def decode_predictions(preds, vocab=INDEX_TO_CHAR):
    """
    Decodes predictions using CTC greedy decoder (best path).
    """
    # Preds shape: [SeqLen, Batch, NumClasses]
    preds = preds.argmax(dim=2)  # [SeqLen, Batch]
    preds = preds.transpose(0, 1)  # [Batch, SeqLen]
    
    decoded_texts = []
    for batch_idx in range(preds.size(0)):
        char_list = []
        prev_idx = -1
        for t in range(preds.size(1)):
            idx = preds[batch_idx, t].item()
            if idx != 0 and idx != prev_idx:  # Skip blank and repeated tokens
                char_list.append(vocab[idx])
            prev_idx = idx
        decoded_texts.append("".join(char_list))
    return decoded_texts

# --- 4. Levenshtein Metrics (CER/WER) ---
def compute_levenshtein(s1, s2):
    if len(s1) < len(s2):
        return compute_levenshtein(s2, s1)
    if len(s2) == 0:
        return len(s1)
        
    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
        
    return previous_row[-1]

# --- 5. Main Training Run Simulator ---
def train_htr_model(epochs=3):
    print("=" * 60)
    print("      PyTorch CRNN + CTC Sequence Model Trainer Initializing")
    print("=" * 60)
    
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"[*] Running training execution on target device: {device}")
    
    # Initialize mock datasets
    train_dataset = DevanagariHTRDataset(size=90)
    val_dataset = DevanagariHTRDataset(size=15)
    
    # Dataloaders (with custom collate for variable length labels)
    def collate_fn(batch):
        images, labels, label_lengths = zip(*batch)
        images = torch.stack(images, 0)
        label_lengths = torch.stack(label_lengths, 0)
        
        # Pad labels to same length for tensor loading
        flat_labels = torch.cat(labels, 0)
        return images, flat_labels, label_lengths

    train_loader = DataLoader(train_dataset, batch_size=8, shuffle=True, collate_fn=collate_fn)
    val_loader = DataLoader(val_dataset, batch_size=8, shuffle=False, collate_fn=collate_fn)
    
    # Instantiate CRNN Network model
    model = CRNN().to(device)
    
    # Define CTC Loss & Optimizer (AdamW standard)
    criterion = nn.CTCLoss(blank=0, zero_infinity=True).to(device)
    optimizer = optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-4)
    
    print(f"[*] Network instantiated successfully. Total Param Count: {sum(p.numel() for p in model.parameters()):,}")
    print("[*] Starting training loops...")
    
    for epoch in range(1, epochs + 1):
        model.train()
        train_loss = 0.0
        
        for images, targets, target_lengths in train_loader:
            images = images.to(device)
            batch_size = images.size(0)
            
            optimizer.zero_grad()
            
            # Forward pass: outputs size [SeqLen, Batch, NumClasses]
            preds = model(images)
            
            # Calculate input lengths for CTC (matching CNN spatial dimensions squeeze)
            input_lengths = torch.full(size=(batch_size,), fill_value=preds.size(0), dtype=torch.long).to(device)
            
            # Compute CTC Loss
            loss = criterion(preds, targets.to(device), input_lengths, target_lengths.to(device))
            
            # Backward pass & Optimize
            loss.backward()
            optimizer.step()
            
            train_loss += loss.item() * batch_size
            
        epoch_loss = train_loss / len(train_dataset)
        
        # Validation evaluation loop
        model.eval()
        val_loss = 0.0
        total_chars = 0
        char_errors = 0
        
        with torch.no_grad():
            for images, targets, target_lengths in val_loader:
                images = images.to(device)
                batch_size = images.size(0)
                preds = model(images)
                
                input_lengths = torch.full(size=(batch_size,), fill_value=preds.size(0), dtype=torch.long).to(device)
                loss = criterion(preds, targets.to(device), input_lengths, target_lengths.to(device))
                val_loss += loss.item() * batch_size
                
                # Decode predictions for CER
                decoded = decode_predictions(preds)
                
                # Unflatten target indices back to list of target text strings
                target_idx = 0
                for i in range(batch_size):
                    length = target_lengths[i].item()
                    label_indices = targets[target_idx : target_idx + length].tolist()
                    target_idx += length
                    
                    target_text = "".join([INDEX_TO_CHAR[idx] for idx in label_indices])
                    predicted_text = decoded[i]
                    
                    # Compute distance
                    char_errors += compute_levenshtein(predicted_text, target_text)
                    total_chars += len(target_text)
                    
        val_loss = val_loss / len(val_dataset)
        cer = (char_errors / total_chars) * 100 if total_chars > 0 else 100.0
        
        print(f"Epoch {epoch:02d}/{epochs:02d} - Train Loss: {epoch_loss:.4f} - Val Loss: {val_loss:.4f} - Val CER: {cer:.2f}%")
        
    print("\n" + "=" * 60)
    print("      CRNN + CTC Sequence Model Trainer Finished!")
    print("=" * 60 + "\n")

if __name__ == "__main__":
    train_htr_model(epochs=3)
