---
id: INV.PKG.VERSION-LOCKSTEP
status: active
governs: product
decision: DEC.2026-08-24.OPENCODE-ADAPTER-DELIVERY
check: tests/ci/test_version_contract.py::test_every_contract_location_declares_the_same_version
scope: [pkg, product]
---

# Версия поставки едина во всех контрактных местах

Cargo workspace, оба host-манифеста, запись `unica` в `tools.lock.json` и
npm-пакет `@apshendev/unica-opencode` объявляют одну допустимую версию
выпуска; бампер обновляет все места одной операцией
(tests/ci/test_version_contract.py::VersionBumpContractTests::test_bump_updates_the_npm_package_version_too)
и не оставляет частичной записи при сбое
(tests/ci/test_version_contract.py::VersionBumpContractTests::test_a_render_failure_leaves_every_contract_file_untouched).
