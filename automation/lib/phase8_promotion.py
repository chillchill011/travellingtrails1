#!/usr/bin/env python3
"""Phase 8 production promotion state and safety boundary.

Captures the exact currently-reviewed Staging post/media as an immutable manifest.
Promotion itself is executed by n8n with its GitHub credential. This module never
changes draft:true to false and never calls DeepSeek.
"""
from __future__ import annotations
import base64, hashlib, json, re, urllib.parse, urllib.request, urllib.error, time
from typing import Any
from phase5_state import RunStore, StateError, canonical_json, utc_now

REPO='chillchill011/travellingtrails1'
SOURCE_BRANCH='Staging'
TARGET_BRANCH='main'
PROD_SITE_ID='edd2477f-24f5-4005-a05c-f0310f1efe11'
PROD_SITE_NAME='travellingtrails1'
PROD_ORIGIN='https://travellingtrails.in'
STAGING_ORIGIN='https://devtravtes.netlify.app'
ALLOWED_POST_RE=re.compile(r'^src/blog/[A-Za-z0-9._-]+\.md$')
ALLOWED_MEDIA_RE=re.compile(r'^src/assets/images/[A-Za-z0-9._/-]+$')
SHA40=re.compile(r'^[0-9a-f]{40}$')
STATUSES={'NOT_STARTED','USER_FLOW_READY','APPROVAL_REQUIRED','PROMOTION_READY','PROMOTING','PROMOTED_DRAFT','PRODUCTION_DEPLOY_VERIFIED','PUBLISH_WAITING','PUBLISHED_DETECTED','PUBLISHED_VERIFIED','COMPLETED','FAILED'}


def migrate(store:RunStore)->None:
    additions=[
      ('phase8_status',"TEXT NOT NULL DEFAULT 'NOT_STARTED'"),('phase8_last_safe_status','TEXT'),('phase8_error_message','TEXT'),
      ('orchestration_status','TEXT'),('promotion_approved_at','TEXT'),('promotion_source_commit','TEXT'),('promotion_manifest_json','TEXT'),
      ('promotion_commit_sha','TEXT'),('production_draft_deploy_id','TEXT'),('production_draft_deploy_commit','TEXT'),
      ('publish_commit_sha','TEXT'),('production_deploy_id','TEXT'),('production_deploy_commit','TEXT'),('production_url','TEXT'),
      ('final_result_json','TEXT'),('completion_notification_status','TEXT'),('completion_notification_sent_at','TEXT')]
    with store.connect() as db:
      cols={r[1] for r in db.execute('PRAGMA table_info(runs)')}
      for n,ddl in additions:
        if n not in cols: db.execute(f'ALTER TABLE runs ADD COLUMN {n} {ddl}')


def _run(store,run_id):
    migrate(store); r=store.get_run(run_id)
    if r is None: raise StateError('run not found')
    return r


def _update(store,run_id,**c):
    allowed={'phase8_status','phase8_last_safe_status','phase8_error_message','orchestration_status','promotion_approved_at','promotion_source_commit','promotion_manifest_json','promotion_commit_sha','production_draft_deploy_id','production_draft_deploy_commit','publish_commit_sha','production_deploy_id','production_deploy_commit','production_url','final_result_json','completion_notification_status','completion_notification_sent_at'}
    if set(c)-allowed: raise StateError('invalid Phase 8 state field')
    fields=['updated_at=?']; vals=[utc_now()]
    for k,v in c.items():
      if k=='phase8_status' and v not in STATUSES: raise StateError('invalid Phase 8 status')
      if k in {'promotion_manifest_json','final_result_json'} and not isinstance(v,str): v=canonical_json(v)
      if k=='phase8_error_message' and v is not None: v=str(v)[:4000]
      fields.append(k+'=?'); vals.append(v)
    vals.append(run_id)
    with store.connect() as db: db.execute('UPDATE runs SET '+','.join(fields)+' WHERE run_id=?',vals)
    return _run(store,run_id)


def _api(path:str)->Any:
    req=urllib.request.Request('https://api.github.com'+path,headers={'User-Agent':'travelling-trails-phase8/1','Accept':'application/vnd.github+json'})
    try:
      with urllib.request.urlopen(req,timeout=25) as r: return json.load(r)
    except Exception as exc: raise StateError(f'GitHub read failed for {path}') from exc


