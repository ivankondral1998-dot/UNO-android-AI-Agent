import csv, hashlib, io, json, math, sys, zipfile
from pathlib import Path
with zipfile.ZipFile(sys.argv[1]) as archive:
    assert archive.testzip() is None
    prefix='03_CANONICAL_ASTRA_R53/ORIGINAL_SOURCE_PACKAGE/'
    imports=json.loads(archive.read('03_CANONICAL_ASTRA_R53/REPO_META/docs/precode/r5.3/SOURCE_PACKAGE_IMPORT_MANIFEST.json'))['files']
    original=json.loads(archive.read(prefix+'SHA256_MANIFEST.json'))['files']
    assert len(imports)==64 and len(original)==63
    for row in imports:
        b=archive.read(prefix+row['repo_path'].split('/source-package/',1)[1])
        assert len(b)==row['bytes']
        assert hashlib.sha256(b).hexdigest()==row['sha256']
        assert hashlib.sha1(f'blob {len(b)}\0'.encode()+b).hexdigest()==row['git_blob_sha1']
    for row in original:
        b=archive.read(prefix+row['path'])
        assert len(b)==row['bytes'] and hashlib.sha256(b).hexdigest()==row['sha256']
    r3=archive.read('02_R3_CURRENT_CANDIDATE/UNO_UNOVYRA_FRAMEWORK_R3_ASTRA_COMPATIBLE.md')
    assert hashlib.sha256(r3).hexdigest()=='fe9627eb57facf74c77f8241aada4f282c377bc4fc86dee156ee3347566b64b4'
    evidence=json.loads(archive.read(prefix+'SOURCES/ASTRA_SUPPORT/evidence/arithmetic_v2.json'))
print('SOURCE_SHA_MATCH: 64 import entries and 63 original entries; R3 SHA match')
def calculate(d,V=32768,b=64,J=2,m=128,r=0):
    n=d//b
    matrices=[(V,d)]+[(d,f) for f in (80,768,64,32,d,d)]+[(m,d)]*3+[(d,m)]
    vectors=[6*d,d]
    for _ in range(J*n):
        matrices+=([(4*b,r),(r,d)]*2 if r else [(4*b,d)]*2)+[(b,4*b)]
        vectors += [4*b,b]
    heads=[128]*5+[258]+[1]*4
    matrices += [(h,d) for h in heads]+[(n,2*d+4),(1,32)]
    vectors += heads+[V,n,1]
    P=sum(a*b for a,b in matrices)+sum(vectors)
    align=lambda x,k: ((x+k-1)//k)*k
    packed=4096+128*(len(matrices)+len(vectors))+sum(align(4*v,64) for v in vectors)+sum(align(a*align(c,16),64)+align(4*a,64) for a,c in matrices)
    F=J*n*(2*(r*(d+4*b) if r else 4*b*d)+4*b*b)
    def event(f,H):
        return 2*d*d+d*(f+32)+2*m*d+8192*m+n*(2*d+4)+8*(F+d)+H*d+32
    return dict(d=d,V=V,b=b,J=J,m=m,rank=r,tensor_count=len(matrices)+len(vectors),parameters=P,free_slow_parameters=P-318*(d+1),frozen=318*(d+1),fast_active=21*d,fp16=2*P,int8_unpadded_bytes=P+3*sum(vectors)+4*sum(a for a,_ in matrices),int8_ABI_bytes=packed,F_MAC=F,text8_MAC=event(0,V),audio8_MAC_s=100*event(80,128),image256_full8_MAC=256*event(768,0),tts1000_full8_MAC=1000*event(80,258))
results=[]
for expected in evidence['rows']:
    row=calculate(expected['d'])
    for key in ('tensor_count','parameters','free_slow_parameters','int8_unpadded_bytes','int8_ABI_bytes','F_MAC','text8_MAC','audio8_MAC_s','image256_full8_MAC','tts1000_full8_MAC'):
        assert row[key]==expected[key], (row['d'], key)
    results.append(row)
results += [calculate(384,16384,64,1,64),calculate(256,8192,32,1,64),calculate(256,8192,32,1,64,32)]
assert [x['parameters'] for x in results[-3:]]==[8698053,3339727,3012047]
for delta, expected in [(0,9457),(.02,26268)]:
    assert math.ceil(2*(math.sqrt(math.log(40))+math.sqrt(math.log(10)))**2/(.05-delta)**2)==expected
print('ARITHMETIC_PASS: four dense B2 rows, three compact rows, E6 both thresholds')
print(json.dumps(results,indent=2))
