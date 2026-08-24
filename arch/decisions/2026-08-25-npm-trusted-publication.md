---
id: DEC.2026-08-25.NPM-TRUSTED-PUBLICATION
status: active
governs: product
realized: tests/ci/test_unica_workflow.py::test_opencode_npm_publication_is_fork_gated_and_trusted
supersedes: []
superseded-by: null
establishes: [INV.PKG.NPM-PUBLICATION-GATE, INV.PKG.NPM-RERUN-INTEGRITY]
design: docs/design/2026-08-25-npm-trusted-publication-design.md
---

# npm-выпуск OpenCode-кандидата — trusted publishing за гейтом форка

**Решение.** Публикацию `@apshendev/unica-opencode` выполняет отдельная
работа релизного workflow — только на теговый пуш, только из репозитория
`apshendev/unica`, только после публикации и повторной проверки runtime-ассетов.
Аутентификация — короткоживущий OIDC-токен npm trusted publishing
(`id-token: write`, npm ≥ 11.5); долгоживущий npm-токен в репозитории не
появляется вовсе. Скрипт публикации перепроверяет репозиторий, событие, ref,
идентичность пакета и согласованность версий до первого вызова npm.

**Почему.** Форк владеет своим npm-именем, upstream — нет: тот же файл
workflow на upstream обязан пропускать эту работу, поэтому гейт репозитория
есть и в условии работы, и в агрегатном гейте, и в самом скрипте — литерал
один и тот же во всех трёх копиях. Повторный прогон частично опубликованного
выпуска — штатный случай: уже опубликованная версия принимается только при
побайтовом совпадении тарболла реестра с кандидатом; расхождение или сбой npm
оставляют выпуск красным, не трогая тег и ассеты.

**Цена.** Одноразовый ручной шаг владельца пакета: связать trusted publisher
(`apshendev/unica` + `unica-plugin-release.yml`) с пакетом в интерфейсе npm до
первого релиза. Каталоги Codex и Claude Code и их продвижение не затронуты.

**Что не меняется.** Двухфазная публикация маркетплейсов, идентичность
MCP-сервера, упаковка кандидата и поверхность `unica.*`.