def _ref(branch:str)->str:
    d=_api(f'/repos/{REPO}/git/ref/heads/{urllib.parse.quote(branch,safe="")}')
    sha=str((d.get('object') or {}).get('sha') or '')
    if not SHA40.fullmatch(sha): raise StateError('invalid branch SHA')
    return sha


def _content(path:str,ref:str)->dict[str,Any]|None:
    q=urllib.parse.urlencode({'ref':ref})
    try: d=_api(f'/repos/{REPO}/contents/{urllib.parse.quote(path,safe="/")}?{q}')
    except StateError as exc:
      # Public API returns 404 through urllib; detect explicitly using a direct request.
      url='https://api.github.com'+f'/repos/{REPO}/contents/{urllib.parse.quote(path,safe="/")}?{q}'
      req=urllib.request.Request(url,headers={'User-Agent':'travelling-trails-phase8/1','Accept':'application/vnd.github+json'})
      try:
        with urllib.request.urlopen(req,timeout=25) as r: d=json.load(r)
      except urllib.error.HTTPError as e:
        if e.code==404: return None
        raise exc
    if isinstance(d,list): raise StateError('expected file, got directory')
    return d


def _decode_content(d:dict[str,Any])->bytes:
    raw=d.get('content')
    if not isinstance(raw,str): raise StateError('GitHub content payload missing bytes')
    return base64.b64decode(raw.encode('ascii'),validate=False)


def _sha256(b:bytes)->str: return hashlib.sha256(b).hexdigest()


def _draft_true(markdown:str)->bool:
    if not markdown.startswith('---'): return False
    parts=markdown.split('---',2)
    if len(parts)<3:return False
    return re.search(r'(?mi)^draft:\s*true\s*$',parts[1]) is not None


def _title(markdown:str)->str:
    if not markdown.startswith('---'): return ''
    parts=markdown.split('---',2)
    if len(parts)<3:return ''
    m=re.search(r'(?mi)^title:\s*["\']?(.*?)["\']?\s*$',parts[1])
    return (m.group(1).strip() if m else '').strip('"\'')


def _media_paths(markdown:str)->list[str]:
    vals=sorted(set(re.findall(r'/assets/images/([A-Za-z0-9._/-]+)',markdown)))
    out=['src/assets/images/'+v for v in vals]
    for p in out:
      if not ALLOWED_MEDIA_RE.fullmatch(p) or '..' in p: raise StateError('unsafe media path in reviewed Markdown')
    return out


def mark_review_ready(store:RunStore,run_id:str)->dict[str,Any]:
    r=_run(store,run_id)
    if r.get('phase7_status') not in {'REVIEW_READY','NOTIFICATION_SENDING','NOTIFICATION_SENT'}: raise StateError('Phase 8 requires Phase 7 REVIEW_READY')
    if r.get('phase8_status') in {'PROMOTION_READY','PROMOTING','PROMOTED_DRAFT','PRODUCTION_DEPLOY_VERIFIED','PUBLISH_WAITING','PUBLISHED_DETECTED','PUBLISHED_VERIFIED','COMPLETED'}:
      return view(store,run_id)
    _update(store,run_id,phase8_status='APPROVAL_REQUIRED',phase8_last_safe_status='APPROVAL_REQUIRED',orchestration_status='REVIEW_READY',phase8_error_message=None)
    return view(store,run_id,action='APPROVAL_REQUIRED')


