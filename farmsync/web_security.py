"""CSP for the shared, locally bundled web application."""
import base64
import hashlib
import html
import re
from pathlib import Path
from fastapi.responses import HTMLResponse


def html_response(path, upload_origin=None, base_path=''):
    source = Path(path).read_text(encoding='utf-8')
    if base_path:
        if not re.fullmatch(r'/[a-zA-Z0-9_-]+', base_path):
            raise ValueError('Invalid API stage path')
        source = source.replace('"/static/', '"' + base_path + '/static/')
        source = source.replace('<head>', '<head><meta name="api-base" content="' + base_path + '">')
    scripts = re.findall(r'<script\b[^>]*>(.*?)</script>', source, flags=re.S)
    handlers = [html.unescape(v) for v in re.findall(r'\bon\w+="([^"]*)"', source)]
    hashes = {"'sha256-" + base64.b64encode(hashlib.sha256(v.encode()).digest()).decode() + "'" for v in scripts + handlers if v.strip()}
    policy = "default-src 'none'; base-uri 'self'; object-src 'none'; frame-ancestors 'none'; form-action 'self'; "
    policy += "script-src 'self' 'unsafe-hashes' " + ' '.join(sorted(hashes)) + '; '
    remote = (' ' + upload_origin) if upload_origin else ''
    policy += "style-src 'self' 'unsafe-inline'; font-src 'self'; connect-src 'self'" + remote + "; img-src 'self' data: blob: https://*.basemaps.cartocdn.com https://server.arcgisonline.com" + remote + ';'
    return HTMLResponse(source, headers={'Content-Security-Policy': policy, 'X-Frame-Options': 'DENY'})
