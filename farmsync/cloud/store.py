"""DynamoDB records and private, versioned S3 evidence for Lambda.

No persistent state depends on a Lambda execution environment's /tmp directory.
The single table needs PK/SK and an owner-index GSI (GPK/GSK).
"""
from decimal import Decimal
from hashlib import sha256
import json
import os
from pathlib import Path
import secrets
import time
import tempfile
import uuid

from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError
from farmsync.storage import now, password_hash, password_matches


def clean(value):
    if isinstance(value, Decimal):
        return int(value) if value % 1 == 0 else float(value)
    if isinstance(value, dict):
        return {k: clean(v) for k, v in value.items() if k not in {'PK', 'SK', 'GPK', 'GSK'}}
    if isinstance(value, list):
        return [clean(v) for v in value]
    return value


class CloudStore:
    def __init__(self, table=None, s3=None, bucket=None, materialize=False):
        if table is None or s3 is None:
            import boto3
            from farmsync.aws import REGION, system_ca_bundle
            opts = dict(region_name=REGION, verify=system_ca_bundle())
            table = table or boto3.resource('dynamodb', **opts).Table(os.environ['FARMSYNC_TABLE'])
            s3 = s3 or boto3.client('s3', **opts)
        self.table, self.s3 = table, s3
        self.bucket = bucket or os.environ['FARMSYNC_BUCKET']
        self.materialize = materialize
        self.path = Path(tempfile.gettempdir()) / 'farmsync/unused.sqlite3'  # interface only

    def get(self, pk, sk='META'):
        return clean(self.table.get_item(Key={'PK': pk, 'SK': sk}, ConsistentRead=True).get('Item'))

    def put(self, pk, value, sk='META', **kwargs):
        item = json.loads(json.dumps({'PK': pk, 'SK': sk, **value}, allow_nan=False), parse_float=Decimal)
        self.table.put_item(Item=item, **kwargs)

    def listing(self, partition, prefix='', limit=200):
        condition = Key('GPK').eq(partition)
        if prefix:
            condition = condition & Key('GSK').begins_with(prefix)
        data = self.table.query(IndexName='owner-index', KeyConditionExpression=condition, ScanIndexForward=False, Limit=limit)
        return [clean(v) for v in data.get('Items', [])]

    def create_user(self, username, password, role='user'):
        username = username.strip().casefold()
        if not 3 <= len(username) <= 128 or role not in {'admin', 'reviewer', 'user'}:
            raise ValueError('Invalid username or role')
        identity = uuid.uuid4().hex
        user = {'id': identity, 'username': username, 'role': role, 'password': password_hash(password), 'disabled': False, 'created': now(), 'GPK': 'USERS', 'GSK': 'ROLE#' + role + '#' + username}
        # A name reservation prevents simultaneous duplicate registration.
        self.put('NAME#' + username, {'user_id': identity}, ConditionExpression='attribute_not_exists(PK)')
        try:
            self.put('USER#' + identity, user)
        except Exception:
            self.table.delete_item(Key={'PK': 'NAME#' + username, 'SK': 'META'})
            raise
        return {k: user[k] for k in ('id', 'username', 'role')}

    def admin_count(self):
        return sum(not value.get('disabled') for value in self.listing('USERS', 'ROLE#admin#'))

    def login(self, username, password):
        name = self.get('NAME#' + username.strip().casefold())
        user = self.get('USER#' + name['user_id']) if name else None
        stored = user['password'] if user else 'pbkdf2_sha256$600000$unknown$' + '0' * 64
        if not password_matches(password, stored) or not user or user.get('disabled'):
            return None
        token = secrets.token_urlsafe(40)
        self.put('SESSION#' + sha256(token.encode()).hexdigest(), {'user_id': user['id'], 'ttl': int(time.time()) + 28800})
        return token, {k: user[k] for k in ('id', 'username', 'role')}

    def principal(self, token):
        if not token or len(token) > 256:
            return None
        session = self.get('SESSION#' + sha256(token.encode()).hexdigest())
        if not session or session['ttl'] <= time.time():
            return None
        user = self.get('USER#' + session['user_id'])
        return {k: user[k] for k in ('id', 'username', 'role')} if user and not user.get('disabled') else None

    def logout(self, token):
        if token:
            self.table.delete_item(Key={'PK': 'SESSION#' + sha256(token.encode()).hexdigest(), 'SK': 'META'})

    def admit(self, owner, category, limit, window=60):
        bucket = int(time.time()) // window
        try:
            self.table.update_item(Key={'PK': 'RATE#' + owner, 'SK': f'{category}#{bucket}'},
                UpdateExpression='SET #n=if_not_exists(#n,:zero)+:one, #ttl=:ttl',
                ConditionExpression='attribute_not_exists(#n) OR #n < :limit',
                ExpressionAttributeNames={'#n': 'count', '#ttl': 'ttl'},
                ExpressionAttributeValues={':zero': 0, ':one': 1, ':limit': limit, ':ttl': (bucket + 2) * window})
            return True
        except ClientError as exc:
            if exc.response['Error']['Code'] == 'ConditionalCheckFailedException':
                return False
            raise

    def event(self, owner, kind, payload, run_id=None):
        # Microseconds remain exactly representable by browser Number/SSE cursors.
        identity = time.time_ns() // 1000
        self.put('EVENTS#' + (run_id or owner), {'id': identity, 'owner': owner, 'kind': kind, 'payload': payload, 'created': now()}, f'{identity:020d}#{uuid.uuid4().hex}')

    def events(self, run_id, owner, after=0):
        data = self.table.query(KeyConditionExpression=Key('PK').eq('EVENTS#' + run_id) & Key('SK').gt(f'{int(after):020d}~'), ConsistentRead=True, Limit=500)
        return [clean(v) for v in data.get('Items', []) if v['owner'] == owner]

    def add_asset(self, owner, kind, name, path, checksum, metadata):
        raw = Path(path).read_bytes()
        if sha256(raw).hexdigest() != checksum:
            raise ValueError('Asset checksum mismatch')
        identity, created = uuid.uuid4().hex, now()
        key = f'evidence/{owner}/{identity}'
        self.s3.put_object(Bucket=self.bucket, Key=key, Body=raw, ServerSideEncryption='AES256', ContentType='application/pdf' if kind == 'pdf' else 'image/jpeg')
        self.put('ASSET#' + identity, {'id': identity, 'owner': owner, 'kind': kind, 'original_name': name, 'checksum': checksum, 'metadata': metadata, 'object_key': key, 'created': created, 'deleted': False, 'GPK': 'OWNER#' + owner, 'GSK': 'ASSET#' + created + '#' + identity})
        return identity

    def asset(self, identity, owner, admin=False):
        value = self.get('ASSET#' + identity)
        if not value or value.get('deleted') or (value['owner'] != owner and not admin):
            return None
        if self.materialize:
            path = Path(tempfile.gettempdir()) / 'farmsync/assets' / (identity + ('.pdf' if value['kind'] == 'pdf' else '.jpg'))
            path.parent.mkdir(parents=True, exist_ok=True)
            if not path.exists() or sha256(path.read_bytes()).hexdigest() != value['checksum']:
                raw = self.s3.get_object(Bucket=self.bucket, Key=value['object_key'])['Body'].read()
                if sha256(raw).hexdigest() != value['checksum']:
                    raise ValueError('Stored evidence checksum mismatch')
                path.write_bytes(raw)
            value['path'] = str(path)
        return value

    def assets(self, owner, kind=None):
        return [a for a in self.listing('OWNER#' + owner, 'ASSET#', 500) if not a.get('deleted') and (kind is None or a['kind'] == kind)]

    def reviewer_asset(self, asset_id, reviewer):
        for review in self.reviews(reviewer, reviewer=True):
            if review.get('assigned_to') not in {None, reviewer}:
                continue
            run = self.run(review['run_id'], review['owner'])
            if run and 'asset:' + asset_id in {run['request'].get('document_path'), run['request'].get('image_filename')}:
                return self.asset(asset_id, review['owner'])
        return None

    def create_run(self, owner, request, status='QUEUED'):
        identity, created = uuid.uuid4().hex, now()
        self.put('RUN#' + identity, {'id': identity, 'owner': owner, 'request': request, 'status': status, 'created': created, 'updated': created, 'cancel_requested': False, 'error': None, 'GPK': 'OWNER#' + owner, 'GSK': 'RUN#' + created + '#' + identity})
        self.event(owner, 'QUEUED', {}, identity)
        return identity

    def update_run(self, identity, status, result=None, error=None):
        values = {':status': status, ':updated': now(), ':error': error}
        expression = 'SET #status=:status, updated=:updated, #error=:error'
        if result is not None:
            key = f'results/{identity}.json'
            self.s3.put_object(Bucket=self.bucket, Key=key, Body=json.dumps(result, allow_nan=False, default=str).encode(), ContentType='application/json', ServerSideEncryption='AES256')
            values[':result'] = key
            expression += ', result_key=:result'
        self.table.update_item(Key={'PK': 'RUN#' + identity, 'SK': 'META'}, UpdateExpression=expression, ConditionExpression='attribute_exists(PK)', ExpressionAttributeNames={'#status': 'status', '#error': 'error'}, ExpressionAttributeValues=values)

    def run(self, identity, owner, reviewer=False):
        value = self.get('RUN#' + identity)
        if not value or (value['owner'] != owner and not reviewer):
            return None
        value['result'] = None
        if value.get('result_key'):
            value['result'] = json.loads(self.s3.get_object(Bucket=self.bucket, Key=value['result_key'])['Body'].read())
        return value

    def runs(self, owner):
        return [{k: v.get(k) for k in ('id', 'status', 'created', 'updated', 'error')} for v in self.listing('OWNER#' + owner, 'RUN#', 100)]

    def cancel(self, identity, owner):
        try:
            self.table.update_item(Key={'PK': 'RUN#' + identity, 'SK': 'META'}, UpdateExpression='SET cancel_requested=:yes', ConditionExpression='#owner=:owner AND #status IN (:queued,:running)', ExpressionAttributeNames={'#owner': 'owner', '#status': 'status'}, ExpressionAttributeValues={':yes': True, ':owner': owner, ':queued': 'QUEUED', ':running': 'RUNNING'})
            return True
        except ClientError as exc:
            if exc.response['Error']['Code'] == 'ConditionalCheckFailedException':
                return False
            raise

    def create_review(self, run_id, owner):
        # One review per run makes asynchronous retries idempotent.
        identity, created = run_id, now()
        try:
            self.put('REVIEW#' + identity, {'id': identity, 'run_id': run_id, 'owner': owner, 'state': 'OPEN', 'assigned_to': None, 'resolution': None, 'created': created, 'updated': created, 'GPK': 'REVIEWS', 'GSK': created + '#' + identity}, ConditionExpression='attribute_not_exists(PK)')
        except ClientError as exc:
            if exc.response['Error']['Code'] != 'ConditionalCheckFailedException':
                raise
        return identity

    def reviews(self, owner, reviewer=False):
        return [r for r in self.listing('REVIEWS') if reviewer or r['owner'] == owner]

    def can_review_run(self, run_id, reviewer):
        review = self.get('REVIEW#' + run_id)
        return bool(review and review.get('assigned_to') in {None, reviewer})

    def resolve_review(self, identity, reviewer, resolution):
        try:
            self.table.update_item(Key={'PK': 'REVIEW#' + identity, 'SK': 'META'}, UpdateExpression='SET #state=:resolved, assigned_to=:reviewer, resolution=:resolution, updated=:updated', ConditionExpression='#state=:open AND (attribute_not_exists(assigned_to) OR assigned_to=:null OR assigned_to=:reviewer)', ExpressionAttributeNames={'#state': 'state'}, ExpressionAttributeValues={':open': 'OPEN', ':resolved': 'RESOLVED', ':null': None, ':reviewer': reviewer, ':resolution': resolution, ':updated': now()})
            row = self.get('REVIEW#' + identity)
            self.event(row['owner'], 'REVIEW_RESOLVED', {'reviewer': reviewer, 'resolution': resolution}, row['run_id'])
            return True
        except ClientError as exc:
            if exc.response['Error']['Code'] == 'ConditionalCheckFailedException':
                return False
            raise

    def claim_run(self, identity):
        """Prevent duplicate deliveries from running the same paid tools twice."""
        try:
            self.table.update_item(Key={'PK': 'RUN#' + identity, 'SK': 'META'}, UpdateExpression='SET #status=:running, updated=:updated', ConditionExpression='#status=:queued', ExpressionAttributeNames={'#status': 'status'}, ExpressionAttributeValues={':running': 'RUNNING', ':queued': 'QUEUED', ':updated': now()})
            return True
        except ClientError as exc:
            if exc.response['Error']['Code'] == 'ConditionalCheckFailedException':
                return False
            raise

    def acquire_capacity(self, run_id, capacity=2):
        for slot in range(capacity):
            try:
                self.table.update_item(Key={'PK': 'CAPACITY', 'SK': str(slot)},
                    UpdateExpression='SET run_id=:run, expires=:expiry',
                    ConditionExpression='attribute_not_exists(run_id) OR expires<:now',
                    ExpressionAttributeValues={':run': run_id, ':expiry': int(time.time())+1000, ':now': int(time.time())})
                return True
            except ClientError as exc:
                if exc.response['Error']['Code'] != 'ConditionalCheckFailedException': raise
        return False

    def release_capacity(self, run_id, capacity=2):
        for slot in range(capacity):
            try:
                self.table.delete_item(Key={'PK': 'CAPACITY', 'SK': str(slot)}, ConditionExpression='run_id=:run', ExpressionAttributeValues={':run': run_id})
            except ClientError as exc:
                if exc.response['Error']['Code'] != 'ConditionalCheckFailedException': raise
