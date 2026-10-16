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


def test_student_model_truthful_attribution(pipeline):
    """Verifies that MobileNetV3 inference is honestly labeled and never falsely attributed to Qwen."""
    sample_key = next(iter(pipeline.image_registry))
    sample_record = pipeline.image_registry[sample_key]
    pred = pipeline.predict_crop(sample_record['filepath'])
    assert pred["student_model"] == "MobileNetV3-CropNet (PyTorch)"
    assert "Qwen" not in pred["student_model"]

def test_teacher_fallback_does_not_falsely_claim_claude(pipeline):
    """
    Verifies that when Bedrock is unavailable, local TTA fallback honestly discloses:
    - teacher_model is MobileNetV3-TTA-Ensemble-Teacher (Local Fallback)
    - is_independent_teacher is False
    - teacher_source is LOCAL_MODEL_TTA_FALLBACK
    - Never falsely claims to be Claude
    """
    sample_key = next(iter(pipeline.image_registry))
    sample_record = pipeline.image_registry[sample_key]
    
    # Ensure bedrock_client is None for this test to verify fallback behavior
    saved_client = pipeline.bedrock_client
    try:
        pipeline.bedrock_client = None
        pred = pipeline.predict_crop(sample_record['filepath'], force_escalate=True)
        assert pred["escalated_to_teacher"] is True
        assert pred["teacher_model"] == "MobileNetV3-TTA-Ensemble-Teacher (Local Fallback)"
        assert pred["is_independent_teacher"] is False
        assert pred["teacher_source"] == "LOCAL_MODEL_TTA_FALLBACK"
        assert "Claude" not in pred["teacher_model"]
        assert "not an independent teacher model" in pred["escalation_note"]
    finally:
        pipeline.bedrock_client = saved_client

def test_teacher_ensemble_confidence_dynamic_not_fixed_096(pipeline):
    """Verifies that TTA ensemble confidence is dynamically calculated from logits, not a fixed 0.96."""
    from PIL import Image
    sample_key = next(iter(pipeline.image_registry))
    sample_record = pipeline.image_registry[sample_key]
    img = Image.open(sample_record['filepath']).convert("RGB")
    
    ensemble_res = pipeline._run_teacher_ensemble(img)
    assert ensemble_res["confidence"] > 0.0
    assert ensemble_res["is_independent_teacher"] is False
    assert ensemble_res["teacher_source"] == "LOCAL_MODEL_TTA_FALLBACK"
    assert "Multi-Scale TTA" in ensemble_res["ensemble_method"]
    # Verify confidence was computed from crop and stage confidences
    expected = round(ensemble_res["crop_confidence"] * 0.75 + ensemble_res["stage_confidence"] * 0.25, 3)
    assert ensemble_res["confidence"] == expected

def main():
    print("Testing CropVisionPipeline...")
    p = CropVisionPipeline()
    test_image_registry_indexed(p)
    test_real_student_neural_inference(p)
    test_student_model_truthful_attribution(p)
    test_teacher_escalation_trigger(p)
    test_teacher_fallback_does_not_falsely_claim_claude(p)
    test_teacher_ensemble_confidence_dynamic_not_fixed_096(p)
    test_refuse_to_substitute_unknown_survey(p)
    test_graceful_missing_photo(p)
    print("ALL VISION TESTS PASSED!")


if __name__ == "__main__":
    main()
