---
id: INV.PKG.NPM-PROMOTION-IDEMPOTENT
status: active
governs: product
decision: DEC.2026-08-25.NPM-DIST-TAG-PROMOTION
check: tests/ci/test_promote_unica_opencode.py::test_an_already_promoted_version_is_idempotent
scope: [pkg, ci]
supersedes: []
---

# Повторный promotion — no-op

Когда целевой dist-tag уже указывает на версию кандидата, promotion
не выполняет ни одной записи и завершается успехом.
