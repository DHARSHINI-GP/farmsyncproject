"""Lightweight Lambda HTTP API; expensive ML/GIS work runs in a second Lambda.

This module never imports torch, geopandas or sentence-transformers. Deploy only
after the Linux worker bundle and the live release smoke have passed.
"""
import io
import json
import os
from pathlib import Path
import time
import tempfile
import uuid

from fastapi import FastAPI, Request, Response, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.gzip import GZipMiddleware
from pydantic import BaseModel, Field

from farmsync.cloud.store import CloudStore
from farmsync.platform_api import LoginInput, UserInput, JobInput, ReviewInput, BatchInput
from farmsync.runtime import Runtime
from farmsync.aws import create_client, check_approved_services, TEXT_MODEL
from farmsync.spatial.amazon_location import AmazonLocationServiceEngine


class UploadIntent(BaseModel):
    kind: str
    filename: str = Field(min_length=1, max_length=150)
    metadata: dict = Field(default_factory=dict)


class SnapshotSpatial:
    def __init__(self, snapshot):
        self.snapshot = snapshot

    def detail(self, identity):
        value = self.snapshot.get('details', {}).get(identity)
        if not value:
            raise HTTPException(404, 'Parcel not found or identity is ambiguous')
        return value

    def get_parcel(self, identity):
        return self.detail(identity)['parcel']

    def check_constraints(self, identity):
        return self.detail(identity)['constraints']


