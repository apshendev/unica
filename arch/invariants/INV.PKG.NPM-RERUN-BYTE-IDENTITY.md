---
id: INV.PKG.NPM-RERUN-BYTE-IDENTITY
status: active
governs: product
decision: DEC.2026-08-25.NPM-DIST-TAG-PROMOTION
check: tests/ci/test_publish_unica_opencode.py::test_a_rerun_is_accepted_only_with_identical_registry_bytes
scope: [pkg, ci]
supersedes: [INV.PKG.NPM-RERUN-INTEGRITY]
---

# Повторная публикация успешна только при побайтовом совпадении

Повторный прогон принимает уже опубликованную версию лишь когда
тарболл реестра побайтово равен кандидату; расхождение байтов — отказ. Сбой
npm без опубликованной версии остаётся сбоем без восстановления
(tests/ci/test_publish_unica_opencode.py::test_a_publish_failure_without_a_published_version_stays_failed).
