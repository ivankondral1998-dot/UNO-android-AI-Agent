# ASTRA 05 — доверенная Android-граница, DSP и материальный бюджет

## 1. Threat model и реализуемая граница

Допущения A_cap: Android kernel/permission system, controller/verifier и cryptographic primitives корректны; neural worker может выдавать произвольные bytes, зависать и портить собственное состояние. Root/kernel compromise, физический rollback всей trusted OS и эксплуатация неизвестной уязвимости controller не включены в доказательство. Network/cloud dependencies в runtime отсутствуют. Эти границы не означают, что система уже реализована.

Предкодовое решение: один интеллектуальный worker, общий Θ/F/s; узкий native/trusted controller в процессе приложения, worker в Android isolated process без permissions, файлов пользователя и сети. Binder принимает только bounded typed proposals/result tensors; exported=false, проверка caller identity и session handle. Контроллер не планирует задачи и не добавляет второй интеллект. OS permissions выданы только контроллеру. Любой ускоритель/backend, требующий incompatible shared permissions или неподконтрольного dynamic code, отклоняется до threat review.

STOP — atomic latch controller, проверяется при admission, каждом worker return и **linearization dispatch**. Worker не может задержать latch своим F. Доказательство: в переходах mutable worker нет операции OS dispatch; единственный dispatch path требует cap/consent/epoch/STOP. Следовательно при A_cap любые Θ/P не расширяют capability. STOP до linearization запрещает dispatch; после неё возможен already-in-flight эффект. L_stop≤L_controller_service+L_lock+L_gate измеряется; hard real-time на Android не выводится из формулы.

### Generation без выдуманного hardware counter

Primary deployment profile **P128**: каждый запуск/restore/model switch генерирует независимый 128-bit nonce ν из OS CSPRNG; ν не загружается из snapshot, pending handles не сериализуются в исполнимом виде. При Q запусках collision probability≤Q(Q−1)/2^129; например Q=10^9 даёт≈1.47·10^-21, но **не 0**. Без надёжной свежей entropy — SAFE_MODE. Точное deterministic no-rollback theorem относится только к дополнительному profile COUNTER с externally verified monotonic anchor. Наличие Android Keystore не доказывает такой counter. Старый authenticated model/snapshot replay может потерять недавнюю память; freshν препятствует оживлению старых tickets с указанной вероятностью, но не восстанавливает lost knowledge и не доказывает freshness самого model file.

Signed model manifest проверяется против pinned owner-approved key и approved version set. При полной rollback trusted storage freshness вне threat model P128; это явно открытый blocker для требования защиты от такого противника. OS Keystore/AES-GCM защищает snapshot confidentiality/authenticity при соответствующей key security; nonce96bits случайный с отдельным collision budget и AAD=(schema,modelDigest,slotGeneration), counters не восстанавливать для nonce reuse. Рекомендуется ограничить encryptions/key≤2^24 и rotate с new key; вероятность collision≤2^-49. Key compromise не покрывается. Источник: https://developer.android.com/privacy-and-security/keystore — поддержка secure hardware зависит от устройства; temporal authorization не равна общему anti-rollback.

## 2. Capability matrix — closed schema, расширяемый каталог

Все строки наследуют: exact args digest+owner consent scope+ν/e+unlocked policy; per-operation monotonic deadline; native prestate; endpoint rule01; FALSE только при полноценном sample, иначе UNKNOWN; no retry после crash для неидемпотентных effects. Pre/post evidence сохраняет observation time/source, не только boolean. Номера 0–23 ниже,24–127 RESERVED_DENY. Произвольный text не имя системного вызова. Новые verbs требуют schema/version/test, не neural mutation.