def create_app(store=None, invoke=None, snapshot=None):
    store = store or CloudStore()
    snapshot = snapshot if snapshot is not None else json.loads(Path(os.environ.get('FARMSYNC_SNAPSHOT', 'cloud-snapshot.json')).read_text(encoding='utf-8'))
    spatial = SnapshotSpatial(snapshot)
    location = AmazonLocationServiceEngine(spatial)
    client = None if invoke else create_client('lambda')
    invoke = invoke or (lambda event: client.invoke(FunctionName=os.environ['FARMSYNC_WORKER'], InvocationType='Event', Payload=json.dumps(event).encode()))
    app = FastAPI(title='FARMSYNC AWS workspace', docs_url=None, redoc_url=None, openapi_url=None)
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    asset_dir = Path(tempfile.gettempdir()) / 'farmsync/assets'
    asset_dir.mkdir(parents=True, exist_ok=True)
    uploader = Runtime.__new__(Runtime)
    uploader.store, uploader.asset_dir = store, asset_dir
    uploader.ephemeral_uploads = True

    def user(request):
        value = getattr(request.state, 'principal', None)
        if not value:
            raise HTTPException(401, 'Sign in with your individual account')
        return value

    def admin(request):
        value = user(request)
        if value['role'] != 'admin':
            raise HTTPException(403, 'Administrator role required')
        return value

    def owned_run(identity, principal):
        privileged = principal['role'] == 'admin' or (principal['role'] == 'reviewer' and store.can_review_run(identity, principal['id']))
        value = store.run(identity, principal['id'], reviewer=privileged)
        if not value:
            raise HTTPException(404, 'Run not found')
        if value['status'] in {'QUEUED', 'RUNNING'}:
            from datetime import datetime
            if time.time() - datetime.fromisoformat(value['created']).timestamp() > 1000:
                store.update_run(identity, 'INTERRUPTED', error='WORKER_TIMEOUT_OR_DELIVERY_FAILURE')
                store.release_capacity(identity)
                value.update(status='INTERRUPTED', error='WORKER_TIMEOUT_OR_DELIVERY_FAILURE')
        return value

    @app.middleware('http')
    async def security(request, call_next):
        request_id, started = uuid.uuid4().hex, time.monotonic()
        response = None
        if request.url.path.startswith('/api/'):
            token = request.cookies.get('farmsync_session')
            auth = request.headers.get('authorization', '')
            if auth.lower().startswith('bearer '):
                token = auth[7:]
            request.state.principal = store.principal(token)
            if request.url.path not in {'/api/auth/status', '/api/auth/login'} and not request.state.principal:
                response = JSONResponse({'detail': 'Sign in with your individual account'}, status_code=401)
            origin = request.headers.get('origin')
            allowed = {x.strip() for x in os.getenv('FARMSYNC_ALLOWED_ORIGINS', '').split(',') if x.strip()}
            if request.method not in {'GET', 'HEAD', 'OPTIONS'} and origin and origin not in allowed:
                response = JSONResponse({'detail': 'Unapproved request origin'}, status_code=403)
        response = response or await call_next(request)
        response.headers.update({'X-Content-Type-Options': 'nosniff', 'X-Request-ID': request_id, 'Referrer-Policy': 'same-origin', 'Cache-Control': 'no-store' if request.url.path.startswith('/api/') else 'no-cache'})
        print(json.dumps({'request_id': request_id, 'method': request.method, 'path': request.url.path, 'status': response.status_code, 'latency_ms': round((time.monotonic()-started)*1000, 2)}))
        return response

    @app.get('/health/live')
    def live():
        return {'status': 'alive', 'deployment': 'AWS_LAMBDA'}

    @app.get('/health/ready')
    def ready(response: Response):
        health = store.get('HEALTH#WORKER')
        okay = bool(snapshot.get('details') and health and health.get('ready') and health.get('bundle_sha256') == os.getenv('FARMSYNC_BUNDLE_SHA256'))
        response.status_code = 200 if okay else 503
        return {'ready': okay, 'scope': 'API, snapshot and worker bundle initialization; cloud model calls checked separately'}

    @app.get('/api/auth/status')
    def status(request: Request):
        value = getattr(request.state, 'principal', None)
        return {'authenticated': bool(value), 'user': value, 'login_required': True, 'production': True, 'cloud_deployment': True, 'progress_transport': 'poll'}

    @app.post('/api/auth/login')
    def login(payload: LoginInput, request: Request, response: Response):
        host = request.client.host if request.client else 'unknown'
        if not store.admit('login:' + host, 'login', 8, 300):
            raise HTTPException(429, 'Too many sign-in attempts')
        value = store.login(payload.username, payload.password.get_secret_value())
        if not value:
            raise HTTPException(401, 'Invalid username or password')
        token, principal = value
        response.set_cookie('farmsync_session', token, secure=True, httponly=True, samesite='strict', max_age=28800)
        store.event(principal['id'], 'SIGNED_IN', {})
        return {'user': principal}

    @app.post('/api/auth/logout')
    def logout(request: Request, response: Response):
        token = request.cookies.get('farmsync_session')
        if request.headers.get('authorization','').lower().startswith('bearer '):
            token = request.headers['authorization'][7:]
        store.logout(token)
        response.delete_cookie('farmsync_session', secure=True, httponly=True, samesite='strict')
        return {'signed_out': True}

    @app.post('/api/users', status_code=201)
    def create_user(payload: UserInput, request: Request):
        admin(request)
        try:
            return store.create_user(payload.username, payload.password.get_secret_value(), payload.role)
        except Exception as exc:
            raise HTTPException(400, 'User could not be created; check uniqueness, password length and role') from exc

    def submit(payload, principal, kind='analysis'):
        for field, expected in [('document_path', 'pdf'), ('image_filename', 'image')]:
            ref = payload.get(field) or ''
            if ref.startswith('asset:'):
                asset = store.asset(ref[6:], principal['id'])
                if not asset or asset['kind'] != expected:
                    raise HTTPException(404, 'Evidence not found')
            elif ref and ref not in snapshot.get('allowed_evidence', {}).get(field, []):
                raise HTTPException(404, 'Supplied evidence not found')
        if payload.get('simulate_conflict') or payload.get('simulate_ood'):
            raise HTTPException(400, 'Simulation disabled in production')
        if not store.admit(principal['id'], 'analysis', 10) or not store.admit(principal['id'], 'analysis_day', 100, 86400) or not store.admit('deployment', 'analysis_day', int(os.getenv('FARMSYNC_GLOBAL_ANALYSES_PER_DAY', '200')), 86400):
            raise HTTPException(429, 'Analysis quota reached')
        run_id = store.create_run(principal['id'], {**payload, '_job_kind': kind})
        if not store.acquire_capacity(run_id):
            store.update_run(run_id, 'FAILED', error='CAPACITY_LIMIT')
            raise HTTPException(429, 'Processing capacity reached; retry after an active job completes')
        try:
            invoke({'run_id': run_id, 'owner': principal['id']})
        except Exception as exc:
            store.release_capacity(run_id)
            store.update_run(run_id, 'FAILED', error='DISPATCH_FAILED')
            raise HTTPException(503, 'Analysis dispatch failed; inspect saved history') from exc
        return {'run_id': run_id, 'status': 'QUEUED', 'progress_transport': 'poll'}

    @app.post('/api/jobs', status_code=202)
    def jobs(payload: JobInput, request: Request):
        return submit(payload.model_dump(), user(request))

    @app.post('/api/documents/batch', status_code=202)
    def batch(payload: BatchInput, request: Request):
        if not payload.document_path.startswith('asset:'):
            raise HTTPException(400, 'Upload and select your PDF first')
        return submit(payload.model_dump(), user(request), 'batch')

    @app.get('/api/jobs/{identity}')
    @app.get('/api/runs/{identity}')
    def job(identity: str, request: Request):
        return owned_run(identity, user(request))

    @app.get('/api/jobs/{identity}/events')
    def events(identity: str, request: Request, after: int = 0):
        principal = user(request)
        owned_run(identity, principal)
        return {'events': store.events(identity, principal['id'], after)}

    @app.post('/api/jobs/{identity}/cancel')
    def cancel(identity: str, request: Request):
        owned_run(identity, user(request))
        return {'cancel_requested': store.cancel(identity, user(request)['id'])}

    @app.get('/api/runs')
    def runs(request: Request):
        return {'runs': store.runs(user(request)['id'])}

    @app.get('/api/runs/{identity}/export')
    def export(identity: str, request: Request):
        return JSONResponse(owned_run(identity, user(request)), headers={'Content-Disposition': f'attachment; filename="farmsync-{uuid.UUID(identity).hex}.json"'})

    @app.get('/api/reviews')
    def reviews(request: Request):
        principal = user(request)
        return {'reviews': store.reviews(principal['id'], reviewer=principal['role'] in {'admin', 'reviewer'})}

    @app.post('/api/reviews/{identity}/resolve')
    def resolve(identity: str, payload: ReviewInput, request: Request):
        principal = user(request)
        if principal['role'] not in {'admin', 'reviewer'}:
            raise HTTPException(403, 'Reviewer role required')
        if not store.resolve_review(identity, principal['id'], payload.resolution):
            raise HTTPException(404, 'Open review not found')
        return {'resolved': True, 'ownership_verified': False}

    @app.get('/api/assets')
    def assets(request: Request):
        return {'assets': store.assets(user(request)['id'])}

    @app.post('/api/assets/{identity}/archive')
    @app.post('/api/assets/{identity}/restore')
    def archive_asset(identity: str, request: Request):
        from botocore.exceptions import ClientError
        principal = user(request)
        archived = request.url.path.endswith('/archive')
        try:
            store.table.update_item(Key={'PK':'ASSET#'+identity,'SK':'META'}, UpdateExpression='SET deleted=:deleted', ConditionExpression='#owner=:owner', ExpressionAttributeNames={'#owner':'owner'}, ExpressionAttributeValues={':deleted':archived, ':owner':principal['id']})
        except ClientError as exc:
            if exc.response['Error']['Code'] == 'ConditionalCheckFailedException': raise HTTPException(404, 'Evidence not found') from exc
            raise
        store.event(principal['id'], 'ASSET_ARCHIVED' if archived else 'ASSET_RESTORED', {'asset_id':identity})
        return {'archived':archived,'recoverable':True}

    @app.post('/api/uploads/intent')
    def upload_intent(payload: UploadIntent, request: Request):
        principal = user(request)
        if payload.kind not in {'pdf', 'image'}:
            raise HTTPException(422, 'Unsupported upload kind')
        if not store.admit(principal['id'], 'upload_intent', 20):
            raise HTTPException(429, 'Upload rate limit reached')
        identity, key = uuid.uuid4().hex, f'staging/{principal["id"]}/{uuid.uuid4().hex}'
        store.put('UPLOAD#' + identity, {'owner': principal['id'], 'key': key, 'kind': payload.kind, 'filename': payload.filename, 'metadata': payload.metadata, 'ttl': int(time.time()) + 600})
        post = store.s3.generate_presigned_post(Bucket=store.bucket, Key=key, Fields={'x-amz-server-side-encryption': 'AES256'}, Conditions=[['content-length-range', 1, 15*1024*1024], {'x-amz-server-side-encryption': 'AES256'}], ExpiresIn=300)
        return {'upload_id': identity, 'post': post}

    @app.post('/api/uploads/{identity}/complete')
    async def complete_upload(identity: str, request: Request):
        principal = user(request)
        ticket = store.get('UPLOAD#' + identity)
        if not ticket or ticket['owner'] != principal['id'] or ticket['ttl'] < time.time():
            raise HTTPException(404, 'Upload not found or expired')
        if ticket.get('result'):
            return ticket['result']
        metadata = ticket['metadata']
        lat, lon = metadata.get('latitude'), metadata.get('longitude')
        try:
            if lat is not None or lon is not None:
                lat, lon = float(lat), float(lon)
                if not (-90 <= lat <= 90 and -180 <= lon <= 180):
                    raise ValueError()
                metadata.update(latitude=lat, longitude=lon)
        except (TypeError, ValueError) as exc:
            raise HTTPException(422, 'Invalid coordinate pair') from exc
        body = store.s3.get_object(Bucket=store.bucket, Key=ticket['key'])
        if not 0 < body['ContentLength'] <= 15*1024*1024:
            raise HTTPException(413, 'Upload size limit exceeded')
        file = UploadFile(io.BytesIO(body['Body'].read()), filename=ticket['filename'])
        try:
            result = await uploader.upload(request, file, ticket['kind'], metadata)
        finally:
            await file.close()
        ticket['result'] = result
        store.put('UPLOAD#' + identity, ticket)
        return result

    @app.get('/api/assets/{identity}/file')
    @app.get('/api/image/{identity:path}')
    def file(identity: str, request: Request):
        principal = user(request)
        if identity.startswith('asset:'):
            identity = identity[6:]
        asset = store.asset(identity, principal['id'], admin=principal['role'] == 'admin')
        if not asset and principal['role'] == 'reviewer':
            asset = store.reviewer_asset(identity, principal['id'])
        if not asset:
            key = snapshot.get('image_objects', {}).get(identity)
            if not key:
                raise HTTPException(404, 'Evidence not found')
        else:
            key = asset['object_key']
        url = store.s3.generate_presigned_url('get_object', Params={'Bucket': store.bucket, 'Key': key}, ExpiresIn=60)
        return RedirectResponse(url)

    @app.get('/api/images')
    def images(request: Request):
        return {'images': snapshot.get('images', []) + [{'filename': 'asset:' + a['id'], 'label': a['original_name']} for a in store.assets(user(request)['id'], 'image')]}

    @app.get('/api/documents/list')
    def documents(request: Request):
        docs = dict(snapshot.get('documents', {}))
        docs['My uploads'] = [{'filename': a['original_name'], 'relative_path': 'asset:' + a['id'], 'size_bytes': 0} for a in store.assets(user(request)['id'], 'pdf')]
        return {'documents': docs, 'total_categories': len(docs)}

    @app.get('/api/parcel/{identity:path}')
    def parcel(identity: str):
        return spatial.detail(identity)

    @app.get('/api/location/status')
    def location_status():
        return location.get_status()

    @app.get('/api/location/reverse-geocode/{identity:path}')
    def geocode(identity: str):
        p = spatial.get_parcel(identity)
        return location.reverse_geocode(p['centroid']['latitude'], p['centroid']['longitude'], identity)

    @app.get('/api/location/geofence/{identity:path}')
    def geofence(identity: str):
        return location.evaluate_cadastral_geofence(identity)

    @app.post('/api/location/route')
    async def route(request: Request):
        if not store.admit(user(request)['id'], 'route', 10):
            raise HTTPException(429, 'Route rate limit reached')
        body = await request.json()
        return location.calculate_agri_route(body.get('parcel_id') or body.get('survey_no'), body.get('origin_lat'), body.get('origin_lon'))

    @app.get('/api/settings/aws/status')
    def aws_status():
        return {'bedrock_client_ready': True, 'connection_verified': False, 'connection_status': 'UNVERIFIED', 'model_id': TEXT_MODEL}

    @app.post('/api/settings/aws/check')
    def aws_check(request: Request):
        principal = admin(request)
        if not store.admit(principal['id'], 'cloud_check', 1, 300):
            raise HTTPException(429, 'Live checks limited to one per five minutes')
        return check_approved_services()

    @app.get('/api/{path:path}')
    def data(path: str):
        value = snapshot.get('responses', {}).get('/api/' + path)
        if value is None:
            raise HTTPException(404, 'Endpoint not found')
        return value

    static = Path(__file__).resolve().parents[1] / 'static'
    app.mount('/static', StaticFiles(directory=static), name='static')

    @app.get('/', response_class=HTMLResponse)
    def index():
        from farmsync.web_security import html_response
        return html_response(static / 'index.html', 'https://' + store.bucket + '.s3.ap-south-1.amazonaws.com', os.getenv('FARMSYNC_API_STAGE', '/prod'))

    return app


def handler(event, context):
    # Defer construction so importing/testing this module never calls AWS.
    global _adapter
    if '_adapter' not in globals():
        from mangum import Mangum
        _adapter = Mangum(create_app(), lifespan='off', api_gateway_base_path=os.getenv('FARMSYNC_API_STAGE', '/prod'))
    return _adapter(event, context)
