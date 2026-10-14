import os
import sys
import csv
import json
import time
from collections import Counter
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import TensorDataset, DataLoader
from PIL import Image
import torchvision.models as models
import torchvision.transforms as transforms

# Base paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TASK_4_DIR = os.path.join(BASE_DIR, "data", "FAI_Product_Challange", "TASK_4")
CSV_PATH = os.path.join(TASK_4_DIR, "Ground_Truth_Points", "Ground_truth_Points.csv")
IMG_DIR = os.path.join(TASK_4_DIR, "Images", "images")
WEIGHTS_DIR = os.path.join(BASE_DIR, "farmsync", "vision", "weights")
os.makedirs(WEIGHTS_DIR, exist_ok=True)

# Standardized Class Dictionaries
CROP_CLASSES = [
    "Rice (Paddy)",
    "Coconut",
    "Maize",
    "Sugarcane",
    "Banana",
    "Sorghum",
    "Cassava",
    "Marigold",
    "Cotton",
    "Groundnut",
    "Mango"
]

STAGE_CLASSES = [
    "vegetation",
    "full_growth",
    "sown",
    "harvesting",
    "flowering"
]

CROP_TO_IDX = {c: i for i, c in enumerate(CROP_CLASSES)}
STAGE_TO_IDX = {s: i for i, s in enumerate(STAGE_CLASSES)}

def normalize_crop_name(raw_name: str) -> str:
    r = raw_name.strip()
    if "Fodder Sorghum" in r or "Sorghum" in r:
        return "Sorghum"
    if "Cotton" in r:
        return "Cotton"
    for c in CROP_CLASSES:
        if c.lower() in r.lower():
            return c
    return "Rice (Paddy)"

def normalize_stage_name(raw_stage: str) -> str:
    r = raw_stage.strip().lower()
    for s in STAGE_CLASSES:
        if s in r:
            return s
    return "vegetation"

class MultiTaskCropNet(nn.Module):
    """Production Multi-Task Crop and Stage Perception Network."""
    def __init__(self, num_crops=len(CROP_CLASSES), num_stages=len(STAGE_CLASSES)):
        super().__init__()
        self.crop_head = nn.Sequential(
            nn.Linear(576, 128),
            nn.BatchNorm1d(128),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(128, num_crops)
        )
        self.stage_head = nn.Sequential(
            nn.Linear(576, 64),
            nn.BatchNorm1d(64),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(64, num_stages)
        )

    def forward(self, feat):
        crop_logits = self.crop_head(feat)
        stage_logits = self.stage_head(feat)
        return crop_logits, stage_logits

