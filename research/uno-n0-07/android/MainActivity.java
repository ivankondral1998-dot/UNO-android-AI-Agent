package org.unovyra.n007;

import android.app.Activity;
import android.app.AlertDialog;
import android.os.Bundle;
import android.os.Build;
import android.os.Handler;
import android.os.Looper;
import android.os.SystemClock;
import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.Context;
import android.content.SharedPreferences;
import android.hardware.Sensor;
import android.hardware.SensorEvent;
import android.hardware.SensorEventListener;
import android.hardware.SensorManager;
import android.util.Base64;
import android.view.View;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;
import org.json.JSONArray;
import org.json.JSONObject;
import java.util.*;

/**
 * UNO-N0-07 sensor RESEARCH adapter. One TinyOrganism, NO Android external actions.
 * Android sensor labels are not independent proof of OS action consequences.
 * Distinct package from prior N0-04/N0-05; no network permissions.
 */
public final class MainActivity extends Activity implements SensorEventListener {
    private static final String[] STAGES={"A — ОБУЧЕНИЕ", "A — КОНТРОЛЬ", "B — ОБУЧЕНИЕ", "B — КОНТРОЛЬ", "A — ПОВТОР ПОСЛЕ ПЕРЕЗАПУСКА"};
    private static final int[] MODES={0,0,1,1,0};
    private static final boolean[] LEARN={true,false,true,false,false};
    private static final int TARGET=80,WINDOW_MS=250;
    private static final long TIMEOUT_NS=60_000_000_000L;
    private static final String PREF="uno_n007_research_private_v1",KEY="checkpoint",KEY_HASH="sha256";
    private SensorManager manager;
    private Sensor sensor;
    private boolean useGravityFilter=false,gravityReady=false,active=false,corrupt=false,loadedFromDiskThisActivity=false;
    private final double[] gravity=new double[3];
    private double windowMax=0;
    private int windowEvents=0,eventCount=0;
    private long lastEventAt=0,stageStartedAt=0;
    private int stage=0,valid=0,changed=0,skipped=0,correct=0,persistenceRight=0,markovRight=0,alwaysStill=0;
    private int older=-1,previous=-1,oldActual=-1,overrides=0;
    private long inferenceSumNs=0,inferenceMaxNs=0;
    private final ArrayList<Long> nanos=new ArrayList<>();
    private final int[][][] markov=new int[2][3][3];
    private TinyOrganism brain=new TinyOrganism(0x7a07L);
    private byte[] rollback;
    private int rollbackTraceLen=0,rollbackReportLen=0;
    private int[][][] rollbackMarkov;
    private final Handler handler=new Handler(Looper.getMainLooper());
    private final StringBuilder report=new StringBuilder("UNO-N0-07 / REAL SENSOR / Tiny Shared F / v0.7.0-research\n");
    private final StringBuilder trace=new StringBuilder("stage,index,mode,older,prev,model,markov,persistence,actual,executedBlocks,skippedBlocks\n");
    private TextView statusView,reportView;
    private Button startButton,stopButton,ownerAttention,ownerOrdinary;
    private String checkpointStatus="NO_CHECKPOINT_YET",restoreStatus="NO_CHECKPOINT_YET";

