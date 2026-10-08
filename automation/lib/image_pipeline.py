#!/usr/bin/env python3
import hashlib, io, json, os, re, unicodedata
from pathlib import Path
from PIL import Image, ImageOps

SAFE_NAME_RE = re.compile(r'^[a-z0-9]+(?:-[a-z0-9]+)*\.jpg$')
MEDIA_EXTENSIONS = {'image/jpeg': '.jpg', 'image/png': '.png', 'image/webp': '.webp'}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()


def sha256_file(path) -> str:
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def sanitize_slug(value: str) -> str:
    value = unicodedata.normalize('NFKD', str(value or '')).encode('ascii', 'ignore').decode('ascii')
    value = value.lower().replace('&', ' and ')
    value = re.sub(r'[^a-z0-9]+', '-', value).strip('-')
    value = re.sub(r'-+', '-', value)
    if not value:
        raise ValueError('slug is empty after sanitization')
    return value


def normalize_extension(media_type: str) -> str:
    try:
        return MEDIA_EXTENSIONS[media_type.lower()]
    except Exception:
        raise ValueError(f'unsupported media type: {media_type}')


def orientation(width: int, height: int) -> str:
    if width == height:
        return 'square'
    return 'landscape' if width > height else 'portrait'


def validate_repo_path(repo_path: str) -> str:
    p = str(repo_path or '')
    prefix = 'src/assets/images/'
    if not p.startswith(prefix) or p.startswith('/') or '..' in p or '\\' in p:
        raise ValueError('unsafe repo path')
    name = p[len(prefix):]
    if '/' in name or not SAFE_NAME_RE.fullmatch(name):
        raise ValueError('unsafe image filename')
    return p


def inspect_source(path, source_id, source_filename, role):
    path = Path(path)
    with Image.open(path) as raw:
        im = ImageOps.exif_transpose(raw)
        width, height = im.size
        media_type = Image.MIME.get(im.format or raw.format, '') or Image.MIME.get(raw.format, '')
    if media_type not in MEDIA_EXTENSIONS:
        raise ValueError(f'unsupported source image type: {media_type}')
    return {
        'sourceId': str(source_id), 'sourceFilename': str(source_filename), 'sourcePath': str(path),
        'mediaType': media_type, 'width': width, 'height': height,
        'orientation': orientation(width, height), 'bytes': path.stat().st_size,
        'sha256': sha256_file(path), 'role': role,
    }


def _rgb(im):
    if im.mode == 'RGB': return im
    if im.mode in ('RGBA', 'LA'):
        bg = Image.new('RGB', im.size, 'white'); bg.paste(im, mask=im.getchannel('A')); return bg
    return im.convert('RGB')


def _fit_inside(im, max_width, max_height=None):
    w, h = im.size
    scale = min(1.0, max_width / w)
    if max_height:
        scale = min(scale, max_height / h)
    if scale < 1.0:
        return im.resize((max(1, round(w * scale)), max(1, round(h * scale))), Image.Resampling.LANCZOS)
    return im


def _crop_ratio_no_upscale(im, target_w, target_h):
    w, h = im.size
    ratio = target_w / target_h
    current = w / h
    if current > ratio:
        crop_w = round(h * ratio); left = (w - crop_w) // 2
        im = im.crop((left, 0, left + crop_w, h))
    elif current < ratio:
        crop_h = round(w / ratio); top = (h - crop_h) // 2
        im = im.crop((0, top, w, top + crop_h))
    return _fit_inside(im, target_w, target_h)


def process_derivative(source_path, output_path, role):
    with Image.open(source_path) as raw:
        im = _rgb(ImageOps.exif_transpose(raw))
        if role == 'featured': out = _fit_inside(im, 1600)
        elif role == 'thumbnail': out = _crop_ratio_no_upscale(im, 400, 267)
        elif role == 'gallery': out = _crop_ratio_no_upscale(im, 800, 533)
        elif role == 'route': out = _fit_inside(im, 1600)
        else: raise ValueError(f'unsupported derivative role: {role}')
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        out.save(output_path, 'JPEG', quality=85, optimize=True, progressive=True)
        width, height = out.size
    data = Path(output_path).read_bytes()
    return {'width': width, 'height': height, 'bytes': len(data), 'sha256': sha256_bytes(data), 'gitBlobSha': git_blob_sha(data)}


def build_manifest(run_id, post_slug, sources, output_dir):
    slug = sanitize_slug(post_slug)
    if str(run_id or '').strip() == '': raise ValueError('runId required')
    output_dir = Path(output_dir)
    inspected = []
    outputs = []
    gallery_i = route_i = 0
    for s in sources:
        role = s['role']
        meta = inspect_source(s['sourcePath'], s['sourceId'], s.get('sourceFilename', Path(s['sourcePath']).name), role)
        inspected.append(meta)
        if role == 'featured':
            planned = [('featured', f'{slug}-featured.jpg'), ('thumbnail', f'{slug}-thumbnail.jpg')]
        elif role == 'gallery':
            gallery_i += 1; planned = [('gallery', f'{slug}-{gallery_i:02d}.jpg')]
        elif role == 'route':
            route_i += 1; planned = [('route', f'{slug}-route-{route_i:02d}.jpg')]
        elif role == 'unused': planned = []
        else: raise ValueError(f'invalid source role: {role}')
        for out_role, filename in planned:
            repo = validate_repo_path(f'src/assets/images/{filename}')
            outputs.append({'sourceId': str(s['sourceId']), 'role': out_role, 'filename': filename,
                            'repoPath': repo, 'publicPath': f'/assets/images/{filename}',
                            'width': 0, 'height': 0, 'bytes': 0, 'sha256': '', 'status': 'PLANNED',
                            '_sourcePath': str(s['sourcePath']), '_localPath': str(output_dir / filename)})
    paths = [o['repoPath'] for o in outputs]
    if len(paths) != len(set(paths)): raise ValueError('duplicate output path')
    return {'runId': str(run_id), 'postSlug': slug, 'sourceImages': inspected, 'outputs': outputs}


def process_manifest(manifest):
    for o in manifest['outputs']:
        info = process_derivative(o['_sourcePath'], o['_localPath'], o['role'])
        o.update(info); o['status'] = 'PROCESSED'
    return manifest


def public_manifest(manifest):
    clean = json.loads(json.dumps(manifest))
    for o in clean['outputs']:
        o.pop('_sourcePath', None); o.pop('_localPath', None)
    return clean
