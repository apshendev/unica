---
id: INV.HOST.OPENCODE-CLIENT-FLOOR
status: active
governs: product
decision: DEC.2026-08-25.OPENCODE-CONSUMER-SMOKE
check: tests/ci/test_package_unica_opencode.py::test_the_candidate_documents_a_version_floor_not_a_ceiling
scope: [host, docs]
---

# Пол клиента OpenCode задокументирован, а не потолок

Кандидат документирует минимальную версию OpenCode `1.18.22 or newer` и не
запрещает более новые: код адаптера не ограничивает версии OpenCode сверху.
Потребители выпуска фиксированы отдельным правилом
INV.CI.OPENCODE-CONSUMER-SMOKE.
