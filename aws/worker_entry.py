"""Small Lambda bootstrap for a checksum-pinned S3 ML/GIS bundle.

Download occurs inside the async invocation (not during init). HTTP requests use
a different lightweight Lambda, so a large model cold start cannot block its API.
"""
from hashlib import sha256
import os
from pathlib import Path
import shutil
import sys
import tarfile
import uuid


def safe_extract(archive, target, max_bytes=8 * 1024**3):
    root, total = Path(target).resolve(), 0
    with tarfile.open(archive, 'r:gz') as bundle:
        members = bundle.getmembers()
        for member in members:
            path = (root / member.name).resolve()
            total += member.size
            if not path.is_relative_to(root) or member.issym() or member.islnk() or not (member.isfile() or member.isdir()) or total > max_bytes:
                raise ValueError('Unsafe or excessive bundle entry')
        bundle.extractall(root, members=members, filter='data')


def load_bundle():
    checksum = os.environ['FARMSYNC_BUNDLE_SHA256']
    if len(checksum) != 64 or any(c not in '0123456789abcdef' for c in checksum):
        raise ValueError('A pinned SHA256 bundle is required')
    target = Path('/tmp') / ('farmsync-bundle-' + checksum)
    if not (target / '.verified').exists():
        import boto3
        client = boto3.client('s3', region_name='ap-south-1')
        archive = Path('/tmp') / ('farmsync-' + uuid.uuid4().hex + '.tar.gz')
        staging = Path('/tmp') / ('farmsync-unpack-' + uuid.uuid4().hex)
        try:
            metadata = client.head_object(Bucket=os.environ['FARMSYNC_BUCKET'], Key=os.environ['FARMSYNC_BUNDLE_KEY'])
            if metadata['ContentLength'] > 4 * 1024**3:
                raise ValueError('Bundle exceeds download limit')
            client.download_file(os.environ['FARMSYNC_BUCKET'], os.environ['FARMSYNC_BUNDLE_KEY'], str(archive))
            digest = sha256()
            with archive.open('rb') as handle:
                for chunk in iter(lambda: handle.read(1024 * 1024), b''):
                    digest.update(chunk)
            if digest.hexdigest() != checksum:
                raise ValueError('Bundle checksum mismatch')
            safe_extract(archive, staging)
            (staging / '.verified').write_text(checksum)
            staging.rename(target)
        finally:
            archive.unlink(missing_ok=True)
            if staging.exists():
                shutil.rmtree(staging)
    # Application updates are small signed Lambda artifacts; dependency/data
    # bundles remain immutable. Verify the overlay before replacing cached code.
    overlay=Path(__file__).resolve().parent/'overlay/farmsync'
    expected=os.environ.get('FARMSYNC_SOURCE_SHA256')
    digest=sha256()
    for path in sorted(overlay.rglob('*')):
        if path.is_file() and '__pycache__' not in path.parts and path.suffix in {'.py','.json','.html','.js','.css','.pth','.png'}:
            digest.update(path.relative_to(overlay).as_posix().encode())
            digest.update(sha256(path.read_bytes()).digest())
    if not expected or digest.hexdigest()!=expected:
        raise ValueError('Application overlay checksum mismatch')
    shutil.copytree(overlay,target/'farmsync',dirs_exist_ok=True)
    sys.path[:0] = [str(target / 'python'), str(target)]
    os.chdir(target)
    os.environ.update({'HF_HUB_OFFLINE': '1', 'HF_HOME': str(target / 'cache/huggingface'), 'TORCH_HOME': str(target / 'cache/torch'), 'FARMSYNC_OCR_MODEL_DIR': str(target / 'models/easyocr'), 'OMP_NUM_THREADS': '1', 'MKL_NUM_THREADS': '1'})
    return target


def handler(event, context):
    load_bundle()
    from farmsync.cloud.worker import execute
    return execute(event, context)
