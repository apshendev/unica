---
id: INV.HOST.OPENCODE-PLATFORM-REFUSAL
status: active
governs: product
decision: DEC.2026-08-25.RULE-CLAIMS-TIGHTENED
check: tests/ci/test_opencode_adapter.py::test_unsupported_platforms_fail_during_initialization
scope: [host, platform]
supersedes: [INV.HOST.OPENCODE-PLATFORM-GATE]
---

# Неподдерживаемые платформы получают явный отказ

Адаптер отказывает в инициализации на macOS и неподдерживаемых
архитектурах, а не запускает чужой бинарник. Положительный выбор
поддерживаемых целей — проза решения об адаптере.
