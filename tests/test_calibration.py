from hashlib import sha256
import json
from farmsync.vision.calibration import load_calibration


def test_calibration_requires_matching_model_and_valid_temperatures(tmp_path):
    weights=tmp_path / "crop_model.pth"
    weights.write_bytes(b"model-one")
    config={"model_sha256":sha256(weights.read_bytes()).hexdigest(), "crop_temperature":.8, "stage_temperature":1.15}
    (tmp_path / "calibration.json").write_text(json.dumps(config))
    assert load_calibration(weights)["crop_temperature"] == .8
    weights.write_bytes(b"changed-model")
    assert load_calibration(weights) is None
    config["model_sha256"]=sha256(weights.read_bytes()).hexdigest()
    config["stage_temperature"]=float("nan")
    (tmp_path / "calibration.json").write_text(json.dumps(config))
    assert load_calibration(weights) is None
