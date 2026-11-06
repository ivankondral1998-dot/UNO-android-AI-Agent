# ASTRA 12 — неизвестные входы, способы определения и блокеры

Это реестр необходимых измерений, а не запрос остановить текущую работу. Формулы и протоколы выданы; неизвестные числа нельзя получить из числа параметров. До отдельного разрешения производственная реализация не начинается.

## 1. Минимальные входы для принятия следующего решения

|Символ / единица|Как получить|Допустимая область / кандидат|Чувствительность / правило решения|Блокирует production?|
|---|---|---|---|---|
|D_task, распределение задач|обезличенный согласованный каталог реальных RU задач, strata07|конечные длины 01; все 12 направлений обязательны|смена распределения меняет качество и оптимальный размер|Да|
|q_j,c_j,r_j, доли|утверждение product contract до test|кандидаты 07; все в[0,1]|границы feasible-set; не оценивать после просмотра test|Да|
|N_train,e, events|лицензированный manifest по modalities|≥0; сценарии 03 не минимально достаточные объёмы|compute линейно по N_e; качество нелинейно/неизвестно|Да|
|rights_e / разрешения|договор/лицензия/consent для каждого source|train/distribute/derive отдельно true/false|нет права→quarantine, без нужной modality нет её training gate|Да|
|μ_i,σ_i, DSP units|статистика train-only аудио, fixed normalization|σfloor10^-3|изменяет все audio features; hash/version binding|Да для export|
|tokenizer merges / bytes|детерминированный train-only BPE|V32768 с byte fallback|влияет на length/MAC/RUquality; не встраивать произвольный словарь|Да для weights|
|SKU/RAM/SoC/OSbuild|A52 device inventory без secrets|не считать все A52 одинаковыми|выбор backend и memorycap|Да|
|R_cap / MiB|app limit, sustained peakPSS measurement|512MiB только unapproved candidate|∂R/∂P=2bytesFP16 до overhead; coldpeak отдельно|Да|
|r_MAC / MAC/s|primitive sweep shapes/q/format/temperature|>0, неизвестен|latency нижняяграница C/r; сравниватьполные paths|Да|
|r_BW / bytes/s|cold/warm memory traffic benchmarks|>0, неизвестен|dense recurrence/vocab могут быть bandwidth-bound|Да|
|B_backend,B_capture,B_driver / bytes|instrumented allocations+PSS/driver report|≥0, нет честной конечной численнойграницы изархива|каждыйбайтдобавляется peak; неопределённостьнеобнулять|Да|
|θ_m,θ_b,θ_d,θ_i / J perunit|power-meter paired primitive experiments, identifiable design|≥0; coefficient intervals|J линейно по features только после validation модели|Да для energyclaim|
|P_idle / W|matched1h/24h standby,screen/radio controlled|≥0; .2Wincremental только candidatecap|ΔJ=ΔP×duration; standby может доминировать|Да|
|L_control,L_OS / ms|priority dispatch/readback/STOP probes, processkill|≥0, operation-specific|без servicebound нет hard stoplatency; только empiricalquantile|Да|
|A_tx,A_fs / свойства|fault injection atallcommit boundaries, crash/reboot|pass/fail underdeclared filesystem/OS|без atomicity replayproof неприменим|Да|
|ν entropy/antirollback profile|CSPRNG health/error handling; separateanchorassessment|P128 probabilitybound;COUNTERoptional|exactnonrollback невыводитсяиз Keystore|Да для strongerthreatclaim|
|WER/MOS/grounding/success / метрики|independent locked stratified tests aftertraining|unknown;candidate thresholds07|невыводятсяиз d; отсутствие data→REQUIRES_DATA|Да|
|R-observability / доля|полныйжурнал eligibleattempts, включая unknown|[0,1]|qYconditional; qR qYverifiedjointfrequency|Да для calibration|
|forgetting Δ / доля|pairedretention/delaybattery,newv/Pablations|[-1,1]|localPdescent необеспечивает populationgain|Да для adaptiveclaim|
|GPU r_eff / FLOP/s;VRAM / bytes|training primitive microbenchmark+actualpeak|>0, неизвестно|t=F/r;L7activation scalesBLK|Да для trainingcommitment|
|training budget / hours,J,currency|доступный hardware/time envelope|≥0; noassumedcloudaccount|rejecttrialifreservedcostexceedsbudget|Да|
|toolchain/backend hashes|проверенные localpackages послевыбора equipment|exactversion+SHA; candidates07|изменениеопов/rounding требует parityredo|Да|
|λcost,normcaps,κthresholds|predefineddevgrid/quality-resourcePareto|defaults01–03, frozenbeforetest|могутсделать familyinfeasible; не authoritysettings|Да для finalmanifest|
|NCR θ_i,cost_i,Δyield|isolatedequal-total-costA/B/C/D|probabilities[0,1], cost≥0|surrogatebreak-even06; mayloseafterfitcost|Да для NCRsuperiority, не baseUNO|
|commercial support/licensecost|pilotincidents,permitteddistribution review|unknown, nonnegative|C_support07, nosales/ROIclaimwithoutinputs|Да для releaseeconomics|

