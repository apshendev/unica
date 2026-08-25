---
id: INV.PKG.NPM-CANDIDATE-BOOTSTRAP-REFUSED
status: active
governs: product
decision: DEC.2026-08-25.RULE-CLAIMS-TIGHTENED
check: tests/ci/test_package_unica_opencode.py::test_a_thin_root_without_a_bootstrap_is_refused
scope: [pkg]
supersedes: [INV.PKG.NPM-CANDIDATE-FROM-THIN-ROOT]
---

# Тонкий корень без bootstrap не становится кандидатом

Тонкий корень без bootstrap поддерживаемой цели отвергается до вызова npm.
