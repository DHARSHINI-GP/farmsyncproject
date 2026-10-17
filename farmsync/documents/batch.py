"""Compare every source claim without guessing its village or parcel identity."""
import os
from farmsync.documents.evidence import extract_claims


def compare_document(runtime, user, payload, run_id=None):
    args, _ = runtime.authorize_payload({'document_path': payload['document_path']}, user)
    if not payload['document_path'].startswith('asset:'):
        raise ValueError('Batch comparison requires an owned uploaded PDF')
    claims, notices = runtime.orchestrator.docs.extract_source_claims(args['document_path'])
    if len(claims) > 500:
        raise ValueError('Batch limit is 500 source claims')
    run_id = run_id or runtime.store.create_run(user['id'], payload, 'RUNNING')
    results = []
    for source in claims:
        state = runtime.store.run(run_id, user['id'])
        if state and state['cancel_requested']:
            raise RuntimeError('REQUEST_CANCELLED')
        selected_village = payload.get('village')
        if source.get('document_village') and selected_village and source['document_village'].strip().casefold() != selected_village.strip().casefold():
            results.append({'claim': source, 'parcel_id': None, 'status': 'VILLAGE_CONFLICT', 'ownership_verified': False})
            continue
        village = source.get('document_village') or selected_village
        frame = runtime.orchestrator.spatial.gdf_parcels_wgs84
        matches = frame[frame['survey_no_clean'] == source['survey_no']]
        if village:
            matches = matches[matches['vil_name'].astype(str).str.strip().str.casefold() == village.strip().casefold()]
        parcel = runtime.orchestrator.spatial.get_parcel(runtime.orchestrator.spatial.feature_id(matches.iloc[0])) if len(matches) == 1 else None
        extent = source['claimed_extent_acres']
        row = {'claim': source, 'parcel_id': parcel['parcel_id'] if parcel else None, 'status': 'PARCEL_UNRESOLVED' if not parcel else 'DOCUMENT_EXTENT_MISSING' if extent is None else 'COMPARED', 'ownership_verified': False}
        if parcel and extent is not None:
            row['extent_comparison'] = runtime.orchestrator.spatial.verify_extent(parcel['parcel_id'], extent)
        results.append(row)
        runtime.store.event(user['id'], 'TASK_PROGRESS', {'name': 'Document row comparison', 'status': 'RUNNING', 'completed': len(results), 'total': len(claims)}, run_id)
    result = {'run_id': run_id, 'claims': results, 'total_claims': len(results), 'notices': notices, 'ownership_verified': False, 'scope': 'Document row and cadastral extent comparison; not legal ownership verification'}
    runtime.store.update_run(run_id, 'COMPLETED', result)
    runtime.store.event(user['id'], 'BATCH_COMPLETED', {'claims': len(results)}, run_id)
    runtime.store.create_review(run_id, user['id'])
    return result