|ID/verb и args|OS gate / scope|Before→after readback; default timeout|Idempotence / partial/crash|
|---|---|---|---|
|0 ABSTAIN,1 CLARIFY,2 NOOP|нет mutation; внутренний вывод|NOOP только verified pre-predicate|не записывать action success|
|3 ANSWER(text≤4096tokens)|локальный UI|render completion≠истинность текста;5s|повтор UI допустим|
|4 SPEAK(text≤256tokens/chunk)|AudioTrack/audio focus; owner session|audio submission/end callback≠услышанная речь;15s|после crash не повторять длинную речь без запроса|
|5 LISTEN(duration≤10s)|RECORD_AUDIO, microphone FGS, foreground initiation|actual captured samples/permission;12s|partial buffer labelled, stop closes capture|
|6 READ_SCREEN|fresh MediaProjection session consent или явно включённая accessibility read scope|native image/UI snapshot, source/time;3s|повтор read safe; secure/unavailable surfacesUNKNOWN|
|7 READ_SENSORS(channel-set)|канал whitelist; permission если требуется|SensorEvent/native timestamp;2s|read only; missingmask|
|8 GET_VOLUME(stream)|AudioManager read|actual stream index/range;1s|read only|
|9 SET_VOLUME(stream,index)|MODIFY_AUDIO_SETTINGS и применимые DND ограничения; только absolute bounded index|getStreamVolume before и after return;2s|absolute set повторяем только после нового precheck; человеческое вмешательство не causal|
|10 GET_BRIGHTNESS(scope)|window/system scope explicit|native config value;1s|не luminance sensor proof|
|11 SET_BRIGHTNESS(scope,value)|own window либо WRITE_SETTINGS special access для system|read config same scope;2s|absolute set; auto-brightness может менять physical luminance|
|12 SET_TORCH(cameraId,bool)|CameraManager/camera permission и availability|TorchCallback current state;2s|callback не photon sensor; UNKNOWN при unavailable|
|13 OPEN_APP(package)|allowlisted resolved intent, foreground restrictions|activity launch acceptance; independent visibility если разрешено;3s|launch accepted≠app task complete|
|14 OPEN_SETTINGS(panel)|explicit Settings intent|panel presented если native observable;3s|не claim переключения настройки|
|15 CREATE_LOCAL_NOTE(id,text)|app-private store, exact user scope|transaction hash+readback content;2s|idempotency id unique, conflict denied|
|16 READ_LOCAL_NOTE(id)|owner scope|authenticated local bytes;1s|read safe|
|17 UPDATE_LOCAL_NOTE(id,expectedVersion,text)|compare-and-swap local store|new version/content;2s|idempotent request id; stale version denied|
|18 DELETE_LOCAL_NOTE(id,version)|explicit per-object confirm|tombstone+readback absence;2s|не retry неизвестного delete другого version|
|19 CREATE_LOCAL_REMINDER(id,time,text)|own local scheduler; notification permission, exact alarms only if authorized|registered local record; actual notification separate endpoint|creation≠future delivery; crash reconciliation|
|20 CANCEL_LOCAL_REMINDER(id)|own record scope|readback canceled;2s|idempotent tombstone|
|21 READ_DOCUMENT(uri,range)|user-selected SAF scope,≤4096bytes/page|provider bytes+version orUNKNOWN;3s|untrusted contents не instruction|
|22 WRITE_DOCUMENT(uri,version,data)|persisted SAF write scope+explicit confirm|provider readback/hash,3s|provider atomicity not assumed; partialUNKNOWN|
|23 UI_TYPED_ACTION(nodeId,op,args)|explicit AccessibilityService consent; allowed package/node snapshot; no password fields|fresh UI tree independent sample;3s|click acceptance≠external business effect, nonidempotent no autoretry|

