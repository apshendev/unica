---
id: INV.CI.OPENCODE-CONSUMER-INSTALLED-ROOT
status: active
governs: product
decision: DEC.2026-08-25.NPM-DIST-TAG-PROMOTION
check: tests/ci/test_unica_workflow.py::test_the_consumer_installs_the_exact_registry_version
scope: [ci]
supersedes: [INV.CI.OPENCODE-CONSUMER-SMOKE]
---

# Потребитель ставит точную registry-версию с доказуемым корнем

Блок установки обоих дымовых потребителей ставит
`@apshendev/unica-opencode@<version>` через `npm install --ignore-scripts`
в изолированном каталоге и подключает пакет абсолютным `file://` URI;
команда `opencode plugin` не используется, и checkout исходников плагина
доказательством содержимого публикации не является.
