from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, KeepTogether
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.platypus import BaseDocTemplate, Frame, PageTemplate
from reportlab.lib.colors import HexColor
import os

# ─── Colour Palette ────────────────────────────────────────────────────────────
C_DARK      = HexColor("#0D1B2A")   # near-black navy
C_PRIMARY   = HexColor("#1A6B3C")   # deep forest green
C_ACCENT    = HexColor("#27AE60")   # vivid green
C_LIGHT_BG  = HexColor("#F0F7F4")   # very light green tint
C_GOLD      = HexColor("#F39C12")   # gold for highlights
C_WHITE     = colors.white
C_MID_GREY  = HexColor("#5D6D7E")
C_LIGHT_GREY= HexColor("#BDC3C7")
C_CODE_BG   = HexColor("#1E2D3D")   # dark code block
C_CODE_TEXT = HexColor("#A8D5A2")   # soft green code text

PAGE_W, PAGE_H = A4
MARGIN = 2.0 * cm

# ─── Document Setup ────────────────────────────────────────────────────────────
output_path = r"c:\farmAi hackathon\FARMSYNC_Proposal_TCPC-2026-00071.pdf"

doc = SimpleDocTemplate(
    output_path,
    pagesize=A4,
    leftMargin=MARGIN,
    rightMargin=MARGIN,
    topMargin=2.5 * cm,
    bottomMargin=2.0 * cm,
    title="FARMSYNC Proposal — TCPC-2026-00071",
    author="Safi A, Mohamed Asfaq S, Sooraj TS",
    subject="FarmwiseAI Campus Product Challenge — Task 1",
)

# ─── Styles ────────────────────────────────────────────────────────────────────
styles = getSampleStyleSheet()

def S(name, **kw):
    return ParagraphStyle(name, **kw)

style_cover_title = S("CoverTitle",
    fontName="Helvetica-Bold", fontSize=32, textColor=C_WHITE,
    alignment=TA_CENTER, leading=40, spaceAfter=8)

style_cover_sub = S("CoverSub",
    fontName="Helvetica", fontSize=14, textColor=HexColor("#A8D5A2"),
    alignment=TA_CENTER, leading=20, spaceAfter=6)

style_cover_meta = S("CoverMeta",
    fontName="Helvetica", fontSize=11, textColor=HexColor("#D5E8D4"),
    alignment=TA_CENTER, leading=16, spaceAfter=4)

style_h1 = S("H1",
    fontName="Helvetica-Bold", fontSize=16, textColor=C_PRIMARY,
    spaceAfter=6, spaceBefore=18, leading=20,
    borderPad=4)

style_h2 = S("H2",
    fontName="Helvetica-Bold", fontSize=12, textColor=C_DARK,
    spaceAfter=4, spaceBefore=12, leading=16)

style_h3 = S("H3",
    fontName="Helvetica-BoldOblique", fontSize=10.5, textColor=C_PRIMARY,
    spaceAfter=3, spaceBefore=8, leading=14)

style_body = S("Body",
    fontName="Helvetica", fontSize=9.5, textColor=C_DARK,
    spaceAfter=5, leading=15, alignment=TA_JUSTIFY)

style_bullet = S("Bullet",
    fontName="Helvetica", fontSize=9.5, textColor=C_DARK,
    leftIndent=16, firstLineIndent=0, spaceAfter=3,
    leading=14, bulletIndent=6)

style_code = S("Code",
    fontName="Courier", fontSize=7.8, textColor=C_CODE_TEXT,
    backColor=C_CODE_BG, leftIndent=10, rightIndent=10,
    spaceAfter=6, spaceBefore=4, leading=12,
    borderPad=6)

style_caption = S("Caption",
    fontName="Helvetica-Oblique", fontSize=8.5, textColor=C_MID_GREY,
    alignment=TA_CENTER, spaceAfter=4)

style_note = S("Note",
    fontName="Helvetica-Oblique", fontSize=8.5, textColor=C_MID_GREY,
    spaceAfter=4, leading=13)

style_formula = S("Formula",
    fontName="Helvetica-BoldOblique", fontSize=9, textColor=C_DARK,
    backColor=C_LIGHT_BG, leftIndent=20, spaceAfter=6,
    spaceBefore=4, leading=16, borderPad=6)

style_th = S("TH",
    fontName="Helvetica-Bold", fontSize=8.5, textColor=C_WHITE,
    alignment=TA_LEFT, leading=12)

style_td = S("TD",
    fontName="Helvetica", fontSize=8.5, textColor=C_DARK,
    leading=12, alignment=TA_LEFT)

style_td_code = S("TDCode",
    fontName="Courier", fontSize=7.5, textColor=C_DARK,
    leading=11, alignment=TA_LEFT)

# ─── Helpers ───────────────────────────────────────────────────────────────────
def H1(text):
    num = text.split(".")[0] if text[0].isdigit() else ""
    return [
        Spacer(1, 0.3*cm),
        HRFlowable(width="100%", thickness=2, color=C_PRIMARY, spaceAfter=4),
        Paragraph(text, style_h1),
        HRFlowable(width="100%", thickness=0.5, color=C_LIGHT_GREY, spaceAfter=6),
    ]

def H2(text):
    return [Paragraph(text, style_h2)]

def H3(text):
    return [Paragraph(text, style_h3)]

def P(text):
    return [Paragraph(text, style_body)]

