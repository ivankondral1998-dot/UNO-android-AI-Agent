package org.unovyra.n0research;

import android.app.Activity;
import android.os.Bundle;
import android.os.Build;
import android.os.SystemClock;
import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.Context;
import android.graphics.Color;
import android.view.View;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.Comparator;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

/** UNO-N0-03: isolated Android-only research, no production UNO components. */
public final class MainActivity extends Activity {
    private TextView reportView;
    private Button stageAButton, stageBButton;
    private NeuralOrganism organism;
    private int stage;
    private final StringBuilder report = new StringBuilder();
    private static final String[] SIGNALS = {"ICE", "MAGNET_ON", "FIELD_HIGH", "COLOR_BLUE", "MATERIAL_STEEL"};

    @Override public void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        ScrollView scroll = new ScrollView(this);
        scroll.setFillViewport(true);
        LinearLayout column = new LinearLayout(this);
        column.setOrientation(LinearLayout.VERTICAL);
        column.setPadding(dp(18), dp(20), dp(18), dp(32));
        column.setBackgroundColor(Color.rgb(245, 247, 250));
        scroll.addView(column);
        TextView title = text("UNO-N0-03 • Живые связи", 23, 0xff142c47);
        title.setTypeface(null, 1);
        column.addView(title);
        column.addView(text("Исследовательский опыт на Android: нейроны без числовых синаптических весов. Виртуальный мир, не доступ к устройству.", 15, 0xff394e61));
        stageAButton = button("1 • Обучить на телефоне", column, v -> runA());
        stageBButton = button("2 • Исправить неожиданную ошибку", column, v -> runB());
        button("Сбросить исследовательскую сеть", column, v -> reset());
        button("Скопировать отчёт", column, v -> {
            ((ClipboardManager)getSystemService(Context.CLIPBOARD_SERVICE))
                .setPrimaryClip(ClipData.newPlainText("UNO-N0-03 report", report.toString()));
            android.widget.Toast.makeText(this, "Отчёт скопирован", android.widget.Toast.LENGTH_SHORT).show();
        });
        reportView = text("", 14, 0xff183049);
        reportView.setTextIsSelectable(true);
        column.addView(reportView);
        setContentView(scroll);
        reset();
    }

    private int dp(int n) { return Math.round(getResources().getDisplayMetrics().density * n); }
    private TextView text(String s, int size, int color) {
        TextView t = new TextView(this);
        t.setText(s);
        t.setTextSize(size);
        t.setTextColor(color);
        t.setPadding(0, dp(7), 0, dp(7));
        return t;
    }
    private Button button(String s, LinearLayout layout, View.OnClickListener click) {
        Button b = new Button(this);
        b.setText(s);
        b.setAllCaps(false);
        layout.addView(b);
        b.setOnClickListener(click);
        return b;
    }
    private void log(String s) { report.append(s).append('\n'); reportView.setText(report.toString()); }
    private void reset() {
        organism = new NeuralOrganism();
        stage = 0;
        stageAButton.setEnabled(true);
        stageBButton.setEnabled(false);
        report.setLength(0);
        log("UNO-N0-03 / ANDROID EXPERIMENT / VERSION 1\n" +
            "Устройство: " + Build.MANUFACTURER + " " + Build.MODEL + ", Android API " + Build.VERSION.SDK_INT + "\n" +
            "Эксперимент ещё не запущен. Нажмите кнопку 1.\n" +
            "Важное ограничение: виртуальный симулятор выдаёт результаты; это НЕ нативная проверка физических действий Android.\n" +
            "Алгоритм построения составных нейронов задан разработчиком. Без числовых весов ≠ без числовых вычислений.\n");
    }

    private static boolean worldFlip(int state) {
        boolean ice = (state & 1) != 0;
        boolean magnet = (state & 2) != 0;
        boolean field = (state & 4) != 0;
        boolean blue = (state & 8) != 0;
        // Secret environment law; NeuralOrganism NEVER calls this method.
        return (field || (ice && magnet)) ^ (ice && magnet && field && blue);
    }
    private static boolean reportedOutcome(int state, boolean actionRight) {
        return actionRight ^ worldFlip(state);
    }
    private static Set<String> activeSignals(int mask) {
        LinkedHashSet<String> active = new LinkedHashSet<>();
        for (int i=0; i<SIGNALS.length; i++) if ((mask & (1 << i)) != 0) active.add(SIGNALS[i]);
        return active;
    }
    private static int evaluate(NeuralOrganism n, boolean actionRight) {
        int correct = 0;
        for (int mask=0; mask<32; mask++) {
            Boolean got = n.predictOutcome(activeSignals(mask), actionRight);
            if (got != null && got.booleanValue() == reportedOutcome(mask, actionRight)) correct++;
        }
        return correct;
    }
    private static int evaluateUnseen(NeuralOrganism n, boolean actionRight) {
        int correct = 0;
        for (int mask=0; mask<32; mask++) {
            if (n.observed.containsKey(mask)) continue;
            Boolean got = n.predictOutcome(activeSignals(mask), actionRight);
            if (got != null && got.booleanValue() == reportedOutcome(mask, actionRight)) correct++;
        }
        return correct;
    }
    private static int retainSingles(NeuralOrganism n) {
        int correct = 0;
        for (int mask : new int[]{0,1,2,4,8,16}) {
            for (boolean actionRight : new boolean[]{false,true}) {
                Boolean p = n.predictOutcome(activeSignals(mask), actionRight);
                if (p != null && p.booleanValue() == reportedOutcome(mask, actionRight)) correct++;
            }
        }
        return correct;
    }
    private String graph(NeuralOrganism n) {
        StringBuilder sb = new StringBuilder();
        for (NeuralOrganism.CompositeNeuron node : n.composites) {
            sb.append("  [").append(node.name).append("] ").append(node.required).append(" → FLIP\n");
        }
        return sb.toString();
    }
    private static String fmtTime(long durationNanos) { return (durationNanos / 1000000L) + " ms"; }
    private static long heap() { Runtime r=Runtime.getRuntime(); return (r.totalMemory()-r.freeMemory()) / 1024; }

    private void runA() {
        if (stage != 0) return;
        long heapBefore = heap(), start = SystemClock.elapsedRealtimeNanos();
        int visits = 0;
        for (int level=0; level<=2; level++) {
            for (int mask=0; mask<32; mask++) {
                if (Integer.bitCount(mask) != level) continue;
                organism.observe(mask, activeSignals(mask), true, reportedOutcome(mask,true), true);
                visits++;
            }
        }
        // Deliberately learn a three-way interaction in the baseline color/material.
        organism.observe(7, activeSignals(7), true, reportedOutcome(7,true), true);
        visits++;
        long elapsed = SystemClock.elapsedRealtimeNanos()-start;
        stage=1; stageAButton.setEnabled(false); stageBButton.setEnabled(true);
        log("=== СТАДИЯ 1: ОБУЧЕНИЕ ===");
        log("Получено проверенных результатов виртуального мира: " + visits);
        log("Научившиеся составные нейроны: " + organism.composites.size());
        log(graph(organism));
        log("Старые ситуации: " + retainSingles(organism) + "/12");
        log("Все 32 контекста / прежнее действие: " + evaluate(organism,true) + "/32");
        log("Невиданные контексты / прежнее действие: " + evaluateUnseen(organism,true) + "/" + (32-organism.observed.size()));
        log("Новое направление действия: " + evaluate(organism,false) + "/32");
        log("Простая сеть с одним FIELD-модификатором: " + fixedFieldScore() + "/32");
        log("Ожидаемое неожиданное событие: ICE + MAGNET + FIELD + BLUE (четверное взаимодействие).");
        log("Измерено на этом телефоне: обучение " + fmtTime(elapsed) + ", heap до " + heapBefore + " KiB, после " + heap() + " KiB. НЕ энергия батареи.\n");
    }
    private int fixedFieldScore() {
        int total=0;
        for(int mask=0;mask<32;mask++) if (((mask & 4)!=0)==worldFlip(mask)) total++;
        return total;
    }
    private void runB() {
        if (stage!=1) return;
        final int surprise=15; // ICE, MAGNET, FIELD, BLUE; never presented during stage 1.
        long heapBefore=heap(), start=SystemClock.elapsedRealtimeNanos();
        Boolean before=organism.predictOutcome(activeSignals(surprise), true);
        boolean actual=reportedOutcome(surprise, true);
        if (before != null && before.booleanValue()==actual) {
            log("НЕОЖИДАННЫЙ СТОП: контрольная ошибка не воспроизведена. Без перестройки.");return;
        }
        String first=organism.observe(surprise,activeSignals(surprise),true,actual,true);
        log("=== СТАДИЯ 2: ОШИБКА И ВОССТАНОВЛЕНИЕ ===");
        log("До обучения: предсказано " + before + ", реально " + actual + "; реакция=" + first);
        // Network proposes the missing contrast contexts for the single open puzzle.
        List<Integer> probes = organism.missingContrasts(surprise);
        log("Сеть запросила контрольные наблюдения: " + probes.toString());
        for (int p : probes) {
            log("  Probe " + p + " : " + organism.observe(p, activeSignals(p), true, reportedOutcome(p,true), true));
        }
        String resolved=organism.resolvePending();
        long elapsed=SystemClock.elapsedRealtimeNanos()-start;
        stage=2; stageBButton.setEnabled(false);
        log("Перестройка: " + resolved);
        log("Соединения после новых наблюдений:\n" + graph(organism));
        log("Проверка старых ситуаций: " + retainSingles(organism) + "/12");
        log("Все 32 контекста / прежнее действие: " + evaluate(organism,true) + "/32");
        log("Невиданные контексты / прежнее действие: " + evaluateUnseen(organism,true) + "/" + (32-organism.observed.size()));
        log("Необученное другое действие: " + evaluate(organism,false) + "/32");
        log("Сколько наблюдений использовано всего: " + organism.observed.size());
        // Negative controls: receipt contradiction and new unseen latent cause.
        int priorEdges = organism.synapses.size();
        String unverified=organism.observe(31, activeSignals(31), true, !reportedOutcome(31,true), false);
        log("Ложный неподтверждённый результат: " + unverified + "; граф не изменён=" + (priorEdges==organism.synapses.size()));
        String conflict=organism.observe(0, activeSignals(0), true, !reportedOutcome(0,true), true);
        log("Противоречивый подтверждённый результат: " + conflict + "; прогноз для этого контекста UNKNOWN=" + (organism.predictOutcome(activeSignals(0),true)==null));
        log("Новая скрытая причина SHIELD (не представлена сенсором) может перевернуть результат без изменения входов: FAIL_EXPECTED.");
        log("Измерено на этом телефоне: дообучение " + fmtTime(elapsed) + ", heap до " + heapBefore + " KiB, после " + heap() + " KiB. НЕ энергия батареи.");
        log("\nВнимание: обучающий симулятор и генератор контрастов не являются системой реального Android readback. Это не AGI и не доказательство научной новизны.");
    }

    /** Plastic neurons are Boolean coincidence detectors with typed synapses. */
    static final class NeuralOrganism {
        static final class Synapse {
            final String source, target, relation;
            Synapse(String a, String b, String r) { source=a; target=b; relation=r; }
            @Override public boolean equals(Object o) {
                if(!(o instanceof Synapse))return false;
                Synapse z=(Synapse)o;
                return source.equals(z.source)&&target.equals(z.target)&&relation.equals(z.relation);
            }
            @Override public int hashCode() {return (source+"|"+target+"|"+relation).hashCode();}
        }
        static final class CompositeNeuron {
            final String name;
            final Set<String> required;
            CompositeNeuron(String name,Set<String> requires) {
                this.name=name;
                this.required=Collections.unmodifiableSet(new LinkedHashSet<>(requires));
            }
            boolean fires(Set<String> active) {return active.containsAll(required);}
        }
        final List<CompositeNeuron> composites=new ArrayList<>();
        final Set<Synapse> synapses=new LinkedHashSet<>();
        final Map<Integer,Boolean> observed=new LinkedHashMap<>();
        final Set<Integer> contradictory=new HashSet<>();
        final Map<Integer,Boolean> pending=new LinkedHashMap<>();
        Boolean defaultFlip=null;

        Boolean predictFlip(Set<String> signals) {
            if(defaultFlip==null) return null;
            boolean flip=defaultFlip;
            for(CompositeNeuron neuron:composites) if(neuron.fires(signals)) flip=!flip;
            return flip;
        }
        Boolean predictOutcome(Set<String> signals,boolean actionRight) {
            // No environment oracle or numerical synaptic coefficient is read here.
            int contextId=0;
            for(int i=0;i<SIGNALS.length;i++) if(signals.contains(SIGNALS[i])) contextId|=(1<<i);
            if(contradictory.contains(contextId)) return null;
            Boolean predicted=predictFlip(signals);
            return predicted==null?null:(actionRight ^ predicted.booleanValue());
        }
        String observe(int id,Set<String> signals,boolean actionRight,boolean actualRight,boolean independentlyVerified) {
            if(!independentlyVerified)return "UNVERIFIED_REJECTED";
            boolean flip=(actionRight!=actualRight);
            if(observed.containsKey(id)) {
                if(observed.get(id).booleanValue()!=flip) {contradictory.add(id);return "CONFLICT_UNKNOWN";}
                return "REPEAT_NO_CHANGE";
            }
            if(id==0 && defaultFlip==null) {
                defaultFlip=flip;observed.put(0,flip);return "REFERENCE_LEARNED";
            }
            if(defaultFlip==null)return "NEED_REFERENCE";
            if(!hasAllStrictSubsets(id)) {pending.put(id,flip);return "MISSING_CONTRASTS";}
            observed.put(id,flip);
            Boolean p=predictFlip(signals);
            if(p==null)return "UNKNOWN";
            if(p.booleanValue()!=flip) {
                createComposite(signals);
                return "NEW_COMPOSITE_NEURON_"+signals.size();
            }
            return "MATCH_NO_REWIRE";
        }
        private void createComposite(Set<String> signals) {
            StringBuilder sb=new StringBuilder("JOINT:");
            for(String v:signals) sb.append(v).append("+");
            String id=sb.toString();
            for (CompositeNeuron old:composites) if(old.name.equals(id))return;
            CompositeNeuron node=new CompositeNeuron(id,signals);
            composites.add(node);
            for(String signal:signals) synapses.add(new Synapse("SENSE:"+signal,id,"REQUIRES"));
            synapses.add(new Synapse(id,"STATE:PARITY","FLIP"));
        }
        boolean hasAllStrictSubsets(int id) {
            for(int sub=(id-1)&id;;sub=(sub-1)&id) {
                if(!observed.containsKey(sub))return false;
                if(sub==0)break;
            }
            return true;
        }
        List<Integer> missingContrasts(int id) {
            List<Integer> list=new ArrayList<>();
            for(int sub=(id-1)&id;;sub=(sub-1)&id) {
                if(!observed.containsKey(sub))list.add(sub);
                if(sub==0)break;
            }
            Collections.sort(list, new Comparator<Integer>() {
                @Override public int compare(Integer a,Integer b) {
                    int x=Integer.compare(Integer.bitCount(a),Integer.bitCount(b));
                    return x!=0?x:Integer.compare(a,b);
                }
            });
            return list;
        }
        String resolvePending() {
            if(pending.isEmpty())return "NO_PENDING";
            List<Integer> keys=new ArrayList<>(pending.keySet());
            for(int id:keys) {
                if(hasAllStrictSubsets(id)) {
                    boolean relation=pending.remove(id);
                    String result=observe(id,activeSignals(id),true,true ^ relation,true);
                    return result;
                }
            }
            return "UNRESOLVED_PENDING";
        }
    }
}