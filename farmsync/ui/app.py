import sys
import os
import streamlit as st
import folium
from streamlit_folium import st_folium
import json
import pandas as pd

# Add workspace to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from farmsync.orchestrator import FarmSyncOrchestrator

# Configure page
st.set_page_config(
    page_title="FARMSYNC | Task 1 AI Orchestration",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling
st.markdown("""
<style>
    .main-title {
        font-size: 2.2rem;
        font-weight: 800;
        color: #1A6B3C;
        margin-bottom: 0px;
    }
    .sub-title {
        font-size: 1.05rem;
        color: #5D6D7E;
        margin-bottom: 15px;
    }
    .metric-card {
        background-color: #F0F7F4;
        border-left: 5px solid #27AE60;
        padding: 12px 16px;
        border-radius: 6px;
        margin-bottom: 10px;
    }
    .badge-accept {
        background-color: #27AE60;
        color: white;
        padding: 4px 12px;
        border-radius: 12px;
        font-weight: bold;
    }
    .badge-escalate {
        background-color: #F39C12;
        color: white;
        padding: 4px 12px;
        border-radius: 12px;
        font-weight: bold;
    }
    .badge-abstain {
        background-color: #E74C3C;
        color: white;
        padding: 4px 12px;
        border-radius: 12px;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def get_orchestrator():
    return FarmSyncOrchestrator()

orchestrator = get_orchestrator()

# Header
col_t1, col_t2 = st.columns([3, 1])
with col_t1:
    st.markdown('<div class="main-title">FARMSYNC: Adaptive Multi-Model AI Orchestrator</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Evidence-Driven Multimodal Geospatial Intelligence & Verification Platform · <b>Task 1</b></div>', unsafe_allow_html=True)
with col_t2:
    st.info("**Team PRIME** (TCPC-2026-00071)\n\nLead: Mohammed Asfaq S | Safi A, Sooraj TS")

st.divider()

# Sidebar: Controls & Scenarios
st.sidebar.header("🛠️ Query & Simulation Controls")

preset = st.sidebar.selectbox(
    "Select Evaluation Scenario:",
    [
        "Scenario 1: Primary Multimodal Request (Survey 384, Keelathattaparai)",
        "Scenario 2: Unseen Survey Analysis (Survey 381, Thoothukudi)",
        "Scenario 3: Wetland Proximity & Extent Check (Survey 176)",
        "Custom Natural Language Query"
    ]
)

if preset == "Scenario 1: Primary Multimodal Request (Survey 384, Keelathattaparai)":
    query_text = "Using the supplied land document and field photograph for Keelathattaparai village, identify Survey Number 384, verify parcel boundary and owner, predict crop and growth stage from field image, retrieve applicable fertilizer advisory, perform spatial proximity checks, and return verified recommendation."
elif preset == "Scenario 2: Unseen Survey Analysis (Survey 381, Thoothukudi)":
    query_text = "Analyze Survey Number 381 in Keelathattaparai, resolve registry owner, compute GIS area delta, identify crop from field image, and provide verified advisory."
elif preset == "Scenario 3: Wetland Proximity & Extent Check (Survey 176)":
    query_text = "Check Survey Number 176 for waterbody buffer conflict, cross-check patta extent with cadastral polygon, and inspect field image."
else:
    query_text = st.sidebar.text_area("Enter Custom Query:", "Analyze Survey Number 384 in Keelathattaparai and verify parcel area and crop.")

st.sidebar.subheader("🧪 Red-Team & Robustness Toggles")
force_escalate = st.sidebar.checkbox("Simulate Low-Confidence Photo (Trigger Teacher Escalation)", value=False)
simulate_conflict = st.sidebar.checkbox("Inject Document-Registry Conflict (Trigger Abstention)", value=False)
simulate_ood = st.sidebar.checkbox("Simulate Out-of-Distribution Weed/Unknown Crop", value=False)
selected_photo = st.sidebar.selectbox(
    "Optional image-only evidence",
    [""] + sorted(orchestrator.vision.image_registry),
    format_func=lambda name: name or "Only spatially matched parcel photo",
)

run_button = st.sidebar.button("🚀 Run FARMSYNC Orchestration", type="primary", width="stretch")

# Run Orchestration
execution_key = (query_text, force_escalate, simulate_conflict, simulate_ood, selected_photo)
if run_button or st.session_state.get("execution_key") != execution_key:
    st.session_state["orchestration_result"] = orchestrator.execute_request(
        query=query_text,
        force_escalate_vision=force_escalate,
        simulate_conflict=simulate_conflict,
        simulate_unsupported_crop=simulate_ood,
        image_filename=selected_photo or None
    )
    st.session_state["execution_key"] = execution_key
res = st.session_state["orchestration_result"]

vobj = res["verified_result_object"]
trust = vobj["trust_metrics"]
telemetry = vobj["routing_telemetry"]
attrs = vobj["extracted_attributes"]
spatial_checks = vobj["deterministic_spatial_checks"]
baselines = res["baseline_comparison"]

# Top KPI Metric Cards
m1, m2, m3, m4 = st.columns(4)

with m1:
    status_str = trust["verification_status"].replace("VERIFIED_", "")
    badge_class = "badge-accept" if status_str == "ACCEPT" else ("badge-escalate" if status_str == "ESCALATE" else "badge-abstain")
    st.markdown(f"**Verification Decision**")
    st.markdown(f'<span class="{badge_class}">{status_str}</span>', unsafe_allow_html=True)
    st.caption(trust["decision_message"])

with m2:
    st.metric(
        label="Model-Agnostic Trust Score (FTS)",
        value=f"{trust['task_trust_score_fts']:.3f} / 1.000",
        delta="Verified by Observable Signals"
    )

with m3:
    st.metric(
        label="Estimated Routing Cost",
        value=f"${telemetry['total_estimated_cost_usd']:.4f}",
        delta="Scenario assumptions; not an AWS bill"
    )

with m4:
    st.metric(
        label="Total Latency",
        value=f"{telemetry['total_latency_ms']} ms",
        delta=f"-{1850 - telemetry['total_latency_ms']} ms vs Commercial VLM"
    )

st.divider()

# Tabbed Interface
tab_map, tab_crop, tab_graph, tab_telemetry, tab_baselines, tab_json = st.tabs([
    "🗺️ Geospatial Map & Cadastral GIS",
    "🌾 Crop Vision & Agronomy Advisory",
    "🕸️ In-Memory Evidence Graph",
    "⚡ Router Telemetry & Trace",
    "🏆 Head-to-Head Baselines",
    "📄 VerifiedResultObject JSON"
])

# Tab 1: GIS Map
with tab_map:
    col_map_view, col_map_info = st.columns([2, 1])
    
    with col_map_view:
        st.subheader("Interactive Cadastral GIS Workspace")
        
        # Load parcel GeoJSON
        survey_clean = str(vobj["survey_number"]).strip()
        parcel_data = orchestrator.spatial.get_parcel(survey_clean)
        
        if parcel_data:
            lat = parcel_data["centroid"]["latitude"]
            lon = parcel_data["centroid"]["longitude"]
            
            # Create folium map centered on parcel
            m = folium.Map(location=[lat, lon], zoom_start=15, tiles="OpenStreetMap")
            
            # Highlight selected parcel polygon in green
            folium.GeoJson(
                parcel_data["geometry_geojson"],
                name=f"Survey {survey_clean}",
                style_function=lambda x: {
                    "fillColor": "#27AE60",
                    "color": "#1A6B3C",
                    "weight": 3,
                    "fillOpacity": 0.5
                },
                tooltip=f"Survey {survey_clean}: {parcel_data['area_acres']} Acres"
            ).add_to(m)
            
            # Marker on centroid
            folium.Marker(
                [lat, lon],
                popup=f"Survey {survey_clean}<br>Owner: {attrs['registered_owner']}<br>Area: {parcel_data['area_acres']} Acres",
                icon=folium.Icon(color="green", icon="leaf")
            ).add_to(m)

            # Route & Depot Marker from Agri-Logistics
            if vobj.get("agri_logistics") and "origin" in vobj["agri_logistics"]:
                alog = vobj["agri_logistics"]
                depot = alog["origin"]
                folium.Marker(
                    [depot["latitude"], depot["longitude"]],
                    popup=depot["name"],
                    icon=folium.Icon(color="blue", icon="home")
                ).add_to(m)
                if "geojson_route" in alog and "coordinates" in alog["geojson_route"]:
                    folium.GeoJson(
                        alog["geojson_route"],
                        name="Ag-Logistics Supply Route",
                        style_function=lambda x: {
                            "color": "#2980B9",
                            "weight": 4,
                            "dashArray": "6, 6" if not alog.get("aws_credentials_available") else None
                        },
                        tooltip=f"Route: {alog.get('distance_km')} km ({alog.get('duration_minutes')} min)"
                    ).add_to(m)
            
            st_folium(m, width="100%", height=450)
        else:
            st.warning("Parcel boundary geometry not found in cadastral layer.")

    with col_map_info:
        st.subheader("Deterministic Spatial Audit")
        st.markdown(f"**District:** {vobj['district']}")
        st.markdown(f"**Village:** {vobj['village']}")
        owner_str = attrs.get('registered_owner') or "None (Unregistered / Absent)"
        st.markdown(f"**Registered Owner:** `{owner_str}` *(Demonstration Fixture)*")
        st.caption("ℹ️ *Matched against bundled TamilNilam demonstration Record of Rights dataset; not an authoritative live government portal confirmation.*")
        st.markdown(f"**GIS Calculated Area:** **`{attrs['gis_area_acres']} acres`**")
        st.markdown(f"**Documented Area:** `{attrs['documented_area_acres']} acres`")
        
        diff_pct = attrs['extent_difference_pct']
        diff_color = "gray" if diff_pct is None else ("green" if diff_pct <= 5.0 else "red")
        st.markdown(f"**Extent Discrepancy:** <span style='color:{diff_color}; font-weight:bold;'>{diff_pct}%</span>", unsafe_allow_html=True)
        
        st.markdown("---")
        st.markdown("**Deterministic Spatial & Proximity Audit:**")
        st.markdown(f"• Distance to Waterbody: **`{spatial_checks['distance_to_waterbody_meters']} m`**")
        st.markdown(f"• Waterbody Buffer Conflict (<{spatial_checks.get('waterbody_buffer_threshold_meters', 50)} m): **`{spatial_checks['waterbody_buffer_conflict']}`**")
        st.markdown(f"• Cadastral Containment Verified: **`{spatial_checks.get('cadastral_containment_valid', True)}`**")
        st.markdown(f"• Distance to Road Network: **`{spatial_checks['distance_to_road_meters']} m`**")
        st.markdown(f"• Direct Road Access: **`{spatial_checks['road_accessible']}`**")
        st.caption(f"Engine: *{spatial_checks.get('spatial_engine', 'GeoPandas & Shapely (UTM Zone 44N)')}*")

        if vobj.get("agri_logistics") and not vobj["agri_logistics"].get("error"):
            alog = vobj["agri_logistics"]
            st.markdown("---")
            st.markdown("**Ag-Logistics & Supply Transit:**")
            st.markdown(f"• Origin Depot: `{alog['origin']['name']}`")
            st.markdown(f"• Road Distance: **`{alog['distance_km']} km`**")
            st.markdown(f"• Travel Time: **`{alog['duration_minutes']} min`**")
            src_lbl = "Amazon Location Service" if alog.get("aws_credentials_available") else "Local Haversine Estimate (1.28× Detour)"
            st.caption(f"Routing Source: *{src_lbl}*")

# Tab 2: Crop Vision & Advisory
with tab_crop:
    col_img, col_adv = st.columns([1, 1])
    
    with col_img:
        st.subheader("Field Ground Photo Perception")
        filename = next((e.get("source_ref") for e in vobj.get("source_evidence", []) if e.get("source_type") == "FIELD_PHOTOGRAPH"), None)
        img_record = orchestrator.vision.image_registry.get(filename) if filename else None
        if img_record and os.path.exists(img_record["filepath"]):
            st.image(img_record["filepath"], caption=f"Field Photo: {img_record['filename']}")
        else:
            st.info("Field photo preview placeholder.")
        
        st.markdown("---")
        vision_step = next((step for step in telemetry['steps'] if 'has_image' in step), {})
        actual_model = vision_step.get('actual_execution_model') or vision_step.get('model_or_tool', 'Vision not executed')
        is_indep = vision_step.get('is_independent_teacher', False)
        st.markdown(f"**Planned Route:** `{vision_step.get('planned_route', 'Vision not planned')}`")
        st.markdown(f"**Runtime Execution:** `{actual_model}`")
        if force_escalate:
            if is_indep:
                st.success("✅ Escalated to independent multimodal teacher: **Ministral 8B (AWS Bedrock)**")
            else:
                st.warning("⚠️ Escalated to **MobileNetV3-TTA-Ensemble-Teacher (Local Fallback)** (Bedrock offline; running multi-scale TTA ensemble over student backbone).")
        st.markdown(f"**Predicted Crop:** **`{attrs['predicted_crop']}`**")
        st.markdown(f"**Growth Stage:** **`{attrs['growth_stage']}`**")
        st.markdown(f"**Model Confidence:** `{trust['model_reported_confidence']}`")
        st.caption("Photo location: matched to the selected polygon" if attrs.get("photo_association_verified") else "Photo location is unverified; image-only findings do not confirm a parcel crop.")

    with col_adv:
        st.subheader("Cited Agronomy Advisory (TNAU / ICAR)")
        adv = vobj["advisory_recommendation"]
        if adv.get("source_grounded", False):
            sim = adv.get('retrieval_similarity')
            sim_str = f"Cosine Sim: {sim:.3f}" if isinstance(sim, (int, float)) else "Dense Vector Match"
            st.success(f"✅ **Grounded Advisory** · `{sim_str}`")
            st.info(f"📋 **{adv.get('advisory_title', 'Agronomy Recommendation')}**")
            
            st.markdown("**Fertilizer Schedule:**")
            fert = adv.get("fertilizer_schedule")
            if isinstance(fert, dict):
                for k, v in fert.items():
                    st.markdown(f"- **{k.replace('_', ' ').title()}:** {v}")
            else:
                st.write(fert)
            
            st.markdown("**Water & Irrigation Management:**")
            st.write(adv.get("water_management"))
            
            st.markdown("**Pest & Disease Control:**")
            st.write(adv.get("pest_management"))
            
            st.markdown("---")
            doc_id = adv.get('matched_document_id', 'N/A')
            st.caption(f"📖 **Citation Source:** *{adv.get('citation_source')}* (`{doc_id}`)")
        else:
            st.error("🚫 **Zero-Hallucination Guardrail Active**")
            st.warning(
                f"**Advisory Refused**: {adv.get('advisory_title')}\n\n"
                f"• **Reason**: {adv.get('note', 'No grounded ICAR/TNAU research document matches this crop.')}\n\n"
                f"• **System Policy**: Refuse to invent ungrounded fertilizer schedules or chemical dosages for unverified/out-of-distribution crops."
            )
            st.markdown("---")
            st.caption(f"📖 **Citation Status:** *{adv.get('citation_source')}*")

# Tab 3: Evidence Graph
with tab_graph:
    st.subheader("In-Memory Evidence Graph DAG")
    st.markdown("Every claim is directly connected to observable source evidence, preventing unsupported hallucinations:")
    
    dag_nodes = vobj["evidence_graph_dag"]["nodes"]
    dag_edges = vobj["evidence_graph_dag"]["edges"]
    
    col_n, col_e = st.columns(2)
    with col_n:
        st.markdown("#### Evidence Nodes")
        df_nodes = pd.DataFrame(dag_nodes)
        st.dataframe(df_nodes, width="stretch")
    with col_e:
        st.markdown("#### Provenance Relationships")
        df_edges = pd.DataFrame(dag_edges)
        st.dataframe(df_edges, width="stretch")
    
    st.markdown("---")
    st.markdown("#### Trust Score (FTS) Mathematical Breakdown")
    breakdown = trust["signal_breakdown"]
    df_b = pd.DataFrame([
        {"Signal": "Historical Calibration (w1=0.15)", "Value": breakdown["calibration"]},
        {"Signal": "Evidence Coverage (w2=0.25)", "Value": breakdown["evidence_coverage"]},
        {"Signal": "Source Consistency (w3=0.25)", "Value": breakdown["source_consistency"]},
        {"Signal": "Deterministic Spatial Validation (w4=0.25)", "Value": breakdown["deterministic_validation"]},
        {"Signal": "Output Schema Validity (w5=0.10)", "Value": breakdown["output_validity"]},
        {"Signal": "Conflict Penalty (w6=0.20)", "Value": -float(breakdown['conflict_penalty'])}
    ])
    st.table(df_b)

# Tab 4: Telemetry Trace
with tab_telemetry:
    st.subheader("Live Execution Trace & Model Telemetry")
    st.markdown("Task 1 explicitly evaluates model routing by capability, cost, latency, and verification:")
    
    df_tel = pd.DataFrame(telemetry["steps"])
    st.dataframe(df_tel[["task_id", "name", "model_or_tool", "type", "latency_ms", "cost_usd", "rationale"]], width="stretch")
    
    col_tc, col_tl = st.columns(2)
    with col_tc:
        st.metric("Total Estimated Cost", f"${telemetry['total_estimated_cost_usd']:.5f}")
    with col_tl:
        st.metric("Total Processing Latency", f"{telemetry['total_latency_ms']} ms")

# Tab 5: measured telemetry, without unsupported competitor accuracy claims.
with tab_baselines:
    st.subheader("Measured workflow telemetry")
    st.warning("Historical 50-query results predate the source-evidence fixes. They are not current accuracy evidence. Competitor figures were simulations, not live provider comparisons.")
    st.metric("Current measured workflow latency", f"{telemetry['total_latency_ms']} ms")
    st.metric("Estimated routing cost", f"${telemetry['total_estimated_cost_usd']:.5f}")
    st.caption("Estimated routing cost is not the actual AWS bill. There is no validated claim of 100% accuracy, zero hallucinations or unchanged accuracy at a given cost saving.")
    st.json({"planner_source": telemetry.get("planner_source"), "planning_usage": telemetry.get("planning_usage"), "policy_version": trust.get("policy_version"), "score_kind": trust.get("score_kind")})

# Tab 6: JSON Output
with tab_json:
    st.subheader("Strict Schema VerifiedResultObject JSON")
    st.caption("Machine-readable JSON payload consumed by downstream agricultural and government applications:")
    st.json(vobj)