    @Override public void onCreate(Bundle saved){
        super.onCreate(saved);
        manager=(SensorManager)getSystemService(SENSOR_SERVICE);
        if(manager!=null){sensor=manager.getDefaultSensor(Sensor.TYPE_LINEAR_ACCELERATION);if(sensor==null){sensor=manager.getDefaultSensor(Sensor.TYPE_ACCELEROMETER);useGravityFilter=sensor!=null;}}
        loadCheckpoint();
        ScrollView scroll=new ScrollView(this);LinearLayout layout=new LinearLayout(this);
        layout.setOrientation(LinearLayout.VERTICAL);layout.setPadding(dp(18),dp(18),dp(18),dp(30));layout.setBackgroundColor(0xffeef3f7);
        scroll.addView(layout);layout.addView(text("UNO N0-07 • маленький единый F",21,true));
        layout.addView(text("16-мерное общее состояние • 4 блока F • 2 реально активных блока за проход • K=2. Новые экспериментальные обучаемые числа, память и подсказки владельца. Не финальный UNO.",14,false));
        statusView=text("",15,true);layout.addView(statusView);
        startButton=button(layout,"Начать текущую стадию",v->startStage());
        stopButton=button(layout,"СТОП / отменить стадию",v->abort("OWNER_STOP"));
        ownerAttention=button(layout,"Подсказка: это привлечение внимания",v->ownerTeach(1));
        ownerOrdinary=button(layout,"Подсказка: обычное движение",v->ownerTeach(0));
        button(layout,"Скопировать сводный отчёт",v->copy("UNO N0-07 Report",fullReport()));
        button(layout,"Скопировать 400 окон (трасса)",v->copy("UNO N0-07 Trace",trace.toString()));
        button(layout,"Сбросить ТОЛЬКО N0-07 (с подтверждением)",v->new AlertDialog.Builder(this).setTitle("Удалить эксперимент N0-07?")
            .setMessage("Все веса N0-07 и его история будут потеряны. N0-04/N0-05 не затрагиваются.")
            .setNegativeButton("Отмена",(d,w)->{}).setPositiveButton("Сбросить",(d,w)->resetResearch()).show());
        reportView=text("",13,false);reportView.setTextIsSelectable(true);layout.addView(reportView);setContentView(scroll);
        line("Device "+Build.MANUFACTURER+" "+Build.MODEL+" / API "+Build.VERSION.SDK_INT);
        line("Sensor "+(sensor==null?"MISSING":sensor.getName()+" type "+sensor.getType()));
        line("Readback of saved checkpoint: "+restoreStatus);
        line("Owner explanations != sensor truth != independent Android action readback. No external OS operations or network.");
        refresh();
    }
    private int dp(int v){return (int)(v*getResources().getDisplayMetrics().density+.5f);}
    private TextView text(String s,int size,boolean bold){TextView t=new TextView(this);t.setText(s);t.setTextSize(size);t.setTextColor(0xff203c56);t.setPadding(0,dp(6),0,dp(6));if(bold)t.setTypeface(null,1);return t;}
    private Button button(LinearLayout b,String title,View.OnClickListener listener){Button v=new Button(this);v.setAllCaps(false);v.setText(title);b.addView(v);v.setOnClickListener(listener);return v;}
    private void line(String s){report.append(s).append('\n');if(reportView!=null)reportView.setText(report.toString());}
    private void copy(String label,String value){ClipboardManager cm=(ClipboardManager)getSystemService(Context.CLIPBOARD_SERVICE);if(cm!=null)cm.setPrimaryClip(ClipData.newPlainText(label,value));Toast.makeText(this,"Скопировано",Toast.LENGTH_SHORT).show();}
    private String fullReport(){return report+"\nCURRENT_STATE stage="+stage+" checkpoint="+checkpointStatus+" restore="+restoreStatus+" learnedSensorEvents="+brain.sensoryLearningCount()+" ownerHints="+brain.ownerTeachingCount()+"\n";}
    private void refresh(){
        if(statusView==null)return;
        String title=stage<5?STAGES[stage]:"Все пять стадий завершены";
        String desc="Этап: "+title+"\nСенсор "+(sensor==null?"отсутствует":"доступен")+"; 80 прогнозов/этап; >=8 смен движения.\n";
        if(stage==4&&!loadedFromDiskThisActivity)desc+="Перед последним A: полностью закрой и повторно открой приложение.\n";
        if(active)desc+="Реальные окна "+valid+"/80; сенсорных событий "+eventCount+"; переходов "+changed+"\n";
        desc+="Обучение по датчику: "+brain.sensoryLearningCount()+"; подсказки: "+brain.ownerTeachingCount()+"; память "+brain.activeMemoryEntries()+"\nПроверка: "+checkpointStatus;
        statusView.setText(desc);
        startButton.setEnabled(!active&&!corrupt&&sensor!=null&&stage<5&&(stage!=4||loadedFromDiskThisActivity));
        stopButton.setEnabled(active);
        ownerAttention.setEnabled(active&&LEARN[stage]&&valid>0);
        ownerOrdinary.setEnabled(active&&LEARN[stage]&&valid>0);
    }
    private int tablePredict(int mode,int prev){int best=prev,max=0;for(int k=0;k<3;k++)if(markov[mode][prev][k]>max){best=k;max=markov[mode][prev][k];}return best;}
    private static int classify(double norm){return norm<.65?0:(norm<2.5?1:2);}
    private void startStage(){
        if(active||corrupt||sensor==null||stage>=5||(stage==4&&!loadedFromDiskThisActivity))return;
        rollback=brain.checkpoint();rollbackMarkov=copyCounts(markov);rollbackTraceLen=trace.length();rollbackReportLen=report.length();
        valid=changed=skipped=correct=persistenceRight=markovRight=alwaysStill=overrides=eventCount=windowEvents=0;
        older=previous=oldActual=-1;gravityReady=false;windowMax=0;lastEventAt=0;inferenceSumNs=inferenceMaxNs=0;nanos.clear();
        active=true;stageStartedAt=SystemClock.elapsedRealtimeNanos();
        if(!manager.registerListener(this,sensor,SensorManager.SENSOR_DELAY_GAME)){active=false;line("SENSOR_REGISTRATION_FAILED");refresh();return;}
        line("\n=== START "+STAGES[stage]+" / learn="+LEARN[stage]+" ===");
        handler.postDelayed(tick,WINDOW_MS);refresh();
    }
    private final Runnable tick=new Runnable(){@Override public void run(){
        if(!active)return;
        if(SystemClock.elapsedRealtimeNanos()-stageStartedAt>TIMEOUT_NS){abort("TIMEOUT");return;}
        if(windowEvents==0||SystemClock.elapsedRealtimeNanos()-lastEventAt>1_500_000_000L)skipped++;
        else {
            int actual=classify(windowMax);
            if(oldActual>=0&&actual!=oldActual)changed++;
            if(older>=0&&previous>=0){
                TinyOrganism.Context ctx=new TinyOrganism.Context(MODES[stage],older,previous);
                int simple=previous,table=tablePredict(MODES[stage],previous);
                long begin=SystemClock.elapsedRealtimeNanos();
                TinyOrganism.Prediction p=brain.predict(ctx);
                long cost=SystemClock.elapsedRealtimeNanos()-begin;
                nanos.add(cost);inferenceSumNs+=cost;inferenceMaxNs=Math.max(inferenceMaxNs,cost);
                if(p.label==actual)correct++;if(simple==actual)persistenceRight++;if(table==actual)markovRight++;
                if(actual==0)alwaysStill++;if(p.label!=simple)overrides++;
                trace.append(stage+1).append(',').append(valid+1).append(',').append(MODES[stage]==0?"A":"B").append(',')
                    .append(TinyOrganism.CLASS_NAMES[older]).append(',').append(TinyOrganism.CLASS_NAMES[previous]).append(',')
                    .append(TinyOrganism.CLASS_NAMES[p.label]).append(',').append(TinyOrganism.CLASS_NAMES[table]).append(',')
                    .append(TinyOrganism.CLASS_NAMES[simple]).append(',').append(TinyOrganism.CLASS_NAMES[actual]).append(',')
                    .append(p.computedBlocks).append(',').append(p.skippedBlocks).append('\n');
                // Real Android next-window sensor label comes after forecast. No owner labels used as sensor truth.
                brain.observeSensor(actual,LEARN[stage]);
                if(LEARN[stage])markov[MODES[stage]][previous][actual]++;
                valid++;
            }
            older=previous;previous=actual;oldActual=actual;
        }
        windowEvents=0;windowMax=0;
        if(valid>=TARGET){finishStage();return;}refresh();handler.postDelayed(this,WINDOW_MS);
    }};
    private void ownerTeach(int label){
        if(!active||!LEARN[stage]||valid==0)return;
        try{brain.teachOwnerIntent(label);line("OWNER_TEACHING: "+(label==1?"attention":"ordinary")+" — intention only, not a sensor observation or Android permission");refresh();}
        catch(IllegalArgumentException e){line("OWNER_TEACHING_REJECTED: "+e.getMessage());}
    }
    private void finishStage(){
        if(!active)return;handler.removeCallbacks(tick);manager.unregisterListener(this);active=false;
        Collections.sort(nanos);
        long mean=nanos.isEmpty()?0:(inferenceSumNs/nanos.size())/1000L;
        long p95=nanos.isEmpty()?0:nanos.get((int)Math.ceil(nanos.size()*.95)-1)/1000L;
        long elapsed=(SystemClock.elapsedRealtimeNanos()-stageStartedAt)/1_000_000L;
        line("END "+STAGES[stage]+"; valid="+valid+"; changes="+changed+"; dropped="+skipped+"; events="+eventCount+"; time="+elapsed+"ms");
        line("TINY_F="+correct+"/80; PERSISTENCE="+persistenceRight+"/80; MARKOV="+markovRight+"/80; STILL="+alwaysStill+"/80; overrides="+overrides+"/80");
        line("K=2; computedBlocks=4; skippedBlocks=4; mean/p95/max="+mean+"/"+p95+"/"+(inferenceMaxNs/1000)+"µs; JavaHeapSnapshot="+((Runtime.getRuntime().totalMemory()-Runtime.getRuntime().freeMemory())/1024)+"KiB NOT PSS/energy");
        line("AUDIT_GATE: "+(changed>=8?"DIVERSITY_PASS":"INVALID_LOW_MOTION_DIVERSITY")+"; SENSOR_WEIGHT_COUNT="+brain.sensoryLearningCount()+"; ownerHints="+brain.ownerTeachingCount());
        int completed=stage+1;stage++;
        if(stage==4)loadedFromDiskThisActivity=false;
        checkpointStatus=commitCheckpoint()?"COMMIT_AND_READBACK_PASS / completed="+completed:"CHECKPOINT_ERROR";
        if(stage==4)line("Закрой и повторно открой приложение, затем запусти последний A.");
        if(stage==5)line("DEVICE RESEARCH PROTOCOL COMPLETE. This is not AGI and no external Android action was exercised.");
        line("CHECKPOINT "+checkpointStatus);refresh();
    }
    private void abort(String reason){
        if(!active)return;handler.removeCallbacks(tick);manager.unregisterListener(this);active=false;
        try{brain=TinyOrganism.restore(rollback);copyCountsInto(rollbackMarkov,markov);trace.setLength(rollbackTraceLen);report.setLength(rollbackReportLen);}catch(Exception e){corrupt=true;line("ROLLBACK_FAILURE "+e.getMessage());}
        line("ABORT "+STAGES[stage]+" reason="+reason+" partial predictions NOT committed; restart stage");
        refresh();
    }
    @Override protected void onPause(){if(active)abort("ACTIVITY_PAUSED");super.onPause();}
    @Override public void onSensorChanged(SensorEvent e){
        if(!active||sensor==null||e.sensor.getType()!=sensor.getType()||e.values==null||e.values.length<3)return;
        double x=e.values[0],y=e.values[1],z=e.values[2];
        if(!Double.isFinite(x)||!Double.isFinite(y)||!Double.isFinite(z))return;
        if(useGravityFilter){
            if(!gravityReady){gravity[0]=x;gravity[1]=y;gravity[2]=z;gravityReady=true;}
            for(int i=0;i<3;i++)gravity[i]=.92*gravity[i]+.08*e.values[i];
            x-=gravity[0];y-=gravity[1];z-=gravity[2];
        }
        double norm=Math.sqrt(x*x+y*y+z*z);
        if(!Double.isFinite(norm))return;
        windowMax=Math.max(windowMax,norm);eventCount++;windowEvents++;lastEventAt=SystemClock.elapsedRealtimeNanos();
    }
    @Override public void onAccuracyChanged(Sensor s,int accuracy){}
    private static int[][][] copyCounts(int[][][] old){int[][][] next=new int[2][3][3];copyCountsInto(old,next);return next;}
    private static void copyCountsInto(int[][][] a,int[][][] b){for(int i=0;i<2;i++)for(int j=0;j<3;j++)System.arraycopy(a[i][j],0,b[i][j],0,3);}
    private boolean commitCheckpoint(){
        try{
            JSONObject payload=new JSONObject();payload.put("stage",stage);
            payload.put("brain",Base64.encodeToString(brain.checkpoint(),Base64.NO_WRAP));
            JSONArray modes=new JSONArray();for(int[][] matrix:markov){JSONArray rows=new JSONArray();for(int[] row:matrix){JSONArray columns=new JSONArray();for(int v:row)columns.put(v);rows.put(columns);}modes.put(rows);}
            payload.put("markov",modes);payload.put("report",report.toString());payload.put("trace",trace.toString());
            String raw=payload.toString(),digest=TinyOrganism.sha256(raw.getBytes("UTF-8"));
            SharedPreferences prefs=getSharedPreferences(PREF,MODE_PRIVATE);
            if(!prefs.edit().putString(KEY,raw).putString(KEY_HASH,digest).commit())return false;
            String saved=prefs.getString(KEY,null),savedHash=prefs.getString(KEY_HASH,null);
            if(saved==null||savedHash==null||!saved.equals(raw)||!digest.equals(savedHash))return false;
            TinyOrganism round=TinyOrganism.restore(Base64.decode(new JSONObject(saved).getString("brain"),Base64.NO_WRAP));
            return Arrays.equals(round.checkpoint(),brain.checkpoint());
        }catch(Exception e){line("CHECKPOINT_FAILED "+e.getClass().getSimpleName()+" "+e.getMessage());corrupt=true;return false;}
    }
    private void loadCheckpoint(){
        SharedPreferences prefs=getSharedPreferences(PREF,MODE_PRIVATE);
        String raw=prefs.getString(KEY,null),digest=prefs.getString(KEY_HASH,null);
        if(raw==null)return;
        try{
            if(digest==null||!TinyOrganism.sha256(raw.getBytes("UTF-8")).equals(digest))throw new IllegalStateException("SHA256 mismatch");
            JSONObject payload=new JSONObject(raw);int found=payload.getInt("stage");
            if(found<0||found>5)throw new IllegalStateException("bad stage");
            TinyOrganism restored=TinyOrganism.restore(Base64.decode(payload.getString("brain"),Base64.NO_WRAP));
            JSONArray counts=payload.getJSONArray("markov");if(counts.length()!=2)throw new IllegalStateException("markov modes");
            for(int i=0;i<2;i++){JSONArray rows=counts.getJSONArray(i);if(rows.length()!=3)throw new IllegalStateException("markov rows");
                for(int j=0;j<3;j++){JSONArray cells=rows.getJSONArray(j);if(cells.length()!=3)throw new IllegalStateException("markov cells");
                    for(int k=0;k<3;k++){int value=cells.getInt(k);if(value<0||value>1000000)throw new IllegalStateException("markov range");markov[i][j][k]=value;}}}
            String rr=payload.getString("report"),tt=payload.getString("trace");
            if(rr.length()>200000||tt.length()>200000)throw new IllegalStateException("saved report too large");
            report.setLength(0);report.append(rr);trace.setLength(0);trace.append(tt);
            brain=restored;stage=found;checkpointStatus=restoreStatus="PASS_SHA256 / completed="+stage+" / hash="+digest.substring(0,16);
            loadedFromDiskThisActivity=true;
        }catch(Exception e){corrupt=true;restoreStatus="CHECKPOINT_CORRUPT / "+e.getClass().getSimpleName();checkpointStatus="CORRUPT — refusing to overwrite";}
    }
    private void resetResearch(){
        if(active)return;
        getSharedPreferences(PREF,MODE_PRIVATE).edit().remove(KEY).remove(KEY_HASH).commit();
        brain=new TinyOrganism(0x7a07L);stage=0;for(int[][] m:markov)for(int[] row:m)Arrays.fill(row,0);
        report.setLength(0);report.append("UNO-N0-07 / owner explicitly reset this research experiment\n");
        trace.setLength(0);trace.append("stage,index,mode,older,prev,model,markov,persistence,actual,executedBlocks,skippedBlocks\n");
        corrupt=false;loadedFromDiskThisActivity=false;checkpointStatus="NO_CHECKPOINT_YET";restoreStatus="OWNER_RESET";
        line("RESET complete for org.unovyra.n007 only");refresh();
    }
}
