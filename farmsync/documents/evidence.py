"""Conservative PDF claims: source text only; unknown fields stay null."""
from decimal import Decimal, InvalidOperation
from hashlib import sha256
import os
from pathlib import Path
import re

import pdfplumber

SURVEY = re.compile(r"\b\d+(?:/[0-9]+[A-Za-z]*)?\b")
ALIASES = {
    "survey": ("survey", "s.no", "s.f.", "புல எண்", "சர்வே"),
    "owner": ("owner", "pattadar", "claimant", "landholder", "உரிமையாளர்", "பெயர்"),
    "extent": ("extent", "area", "விஸ்தீரணம்", "பரப்பளவு"),
    "village": ("village", "கிராமம்"),
}


def area_acres(raw, unit):
    """Convert only declared units. Never infer units from numeric magnitude."""
    if not raw or not unit:
        return None
    value = str(raw).strip().replace(",", "")
    unit = unit.casefold()
    try:
        if re.fullmatch(r"\d+\.\d{1,2}\.\d{1,2}", value) and any(x in unit for x in ("hect", "ஹெக்", "ha")):
            h, a, sqm = map(Decimal, value.split("."))
            if a >= 100 or sqm >= 100:
                return None
            amount = h + a / 100 + sqm / 10000
            factor = Decimal("2.47105381467165")
        else:
            # Unit suffix is allowed, extra numbers or unrelated text are not.
            match = re.fullmatch(r"(\d+(?:\.\d+)?)\s*(?:acres?|ac|ha|hectares?|sqm|m²|ஏக்கர்|ஹெக்டேர்)?", value, re.I)
            if not match:
                return None
            amount = Decimal(match[1])
            if "acre" in unit or unit.strip() == "ac" or "ஏக்கர்" in unit:
                factor = Decimal(1)
            elif any(x in unit for x in ("hect", "ஹெக்")) or re.search(r"\bha\b", unit):
                factor = Decimal("2.47105381467165")
            elif any(x in unit for x in ("sqm", "sq.m", "m²", "square metre", "square meter")):
                factor = Decimal("0.000247105381467165")
            else:
                return None
        result = amount * factor
        return round(float(result), 6) if result.is_finite() and result > 0 else None
    except (InvalidOperation, ValueError, OverflowError):
        return None


def column_map(row):
    result = {}
    for index, cell in enumerate(row or []):
        text = re.sub(r"\s+", " ", str(cell or "")).casefold()
        for field, names in ALIASES.items():
            if any(name in text for name in names):
                result.setdefault(field, (index, text))
    return result


def claim(survey, page, method, raw, owner=None, extent=None, village=None, confidence=None):
    return {
        "found": True, "survey_no": survey,
        "extracted_owner": owner or None, "claimed_extent_acres": extent,
        "claimed_extent_hectares": None, "land_classification": None,
        "document_village": village or None, "page_number": page,
        "extraction_method": method, "ocr_confidence": confidence,
        "confidence_kind": "OCR engine score" if confidence is not None else "not calibrated",
        "raw_text_snippet": raw[:6000],
        "field_status": {"owner": "EXTRACTED" if owner else "MISSING", "extent": "EXTRACTED_WITH_UNIT" if extent is not None else "MISSING_OR_UNIT_AMBIGUOUS"},
        "status": "SOURCE_FIELDS_EXTRACTED" if owner and extent is not None else "PARTIAL_SOURCE_EVIDENCE",
    }


