"""Reproducible supplied-data validation of a newly trained crop/stage head.

No independent field-test accuracy is implied. Model selection/calibration use
validation groups; final metrics use separate supplied-data test groups.
"""
import argparse
import copy
import csv
from hashlib import sha256
import json
import os
from pathlib import Path
import random
import shutil
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def labels(crop, stage, crops, stages):
    crop = crop.strip().casefold()
    stage = stage.strip().casefold()
    normalized = next((c for c in crops if c.casefold() in crop), None)
    if "sorghum" in crop: normalized = "Sorghum"
    if "cotton" in crop: normalized = "Cotton"
    if crop in {"rice", "paddy"}: normalized = "Rice (Paddy)"
    return normalized, stage if stage in stages else None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--promote", action="store_true")
    parser.add_argument("--output", default=".runtime/evaluation")
    args = parser.parse_args()
    import numpy as np
    import torch
    from PIL import Image
    from sklearn.model_selection import GroupShuffleSplit
    from sklearn.metrics import accuracy_score, classification_report, log_loss
    from torch.utils.data import TensorDataset, DataLoader
    from torchvision import models, transforms
    from farmsync.vision.train_crop_model import CROP_CLASSES, STAGE_CLASSES, MultiTaskCropNet
    torch.set_num_threads(1)
    torch.manual_seed(42); np.random.seed(42); random.seed(42)
    torch.use_deterministic_algorithms(True)
    output = Path(args.output); output.mkdir(parents=True, exist_ok=True)
    task = ROOT / "data/FAI_Product_Challange/TASK_4"
    csv_path = task / "Ground_Truth_Points/Ground_truth_Points.csv"
    disk = sorted((task / "Images/images").glob("*.jpg"))
    samples, seen_files, seen_hashes = [], set(), set()
    excluded = {"missing_label": 0, "unmatched_or_ambiguous_file": 0, "duplicate": 0, "missing_group": 0, "corrupt_image": 0}
    with csv_path.open(encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            crop, stage = labels(row.get("final_crop_name", ""), row.get("final_crop_stage", ""), CROP_CLASSES, STAGE_CLASSES)
            if not crop or not stage:
                excluded["missing_label"] += 1; continue
            key = row.get("image_path", "").strip()
            candidates = [p for p in disk if key and key in p.name]
            if len(candidates) != 1:
                excluded["unmatched_or_ambiguous_file"] += 1; continue
            path = candidates[0]
            digest = sha256(path.read_bytes()).hexdigest()
            if path.name in seen_files or digest in seen_hashes:
                excluded["duplicate"] += 1; continue
            survey = row.get("survey_n_1", "").strip()
            if not survey:
                excluded["missing_group"] += 1; continue
            group = "|".join(row.get(k, "").strip() for k in ("district_1", "taluk_co_1", "village__1", "survey_n_1"))
            seen_files.add(path.name); seen_hashes.add(digest)
            samples.append({"file": path.name, "sha256": digest, "group": group, "crop": CROP_CLASSES.index(crop), "stage": STAGE_CLASSES.index(stage)})
    print("Unique labelled source images:", len(samples), "Excluded:", excluded, flush=True)
    if len(samples) < 100:
        raise SystemExit("Insufficient labelled grouped images; no accuracy or calibration result published")
    preprocess = transforms.Compose([transforms.Resize((224, 224)), transforms.ToTensor(), transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])])
    model = models.mobilenet_v3_small(weights=models.MobileNet_V3_Small_Weights.DEFAULT).eval()
    features, retained = [], []
    with torch.no_grad():
        for index in range(0, len(samples), 32):
            batch, records = [], []
            for item in samples[index:index + 32]:
                try:
                    with Image.open(task / "Images/images" / item["file"]) as image:
                        batch.append(preprocess(image.convert("RGB"))); records.append(item)
                except Exception:
                    excluded["corrupt_image"] += 1
            if batch:
                feat = model.avgpool(model.features(torch.stack(batch))).flatten(1)
                features.append(feat); retained.extend(records)
            if index % 320 == 0:
                print("Feature extraction:", min(index + 32, len(samples)), "/", len(samples), flush=True)
    samples = retained
    X = torch.cat(features)
    crops = torch.tensor([s["crop"] for s in samples]); stages = torch.tensor([s["stage"] for s in samples])
    groups = np.array([s["group"] for s in samples])
    remaining, test = next(GroupShuffleSplit(n_splits=1, test_size=.20, random_state=42).split(X, groups=groups))
    train_local, validation_local = next(GroupShuffleSplit(n_splits=1, test_size=.20, random_state=43).split(X[remaining], groups=groups[remaining]))
    train, validation = remaining[train_local], remaining[validation_local]
    assert not (set(groups[train]) & set(groups[test]) or set(groups[validation]) & set(groups[test]) or set(groups[train]) & set(groups[validation]))
    assert len({s["sha256"] for s in samples}) == len(samples)
    head = MultiTaskCropNet()
    optimizer = torch.optim.AdamW(head.parameters(), lr=.002, weight_decay=1e-4)
    criterion = torch.nn.CrossEntropyLoss()
    counts = torch.bincount(crops[train], minlength=len(CROP_CLASSES)).float()
    weights = (len(train) / (len(CROP_CLASSES) * counts.clamp(min=1))).clamp(max=20)
    crop_loss = torch.nn.CrossEntropyLoss(weight=weights)
    loader = DataLoader(TensorDataset(X[train], crops[train], stages[train]), batch_size=64, shuffle=True, drop_last=True)
    best, best_loss = None, float("inf")
    for epoch in range(args.epochs):
        head.train()
        for x, y_crop, y_stage in loader:
            optimizer.zero_grad(); cp, sp = head(x)
            loss = crop_loss(cp, y_crop) + criterion(sp, y_stage)
            loss.backward(); optimizer.step()
        head.eval()
        with torch.no_grad():
            cp, sp = head(X[validation])
            value = float(criterion(cp, crops[validation]) + criterion(sp, stages[validation]))
        if value < best_loss:
            best_loss, best = value, copy.deepcopy(head.state_dict())
        if epoch % 5 == 0: print("Epoch", epoch + 1, "validation loss", round(value, 4), flush=True)
    head.load_state_dict(best); head.eval()
    with torch.no_grad():
        val_crop, val_stage = head(X[validation]); test_crop, test_stage = head(X[test])
    def temperature(logits, target):
        choices = np.linspace(.5, 5, 91)
        losses = [float(criterion(logits / float(t), target)) for t in choices]
        return float(choices[int(np.argmin(losses))])
    crop_t, stage_t = temperature(val_crop, crops[validation]), temperature(val_stage, stages[validation])
    def metrics(logits, targets, names, temp):
        probs = torch.softmax(logits / temp, dim=1).numpy()
        truth = targets.numpy(); pred = probs.argmax(axis=1)
        confidence = probs.max(axis=1); correct = pred == truth
        ece = 0.0
        for low in np.linspace(0, .9, 10):
            mask = (confidence >= low) & (confidence < low + .1 + 1e-9)
            if mask.any(): ece += float(mask.mean() * abs(correct[mask].mean() - confidence[mask].mean()))
        return {"accuracy": float(accuracy_score(truth, pred)), "nll": float(log_loss(truth, probs, labels=list(range(len(names))))), "ece_10_bins": ece,
                "per_class": classification_report(truth, pred, labels=list(range(len(names))), target_names=names, output_dict=True, zero_division=0)}
    torch.save(best, output / "crop_model.pth")
    checkpoint_sha = sha256((output / "crop_model.pth").read_bytes()).hexdigest()
    report = {"protocol": "grouped-train-validation-test-v1", "seed": 42,
              "dataset_sha256": sha256(csv_path.read_bytes()).hexdigest(), "model_sha256": checkpoint_sha,
              "samples": len(samples), "train": len(train), "validation": len(validation), "test": len(test), "group_overlap": 0,
              "duplicate_content_overlap": 0, "excluded": excluded,
              "crop": metrics(test_crop, crops[test], CROP_CLASSES, crop_t), "stage": metrics(test_stage, stages[test], STAGE_CLASSES, stage_t),
              "limitations": "Supplied labels and claimed parcel groups; not an independent real-field trial, legal verification or disease validation. Rare-class metrics may have few or zero test examples."}
    calibration = {"model_sha256": checkpoint_sha, "crop_temperature": crop_t, "stage_temperature": stage_t,
                   "method": "Validation-only bounded temperature fit; evaluated on separate test groups", "protocol": report["protocol"]}
    (output / "calibration.json").write_text(json.dumps(calibration, indent=2))
    (output / "metrics.json").write_text(json.dumps(report, indent=2))
    split = {"train": train, "validation": validation, "test": test}
    (output / "split-manifest.json").write_text(json.dumps({name:[samples[int(i)] for i in ids] for name,ids in split.items()}, indent=2))
    metadata = {"crop_classes": CROP_CLASSES, "stage_classes": STAGE_CLASSES, "backbone": "mobilenet_v3_small", "feature_dim":576, "validation_split_strategy":report["protocol"], "trained_timestamp":time.strftime("%Y-%m-%d %H:%M:%S"), "test_crop_accuracy_pct":round(report["crop"]["accuracy"]*100,2), "test_stage_accuracy_pct":round(report["stage"]["accuracy"]*100,2)}
    (output / "classes.json").write_text(json.dumps(metadata, indent=2))
    if args.promote:
        if report["crop"]["accuracy"] < .80 or report["stage"]["accuracy"] < .65:
            raise SystemExit("Candidate did not meet the stated minimum promotion gate; existing artifacts preserved")
        target = ROOT / "farmsync/vision/weights"
        archive = ROOT / ".runtime/model-archive" / str(int(time.time())); archive.mkdir(parents=True)
        for name in ["crop_model.pth", "classes.json", "calibration.json"]:
            if (target / name).exists(): shutil.copyfile(target / name, archive / name)
            shutil.copyfile(output / name, target / name)
        report["promoted"] = True
        (output / "metrics.json").write_text(json.dumps(report, indent=2))
    print(json.dumps({"crop_accuracy":report["crop"]["accuracy"], "stage_accuracy":report["stage"]["accuracy"], "test_samples":len(test), "model_sha256":checkpoint_sha, "promoted":report.get("promoted",False)},indent=2), flush=True)


if __name__ == "__main__":
    main()
