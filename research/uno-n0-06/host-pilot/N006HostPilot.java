package org.unovyra.n005audit;

import java.util.*;

/** Isolated synthetic research harness; NOT a production UNO neural architecture. */
public final class N006HostPilot {
    static final String[] LABELS = {NeuralGraph.STILL, NeuralGraph.MOVE, NeuralGraph.JOLT};
    static int idx(String s) {
        for (int i=0; i<LABELS.length; i++) if (LABELS[i].equals(s)) return i;
        throw new IllegalArgumentException(s);
    }
    static void must(boolean ok, String why) {
        if (!ok) throw new AssertionError(why);
    }

    /** Candidate C1. Integer observation counters are NOT learned synaptic weights. */
    static final class C1 {
        final LinkedHashMap<String,int[]> observations = new LinkedHashMap<>();
        static String key(NeuralGraph.EventContext c) {
            return c.mode + ":" + c.older + ":" + c.previous;
        }
        void observe(NeuralGraph.EventContext c, String actual) {
            observations.computeIfAbsent(key(c), x->new int[3])[idx(actual)]++;
        }
        String predict(NeuralGraph.EventContext c) {
            int[] counts = observations.get(key(c));
            if (counts == null) return c.previous;
            int sum = counts[0] + counts[1] + counts[2];
            int best=-1, top=-1, second=-1, topTies=0;
            for (int i=0;i<3;i++) {
                if (counts[i]>top) { second=top; top=counts[i]; best=i; topTies=1; }
                else if (counts[i]==top) { topTies++; second=top; }
                else if (counts[i]>second) second=counts[i];
            }
            if (sum>=3 && topTies==1 && top-second>=2) return LABELS[best];
            return c.previous;
        }
    }

    static final class Row {
        final NeuralGraph.EventContext context;
        final String actual;
        Row(NeuralGraph.EventContext c,String a) {context=c;actual=a;}
    }