def approve_and_capture(store:RunStore,run_id:str,approved:bool,expected_title:str='')->dict[str,Any]:
    r=_run(store,run_id)
    if approved is not True: raise StateError('explicit approved=true is required')
    if r.get('phase7_status') not in {'REVIEW_READY','NOTIFICATION_SENDING','NOTIFICATION_SENT'}: raise StateError('promotion requires Phase 7 REVIEW_READY')
    if r.get('promotion_manifest_json'):
      return view(store,run_id,action='PROMOTION_READY',idempotent=True)
    post_path=str(r.get('post_path') or '')
    if not ALLOWED_POST_RE.fullmatch(post_path) or '..' in post_path: raise StateError('post path is not allowlisted')
    source_commit=str(r.get('staging_deploy_commit') or '')
    draft_commit=str(r.get('draft_commit_sha') or '')
    if not SHA40.fullmatch(source_commit): raise StateError('verified reviewed Staging commit missing')
    if not SHA40.fullmatch(draft_commit) or draft_commit!=source_commit: raise StateError('reviewed Staging commit does not match draft commit')
    try: review_payload=json.loads(r.get('review_payload_json') or 'null')
    except Exception as exc: raise StateError('review payload is invalid') from exc
    if not isinstance(review_payload,dict) or str(review_payload.get('commitSha') or '')!=source_commit:
      raise StateError('review payload commit does not match reviewed Staging commit')
    post=_content(post_path,source_commit)
    if post is None: raise StateError('reviewed Staging post is missing')
    post_bytes=_decode_content(post); markdown=post_bytes.decode('utf-8')
    if not _draft_true(markdown): raise StateError('automated promotion requires reviewed draft:true')
    title=_title(markdown)
    if expected_title.strip() and title.strip()!=expected_title.strip(): raise StateError('reviewed title does not match approval')
    media=[]
    for path in _media_paths(markdown):
      d=_content(path,source_commit)
      if d is None: raise StateError(f'referenced media missing on Staging: {path}')
      b=_decode_content(d); sha=str(d.get('sha') or '')
      if not SHA40.fullmatch(sha): raise StateError('invalid media blob SHA')
      media.append({'repoPath':path,'blobSha':sha,'sha256':_sha256(b)})
    post_sha=str(post.get('sha') or '')
    if not SHA40.fullmatch(post_sha): raise StateError('invalid post blob SHA')
    main_sha=_ref(TARGET_BRANCH)
    entries=[{'repoPath':post_path,'blobSha':post_sha,'sha256':_sha256(post_bytes)}]+media
    collisions=[]; identical=[]; creates=[]
    for e in entries:
      cur=_content(e['repoPath'],main_sha)
      if cur is None: creates.append(e['repoPath']); continue
      cur_sha=str(cur.get('sha') or '')
      if cur_sha==e['blobSha']: identical.append(e['repoPath'])
      else: collisions.append({'repoPath':e['repoPath'],'mainBlobSha':cur_sha,'reviewedBlobSha':e['blobSha']})
    if collisions: raise StateError('HARD_COLLISION: '+canonical_json(collisions))
    manifest={'runId':run_id,'sourceBranch':SOURCE_BRANCH,'sourceCommit':source_commit,'postPath':post_path,'postBlobSha':post_sha,'postSha256':_sha256(post_bytes),'draft':True,'title':title,'media':media,'targetBranch':TARGET_BRANCH,'targetBaseCommit':main_sha,'approved':True,'creates':creates,'identical':identical}
    _update(store,run_id,phase8_status='PROMOTION_READY',phase8_last_safe_status='PROMOTION_READY',phase8_error_message=None,orchestration_status='APPROVED',promotion_approved_at=utc_now(),promotion_source_commit=source_commit,promotion_manifest_json=manifest)
    return view(store,run_id,action='PROMOTION_READY')


def mark_promoting(store:RunStore,run_id:str)->dict[str,Any]:
    r=_run(store,run_id)
    if r.get('promotion_commit_sha'): return view(store,run_id,action='ALREADY_PROMOTED',idempotent=True)
    if r.get('phase8_status')!='PROMOTION_READY' or not r.get('promotion_manifest_json'): raise StateError('promotion manifest is not ready')
    _update(store,run_id,phase8_status='PROMOTING',phase8_last_safe_status='PROMOTION_READY')
    return view(store,run_id,action='PROMOTE')


def complete_promotion(store:RunStore,run_id:str,commit_sha:str)->dict[str,Any]:
    r=_run(store,run_id)
    if r.get('promotion_commit_sha'):
      if r.get('promotion_commit_sha')!=commit_sha: raise StateError('promotion commit mismatch')
      return view(store,run_id,action='ALREADY_PROMOTED',idempotent=True)
    if not SHA40.fullmatch(str(commit_sha or '')): raise StateError('invalid promotion commit SHA')
    manifest=json.loads(r.get('promotion_manifest_json') or 'null')
    if not isinstance(manifest,dict): raise StateError('promotion manifest missing')
    _update(store,run_id,phase8_status='PROMOTED_DRAFT',phase8_last_safe_status='PROMOTED_DRAFT',promotion_commit_sha=commit_sha,phase8_error_message=None)
    return view(store,run_id,action='VERIFY_PRODUCTION_DRAFT')



