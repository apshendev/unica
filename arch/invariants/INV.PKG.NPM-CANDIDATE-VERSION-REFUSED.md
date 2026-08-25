---
id: INV.PKG.NPM-CANDIDATE-VERSION-REFUSED
status: active
governs: product
decision: DEC.2026-08-25.RULE-CLAIMS-TIGHTENED
check: tests/ci/test_package_unica_opencode.py::test_a_version_that_disagrees_with_the_source_is_refused
scope: [pkg]
supersedes: [INV.PKG.NPM-CANDIDATE-FROM-THIN-ROOT]
---

# Рассинхрон версии не становится кандидатом

Тонкий корень, чья версия манифеста расходится с версией выпуска,
отвергается до вызова npm.
