"""AWS adapter integration tests use Moto; no requests leave the process."""
from io import BytesIO
import json
from pathlib import Path
import tarfile
import importlib.util

import boto3
from fastapi.testclient import TestClient
import pytest

moto = pytest.importorskip('moto', reason='Install aws/test-requirements.txt for AWS adapter tests')
from farmsync.cloud.store import CloudStore
from farmsync.cloud.api import create_app


@pytest.fixture
def cloud(monkeypatch):
    monkeypatch.setenv('FARMSYNC_OFFLINE', 'true')
    monkeypatch.setenv('FARMSYNC_ALLOWED_ORIGINS', 'https://testserver')
    with moto.mock_aws():
        ddb = boto3.resource('dynamodb', region_name='ap-south-1')
        table = ddb.create_table(TableName='fai-tce-team26-records', KeySchema=[{'AttributeName':'PK','KeyType':'HASH'},{'AttributeName':'SK','KeyType':'RANGE'}], AttributeDefinitions=[{'AttributeName':k,'AttributeType':'S'} for k in ['PK','SK','GPK','GSK']], GlobalSecondaryIndexes=[{'IndexName':'owner-index','KeySchema':[{'AttributeName':'GPK','KeyType':'HASH'},{'AttributeName':'GSK','KeyType':'RANGE'}], 'Projection':{'ProjectionType':'ALL'}}], BillingMode='PAY_PER_REQUEST')
        s3 = boto3.client('s3', region_name='ap-south-1')
        bucket = 'fai-tce-team26-test-evidence'
        s3.create_bucket(Bucket=bucket, CreateBucketConfiguration={'LocationConstraint':'ap-south-1'})
        store = CloudStore(table, s3, bucket)
        alice = store.create_user('alice','alice-strong-password')
        bob = store.create_user('bob','bob-strong-password')
        yield store, alice, bob


def test_durable_scoped_results_and_atomic_capacity(cloud):
    store, alice, bob = cloud
    identity = store.create_run(alice['id'], {'query':'Audit Survey 384'})
    assert store.run(identity,bob['id']) is None
    assert store.acquire_capacity(identity)
    second = store.create_run(bob['id'],{'query':'Other'})
    assert store.acquire_capacity(second)
    assert not store.acquire_capacity('third')
    assert store.claim_run(identity)
    assert not store.claim_run(identity)
    store.update_run(identity,'COMPLETED',{'source_claim':None,'large':'e'*500000})
    assert store.run(identity,alice['id'])['result']['source_claim'] is None
    store.release_capacity(identity)
    assert store.acquire_capacity('third')
    assert len(store.runs(alice['id'])) == 1
    assert len(store.events(identity,alice['id'])) == 1
    assert store.events(identity,bob['id']) == []


def test_cloud_login_revocation_quota_and_review(cloud):
    store, alice, _ = cloud
    assert store.login('alice','wrong-password') is None
    token, _ = store.login('alice','alice-strong-password')
    assert store.principal(token)['id'] == alice['id']
    store.logout(token)
    assert store.principal(token) is None
    assert store.admit(alice['id'],'test',1)
    assert not store.admit(alice['id'],'test',1)
    identity=store.create_run(alice['id'],{'query':'Test'})
    review=store.create_review(identity,alice['id'])
    assert store.create_review(identity,alice['id']) == review
    assert len(store.reviews(alice['id'])) == 1
    assert store.can_review_run(identity,'reviewer')
    assert store.resolve_review(review,'reviewer','Source checked; ownership remains unverified')
    assert not store.resolve_review(review,'other','Try again')
    assert not store.can_review_run(identity,'other')


def test_private_evidence_materialization_detects_tampering(cloud,tmp_path):
    from hashlib import sha256
    store,alice,bob=cloud
    source=tmp_path/'evidence.pdf'; source.write_bytes(b'private-evidence')
    identity=store.add_asset(alice['id'],'pdf','evidence.pdf',source,sha256(source.read_bytes()).hexdigest(),{})
    assert store.asset(identity,bob['id']) is None
    value=store.asset(identity,alice['id'])
    assert 'path' not in value
    store.s3.put_object(Bucket=store.bucket,Key=value['object_key'],Body=b'modified')
    store.materialize=True
    with pytest.raises(ValueError,match='checksum'):
        store.asset(identity,alice['id'])


