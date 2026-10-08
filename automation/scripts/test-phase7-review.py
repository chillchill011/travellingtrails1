#!/usr/bin/env python3
import json,sys,tempfile
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'lib'))
from phase5_state import RunStore,StateError,canonical_json
from phase6_state import migrate as migrate_phase6
import phase7_review as p7

def seed(store,suffix='a'):
  rid='tt-20261008-'+suffix*16
  store.create_or_verify_run(run_id=rid,source='form',post_slug='test-ridge',raw_input={'source':'form'},normalized_input={'source':'form','trip':{'destination':'Test Ridge'}},fingerprint=suffix*64,test_run=True)
  with store.connect() as db:
    db.execute("UPDATE runs SET status='GITHUB_IMAGES_COMPLETE',phase6_status='DRAFT_CREATED',draft_commit_sha=?,post_path=?,generated_json=?,processed_image_manifest_json=? WHERE run_id=?",('1'*40,'src/blog/2026-10-08-test.md',canonical_json({'frontmatter':{'draft':True,'title':'Synthetic Phase 7 Ridge','destination':'Test Ridge'},'reviewWarnings':['check'],'missingInformation':['cost']}),canonical_json({'outputs':[{'repoPath':'src/assets/images/x.jpg'}]}),rid))
  return rid

def fresh(suffix='a'):
  td=tempfile.TemporaryDirectory(); st=RunStore(td.name); migrate_phase6(st); p7.migrate(st); return td,st,seed(st,suffix)

def correct_site(): return {'id':p7.STAGING_SITE_ID,'name':p7.STAGING_SITE_NAME}
def ready(commit='1'*40,branch='Staging',state='ready'): return [{'id':'deploy-1','branch':branch,'state':state,'commit_ref':commit}]

def main():
  # Environment identity guard.
  for args in [('main',p7.STAGING_SITE_ID,p7.STAGING_SITE_NAME),(p7.STAGING_BRANCH,p7.PROD_SITE_ID,p7.STAGING_SITE_NAME),(p7.STAGING_BRANCH,p7.STAGING_SITE_ID,'travellingtrails1')]:
    try:p7.assert_staging_identity(*args); raise AssertionError('guard accepted unsafe target')
    except StateError: pass
  p7.assert_staging_identity(p7.STAGING_BRANCH,p7.STAGING_SITE_ID,p7.STAGING_SITE_NAME)
  assert p7.slugify_title('Synthetic Phase 7 Ridge')=='synthetic-phase-7-ridge'

  # Matching commit + ready deployment succeeds and yields staging-only review payload.
  td,st,rid=fresh('a')
  try:
    assert p7.prepare(st,rid)['action']=='VERIFY_DEPLOY'
    with patch.object(p7,'_commit_on_staging',return_value=True), patch.object(p7,'_json_url',side_effect=[correct_site(),ready()]), patch.object(p7,'_http_ok',return_value=True):
      r=p7.verify_live_deploy(st,rid)
    q=r['reviewPayload']; assert r['action']=='REVIEW_READY' and q['published'] is False and q['branch']=='Staging' and q['imageCount']==1
    assert q['previewUrl'].startswith(p7.STAGING_ORIGIN+'/') and 'travellingtrails.in' not in q['previewUrl']
    a=p7.mark_notification_sending(st,rid); assert a['action']=='SEND_NOTIFICATION'
    b=p7.complete_notification(st,rid); assert b['notificationStatus']=='SENT'
    c=p7.mark_notification_sending(st,rid); assert c['action']=='NO_NOTIFICATION_NEEDED' and c['idempotent']
  finally: td.cleanup()

  # Wrong site identity is rejected.
  td,st,rid=fresh('b')
  try:
    p7.prepare(st,rid)
    with patch.object(p7,'_commit_on_staging',return_value=True), patch.object(p7,'_json_url',return_value={'id':p7.PROD_SITE_ID,'name':'travellingtrails1'}):
      try:p7.verify_live_deploy(st,rid); raise AssertionError('wrong site accepted')
      except StateError: pass
  finally: td.cleanup()

  # Wrong branch and failed deployment remain retryable DEPLOY_WAITING.
  for suffix,deploys in [('c',ready(branch='main')),('d',ready(state='error'))]:
    td,st,rid=fresh(suffix)
    try:
      p7.prepare(st,rid)
      with patch.object(p7,'_commit_on_staging',return_value=True), patch.object(p7,'_json_url',side_effect=[correct_site(),deploys]):
        r=p7.verify_live_deploy(st,rid)
      assert r['action']=='DEPLOY_WAITING' and r['phase7Status']=='DEPLOY_WAITING'
    finally: td.cleanup()

  # Descendant deploy is accepted only when containment check proves it.
  td,st,rid=fresh('e')
  try:
    p7.prepare(st,rid)
    descendant='2'*40
    with patch.object(p7,'_commit_on_staging',return_value=True), patch.object(p7,'_is_descendant',return_value=True), patch.object(p7,'_json_url',side_effect=[correct_site(),ready(descendant)]), patch.object(p7,'_http_ok',return_value=True):
      assert p7.verify_live_deploy(st,rid)['action']=='REVIEW_READY'
  finally: td.cleanup()

  # Timeout leaves durable waiting state; a retry can then succeed.
  td,st,rid=fresh('f')
  try:
    p7.prepare(st,rid)
    with patch.object(p7,'_commit_on_staging',return_value=True), patch.object(p7,'_json_url',side_effect=TimeoutError('synthetic timeout')):
      try:p7.verify_live_deploy(st,rid); raise AssertionError('timeout did not surface')
      except TimeoutError: pass
    assert p7.view(st,rid)['phase7Status']=='DEPLOY_WAITING'
    with patch.object(p7,'_commit_on_staging',return_value=True), patch.object(p7,'_json_url',side_effect=[correct_site(),ready()]), patch.object(p7,'_http_ok',return_value=True):
      assert p7.verify_live_deploy(st,rid)['action']=='REVIEW_READY'
  finally: td.cleanup()

  print('phase7 review/deploy/state/idempotency tests: PASS')
if __name__=='__main__': main()
