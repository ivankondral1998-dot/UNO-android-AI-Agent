"""Document arithmetic only. No UNO implementation, training, or simulation."""
import json, math, hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def tensors(d,H=902):
    b,chi,J,m,V,A=64,4,2,128,32768,128
    out=[]
    def add(name,shape,vector=False):
        out.append(dict(name=name,shape=list(shape),elements=math.prod(shape),vector=vector))
    for name,shape in [('E_text',(V,d)),('W_audio',(d,80)),('W_image',(d,768)),('W_sensor',(d,64)),('W_meta',(d,32)),('U_s',(d,d)),('U_g',(d,d)),('W_q',(m,d)),('W_k',(m,d)),('W_v',(m,d)),('W_r',(d,m))]: add(name,shape)
    add('e_modality',(6,d),True);add('b_z',(d,),True)
    for l in range(J):
        for j in range(d//b):
            for name,shape,vec in [('A',(chi*b,d),False),('C',(chi*b,d),False),('B',(b,chi*b),False),('a',(chi*b,),True),('b',(b,),True)]:add(f'F.{l}.{j}.{name}',shape,vec)
    for name,n in [('verb',A),('outcome',A),('observable',A),('ctc',128),('belief',128),('speech',258),('value',1),('risk',1),('halt',1),('conf',1)]:
        add('W_'+name,(n,d));add('b_'+name,(n,),True)
    add('b_text',(V,),True);add('W_mask',(d//b,2*d+4));add('b_mask',(d//b,),True)
    add('W_wake',(1,32));add('b_wake',(1,),True)
    return out
def align(n,a=64):return a*((n+a-1)//a)
def counts(d):
    b,chi,J,m,V,A,H=64,4,2,128,32768,128,902
    ts=tensors(d)
    P=V*d+951*d+2*d*d+4*m*d+J*(2*chi*d*d+chi*b*d+(chi+1)*d)+H*(d+1)+V+(d//b)*(2*d+5)+33
    assert sum(t['elements'] for t in ts)==P
    vec=sum(t['elements'] for t in ts if t['vector']);rows=sum(t['shape'][0] for t in ts if not t['vector'])
    B8=P+3*vec+4*rows
    packed=4096+128*len(ts)
    for t in ts:
        if t['vector']:packed+=align(4*t['elements'])
        else:
            nr,nc=t['shape'];packed+=align(nr*align(nc,16))+align(4*nr)
    R=J*(2*chi*d*d+chi*b*d)
    Rcache=J*(chi*d*d+chi*b*d)
    pre=J*chi*d*d
    enc=lambda f,M=4096:2*d*d+d*f+32*d+2*m*d+2*M*m
    mask=(d//b)*(2*d+4)
    def event(f,K=8,head=128,text=False,q=None,M=4096):
        q=d//b if q is None else q
        cr=J*q*(2*chi*b*d+chi*b*b)
        return enc(f,M)+mask+K*(cr+d)+head*d+(V*d if text else 0)+32
    text8=event(0,8,0,True)
    # Low rank alternative: A=L_A R_A,C=L_C R_C; independent factors per branch/block.
    rank=64
    oldAC=2*J*chi*d*d
    newAC=2*J*(d//b)*rank*(d+chi*b)
    lowP=P-oldAC+newAC
    lowR=J*(d//b)*(2*rank*(d+chi*b)+chi*b*b)
    # Attention hybrid: Q,K,V,O with no bias, one head, full ctx <=256.
    hybridP=P+4*d*d
    workspace=4*(12*d+2*J*chi*d+V+4*4096+2*258*1000+2*512*1000)
    state=4*A*d+4096*(4*m+64)+2*256*d+32*(4*d+256)+4096*4096+2*8192*128+1024*128+64*128+320000
    return dict(d=d,v1_parameters=P-A*(d+1),parameters=P,tensor_count=len(ts),fp16_MiB=2*P/2**20,fp32_training_MiB=16*P/2**20,mixed_training_MiB=18*P/2**20,int8_unpadded_bytes=B8,int8_ABI_bytes=packed,int8_ABI_MiB=packed/2**20,F_MAC=R,F8_MAC=8*R,cached_Cz_pre_MAC=pre,cached_inner_MAC=Rcache,cached_F8_MAC=pre+8*Rcache,vocab_MAC=V*d,text8_MAC=text8,audio8_MAC_s=100*event(80,8,128),audio1quarter_MAC_s=100*event(80,1,128,q=d//b//4),image256_full8_MAC=256*event(768,8,0),tts1000_full8_MAC=1000*event(80,8,258),state_payload_bytes=state,declared_workspace_bytes=workspace,partial_FP16_resident_MiB=(2*P+state+workspace)/2**20,lowrank64_parameters=lowP,lowrank64_F_MAC=lowR,hybrid_parameters=hybridP,hybrid_attention_MAC_per_event=4*d*d+2*256*d,train_text8_FLOP_per_event=6*text8)
def main():
    data={'scope':'Exact integer counts plus explicitly defined analytical scenarios; no model/device tests.','rows':[counts(d) for d in [512,1024,1536,2048]],'statistics':{'fixed_accuracy_n':math.ceil(math.log(40)/(2*.02**2)),'joint_comparison_n':math.ceil(2*(math.sqrt(math.log(40))+math.sqrt(math.log(10)))**2/.05**2),'zero_failures_n_p1e4':math.ceil(math.log(.05)/math.log(1-1e-4))}}
    (ROOT/'evidence/arithmetic_v2.json').write_text(json.dumps(data,indent=2))
    (ROOT/'evidence/tensor_manifest_d1024.json').write_text(json.dumps({'architecture':'UNO-B2-candidate','slow_tensors':tensors(1024),'fast_P_shape':[128,1024]},indent=2))
    src=ROOT.parent/'completion_sources_20261102'
    files=[dict(path=str(p.relative_to(src)),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in sorted(src.rglob('*')) if p.is_file()]
    (ROOT/'evidence/SOURCE_HASHES.json').write_text(json.dumps(files,indent=2))
    print(json.dumps(data,indent=2))
if __name__=='__main__':main()
