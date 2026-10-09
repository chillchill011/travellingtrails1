#!/usr/bin/env python3
import json, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'lib'))
from phase5_state import RunStore, StateError
import phase8_promotion as p8
from phase6_state import migrate as migrate6
from phase7_review import migrate as migrate7

def make_store(root, post_path='src/blog/2026-10-09-reviewed-trip.md'):
    s=RunStore(root)
    r,_=s.create_or_verify_run(run_id='tt-20261009-0123456789abcdef',source='form',post_slug='reviewed-trip',raw_input={'x':1},normalized_input={'trip':{'date':'2026-10-09','author':'aniket'}},fingerprint='f'*64)
    migrate6(s); migrate7(s); p8.migrate(s)
    with s.connect() as db:
        db.execute("UPDATE runs SET status='GITHUB_IMAGES_COMPLETE',post_path=?,phase6_status='DRAFT_CREATED',phase7_status='REVIEW_READY' WHERE run_id=?",(post_path,r['run_id']))
    return s,r['run_id']

def main():
  with tempfile.TemporaryDirectory() as td:
    s,rid=make_store(td)
    post=b'''---\ndraft: true\ntitle: "Reviewed Trip"\nfeaturedImage: "/assets/images/reviewed-featured.jpg"\n---\n\n## One\nText\n'''
    media=b'jpeg-bytes'
    src='a'*40; mainsha='b'*40; postsha='c'*40; mediasha='d'*40
    p8._ref=lambda branch: src if branch=='Staging' else mainsha
    def content(path,ref):
      if ref==src and path.endswith('.md'): return {'sha':postsha,'content':__import__('base64').b64encode(post).decode()}
      if ref==src and path.endswith('reviewed-featured.jpg'): return {'sha':mediasha,'content':__import__('base64').b64encode(media).decode()}
      if ref==mainsha: return None
      raise AssertionError((path,ref))
    p8._content=content
    try: p8.approve_and_capture(s,rid,False,'Reviewed Trip'); raise AssertionError('approval gate failed')
    except StateError as e: assert 'approved=true' in str(e)
    out=p8.approve_and_capture(s,rid,True,'Reviewed Trip')
    m=out['promotionManifest']
    assert m['sourceBranch']=='Staging' and m['targetBranch']=='main' and m['draft'] is True
    assert m['postBlobSha']==postsha and m['media'][0]['blobSha']==mediasha
    assert m['creates']==['src/blog/2026-10-09-reviewed-trip.md','src/assets/images/reviewed-featured.jpg']
    out2=p8.approve_and_capture(s,rid,True,'Reviewed Trip'); assert out2['idempotent'] is True
    pr=p8.mark_promoting(s,rid); assert pr['action']=='PROMOTE'
    done=p8.complete_promotion(s,rid,'e'*40); assert done['promotionCommitSha']=='e'*40
    done2=p8.complete_promotion(s,rid,'e'*40); assert done2['idempotent'] is True

  with tempfile.TemporaryDirectory() as td:
    s,rid=make_store(td)
    bad=post.replace(b'draft: true',b'draft: false')
    p8._ref=lambda branch: src if branch=='Staging' else mainsha
    p8._content=lambda path,ref: {'sha':postsha,'content':__import__('base64').b64encode(bad).decode()} if ref==src and path.endswith('.md') else None
    try: p8.approve_and_capture(s,rid,True,'Reviewed Trip'); raise AssertionError('draft:false accepted')
    except StateError as e: assert 'draft:true' in str(e)

  with tempfile.TemporaryDirectory() as td:
    s,rid=make_store(td)
    p8._ref=lambda branch: src if branch=='Staging' else mainsha
    def collision(path,ref):
      if ref==src and path.endswith('.md'): return {'sha':postsha,'content':__import__('base64').b64encode(post).decode()}
      if ref==src: return {'sha':mediasha,'content':__import__('base64').b64encode(media).decode()}
      if ref==mainsha and path.endswith('.md'): return {'sha':'f'*40,'content':__import__('base64').b64encode(b'different').decode()}
      return None
    p8._content=collision
    try: p8.approve_and_capture(s,rid,True,'Reviewed Trip'); raise AssertionError('collision accepted')
    except StateError as e: assert 'HARD_COLLISION' in str(e)

  # Workflow contracts
  p2=json.load(open(ROOT/'n8n/phase2-staging-draft-write-workflow.json'))[0]
  p4=json.load(open(ROOT/'n8n/phase4-staging-image-upload-workflow.json'))[0]
  p5=json.load(open(ROOT/'n8n/phase5-ingestion-run-state-workflow.json'))[0]
  p6=json.load(open(ROOT/'n8n/phase6-full-staging-draft-workflow.json'))[0]
  p7=json.load(open(ROOT/'n8n/phase7-staging-review-handoff-workflow.json'))[0]
  p8wf=json.load(open(ROOT/'n8n/phase8-production-promotion-workflow.json'))[0]
  watch=json.load(open(ROOT/'n8n/phase8-publication-watch-workflow.json'))[0]
  for wf in (p2,p4,p6,p7):
    assert wf['active'] is True
    assert any(n['type']=='n8n-nodes-base.executeWorkflowTrigger' for n in wf['nodes'])
    assert not any('webhook' in n['type'].lower() or 'formtrigger' in n['type'].lower() for n in wf['nodes'])
  assert 'Phase 6 - Full Staging Draft' in p5['connections'] and 'Phase 7 - Staging Review Handoff' in p5['connections']
  form=next(n for n in p8wf['nodes'] if n['name']=='Form - Explicit Promotion Approval')
  assert form['parameters']['authentication']=='n8nUserAuth' and form['parameters']['requireExecuteAccess'] is True
  fields=form['parameters']['formFields']['values']; assert fields[0]['fieldType']=='hiddenField' and fields[1]['fieldType']=='hiddenField'
  assert p8wf['meta']['preservesDraftTrue'] is True
  assert any(n['type']=='n8n-nodes-base.scheduleTrigger' for n in watch['nodes'])
  assert not any('github' in n['type'].lower() or 'api.github.com' in str(n.get('parameters',{})).lower() for n in watch['nodes'])
  print('PASS phase8 promotion/orchestration contract')

if __name__=='__main__': main()
