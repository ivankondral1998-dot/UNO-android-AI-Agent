"""R5.4 errata 14–16. Research measurement only; no training or checkpoint writes."""
from collections import Counter, defaultdict
import hashlib
import math
import struct


def value_loss_floor(target, cap=2., coefficient=.2):
    """Exact-real lower bound given |state_i|<=1 and Wv row L1<=cap."""
    if not all(map(math.isfinite, (target, cap, coefficient))) or cap < 0 or coefficient < 0:
        raise ValueError('INVALID_BOUND')
    return coefficient * max(0., abs(target)-math.tanh(cap))**2


def trajectory_keys(events):
    """Binary64 numerical identity, independent of TSV formatting and signed zero.
    Noise family is a dependence proxy, not proof of independent generation.
    Compute from original input before any dtype conversion; never use teacher.
    """
    def digest(rows):
        return hashlib.sha256(b''.join(struct.pack('>ddd', *(0. if v == 0 else v for v in row)) for row in rows)).hexdigest()
    if not events or any(len(row)!=3 or not all(map(math.isfinite,row)) for row in events):
        raise ValueError('INVALID_EVENTS')
    return digest(events), digest([row for row in events if row[2]==0.])


def group_accuracy(observations):
    """Equal-family and episode-weighted accuracy, not an independence claim or CI."""
    groups=defaultdict(lambda:[0,0])
    for key,ok in observations:
        if ok not in (0,1):raise ValueError('INVALID_CORRECTNESS')
        groups[key][0]+=int(ok);groups[key][1]+=1
    if not groups:raise ValueError('EMPTY_EVALUATION')
    correct=sum(c for c,n in groups.values());n=sum(n for c,n in groups.values())
    return {'correct':correct,'n':n,'accuracy':correct/n,'noise_families':len(groups),
            'equal_family_accuracy':sum(c/n for c,n in groups.values())/len(groups),
            'max_family_size':max(n for c,n in groups.values()),
            'independence_established':False}


def wilson95(correct,n):
    """Nominal binomial interval only under independent Bernoulli sampling."""
    if type(correct) is not int or type(n) is not int or not 0<=correct<=n or n==0:
        raise ValueError('INVALID_COUNTS')
    p=correct/n;z=1.959963984540054;den=1+z*z/n
    center=(p+z*z/(2*n))/den;half=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return {'correct':correct,'n':n,'accuracy':p,'wilson95':[max(0.,center-half),min(1.,center+half)],
            'interval_assumption':'independent Bernoulli episodes; not across training seeds'}


def recover_rounded_count(acc,n):
    """Legacy 4-decimal accuracy; reject ambiguous numerator rather than invent it."""
    if not math.isfinite(acc) or not 0<=acc<=1 or type(n) is not int or n<=0:
        raise ValueError('INVALID_LEGACY_METRIC')
    lo=max(0,math.floor((acc-.00005)*n)-1);hi=min(n,math.ceil((acc+.00005)*n)+1)
    matches=[c for c in range(lo,hi+1) if round(c/n,4)==acc]
    if len(matches)!=1:raise ValueError('AMBIGUOUS_LEGACY_COUNT')
    return matches[0]


def overwrite_info(events):
    """Use observed writes only; labels must never define the hard subset."""
    if not events or events[-1][2]!=-1.:raise ValueError('INDEXED_QUERY_REQUIRED')
    slot=events[-1][1];values=[v for v,k,op in events[:-1] if op==1. and k==slot]
    if not values:raise ValueError('NO_QUERY_WRITE')
    return {'first':int(values[0]>0),'last':int(values[-1]>0),
            'overwritten':len(values)>1,'hard':len(values)>1 and (values[0]>0)!=(values[-1]>0)}


def paired_counts(rows):
    """Rows: (unique episode id, left correct, right correct, hard flag).
    Keep discordant counts; no unpaired significance claim.
    """
    counts={'all':Counter(),'hard':Counter()};seen=set()
    for ident,left,right,hard in rows:
        if ident in seen or left not in (0,1) or right not in (0,1) or type(hard) is not bool:
            raise ValueError('INVALID_PAIR')
        seen.add(ident);key=f'{int(left)}{int(right)}';counts['all'][key]+=1
        if hard:counts['hard'][key]+=1
    if not seen:raise ValueError('EMPTY_PAIRS')
    out={}
    for name,c in counts.items():
        n=sum(c.values());out[name]={'n':n,'both_correct':c['11'],'left_only':c['10'],'right_only':c['01'],
          'both_wrong':c['00'],'paired_accuracy_delta_left_minus_right':(c['10']-c['01'])/n if n else None}
    return out


