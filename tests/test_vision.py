import sys
import os
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from farmsync.vision.classifier import CropVisionPipeline

@pytest.fixture(scope="module")
def pipeline():
    return CropVisionPipeline()

def test_image_registry_indexed(pipeline):
    assert len(pipeline.image_registry) > 0, "No images indexed!"

def test_real_student_neural_inference(pipeline):
    sample_key = next(iter(pipeline.image_registry))
    sample_record = pipeline.image_registry[sample_key]
    pred = pipeline.predict_crop(sample_record['filepath'])
    assert pred["has_image"] is True
    assert "visual_evidence" in pred
    assert len(pred["top_3_crops"]) > 0
    assert pred["confidence"] > 0.0

def test_teacher_escalation_trigger(pipeline):
    sample_key = next(iter(pipeline.image_registry))
    sample_record = pipeline.image_registry[sample_key]
    pred_escalated = pipeline.predict_crop(sample_record['filepath'], force_escalate=True)
    assert pred_escalated["escalated_to_teacher"] is True
    assert pred_escalated["teacher_model"] is not None

def test_refuse_to_substitute_unknown_survey(pipeline):
    img_unknown = pipeline.get_image_for_survey("9999_UNKNOWN")
    assert img_unknown is None, "Violation: Unknown survey must not receive arbitrary fallback image!"

def test_graceful_missing_photo(pipeline):
    pred_none = pipeline.predict_crop(None)
    assert pred_none["has_image"] is False
    assert pred_none["confidence"] == 0.0


def main():
    print("Testing CropVisionPipeline...")
    p = CropVisionPipeline()
    test_image_registry_indexed(p)
    test_real_student_neural_inference(p)
    test_teacher_escalation_trigger(p)
    test_refuse_to_substitute_unknown_survey(p)
    test_graceful_missing_photo(p)
    print("ALL VISION TESTS PASSED!")


if __name__ == "__main__":
    main()