def _compare_contains(base:str,head:str)->bool:
    try: d=_api(f'/repos/{REPO}/compare/{base}...{head}')
    except Exception: return False
    return d.get('status') in {'identical','ahead'}

def _netlify_json(url:str)->Any:
    req=urllib.request.Request(url,headers={'User-Agent':'travelling-trails-phase8/1'})
    with urllib.request.urlopen(req,timeout=25) as r: return json.load(r)

def _http_text(url:str)->tuple[int,str]:
    req=urllib.request.Request(url,headers={'User-Agent':'travelling-trails-phase8/1'})
    with urllib.request.urlopen(req,timeout=25) as r: return r.status,r.read().decode('utf-8','replace')

def _slugify_title(title:str)->str:
    import unicodedata
    x=unicodedata.normalize('NFKD',title).encode('ascii','ignore').decode().lower()
    x=re.sub(r'[^a-z0-9]+','-',x).strip('-')
    if not x: raise StateError('cannot derive production URL from title')
    return x

def verify_production_draft(store:RunStore,run_id:str)->dict[str,Any]:
    r=_run(store,run_id); promotion=str(r.get('promotion_commit_sha') or '')
    if not SHA40.fullmatch(promotion): raise StateError('promotion commit missing')
    main=_ref(TARGET_BRANCH)
    if not _compare_contains(promotion,main): raise StateError('promotion commit is not contained by main')
    manifest=json.loads(r.get('promotion_manifest_json') or 'null')
    if not isinstance(manifest,dict): raise StateError('promotion manifest missing')
    cur=_content(manifest['postPath'],main)
    if cur is None: raise StateError('production draft post missing')
    md=_decode_content(cur).decode('utf-8')
    if not _draft_true(md): raise StateError('production promotion no longer has draft:true before handoff')
    site=_netlify_json(f'https://api.netlify.com/api/v1/sites/{PROD_SITE_ID}')
    if str(site.get('id') or '')!=PROD_SITE_ID or str(site.get('name') or '')!=PROD_SITE_NAME: raise StateError('wrong production Netlify identity')
    deploys=_netlify_json(f'https://api.netlify.com/api/v1/sites/{PROD_SITE_ID}/deploys?per_page=30')
    match=None
    for d in deploys:
      if d.get('branch')!=TARGET_BRANCH or d.get('state')!='ready': continue
      dep=str(d.get('commit_ref') or '')
      if dep==promotion or (SHA40.fullmatch(dep) and _compare_contains(promotion,dep)):
        match=d; break
    if not match: return view(store,run_id,action='PRODUCTION_DEPLOY_WAITING')
    _update(store,run_id,phase8_status='PUBLISH_WAITING',phase8_last_safe_status='PUBLISH_WAITING',production_draft_deploy_id=match.get('id'),production_draft_deploy_commit=match.get('commit_ref'))
    return view(store,run_id,action='PUBLISH_WAITING')

def wait_production_draft(store:RunStore,run_id:str,timeout_seconds:int=150)->dict[str,Any]:
    deadline=time.monotonic()+max(0,min(int(timeout_seconds),240))
    while True:
      r=verify_production_draft(store,run_id)
      if r.get('action')!='PRODUCTION_DEPLOY_WAITING': return r
      if time.monotonic()>=deadline: return r
      time.sleep(5)

def waiting_run_ids(store:RunStore)->list[str]:
    migrate(store)
    with store.connect() as db:
      return [r[0] for r in db.execute("SELECT run_id FROM runs WHERE phase8_status IN ('PUBLISH_WAITING','PUBLISHED_DETECTED') ORDER BY updated_at")]

