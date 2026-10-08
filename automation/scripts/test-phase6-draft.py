#!/usr/bin/env python3
import copy, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'lib'))
from phase6_draft import strict_json, validate_and_assemble, Phase6Error

normalized={"trip":{"date":"2026-10-08","author":"aniket","destination":"Synthetic Ridge","duration":"1 day","rawNotes":"Synthetic test. The featured image is a blue rectangle. The gallery image is a green rectangle. The route image is a simple test route graphic.","routeNotes":"","costNotes":"","gearNotes":"","mustInclude":[]}}
processed={"outputs":[
 {"sourceId":"featured-1","role":"featured","publicPath":"/assets/images/p6-featured.jpg"},
 {"sourceId":"featured-1","role":"thumbnail","publicPath":"/assets/images/p6-thumbnail.jpg"},
 {"sourceId":"gallery-001","role":"gallery","publicPath":"/assets/images/p6-01.jpg"},
 {"sourceId":"route-001","role":"route","publicPath":"/assets/images/p6-route-01.jpg"}]}
base={"frontmatter":{"draft":True,"featured":False,"date":"2026-10-08","lastModified":"2026-10-08","title":"Synthetic Ridge Phase 6 Test","description":"A synthetic Phase 6 staging test.","author":"aniket","destination":"Synthetic Ridge","coordinates":{"latitude":None,"longitude":None},"duration":"1 day","categories":"Adventure","travelType":["Solo Bike Ride"],"rideMode":["Motorcycle"],"activities":["Photography"],"tags":["post","day-trip"],"featuredImage":"","imageAlt":"Blue synthetic test rectangle","imageCredit":"Aniket","imageCreditLink":"","thumbnailImage":"","thumbnailAlt":"Blue synthetic test rectangle","thumbnailCredit":"Aniket","gallery":[],"routeGallery":[],"tripDetails":{"itinerary":[],"costs":{},"seasonal":{},"difficulty":{},"localResources":{},"altTransportation":{}},"affiliateGallery":[],"showTableOfContents":True,"tocMinHeadings":3,"layout":"article.njk"},"bodyMarkdown":"## Synthetic departure\n\nThis is a synthetic Phase 6 test.\n\n## Synthetic destination\n\nNo real-world claims are made.\n\n## Synthetic return\n\nThe controlled test ends here.","imagePlan":[{"sourceId":"featured-1","role":"featured","alt":"Blue synthetic test rectangle","caption":"","location":""},{"sourceId":"gallery-001","role":"gallery","alt":"Green synthetic test rectangle","caption":"Synthetic gallery image","location":""},{"sourceId":"route-001","role":"route","alt":"Simple synthetic route graphic","caption":"","location":""}],"reviewWarnings":[],"missingInformation":[]}

def ok(x):
 r=validate_and_assemble(normalized,processed,x); assert r['ok'],r; return r
r1=ok(copy.deepcopy(base)); r2=ok(copy.deepcopy(base)); assert r1['markdown']==r2['markdown']; assert r1['postPath']==r2['postPath']
assert r1['frontmatter']['featuredImage']==processed['outputs'][0]['publicPath']; assert r1['frontmatter']['thumbnailImage']==processed['outputs'][1]['publicPath']
assert r1['frontmatter']['gallery'][0]['src']==processed['outputs'][2]['publicPath']; assert r1['frontmatter']['routeGallery'][0]['src']==processed['outputs'][3]['publicPath']
for mutate,needle in [
 (lambda x:x['frontmatter'].__setitem__('draft',False),'draft must be true'),
 (lambda x:x['frontmatter'].__setitem__('categories','Invented'),'categories:'),
 (lambda x:x['frontmatter'].__setitem__('featuredImage','/assets/images/not-real.jpg'),'unknown image path'),
 (lambda x:x['frontmatter'].__setitem__('featuredImage','/assets/images/p6-thumbnail.jpg'),'wrong image role/path')]:
 x=copy.deepcopy(base); mutate(x); rr=validate_and_assemble(normalized,processed,x); assert not rr['ok'] and any(needle in e for e in rr['errors']),rr
try: strict_json('```json\n{}\n```'); raise AssertionError('fence accepted')
except Phase6Error: pass
try: strict_json('{bad'); raise AssertionError('malformed accepted')
except Phase6Error: pass
assert strict_json(json.dumps(base,separators=(',',':')))['frontmatter']['draft'] is True
print('PASS phase6 draft validation/media/serialization')
print(r1['postPath'])
