---
id: CTR.HOST.OPENCODE-STATE-XDG-DERIVATION
status: active
governs: product
version: 1
decision: DEC.2026-08-25.RULE-CLAIMS-TIGHTENED
producer: plugins/unica/opencode/index.js
consumers: [host, docs]
check: tests/ci/test_opencode_adapter.py::test_locations_are_derived_from_the_cache_home_when_unset
scope: [host, pkg]
supersedes: [CTR.HOST.OPENCODE-CONFIG]
---

# Незаданные адреса состояния выводятся из домашнего каталога кеша

Когда процесс не задаёт адреса кеша и состояния, они выводятся из
домашнего каталога кеша пользователя в OpenCode-специфичной области.