def B(text, indent=0):
    style = ParagraphStyle("BulletI", parent=style_bullet, leftIndent=16+indent)
    return Paragraph(f"• &nbsp; {text}", style)

def Code(text):
    return [
        Spacer(1, 0.15*cm),
        Paragraph(text.replace(" ", "&nbsp;").replace("\n", "<br/>"), style_code),
        Spacer(1, 0.15*cm),
    ]

def Formula(text):
    return [Paragraph(text, style_formula)]

def HR():
    return [HRFlowable(width="100%", thickness=0.5, color=C_LIGHT_GREY,
                       spaceAfter=6, spaceBefore=6)]

def Note(text):
    return [Paragraph(f"<i>ℹ {text}</i>", style_note)]

def section_badge(text):
    """Colored section number badge using a 1-cell table."""
    t = Table([[Paragraph(text, ParagraphStyle("Badge",
        fontName="Helvetica-Bold", fontSize=9, textColor=C_WHITE,
        alignment=TA_CENTER, leading=11))]],
        colWidths=[1.6*cm], rowHeights=[0.55*cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), C_ACCENT),
        ("ROUNDEDCORNERS", [4]),
        ("TOPPADDING", (0,0), (-1,-1), 2),
        ("BOTTOMPADDING", (0,0), (-1,-1), 2),
    ]))
    return t

def make_table(headers, rows, col_widths=None, alt_rows=True):
    header_row = [Paragraph(h, style_th) for h in headers]
    data = [header_row]
    for row in rows:
        data.append([Paragraph(str(c), style_td) for c in row])
    
    if col_widths is None:
        avail = PAGE_W - 2*MARGIN
        col_widths = [avail / len(headers)] * len(headers)
    
    t = Table(data, colWidths=col_widths, repeatRows=1)
    ts = TableStyle([
        ("BACKGROUND", (0,0), (-1,0), C_PRIMARY),
        ("TEXTCOLOR", (0,0), (-1,0), C_WHITE),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 8.5),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [C_WHITE, C_LIGHT_BG]),
        ("GRID", (0,0), (-1,-1), 0.4, C_LIGHT_GREY),
        ("TOPPADDING", (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("LEFTPADDING", (0,0), (-1,-1), 6),
        ("RIGHTPADDING", (0,0), (-1,-1), 6),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
    ])
    t.setStyle(ts)
    return t

# ─── Cover Page ────────────────────────────────────────────────────────────────
def cover_page():
    elems = []

    # Full-width dark banner via a 1-cell table
    cover_data = [[
        Paragraph("FARMSYNC", style_cover_title),
    ]]
    ct = Table(cover_data, colWidths=[PAGE_W - 2*MARGIN])
    ct.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), C_DARK),
        ("TOPPADDING", (0,0), (-1,-1), 30),
        ("BOTTOMPADDING", (0,0), (-1,-1), 8),
        ("LEFTPADDING", (0,0), (-1,-1), 10),
        ("RIGHTPADDING", (0,0), (-1,-1), 10),
    ]))
    elems.append(ct)

    sub_data = [[
        Paragraph("Evidence-Driven Adaptive AI Orchestration<br/>for Geospatial Intelligence", style_cover_sub),
    ]]
    st = Table(sub_data, colWidths=[PAGE_W - 2*MARGIN])
    st.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), C_PRIMARY),
        ("TOPPADDING", (0,0), (-1,-1), 14),
        ("BOTTOMPADDING", (0,0), (-1,-1), 14),
    ]))
    elems.append(st)
    elems.append(Spacer(1, 1.0*cm))

    # Challenge badge
    badge_data = [[Paragraph(
        "FarmwiseAI Campus Product Challenge &nbsp;|&nbsp; Task 1: Multi-Model, Multimodal &amp; Agentic AI System",
        ParagraphStyle("BadgeText", fontName="Helvetica-Bold", fontSize=10,
            textColor=C_DARK, alignment=TA_CENTER, leading=14))]]
    bt = Table(badge_data, colWidths=[PAGE_W - 2*MARGIN])
    bt.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), C_GOLD),
        ("TOPPADDING", (0,0), (-1,-1), 8),
        ("BOTTOMPADDING", (0,0), (-1,-1), 8),
        ("ROUNDEDCORNERS", [6]),
    ]))
    elems.append(bt)
    elems.append(Spacer(1, 1.2*cm))

    # Metadata card
    meta_rows = [
        ["Registration ID", "TCPC-2026-00071"],
        ["Team Lead", "Safi A"],
        ["Team Member 2", "Mohamed Asfaq S"],
        ["Team Member 3", "Sooraj TS"],
        ["Primary Use Case", "Parcel Evidence & Advisory Intelligence"],
        ["Prototype Window", "2–3 weeks post-shortlisting"],
        ["Core Models", "GPT-4o / Claude 3.5 Sonnet / Qwen2.5-VL-7B"],
    ]
    cell_data = []
    for k, v in meta_rows:
        cell_data.append([
            Paragraph(k, ParagraphStyle("MK", fontName="Helvetica-Bold",
                fontSize=9.5, textColor=C_PRIMARY, leading=13)),
            Paragraph(v, ParagraphStyle("MV", fontName="Helvetica",
                fontSize=9.5, textColor=C_DARK, leading=13)),
        ])
    mt = Table(cell_data, colWidths=[5.5*cm, PAGE_W - 2*MARGIN - 5.5*cm])
    mt.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (0,-1), C_LIGHT_BG),
        ("GRID", (0,0), (-1,-1), 0.4, C_LIGHT_GREY),
        ("TOPPADDING", (0,0), (-1,-1), 6),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
        ("LEFTPADDING", (0,0), (-1,-1), 8),
        ("RIGHTPADDING", (0,0), (-1,-1), 8),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
    ]))
    elems.append(mt)
    elems.append(Spacer(1, 1.0*cm))

    # Thesis statement
    thesis_text = (
        '<b>Core Thesis:</b> FARMSYNC treats AI orchestration as a <i>verified decision problem</i>, '
        'not merely a model-selection problem. The system routes tasks using expected verified utility, '
        'then computes a Model-Agnostic Trust Score (FTS) from independent observable evidence to determine '
        'whether claims are sufficiently proven before answering — or explicitly abstains.'
    )
    thesis_data = [[Paragraph(thesis_text, ParagraphStyle("Thesis",
        fontName="Helvetica", fontSize=9.5, textColor=C_DARK,
        leading=15, alignment=TA_JUSTIFY))]]
    tt = Table(thesis_data, colWidths=[PAGE_W - 2*MARGIN])
    tt.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), C_LIGHT_BG),
        ("LEFTPADDING", (0,0), (-1,-1), 14),
        ("RIGHTPADDING", (0,0), (-1,-1), 14),
        ("TOPPADDING", (0,0), (-1,-1), 12),
        ("BOTTOMPADDING", (0,0), (-1,-1), 12),
        ("LINEAFTER", (0,0), (0,-1), 3, C_ACCENT),
    ]))
    elems.append(tt)
    elems.append(PageBreak())
    return elems

