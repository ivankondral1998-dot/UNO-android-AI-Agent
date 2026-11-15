"""Cluster/seed paired estimates; standard library only, no invented independent pooled sample."""
import math,random

def percentile(x,p):
    v=sorted(x);index=(len(v)-1)*p;lo=int(index);return v[lo]+(v[min(lo+1,len(v)-1)]-v[lo])*(index-lo)
def wilson(correct,n,z=1.959963984540054):
    p=correct/n;d=1+z*z/n;c=(p+z*z/(2*n))/d;r=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d
    return [c-r,c+r]
def paired(rows_a,rows_b,draws=2000,seed=20261115):
    a={r['id']:r for r in rows_a};b={r['id']:r for r in rows_b}
    if a.keys()!=b.keys():raise ValueError('UNPAIRED_DATA')
    groups={};wins=losses=0
    for key,r in a.items():
        s=b[key]
        if r['label']!=s['label']:raise ValueError('UNPAIRED_LABELS')
        delta=int(r['correct'])-int(s['correct']);groups.setdefault(r['pair'],[]).append(delta);wins+=delta>0;losses+=delta<0
    means=[sum(v)/len(v) for v in groups.values()];rng=random.Random(seed)
    boot=[sum(rng.choices(means,k=len(means)))/len(means) for _ in range(draws)]
    n=wins+losses;p=min(1.,2*sum(math.comb(n,k) for k in range(min(wins,losses)+1))/2**n) if n else 1.
    return {'n':len(a),'clusters':len(means),'delta':sum(means)/len(means),'cluster_bootstrap_ci95':[percentile(boot,.025),percentile(boot,.975)],'wins':wins,'losses':losses,'mcnemar_exact_descriptive':p,'mcnemar_limit':'does not account for clustered/reused generator seeds; primary interval is cluster bootstrap'}
def hierarchical(seed_pairs,draws=2000):
    # Each element is one training-seed's paired test records (same held-out dataset across seeds).
    if not seed_pairs:raise ValueError('NO_SEEDS')
    arrays=[]
    for a,b in seed_pairs:
        aa={r['id']:r for r in a};bb={r['id']:r for r in b}
        if aa.keys()!=bb.keys():raise ValueError('UNPAIRED_DATA')
        groups={};strata={}
        for k,r in aa.items():
            if r['label']!=bb[k]['label']:raise ValueError('UNPAIRED_LABELS')
            groups.setdefault(r['pair'],[]).append(int(r['correct'])-int(bb[k]['correct']));strata[r['pair']]=r.get('group','all')
        arrays.append({key:sum(v)/len(v) for key,v in groups.items()})
    keys=sorted(arrays[0])
    if any(sorted(v)!=keys for v in arrays):raise ValueError('UNPAIRED_SEEDS')
    rng=random.Random(260002);boot=[]
    by_stratum={}
    for key in keys:by_stratum.setdefault(strata[key],[]).append(key)
    for _ in range(draws):
        selected=rng.choices(arrays,k=len(arrays));clusters=[key for cell in by_stratum.values() for key in rng.choices(cell,k=len(cell))]
        # Same held-out cluster draw across seeds preserves shared-test dependence.
        boot.append(sum(s[k] for s in selected for k in clusters)/(len(selected)*len(clusters)))
    return {'training_seeds':len(arrays),'test_clusters':len(keys),'mean_delta':sum(sum(v.values())/len(v) for v in arrays)/len(arrays),'hierarchical_paired_ci95':[percentile(boot,.025),percentile(boot,.975)],'limit':'pointwise exploratory CI, no multiplicity correction; three training seeds are few; strata fixed by family/length; conditional on declared synthetic generator, not general language ability'}
