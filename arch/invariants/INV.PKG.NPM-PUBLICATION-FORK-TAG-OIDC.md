---
id: INV.PKG.NPM-PUBLICATION-FORK-TAG-OIDC
status: active
governs: product
decision: DEC.2026-08-25.NPM-DIST-TAG-PROMOTION
check: tests/ci/test_unica_workflow.py::test_opencode_npm_publication_is_fork_gated_and_trusted
scope: [pkg, ci]
supersedes: [INV.PKG.NPM-PUBLICATION-GATE]
---

# Стадирование идёт только из тегового пуша форка через OIDC

Работа публикации npm-кандидата выполняется после успешной публикации и
повторной проверки runtime-ассетов, только на теговый пуш и только в
репозитории `apshendev/unica`; аутентификация — trusted publishing с
`id-token: write`, без какого-либо npm-токена у работы. Литерал владельца
одинаков в workflow, скрипте публикации и агрегатном гейте.
