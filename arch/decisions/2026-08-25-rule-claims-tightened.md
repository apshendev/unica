---
id: DEC.2026-08-25.RULE-CLAIMS-TIGHTENED
status: active
governs: product
realized: tests/arch/test_registry.py::test_the_ten_widened_rules_are_replaced_by_narrow_successors
superseded-by: null
establishes: [INV.PKG.VERSION-DECLARED-LOCKSTEP, INV.PKG.VERSION-BUMP-COMPLETE, INV.PKG.VERSION-BUMP-ATOMIC, CTR.HOST.OPENCODE-MCP-OWNERSHIP, CTR.HOST.OPENCODE-SKILLS-PATHS, CTR.HOST.OPENCODE-STATE-PROCESS-OVERRIDES, CTR.HOST.OPENCODE-STATE-XDG-DERIVATION, CTR.HOST.OPENCODE-STATE-WINDOWS-DERIVATION, INV.HOST.OPENCODE-PLATFORM-REFUSAL, CTR.PKG.CORE-PROVENANCE-BY-BUILD-INPUT, CTR.PKG.CORE-PROVENANCE-DEFAULT-ADDRESSES, CTR.PKG.CORE-PROVENANCE-REFUSED-BY-MISMATCH, INV.HOST.OPENCODE-CLIENT-FLOOR-DOCUMENTED, INV.HOST.OPENCODE-SINGLE-CONFIG-HOOK, CTR.PKG.NPM-CANDIDATE-COMPOSITION, INV.PKG.NPM-CANDIDATE-DEV-MANIFEST-REFUSED, INV.PKG.NPM-CANDIDATE-VERSION-REFUSED, INV.PKG.NPM-CANDIDATE-BOOTSTRAP-REFUSED]
design: docs/design/2026-08-25-rule-claims-tightened-design.md
---

# Сужение заявок правил до доказанного

**Решение.** Семь записей, чья формулировка была шире их единственной
проверки, заменены штампами на узких преемников; каждая новая запись
заявляет один независимо нарушаемый контракт с одним фальсифицируемым
адресом проверки. Вместе с тремя npm-записями, суженными решением
DEC.2026-08-25.NPM-DIST-TAG-PROMOTION, все десять расширительных записей
ревью закрыты; целостность отображения держит агрегатный тест, являющийся
`realized` этого решения.

**Почему.** Запись, заявляющая больше проверенного, утверждает то, что
сборка может опровергнуть (DEC.2026-08-19.RULE-CLAIMS-ONLY-WHAT-IT-CHECKS).
Наблюдаемая форма контрактов не меняется: сужаются заявки записей, а не
поведение — положительный выбор платформы, умолчания происхождения ядра,
происхождение общей поставки, происхождение npm-источников и отсутствие
потолка версий клиента остаются прозой решений.

**Цена.** Реестр вырос на восемнадцать преемников, и часть прежних
гарантий перешла в прозу: читатель обязан различать доказанное адресом и
обещанное решением. Атомарность бампа доказывается только после снапшота
байтов всех пяти локаций; оба теста версий сразу зелёные — дефектом было
отсутствие доказательства, а не поведение.

**Что не меняется.** Тела заменённых записей и их исторические адреса
проверок, идентичность MCP-сервера, поверхность `unica.*`, наблюдаемая
форма всех контрактов.