def verify_publication(store:RunStore,run_id:str)->dict[str,Any]:
    r=_run(store,run_id)
    if r.get('phase8_status')=='COMPLETED': return view(store,run_id,action='COMPLETED',idempotent=True)
    if r.get('phase8_status') not in {'PUBLISH_WAITING','PUBLISHED_DETECTED','PUBLISHED_VERIFIED','FAILED'}: raise StateError('run is not awaiting manual publication')
    manifest=json.loads(r.get('promotion_manifest_json') or 'null')
    if not isinstance(manifest,dict): raise StateError('promotion manifest missing')
    main=_ref(TARGET_BRANCH); cur=_content(manifest['postPath'],main)
    if cur is None: raise StateError('production article missing')
    md=_decode_content(cur).decode('utf-8')
    if _draft_true(md): return view(store,run_id,action='PUBLISH_WAITING',idempotent=True)
    # Require explicit draft:false in current front matter.
    if not re.search(r'(?mi)^draft:\s*false\s*$',md.split('---',2)[1] if md.startswith('---') and len(md.split('---',2))>=3 else ''):
      raise StateError('manual publication state is ambiguous')
    promotion=str(r.get('promotion_commit_sha') or '')
    cmp=_api(f'/repos/{REPO}/compare/{promotion}...{main}')
    files=[f.get('filename') for f in (cmp.get('files') or [])]
    unexpected=[f for f in files if f!=manifest['postPath']]
    if unexpected: raise StateError('unexpected unrelated changes between promotion and publish: '+canonical_json(unexpected))
    _update(store,run_id,phase8_status='PUBLISHED_DETECTED',phase8_last_safe_status='PUBLISHED_DETECTED',publish_commit_sha=main)
    site=_netlify_json(f'https://api.netlify.com/api/v1/sites/{PROD_SITE_ID}')
    if str(site.get('id') or '')!=PROD_SITE_ID or str(site.get('name') or '')!=PROD_SITE_NAME: raise StateError('wrong production Netlify identity')
    deploys=_netlify_json(f'https://api.netlify.com/api/v1/sites/{PROD_SITE_ID}/deploys?per_page=30')
    match=None
    for d in deploys:
      if d.get('branch')!=TARGET_BRANCH or d.get('state')!='ready': continue
      dep=str(d.get('commit_ref') or '')
      if dep==main or (SHA40.fullmatch(dep) and _compare_contains(main,dep)):
        match=d; break
    if not match: return view(store,run_id,action='PRODUCTION_PUBLISH_DEPLOY_WAITING')
    title=_title(md) or str(manifest.get('title') or '')
    url=f'{PROD_ORIGIN}/{_slugify_title(title)}/'
    status,html=_http_text(url)
    if not (200<=status<400): raise StateError('live article URL failed')
    _,blog=_http_text(PROD_ORIGIN+'/blog/')
    slug='/' + _slugify_title(title) + '/'
    if slug not in blog and title not in blog: raise StateError('published article not found in blog listing')
    final={'runId':run_id,'status':'COMPLETED','published':True,'publishCommitSha':main,'productionDeployId':match.get('id'),'productionDeployCommit':match.get('commit_ref'),'productionUrl':url}
    _update(store,run_id,phase8_status='COMPLETED',phase8_last_safe_status='COMPLETED',production_deploy_id=match.get('id'),production_deploy_commit=match.get('commit_ref'),production_url=url,final_result_json=final)
    return view(store,run_id,action='COMPLETED')

def fail(store,run_id,message):
    r=_run(store,run_id); safe=r.get('phase8_last_safe_status')
    _update(store,run_id,phase8_status='FAILED',phase8_last_safe_status=safe,phase8_error_message=message)
    return view(store,run_id,action='FAILED')


def view(store,run_id,*,action=None,idempotent=False):
    r=_run(store,run_id)
    try: manifest=json.loads(r.get('promotion_manifest_json') or 'null')
    except Exception: manifest=None
    return {'ok':True,'runId':run_id,'phase8Status':r.get('phase8_status') or 'NOT_STARTED','phase8LastSafeStatus':r.get('phase8_last_safe_status'),'action':action,'idempotent':idempotent,'promotionApprovedAt':r.get('promotion_approved_at'),'promotionSourceCommit':r.get('promotion_source_commit'),'promotionManifest':manifest,'promotionCommitSha':r.get('promotion_commit_sha'),'productionDraftDeployId':r.get('production_draft_deploy_id'),'productionDraftDeployCommit':r.get('production_draft_deploy_commit'),'publishCommitSha':r.get('publish_commit_sha'),'productionDeployId':r.get('production_deploy_id'),'productionDeployCommit':r.get('production_deploy_commit'),'productionUrl':r.get('production_url'),'errorMessage':r.get('phase8_error_message')}
