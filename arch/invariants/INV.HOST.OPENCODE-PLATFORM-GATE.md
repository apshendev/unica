---
id: INV.HOST.OPENCODE-PLATFORM-GATE
status: active
governs: product
decision: DEC.2026-08-24.OPENCODE-ADAPTER-DELIVERY
check: tests/ci/test_opencode_adapter.py::test_unsupported_platforms_fail_during_initialization
scope: [host, platform]
---

# OpenCode-адаптер выбирает только поддерживаемые цели

Адаптер запускает bootstrap только для Windows x64 и Linux x64; macOS и
неподдерживаемые архитектуры получают явный отказ при инициализации, а не
запуск чужого бинарника.