# ─── Build Story ───────────────────────────────────────────────────────────────
story = []
story.extend(cover_page())

avail_w = PAGE_W - 2*MARGIN

# ════════════════════════════════════════════════════════
# WHY THIS IS A STRONG TASK 1 FIT
# ════════════════════════════════════════════════════════
story.extend(H1("Why This Is a Strong Task 1 Fit"))
why_rows = [
    ["Multi-Model Orchestration",
     "Dynamically routes across GPT-4o / Claude 3.5 Sonnet (complex planning), Gemini 1.5 Pro (verification), and open-weight Qwen2.5-VL (low-cost vision). Final model selection benchmarked after credit confirmation."],
    ["Multimodal Intelligence",
     "Ingests text queries, scanned land records (PDF), field ground photos, and PostGIS vector GIS layers in a single unified workflow."],
    ["Agentic Routing & Recovery",
     "Verified-Utility Router (Quality – Cost – Latency – Risk) selects models and tools; bounded escalation and explicit abstention when evidence is insufficient."],
    ["Deterministic-First Verification",
     "Spatial containment, distance buffers, and numeric area math computed by PostGIS / Python, not guessed by language models."],
    ["Observable Telemetry",
     "Interactive UI panel shows live task graph, routing rationale, latency per step, API cost, and evidence graph — agent behaviour fully visible to evaluators."],
]
story.append(make_table(
    ["Requirement", "FARMSYNC Implementation"],
    why_rows,
    col_widths=[4.5*cm, avail_w - 4.5*cm]
))
story.append(Spacer(1, 0.3*cm))

# ════════════════════════════════════════════════════════
# SECTION 1
# ════════════════════════════════════════════════════════
story.extend(H1("1. Chosen Challenge, Title and Objective"))
story.extend(H2("Project Title"))
story.extend(P("FARMSYNC — Evidence-Driven Adaptive AI Orchestration for Geospatial Intelligence"))
story.extend(H2("Objective"))
story.extend(P(
    "Build and demonstrate a reusable, generic agentic AI system that accepts text requests, land documents, "
    "field photographs, and spatial datasets; compiles requests into execution graphs; routes subtasks across "
    "proprietary and open-weight models; verifies claims via deterministic tools; and produces a source-traceable "
    "final answer with visible routing telemetry."
))
story.extend(H2("Primary Demonstration Scenario"))

demo_box_text = (
    '"Using the supplied land document and field photograph for Devapura village, identify Survey Number 144/3B, '
    'verify its parcel boundary and registered owner, predict the crop type and growth stage from the field image, '
    'retrieve the applicable fertilizer advisory, perform spatial proximity checks against restricted waterbody zones, '
    'and return a source-traceable verified recommendation."'
)
demo_data = [[Paragraph(demo_box_text, ParagraphStyle("DemoQ",
    fontName="Helvetica-Oblique", fontSize=9.5, textColor=C_DARK,
    leading=14, alignment=TA_JUSTIFY))]]
dt = Table(demo_data, colWidths=[avail_w])
dt.setStyle(TableStyle([
    ("BACKGROUND", (0,0), (-1,-1), C_LIGHT_BG),
    ("LINEAFTER", (0,0), (0,-1), 3, C_ACCENT),
    ("LEFTPADDING", (0,0), (-1,-1), 14),
    ("RIGHTPADDING", (0,0), (-1,-1), 12),
    ("TOPPADDING", (0,0), (-1,-1), 10),
    ("BOTTOMPADDING", (0,0), (-1,-1), 10),
]))
story.append(dt)
story.append(Spacer(1, 0.25*cm))

