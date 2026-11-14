package org.unovyra.n007;

import java.io.*;
import java.security.MessageDigest;
import java.util.*;

/**
 * UNO-N0-07 ISOLATED RESEARCH fixture. One state, one shared block-recurrent F,
 * provenance-aware memory, two supervised heads, mock-only outcome P.
 * NOT production R5.3; not an Android action executor or a proven organism.
 */
public final class TinyOrganism {
    public static final int D=16, BLOCK=4, NB=4, J=2, EXP=2, H=BLOCK*EXP;
    public static final int K=2, ACTIVE=2, INPUT=11, LABELS=3, INTENTS=2, MEMORY_CAP=96;
    public static final String[] CLASS_NAMES={"STILL","MOVE","JOLT"};
    private static final int MAGIC=0x554E3037, VERSION=1;
    private static final double ALPHA=.5, LR=.035, INTENT_LR=.06;
    private final double[][] encoder=new double[D][INPUT], us=new double[D][D];
    private final double[][][][] a=new double[NB][J][H][D], c=new double[NB][J][H][D];
    private final double[][][][] b=new double[NB][J][BLOCK][H];
    private final double[][][] aa=new double[NB][J][H], bb=new double[NB][J][BLOCK];
    private final double[][] sensory=new double[LABELS][D], intent=new double[INTENTS][D];
    private final double[] sensoryBias=new double[LABELS], intentBias=new double[INTENTS];
    private final double[] state=new double[D], plastic=new double[D];
    private final ArrayDeque<MemoryRecord> ledger=new ArrayDeque<>();
    private long serial=0, ownerTeachCount=0, sensoryLearningCount=0, checkedOutcomes=0;
    private long stopEpoch=0,lastAcceptedMockOperation=0;
    private boolean stopLatched=false;
    private transient Forward last;
    private transient Forward lastForOwner;
    private transient int lastExec=0, lastSkip=0;

    public static final class Context {
        public final int mode,older,previous;
        public Context(int mode,int older,int previous){
            if(mode<0||mode>1||older<0||older>2||previous<0||previous>2)throw new IllegalArgumentException("bad context");
            this.mode=mode;this.older=older;this.previous=previous;
        }
        public String toString(){return "mode="+mode+", older="+CLASS_NAMES[older]+", prev="+CLASS_NAMES[previous];}
    }
    public static final class Prediction {
        public final int label, intentLabel, computedBlocks, skippedBlocks;
        public final double[] sensoryProb, intentProb;
        public final long eventId;
        private Prediction(int l,int i,int ex,int skip,double[] s,double[] in,long ev){label=l;intentLabel=i;computedBlocks=ex;skippedBlocks=skip;sensoryProb=s;intentProb=in;eventId=ev;}
    }
    public static final class MemoryRecord {
        public final long id;public final String source;public final int mode,older,previous,label;public final String note;
        private MemoryRecord(long id,String source,int mode,int older,int previous,int label,String note){this.id=id;this.source=source;this.mode=mode;this.older=older;this.previous=previous;this.label=label;this.note=note;}
    }
    public enum ExactStatus {COMPLETE, TRUNCATED, UNKNOWN}
    public static final class ExactResult {
        public final ExactStatus status;public final MemoryRecord record;
        private ExactResult(ExactStatus s,MemoryRecord r){status=s;record=r;}
    }
    private static final class StepCache {
        final double[] input=new double[D],output=new double[D];
        final boolean[] on=new boolean[NB];
        final double[][][] hidden=new double[NB][J][H], branch=new double[NB][J][BLOCK];
    }
    private static final class Forward {
        Context context;double[] feat,z,sIn,hFinal,sensorProb,intentProb;StepCache[] steps=new StepCache[K];
    }
    /** MOCK ONLY. Caller provides a simulated trusted native ticket/receipt, never available from model memory. */
    public static final class MockTicket {
        public final long epoch,operation,issuedAt;public final boolean authorized;
        public MockTicket(long epoch,long operation,long issuedAt,boolean authorized){this.epoch=epoch;this.operation=operation;this.issuedAt=issuedAt;this.authorized=authorized;}
    }
    public static final class MockReceipt {
        public final long epoch,operation,observedAt;public final boolean known,verified,matchingPostcondition;
        public MockReceipt(long epoch,long operation,long observedAt,boolean known,boolean verified,boolean matchingPostcondition){this.epoch=epoch;this.operation=operation;this.observedAt=observedAt;this.known=known;this.verified=verified;this.matchingPostcondition=matchingPostcondition;}
    }

