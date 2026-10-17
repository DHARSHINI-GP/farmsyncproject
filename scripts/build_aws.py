"""Build immutable AWS artifacts using Linux wheels, never Windows DLLs.

Download wheels first with --download-wheels. A build has NOT passed Linux runtime
validation until the deployment script initializes and smoke-tests its worker.
"""
import argparse
import asyncio
from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def source_digest(root):
    digest=sha256()
    allowed={'.py','.json','.html','.js','.css','.pth','.png'}
    for path in sorted(Path(root).rglob('*')):
        if path.is_file() and '__pycache__' not in path.parts and path.suffix in allowed:
            digest.update(path.relative_to(root).as_posix().encode())
            digest.update(sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def build_entry(out):
    with zipfile.ZipFile(out/'worker-entry.zip','w',zipfile.ZIP_DEFLATED) as archive:
        archive.write(ROOT/'aws/worker_entry.py','worker_entry.py')
        for path in (ROOT/'farmsync').rglob('*'):
            if path.is_file() and '__pycache__' not in path.parts:
                archive.write(path,'overlay/farmsync/'+path.relative_to(ROOT/'farmsync').as_posix())


def unpack_wheel(wheel, target):
    with zipfile.ZipFile(wheel) as archive:
        for name in archive.namelist():
            if name.endswith('/'):
                continue
            parts = Path(name).parts
            if any(p == '..' for p in parts) or Path(name).is_absolute():
                raise ValueError('Unsafe wheel entry')
            # Wheel .data purelib/platlib payload belongs on sys.path.
            if parts[0].endswith('.data'):
                if len(parts) < 3 or parts[1] not in {'purelib', 'platlib'}:
                    continue
                parts = parts[2:]
            destination = target.joinpath(*parts)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(archive.read(name))


def snapshot():
    print('Loading source engines for snapshot...', flush=True)
    from farmsync import server
    print('Source engines ready', flush=True)
    responses = {}
    for path, func in [('/api/parcels', server.get_parcels), ('/api/geojson/all-parcels', server.get_all_parcels_geojson), ('/api/geojson/roads', server.get_roads_geojson), ('/api/geojson/waterbodies', server.get_waterbodies), ('/api/status', server.get_system_status), ('/api/knowledge/status', server.get_knowledge_status)]:
        print('Snapshot:', path, flush=True)
        responses[path] = asyncio.run(func())
    spatial = server.orchestrator.spatial
    identities = list(spatial.gdf_parcels_wgs84['parcel_id']) + list(spatial.list_surveys())
    if spatial.gdf_fmb_wgs84 is not None:
        identities += list(spatial.gdf_fmb_wgs84['kide_clean'])
    details = {}
    for index, identity in enumerate(set(str(v) for v in identities)):
        if index % 100 == 0: print('Parcel snapshot:', index, 'of', len(set(identities)), flush=True)
        p = spatial.get_parcel(identity)
        if p:
            details[identity] = {'parcel': p, 'constraints': spatial.check_constraints(identity)}
    from farmsync.platform_api import capability_summary
    responses['/api/capabilities'] = capability_summary(server.orchestrator)
    responses['/api/status'].update(s3_integrated=True, dynamodb_integrated=True, deployment='AWS_LAMBDA_S3_DYNAMODB')
    documents = {}
    root = ROOT / 'data/FAI_Product_Challange/TASK_2/Land_documents'
    for p in root.rglob('*.pdf'):
        if 'Uploads' in p.parts:
            continue
        relative = p.relative_to(root)
        documents.setdefault(str(relative.parent), []).append({'filename': p.name, 'relative_path': str(relative), 'size_bytes': p.stat().st_size})
    images = [{'filename': name} for name in sorted(server.orchestrator.vision.image_registry) if not name.startswith('asset:')]
    return {'responses': responses, 'details': details, 'documents': documents, 'images': images,
            'allowed_evidence': {'document_path': [v['relative_path'] for rows in documents.values() for v in rows], 'image_filename': [i['filename'] for i in images]},
            'image_objects': {name: 'dataset-images/' + name for name in server.orchestrator.vision.image_registry if not name.startswith('asset:')},
            'source_scope': 'Supplied cadastral snapshots, not authoritative ownership records'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--download-wheels', action='store_true')
    parser.add_argument('--snapshot-only', action='store_true')
    parser.add_argument('--api-wheels', action='store_true')
    parser.add_argument('--reuse-snapshot', action='store_true')
    parser.add_argument('--refresh-code', action='store_true')
    parser.add_argument('--entry-only', action='store_true', help='Refresh the small signed application overlay without rebuilding the immutable dependency/data bundle')
    args = parser.parse_args()
    out = ROOT / '.runtime/aws-build'
    out.mkdir(parents=True, exist_ok=True)
    if args.entry_only:
        record=json.loads((out/'manifest.json').read_text())
        build_entry(out)
        record.update(source_sha256=source_digest(ROOT/'farmsync'),entry_sha256=sha256((out/'worker-entry.zip').read_bytes()).hexdigest(),linux_runtime_verified=False)
        (out/'manifest.json').write_text(json.dumps(record,indent=2))
        print('Application overlay refreshed; target runtime revalidation is required')
        return
    wheels = ROOT / ('.runtime/aws-api-wheels' if args.api_wheels else '.runtime/aws-wheels')
    if args.download_wheels:
        from farmsync.aws import system_ca_bundle
        env = dict(os.environ)
        ca = system_ca_bundle()
        if ca is not True: env['PIP_CERT'] = str(ca)
        requirements = ROOT / ('aws/api-requirements.txt' if args.api_wheels else 'requirements.aws.txt')
        subprocess.run([sys.executable, '-m', 'pip', 'download', '--dest', str(wheels), '--only-binary=:all:', '--platform', 'manylinux_2_28_x86_64', '--platform', 'manylinux2014_x86_64', '--python-version', '312', '--implementation', 'cp', '--abi', 'cp312', '--extra-index-url', 'https://download.pytorch.org/whl/cpu', '-r', str(requirements)], env=env, check=True)
        return
    os.environ.update(FARMSYNC_OFFLINE='true', HF_HUB_OFFLINE='1', OMP_NUM_THREADS='1', MKL_NUM_THREADS='1', FARMSYNC_DATABASE=str(out / 'build.sqlite3'))
    if args.reuse_snapshot:
        data=json.loads((out/'cloud-snapshot.json').read_text(encoding='utf8'))
    else:
        data = snapshot()
        (out / 'cloud-snapshot.json').write_text(json.dumps(data, allow_nan=False), encoding='utf-8')
    if args.snapshot_only:
        print('Built source snapshot with', len(data['details']), 'unambiguous parcel identities')
        return
    if args.api_wheels:
        stage = out / 'api'
        if stage.exists() and not args.refresh_code:
            raise SystemExit('Existing API staging directory; archive it before rebuilding')
        stage.mkdir(exist_ok=True)
        wheel_files = sorted(wheels.glob('*.whl'))
        if not wheel_files:
            raise SystemExit('Download the API Linux wheels first')
        for wheel in wheel_files: unpack_wheel(wheel, stage)
        shutil.copytree(ROOT/'farmsync/cloud', stage/'farmsync/cloud', dirs_exist_ok=True, ignore=shutil.ignore_patterns('__pycache__'))
        for directory in ('farmsync', 'farmsync/spatial'):
            (stage/directory).mkdir(exist_ok=True)
            (stage/directory/'__init__.py').touch()
        for name in ('storage.py', 'runtime.py', 'platform_api.py', 'aws.py', 'web_security.py'):
            shutil.copyfile(ROOT/'farmsync'/name, stage/'farmsync'/name)
        shutil.copyfile(ROOT/'farmsync/spatial/amazon_location.py', stage/'farmsync/spatial/amazon_location.py')
        shutil.copytree(ROOT/'farmsync/static', stage/'farmsync/static', dirs_exist_ok=True)
        shutil.copyfile(out/'cloud-snapshot.json', stage/'cloud-snapshot.json')
        with zipfile.ZipFile(out/'api.zip', 'w', zipfile.ZIP_DEFLATED) as z:
            for p in stage.rglob('*'):
                if p.is_file(): z.write(p, p.relative_to(stage).as_posix())
        total=sum(p.stat().st_size for p in stage.rglob('*') if p.is_file())
        if total > 250*1024**2: raise ValueError('API exceeds Lambda uncompressed package limit')
        print('API package built:', total, 'uncompressed bytes; Lambda functional smoke still required')
        (out/'api-source-sha256.txt').write_text(source_digest(ROOT/'farmsync'))
        (out/'api-sha256.txt').write_text(sha256((out/'api.zip').read_bytes()).hexdigest())
        return
    wheel_files = sorted(wheels.glob('*.whl'))
    if not wheel_files:
        raise SystemExit('Linux wheels are missing; run --download-wheels first')
    stage = out / 'bundle'
    if stage.exists() and not args.refresh_code:
        raise SystemExit('Use a new build directory or archive the existing bundle before rebuilding')
    stage.mkdir(exist_ok=True)
    site = stage / 'python'
    site.mkdir(exist_ok=True)
    manifest = []
    for wheel in wheel_files:
        if 'win_' in wheel.name or 'macosx' in wheel.name:
            raise ValueError('Non-Linux native wheel rejected')
        if not args.refresh_code: unpack_wheel(wheel, site)
        manifest.append({'filename': wheel.name, 'sha256': sha256(wheel.read_bytes()).hexdigest()})
    shutil.copytree(ROOT / 'farmsync', stage / 'farmsync', dirs_exist_ok=True, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    if not args.refresh_code:
        shutil.copytree(ROOT / 'data/FAI_Product_Challange/TASK_2', stage / 'data/FAI_Product_Challange/TASK_2', ignore=shutil.ignore_patterns('Uploads'))
        shutil.copytree(ROOT / 'data/FAI_Product_Challange/TASK_4', stage / 'data/FAI_Product_Challange/TASK_4')
    for source, dest in [(Path.home()/'.cache/torch/hub/checkpoints', stage/'cache/torch/hub/checkpoints'), (Path.home()/'.cache/huggingface/hub/models--sentence-transformers--all-MiniLM-L6-v2', stage/'cache/huggingface/hub/models--sentence-transformers--all-MiniLM-L6-v2'), (ROOT/'.runtime/models/easyocr', stage/'models/easyocr')]:
        if source.exists() and not args.refresh_code: shutil.copytree(source, dest, symlinks=False)
    archive = out / 'worker-bundle.tar.gz'
    def release_filter(info):
        name=info.name.replace('\\','/')
        if name.startswith('cache/huggingface/'):
            allowed='cache/huggingface/hub/models--sentence-transformers--all-MiniLM-L6-v2'
            if name not in {'cache/huggingface/hub',allowed} and not name.startswith(allowed+'/'):return None
        if '__pycache__' in name.split('/') or Path(name).name in {'.env','token','stored_tokens','.agent_harnesses.json'}:return None
        return info
    with tarfile.open(archive, 'w:gz', dereference=True, compresslevel=1) as tar:
        for p in stage.iterdir(): tar.add(p, arcname=p.name, filter=release_filter)
    (out / 'worker-entry.zip').unlink(missing_ok=True)
    build_entry(out)
    # API dependency closure is resolved separately to keep native ML imports out.
    # Build script refuses to silently package a worker site-packages tree as API.
    digest=sha256()
    with archive.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024*1024),b''):digest.update(chunk)
    record = {'bundle_sha256': digest.hexdigest(), 'entry_sha256':sha256((out/'worker-entry.zip').read_bytes()).hexdigest(), 'bytes': archive.stat().st_size, 'source_sha256':source_digest(stage/'farmsync'), 'wheels': manifest, 'linux_runtime_verified': False, 'next_gate': 'Private Lambda worker initialization + functional smoke, then API packaging/deployment'}
    (out / 'manifest.json').write_text(json.dumps(record, indent=2))
    print('Worker artifacts built; Linux execution remains unverified')


if __name__ == '__main__': main()