story.extend(H3("What FARMSYNC Executes (7-Step Pipeline):"))
steps = [
    ("1. Task Compiler", "Converts query into a typed 7-task execution DAG with explicit dependencies."),
    ("2. Document & Registry Join", "Extracts owner and survey details from scanned PDF, matched against registry SQL records."),
    ("3. Open-Weight Vision Perception", "Passes field photo to Qwen2.5-VL-7B for low-cost first-pass crop/stage classification."),
    ("4. Deterministic Spatial Verification", "Invokes PostGIS (ST_Contains, ST_Distance) for exact parcel boundary and buffer checks."),
    ("5. Trust Score Evaluation", "Computes FTS; if evidence/confidence is below threshold, auto-escalates to Claude 3.5 Sonnet."),
    ("6. RAG Advisory Synthesis", "Retrieves stage-specific fertilizer advisory from indexed agronomy documents."),
    ("7. Traceable Output", "Returns verified result with interactive map, evidence DAG, and cost/latency telemetry."),
]
for step, desc in steps:
    story.append(Paragraph(
        f"<b>{step}</b>: {desc}", style_bullet))

story.append(Spacer(1, 0.3*cm))

# ════════════════════════════════════════════════════════
# SECTION 2
# ════════════════════════════════════════════════════════
story.extend(H1("2. Problem Understanding"))
story.extend(P(
    "Complex geospatial and agricultural workflows depend on heterogeneous data sources — scanned paper documents, "
    "ground photographs, satellite vector layers, and registry databases. Single-model prompts fail because no "
    "single model is simultaneously economical, deterministically accurate at spatial math, and perfectly calibrated "
    "for all task types. FARMSYNC addresses five core failure modes in current AI systems:"
))

problems = [
    ("Unverified Advisory", "Advisory generated without traceable evidence from approved agronomy sources."),
    ("Model Confidence Fallacy", "Vendor-reported confidence scores are uncalibrated and non-comparable across models from different providers."),
    ("Deterministic Math Failure", "Relying on LLMs for geometric calculations (area, distance, containment) introduces hallucinations."),
    ("Opaque Routing & Cost Waste", "Using premium models for routine OCR/perception wastes compute; static routing lacks adaptability."),
    ("Forced Predictions", "Systems without an abstention mechanism generate hallucinated answers when evidence is missing."),
]
story.append(make_table(
    ["Failure Mode", "Root Cause"],
    problems,
    col_widths=[4.5*cm, avail_w - 4.5*cm]
))
story.append(Spacer(1, 0.25*cm))
story.extend(H2("Working Principle"))
story.extend(Formula(
    "Understand  →  Compile Task Graph  →  Route (Verified Utility)  →  Ground & Execute  "
    "→  Verify (FTS)  →  Accept / Escalate / Abstain"
))
story.extend(P(
    "If required evidence cannot be verified, FARMSYNC refuses to invent missing facts. It escalates to an alternate "
    "model route or explicitly abstains and flags for human review — never manufacturing a confident answer."
))

# ════════════════════════════════════════════════════════
# SECTION 3
# ════════════════════════════════════════════════════════
story.extend(H1("3. What We Propose to Build and Demonstrate"))
story.extend(P(
    "FARMSYNC delivers a complete AI orchestration workspace that turns multimodal geospatial requests into "
    "verified operational answers. The evaluator will see the following demonstrations:"
))

demo_rows = [
    ["Multimodal Query Ingestion", "Upload land document PDF + field photo + natural language query for Survey 144/3B."],
    ["Dynamic Execution Graph", "Visual task DAG panel showing 7 subtasks, dependencies, and live execution status."],
    ["Adaptive Model Routing", "Telemetry showing routine perception sent to Qwen2.5-VL and complex tasks escalated to GPT-4o / Claude 3.5 Sonnet."],
    ["Deterministic Spatial Check", "PostGIS computing exact geometric area and distance buffers — no LLM hallucination."],
    ["Evidence Graph Provenance", "Interactive claim-to-source DAG linking findings to source documents, SQL records, and GIS layers."],
    ["Trust Engine & Recovery", "FTS evaluated live; auto-escalation on low confidence; explicit abstention on missing evidence."],
    ["Unseen Request Benchmark", "Land Acquisition Discrepancy query executed without changing a single line of orchestration code."],
    ["Baseline Comparison", "Live dashboard: FARMSYNC vs. Pure GPT-4o vs. Static Routing — >50% cost savings with zero accuracy loss."],
]
story.append(make_table(
    ["Demonstration Feature", "What the Evaluator Sees"],
    demo_rows,
    col_widths=[5.2*cm, avail_w - 5.2*cm]
))

story.append(Spacer(1, 0.25*cm))
story.extend(H2("Unseen Request — Generic Architecture Proof (Query 2)"))
story.extend(P(
    "To demonstrate that FARMSYNC is a generic control plane and not a hard-coded single-query pipeline, "
    "the system executes a completely different request without code changes:"
))
q2_data = [[Paragraph(
    '"Read uploaded land acquisition notice Acquisition_2024_04.pdf, extract all survey numbers and listed extents, '
    'cross-check against the PostGIS cadastral layer and registry database, flag extent discrepancies exceeding 5% '
    'or ownership mismatches, and present findings on a synchronized map."',
    ParagraphStyle("Q2", fontName="Helvetica-Oblique", fontSize=9.5, textColor=C_DARK,
        leading=14, alignment=TA_JUSTIFY))]]
