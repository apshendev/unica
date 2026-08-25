---
id: INV.PKG.NPM-REGISTRY-VISIBILITY
status: active
governs: product
decision: DEC.2026-08-25.NPM-DIST-TAG-PROMOTION
check: tests/ci/test_publish_unica_opencode.py::test_a_successful_publish_waits_for_registry_visibility
scope: [pkg, ci]
supersedes: [INV.PKG.NPM-RERUN-INTEGRITY]
---

# Успешная публикация подтверждается видимостью в реестре

После успешной публикации выполняется bounded-опрос точной версии с
побайтовой сверкой тарболла: timeout ожидания, не-JSON ответ, не-URL
строка и расхождение байтов фатальны; rerun-ветка сверяет те же байты тем
же механизмом. Все сценарии идут subTest'ами одного агрегатного теста.
