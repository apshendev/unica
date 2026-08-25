---
id: CTR.HOST.OPENCODE-MCP-OWNERSHIP
status: active
governs: product
version: 1
decision: DEC.2026-08-25.RULE-CLAIMS-TIGHTENED
producer: plugins/unica/opencode/index.js
consumers: [host, review, docs]
check: tests/ci/test_opencode_adapter.py::test_the_adapter_takes_ownership_of_mcp_unica_and_preserves_neighbours
scope: [host, pkg]
supersedes: [CTR.HOST.OPENCODE-CONFIG]
---

# Конфигурационный хук владеет записью mcp.unica

Запись `mcp.unica` замещается всегда: local, enabled, timeout 900000 мс,
команда — упакованный bootstrap `run --plugin-root <корень пакета>`;
соседние MCP-записи сохраняются.
