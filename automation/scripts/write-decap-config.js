#!/usr/bin/env node
const fs=require('fs');
const src='src/admin/config.yml', out='public/admin/config.yml';
const STAGING_ID='bb8c325b-9562-4952-8613-439ca95dc9e0', PROD_ID='edd2477f-24f5-4005-a05c-f0310f1efe11';
function resolveBranch(env=process.env){
  const id=env.SITE_ID||env.NETLIFY_SITE_ID||'';
  const name=env.SITE_NAME||'';
  if(id===STAGING_ID || name==='devtravtes') {
    if(id && id!==STAGING_ID) throw new Error('Decap staging identity mismatch');
    return 'Staging';
  }
  if(id===PROD_ID || name==='travellingtrails1') {
    if(id && id!==PROD_ID) throw new Error('Decap production identity mismatch');
    return 'main';
  }
  if(env.NETLIFY==='true') throw new Error('Unknown Netlify site identity; refusing Decap branch generation');
  return env.TT_DECAP_TARGET_BRANCH==='Staging' ? 'Staging' : 'main';
}
function render(text,branch){return text.replace(/(^\s*branch:\s*)([^#\n]+)(.*$)/m,`$1${branch} # generated safely for this deployment$3`)}
if(require.main===module){const branch=resolveBranch(); const text=fs.readFileSync(src,'utf8'); fs.mkdirSync('public/admin',{recursive:true}); fs.writeFileSync(out,render(text,branch)); console.log(`Decap config target branch: ${branch}`)}
module.exports={resolveBranch,render,STAGING_ID,PROD_ID};