## 2. Что математически невозможно определить однозначно

**Минимальный достаточный d.** Пусть доступны только shapes и одни и те же наблюдения до момента действия. Мир W0 требует action0, W1 требует action1; оба согласуются с архивом. Любая фиксированная политика ошибётся хотя бы в одном. Из parametercount нельзя выбрать достаточнуюархитектурубез domain/targets/data. Это доказанный non-identification blocker M08; увеличение d самопосебеего не устраняет.

**Энергия телефона.** Один и тот же список MAC может исполняться на backend с разной памятью,частотой,ожиданием итемпературой. Варьируя idlewait, получаем разнуюэнергиюприодинаковых MAC. Поэтому никакоечисло J неопределеноиз W2/R5; нужны R6coefficients илинепосредственно full-taskmeasurement.

**Причинный успех и missing outcomes.** Два мира могут дать одни итеже verifiedreceipts,норазные unobserved outcomes. q_R невыдумывает missinglabels; произведение q_Rq_Y описывает observablejointendpoint. Causality требует controlleddesign илиидентифицирующихпредпосылок.

**Восстановление утраченного произвольного знания.** Если нетдостаточного reference, collisions erasure mapping запрещаютоднозначный repair. Контрактформыданных не содержитзначениявсехутраченныхфактов.

Эти ограничения закрыты доказательствами/контрпримерами, а не временно оставлены «на потом». Эмпирические вопросы ниже отличаются: их можно проверить, но здесь нетсоответствующихданных/устройства/обучения.

## 3. Conservative decision без передачи архитектурного выбора разработчику

Исследовать B2-512→B2-1024→B2-1536 на полном функциональном наборе; d2048 — расширенный контроль, LR2/H2 — заранее выведенные альтернативы при ресурсном/контекстном провале. Выбирать по feasible-set02, не объявлять d1024 каноном. Until empirical gates: noautonomousprivilegedrelease; exacttypedconfirmation/controller обязательны, unknown необучает P, noNCRautopromotion, nohardwareantirollbackclaim.

Первый внешний шаг после утверждения документов — получить task/rights/device/trainingbudget inputs и разрешённую минимальную калибровку. Если лицензированныхданныххотябыоднойобязательной modality нетилиресурсный feasible-set пуст, возвращать конкретный BLOCKED снарушеннымнеравенством. Не запускатьмаленькийклассификаторподназваниемполного UNO.

## 4. Полный критерий окончания данной работы

Теоретическая работа может закончиться, когда исправленные уравнения самосогласованы в stated domain, все D01–D10 имеют алгоритмы/ABI/зависимости/оракулы, независимый финальный reread не оставляет известных критических противоречий либо фиксирует конкретный непреодолённый blocker. Это не равняется G2/G4 implementation approval или commercial release. Финальный verdict после audit находится в ASTRA_FINAL_README_AND_DECISION.md; при выявлении нерешённой ошибки он обязан быть FAIL независимо отобъёмапакета.
