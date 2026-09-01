---
id: CTR.HOST.OPENCODE-REFERENCE-ACCESS
status: active
governs: product
version: 1
decision: DEC.2026-09-01.OPENCODE-PACKAGED-REFERENCE-ACCESS
producer: plugins/unica/opencode/index.js
consumers: [host, review, docs]
check: tests/ci/test_opencode_adapter.py::test_existing_permission_rules_survive_and_gain_the_references_rule
scope: [host, pkg]
---

# Точечное разрешение packaged references в external_directory

После конфигурационного хука `permission.external_directory` — карта, в
которой `<package-root>/references/*` имеет значение `allow` ровно один раз.
Правила потребителя для остальных путей сохраняются; строковая политика
потребителя остаётся правилом `"*"`. Права на остальной пакет и внешние
каталоги адаптер не открывает.
