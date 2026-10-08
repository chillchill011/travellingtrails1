#!/usr/bin/env python3
"""Phase 7 staging-only deployment verification and review handoff."""
from __future__ import annotations
import json,re,unicodedata,urllib.request,urllib.error
from typing import Any
from phase5_state import RunStore,StateError,canonical_json,utc_now

STAGING_BRANCH='Staging'
STAGING_SITE_ID='bb8c325b-9562-4952-8613-439ca95dc9e0'
STAGING_SITE_NAME='devtravtes'
STAGING_ORIGIN='https://devtravtes.netlify.app'
PROD_SITE_ID='edd2477f-24f5-4005-a05c-f0310f1efe11'
PROD_ORIGIN='https://travellingtrails.in'
STATUSES={'NOT_STARTED','DEPLOY_WAITING','DEPLOY_VERIFIED','REVIEW_READY','NOTIFICATION_SENDING','NOTIFICATION_SENT','FAILED'}
SHA40=re.compile(r'^[0-9a-f]{40}$')

def migrate(store:RunStore)->None:
    additions=[
      ('phase7_status',"TEXT NOT NULL DEFAULT 'NOT_STARTED'"),('phase7_last_safe_status','TEXT'),('phase7_error_message','TEXT'),
      ('staging_deploy_id','TEXT'),('staging_deploy_commit','TEXT'),('staging_preview_url','TEXT'),('review_url','TEXT'),
      ('review_payload_json','TEXT'),('notification_status','TEXT'),('notification_sent_at','TEXT')]
    with store.connect() as db:
      cols={r[1] for r in db.execute('PRAGMA table_info(runs)')}
      for n,ddl in additions:
        if n not in cols: db.execute(f'ALTER TABLE runs ADD COLUMN {n} {ddl}')

def _run(store,run_id):
    migrate(store); r=store.get_run(run_id)
    if r is None: raise StateError('run not found')
    return r

def _update(store,run_id,**c):
    allowed={'phase7_status','phase7_last_safe_status','phase7_error_message','staging_deploy_id','staging_deploy_commit','staging_preview_url','review_url','review_payload_json','notification_status','notification_sent_at'}
    if set(c)-allowed: raise StateError('invalid Phase 7 state field')
    fields=['updated_at=?']; vals=[utc_now()]
    for k,v in c.items():
      if k=='phase7_status' and v not in STATUSES: raise StateError('invalid Phase 7 status')
      if k=='review_payload_json' and not isinstance(v,str): v=canonical_json(v)
      if k=='phase7_error_message' and v is not None: v=str(v)[:4000]
      fields.append(k+'=?'); vals.append(v)
    vals.append(run_id)
    with store.connect() as db:
      db.execute('UPDATE runs SET '+','.join(fields)+' WHERE run_id=?',vals)
    return _run(store,run_id)

def assert_staging_identity(branch:str,site_id:str,site_name:str)->None:
    if branch!=STAGING_BRANCH: raise StateError('Phase 7 refuses non-Staging branch')
    if site_id!=STAGING_SITE_ID: raise StateError('Phase 7 refuses non-staging Netlify site ID')
    if site_name!=STAGING_SITE_NAME: raise StateError('Phase 7 refuses non-staging Netlify project')

def slugify_title(title:str)->str:
    s=unicodedata.normalize('NFKD',title).encode('ascii','ignore').decode().lower()
    s=re.sub(r"[^a-z0-9]+",'-',s).strip('-')
    if not s: raise StateError('cannot derive staging permalink from title')
    return s

def _json_url(url:str)->Any:
    req=urllib.request.Request(url,headers={'User-Agent':'travelling-trails-phase7/1'})
    with urllib.request.urlopen(req,timeout=20) as r: return json.load(r)

def _http_ok(url:str)->bool:
    req=urllib.request.Request(url,method='GET',headers={'User-Agent':'travelling-trails-phase7/1'})
    with urllib.request.urlopen(req,timeout=20) as r: return 200 <= r.status < 400

def _commit_on_staging(commit:str)->bool:
    # compare base=commit, head=Staging; identical/ahead means commit is contained by Staging.
    u=f'https://api.github.com/repos/chillchill011/travellingtrails1/compare/{commit}...Staging'
    try: d=_json_url(u)
    except Exception:return False
    return d.get('status') in {'identical','ahead'}

def prepare(store:RunStore,run_id:str)->dict[str,Any]:
    r=_run(store,run_id)
    if r.get('phase6_status')!='DRAFT_CREATED': raise StateError('Phase 7 requires Phase 6 DRAFT_CREATED')
    sha=str(r.get('draft_commit_sha') or '')
    if not SHA40.fullmatch(sha): raise StateError('Phase 6 draft commit is missing or invalid')
    if r.get('phase7_status') in {'REVIEW_READY','NOTIFICATION_SENDING','NOTIFICATION_SENT'}:
      return view(store,run_id,action='NO_DEPLOY_CHECK_NEEDED',idempotent=True)
    _update(store,run_id,phase7_status='DEPLOY_WAITING',phase7_last_safe_status=None,phase7_error_message=None)
    return view(store,run_id,action='VERIFY_DEPLOY')

