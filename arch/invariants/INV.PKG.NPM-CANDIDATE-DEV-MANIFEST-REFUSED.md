---
id: INV.PKG.NPM-CANDIDATE-DEV-MANIFEST-REFUSED
status: active
governs: product
decision: DEC.2026-08-25.RULE-CLAIMS-TIGHTENED
check: tests/ci/test_package_unica_opencode.py::test_a_development_manifest_never_becomes_a_candidate
scope: [pkg]
supersedes: [INV.PKG.NPM-CANDIDATE-FROM-THIN-ROOT]
---

# Development-манифест не становится кандидатом

Тонкий корень с development-манифестом отвергается до вызова npm: ни один
npm-вызов не происходит.
