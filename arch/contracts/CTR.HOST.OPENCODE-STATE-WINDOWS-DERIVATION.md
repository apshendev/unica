---
id: CTR.HOST.OPENCODE-STATE-WINDOWS-DERIVATION
status: active
governs: product
version: 1
decision: DEC.2026-08-25.RULE-CLAIMS-TIGHTENED
producer: plugins/unica/opencode/index.js
consumers: [host, docs]
check: tests/ci/test_opencode_adapter.py::test_windows_locations_derive_from_localappdata
scope: [host, pkg]
supersedes: [CTR.HOST.OPENCODE-CONFIG]
---

# На Windows адреса состояния выводятся из LOCALAPPDATA

На Windows незаданные адреса кеша и состояния выводятся из `LOCALAPPDATA`
пользователя.
