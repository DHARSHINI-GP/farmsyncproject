from unittest.mock import MagicMock

import pytest

from farmsync.documents import evidence
from farmsync.documents.extractor import DocumentRegistryEngine


@pytest.mark.parametrize("value,unit,expected", [
    ("10.00", "Extent (acres)", 10.0), ("1.00", "Extent hectares", 2.471054),
    ("0.60.50", "Extent hectares", 1.494988), ("10000", "area sqm", 2.471054),
    ("10.00", "Extent", None), ("0.120.50", "hectares", None),
    ("2.5 384", "acres", None), ("NaN", "acres", None), ("0", "acres", None),
])
def test_explicit_area_units(value, unit, expected):
    assert evidence.area_acres(value, unit) == expected


def pdf_with_tables(monkeypatch, tmp_path, rows, text=""):
    path = tmp_path / "evidence.pdf"
    path.write_bytes(b"%PDF-mocked-content")
    page = MagicMock()
    page.extract_tables.return_value = [rows]
    page.extract_text.return_value = text
    pdf = MagicMock()
    pdf.pages = [page]
    opened = MagicMock()
    opened.__enter__.return_value = pdf
    monkeypatch.setattr(evidence.pdfplumber, "open", lambda _: opened)
    return path


def test_missing_owner_never_borrowed_from_registry(monkeypatch, tmp_path):
    path = pdf_with_tables(monkeypatch, tmp_path, [["Survey no", "Extent acres", "Owner"], ["384", "10.00", ""]])
    engine = DocumentRegistryEngine.__new__(DocumentRegistryEngine)
    engine.land_docs_dir = str(tmp_path)
    engine.data_root = str(tmp_path)
    engine.revenue_registry = {"384": {"registered_owner": "Ramesh Kumar"}}
    engine.cadastral_registry = {"384": {"registered_extent_acres": 10.349}}
    result = engine.extract_document_claims(str(path), "384")
    assert result["found"]
    assert result["extracted_owner"] is None
    assert result["claimed_extent_acres"] == 10.0
    assert result["ocr_confidence"] is None
    assert result["field_status"]["owner"] == "MISSING"
    assert len(result["source_sha256"]) == 64


def test_missing_extent_and_unknown_units_stay_null(monkeypatch, tmp_path):
    path = pdf_with_tables(monkeypatch, tmp_path, [["Survey no", "Extent", "Owner"], ["384", "10.00", "Actual claimant"]])
    rows, _ = evidence.extract_claims(path)
    assert rows[0]["claimed_extent_acres"] is None
    assert rows[0]["extracted_owner"] == "Actual claimant"


def test_conflicting_rows_are_preserved_not_silently_selected(monkeypatch, tmp_path):
    path = pdf_with_tables(monkeypatch, tmp_path, [["Survey no", "Extent acres", "Owner"], ["384", "10.00", "One"], ["384", "20.00", "Two"]])
    rows, _ = evidence.extract_claims(path)
    assert len(rows) == 2


def test_unlabelled_number_is_not_a_survey_or_owner():
    assert evidence.text_claims("Invoice 384 for 10.00 rupees", 1) == []
    result = evidence.text_claims("Survey 384; Area: 4 hectares; Owner: Actual Name", 3)[0]
    assert result["extracted_owner"] == "Actual Name"
    assert result["claimed_extent_acres"] == 9.884215


def test_headerless_table_does_not_invent_field_semantics(monkeypatch, tmp_path):
    path = pdf_with_tables(monkeypatch, tmp_path, [["384", "10.00", ""]])
    rows, _ = evidence.extract_claims(path)
    assert rows == []

def test_source_cache_uses_content_version_and_isolates_returned_values(monkeypatch,tmp_path):
    import os
    path=tmp_path/'source.pdf'; path.write_bytes(b'VersionA')
    original_time=path.stat().st_mtime_ns
    calls=[]
    def parse(source):
        calls.append(1)
        return [{'extracted_owner':source.read_text()}],[]
    monkeypatch.setattr(evidence,'extract_claims',parse)
    engine=DocumentRegistryEngine.__new__(DocumentRegistryEngine)
    first,_=engine.extract_source_claims(path)
    first[0]['extracted_owner']='Modified caller value'
    assert engine.extract_source_claims(path)[0][0]['extracted_owner']=='VersionA'
    assert len(calls)==1
    path.write_bytes(b'VersionB')
    os.utime(path,ns=(original_time,original_time))
    assert engine.extract_source_claims(path)[0][0]['extracted_owner']=='VersionB'
    assert len(calls)==2
