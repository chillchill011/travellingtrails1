#!/usr/bin/env python3
import sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'lib'))
from phase5_state import RunStore
from phase6_state import migrate,prepare,persist_generated,persist_validation,mark_writing,fail,complete,view

with tempfile.TemporaryDirectory() as td:
    s=RunStore(td); migrate(s)
    rid='tt-20261008-aaaaaaaaaaaaaaaa'
    s.create_or_verify_run(run_id=rid,source='manual',post_slug='x',raw_input={'x':1},normalized_input={'trip':{'date':'2026-10-08','author':'aniket'}},fingerprint='f'*64,test_run=True)
    with s.connect() as db:
        db.execute("update runs set status='GITHUB_IMAGES_COMPLETE',last_safe_status='GITHUB_IMAGES_COMPLETE',git_commit_sha=? where run_id=?",('1'*40,rid))

    assert prepare(s,rid)['action']=='CALL_DEEPSEEK'
    g={'frontmatter':{},'bodyMarkdown':'x','imagePlan':[],'reviewWarnings':[],'missingInformation':[]}
    persist_generated(s,rid,g)
    assert view(s,rid)['deepseekCallCount']==1
    assert prepare(s,rid)['action']=='VALIDATE_PERSISTED'

    # Invalid model output remains durable evidence but is not a safe reusable generation.
    persist_validation(s,rid,{'errors':['synthetic invalid generation']})
    bad=view(s,rid)
    assert bad['phase6Status']=='FAILED'
    assert bad['phase6LastSafeStatus'] is None
    assert bad['validationErrors']==['synthetic invalid generation']
    assert prepare(s,rid)['action']=='CALL_DEEPSEEK'

    # A regenerated valid result becomes durable and validates to exact retry bytes.
    persist_generated(s,rid,g)
    assert view(s,rid)['deepseekCallCount']==2
    persist_validation(s,rid,{'errors':[],'postPath':'src/blog/2026-10-08-x.md','markdown':'---\ndraft: true\n---\n\nx\n'})
    assert prepare(s,rid)['action']=='WRITE_DRAFT'
    mark_writing(s,rid)
    fail(s,rid,'synthetic downstream failure')
    resumed=prepare(s,rid)
    assert resumed['action']=='WRITE_DRAFT'
    assert resumed['deepseekCallCount']==2

    mark_writing(s,rid)
    complete(s,rid,{'branch':'Staging','action':'CREATE','commitSha':'2'*40})
    v=prepare(s,rid)
    assert v['action']=='NO_DRAFT_WRITE_NEEDED' and v['idempotent']
    assert v['deepseekCallCount']==2
    assert v['postPath']=='src/blog/2026-10-08-x.md' and v['draftCommitSha']=='2'*40
    print('PASS phase6 durable state/recovery/idempotency')
