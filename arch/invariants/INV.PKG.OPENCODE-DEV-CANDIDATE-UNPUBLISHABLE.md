---
id: INV.PKG.OPENCODE-DEV-CANDIDATE-UNPUBLISHABLE
status: active
governs: product
decision: DEC.2026-08-25.OPENCODE-LOCAL-DEBUG-RUNTIME
check: tests/ci/test_publish_unica_opencode.py::test_a_local_debug_candidate_is_refused_before_publish
scope: [pkg]
---

# Local-debug кандидат не доходит до npm publish

Стадирование с маркером `opencode/local-debug.json` или с development-манифестом
отвергается до первого npm-вызова: ни publish, ни опрос реестра не происходит.
