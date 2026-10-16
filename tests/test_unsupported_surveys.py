import sys
import os
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from farmsync.router.compiler import TaskGraphCompiler, extract_survey_number, extract_village_name
from farmsync.spatial.engine import SpatialEngine
from farmsync.vision.classifier import CropVisionClassifier
from farmsync.orchestrator import FarmSyncOrchestrator


class TestSurveyAndVillageEntityExtraction:
    """
    Validates regex-based cadastral entity extraction for diverse survey notations
    and multi-word village names.
    """

    def test_extract_standard_survey_number(self):
        assert extract_survey_number("Audit parcel for Survey 384") == "384"
        assert extract_survey_number("Survey No. 384 land verification") == "384"
        assert extract_survey_number("Check survey number 176 in village") == "176"

    def test_extract_sno_variations(self):
        assert extract_survey_number("Audit land record for S.No. 176") == "176"
        assert extract_survey_number("Verify plot at S.No 176") == "176"
        assert extract_survey_number("Check SNo 176 status") == "176"
        assert extract_survey_number("Sy. No. 387 boundary check") == "387"
        assert extract_survey_number("Sy.No. 387 boundary check") == "387"

    def test_extract_sf_no_and_subdivisions(self):
        assert extract_survey_number("Verify land at S.F. No. 381/1A") == "381/1A"
        assert extract_survey_number("Check SF No 384/1 boundary") == "384/1"
        assert extract_survey_number("Subdivision SF No. 176-2B audit") == "176-2B"

    def test_extract_rs_no_and_parcel_variations(self):
        assert extract_survey_number("R.S. No. 402 boundary verification") == "402"
        assert extract_survey_number("RS No 402 in village") == "402"
        assert extract_survey_number("Cadastral Parcel 175 audit") == "175"
        assert extract_survey_number("Check Parcel 384 area") == "384"

    def test_unspecified_survey_returns_none(self):
        assert extract_survey_number("Audit general agricultural parcel") is None
        assert extract_survey_number("Crop classification and advisory request") is None

    def test_extract_multi_word_village_names(self):
        assert extract_village_name("Audit land in Keela Thattaparai village") == "Keela Thattaparai"
        assert extract_village_name("Plot located at Mela Thattaparai village") == "Mela Thattaparai"
        assert extract_village_name("Cadastral check for village of Keela Thattaparai") == "Keela Thattaparai"
        assert extract_village_name("Verify parcel in Keelathattaparai") == "Keelathattaparai"

    def test_extract_village_default(self):
        # When no village name is present, defaults cleanly to Keelathattaparai
        assert extract_village_name("Survey 384 audit") == "Keelathattaparai"


class TestTaskGraphCompilerSurveyHandling:
    """
    Validates compiler sets target_survey_no and explicit_survey_provided properly.
    """

    def test_compiler_with_explicit_survey(self):
        compiler = TaskGraphCompiler()
        graph = compiler.compile("Run cadastral audit for Survey 9999 in Keela Thattaparai village")
        assert graph.target_survey_no == "9999"
        assert graph.explicit_survey_provided is True
        assert graph.target_village == "Keela Thattaparai"

    def test_compiler_without_survey(self):
        compiler = TaskGraphCompiler()
        graph = compiler.compile("Audit general agricultural land recommendations")
        assert graph.target_survey_no is None
        assert graph.explicit_survey_provided is False


