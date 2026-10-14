import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from farmsync.vision.classifier import CropVisionPipeline

def main():
    print("Testing CropVisionPipeline...")
    pipeline = CropVisionPipeline()
    print(f"Total indexed field images: {len(pipeline.image_registry)}")
    assert len(pipeline.image_registry) > 0, "No images indexed!"

    # Test image retrieval
    sample_key = next(iter(pipeline.image_registry))
    sample_record = pipeline.image_registry[sample_key]
    print(f"Sample image: {sample_key} | Crop={sample_record['true_crop']} | Stage={sample_record['true_stage']}")

    # Test 1: Real Student Neural Inference on Pixels
    pred_normal = pipeline.predict_crop(sample_record['filepath'])
    print("Normal prediction:", pred_normal)
    assert pred_normal["has_image"] == True
    assert "visual_evidence" in pred_normal
    assert len(pred_normal["top_3_crops"]) > 0

    # Test 2: Teacher Escalation Trigger
    pred_escalated = pipeline.predict_crop(sample_record['filepath'], force_escalate=True)
    print("Escalated prediction:", pred_escalated)
    assert pred_escalated["escalated_to_teacher"] == True
    assert pred_escalated["teacher_model"] is not None

    # Test 3: Refuse-to-Substitute (Survey with no photo must return None)
    img_unknown = pipeline.get_image_for_survey("9999_UNKNOWN")
    print("Image for unknown survey (must be None):", img_unknown)
    assert img_unknown is None, "Violation: Unknown survey must not receive arbitrary fallback image!"

    # Test 4: Graceful handling when image is None
    pred_none = pipeline.predict_crop(None)
    print("Prediction for None image:", pred_none)
    assert pred_none["has_image"] == False
    assert pred_none["confidence"] == 0.0

    print("ALL VISION TESTS PASSED!")

if __name__ == "__main__":
    main()
