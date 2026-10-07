"use strict";
const crypto=require('crypto');
function sha256(v){return crypto.createHash('sha256').update(String(v),'utf8').digest('hex');}
function assertStagingDraft({branch,postPath,markdown}){
  if(branch!=='Staging') throw new Error('Phase 2 is staging-only');
  if(!/^src\/blog\/\d{4}-\d{2}-\d{2}-[a-z0-9-]+\.md$/.test(String(postPath||''))) throw new Error('unsafe or invalid postPath');
  const text=String(markdown||'');
  if(!text.startsWith('---\n')) throw new Error('markdown must start with front matter');
  if(!/^draft:\s*true\s*$/m.test(text)) throw new Error('draft:true required');
  if(/^draft:\s*false\s*$/m.test(text)) throw new Error('draft:false forbidden');
  return true;
}
function buildDraftWritePlan({runId,branch='Staging',postPath,markdown,existingContent=null}){
  assertStagingDraft({branch,postPath,markdown});
  const desiredSha256=sha256(markdown);
  let action='CREATE';
  if(existingContent!==null && existingContent!==undefined){
    action=sha256(existingContent)===desiredSha256?'ALREADY_CREATED_SAME_CONTENT':'COLLISION_DIFFERENT_CONTENT';
  }
  return {runId:String(runId||''),branch,postPath,desiredSha256,action,commitMessage:`Create draft post: ${postPath.split('/').pop().replace(/\.md$/,'')}`};
}
module.exports={sha256,assertStagingDraft,buildDraftWritePlan};
