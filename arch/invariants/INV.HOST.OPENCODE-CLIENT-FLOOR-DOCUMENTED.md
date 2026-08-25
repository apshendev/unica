---
id: INV.HOST.OPENCODE-CLIENT-FLOOR-DOCUMENTED
status: active
governs: product
decision: DEC.2026-08-25.RULE-CLAIMS-TIGHTENED
check: tests/ci/test_package_unica_opencode.py::test_the_candidate_documents_a_version_floor_not_a_ceiling
scope: [host, docs]
supersedes: [INV.HOST.OPENCODE-CLIENT-FLOOR]
---

# Пол клиента OpenCode задокументирован

Кандидат документирует минимальную версию OpenCode `1.18.22 or newer` и
описывает перезапуск и первый запуск. Отсутствие потолка версий — проза
решения: код адаптера версии OpenCode не ограничивает.