def text_claims(text, page, method="pdfplumber_labelled_text", confidence=None):
    results = []
    for line in text.splitlines():
        match = re.search(r"(?:survey(?:\s*(?:number|no\.?))?|s\.?\s*f\.?\s*no\.?|s\.?\s*no\.?|புல எண்|சர்வே)\s*[:#-]?\s*(\d+(?:/\d+[A-Za-z]*)?)\b", line, re.I)
        if not match:
            continue
        def field(label):
            found = re.search(label + r"\s*[:=]\s*([^;|]+)", line, re.I)
            return found[1].strip() if found else None
        owner = field(r"(?:owner|pattadar|claimant|உரிமையாளர்)")
        village = field(r"(?:village|கிராமம்)")
        extent = re.search(r"(?:extent|area|பரப்பளவு)\s*[:=]\s*(\d+(?:\.\d+){0,2})\s*(acres?|ha|hectares?|sqm|m²|ஏக்கர்|ஹெக்டேர்)\b", line, re.I)
        results.append(claim(match[1], page, method, line, owner, area_acres(extent[1], extent[2]) if extent else None, village, confidence))
    return results


def extract_claims(path, reader=None, max_pages=None):
    path = Path(path)
    max_pages = max_pages or int(os.getenv("FARMSYNC_MAX_PDF_PAGES", "100"))
    results, notices = [], []
    blank_pages = []
    with pdfplumber.open(path) as pdf:
        if len(pdf.pages) > max_pages:
            raise ValueError(f"PDF exceeds the {max_pages}-page processing limit")
        for number, page in enumerate(pdf.pages, 1):
            text = page.extract_text() or ""
            if not text.strip():
                blank_pages.append(number)
            for table in page.extract_tables() or []:
                headers = {}
                for row in table or []:
                    mapping = column_map(row)
                    if "survey" in mapping:
                        headers = mapping
                        continue
                    if not headers:
                        continue
                    def cell(key):
                        index = headers.get(key, (-1, ""))[0]
                        return str(row[index] or "").strip() if 0 <= index < len(row) else ""
                    survey = cell("survey")
                    if not SURVEY.fullmatch(survey):
                        continue
                    extent = area_acres(cell("extent"), headers.get("extent", (0, ""))[1])
                    results.append(claim(survey, number, "pdfplumber_header_table", " | ".join(str(c or "") for c in row), cell("owner"), extent, cell("village")))
            results.extend(text_claims(text, number))
    if blank_pages and reader is not None:
        try:
            import numpy as np
            with pdfplumber.open(path) as pdf:
                for number in blank_pages:
                    page = pdf.pages[number - 1]
                    if page.width * page.height * 4 > 20_000_000:
                        notices.append(f"Page {number}: raster limit exceeded")
                        continue
                    image = page.to_image(resolution=144).original
                    words = reader.readtext(np.asarray(image))
                    # Keep OCR layout lines together; never infer names from a registry.
                    lines = {}
                    for box, value, score in words:
                        line = round(min(p[1] for p in box) / 18)
                        lines.setdefault(line, []).append((min(p[0] for p in box), value, float(score)))
                    for words_on_line in lines.values():
                        words_on_line.sort()
                        raw = " ".join(w[1] for w in words_on_line)
                        results.extend(text_claims(raw, number, "easyocr_rendered_page", min(w[2] for w in words_on_line)))
        except ImportError:
            notices.append("Scanned-page rendering unavailable; provision pypdfium2 and OCR models")
        except Exception as exc:
            notices.append("OCR incomplete: " + type(exc).__name__)
    elif blank_pages:
        notices.append("Scanned pages require provisioned OCR models; no extracted claims invented")
    checksum = sha256(path.read_bytes()).hexdigest()
    for item in results:
        item.update(document_source=path.name, document_path=str(path), source_sha256=checksum)
    # The same row may also occur in extracted page text. Prefer structured rows.
    unique = {}
    table_keys = {(r["survey_no"], r["page_number"]) for r in results if r["extraction_method"] == "pdfplumber_header_table"}
    for item in results:
        if item["extraction_method"] != "pdfplumber_header_table" and (item["survey_no"], item["page_number"]) in table_keys:
            continue
        key = (item["survey_no"], item["page_number"], item["extracted_owner"], item["claimed_extent_acres"], item["document_village"])
        unique[key] = item
    return list(unique.values()), notices
