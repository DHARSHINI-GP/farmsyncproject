"""Async worker entry, imported only after the verified Linux bundle is loaded."""
import os
import time
from farmsync.cloud.store import CloudStore

_runtime = None


def runtime():
    global _runtime
    if _runtime is None:
        from farmsync.orchestrator import FarmSyncOrchestrator
        from farmsync.ai.engine import AIAssistantEngine
        from farmsync.runtime import Runtime
        orchestrator = FarmSyncOrchestrator()
        store = CloudStore(materialize=True)
        _runtime = Runtime(orchestrator, AIAssistantEngine(orchestrator), store=store, asset_dir='/tmp/farmsync/assets')
        if orchestrator.vision.mobilenet is None:
            raise RuntimeError('Local vision model failed to initialize')
        store.put('HEALTH#WORKER', {'ready': True, 'checked_at': int(time.time()), 'bundle_sha256': os.environ['FARMSYNC_BUNDLE_SHA256']})
    return _runtime


def execute(event, context):
    service = runtime()
    if event.get('warmup') is True:
        result = {'ready': True, 'vision_ready': True, 'bundle_sha256': os.environ['FARMSYNC_BUNDLE_SHA256']}
        if event.get('selftest'):
            identity = str(service.orchestrator.spatial.gdf_parcels_wgs84.iloc[0]['parcel_id'])
            constraints = service.orchestrator.spatial.check_constraints(identity)
            photo = next(iter(service.orchestrator.vision.image_registry.values()))
            prediction = service.orchestrator.vision.predict_crop(photo['filepath'])
            from farmsync.documents.ocr import reader
            ocr_ready = reader() is not None
            from farmsync.aws import check_approved_services
            result['aws_checks'] = check_approved_services()
            center=service.orchestrator.spatial.get_parcel(identity)['centroid']
            geocode=service.orchestrator.location_engine.reverse_geocode(center['latitude'],center['longitude'],identity)
            route=service.orchestrator.location_engine.calculate_agri_route(identity)
            result['location_checks']={'geocoding':bool(geocode.get('aws_credentials_available')), 'routing':bool(route.get('aws_credentials_available'))}
            result['selftest_passed'] = bool(constraints.get('geometry_valid') and prediction.get('has_image') and prediction.get('predicted_crop') and ocr_ready and result['aws_checks']['all_passed'] and all(result['location_checks'].values()))
            result['scope'] = 'Target Linux GIS, local crop inference, OCR initialization and point-in-time AWS calls under the execution role; not field accuracy or an uptime guarantee'
        return result
    identity, owner = event['run_id'], event['owner']
    run = service.store.run(identity, owner)
    if not run or not service.store.claim_run(identity):
        return {'skipped': True, 'reason': 'Missing run or duplicate delivery'}
    user = service.store.get('USER#' + owner)
    if not user or user.get('disabled'):
        service.store.update_run(identity, 'FAILED', error='ACCOUNT_DISABLED')
        service.store.release_capacity(identity)
        return {'failed': True}
    principal = {k: user[k] for k in ('id', 'username', 'role')}
    try:
        if run['request'].get('_job_kind') == 'batch':
            from farmsync.documents.batch import compare_document
            compare_document(service, principal, run['request'], identity)
        else:
            service.analyze(principal, run['request'], run_id=identity)
        return {'completed': True}
    except Exception as exc:
        current = service.store.run(identity, owner)
        if current['status'] == 'RUNNING':
            code = str(exc) if str(exc) == 'REQUEST_CANCELLED' else type(exc).__name__
            service.store.update_run(identity, 'CANCELLED' if code == 'REQUEST_CANCELLED' else 'FAILED', error=code)
            service.store.event(owner, 'FAILED', {'error_code': code}, identity)
        # The persisted result is terminal. Do not ask Lambda to retry paid tools.
        return {'failed': True, 'error_code': type(exc).__name__}
    finally:
        service.store.release_capacity(identity)
