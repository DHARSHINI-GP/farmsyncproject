"""Explicitly provision public model artifacts before offline application startup."""
import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vision", action="store_true")
    parser.add_argument("--embeddings", action="store_true")
    parser.add_argument("--ocr", action="store_true")
    args = parser.parse_args()
    from farmsync.aws import system_ca_bundle
    bundle = system_ca_bundle()
    if bundle is not True:
        os.environ.setdefault("SSL_CERT_FILE", bundle)
        os.environ.setdefault("REQUESTS_CA_BUNDLE", bundle)
    if args.vision:
        from torchvision import models
        models.mobilenet_v3_small(weights=models.MobileNet_V3_Small_Weights.DEFAULT)
    if args.embeddings:
        from sentence_transformers import SentenceTransformer
        SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    if args.ocr:
        from farmsync.documents.ocr import reader
        os.environ.setdefault('FARMSYNC_OCR_MODEL_DIR', str(ROOT / '.runtime/models/easyocr'))
        reader(download=True)
    paths = [ROOT / "farmsync/vision/weights/crop_model.pth", ROOT / "farmsync/vision/weights/classes.json"]
    manifest = {str(p.relative_to(ROOT)): sha256(p.read_bytes()).hexdigest() for p in paths if p.is_file()}
    output = ROOT / ".runtime/model-manifest.json"
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print("Provisioning completed; local model manifest saved. Model accuracy is evaluated separately.")


if __name__ == "__main__":
    main()