def test_cloud_api_sessions_jobs_and_cross_user_access(cloud):
    store,alice,bob=cloud
    delivered=[]
    app=create_app(store,delivered.append,{'details':{},'responses':{'/api/parcels':{'parcels':[]}}})
    with TestClient(app,base_url='https://testserver') as client:
        assert client.get('/api/parcels').status_code == 401
        status=client.get('/api/auth/status').json()
        assert status['cloud_deployment'] and status['login_required']
        login=client.post('/api/auth/login',json={'username':'alice','password':'alice-strong-password'})
        assert login.status_code == 200
        assert 'Secure' in login.headers['set-cookie'] and 'HttpOnly' in login.headers['set-cookie']
        assert client.get('/api/parcels').status_code == 200
        job=client.post('/api/jobs',json={'query':'Check Survey 384','model_id':'mistral.ministral-3-8b-instruct'})
        assert job.status_code == 202
        identity=job.json()['run_id']
        assert store.run(identity,alice['id'])['request']['model_id'] == 'mistral.ministral-3-8b-instruct'
        assert client.post('/api/jobs',json={'query':'test','model_id':'unapproved-model'}).status_code == 422
        assert delivered == [{'run_id':identity,'owner':alice['id']}]
        assert client.post('/api/jobs',json={'query':'test','document_path':'asset:not-owned'}).status_code == 404
        assert client.post('/api/jobs',json={'query':'test','simulate_conflict':True}).status_code == 400
        assert client.post('/api/jobs',json={'query':'test'},headers={'Origin':'https://evil.example'}).status_code == 403
        assert client.post('/api/settings/aws/check').status_code == 403
        client.post('/api/auth/logout')
        client.post('/api/auth/login',json={'username':'bob','password':'bob-strong-password'})
        assert client.get('/api/jobs/'+identity).status_code == 404
        assert client.get('/api/jobs/'+identity+'/events').status_code == 404
        assert client.get('/api/runs/'+identity+'/export').status_code == 404


def test_cloud_upload_validates_pdf_before_publishing_asset(cloud):
    from reportlab.pdfgen.canvas import Canvas
    store,alice,_=cloud
    app=create_app(store,lambda _:None,{'details':{}})
    with TestClient(app,base_url='https://testserver') as client:
        client.post('/api/auth/login',json={'username':'alice','password':'alice-strong-password'})
        ticket=client.post('/api/uploads/intent',json={'kind':'pdf','filename':'notice.pdf'}).json()
        record=store.get('UPLOAD#'+ticket['upload_id'])
        store.s3.put_object(Bucket=store.bucket,Key=record['key'],Body=b'%PDF-fake')
        assert client.post('/api/uploads/'+ticket['upload_id']+'/complete').status_code == 400
        stream=BytesIO(); c=Canvas(stream); c.drawString(70,700,'Survey 384; Area: 2 acres'); c.save()
        store.s3.put_object(Bucket=store.bucket,Key=record['key'],Body=stream.getvalue())
        result=client.post('/api/uploads/'+ticket['upload_id']+'/complete')
        assert result.status_code == 200
        asset_id=result.json()['asset_id']
        assert store.asset(asset_id,alice['id'])['kind'] == 'pdf'
        assert client.post('/api/uploads/'+ticket['upload_id']+'/complete').json()['asset_id'] == asset_id


def test_worker_bundle_rejects_traversal_and_links(tmp_path):
    path=Path(__file__).resolve().parents[1]/'aws/worker_entry.py'
    spec=importlib.util.spec_from_file_location('worker_bootstrap',path)
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    for name,link in [('../escape',False),('symlink',True)]:
        archive=tmp_path/'malicious.tar.gz'
        with tarfile.open(archive,'w:gz') as tar:
            entry=tarfile.TarInfo(name)
            if link: entry.type=tarfile.SYMTYPE; entry.linkname='/etc/passwd'
            else: entry.size=1
            tar.addfile(entry,None if link else BytesIO(b'x'))
        with pytest.raises(ValueError,match='Unsafe'):
            module.safe_extract(archive,tmp_path/'unpack')