q2t = Table(q2_data, colWidths=[avail_w])
q2t.setStyle(TableStyle([
    ("BACKGROUND", (0,0), (-1,-1), HexColor("#FEF9E7")),
    ("LINEAFTER", (0,0), (0,-1), 3, C_GOLD),
    ("LEFTPADDING", (0,0), (-1,-1), 14),
    ("RIGHTPADDING", (0,0), (-1,-1), 12),
    ("TOPPADDING", (0,0), (-1,-1), 10),
    ("BOTTOMPADDING", (0,0), (-1,-1), 10),
]))
story.append(q2t)
story.extend(Note(
    "When Query 2 is submitted, the Task Graph Compiler dynamically generates an OCR → Entity Extraction "
    "→ Database Join → PostGIS Intersection → Discrepancy Flagging DAG, without modifying any orchestration code."
))

# ════════════════════════════════════════════════════════
# SECTION 4
# ════════════════════════════════════════════════════════
story.extend(H1("4. Solution Approach, Architecture, Models and Technology"))

story.extend(H2("4.1  System Architecture"))
story.extend(Code(
    "                         USER REQUEST\n"
    "                               |\n"
    "                               v\n"
    "                   +---------------------+\n"
    "                   | TASK GRAPH COMPILER |\n"
    "                   +----------+----------+\n"
    "                              | typed subtasks\n"
    "                              v\n"
    "                   +---------------------+\n"
    "                   | CAPABILITY REGISTRY |\n"
    "                   +----------+----------+\n"
    "                              |\n"
    "                              v\n"
    "                   +------------------------+\n"
    "                   | VERIFIED-UTILITY ROUTER|\n"
    "                   +----------+-------------+\n"
    "         __________|__________|___________\n"
    "         |                   |           |\n"
    "         v                   v           v\n"
    "  OPEN-WEIGHT MODEL   PROPRIETARY A   PROPRIETARY B\n"
    "  (Qwen2.5-VL-7B)    (GPT-4o /        (Gemini 1.5 Pro)\n"
    "                      Claude 3.5)\n"
    "         |___________________|___________|\n"
    "                              |\n"
    "                              v\n"
    "                   +---------------------+\n"
    "                   |   GROUNDED TOOLS    |\n"
    "                   |  PostGIS / SQL /    |\n"
    "                   |  PaddleOCR / RAG    |\n"
    "                   +----------+----------+\n"
    "                              |\n"
    "                              v\n"
    "                   +---------------------+\n"
    "                   |   EVIDENCE GRAPH    |\n"
    "                   +----------+----------+\n"
    "                              |\n"
    "                              v\n"
    "                   +---------------------+\n"
    "                   |    TRUST ENGINE     |\n"
    "                   +----+--------+-------+\n"
    "                        |        |       |\n"
    "                        v        v       v\n"
    "                    ACCEPT   ESCALATE  ABSTAIN\n"
    "                              |       |\n"
    "                           Alt Route Human Review\n"
    "                        |__________|___________|\n"
    "                                   |\n"
    "                                   v\n"
    "                           VERIFIED RESULT"
))

story.extend(H2("4.2  Core Technical Formulations"))
story.extend(H3("Verified-Utility Router Policy"))
story.extend(P(
    "Instead of asking 'which model is smartest?', the router optimizes expected utility after verification:"
))
story.extend(Formula(
    "Expected Verified Utility  =  Expected Verified Quality\n"
    "                            −  λ · Cost  −  μ · Latency  −  ρ · Failure Risk\n"
    "                            +  η · Verification Gain"
))

story.extend(H3("Model-Agnostic Trust Score (FTS)"))
story.extend(P(
    "Vendor confidence scores are uncalibrated and non-comparable across model providers. "
    "FARMSYNC computes trust strictly from independent, observable evidence:"
))
story.extend(Formula(
    "FTS  =  w₁·Calibration  +  w₂·EvidenceCoverage  +  w₃·SourceConsistency\n"
    "      +  w₄·DeterministicValidation  +  w₅·OutputValidity  −  w₆·ConflictPenalty"
))

fts_rows = [
    ["Calibration (w₁)", "Historical reliability of model/task pair on validation set", "Vision accuracy on supported crop classes"],
    ["Evidence Coverage (w₂)", "Proportion of claim directly supported by retrieved evidence", "Owner claim supported by document + database"],
    ["Source Consistency (w₃)", "Agreement between independent sources", "Document owner matches registry owner"],
    ["Deterministic Validation (w₄)", "Exact computational/rule-based checks", "GIS containment, area delta, polygon check"],
    ["Output Validity (w₅)", "Schema, type, and structural constraint validity", "Required fields present; valid geometry/numbers"],
    ["Conflict Penalty (w₆)", "Contradictory evidence or out-of-distribution inputs", "Two sources disagree; image outside distribution"],
]
story.append(make_table(
    ["Signal", "Meaning", "Concrete Example"],
    fts_rows,
    col_widths=[3.5*cm, 5.8*cm, avail_w - 9.3*cm]
))
story.extend(Note(
    "Hyperparameter Safeguard: Weights w₁…w₆ normalized via min-max feature scaling on an initial "
    "20-sample validation set. Default: equal weights (wᵢ = 1/6) when N < 10."
))

