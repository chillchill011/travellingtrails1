"use strict";
const crypto=require('crypto');
const SAFE=/^src\/assets\/images\/[a-z0-9]+(?:-[a-z0-9]+)*\.jpg$/;
function sha256(v){return crypto.createHash('sha256').update(Buffer.isBuffer(v)?v:Buffer.from(v)).digest('hex');}
function assertStagingImage({branch,repoPath}){
  if(branch!=='Staging') throw new Error('Phase 4 is staging-only');
  const p=String(repoPath||'');
  if(p.startsWith('/')||p.includes('..')||p.includes('\\')||!SAFE.test(p)) throw new Error('unsafe image repoPath');
  return true;
}
function buildImageWritePlan({branch='Staging',repoPath,content,existingContent=null}){
  assertStagingImage({branch,repoPath});
  const desiredSha256=sha256(content);
  let action='CREATE';
  if(existingContent!==null&&existingContent!==undefined){
    action=sha256(existingContent)===desiredSha256?'ALREADY_EXISTS_SAME_CONTENT':'COLLISION_DIFFERENT_CONTENT';
  }
  return {branch,repoPath,desiredSha256,action};
}
module.exports={sha256,assertStagingImage,buildImageWritePlan};
