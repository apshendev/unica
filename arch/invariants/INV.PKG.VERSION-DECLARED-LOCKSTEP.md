---
id: INV.PKG.VERSION-DECLARED-LOCKSTEP
status: active
governs: product
decision: DEC.2026-08-25.RULE-CLAIMS-TIGHTENED
check: tests/ci/test_version_contract.py::test_every_contract_location_declares_the_same_version
scope: [pkg, product]
supersedes: [INV.PKG.VERSION-LOCKSTEP]
---

# Версия поставки едина во всех контрактных местах

Cargo workspace, оба host-манифеста, запись `unica` в `tools.lock.json` и
npm-пакет `@apshendev/unica-opencode` объявляют одну допустимую версию
выпуска: статическое равенство всех пяти мест проверяется одним прогоном.
