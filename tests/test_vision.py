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

    # Test student prediction (normal confident case)
    pred_normal = pipeline.predict_crop(sample_record['filepath'])
    print("Normal prediction:", pred_normal)
    assert pred_normal["escalated_to_teacher"] == False

    # Test escalation trigger (low confidence / OOD)
    pred_escalated = pipeline.predict_crop(sample_record['filepath'], force_escalate=True)
    print("Escalated prediction:", pred_escalated)
    assert pred_escalated["escalated_to_teacher"] == True
    assert pred_escalated["teacher_model"] is not None

    print("ALL VISION TESTS PASSED!")

if __name__ == "__main__":
    main()