    public TinyOrganism(long seed){initialize(seed);}
    private void initialize(long seed){
        Random r=new Random(seed); // new lab-only weights; no Jarvis/old UNO weights imported
        for(int i=0;i<D;i++){
            for(int k=0;k<INPUT;k++)encoder[i][k]=r.nextGaussian()*.10;
            for(int k=0;k<D;k++)us[i][k]=r.nextGaussian()*.015;
            for(int t=0;t<LABELS;t++)sensory[t][i]=r.nextGaussian()*.06;
            for(int t=0;t<INTENTS;t++)intent[t][i]=r.nextGaussian()*.06;
        }
        for(int block=0;block<NB;block++)for(int j=0;j<J;j++){
            for(int u=0;u<H;u++)for(int i=0;i<D;i++){
                a[block][j][u][i]=r.nextGaussian()*.065;
                c[block][j][u][i]=r.nextGaussian()*.065;
            }
            for(int q=0;q<BLOCK;q++)for(int u=0;u<H;u++)b[block][j][q][u]=r.nextGaussian()*.065;
        }
    }
    private static double clip(double x){return x>1?1:x< -1?-1:x;}
    private static double[] softmax(double[] logits){
        double max=Double.NEGATIVE_INFINITY,sum=0;for(double x:logits)max=Math.max(max,x);
        double[] p=new double[logits.length];for(int i=0;i<p.length;i++){p[i]=Math.exp(logits[i]-max);sum+=p[i];}
        for(int i=0;i<p.length;i++)p[i]/=sum;return p;
    }
    private static int argmax(double[] v){int k=0;for(int i=1;i<v.length;i++)if(v[i]>v[k])k=i;return k;}
    private static double[] features(Context e){
        double[] f=new double[INPUT];f[e.older]=1;f[3+e.previous]=1;
        int trend=e.previous>e.older?0:(e.previous<e.older?1:2);
        f[6+trend]=1;f[9+e.mode]=1;return f;
    }
    private double[] semanticSummary(){
        double[] mem=new double[D];int n=0;
        Iterator<MemoryRecord> it=ledger.descendingIterator();
        while(it.hasNext()&&n<8){MemoryRecord r=it.next();
            if(!r.source.equals("ANDROID_SENSOR_OBS")&&!r.source.equals("OWNER_TEACHING"))continue;
            double sign=r.source.equals("OWNER_TEACHING")?1:-1;
            // A lossy, bounded semantic signal, never exact recall and never authority.
            mem[(r.label+16)%D]+=sign*.12; mem[(r.previous+3)%D]+=.03;n++;
        }
        if(n>0)for(int i=0;i<D;i++)mem[i]/=n;return mem;
    }
    public Prediction predict(Context context){
        Forward f=new Forward();f.context=context;f.feat=features(context);f.sIn=state.clone();
        double[] sem=semanticSummary();f.z=new double[D];
        for(int i=0;i<D;i++){
            double v=sem[i];for(int k=0;k<INPUT;k++)v+=encoder[i][k]*f.feat[k];
            for(int k=0;k<D;k++)v+=us[i][k]*f.sIn[k];f.z[i]=Math.tanh(v);
        }
        double[] h=new double[D];for(int i=0;i<D;i++)h[i]=.5*(state[i]+f.z[i]);
        lastExec=lastSkip=0;
        for(int step=0;step<K;step++){
            StepCache cache=new StepCache();f.steps[step]=cache;System.arraycopy(h,0,cache.input,0,D);
            int first=(int)((serial+step)%NB);
            for(int t=0;t<ACTIVE;t++)cache.on[(first+t)%NB]=true;
            double[] next=h.clone();
            for(int block=0;block<NB;block++){
                if(!cache.on[block]){lastSkip++;continue;} // actual skip, no A/C/B kernels called
                lastExec++;
                for(int j=0;j<J;j++){
                    for(int u=0;u<H;u++){
                        double v=aa[block][j][u];
                        for(int q=0;q<D;q++)v+=a[block][j][u][q]*h[q]+c[block][j][u][q]*f.z[q];
                        cache.hidden[block][j][u]=Math.tanh(v);
                    }
                    for(int q=0;q<BLOCK;q++){
                        double v=bb[block][j][q];for(int u=0;u<H;u++)v+=b[block][j][q][u]*cache.hidden[block][j][u];
                        cache.branch[block][j][q]=Math.tanh(v);
                    }
                }
                for(int q=0;q<BLOCK;q++){
                    double v=0;for(int j=0;j<J;j++)v+=cache.branch[block][j][q];
                    int off=block*BLOCK+q;
                    next[off]=clip((1-ALPHA)*h[off]+(ALPHA/J)*v);
                }
            }
            h=next;System.arraycopy(h,0,cache.output,0,D);
        }
        f.hFinal=h.clone();System.arraycopy(h,0,state,0,D);
        double[] sLog=new double[LABELS],iLog=new double[INTENTS];
        for(int t=0;t<LABELS;t++){sLog[t]=sensoryBias[t];for(int i=0;i<D;i++)sLog[t]+=sensory[t][i]*h[i];}
        for(int t=0;t<INTENTS;t++){iLog[t]=intentBias[t];for(int i=0;i<D;i++)iLog[t]+=intent[t][i]*h[i];}
        f.sensorProb=softmax(sLog);f.intentProb=softmax(iLog);last=f;lastForOwner=f;
        long ev=++serial;append(new MemoryRecord(ev,"MODEL_PREDICTION",context.mode,context.older,context.previous,argmax(f.sensorProb),"unverified future window"));
        return new Prediction(argmax(f.sensorProb),argmax(f.intentProb),lastExec,lastSkip,f.sensorProb.clone(),f.intentProb.clone(),ev);
    }
    /** Actual next Android sensor label arrives only AFTER prospective forecast. */
    public void observeSensor(int actual,boolean train){
        if(actual<0||actual>=LABELS||last==null)throw new IllegalArgumentException("no prospective prediction/invalid label");
        Forward f=last;append(new MemoryRecord(++serial,"ANDROID_SENSOR_OBS",f.context.mode,f.context.older,f.context.previous,actual,"observed after prediction; not an OS action receipt"));
        if(train){superviseSensor(f,actual);sensoryLearningCount++;}
        last=null; // prevents retroactive multiple updates on one observation
    }
    private void superviseSensor(Forward f,int label){
        double[] delta=f.sensorProb.clone();delta[label]-=1;
        double[] g=new double[D];
        for(int t=0;t<LABELS;t++){
            for(int i=0;i<D;i++)g[i]+=sensory[t][i]*delta[t];
        }
        for(int t=0;t<LABELS;t++){
            for(int i=0;i<D;i++)sensory[t][i]=clip(sensory[t][i]-LR*delta[t]*f.hFinal[i]);
            sensoryBias[t]=clip(sensoryBias[t]-LR*delta[t]);
        }
        double[] gradZ=new double[D];
        // Reverse through the same two recurrent F passes, with a fixed executed mask path.
        for(int step=K-1;step>=0;step--){
            StepCache sc=f.steps[step];double[] previousG=new double[D];
            for(int block=0;block<NB;block++){
                if(!sc.on[block]){for(int q=0;q<BLOCK;q++)previousG[block*BLOCK+q]+=g[block*BLOCK+q];continue;}
                for(int q=0;q<BLOCK;q++)previousG[block*BLOCK+q]+=(1-ALPHA)*g[block*BLOCK+q];
                for(int j=0;j<J;j++){
                    double[] gHidden=new double[H];
                    for(int q=0;q<BLOCK;q++){
                        int idx=block*BLOCK+q;
                        double vf=sc.branch[block][j][q];
                        double gv=g[idx]*(ALPHA/J)*(1-vf*vf);
                        for(int u=0;u<H;u++){
                            gHidden[u]+=b[block][j][q][u]*gv;
                            b[block][j][q][u]=clip(b[block][j][q][u]-LR*gv*sc.hidden[block][j][u]);
                        }
                        bb[block][j][q]=clip(bb[block][j][q]-LR*gv);
                    }
                    for(int u=0;u<H;u++){
                        double zH=sc.hidden[block][j][u];double gu=gHidden[u]*(1-zH*zH);
                        for(int p=0;p<D;p++){
                            previousG[p]+=a[block][j][u][p]*gu;
                            gradZ[p]+=c[block][j][u][p]*gu;
                            a[block][j][u][p]=clip(a[block][j][u][p]-LR*gu*sc.input[p]);
                            c[block][j][u][p]=clip(c[block][j][u][p]-LR*gu*f.z[p]);
                        }
                        aa[block][j][u]=clip(aa[block][j][u]-LR*gu);
                    }
                }
            }
            g=previousG;
        }
        for(int i=0;i<D;i++){
            double gz=(gradZ[i]+.5*g[i])*(1-f.z[i]*f.z[i]);
            for(int k=0;k<INPUT;k++)encoder[i][k]=clip(encoder[i][k]-LR*gz*f.feat[k]);
            for(int k=0;k<D;k++)us[i][k]=clip(us[i][k]-LR*gz*f.sIn[k]);
        }
    }
    /** Owner correction affects an intent head, not physical ground truth or OS capabilities. */
    public void teachOwnerIntent(int intendedMeaning){
        if(intendedMeaning<0||intendedMeaning>=INTENTS||(last==null&&lastForOwner==null))throw new IllegalArgumentException("owner feedback requires latest event");
        Forward f=last!=null?last:lastForOwner;double[] delta=f.intentProb.clone();delta[intendedMeaning]-=1;
        for(int t=0;t<INTENTS;t++){
            for(int i=0;i<D;i++)intent[t][i]=clip(intent[t][i]-INTENT_LR*delta[t]*f.hFinal[i]);
            intentBias[t]=clip(intentBias[t]-INTENT_LR*delta[t]);
        }
        append(new MemoryRecord(++serial,"OWNER_TEACHING",f.context.mode,f.context.older,f.context.previous,intendedMeaning,"reported intended meaning; not an Android receipt"));
        ownerTeachCount++;
    }
    public void stop(){stopLatched=true;stopEpoch++;append(new MemoryRecord(++serial,"OWNER_STOP",0,0,0,0,"latch; no automatic reset"));}
    public void ownerClearStop(){stopLatched=false;}
    public long epoch(){return stopEpoch;}
    /** Models an externally verified outcome. This class cannot validate real Android evidence. */
    public boolean learnMockVerifiedOutcome(MockTicket ticket,MockReceipt receipt,int observedBinary){
        if(ticket==null||receipt==null||last==null||stopLatched||!ticket.authorized||observedBinary<0||observedBinary>1)return false;
        if(ticket.epoch!=stopEpoch||receipt.epoch!=ticket.epoch||ticket.operation!=receipt.operation||ticket.operation<=lastAcceptedMockOperation||ticket.issuedAt<0)return false;
        if(receipt.observedAt<=ticket.issuedAt||receipt.observedAt-ticket.issuedAt>60_000||!receipt.known||!receipt.verified||!receipt.matchingPostcondition)return false;
        double[] h=last.hFinal;double logit=0,norm=1;
        for(int i=0;i<D;i++){logit+=plastic[i]*h[i];norm+=h[i]*h[i];}
        double p=1/(1+Math.exp(-logit));double update=(p-observedBinary)/norm;
        double radius2=0;
        for(int i=0;i<D;i++){plastic[i]-=.01*(update*h[i]+.001*plastic[i]);radius2+=plastic[i]*plastic[i];}
        if(radius2>1){double factor=1/Math.sqrt(radius2);for(int i=0;i<D;i++)plastic[i]*=factor;}
        append(new MemoryRecord(++serial,"MOCK_VERIFIED_OUTCOME",last.context.mode,last.context.older,last.context.previous,observedBinary,"synthetic fixture only; not native Android readback"));
        lastAcceptedMockOperation=ticket.operation;checkedOutcomes++;return true;
    }
    private void append(MemoryRecord r){if(ledger.size()==MEMORY_CAP)ledger.removeFirst();ledger.addLast(r);}
    public ExactResult retrieveExact(long id){
        if(id<=0||id>serial)return new ExactResult(ExactStatus.UNKNOWN,null);
        for(MemoryRecord r:ledger)if(r.id==id)return new ExactResult(ExactStatus.COMPLETE,r);
        return new ExactResult(ExactStatus.TRUNCATED,null);
    }
    public int activeMemoryEntries(){return ledger.size();}
    public long sensoryLearningCount(){return sensoryLearningCount;}
    public long ownerTeachingCount(){return ownerTeachCount;}
    public long mockOutcomeCount(){return checkedOutcomes;}
    public int executedBlocks(){return lastExec;}
    public int skippedBlocks(){return lastSkip;}
    public double[] currentState(){return state.clone();}
    public double plasticNorm(){double n=0;for(double v:plastic)n+=v*v;return Math.sqrt(n);}
    public String weightsFingerprint(){
        try{
            ByteArrayOutputStream out=new ByteArrayOutputStream();DataOutputStream d=new DataOutputStream(out);
            writeWeights(d);d.flush();return sha256(out.toByteArray());
        }catch(IOException x){throw new IllegalStateException(x);}
    }
    public static String sha256(byte[] raw){
        try{byte[] h=MessageDigest.getInstance("SHA-256").digest(raw);StringBuilder b=new StringBuilder();for(byte x:h)b.append(String.format(Locale.ROOT,"%02x",x&255));return b.toString();}
        catch(Exception e){throw new IllegalStateException(e);}
    }
    private static void writeDouble(DataOutputStream d,double v)throws IOException{if(!Double.isFinite(v)||Math.abs(v)>2)throw new IOException("nonfinite/unsafe number");d.writeDouble(v);}
    private static void write2(DataOutputStream d,double[][] arr)throws IOException{for(double[] row:arr)for(double v:row)writeDouble(d,v);}
    private static void read2(DataInputStream d,double[][] arr)throws IOException{for(double[] row:arr)for(int i=0;i<row.length;i++)row[i]=safeRead(d);}
    private static double safeRead(DataInputStream d)throws IOException{double x=d.readDouble();if(!Double.isFinite(x)||Math.abs(x)>2)throw new IOException("unsafe state");return x;}
    private void writeWeights(DataOutputStream d)throws IOException{
        write2(d,encoder);write2(d,us);
        for(int k=0;k<NB;k++)for(int j=0;j<J;j++){write2(d,a[k][j]);write2(d,c[k][j]);write2(d,b[k][j]);for(double x:aa[k][j])writeDouble(d,x);for(double x:bb[k][j])writeDouble(d,x);}
        write2(d,sensory);write2(d,intent);for(double x:sensoryBias)writeDouble(d,x);for(double x:intentBias)writeDouble(d,x);
    }
    private void readWeights(DataInputStream d)throws IOException{
        read2(d,encoder);read2(d,us);
        for(int k=0;k<NB;k++)for(int j=0;j<J;j++){read2(d,a[k][j]);read2(d,c[k][j]);read2(d,b[k][j]);for(int x=0;x<H;x++)aa[k][j][x]=safeRead(d);for(int x=0;x<BLOCK;x++)bb[k][j][x]=safeRead(d);}
        read2(d,sensory);read2(d,intent);for(int i=0;i<LABELS;i++)sensoryBias[i]=safeRead(d);for(int i=0;i<INTENTS;i++)intentBias[i]=safeRead(d);
    }
    public byte[] checkpoint(){
        try{
            ByteArrayOutputStream buf=new ByteArrayOutputStream();DataOutputStream d=new DataOutputStream(buf);
            d.writeInt(MAGIC);d.writeInt(VERSION);writeWeights(d);
            for(double x:state)writeDouble(d,x);for(double x:plastic)writeDouble(d,x);
            d.writeLong(serial);d.writeLong(ownerTeachCount);d.writeLong(sensoryLearningCount);d.writeLong(checkedOutcomes);d.writeLong(stopEpoch);d.writeLong(lastAcceptedMockOperation);d.writeBoolean(stopLatched);
            d.writeInt(ledger.size());for(MemoryRecord r:ledger){d.writeLong(r.id);d.writeUTF(r.source);d.writeInt(r.mode);d.writeInt(r.older);d.writeInt(r.previous);d.writeInt(r.label);d.writeUTF(r.note);}
            d.flush();byte[] payload=buf.toByteArray();
            byte[] digest=MessageDigest.getInstance("SHA-256").digest(payload);
            ByteArrayOutputStream envelope=new ByteArrayOutputStream();envelope.write(payload);envelope.write(digest);
            return envelope.toByteArray();
        }catch(Exception e){throw new IllegalStateException(e);}
    }
    public static TinyOrganism restore(byte[] raw)throws IOException{
        if(raw==null||raw.length<40||raw.length>500_000)throw new IOException("bad size");
        int len=raw.length-32;
        byte[] payload=Arrays.copyOf(raw,len);
        byte[] expected=Arrays.copyOfRange(raw,len,raw.length);
        try{if(!Arrays.equals(expected,MessageDigest.getInstance("SHA-256").digest(payload)))throw new IOException("checkpoint SHA256 mismatch");}
        catch(java.security.NoSuchAlgorithmException x){throw new IOException(x);}
        DataInputStream d=new DataInputStream(new ByteArrayInputStream(payload));
        if(d.readInt()!=MAGIC||d.readInt()!=VERSION)throw new IOException("ABI mismatch");
        TinyOrganism n=new TinyOrganism(0);n.readWeights(d);
        for(int i=0;i<D;i++){n.state[i]=safeRead(d);if(Math.abs(n.state[i])>1)throw new IOException("state out of cube");}
        for(int i=0;i<D;i++)n.plastic[i]=safeRead(d);
        if(n.plasticNorm()>1.000000001)throw new IOException("plastic norm");
        n.serial=d.readLong();n.ownerTeachCount=d.readLong();n.sensoryLearningCount=d.readLong();n.checkedOutcomes=d.readLong();n.stopEpoch=d.readLong();n.lastAcceptedMockOperation=d.readLong();n.stopLatched=d.readBoolean();
        if(n.serial<0||n.ownerTeachCount<0||n.sensoryLearningCount<0||n.checkedOutcomes<0||n.stopEpoch<0||n.lastAcceptedMockOperation<0)throw new IOException("bad counters");
        int count=d.readInt();if(count<0||count>MEMORY_CAP)throw new IOException("memory size");
        long prev=0;for(int i=0;i<count;i++){
            long id=d.readLong();String source=d.readUTF();int mode=d.readInt(),older=d.readInt(),previous=d.readInt(),label=d.readInt();String note=d.readUTF();
            if(id<=prev||id>n.serial||mode<0||mode>1||older<0||older>2||previous<0||previous>2||label<0||label>2||source.length()>64||note.length()>512)throw new IOException("bad evidence");
            prev=id;n.append(new MemoryRecord(id,source,mode,older,previous,label,note));
        }
        if(d.available()!=0)throw new IOException("trailing bytes");return n;
    }
}
