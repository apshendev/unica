---
id: CTR.HOST.OPENCODE-LAUNCH-MODES
status: active
governs: product
version: 1
decision: DEC.2026-08-25.OPENCODE-LOCAL-DEBUG-RUNTIME
producer: plugins/unica/opencode/index.js
consumers: [host, review, docs]
check: tests/ci/test_opencode_adapter.py::test_local_debug_marker_switches_to_direct_binary_launch
scope: [host, pkg]
---

# Маркер local-debug переключает запуск на упакованный бинарник

Валидный маркер `opencode/local-debug.json` меняет команду `mcp.unica` с
bootstrap на упакованный бинарник `bin/<target>/<unica(.exe)>` напрямую,
сохраняя владение записью, вывод окружения и timeout 900000 мс. Маркер, чья
цель расходится с целью хоста, отказывает при инициализации, не мутируя
конфигурацию. Без маркера действует `CTR.HOST.OPENCODE-MCP-OWNERSHIP`.
