---
id: CTR.PKG.CORE-PROVENANCE-DEFAULT-ADDRESSES
status: active
governs: product
version: 1
decision: DEC.2026-08-25.RULE-CLAIMS-TIGHTENED
producer: scripts/ci/package-unica-plugin.py
consumers: [review, docs]
check: tests/ci/test_package_unica_plugin.py::test_generated_marketplace_is_thin_pinned_and_target_neutral
scope: [ci, pkg]
supersedes: [CTR.PKG.CORE-PROVENANCE-SELECTABLE]
---

# Вызов без входа порождает прежние адреса умолчания

Умолчание — `https://github.com/IngvarConsulting/unica`: вызов упаковщика
без явного входа порождает прежние адреса `source`/`release` манифеста и
прежние адреса ассетов ядра и движка от их умолчательных репозиториев и
тегов.
