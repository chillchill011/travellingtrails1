#!/usr/bin/env node
const assert=require('assert'); const G=require('../lib/github-image');
const base={branch:'Staging',repoPath:'src/assets/images/phase-4-test-featured.jpg',content:Buffer.from('abc')};
assert.equal(G.buildImageWritePlan(base).action,'CREATE');
assert.equal(G.buildImageWritePlan({...base,existingContent:Buffer.from('abc')}).action,'ALREADY_EXISTS_SAME_CONTENT');
assert.equal(G.buildImageWritePlan({...base,existingContent:Buffer.from('different')}).action,'COLLISION_DIFFERENT_CONTENT');
assert.throws(()=>G.buildImageWritePlan({...base,branch:'main'}),/staging-only/);
for(const p of ['../bad.jpg','/src/assets/images/bad.jpg','src/assets/images/../bad.jpg','src/assets/images/Bad File.jpg','src/blog/bad.jpg']) assert.throws(()=>G.buildImageWritePlan({...base,repoPath:p}),/unsafe/);
console.log('PASS github image plan');
