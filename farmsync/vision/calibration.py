"""Load calibration only when it matches the exact trained model bytes."""
from hashlib import sha256
import json
import math
from pathlib import Path


def load_calibration(weights_path):
    path = Path(weights_path).with_name("calibration.json")
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text())
        if data["model_sha256"] != sha256(Path(weights_path).read_bytes()).hexdigest():
            return None
        for key in ("crop_temperature", "stage_temperature"):
            value = float(data[key])
            if not math.isfinite(value) or not .5 <= value <= 5:
                return None
        return data
    except (KeyError, ValueError, OSError, TypeError):
        return None
