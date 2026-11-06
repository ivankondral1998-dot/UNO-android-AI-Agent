# 09. Контракт будущей реализации — только после утверждения

Этот документ не поручает сейчас писать ядро. В этой работе production code, training, Android builds и изменения репозиториев не выполняются.

## 1. Типизированные интерфейсы

| Контракт | Вход → выход | Обязательство |
|---|---|---|
| ValidateObservation | bounded raw event → Valid(x) / INVALID | Не выделять по непроверенной длине; finite checks |
| Admit | metadata,state,budget → IDLE / ABSTAIN / WorkPermit | Полная цена выбора; reserve control |
| EncodeRead | x,s,g,M → z,readProvenance,cost | Полный bounded scan, не fake ANN |
| SharedF | h,z,blockMask,Θ → h',cost | D1, одни Φ_R на всех k; реальные пропуски блоков |
| Decode | h,P,schema → typed proposal / clarify / abstain | Logit ordering, bounded grammar, no authority |
| AuthorizeDispatch | proposal,current trusted state → ticket / deny | Linearization, owner/STOP/epoch/confirmation |
| NativeReadback | trusted ticket → observed state / UNKNOWN | Источник независим от текста модели |
| Verify | schema predicate,prestate,receipt,readback → Evidence | Completion отдельно от attribution |
| CommitExperience | fresh Evidence,current P,frozen trace → committed / stale / error | MarkUsed+P+receipt атомарно |
| Restore | authenticated snapshot → fresh generation+validated state / safe mode | Pending не восстанавливается |
| LabEvaluate | capability-free candidate,budget → typed metrics | No production access; timeout/censor explicit |
| Promote | reviewed artifact,independent/device evidence,owner decision → new signed version | Никогда не автоматический self-update |

Model ABI: digest конфигурации включает V,d,b,χ,J,m,A,H, формы, токенизатор, schema, нормирование, norms, quant format, DSP и numerical conventions. Несовместимый modelVersion запрещает смешивать memory/traces без проверенной миграции.

Для M при смене representation-version: либо replay/re-encode исходных validated данных новым Θ, либо quarantine/clear вычислимых embeddings с сохранением provenance/raw records. Без такого правила косинусная близость старого key и нового query не имеет согласованного смысла.

## 2. Математические oracle и контрольные данные

Это спецификации, не уже запущенные тесты.

| Oracle | Вход | Точный ожидаемый результат |
|---|---|---|
| O1 scalar contraction | F(h)=0.5h,α=.5,h0=1,full mask | h1=.75; hk=.75^k; cap≤1 |
| O2 fairness counterexample | F=0,d=2,mask=(1,0),h0=(1,1),α=1 | h1=(0,1), никогда (0,0) |
| O3 norm distinction | W=[[.8,.8],[0,0]] | max element .8; induced infinity norm1.6; capγ=.9 FAIL |
| O4 local plasticity | h=1,P=0,l0=0,y=1,λ=0,ε=.01,η=.2,no cap | q=.5; P'=10/101≈.0990099; BCE уменьшается |
| O5 no update | То же, но UNKNOWN/stale/STOP/replay | P'=P ровно; не нулевой псевдо-gradient |
| O6 budget | B_work=100,c_final=20,c_abort=5,step=30 | ≤2 steps; третий запрещён (60+30+25>100) |
| O7 restore identity | ticket(ν=7,e=0),restore→ν=8 | Старый ticket STALE даже при совпавших serial/h |
| O8 same-value ambiguity | Native TRUE,но external interference | taskEvidence TRUE, attribution UNKNOWN/OBSERVATIONAL |
| O9 saturation | logits48.742,54.835 | Выбирается индекс1 по logits |
| O10 regeneration | Четыре ручных входа 06 §5 | c2 outputs согласно таблице; c1/c1b FAIL на контрпримерах |
| O11 finite-pool sampling | N=2,π=(.25,.75),b=2 | inclusion p=(7/16,15/16); IPW expectation равен full-pool mean |
| O12 zero successes | N=10,Nsuccess=0,J=3 | extended energy/success=+∞; success-rate0,не NA |
| O13 prior solved goal | predicate true до отправки | SATISFIED_NOOP,не новая action success-label |
| O14 key replay | Смена v меняет W_k/W_q | Старая M quarantine либо пересчёт,не незаметное смешение |

При finite precision сравнение реальных чисел использует error bounds для конкретного dtype, но logical statuses/ids/guards должны быть точными. Gradient finite differences проверяются away from nondifferentiable boundaries; сами finite differences не доказывают глобальную формулу.

## 3. Порядок будущей приёмки

1. Утвердить область задач, формализм и открытые пороги без утверждений о product-ready.
2. Зафиксировать model ABI, trusted threat model и resource counters. Отдельно доказать/проверить generation и transaction backend.
3. Реализовать математический reference только после разрешения, сверить с O1–O14 и аналитическими теоремами. Отрицательные сценарии обязательны.
4. Offline dataset/training всех Θ, matched baselines (table, fixed network, recurrent family, при необходимости attention).
5. Проверить full held-out capabilities: ASR, TTS intelligibility, grounded commands, multi-step tasks, retention, calibration, resource Pareto. Малая классификация не заменяет эти наборы.
6. Затем Android интеграция и device tests с реальными permissions/readback/STOP, offline verification, joules/PSS/thermal/latency.
7. Лишь отдельным исследованием NCR-EVO A/B/C/D; никакого автоматического переноса в рабочий продукт.

GitHub Actions, merge, публикация и изменения JarvisLab не подразумеваются ни одним пунктом этого документа. Для них требуется отдельное прямое поручение.

## 4. Решение по уже открытому PR #3

PR не является обязательным фундаментом нового F. Его полезно сохранить как исторический host-reference и источник регрессий O7/O9, но нельзя переносить TrustBoundary.restore-семантику в новое ядро. Его code-fixes, если будут поручены, выполняются отдельно от данного математического пакета; PR здесь не изменялся.

## 5. Незавершённые внешние операции после restart

Новая generation запрещает learning старым ticket, но не повтор физического эффекта. Для неидемпотентного действия с UNKNOWN после crash автоматически повторять dispatch запрещено: сначала operation-specific readback/reconciliation либо новое информированное owner-решение. Идемпотентность и idempotency-key объявляются schema, а не угадываются моделью. Retry≤3 касается только доказанно безопасных для повтора failures; UNKNOWN не расходуется как разрешение ещё одной попытки.
