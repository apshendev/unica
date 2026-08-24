---
id: INV.HOST.OPENCODE-SHARED-SURFACE
status: active
governs: product
decision: DEC.2026-08-24.OPENCODE-ADAPTER-DELIVERY
check: tests/ci/test_opencode_adapter.py::test_the_module_exports_one_plugin_whose_only_hook_is_config
scope: [host, wire]
---

# Адаптер OpenCode разделяет поверхность продукта

Модуль адаптера выставляет один плагин с единственным хуком `config`: скиллы и
сервер `unica.*` приходят из общей поставки, нативных инструментов-обёрток
OpenCode не появляется.