class TestSpatialSubdivisionAndUnknownSurveys:
    """
    Validates spatial engine handling of subdivisions and unsupported surveys.
    """

    def test_subdivision_resolves_to_exact_fmb_geometry_not_parent(self):
        engine = SpatialEngine()
        # Parcel 384/1 must resolve to authentic FMB subdivision geometry (8.191 acres), NOT parent parcel (10.349 acres)
        parcel = engine.get_parcel("384/1")
        assert parcel is not None
        assert parcel["survey_no"] == "384/1"
        assert parcel["parent_survey_no"] == "384"
        assert parcel["sub_div"] == "1"
        assert parcel["is_subdivision"] is True
        assert round(parcel["area_acres"], 3) == 8.191
        assert "Park_fmb_Map" in parcel["gis_source"]

    def test_subdivision_384_2_resolves_exact_fmb_geometry(self):
        engine = SpatialEngine()
        # Parcel 384/2 must resolve to authentic FMB subdivision geometry (2.067 acres)
        parcel = engine.get_parcel("384/2")
        assert parcel is not None
        assert parcel["survey_no"] == "384/2"
        assert parcel["is_subdivision"] is True
        assert round(parcel["area_acres"], 3) == 2.067
        assert "Park_fmb_Map" in parcel["gis_source"]

    def test_unrecorded_subdivision_strictly_refuses_parent_substitution(self):
        engine = SpatialEngine()
        # Unrecorded subdivision 384/99 must return None under Refuse-to-Substitute policy
        parcel = engine.get_parcel("384/99")
        assert parcel is None

        constraints = engine.check_constraints("384/99")
        assert constraints["deterministic_spatial_verified"] is False
        assert "not found" in constraints["error"].lower()

    def test_parent_parcel_384_retains_cadastral_extent_and_lists_subdivisions(self):
        engine = SpatialEngine()
        # Parent parcel 384 remains 10.349 acres and lists its authentic subdivisions
        parcel = engine.get_parcel("384")
        assert parcel is not None
        assert parcel["survey_no"] == "384"
        assert parcel["is_subdivision"] is False
        assert round(parcel["area_acres"], 3) == 10.349
        assert "384/1" in parcel.get("subdivisions_available", [])
        assert "384/2" in parcel.get("subdivisions_available", [])

    def test_subdivision_spatial_constraints_distance_distinct_from_parent(self):
        engine = SpatialEngine()
        c_sub = engine.check_constraints("384/1")
        c_parent = engine.check_constraints("384")
        assert c_sub["deterministic_spatial_verified"] is True
        assert "Park_fmb_Map" in c_sub["gis_source"]
        # FMB polygon 384/1 has distinct road distance from parent parcel envelope
        assert c_sub["distance_to_road_meters"] == 214.04
        assert c_parent["distance_to_road_meters"] == 206.14

    def test_spatial_returns_none_for_unknown_survey(self):
        engine = SpatialEngine()
        parcel = engine.get_parcel("9999")
        assert parcel is None


class TestVisionClassifierRefusal:
    """
    Validates vision classifier refuses to substitute or fabricate images for unknown surveys.
    """

    def test_classifier_refuses_to_substitute_for_unsupported_survey(self):
        classifier = CropVisionClassifier()
        img_path = classifier.get_image_for_survey("9999")
        assert img_path is None


class TestOrchestratorUnsupportedSurveyEndToEnd:
    """
    Validates the end-to-end orchestrator never silently falls back to Survey 384
    or fabricates crops, GIS boundaries, or advisories for unsupported parcels.
    """

    @pytest.fixture(scope="class")
    def orchestrator(self):
        return FarmSyncOrchestrator()

    def test_unsupported_survey_9999_abstains(self, orchestrator):
        result = orchestrator.execute_request(
            query="Audit parcel Survey 9999 in Keela Thattaparai village",
            survey_no="9999"
        )
        vobj = result["verified_result_object"]
        assert vobj["survey_number"] == "9999"

        extracted = vobj["extracted_attributes"]
        assert extracted["gis_area_acres"] is None
        assert extracted["predicted_crop"] is None
        assert extracted["growth_stage"] is None

        logistics = vobj["agri_logistics"]
        assert logistics["status"] == "NO_PARCEL_COORDINATES"

        advisory = vobj["advisory_recommendation"]
        assert advisory["source_grounded"] is False
        assert advisory.get("fertilizer_schedule") is None

        trust = vobj["trust_metrics"]
        assert trust["verification_status"] == "VERIFIED_ABSTAIN"
        assert trust["task_trust_score_fts"] < 0.70

    def test_unspecified_survey_abstains(self, orchestrator):
        result = orchestrator.execute_request(
            query="Audit crop health and fertilizer advice for general farm",
            survey_no=None
        )
        vobj = result["verified_result_object"]
        assert vobj["survey_number"] == "UNSPECIFIED"

        extracted = vobj["extracted_attributes"]
        assert extracted["gis_area_acres"] is None
        assert extracted["predicted_crop"] is None

        trust = vobj["trust_metrics"]
        assert trust["verification_status"] == "VERIFIED_ABSTAIN"