story.extend(H2("4.3  Agentic Control Loop"))
loop_steps = [
    ("Understand & Compile", "LLM converts user query into typed task DAG. Fallback: malformed DAG triggers pre-validated linear workflow template."),
    ("Match Capabilities", "Query capability registry for available models, tools, and latency/cost specs."),
    ("Route", "Select route maximizing Expected Verified Utility."),
    ("Ground & Execute", "Run models for perception/synthesis; run PostGIS/SQL/Python for exact deterministic facts."),
    ("Build Evidence Graph", "Construct in-memory DAG linking claims to source documents and GIS polygons."),
    ("Verify & Recover", "FTS ≥ 0.85 → ACCEPT | 0.60 ≤ FTS < 0.85 → ESCALATE | FTS < 0.60 → ABSTAIN"),
]
for step, desc in loop_steps:
    story.append(Paragraph(f"<b>{step}</b>: {desc}", style_bullet))

story.append(Spacer(1, 0.3*cm))

# ════════════════════════════════════════════════════════
# SECTION 5
# ════════════════════════════════════════════════════════
story.extend(H1("5. Main Components and Prototype Capabilities"))

comp_rows = [
    ["Task Graph Compiler", "FastAPI + GPT-4o / Instructor", "Deconstructs request into typed subtask DAG; automatic fallback to linear templates on malformed output."],
    ["Capability Registry", "Python Registry Engine", "Dynamic performance, cost ($/1k tokens), latency, and capability profiles of all models/tools."],
    ["Verified-Utility Router", "Lightweight Scored Policy Engine", "RouteScore per subtask routes work economically without quality loss."],
    ["Document & OCR Engine", "PaddleOCR + PyMuPDF", "Extracts survey numbers, owners, and extents from scanned Patta/acquisition PDFs."],
    ["Deterministic Spatial Engine", "PostgreSQL / PostGIS + GeoPandas", "ST_Contains, ST_Distance, area delta — exact geometric computation."],
    ["Open-Weight Vision Model", "Qwen2.5-VL-7B (vLLM / Ollama)", "Low-cost first-pass crop classification, growth stage, and visual feature extraction."],
    ["Proprietary Multimodal VLM", "Claude 3.5 Sonnet / GPT-4o API", "Complex planning, document-to-parcel resolution, escalation verification."],
    ["Agronomy RAG System", "LangChain / LlamaIndex + FAISS", "Stage-appropriate fertilizer/management recommendations with page citations."],
    ["Trust & Verification Engine", "Custom Python Engine", "Computes FTS, checks deterministic constraints, governs bounded escalation/abstention."],
    ["Interactive Telemetry UI", "React.js + Leaflet + CSS", "Synchronized map, task DAG panel, evidence graph, cost/latency counters, baseline charts."],
]
story.append(make_table(
    ["Component", "Technology", "Prototype Capability"],
    comp_rows,
    col_widths=[3.8*cm, 3.8*cm, avail_w - 7.6*cm]
))

# ════════════════════════════════════════════════════════
# SECTION 6
# ════════════════════════════════════════════════════════
story.extend(H1("6. Innovative and Exploratory Ideas"))

story.extend(H2("6.1  Refuse-to-Invent Principle (Bounded Abstention)"))
story.extend(P(
    "FARMSYNC guarantees that an ungrounded or contradictory claim will never be presented as verified advice. "
    "This is a hard architectural constraint, not a post-hoc filter:"
))
abstain_cases = [
    "If land document owner differs from database registry: result flagged as CONFLICT_DISCREPANCY.",
    "If field photo is blurry or out-of-distribution: open-weight model returns low FTS → Proprietary VLM Escalation.",
    "If alternate route also fails verification: system enters explicit ABSTAIN_HUMAN_REVIEW state.",
]
for c in abstain_cases:
    story.append(B(c))

story.extend(H2("6.2  In-Memory JSON Evidence Graph DAG"))
story.extend(P(
    "Rather than deploying heavy graph database infrastructure (Neo4j), FARMSYNC builds an in-memory "
    "Directed Acyclic Graph JSON structure passed through shared execution state — full claim-to-source "
    "traceability with zero database overhead:"
))
story.extend(Code(
    '{\n'
    '  "claim_id": "CLM-2026-DEV-144",\n'
    '  "survey_number": "144/3B",\n'
    '  "village": "Devapura",\n'
    '  "extracted_owner": "Ramesh Kumar",\n'
    '  "source_evidence": [\n'
    '    { "type": "DOCUMENT_OCR",     "ref": "Acquisition_04.pdf#P2",  "confidence": 0.91 },\n'
    '    { "type": "DATABASE_REGISTRY","ref": "Land_Registry.parcels",  "confidence": 1.0  }\n'
    '  ],\n'
    '  "deterministic_checks": {\n'
    '    "postgis_containment_valid": true,\n'
    '    "extent_mismatch_pct": 0.0,\n'
    '    "waterbody_buffer_conflict": false\n'
    '  },\n'
    '  "trust_metrics": {\n'
    '    "model_reported_confidence": 0.84,\n'
    '    "task_trust_score_fts": 0.95,\n'
    '    "verification_status": "VERIFIED_ACCEPTED"\n'
    '  },\n'
    '  "routing_telemetry": {\n'
    '    "primary_model": "Qwen2.5-VL-7B",\n'
    '    "escalation_model": "Claude-3.5-Sonnet",\n'
    '    "was_escalated": true,\n'
    '    "total_latency_ms": 1120,\n'
    '    "estimated_cost_usd": 0.0038\n'
    '  }\n'
    '}'
))

