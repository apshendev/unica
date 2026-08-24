---
id: CTR.PKG.CORE-PROVENANCE-SELECTABLE
status: active
governs: product
version: 1
decision: DEC.2026-08-24.CORE-PROVENANCE-NAMED-BY-BUILD
producer: scripts/ci/package-unica-plugin.py
consumers: [review, docs]
check: tests/ci/test_package_unica_plugin.py::test_core_release_repository_override_names_the_fork_as_owner
scope: [ci, pkg]
---

# Происхождение ядра выбирается сборкой с одним умолчанием

Упаковщик принимает явный `--core-release-repository` и выводит из него каждый
адрес ассета ядра и идентичность `source`/`release` манифеста; происхождение
движков при этом не двигается. Умолчание —
`https://github.com/IngvarConsulting/unica`: вызов без входа порождает прежние
адреса и прежние байты
(tests/ci/test_package_unica_plugin.py::test_generated_marketplace_is_thin_pinned_and_target_neutral).
Bootstrap принимает тот же репозиторий при сборке через
`UNICA_BOOTSTRAP_CORE_REPOSITORY` и отвергает манифест, чей владелец ядра не
совпадает с названным
(crates/unica-bootstrap/tests/manifest_contract.rs::a_fork_core_manifest_is_refused_by_the_default_build).
Происхождение тулчейна выбираемым не является: третий адрес по-прежнему
требует новой записи реестра.
