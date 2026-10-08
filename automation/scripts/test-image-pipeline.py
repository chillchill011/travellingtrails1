#!/usr/bin/env python3
import json, tempfile
from pathlib import Path
from PIL import Image
import sys
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'lib'))
import image_pipeline as I

def make(path, size, color): Image.new('RGB', size, color).save(path, 'JPEG', quality=90)

with tempfile.TemporaryDirectory() as td:
    td=Path(td); src=td/'src'; out=td/'out'; src.mkdir()
    make(src/'featured.JPG',(2400,1200),'red'); make(src/'gallery.jpeg',(1200,1800),'green'); make(src/'route.jpg',(600,1200),'blue'); make(src/'small.jpg',(120,80),'white')
    assert I.sanitize_slug(' Café / My Trip! ')=='cafe-my-trip'
    assert I.normalize_extension('image/jpeg')=='.jpg'
    try: I.validate_repo_path('src/assets/images/../bad.jpg'); raise AssertionError('traversal accepted')
    except ValueError: pass
    assert I.orientation(3,2)=='landscape' and I.orientation(2,3)=='portrait' and I.orientation(2,2)=='square'
    s=I.inspect_source(src/'featured.JPG','f','Original.JPG','featured'); assert (s['width'],s['height'])==(2400,1200)
    manifest=I.build_manifest('tt-phase4-test','Phase 4 Integration Test',[
      {'sourceId':'f','sourcePath':str(src/'featured.JPG'),'sourceFilename':'unsafe ORIGINAL name.JPG','role':'featured'},
      {'sourceId':'g','sourcePath':str(src/'gallery.jpeg'),'sourceFilename':'gallery.jpeg','role':'gallery'},
      {'sourceId':'r','sourcePath':str(src/'route.jpg'),'sourceFilename':'route.jpg','role':'route'}],out)
    assert [o['filename'] for o in manifest['outputs']]==['phase-4-integration-test-featured.jpg','phase-4-integration-test-thumbnail.jpg','phase-4-integration-test-01.jpg','phase-4-integration-test-route-01.jpg']
    assert all(o['repoPath']=='src/assets/images/'+o['filename'] for o in manifest['outputs'])
    assert all(o['publicPath']=='/assets/images/'+o['filename'] for o in manifest['outputs'])
    I.process_manifest(manifest)
    dims={o['role']:(o['width'],o['height']) for o in manifest['outputs']}
    assert dims['featured']==(1600,800)
    assert dims['thumbnail']==(400,267)
    assert dims['gallery']==(800,533)
    assert dims['route']==(600,1200), dims
    small=td/'small-out.jpg'; d=I.process_derivative(src/'small.jpg',small,'thumbnail'); assert d['width']<=120 and d['height']<=80
    assert all(o['status']=='PROCESSED' and o['sha256'] for o in manifest['outputs'])
    try:
      I.build_manifest('x','same',[{'sourceId':'1','sourcePath':str(src/'small.jpg'),'role':'featured'},{'sourceId':'2','sourcePath':str(src/'small.jpg'),'role':'featured'}],out)
      raise AssertionError('duplicate output path accepted')
    except ValueError as e: assert 'duplicate' in str(e)
    print('PASS image pipeline')
    print(json.dumps(I.public_manifest(manifest),indent=2))
