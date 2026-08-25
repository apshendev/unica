---
id: INV.PKG.NPM-CREDENTIAL-SPLIT
status: active
governs: product
decision: DEC.2026-08-25.NPM-DIST-TAG-PROMOTION
check: tests/ci/test_unica_workflow.py::test_opencode_promotion_credentials_are_isolated_from_publishing
scope: [pkg, ci]
supersedes: []
---

# Токен promotion изолирован от публикации

Работа публикации не получает npm-токенов ни на каком уровне;
promotion читает NODE_AUTH_TOKEN только в шаге promotion из секрета
окружения `npm-promotion` и объявляет это окружение. Scope токена и защита
Environment — живое evidence внешнего этапа настройки, статической заявкой
не являются.
