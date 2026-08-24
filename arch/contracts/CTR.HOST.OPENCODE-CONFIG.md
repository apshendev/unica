---
id: CTR.HOST.OPENCODE-CONFIG
status: active
governs: product
version: 1
decision: DEC.2026-08-24.OPENCODE-ADAPTER-DELIVERY
producer: plugins/unica/opencode/index.js
consumers: [host, review, docs]
check: tests/ci/test_opencode_adapter.py::test_the_adapter_takes_ownership_of_mcp_unica_and_preserves_neighbours
scope: [host, pkg]
---

# Конфигурация OpenCode получает упакованные скиллы и владельца mcp.unica

Конфигурационный хук добавляет упакованный корень скиллов в `skills.paths`
ровно один раз, сохраняя прочие пути и URL
(tests/ci/test_opencode_adapter.py::test_the_packaged_skills_root_is_appended_once_and_others_survive).
Запись `mcp.unica` замещается всегда: local, enabled, timeout 900000 мс,
команда — упакованный bootstrap `run --plugin-root <корень пакета>`; прочие
MCP-записи сохраняются. Окружение процесса получает
`UNICA_RUNTIME_CACHE_DIR`/`UNICA_PROVIDER_STATE_DIR`: существующие значения
процесса выигрывают, иначе адреса выводятся из домашнего каталога кеша
пользователя в OpenCode-специфичной области
(tests/ci/test_opencode_adapter.py::test_existing_process_overrides_win_over_derived_locations).