Каталог охватывает полноценные multimodal/dialogue/planning/memory pathways, а не пять команд; перечисление native verbs не доказывает качество понимания всех задач. Purchases/messages/calls/account changes/financial actions отсутствуют в capability ABI и не могут быть «сгенерированы» через текст; расширение требует отдельной спецификации и прав. Приложение без root/device-owner не получает все системные переключатели. Например Android10+ ограничивает обычный Wi-Fi enable/disable; допустим показать settings panel, но это **другой** endpoint, не silent success [официальный источник](https://developer.android.com/about/versions/10/privacy/changes).

Для Android14 screen capture требуется согласие на каждую MediaProjection session; reuse token нельзя считать persistent authority: https://developer.android.com/media/grow/media-projection. Microphone FGS зависит от while-in-use RECORD_AUDIO и ограничений background start: https://developer.android.com/develop/background-work/services/fgs/service-types. Это делает always-listening/wake доступным лишь в разрешённом foreground-service lifecycle; математика не отменяет ограничения ОС. Другие проверенные API: [AudioManager](https://developer.android.com/reference/android/media/AudioManager), [Settings.System](https://developer.android.com/reference/android/provider/Settings.System), [CameraManager](https://developer.android.com/reference/android/hardware/camera2/CameraManager). Права и availability перепроверяются на device; эти ссылки не сертификат реализации.

## 3. Полный DSP contract

PCM16→x=sample/32768. Causal framing: end_f=160(f+1), frame512 samples x[end_f−512:end_f], negative indices zero. Для Nsamples>0 F=ceil(N/160), последний frame zero-padded справа до end_f; N=0→NO_AUDIO, не искусственный blank. Window sqrt-Hann (w_n=\sqrt{.5-.5\cos(2π(n+.5)/512)}), DFT convention Σx_n w_n exp(−2πikn/512), one-sided257 bins. Inverse scale1/512; mirrored spectrum enforces real waveform. За 10s F=1000; без initial left padding было бы другой framecount — версии несовместимы.

Fixed80 triangular mel filters between0 and8000Hz, mel(f)=2595log10(1+f/700),82 evenly spaced mel vertices; filter evaluated at FFT-bin frequency, peak1, **без** area normalization. Power magnitude²; feature \\(f_i=clip((log(10^{-6}+\sum_k H_{ik}|X_k|²)-\mu_i)/max(\sigma_i,10^{-3}),-4,4)/4\\). μ,σ computed only train split и locked in DSP manifest; без них export запрещён. TTS uses identical mel transform on synthesized previous-frame magnitude², starting previous magnitude all0. W_audio then receives80 values, а не 257-vector. RAW magnitude capMcap=512, logε=log10^-6; sigmoid stop отдельный 258 й output. Последовательность TTS: encode text chunk≤256tokens в sharedF, set mode SPEAK, one frame/event with previous generated mel, position metadata, emit max1000frames; stop if p_stop≥.5 after min1frame. Во время training previous true mel (teacher forcing), затем отдельная scheduled-feedback fine-tune; exposure bias measured, не exact deployment equality.

GL deterministic chunk/utterance decoder: предсказанные A[f,k] fixed; initialphase0; iterate16times: ISTFT with normalized overlap-add using denominator Σw_n² (zero denominator→0), STFT того же waveform, φ=argZ (при Z=0φ=0), Z←A exp(iφ). Final ISTFT, crop exact 160F samples, clip[-1,1], PCM round-to-nearest; начало/конец 5ms linear fade. Compute whole bounded utterance≤10s; это **не обещание** streaming low-latency TTS. Long text split по punctuation≤256tokens, каждый chunk независим, no invisible crossfade overlap. Качество phase recovery и стыков REQUIRES_DATA.

FFT radix2 reference bound: one complex FFT512 имеет(512/2)log2(512)=2304 butterflies; считать≤10 real arithmetic ops/butterfly (complex mul6+two complex adds4)→23040 realops. Real FFT может оптимизировать, upper reference использует complex form. ASR100frames/s: FFT≤2,304,000ops/s +80×257×100=2,056,000mel MAC/s+window/log/scalar ops. GL16iterations включает 16 STFT+16ISTFT и final ISTFT:33F FFTs→для F1000≤760,320,000real butterfly ops плюс framing/window/OLA/trig; это отдельный scalar/DSP ledger, не neural MAC. Memory estimates ниже резервируют complex/STFT buffers.

## 4. Матрицы и реальные пропуски

Для q активных blocks

\[
C_F(q)=Jq(2χbd+χb²),\quad C_{enc}(f,M)=2d²+df+32d+2md+2Mm,
\]
\[
C_{event}=C_{enc}+nb(2d+4)+K[C_F(q)+d]+dH_{exec}+Vd\,1_{text}+32.
\tag{R5}
\]

H_exec задаётся по пути: ASR128,TTS258,text0 (только vocab),image0 до final heads. Outcome candidate scoring: три scalar row dots W_p[a],P[a],W_R[a]→3d, risk/conf2d; verb stageAd. Не считать постоянно 902heads/аудиокадр. Event β update optional once atturn-end, если включена дополнительно 128d; table ниже её не включает. Key/value write2md/record+normalization/transaction; goal≤4096text-input events; proposal≤128 generation events+≤128canonical re-encode events и score. Все добавляются к task, не кпоследнему token.

Cache C z один раз: precompute Jqχbd MAC; каждый k потом Jq(χbd+χb²). При d1024,q16,K8:17,301,504×8=138,412,032 без cache; с cache8,388,608+8×8,912,896=79,691,776; cache Jqχb FP32=32768bytes. Valid only same z,Θ,mask; invalidation накаждом event. Cached path отдельный numerical parity oracle.

|d|text output fullK8 MAC/event|ASR fullK8 MAC/s|ASR K1,q=nb/4 MAC/s|256image patches fullK8 MAC|
|---:|---:|---:|---:|---:|
|512|54 161 472|3 749 075 200|294 969 600|9 671 032 832|
|1024|175 448 160|14 210 672 000|801 289 600|36 526 120 960|
|1536|364 908 672|31 489 651 200|1 623 820 800|80 833 708 032|
|2048|622 543 008|55 586 012 800|2 762 563 200|142 593 794 048|

Здесь memory full4096 scan накаждом event, uncached Cz, scalar/DSP/control/OS отдельно. При d1024 10s TTS neural=142,239,840,000MAC; GL отдельно. Эти верхние **path scenarios** не рекомендуют denseK8 на 100Hz. Sparse audio.801G MAC/s всё ещё требуетизмерений, a q/K qualityunknown. Если runtime не можетобработать 100fps, запрещено бесконечно накапливать audio: buffer10s, overflow→TRANSCRIPT_INCOMPLETE/CLARIFY, не action пообрезанномускрыто тексту.

## 5. RAM, storage, traffic

Все bytes делитьна 2²⁰для MiB. Базовые allocations:

|Объект|Обязательная квота|
|---|---:|
|Weights|B_Θ(format,packing), по 02 |
|P FP32|4Ad|
|M key/value/header|4096(4m+64)|
|FIFO FP16|2×256d|
|Pending frozen FP32 traces|32(4d+256), исправлено прежнее FP16trace assumption|
|Shared payload contents+index|4096×(4096+64)|
|L/U headers|2×8192×128|
|R/Q headers|1024×128+64×128|
|PCM10s|320000|
|Fixed workspace W|4[12d+2Jχd+V+4Mmax+2×258×1000+2×512×1000]|
|Image canonical+capture staging|256×256×4 + B_capture (real display buffer bounded separately)|
|Frozen compute snapshot M copy-on-write worst|4096(4m+64)+4Ad|
|WAL/staging/controller serialization reserve|8MiB+bounded current row/snapshot staging|

W резервирует 12d state vectors (включая saved goal state), C z/branch buffers, logitsV, memorysoftmax scratch, TTS spectra+complex frames. Decoder detailsmay require дополнительные buffers — входит B_backend, не hiddenzero. Workspace6.172MiB при d1024 — этот конкретный schedule. Raw counted weights+state+W=133.757917MiB, **до**payloadindex.25MiB, image.25MiB,capture,COW2.75MiB,WAL8MiB, backendpacking/duplicate/modelload/heap/controller. Такимобразом explicit subtotals d1024 FP16=145.007917MiB плюс capture+snapshot staging+backend/OS; INT8 вместо rawFP16 снижаетэтот subtotal на 52.480024MiB, но не гарантирует capacity или latency. PSS можетотличатьсяот mapped/allocatedbytes; accounting отдельно private resident+shared proportional+driver allocations.

Полнаяграница (R_{peak}≤B_{explicit}+B_{capture}^{max}+B_{snapshot}^{max}+B_{backend}^{max}+B_{controller}^{max}+B_{driver}^{max}+B_{pack}^{max}) имеетчисленныйсмысллишьпослеустановлениявсех max. Cold load можетодновременно держать compressed file,FP32 decoder и packedΘ: max3representations учитывать, либо запретитьтакой loader. Steady-state неравен coldpeak. Dataset и trainingVRAM неприбавляются runtime.

Disk cap candidate: model two versions2B_model +two snapshots2B_state +WAL8MiB +payload/index16.25MiB +logs≤16MiB +recovery baseline B_model +SBOM/manifests≤4MiB. Не дублировать payload в snapshot если externalreference; если snapshot включает payload, считатьдубли. Near-fullstorage→stopwrites/dispatch, ане unboundedlogs.

Memory traffic: lowerneed (B_{move}≥\max(B_{inputs},B_{outputs},B_{weights not cache-resident})); для conservative streaming schedule ≤Σprimitive(inputbytes+weightbytes+outputbytes+scale reads), включаяповторы K. Ниже bound неравен measuredDRAMtraffic из-за cache. d1024Fmatrices17,301,504elements →17.30MB INT8/step или 34.60MBFP16;8steps и 100fps=13.84GB/s INT8 weight-reads еслине cache-resident, до othertraffic. Cache Cz уменьшает Creads до one/event; q четверть уменьшает selectedrows, но kernelpacking/cachemisses могутсъестьвыигрыш. Fullvocabreads33.55MB INT8/outputtoken. Это важнееоднойтаблицы P.

## 6. Latency/energy/thermal и admission

Для primitive i с calibrated upper costs (mac_i,bytes_i,ops_i,time_i,energy_i), admission разрешает его толькоесли remaining≥cost_i+control_reserve+abort_reserve покомпонентно. Индукциядаёталгоритмический quota invariant. Physical joules не hardbound из estimatedlinearregression; runtimecounter/time/thermal stop используютнаблюдаемую telemetry, modelprediction лишь conservativeadmission.

\[
t_{task}≥\max(C_{MAC}/r_{MAC},B_{move}/r_{BW})+t_{serial},\quad
\hat J=θ_m C_{MAC}+θ_b B_{move}+θ_d C_{DSP}+θ_i B_{IO}+P_{idle}t+J_{OS/control}.
\tag{R6}
\]

Первое — roofline lowerbound при effective capacities, не latencyupper. Верхний bound требует perprimitive WCET+queuewait с assumptions. Coefficients θ≥0fit по nonnegative regression на heldoutprimitive combinations, noise/temperature/frequencystrata; reportpredictioninterval и maxresidual. Коллинеарные MAC/bytes неидентифицируютотдельныеθ: varyarithmetic intensity илииспользовать wholeprimitive lookup. Whbattery=capacity_Ah×voltage, usableJ=3600Wh×usable_fraction; fraction spent=Jtask/usableJ. Батарейнуюёмкостьконкретного A52 невыдумыватьизназвания.

Очередь: arrivalλ_e events/s, serviceμ_e measured; finitecapacity нетверифицирует stability. УсловиеΣλ_e E[t_e]<1 дляодног oworker — лишь necessary utilizationcheck иобычно sufficient толькопридополнительных queue assumptions. Deterministic admission требует burst b_e и servicecurve: backlog≤b+λT_service_latency при service rateμ>λ. Впротивномслучае explicitdrop/backpressure и coveragefailure. Stop/controlpriority отдельноот neuralqueue. Background microphone необходит OSlifecycle.

Calibrationbeforemaincode: толькоизолированные primitives/dummybuffers послеотдельногоразрешения, без UNO reasoningkernel. Sizesd512/1024/1536/2048, q{1,nb/4,nb}, K{1,2,4,8},FP16/INT8,cachewarm/cold, audioFFT,SQLitecommit,screenread,10/30minthermalsoak. Минимум 30repeats/condition плюс paired randomized order; reportmedian,p95,peakPSS,temperature,externalpower еслидоступно. Batterypercentage неподменяет calibratedjoulemeter. Idlebaseline1h и 24h, foregroundserviceon/off,screenmatched. Coefficients закрывают 12unknowns; доних A52PASS нет.

Candidate productcaps для review: runtimePSS≤512MiB, post-utterance responsep95≤2s, simplecontrolp95≤1s, speakingreal-timefactor≤1,incrementalstandby≤.2W, thermalstate без critical, falseactionUCB≤10^-4/issuedtask. Онинеизмереныинеутвержденывладельцем; немолчаливыйновый scope. Ifanypathfeasible-setempty→BLOCKED,сохранитьполныефункцииипересмотреть family/schedule/hardware.