def verify_live_deploy(store:RunStore,run_id:str)->dict[str,Any]:
    r=_run(store,run_id); expected=str(r.get('draft_commit_sha') or '')
    if r.get('phase6_status')!='DRAFT_CREATED': raise StateError('Phase 7 requires Phase 6 DRAFT_CREATED')
    if not _commit_on_staging(expected): raise StateError('draft commit is not contained by GitHub Staging')
    site=_json_url(f'https://api.netlify.com/api/v1/sites/{STAGING_SITE_ID}')
    assert_staging_identity(STAGING_BRANCH,str(site.get('id') or ''),str(site.get('name') or ''))
    deploys=_json_url(f'https://api.netlify.com/api/v1/sites/{STAGING_SITE_ID}/deploys?per_page=30')
    match=None
    for d in deploys:
      if d.get('branch')!=STAGING_BRANCH or d.get('state')!='ready': continue
      dep_commit=str(d.get('commit_ref') or '')
      if dep_commit==expected or (SHA40.fullmatch(dep_commit) and _is_descendant(expected,dep_commit)):
        match=d; break
    if not match: return view(store,run_id,action='DEPLOY_WAITING',idempotent=False)
    generated=json.loads(r.get('generated_json') or '{}'); fm=generated.get('frontmatter') or {}
    if fm.get('draft') is not True: raise StateError('draft:true invariant violated')
    title=str(fm.get('title') or '').strip(); preview=f'{STAGING_ORIGIN}/{slugify_title(title)}/'
    if not preview.startswith(STAGING_ORIGIN+'/') or 'travellingtrails.in' in preview: raise StateError('unsafe preview URL')
    if not _http_ok(preview): raise StateError('staging preview did not return success')
    _update(store,run_id,phase7_status='DEPLOY_VERIFIED',phase7_last_safe_status='DEPLOY_VERIFIED',phase7_error_message=None,
      staging_deploy_id=match.get('id'),staging_deploy_commit=match.get('commit_ref'),staging_preview_url=preview)
    return make_review_ready(store,run_id)

def _is_descendant(base:str,head:str)->bool:
    try: d=_json_url(f'https://api.github.com/repos/chillchill011/travellingtrails1/compare/{base}...{head}')
    except Exception:return False
    return d.get('status') in {'identical','ahead'}

def make_review_ready(store,run_id,cms_safe:bool=True):
    r=_run(store,run_id); generated=json.loads(r.get('generated_json') or '{}'); fm=generated.get('frontmatter') or {}
    manifest=json.loads(r.get('processed_image_manifest_json') or '[]')
    if isinstance(manifest,dict): images=manifest.get('outputs') or manifest.get('images') or manifest.get('files') or []
    else: images=manifest
    payload={'runId':run_id,'status':'REVIEW_READY','title':fm.get('title') or '', 'destination':fm.get('destination') or '',
      'branch':STAGING_BRANCH,'commitSha':r.get('draft_commit_sha'),'postPath':r.get('post_path'),'previewUrl':r.get('staging_preview_url'),
      'cmsReviewUrl':f'{STAGING_ORIGIN}/admin/' if cms_safe else None,'imageCount':len(images) if isinstance(images,list) else 0,
      'warnings':generated.get('reviewWarnings') or [],'missingInformation':generated.get('missingInformation') or [],'published':False}
    _update(store,run_id,phase7_status='REVIEW_READY',phase7_last_safe_status='REVIEW_READY',review_url=payload['cmsReviewUrl'],review_payload_json=payload,notification_status='PENDING')
    return view(store,run_id,action='REVIEW_READY')

def mark_notification_sending(store,run_id):
    r=_run(store,run_id)
    if r.get('notification_status')=='SENT': return view(store,run_id,action='NO_NOTIFICATION_NEEDED',idempotent=True)
    if r.get('phase7_status') not in {'REVIEW_READY','NOTIFICATION_SENDING','FAILED'}: raise StateError('review payload not ready')
    _update(store,run_id,phase7_status='NOTIFICATION_SENDING',phase7_last_safe_status='REVIEW_READY',notification_status='SENDING')
    return view(store,run_id,action='SEND_NOTIFICATION')

def complete_notification(store,run_id):
    r=_run(store,run_id)
    if r.get('notification_status')=='SENT': return view(store,run_id,action='NO_NOTIFICATION_NEEDED',idempotent=True)
    _update(store,run_id,phase7_status='NOTIFICATION_SENT',phase7_last_safe_status='NOTIFICATION_SENT',notification_status='SENT',notification_sent_at=utc_now())
    return view(store,run_id,action='NOTIFICATION_SENT')

def fail(store,run_id,message):
    r=_run(store,run_id); safe=r.get('phase7_last_safe_status')
    _update(store,run_id,phase7_status='FAILED',phase7_last_safe_status=safe,phase7_error_message=message)
    return view(store,run_id,action='FAILED')

def view(store,run_id,*,action=None,idempotent=False):
    r=_run(store,run_id)
    try: payload=json.loads(r.get('review_payload_json') or 'null')
    except Exception: payload=None
    return {'ok':True,'runId':run_id,'phase7Status':r.get('phase7_status') or 'NOT_STARTED','phase7LastSafeStatus':r.get('phase7_last_safe_status'),
      'action':action,'idempotent':idempotent,'stagingSiteId':STAGING_SITE_ID,'stagingProject':STAGING_SITE_NAME,'branch':STAGING_BRANCH,
      'deployId':r.get('staging_deploy_id'),'deployCommit':r.get('staging_deploy_commit'),'previewUrl':r.get('staging_preview_url'),
      'reviewUrl':r.get('review_url'),'reviewPayload':payload,'notificationStatus':r.get('notification_status'),'notificationSentAt':r.get('notification_sent_at'),
      'errorMessage':r.get('phase7_error_message')}
