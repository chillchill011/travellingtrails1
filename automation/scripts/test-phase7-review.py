#!/usr/bin/env python3
import json,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'lib'))
from phase5_state import RunStore,canonical_json
import phase7_review as p7
from phase6_state import migrate as migrate_phase6

def seed(store):
  now='2026-10-08T00:00:00Z'; rid='tt-20261008-'+'a'*16
  raw={'source':'form'}; norm={'source':'form','trip':{'destination':'Test Ridge'}}
  store.create_or_verify_run(run_id=rid,source='form',post_slug='test-ridge',raw_input=raw,normalized_input=norm,fingerprint='f'*64,test_run=True)
  with store.connect() as db:
    db.execute("UPDATE runs SET status='GITHUB_IMAGES_COMPLETE', phase6_status='DRAFT_CREATED', draft_commit_sha=?, post_path=?, generated_json=?, processed_image_manifest_json=? WHERE run_id=?",
      ('1'*40,'src/blog/2026-10-08-test.md',canonical_json({'frontmatter':{'draft':True,'title':'Synthetic Phase 7 Ridge','destination':'Test Ridge'},'reviewWarnings':['check'], 'missingInformation':['cost']}),canonical_json([{'repoPath':'src/assets/images/x.jpg'}]),rid))
  return rid

def main():
  with tempfile.TemporaryDirectory() as td:
    st=RunStore(td); migrate_phase6(st); p7.migrate(st); rid=seed(st)
    for args in [('main',p7.STAGING_SITE_ID,p7.STAGING_SITE_NAME),(p7.STAGING_BRANCH,p7.PROD_SITE_ID,p7.STAGING_SITE_NAME),(p7.STAGING_BRANCH,p7.STAGING_SITE_ID,'travellingtrails1')]:
      try:p7.assert_staging_identity(*args); raise AssertionError('guard accepted unsafe target')
      except Exception:pass
    p7.assert_staging_identity(p7.STAGING_BRANCH,p7.STAGING_SITE_ID,p7.STAGING_SITE_NAME)
    assert p7.slugify_title('Synthetic Phase 7 Ridge')=='synthetic-phase-7-ridge'
    r=p7.prepare(st,rid); assert r['action']=='VERIFY_DEPLOY'
    # simulate verified deploy; review payload must remain staging-only and unpublished
    with st.connect() as db: db.execute("UPDATE runs SET phase7_status='DEPLOY_VERIFIED',phase7_last_safe_status='DEPLOY_VERIFIED',staging_preview_url=? WHERE run_id=?",(p7.STAGING_ORIGIN+'/synthetic-phase-7-ridge/',rid))
    r=p7.make_review_ready(st,rid,True); q=r['reviewPayload']; assert q['published'] is False and q['branch']=='Staging' and q['previewUrl'].startswith(p7.STAGING_ORIGIN) and 'travellingtrails.in' not in q['previewUrl']
    a=p7.mark_notification_sending(st,rid); assert a['action']=='SEND_NOTIFICATION'
    b=p7.complete_notification(st,rid); assert b['notificationStatus']=='SENT'
    c=p7.mark_notification_sending(st,rid); assert c['action']=='NO_NOTIFICATION_NEEDED' and c['idempotent']
    print('phase7 review/state tests: PASS')
if __name__=='__main__':main()
