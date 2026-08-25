---
id: CTR.PKG.CORE-PROVENANCE-REFUSED-BY-MISMATCH
status: active
governs: product
version: 1
decision: DEC.2026-08-25.RULE-CLAIMS-TIGHTENED
producer: crates/unica-bootstrap
consumers: [review]
check: crates/unica-bootstrap/tests/manifest_contract.rs::ordinary_validation_uses_the_repository_compiled_into_the_bootstrap
scope: [ci, pkg]
supersedes: [CTR.PKG.CORE-PROVENANCE-SELECTABLE]
---

# Bootstrap отвергает манифест чужого владельца ядра

Bootstrap принимает тот же репозиторий при сборке через
`UNICA_BOOTSTRAP_CORE_REPOSITORY` и отвергает манифест, чей владелец ядра
не совпадает с названным.
