---
id: INV.CI.OPENCODE-CONSUMER-WINDOWS-BLOCKS
status: active
governs: product
decision: DEC.2026-08-25.NPM-DIST-TAG-PROMOTION
check: tests/ci/test_unica_workflow.py::test_windows_smoke_blocks_the_release
scope: [ci]
supersedes: [INV.CI.OPENCODE-CONSUMER-SMOKE]
---

# Windows-потребитель блокирует выпуск

У Windows дымовой работы нет `continue-on-error`, а promotion требует
её успех в условии запуска: без зелёного Windows-потребителя
потребительский dist-tag не двигается.
