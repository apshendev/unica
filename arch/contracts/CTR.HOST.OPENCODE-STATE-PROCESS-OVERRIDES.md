---
id: CTR.HOST.OPENCODE-STATE-PROCESS-OVERRIDES
status: active
governs: product
version: 1
decision: DEC.2026-08-25.RULE-CLAIMS-TIGHTENED
producer: plugins/unica/opencode/index.js
consumers: [host, docs]
check: tests/ci/test_opencode_adapter.py::test_existing_process_overrides_win_over_derived_locations
scope: [host, pkg]
supersedes: [CTR.HOST.OPENCODE-CONFIG]
---

# Существующие переопределения процесса выигрывают у выведенных адресов

Окружение процесса получает `UNICA_RUNTIME_CACHE_DIR` и
`UNICA_PROVIDER_STATE_DIR`: уже заданные процессом значения не
перезаписываются выведенными адресами кеша и состояния.
