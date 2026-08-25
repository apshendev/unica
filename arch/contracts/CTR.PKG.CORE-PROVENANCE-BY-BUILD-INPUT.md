---
id: CTR.PKG.CORE-PROVENANCE-BY-BUILD-INPUT
status: active
governs: product
version: 1
decision: DEC.2026-08-25.RULE-CLAIMS-TIGHTENED
producer: scripts/ci/package-unica-plugin.py
consumers: [review, docs]
check: tests/ci/test_package_unica_plugin.py::test_core_release_repository_override_names_the_fork_as_owner
scope: [ci, pkg]
supersedes: [CTR.PKG.CORE-PROVENANCE-SELECTABLE]
---

# Явный вход сборки называет владельца происхождения ядра

Упаковщик принимает явный `--core-release-repository` и выводит из него
каждый адрес ассета ядра и идентичность `source`/`release` манифеста;
происхождение движков при этом не двигается.
