#!/usr/bin/env python3
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
w=json.loads((ROOT/'n8n/phase6-full-staging-draft-workflow.json').read_text())[0]
assert w['id']=='TTPhase6FullDraft01'
assert w['name']=='Travelling Trails - Phase 6 Full Staging Draft'
assert w['active'] is True
assert any(n['type']=='n8n-nodes-base.executeWorkflowTrigger' for n in w['nodes'])
assert not any('webhook' in n['type'].lower() or 'formtrigger' in n['type'].lower() for n in w['nodes'])
nodes={n['name']:n for n in w['nodes']}
assert nodes['Phase 2 - Staging Draft Write']['parameters']['workflowId']['value']=='TTPhase2GitHubDraft01'
assert nodes['Phase 2 - Staging Draft Write'].get('onError')=='continueRegularOutput'
assert nodes['DeepSeek - Generate Structured Draft']['credentials']['deepSeekApi']['name']=='DeepSeek - Travelling Trails'
code=nodes['Code - Prepare DeepSeek Request']['parameters']['jsCode']
assert "model:'deepseek-flash'" in code
assert 'TRIP_INPUT=' in code and 'MEDIA_MANIFEST=' in code and 'BLOG_SCHEMA=' in code
assert 'contentBase64' not in code and 'source_image_manifest' not in code
assert 'Keep every frontmatter image path empty' in code
assert 'REQUIRED_SHAPE=' in code
assert 'TT_PHASE6_INJECT_FAIL_AFTER_VALIDATION' in nodes['IF - Inject Downstream Failure']['parameters']['conditions']['conditions'][0]['leftValue']
assert nodes['GitHub - Resolve Draft Commit']['credentials']['githubApi']['name']=='GitHub - Travelling Trails'
assert w['meta']['stagingOnly'] is True
assert w['meta']['phase2WorkflowId']=='TTPhase2GitHubDraft01'
print('PASS phase6 workflow contract')
