const assert=require('assert'); const d=require('./write-decap-config.js');
assert.equal(d.resolveBranch({SITE_ID:d.STAGING_ID,SITE_NAME:'devtravtes'}),'Staging');
assert.equal(d.resolveBranch({SITE_ID:d.PROD_ID,SITE_NAME:'travellingtrails1'}),'main');
assert.throws(()=>d.resolveBranch({NETLIFY:'true',SITE_ID:'wrong'}));
assert.throws(()=>d.resolveBranch({SITE_ID:d.PROD_ID,SITE_NAME:'devtravtes'}));
assert.match(d.render('backend:\n  branch: main\n','Staging'),/branch: Staging/);
console.log('decap branch isolation tests: PASS');
