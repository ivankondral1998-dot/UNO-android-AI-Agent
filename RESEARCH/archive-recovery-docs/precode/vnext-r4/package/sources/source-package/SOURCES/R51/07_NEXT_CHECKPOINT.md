# Контрольная точка после Grok Stage 2: R5.1

**Вход:** исходные оригинальные Astra/B2, R4, R5 candidate, новый полноформатный Stage 2 Grok. Все входы побайтно скопированы в sources/ и снабжены SHA-256.

**Выполнено:** прочитан full Stage2; статус каждого R1/R2, IR01–IR08, D01–D10, X01–X12, B01–B14 восстановлен; проанализированы доказательства/ограничения; IR01 доказательство уточнено и добавлен state-dependent counterexample; IR02 дан типизированный ABI-кандидат; не скрыты G1/G2/G3/G4 block.

**Минимальный следующий paper-only шаг, не требующий кредитов:**
1. Нормативно определённую и независимую от изменения истории версию W4 включить в отдельный draft ASTRA_02-ERRATA (не правя исходный архив); выдать точную гарантию same-mask, указать non-Lipschitz при selector switch.
2. Превратить memory draft из `03` в contract for data/index snapshots, затем adversarial re-audit raw/provenance/permission/expiry/ABA. Проверить, что `COMPLETE` невозможен после частичного scan; не вводить второй мозг.
3. Утвердить owner-stratum choice/thresholds для WAKE/SENSOR, owner identity, строгий offline provider boundary и family/mask trade-offs. Пока нет решения — держать как candidates, не подменять требования.
4. Только после owner decision + данные/измерения: выбрать family и d по quality + footprint + latency + energy (не MAC alone), создать model weights, OS gate tests, etc.
5. Вновь провести independent review исключительно над нормативными поправками, если они будут внесены. Повторять Stage1/Astra без новой необходимости не требуется.

**Запрещено:** full PRE-CODE BASELINE PASS, уменьшение UNO до пяти кнопок/малого классификатора, перенос старых Jarvis weights как runtime brain, cloud dependency, production code/repo changes/Actions/удаление исходников без отдельного решения владельца.

**Важный пользовательский контекст:** пользователя ограничивает финансовая возможность покупки Pro/кредитов, а не просто эмоциональное раздражение лимитами. Не предлагать дорогие режимы как обязательный путь. После «продолжай» выполнять доступные задачи до контрольной точки; различать данные проекта и историю взаимодействия.