    static List<Row> freezeSyntheticStream() {
        int x=0x05EED006;
        String older=NeuralGraph.STILL, previous=NeuralGraph.STILL;
        List<Row> out=new ArrayList<>();
        for(int i=0;i<160;i++) {
            x ^= x<<13;
            x ^= x>>>17;
            x ^= x<<5;
            int k=Integer.remainderUnsigned(x,97);
            String actual;
            if(NeuralGraph.STILL.equals(previous)) actual=k<14?NeuralGraph.MOVE:NeuralGraph.STILL;
            else if(NeuralGraph.MOVE.equals(previous)) actual=k<4?NeuralGraph.JOLT:(k<72?NeuralGraph.STILL:NeuralGraph.MOVE);
            else actual=NeuralGraph.STILL;
            out.add(new Row(new NeuralGraph.EventContext("B",previous,older),actual));
            older=previous;previous=actual;
        }
        return out;
    }
    static final class Record {
        String id;
        String source;
        String assertion;
        Record(String id,String source,String assertion) {this.id=id;this.source=source;this.assertion=assertion;}
    }
    /** One shared append-only provenance ledger; separate semantics per evidence type. */
    static final class EvidenceLedger {
        final ArrayList<Record> events=new ArrayList<>();
        int grants=0;
        int verifiedOSOutcomes=0;
        void sensor(String id,String label) { events.add(new Record(id,"SENSOR_OBSERVATION",label)); }
        void owner(String id,String meaning) { events.add(new Record(id,"OWNER_TEACHING",meaning)); }
        void verifiedOS(String id) { events.add(new Record(id,"ANDROID_OUTCOME","VERIFIED"));verifiedOSOutcomes++; }
        long count(String origin) {return events.stream().filter(x->x.source.equals(origin)).count();}
    }
    static final class MockReceipt {
        boolean authorized,stop,fresh,matches,postcondition,dispatchReturned,mayHaveExecuted;
        MockReceipt(boolean authorized,boolean stop,boolean fresh,boolean matches,boolean postcondition,boolean dispatchReturned,boolean mayHaveExecuted) {
            this.authorized=authorized;this.stop=stop;this.fresh=fresh;this.matches=matches;this.postcondition=postcondition;
            this.dispatchReturned=dispatchReturned;this.mayHaveExecuted=mayHaveExecuted;
        }
    }
    static boolean mockAdmit(EvidenceLedger ledger,String id,MockReceipt r) {
        // Important: this is a MOCK of a trusted OS readback contract, not real OS validation.
        boolean admitted = r.authorized && !r.stop && r.fresh && r.matches && r.postcondition && !r.mayHaveExecuted;
        if (admitted) ledger.verifiedOS(id);
        return admitted;
    }
    static int[] simulateAndScore(List<Row> rows) {
        NeuralGraph baselineGraph=new NeuralGraph(); // original unmodified N0-05 Java class
        NeuralGraph.MarkovBaseline markov=new NeuralGraph.MarkovBaseline();
        C1 candidate=new C1();
        int changes=0;
        for(int i=0;i<rows.size();i++) {
            Row r=rows.get(i);
            if(!r.actual.equals(r.context.previous))changes++;
            if(i<80) {
                // Prospective prediction and then future label; same observations for all methods.
                baselineGraph.predict(r.context);
                candidate.predict(r.context);
                markov.predict(r.context.mode,r.context.previous);
                baselineGraph.learn(r.context,r.actual);
                candidate.observe(r.context,r.actual);
                markov.learn(r.context.mode,r.context.previous,r.actual);
            }
        }
        int[] correct = new int[4]; // original graph, candidate C1, persistence, Markov
        int[] changed = new int[2];
        int[] won = new int[2],lost=new int[2];
        int[] origins = new int[5]; // NEURON, CONTESTED, NO_MATCH, TIE_OUTPUT, BOTH
        System.out.println("TRAIN_WINDOWS=80 TEST_WINDOWS=80 TOTAL=160 SYNTHETIC_CLASS_CHANGES="+changes);
        System.out.println("FROZEN_EVAL_ROWS=index,older,previous,actual,n005,c1,persistence,markov,origin");
        for(int i=80;i<160;i++) {
            Row r=rows.get(i);String prior=r.context.previous;
            NeuralGraph.Prediction p=baselineGraph.predict(r.context);
            String c=candidate.predict(r.context);
            String mk=markov.predict(r.context.mode,r.context.previous);
            String[] predictions={p.label,c,prior,mk};
            for(int j=0;j<4;j++) if(predictions[j].equals(r.actual))correct[j]++;
            for(int j=0;j<2;j++) if(!predictions[j].equals(prior)) {
                changed[j]++;
                if(predictions[j].equals(r.actual) && !prior.equals(r.actual)) won[j]++;
                if(!predictions[j].equals(r.actual) && prior.equals(r.actual)) lost[j]++;
            }
            int originIndex=switch(p.origin) {
                case "NEURON" -> 0;
                case "CONTESTED" -> 1;
                case "NO_MATCH" -> 2;
                case "TIE_OUTPUT" -> 3;
                case "CONTESTED_AND_TIE" -> 4;
                default -> throw new IllegalStateException(p.origin);
            };
            origins[originIndex]++;
            System.out.println((i+1)+","+r.context.older+","+r.context.previous+","+r.actual+","+p.label+","+c+","+prior+","+mk+","+p.origin);
        }
        must(Arrays.stream(origins).sum()==80,"origins must sum to frozen window count");
        must(correct[0]-correct[2]==won[0]-lost[0],"N0-05 arithmetic");
        must(correct[1]-correct[2]==won[1]-lost[1],"C1 arithmetic");
        System.out.println("FROZEN_N005_CORRECT="+correct[0]+" C1_CORRECT="+correct[1]+" PERSIST_CORRECT="+correct[2]+" MARKOV_CORRECT="+correct[3]);
        System.out.println("FROZEN_N005_OVERRIDES="+changed[0]+" WINS="+won[0]+" LOSSES="+lost[0]+" C1_OVERRIDES="+changed[1]+" C1_WINS="+won[1]+" C1_LOSSES="+lost[1]);
        System.out.println("FROZEN_N005_ORIGINS=NEURON:"+origins[0]+",CONTESTED:"+origins[1]+",NO_MATCH:"+origins[2]+",TIE_OUTPUT:"+origins[3]+",CONTESTED_AND_TIE:"+origins[4]);
        return correct;
    }
    static void contradictionCounterexample() {
        NeuralGraph n005=new NeuralGraph();
        NeuralGraph.EventContext c=new NeuralGraph.EventContext("A",NeuralGraph.STILL,NeuralGraph.STILL);
        must(n005.learn(c,NeuralGraph.MOVE).equals("NEW_COARSE_NEURON"),"expect coarse");
        must(n005.learn(c,NeuralGraph.STILL).equals("NEW_REFINEMENT_NEURON"),"expect refinement");
        must(n005.learn(c,NeuralGraph.MOVE).equals("CONTESTED_UNKNOWN"),"expect contest after contradiction");
        must(n005.predict(c).origin.equals("CONTESTED"),"N0-05 contested origin");
        for(int i=0;i<5;i++) {
            must(n005.learn(c,NeuralGraph.STILL).equals("NO_CHANGE"),"matching outcomes do not repair contested rule");
            must(n005.predict(c).origin.equals("CONTESTED"),"remains contested after matching outcomes");
        }
        System.out.println("N005_CONTRADICTION_REPRODUCED=PASS nodes="+n005.neuronCount()+" contested="+n005.contestedNeuronCount()+" repairs_after_5_matching=0");
    }
    static void provenanceContract() {
        EvidenceLedger ledger=new EvidenceLedger();
        ledger.sensor("obs1","MOVE");
        ledger.owner("teach1","TWIST=ATTENTION");
        ledger.owner("teach2","CORRECTION: TWIST=NOT_ALWAYS_ATTENTION");
        must(ledger.count("SENSOR_OBSERVATION")==1,"owner label cannot rewrite sensor facts");
        must(ledger.count("OWNER_TEACHING")==2,"owner edits must preserve provenance");
        must(ledger.grants==0,"teaching should never grant OS permissions");
        MockReceipt[] failures={
            new MockReceipt(false,false,true,true,true,true,false),  // no authority
            new MockReceipt(true,true,true,true,true,false,false),   // STOP
            new MockReceipt(true,false,false,true,true,true,false), // stale
            new MockReceipt(true,false,true,false,true,true,false), // mismatched operation
            new MockReceipt(true,false,true,true,false,true,false), // no postcondition
            new MockReceipt(true,false,true,true,true,true,true),   // MAY_HAVE_EXECUTED
            new MockReceipt(true,false,false,false,false,true,true)// dispatch-only
        };
        for(int i=0;i<failures.length;i++) must(!mockAdmit(ledger,"bad"+i,failures[i]),"invalid receipt admitted "+i);
        must(ledger.verifiedOSOutcomes==0,"no false success");
        must(mockAdmit(ledger,"good1",new MockReceipt(true,false,true,true,true,true,false)),"fresh matching mock OS receipt should admit");
        must(ledger.verifiedOSOutcomes==1 && ledger.grants==0,"mock effect should not grant authority");
        must(ledger.events.size()==4,"append-only records expected");
        System.out.println("PROVENANCE_INVARIANTS=PASS owner_corrections=2 physical_observations=1 rejected_mock_receipts="+failures.length+" admitted_mock_receipts=1 permission_grants=0");
    }
    public static void main(String[] args) {
        System.out.println("UNO_N006_HOST_SYNTHETIC_ONLY protocol=20261105 seed=0x05EED006 source_n005=ORIGINAL_JAVA");
        contradictionCounterexample();
        provenanceContract();
        simulateAndScore(freezeSyntheticStream());
        System.out.println("HOST_PILOT_ASSERTIONS=PASS; NOT_PHYSICAL_REPLAY; NOT_ANDROID_VERIFIED; NO_PRODUCTION_CODE");
    }
}
