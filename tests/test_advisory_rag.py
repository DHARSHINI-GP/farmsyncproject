"""
Tests for farmsync.knowledge.advisory – verifying:
1. Genuine FAISS dense vector search over the official TNAU/ICAR document corpus.
2. Verified retrieval for known regional crops (Coconut, Rice, Banana, Maize, Cotton, Groundnut).
3. Strict Refuse-to-Invent policy: unknown / OOD crops return source_grounded=False and found=False.
4. Never asserts unverified recommendations as source-grounded.
"""

import os
import pytest

from farmsync.knowledge.advisory import AgronomyKnowledgeEngine


@pytest.fixture(scope="module")
def knowledge_engine():
    return AgronomyKnowledgeEngine()


class TestAgronomyFAISSRAG:
    """Verifies FAISS vector search, document corpus retrieval, and honest grounding."""

    def test_faiss_index_initialized(self, knowledge_engine):
        status = knowledge_engine.get_status()
        assert status["index_available"] is True
        assert status["total_indexed_documents"] >= 10
        assert status["faiss_total_vectors"] >= 10
        assert status["similarity_threshold"] == 0.50
        assert "FAISS" in status["rag_engine"]

    def test_retrieve_known_crop_coconut(self, knowledge_engine):
        """Validates that Coconut (Survey 384 benchmark) retrieves authentic ICAR-CPCRI TB 98 advisory."""
        res = knowledge_engine.get_advisory("Coconut", "full_growth")

        assert res["found"] is True
        assert res["source_grounded"] is True
        assert res["verdict"] == "VERIFIED_GROUNDED_ADVISORY"
        assert "CPCRI" in res["doc_id"] or "CPCRI" in res["citation_source"]
        assert "Urea" in res["fertilizer_schedule"]
        assert "Drip" in res["water_management"] or "irrigation" in res["water_management"].lower()
        assert "Rhinoceros Beetle" in res["pest_management"]
        assert "Technical Bulletin No. 98" in res["citation_source"]
        assert res["similarity_score"] >= 0.50
        assert "FAISS" in res["retrieval_method"]

    def test_retrieve_known_crop_rice(self, knowledge_engine):
        """Validates that Rice (Paddy) retrieves authentic TNAU 2024 agronomy advisory."""
        res = knowledge_engine.get_advisory("Rice (Paddy)", "vegetation")

        assert res["found"] is True
        assert res["source_grounded"] is True
        assert "TNAU" in res["citation_source"]
        assert "Nitrogen" in res["fertilizer_schedule"]
        assert "AWD" in res["water_management"] or "submergence" in res["water_management"]
        assert "Stem Borer" in res["pest_management"]
        assert res["similarity_score"] >= 0.50

    def test_retrieve_known_crop_banana(self, knowledge_engine):
        """Validates that Banana retrieves NRCB (National Research Centre for Banana) guidelines."""
        res = knowledge_engine.get_advisory("Banana", "full_growth")

        assert res["found"] is True
        assert res["source_grounded"] is True
        assert "NRCB" in res["citation_source"] or "Banana" in res["citation_source"]
        assert "Urea" in res["fertilizer_schedule"]
        assert res["similarity_score"] >= 0.50

    def test_retrieve_known_crop_maize(self, knowledge_engine):
        """Validates that Maize retrieves Fall Armyworm (FAW) protocol from ICAR-IIMR / TNAU."""
        res = knowledge_engine.get_advisory("Maize", "vegetation")

        assert res["found"] is True
        assert res["source_grounded"] is True
        assert "Fall Armyworm" in res["pest_management"]
        assert "IIMR" in res["citation_source"] or "TNAU" in res["citation_source"]

    def test_refuse_to_invent_unknown_crop(self, knowledge_engine):
        """
        Validates the strict Refuse-to-Invent policy:
        For unknown / OOD crops (Dragonfruit, Avocado, Blueberry), the system must
        NEVER label recommendations as source-grounded.
        """
        res = knowledge_engine.get_advisory("Dragonfruit", "vegetation")

        assert res["found"] is False
        assert res["source_grounded"] is False
        assert res["verdict"] == "UNVERIFIED_CROP_NO_GROUNDED_ADVISORY"
        assert res["fertilizer_schedule"] is None
        assert res["water_management"] is None
        assert res["pest_management"] is None
        assert res["citation_source"] is None
        assert "No Verified Agronomy Advisory" in res["advisory_title"]
        assert "notice" in res

    def test_refuse_to_invent_fabricated_crop(self, knowledge_engine):
        """Ensures random synthetic crop strings strictly return source_grounded=False."""
        res = knowledge_engine.get_advisory("SyntheticXylophoneCrop99", "flowering")

        assert res["found"] is False
        assert res["source_grounded"] is False
        assert res["fertilizer_schedule"] is None
        assert res["citation_source"] is None

    def test_refuse_to_claim_grounded_on_stage_mismatch_faiss(self, knowledge_engine):
        """
        Validates that when the crop exists in the corpus (Coconut) but the requested
        growth stage does not (flowering), the system strictly refuses to return a
        mismatched-stage document as source-grounded.
        """
        res = knowledge_engine.get_advisory("Coconut", "flowering")

        assert res["found"] is False
        assert res["source_grounded"] is False
        assert res["verdict"] == "STAGE_MISMATCH_NO_GROUNDED_ADVISORY"
        assert res["stage_match_status"] == "STAGE_MISMATCH"
        assert res["fertilizer_schedule"] is None
        assert res["water_management"] is None
        assert res["pest_management"] is None
        assert "full_growth" in res["available_stages_in_corpus"]
        assert "vegetation" in res["available_stages_in_corpus"]
        assert "mismatched growth-stage recommendations are refused" in res["notice"]

    def test_corpus_scan_fallback_refuses_to_claim_grounded_on_stage_mismatch(self, knowledge_engine):
        """
        Validates that when FAISS index is bypassed and corpus-scan fallback runs,
        it does NOT assign an artificial 0.85 score to a same-crop document with a
        mismatched growth stage.
        """
        saved_index = knowledge_engine.faiss_index
        try:
            knowledge_engine.faiss_index = None
            res = knowledge_engine.get_advisory("Coconut", "flowering")

            assert res["found"] is False
            assert res["source_grounded"] is False
            assert res["verdict"] == "STAGE_MISMATCH_NO_GROUNDED_ADVISORY"
            assert res["fertilizer_schedule"] is None
            # Under the fix, score must not be 0.85 to bypass the 0.50 threshold
            assert res["similarity_score"] < 0.50
        finally:
            knowledge_engine.faiss_index = saved_index

    def test_corpus_scan_fallback_succeeds_on_exact_stage_match(self, knowledge_engine):
        """
        Validates that when FAISS index is bypassed and corpus-scan fallback runs,
        it correctly matches when the growth stage truly matches.
        """
        saved_index = knowledge_engine.faiss_index
        try:
            knowledge_engine.faiss_index = None
            res = knowledge_engine.get_advisory("Coconut", "full_growth")

            assert res["found"] is True
            assert res["source_grounded"] is True
            assert res["verdict"] == "VERIFIED_GROUNDED_ADVISORY"
            assert res["stage_match_status"] == "EXACT_STAGE_MATCH"
            assert res["fertilizer_schedule"] is not None
            assert res["similarity_score"] == 1.00
            assert "Document_Corpus_Scan" in res["retrieval_method"]
        finally:
            knowledge_engine.faiss_index = saved_index

    def test_stage_synonym_normalization(self, knowledge_engine):
        """Validates that standard agronomic synonyms (mature -> full_growth, vegetative -> vegetation) match properly."""
        res_mature = knowledge_engine.get_advisory("Coconut", "mature")
        assert res_mature["found"] is True
        assert res_mature["source_grounded"] is True

        res_veg = knowledge_engine.get_advisory("Rice (Paddy)", "vegetative")
        assert res_veg["found"] is True
        assert res_veg["source_grounded"] is True
