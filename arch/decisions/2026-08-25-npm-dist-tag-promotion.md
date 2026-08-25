---
id: DEC.2026-08-25.NPM-DIST-TAG-PROMOTION
status: active
governs: product
realized: tests/ci/test_unica_workflow.py::test_opencode_npm_publication_stages_smokes_then_promotes
supersedes: [DEC.2026-08-25.NPM-TRUSTED-PUBLICATION]
superseded-by: null
establishes: [INV.PKG.NPM-STAGING-DIST-TAG, INV.PKG.NPM-PUBLICATION-FORK-TAG-OIDC, INV.CI.NPM-FORK-ONLY-CONTOUR, INV.PKG.NPM-CREDENTIAL-SPLIT, INV.PKG.NPM-REGISTRY-VISIBILITY, INV.PKG.NPM-PROMOTION-FORWARD-ONLY, INV.PKG.NPM-PROMOTION-IDEMPOTENT, INV.PKG.NPM-RERUN-BYTE-IDENTITY, INV.CI.OPENCODE-CONSUMER-INSTALLED-ROOT, INV.CI.OPENCODE-CONSUMER-WINDOWS-BLOCKS, INV.CI.OPENCODE-CONSUMER-LINUX-BEST-EFFORT]
design: docs/design/2026-08-25-npm-dist-tag-promotion-design.md
---

# npm-выпуск OpenCode: stage → потребители → promotion

**Решение.** Публикация `@apshendev/unica-opencode` только этапирует
кандидата под служебным dist-tag `staging`, после чего bounded-опрос
реестра подтверждает видимость этой версии с побайтовым совпадением.
Потребительские теги двигает отдельная работа `promote-opencode-npm`:
она выполняется после дымовых потребителей, работает в окружении
`npm-promotion`, читает npm-токен только на уровне шага из секрета
`NPM_PROMOTION_TOKEN` через `NODE_AUTH_TOKEN`, двигает ровно один
dist-tag (`latest` для stable, `next` для prerelease), только вперёд по
SemVer, идемпотентно, и никогда не публикует.

**Почему.** Публикация и продвижение — разные уровни доверия: staged байты
должны видеть только smoke-потребители, а потребительский тег двигается
лишь после их зелёного отчёта. Разделение секретов делает каждую работу
минимально привилегированной: publish не знает npm-токенов, promotion не
умеет публиковать. Порядок `publish → smoke → promotion` доказывается
агрегатным тестом, являющимся `realized` этого решения; отдельная запись
на порядок не заводится.

**Цена.** Одноразовая служебная версия `0.0.0-bootstrap.1` под dist-tag
`bootstrap`: без существующего пакета реестр не отдаёт `dist-tags`,
которые читает promotion. Процедура — release-runbook; сборка
bootstrap-версии и живая настройка доверия — внешний этап 7. Pipeline не
удаляет тег и runtime-ассеты — это обязательство прозы, статически
недоказуемое. Не включать npm «disallow tokens», пока promotion использует
токен.

**Что не меняется.** Двухфазная публикация маркетплейсов, идентичность
MCP-сервера, упаковка кандидата и поверхность `unica.*`.