story.extend(H2("6.3  Built-In Multi-Baseline Benchmarking"))
story.extend(P(
    "The UI includes real-time telemetry comparing FARMSYNC against two baselines on every evaluation query, "
    "proving quality retention while demonstrating explicit cost and latency reductions:"
))
base_rows = [
    ["Premium-Only", "Strongest proprietary model for every AI step", "Measures cost/latency savings of adaptive routing"],
    ["Static Routing", "Fixed model choice by task type; no verification or escalation", "Measures value of adaptive routing + trust scoring"],
    ["FARMSYNC", "Verified-Utility Route + Deterministic Tools + FTS", "Full proposed architecture — primary evaluation target"],
]
story.append(make_table(
    ["Baseline", "Definition", "Purpose"],
    base_rows,
    col_widths=[3.5*cm, 7.0*cm, avail_w - 10.5*cm]
))

# ════════════════════════════════════════════════════════
# SECTION 7
# ════════════════════════════════════════════════════════
story.extend(H1("7. Data, Compute and Model Access Requirements"))
story.extend(P(
    "To develop and demonstrate the working prototype within the 2–3 week Stage 2 sprint, "
    "FARMSYNC requires the following resources from FarmwiseAI:"
))

resource_rows = [
    ["Cadastral Parcel GIS Layer", "Vector boundaries, survey numbers, and geometries for 1–2 sample villages.", "Required — GeoJSON / Shapefile format"],
    ["Land Record Documents", "Scanned Patta documents and land acquisition notices.", "Required — Sample PDF dataset"],
    ["Field Ground Photographs", "Sample crop images with GPS metadata.", "Required — Sample image dataset"],
    ["Agronomy Advisory Corpus", "TNAU / ICAR crop advisory and fertilizer recommendation manuals.", "Required — Reference PDFs for RAG indexing"],
    ["PostgreSQL + PostGIS", "Spatial database for deterministic geometric computation.", "Local / Cloud container (provided or self-hosted)"],
    ["Open-Weight VLM Compute", "GPU instance to serve Qwen2.5-VL-7B via vLLM / Ollama.", "AWS g5.xlarge / equivalent GPU credits"],
    ["Proprietary Model APIs", "Primary planning and secondary verification LLM access.", "API credits: OpenAI GPT-4o + Anthropic Claude 3.5 Sonnet"],
]
story.append(make_table(
    ["Resource", "Role in FARMSYNC", "Status / Requirement"],
    resource_rows,
    col_widths=[3.8*cm, 7.0*cm, avail_w - 10.8*cm]
))

# ════════════════════════════════════════════════════════
# SECTION 8
# ════════════════════════════════════════════════════════
story.extend(H1("8. Two-to-Three-Week Project Plan"))

plan_rows = [
    ["Days 1–3", "Architecture & Foundations", "PostgreSQL/PostGIS schema, API wrappers, Qwen2.5-VL container, project skeleton."],
    ["Days 4–7", "Planning & Routing", "Task Graph Compiler, Capability Registry, Scored Router, fallback templates."],
    ["Days 8–11", "Multimodal Execution", "PaddleOCR, PostGIS spatial queries, RAG advisory retrieval, in-memory Evidence Graph."],
    ["Days 12–14", "Trust & Recovery Engine", "FTS engine, calibration scaler, bounded escalation, abstention handlers."],
    ["Days 15–17", "Product Integration & UI", "React frontend, Leaflet map, DAG trace panel, evidence graph, route telemetry."],
    ["Days 18–19", "Evaluation & Benchmarking", "Baseline comparison (3 baselines), unseen query testing, failure injection."],
    ["Days 20–21", "Demo Freeze & Documentation", "Code cleanup, deployment verification, demo recording, final documentation."],
]
story.append(make_table(
    ["Period", "Milestone", "Deliverable"],
    plan_rows,
    col_widths=[2.2*cm, 4.0*cm, avail_w - 6.2*cm]
))
story.extend(Note(
    "Final Deliverables: Working web application, live orchestrator trace, cost/latency telemetry dashboard, "
    "evidence graph inspector, baseline benchmark report."
))

# ════════════════════════════════════════════════════════
# SECTION 9
# ════════════════════════════════════════════════════════
story.extend(H1("9. Team and Responsibilities"))

team_rows = [
    ["Safi A\n(Team Lead)", "TCPC-2026-00071\nAI & Orchestration Lead",
     "Task Graph Compiler, Capability Registry, Verified-Utility Router, API integration, project leadership & team coordination."],
    ["Mohamed Asfaq S", "TCPC-2026-00071\nAI Trust & Verification Lead",
     "Trust Score (FTS) formulation, min-max calibration scaler, deterministic verification rules, bounded recovery manager, baseline evaluation suite."],
    ["Sooraj TS", "TCPC-2026-00071\nGeoAI, Full-Stack & UI Lead",
     "PostgreSQL/PostGIS setup, PaddleOCR & RAG pipeline, React + Leaflet interactive UI, execution trace, evidence graph visualization."],
]
story.append(make_table(
    ["Member", "ID / Role", "Primary Responsibility"],
    team_rows,
    col_widths=[3.2*cm, 4.2*cm, avail_w - 7.4*cm]
))

