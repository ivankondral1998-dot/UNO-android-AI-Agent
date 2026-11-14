import hashlib,json,math
from pathlib import Path
root=Path(__file__).resolve().parent
manifest=json.loads((root/'SHA256_MANIFEST.json').read_text())
for name,expected in manifest.items():
 p=root/name
 assert p.is_file(),name
 assert hashlib.sha256(p.read_bytes()).hexdigest()==expected,name
print('SELF_MANIFEST_PASS',len(manifest))
# Enumerate the actual distribution, not a simulation.
for p in [0.1,0.25,0.5,0.8]:
 biased=sum(prob*(-a)*(a-p) for a,prob in [(0,1-p),(1,p)])
 assert math.isclose(biased,-p*(1-p),abs_tol=1e-14)
 corrected=sum(prob*(-0.37)*(a-p) for a,prob in [(0,1-p),(1,p)])
 assert abs(corrected)<1e-14
print('BASELINE_COUNTEREXAMPLE_PASS 4 distributions')
# Finite differences of projected-free scalar logistic gradient.
for w in [-3.,-0.2,0.,2.]:
 for y in [0.,1.]:
  f=lambda v:math.log1p(math.exp(v))-y*v
  numerical=(f(w+1e-5)-f(w-1e-5))/(2e-5)
  analytical=1/(1+math.exp(-w))-y
  assert abs(numerical-analytical)<1e-9
print('LOGISTIC_GRADIENT_PASS 8 cases')
s=(root/'UNO_INTEGRATED_NEURAL_ORGANISM_PRECODE_CANDIDATE_vNEXT.md').read_text()
assert 'β_e' not in s and '+= β ' not in s
assert 'b_t(H_t)' in s and 'upstream_z' in s
print('DOCUMENT_CONSISTENCY_PASS')
