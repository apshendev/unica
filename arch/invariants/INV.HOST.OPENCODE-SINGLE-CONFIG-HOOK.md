---
id: INV.HOST.OPENCODE-SINGLE-CONFIG-HOOK
status: active
governs: product
decision: DEC.2026-08-25.RULE-CLAIMS-TIGHTENED
check: tests/ci/test_opencode_adapter.py::test_the_module_exports_one_plugin_whose_only_hook_is_config
scope: [host, wire]
supersedes: [INV.HOST.OPENCODE-SHARED-SURFACE]
---

# Модуль адаптера выставляет один плагин с единственным хуком config

Модуль адаптера экспортирует один плагин, чей единственный хук — `config`.
Происхождение общей поставки и отсутствие нативных обёрток OpenCode —
проза решения об адаптере.