# ════════════════════════════════════════════════════════
# SECTION 10
# ════════════════════════════════════════════════════════
story.extend(H1("10. Feasibility, Risks and Success Criteria"))

story.extend(H2("10.1  Risk Mitigation Strategy"))
risk_rows = [
    ["LLM Task Compiler Malformed DAG", "Closed JSON task schema + automatic fallback to pre-validated linear workflow template."],
    ["Trust Score Calibration Data Shortage", "Min-max scaling on 20-sample validation set; equal-weighted fallback (wᵢ = 1/6) when N < 10."],
    ["Open-Weight VLM Latency / Hosting", "Serve Qwen2.5-VL-7B via vLLM with quantized weights; fallback to GPT-4o-mini if GPU credit unavailable."],
    ["Scripted Happy Path Perception", "Test pipeline on low-confidence field photos, conflicting owner names, and unseen land acquisition queries."],
    ["Unbounded Recursive Agent Loops", "Cap recovery to 1 alternate route before explicit ABSTAIN_HUMAN_REVIEW — no infinite loops."],
    ["API Provider Changes / Access Issues", "Provider-agnostic model adapter layer; final providers benchmarked after approved access is confirmed."],
]
story.append(make_table(
    ["Risk Factor", "Mitigation Approach"],
    risk_rows,
    col_widths=[5.0*cm, avail_w - 5.0*cm]
))

story.extend(H2("10.2  Success Criteria"))
story.extend(P("The FARMSYNC prototype will demonstrate success when all of the following conditions are met:"))
criteria = [
    "A multimodal request is compiled into a structured task graph and executed across heterogeneous models and tools without manual intervention.",
    "Routine vision perception is handled economically by the open-weight model (Qwen2.5-VL), with complex tasks escalating to proprietary VLMs.",
    "Spatial operations (distance, containment, area) are computed deterministically via PostGIS with zero LLM hallucination.",
    "All claims are backed by a transparent Evidence Graph DAG linked to source documents, SQL records, and spatial layers.",
    "Injected failures and missing evidence trigger bounded escalation or explicit abstention rather than forced predictions.",
    "FARMSYNC demonstrates ≥50% cost reduction over pure GPT-4o baselines on benchmark evaluation queries.",
]
for c in criteria:
    story.append(B(c))

story.append(Spacer(1, 0.5*cm))
story.extend(HR())

# ── Appendix ──
story.extend(H1("Appendix A — Task 1 Requirement Coverage Checklist"))
check_rows = [
    ["Planner / Orchestrator", "Task Graph Compiler with fallback linear workflow template"],
    ["2+ Proprietary Models", "GPT-4o (Planning) + Claude 3.5 Sonnet / Gemini 1.5 Pro (Verification)"],
    ["1 Open-Weight / Smaller Model", "Qwen2.5-VL-7B / Llama-3.2-Vision (Low-cost first-pass vision/OCR)"],
    ["Model Router", "Verified-Utility Router (Quality − Cost − Latency − Risk + Verification Gain)"],
    ["Task / Cost / Latency Routing", "Capability Registry + Scored Route Telemetry Dashboard"],
    ["Tool / Data Connectors", "OCR (PaddleOCR), Database (PostgreSQL), GIS (PostGIS), RAG, Python"],
    ["Structured Outputs", "Typed Task Graph + VerifiedResultObject JSON Schema"],
    ["Verifier / Critic", "Trust Engine (FTS) + Deterministic GIS / Rule Validation"],
    ["Fallback / Recovery", "Bounded alternate route escalation + explicit abstention state"],
    ["Shared State / Memory", "Execution state dict + In-memory Evidence Graph DAG"],
    ["Multimodal Inputs", "Text + Documents + Images + Structured Data + Spatial GIS Layers"],
    ["2+ Meaningful Tool Calls", "OCR, PostGIS spatial queries, RAG retrieval, Database joins"],
    ["Visible Route, Latency, Cost", "Live Telemetry & Execution Trace UI Panel"],
    ["Unseen Comparable Request", "Land Acquisition Discrepancy Query (Query 2) without code changes"],
    ["No Hard-Coded Answers", "Dynamic DAG compilation and capability-based routing"],
]
story.append(make_table(
    ["FarmwiseAI Requirement", "FARMSYNC Implementation Response"],
    check_rows,
    col_widths=[5.5*cm, avail_w - 5.5*cm]
))

# ── Footer note ──
story.append(Spacer(1, 0.6*cm))
footer_data = [[Paragraph(
    "FARMSYNC &nbsp;|&nbsp; TCPC-2026-00071 &nbsp;|&nbsp; "
    "Safi A &nbsp;•&nbsp; Mohamed Asfaq S &nbsp;•&nbsp; Sooraj TS &nbsp;|&nbsp; "
    "FarmwiseAI Campus Product Challenge 2026",
    ParagraphStyle("Footer", fontName="Helvetica", fontSize=8,
        textColor=C_WHITE, alignment=TA_CENTER, leading=12))]]
ft = Table(footer_data, colWidths=[avail_w])
ft.setStyle(TableStyle([
    ("BACKGROUND", (0,0), (-1,-1), C_DARK),
    ("TOPPADDING", (0,0), (-1,-1), 8),
    ("BOTTOMPADDING", (0,0), (-1,-1), 8),
]))
story.append(ft)

# ─── Build PDF ────────────────────────────────────────────────────────────────
doc.build(story)
print(f"PDF generated: {output_path}")
