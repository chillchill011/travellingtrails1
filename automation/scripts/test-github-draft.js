#!/usr/bin/env node
const assert=require('assert');
const G=require('../lib/github-draft');
const md='---\ndraft: true\nfeatured: false\ntitle: "Phase 2 Test"\nlayout: "article.njk"\n---\n\nTest body.\n';
const base={runId:'tt-phase2-test',branch:'Staging',postPath:'src/blog/2026-10-08-phase-2-test.md',markdown:md};
assert.equal(G.buildDraftWritePlan(base).action,'CREATE');
assert.equal(G.buildDraftWritePlan({...base,existingContent:md}).action,'ALREADY_CREATED_SAME_CONTENT');
assert.equal(G.buildDraftWritePlan({...base,existingContent:md+'changed'}).action,'COLLISION_DIFFERENT_CONTENT');
assert.throws(()=>G.buildDraftWritePlan({...base,branch:'main'}),/staging-only/);
assert.throws(()=>G.buildDraftWritePlan({...base,postPath:'../bad.md'}),/invalid postPath/);
assert.throws(()=>G.buildDraftWritePlan({...base,markdown:md.replace('draft: true','draft: false')}),/draft:true required|draft:false forbidden/);
console.log('PASS github draft plan');
