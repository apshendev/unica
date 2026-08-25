---
id: INV.CI.OPENCODE-CONSUMER-LINUX-BEST-EFFORT
status: active
governs: product
decision: DEC.2026-08-25.NPM-DIST-TAG-PROMOTION
check: tests/ci/test_unica_workflow.py::test_linux_smoke_is_best_effort
scope: [ci]
supersedes: [INV.CI.OPENCODE-CONSUMER-SMOKE]
---

# Linux-потребитель — best effort

Linux дымовая работа сохраняет `continue-on-error: true`, promotion
включает её в needs, чтобы отчёт о сбое дожил до агрегатного гейта, но
результат Linux в условии promotion не проверяется.
