---
id: INV.PKG.NPM-PUBLICATION-GATE
status: active
governs: product
decision: DEC.2026-08-25.NPM-TRUSTED-PUBLICATION
check: tests/ci/test_unica_workflow.py::test_opencode_npm_publication_is_fork_gated_and_trusted
scope: [pkg, ci]
---

# npm-выпуск идёт только из тегового пуша форка через OIDC

Работа публикации npm-кандидата выполняется после успешной публикации и
повторной проверки runtime-ассетов, только на теговый пуш и только в
репозитории `apshendev/unica`; аутентификация — trusted publishing без
долгоживущего токена. Литерал владельца одинаков в workflow, скрипте
публикации и агрегатном гейте; upstream ожидает эту работу пропущенной
(tests/ci/test_evaluate_ci_gate.py::EvaluateCiGateTests::test_the_fork_expects_npm_publication_and_upstream_skips_it).