def loss_components(bce, route_ce, coefficient):
    if not all(map(math.isfinite,(bce,route_ce,coefficient))) or min(bce,route_ce,coefficient)<0:
        raise ValueError('INVALID_LOSS')
    return {'answer_bce':bce,'route_ce':route_ce,'route_coefficient':coefficient,'total_loss':bce+coefficient*route_ce}


def parameter_delta(before,model):
    """Exact stored-value differences vs a caller-provided frozen snapshot.
    No optimizer call; counts final differences, not number of optimizer updates.
    """
    import torch
    named=dict(model.named_parameters())
    if named.keys()!=before.keys():raise ValueError('PARAMETER_SET_MISMATCH')
    changed=trainable=total=0;squared=0.
    for name,p in named.items():
        old=before[name];now=p.detach().cpu()
        if old.shape!=now.shape or old.dtype!=now.dtype or not bool(torch.isfinite(old).all() and torch.isfinite(now).all()):raise ValueError('PARAMETER_SNAPSHOT_MISMATCH')
        total+=p.numel();trainable+=p.numel() if p.requires_grad else 0
        changed+=int((now!=old).sum());squared+=float((now.double()-old.double()).square().sum())
    return {'total_count':total,'trainable_count':trainable,'changed_count_vs_snapshot':changed,'delta_l2':math.sqrt(squared)}


def paired_overwrite_evaluate(left,right,make_batch,*,length,seed,n,chunk,device='cpu'):
    """Read-only paired comparison on the historical generator, exact same inputs.
    Works with 005/007 models exposing sequence(x). Caller supplies frozen models.
    No use of erased data for the hard subset; no new training.
    """
    import torch
    if min(n,chunk)<=0:raise ValueError('INVALID_EVAL_SIZE')
    rng=torch.Generator().manual_seed(seed);rows=[]
    modes=(left.training,right.training)
    left.eval();right.eval()
    try:
        with torch.no_grad():
            for start in range(0,n,chunk):
                x,y=make_batch(min(chunk,n-start),length,'r4_overwrite',rng)
                l,_=left.sequence(x.to(device));r,_=right.sequence(x.to(device))
                if l.shape!=y.shape or r.shape!=y.shape or not bool(torch.isfinite(l).all() and torch.isfinite(r).all()):raise ValueError('INVALID_PREDICTIONS')
                for i,(events,target,lp,rp) in enumerate(zip(x.tolist(),y.tolist(),l.cpu().tolist(),r.cpu().tolist())):
                    info=overwrite_info(events)
                    if target!=info['last']:raise ValueError('TEACHER_MISMATCH')
                    rows.append((start+i,int((lp>=0)==bool(target)),int((rp>=0)==bool(target)),info['hard']))
    finally:
        left.train(modes[0]);right.train(modes[1])
    return {'seed':seed,'length':length,'chunk':chunk,'comparison':paired_counts(rows),
            'unit':'paired episode, fixed models; not independent training seeds'}


def split_lineage(splits):
    """Describe split lengths and exact-input/noise overlap, not causal independence."""
    from itertools import combinations
    info={};keys={}
    for name,rows in splits.items():
        if not rows:raise ValueError('EMPTY_SPLIT')
        keys[name]={k:{row[k] for row in rows} for k in ('trajectory_sha256','noise_family_sha256')}
        info[name]={'n':len(rows),'lengths':dict(Counter(len(row['x']) for row in rows)),
                    'unique_trajectories':len(keys[name]['trajectory_sha256']),
                    'noise_families':len(keys[name]['noise_family_sha256'])}
    overlap={a+'__'+b:{k:len(keys[a][k]&keys[b][k]) for k in keys[a]} for a,b in combinations(splits,2)}
    result={'splits':info,'overlap':overlap,'independence_established':False}
    if {'train','validation','test'}<=info.keys():
        lengths=set(info['test']['lengths'])-set(info['train']['lengths'])
        result['unseen_in_training_lengths']=sorted(lengths)
        result['also_used_in_validation_lengths']=sorted(lengths&set(info['validation']['lengths']))
    return result


def answer_objective(logit,y,trace,route_coefficient):
    """007 objective unchanged; return real BCE, optional CE, and total tensor."""
    import torch.nn.functional as F
    if not math.isfinite(route_coefficient) or route_coefficient<0:raise ValueError('INVALID_ROUTE_COEFFICIENT')
    bce=F.binary_cross_entropy_with_logits(logit,y)
    route=F.cross_entropy(trace['route_logits'],trace['route_target']) if trace is not None else None
    total=bce+route_coefficient*route if route is not None and route_coefficient else bce
    return bce,route,total
