---
id: INV.CI.OPENCODE-CONSUMER-SMOKE
status: active
governs: product
decision: DEC.2026-08-25.OPENCODE-CONSUMER-SMOKE
check: tests/ci/test_unica_workflow.py::test_opencode_consumer_smoke_gates_the_release
scope: [ci]
---

# Дымовые потребители OpenCode гейтят теговый выпуск

Теговый выпуск форка проверяют потребители npm-пакета: изолированный вне
checkout потребитель подключает пакет точной версии выпуска, наблюдения
собираются в его каталоге, а верификация запускается из checkout. Windows x64
блокирует выпуск, Linux x64 — best effort, macOS-job OpenCode-потребителя
отсутствует.
