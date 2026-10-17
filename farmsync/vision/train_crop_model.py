import os
import sys
import csv
import json
import time
from collections import Counter
import numpy as np
from PIL import Image
try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    from torch.utils.data import TensorDataset, DataLoader
    import torchvision.models as models
    import torchvision.transforms as transforms
    TORCH_AVAILABLE = True
except ImportError:
    torch = None
    nn = None
    optim = None
    TensorDataset = None
    DataLoader = None
    models = None
    transforms = None
    TORCH_AVAILABLE = False

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
    return None

def normalize_stage_name(raw_stage: str) -> str:
    r = raw_stage.strip().lower()
    for s in STAGE_CLASSES:
        if s in r:
            return s
    return None

if TORCH_AVAILABLE and nn is not None:
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
else:
    class MultiTaskCropNet:
        """Stub class for environments without PyTorch installed."""
        def __init__(self, *args, **kwargs):
            pass

def train():
    """Use the grouped train/validation/test pipeline; --promote is explicit."""
    from scripts.evaluate_models import main
    main()


if __name__ == "__main__":
    train()
