# Локальный `.tgz` из tag-run выпуска: исполняемая процедура

- Date: `2026-08-25`
- Status: `approved`
- Decision: `none — no architectural contract changed`

Процедура заменяет шаг 4 документа
`docs/plans/2026-08-25-opencode-local-test-fix-steps.md` после блокера шага 5:
run `32766639619` оказался PR-run ветки `fix/issue-627-external-source-readers`,
а не выпуском, и его манифест называл пересобранные PR-байты вместо байтов
релиза `v0.12.0`.

## Правило выбора входа

Тонкий артефакт для локального теста выпуска берётся только из run, чей head
SHA совпадает с `targetCommitish` релиза. Одного совпадения
`pluginVersion`/`release.tag` в манифесте недостаточно: PR-run после релиза
несёт те же значения версии, но другие байты ассетов.

## Для выпуска v0.12.0

1. Проверить run перед скачиванием: run `31950933025` — event `push`, branch
   `v0.12.0`, head SHA `6f2acb27ee47b559e782003a62ac9abf8f4c7d71` — тот же,
   что `targetCommitish` релиза `v0.12.0`.

   ```powershell
   gh run view 31950933025 --repo IngvarConsulting/unica --json event,headBranch,headSha
   gh api repos/IngvarConsulting/unica/releases/tags/v0.12.0 --jq .target_commitish
   ```

2. Скачать thin-артефакт:

   ```powershell
   gh run download 31950933025 --repo IngvarConsulting/unica --name unica-thin-marketplace --dir .build/opencode-local/thin
   ```

## Обязательный префлайт до упаковки

Сравнить три manifest SHA (`darwin`/`linux`/`win`) в
`.build/opencode-local/thin/plugins/unica/runtime-manifest.json` с `digest`
ассетов релиза `v0.12.0`; все три должны совпасть.

Красный сигнал закреплён живым прогоном: артефакт старого run `32766639619`
даёт 3/3 mismatch — `dc090553…`/`e8fb673f…`/`c0bb6b3e…` против
`d1fc9ffe…`/`fdea1e1f…`/`3fc92984…`; правильный артефакт run `31950933025`
даёт 3/3 match. Mismatch означает неверный вход: остановиться и сообщить,
другой run самостоятельно не выбирать.

## Сборка и потребитель

Затем — сборка `.tgz` и шаги потребителя как в steps-файле
(`docs/plans/2026-08-25-opencode-local-test-fix-steps.md`, шаги 4–5):
`package-unica-opencode.py` от thin-корня, пустой consumer,
`npm install --ignore-scripts`, изолированный env, проверки
`verify-skills`/`verify-mcp`. `.build/` и `dist/` не коммитить.