def train():
    print("=" * 60)
    print("FARMSYNC Task 4: Training Genuine Crop Intelligence Model")
    print("=" * 60)

    # 1. Map labeled images from CSV
    print(f"Reading ground truth annotations from: {CSV_PATH}")
    disk_files = set(os.listdir(IMG_DIR))
    labeled_samples = []

    with open(CSV_PATH, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            key = row.get("image_path", "").strip()
            raw_c = row.get("final_crop_name", "").strip()
            raw_s = row.get("final_crop_stage", "").strip()
            if not key or not raw_c:
                continue

            c = normalize_crop_name(raw_c)
            s = normalize_stage_name(raw_s)

            # Match on disk
            for df in disk_files:
                if key in df:
                    labeled_samples.append({
                        "filename": df,
                        "path": os.path.join(IMG_DIR, df),
                        "crop_idx": CROP_TO_IDX[c],
                        "stage_idx": STAGE_TO_IDX[s],
                        "crop_name": c,
                        "stage_name": s
                    })
                    break

    # Deduplicate by filename
    unique_samples = {}
    for item in labeled_samples:
        if item["filename"] not in unique_samples:
            unique_samples[item["filename"]] = item
    samples = list(unique_samples.values())
    print(f"Indexed {len(samples)} unique verified field images with ground truth labels.")

    # 2. Extract features with MobileNetV3-Small backbone
    print("Extracting 576-dim feature vectors with MobileNetV3-Small...")
    mobilenet = models.mobilenet_v3_small(weights=models.MobileNet_V3_Small_Weights.DEFAULT)
    mobilenet.eval()
    features_extractor = mobilenet.features
    avgpool = mobilenet.avgpool

    transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])

    X_list = []
    y_crop_list = []
    y_stage_list = []

    t0 = time.time()
    batch_size = 64
    for i in range(0, len(samples), batch_size):
        batch_samples = samples[i:i+batch_size]
        batch_tensors = []
        for s in batch_samples:
            try:
                img = Image.open(s["path"]).convert("RGB")
                batch_tensors.append(transform(img))
            except Exception as e:
                pass
        
        if not batch_tensors:
            continue
        
        inp = torch.stack(batch_tensors)
        with torch.no_grad():
            feat = avgpool(features_extractor(inp))
            feat = torch.flatten(feat, 1)
            X_list.append(feat.cpu())
            for s in batch_samples:
                y_crop_list.append(s["crop_idx"])
                y_stage_list.append(s["stage_idx"])

        if (i // batch_size) % 10 == 0:
            print(f"  Processed {min(i+batch_size, len(samples))}/{len(samples)} images (Elapsed: {time.time()-t0:.1f}s)")

    X = torch.cat(X_list, dim=0)
    y_crop = torch.tensor(y_crop_list, dtype=torch.long)
    y_stage = torch.tensor(y_stage_list, dtype=torch.long)
    print(f"Feature tensor shape: {X.shape}, Crop labels: {y_crop.shape}, Stage labels: {y_stage.shape}")

    # 3. Train/Val Split (85% Train, 15% Val)
    indices = np.random.RandomState(42).permutation(len(X))
    split = int(0.85 * len(X))
    train_idx, val_idx = indices[:split], indices[split:]

    X_train, y_c_train, y_s_train = X[train_idx], y_crop[train_idx], y_stage[train_idx]
    X_val, y_c_val, y_s_val = X[val_idx], y_crop[val_idx], y_stage[val_idx]

    train_ds = TensorDataset(X_train, y_c_train, y_s_train)
    val_ds = TensorDataset(X_val, y_c_val, y_s_val)

    train_loader = DataLoader(train_ds, batch_size=64, shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=64, shuffle=False)

    # 4. Class Weighting to balance common and rare crops
    crop_counts = Counter(y_c_train.numpy())
    total_crops = len(y_c_train)
    crop_weights = [total_crops / (len(CROP_CLASSES) * max(crop_counts[i], 1)) for i in range(len(CROP_CLASSES))]
    crop_weights_t = torch.tensor(crop_weights, dtype=torch.float32)

    model = MultiTaskCropNet(num_crops=len(CROP_CLASSES), num_stages=len(STAGE_CLASSES))
    criterion_crop = nn.CrossEntropyLoss(weight=crop_weights_t)
    criterion_stage = nn.CrossEntropyLoss()
    optimizer = optim.AdamW(model.parameters(), lr=0.003, weight_decay=1e-4)
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=25)

    print("\nTraining MultiTaskCropNet for 25 Epochs...")
    best_val_acc = 0.0
    best_state = None

    for epoch in range(1, 26):
        model.train()
        train_loss = 0.0
        for bx, by_c, by_s in train_loader:
            optimizer.zero_grad()
            out_c, out_s = model(bx)
            loss = criterion_crop(out_c, by_c) + 0.8 * criterion_stage(out_s, by_s)
            loss.backward()
            optimizer.step()
            train_loss += loss.item()
        scheduler.step()

        # Validation
        model.eval()
        correct_c = 0
        correct_s = 0
        total = 0
        with torch.no_grad():
            for vx, vy_c, vy_s in val_loader:
                vc, vs = model(vx)
                pred_c = torch.argmax(vc, dim=1)
                pred_s = torch.argmax(vs, dim=1)
                correct_c += (pred_c == vy_c).sum().item()
                correct_s += (pred_s == vy_s).sum().item()
                total += len(vx)

        crop_acc = (correct_c / total) * 100
        stage_acc = (correct_s / total) * 100
        if (epoch % 5 == 0) or (epoch == 25):
            print(f"  Epoch {epoch:02d}/25 | Loss: {train_loss/len(train_loader):.4f} | Val Crop Acc: {crop_acc:.1f}% | Val Stage Acc: {stage_acc:.1f}%")

        if crop_acc > best_val_acc:
            best_val_acc = crop_acc
            best_state = model.state_dict()

    # 5. Save model checkpoint and labels
    model_path = os.path.join(WEIGHTS_DIR, "crop_model.pth")
    torch.save(best_state or model.state_dict(), model_path)
    print(f"\nSaved trained model weights to: {model_path}")

    meta = {
        "crop_classes": CROP_CLASSES,
        "stage_classes": STAGE_CLASSES,
        "best_val_crop_accuracy_pct": round(best_val_acc, 2),
        "total_training_samples": len(samples),
        "backbone": "mobilenet_v3_small",
        "feature_dim": 576,
        "trained_timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    meta_path = os.path.join(WEIGHTS_DIR, "classes.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
    print(f"Saved model metadata to: {meta_path}")
    print("=" * 60)
    print("TRAINING COMPLETE: Production Crop Intelligence Model Ready!")
    print("=" * 60)

if __name__ == "__main__":
    train()
