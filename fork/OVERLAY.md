# Форк-оверлей unica

- Date: 2026-09-11
- Status: active
- Decision: none — форк-контур, не архитектурный контракт upstream

## Зачем

Форк использует плагин unica только в opencode и рядом с ним держит два
внешних контура с более высоким приоритетом:

- **MCP `vrunner`** (vanessa-runner 3.0) — runtime-домен: сборка, загрузка,
  выгрузка, конвертация, DT, расширения, проверки, фоновые задания;
- **глобальные скиллы `yaxunit-testing` / `vanessa-testing`** с субагентами
  `unit-test-writer`, `vanessa-researcher`, `vanessa-writer` — тестирование.

Роль самого unica — source-домен: `view/apply/resolve/search/check/diff/docs`.

## Как устроено

Git-дерево форка не расходится с upstream. Все правки декларированы в
[`overlay.json`](overlay.json) и применяются скриптом
[`scripts/fork/apply_overlay.py`](../scripts/fork/apply_overlay.py) к
staged-копии упаковки (`package-unica-opencode.py` вызывает его перед
`npm pack`; флаг `--no-fork-overlay` отключает). Несовпадение anchor —
exit 1 со списком правил: после рефакторинга upstream синк не пройдёт тихо.

Глоссарий:

- **форк-оверлей** — декларативный набор правок, применяемый при сборке
  пакета; git-дерево остаётся merge-чистым.
- **runtime-домен** — операции над живой ИБ и артефактами; владелец — vrunner.
- **source-домен** — редактирование XML-исходников; владелец — unica.
- **глобальный тест-контур** — скиллы `yaxunit-testing`/`vanessa-testing`
  и их субагенты в `~/.config/opencode`.

Мини-решение (ADR-форма): overlay при сборке выбран вместо прямых коммитов,
потому что upstream активно переписывает SKILL.md и правки в 30+ файлах
конфликтовали бы на каждом merge; overlay с semantic anchors переживает
рефакторинг и падает громко, а не тихо. Альтернатива (коммиты в дерево)
отвергнута из-за цены сопровождения sync-процедуры.

## Что делает оверлей

1. Удаляет скилл `test-authoring` (пересечение с глобальным тест-контуром).
2. Заменяет абзац INV-MCP-RUNTIME-RECEIPT на vrunner-маршрутизацию
   (26 файлов + epf-bsp-init дважды).
3. Снимает запреты прямых вызовов: "Do not call internal …", "Execution path
   … skill-local …", «Не обходи контракт прямым runner-ом», «MCP-first
   discipline», donor-команды xdto, аналогичные клаузы code-search,
   code-diagnostics, meta-info, cfe-diff, source-access, epf/erf-init.
4. Перенаправляет остаточные упоминания `unica.runtime.execute` на `vrunner`.
5. Чистит ссылку api-design на test-authoring; EPF-сборку ведёт на
   `vrunner_epf_compile`.
6. Safety-правила не трогает: auth probe, connection string, лицензии,
   «не подменяй логическую цель физическим путём», поддержка, `dryRun`-дисциплина.

## Снимок счётчиков (2026-09-11, upstream 70a4402d)

| правило | совпадений |
| --- | --- |
| delete-test-authoring | 1 каталог |
| replace-runtime-contract-vrunner | 28 (27 файлов) |
| remove-do-not-call-single-line | 33 |
| remove-do-not-call-wrapped | 6 |
| remove-execution-path-scripts | 11 |
| remove-epf-erf-init-ban | 2 |
| remove-meta-info-ban | 1 |
| индивидуальные replace (cfe-diff, source-access, code-search ×2, code-diagnostics, xdto, db-auth-check, api-design, epf-bsp-init ×2, form-compile) | по 1 |
| strip-preferred-path-runtime-token | 20 |
| reroute-runtime-execute-token | 26 |
| reroute-runtime-execute-bare | 3 |

## Обновление форка

1. `git fetch upstream` → sync-ветка → merge (существующая процедура из
   docs/plans/2026-09-10-12-04-update-fork-upstream-sync.md).
2. `python scripts/fork/apply_overlay.py --root <staged-copy> --dry-run` —
   упавшие правила показывают, какой boilerplate переписал upstream.
3. Правка anchor в overlay.json, пересборка пакета, `opencode debug skill`.

CI и arch-записи upstream продолжают проверять нетронутое git-дерево и
остаются зелёными; расхождение живёт только в артефакте пакета.
