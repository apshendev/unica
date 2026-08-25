---
id: INV.PKG.NPM-STAGING-DIST-TAG
status: active
governs: product
decision: DEC.2026-08-25.NPM-DIST-TAG-PROMOTION
check: tests/ci/test_publish_unica_opencode.py::test_stable_and_prerelease_publish_under_the_staging_dist_tag
scope: [pkg, ci]
supersedes: [INV.PKG.NPM-PUBLICATION-GATE]
---

# Стадирование публикуется только под служебным dist-tag

Публикация npm-кандидата всегда выходит под служебным dist-tag
`staging` — и stable, и prerelease; потребительские `latest`/`next` на этом
шаге не двигаются. Агрегатный тест прогоняет оба варианта через subTest и
проверяет точное значение тега в аргументах публикации.
