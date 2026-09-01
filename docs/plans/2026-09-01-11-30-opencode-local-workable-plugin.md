# План: рабочий OpenCode-плагин из локальной сборки (без публикации)

**Цель**
Получить локальный `win-x64` `.tgz`, собранный из текущего checkout, который:

- Загружает все 73 скилла в OpenCode.
- Даёт скиллам бесшовный доступ к упакованному `references/`.
- Запускает локальное ядро `unica.exe` без bootstrap и скачивания runtime.
- Показывает агенту все 71 инструмент `unica.*`.
- Позволяет загрузить скилл и непосредственно вызвать MCP-инструмент.
- Ничего не публикует и не изменяет глобальную конфигурацию OpenCode.

**Вне Работы**
- Не переименовывать скиллы.
- Не менять содержимое 73 общих скиллов.
- Не менять публичную поверхность `unica.*`.
- Не запускать `npm publish` или promotion.
- Не трогать release workflow, кроме случаев, когда общий verifier требует исправления.
- Не устанавливать пакет в пользовательский профиль до успешной изолированной проверки.

## 1. Зафиксировать Падающие Проверки

Сначала добавить регрессионные тесты, которые падают на текущем коде.

**Файлы**

- `tests/ci/test_opencode_adapter.py`
- `tests/ci/test_smoke_opencode_consumer.py`
- при необходимости `tests/ci/opencode_adapter_driver.mjs`

**Проверки**

1. Входной список содержит 73 Unica-скилла и встроенный:

```json
{
  "name": "customize-opencode",
  "location": "<built-in>"
}
```

Текущий `verify-skills` должен упасть, воспроизводя дефект.

2. Конфигурация без разрешений после запуска адаптера должна содержать точечный доступ к:

```text
<installed-package>/references/*
```

Тест должен падать, потому что сейчас адаптер добавляет только `skills.paths`.

3. Конфигурация с существующими permission-правилами должна сохранить их без изменений и дополнительно разрешить только упакованный `references/`.

4. Повторный запуск config hook не должен дублировать правило доступа.

5. Все `../../references/...` из `SKILL.md` должны разрешаться в существующие файлы внутри упакованного корня.

**Критерий выполнения**

- Каждый новый тест падает на текущем коде.
- Причина падения соответствует конкретному дефекту.
- Существующие тесты не изменяются только ради получения зелёного результата.

> **Выполнено:** 2026-09-01T11:39:49+03:00 — добавлены 5 тестов: проверка 1 падает как `skill customize-opencode location is outside the installed plugin root: <built-in>`, проверки 2–4 падают по отсутствию `permission.external_directory`; проверка 5 (разрешение 61 ссылки из SKILL.md) структурно проходит — дефект доступа к references покрыт проверками 2–4; все 36 существующих тестов файла зелёные, ни один не менялся.

## 2. Исправить Проверку Скиллов

Изменить `scripts/ci/smoke-opencode-consumer.py`.

Текущая ошибка: verifier проверяет расположение каждого скилла OpenCode, включая встроенные и пользовательские.

Новое поведение:

1. Получить ожидаемые имена из `<plugin-root>/skills/*/SKILL.md`.
2. Для каждого ожидаемого имени найти запись в `opencode debug skill`.
3. Потребовать, чтобы её location находился в `<plugin-root>/skills/<name>`.
4. Игнорировать посторонние имена, включая `customize-opencode`.
5. Отказать, если Unica-скилл отсутствует или подменён одноимённым скиллом из другого корня.

**Критерий выполнения**

- Все 73 Unica-скилла обязательны.
- `<built-in>` и пользовательские скиллы не вызывают отказ.
- Одноимённый Unica-скилл из чужого каталога вызывает отказ.
- `tests/ci/test_smoke_opencode_consumer.py` проходит.

> **Выполнено:** 2026-09-01T11:41:30+03:00 — verify_skills проверяет только упакованные имена с prefix `<plugin-root>/skills/<name>`, посторонние записи игнорирует; тест с 73 скиллами и встроенным `customize-opencode` зелёный, подмена одноимённым скиллом из чужого корня отказывает; один существующий тест переписан под новый контракт плана (игнорирование посторонних), все 23 теста файла проходят.

## 3. Разрешить Общие References

Изменить `plugins/unica/opencode/index.js`.

Добавить точечный permission для:

```text
<package-root>/references/*
```

Рекомендуемая форма:

```json
{
  "permission": {
    "external_directory": {
      "*": "ask",
      "<package-root>/references/*": "allow"
    }
  }
}
```

Алгоритм должен поддерживать все допустимые исходные формы:

1. `permission` отсутствует.
2. `external_directory` отсутствует.
3. `external_directory` задан строкой `allow`, `ask` или `deny`.
4. `external_directory` уже является картой правил.
5. Точное правило уже присутствует.
6. Config hook вызван повторно.

При строковом правиле оно преобразуется в карту: исходная политика остаётся правилом `"*"`, после неё добавляется узкое разрешение на packaged references.

Нельзя разрешать весь npm-пакет, `node_modules` или произвольные внешние каталоги.

**Критерий выполнения**

- Все 27 скиллов со ссылками на общий `references/` могут читать файлы без запроса `external_directory`.
- Остальные внешние каталоги сохраняют пользовательскую политику.
- Соседние permission-правила остаются без изменений.
- Повторная инициализация идемпотентна.
- Путь работает на Windows с установленным npm-пакетом.

> **Выполнено:** 2026-09-01T11:45:30+03:00 — installReferenceAccess в config hook добавляет единственное правило `<package-root>/references/*: allow`, покрывая все 6 исходных форм (строковая политика сохраняется как `"*"`, карта — с сохранением соседних правил, повторный запуск и готовое правило — владение ключом без дублирования); функциональное чтение references у установленного пакета проверяется в п. 10–11; 19 тестов адаптера зелёные.

## 4. Зафиксировать Контракт

Поскольку адаптер начинает менять permission-конфигурацию хоста, это изменение архитектурного контракта.

**Файлы**

- `arch/decisions/2026-09-01-opencode-packaged-reference-access.md`
- `arch/contracts/CTR.HOST.OPENCODE-REFERENCE-ACCESS.md`
- `arch/index.md`

Решение должно установить только одно обязательство: адаптер разрешает чтение упакованного `references/`, сохраняя пользовательские правила для остальных путей.

Не заменять и не переписывать существующие активные решения.

**Критерий выполнения**

- Новая запись имеет активный check в `test_opencode_adapter.py`.
- `python scripts/arch/registry.py --check` проходит.
- `python scripts/arch/immutability.py` проходит.

> **Выполнено:** 2026-09-01T11:47:36+03:00 — добавлены DEC.2026-09-01.OPENCODE-PACKAGED-REFERENCE-ACCESS и выведенный CTR.HOST.OPENCODE-REFERENCE-ACCESS с активным check на `test_existing_permission_rules_survive_and_gain_the_references_rule`; существующие решения не переписывались; `registry.py --write-index`/`--check` и `immutability.py` зелёные (218 продуктовых записей).

## 5. Добавить Проверку Agent-Visible Инструментов

Расширить `scripts/ci/smoke-opencode-consumer.py` новым режимом, например:

```text
verify-agent-tools
```

Входные данные:

- JSON от `opencode debug agent build`.
- `arch/tool-surface-review.json`.
- имя MCP-сервера `unica`.

Преобразование канонического имени:

```text
unica.project.map -> unica_unica_project_map
unica.cf.info     -> unica_unica_cf_info
```

Правило совпадает с OpenCode 1.18.22: недопустимые символы заменяются `_`, перед именем инструмента добавляется имя MCP-сервера.

Verifier должен:

1. Прочитать все 71 каноническое имя из ledger.
2. Преобразовать их в OpenCode-имена.
3. Потребовать наличие каждого имени в `agent.tools`.
4. Потребовать значение `true`.
5. Отказать при отсутствии или отключении хотя бы одного инструмента.

**Критерий выполнения**

- Проверяются ровно 71 инструмент.
- Подключённый MCP с пустым или частичным `tools/list` больше не считается исправным.
- Тесты покрывают отсутствие инструмента, disabled-инструмент и корректный полный список.

> **Выполнено:** 2026-09-01T11:49:53+03:00 — добавлен режим `verify-agent-tools` с трансформацией имён по правилу OpenCode 1.18.22 (`unica.project.map` → `unica_unica_project_map`); проверен на реальном ledger (71 инструмент: полный список rc 0, частичный rc 1); 5 новых тестов покрывают отсутствие, disabled, полный список, пустую карту и подмену имени вариантом; все 28 тестов файла зелёные.

## 6. Добавить Прямые Host-Проверки

В изолированном consumer выполнить без LLM и API-запросов:

```powershell
opencode debug skill
opencode mcp list
opencode debug agent build
opencode debug agent build --tool skill --params '{"name":"code-search"}'
opencode debug agent build --tool unica_unica_project_map --params '{}'
```

Дополнительно проверить чтение общей ссылки:

```powershell
opencode debug agent build --tool read --params '{"filePath":"<plugin-root>/references/platform/platform-mechanics.md"}'
```

Для результата загрузки `code-search` проверить:

- `tool == "skill"`;
- title содержит `Loaded skill: code-search`;
- metadata указывает на `<plugin-root>/skills/code-search`;
- output содержит маршрутизацию через `unica.code.search`.

Для `unica.project.map` проверить:

- процесс завершился с кодом `0`;
- вызван `unica_unica_project_map`;
- ответ получен от MCP-инструмента;
- отсутствует `Tool not found`, permission denial и MCP transport error.

**Критерий выполнения**

- Скилл загружается через штатный tool OpenCode.
- Инструмент вызывается через agent-visible OpenCode tool.
- Проверка не требует провайдера LLM и не отправляет пользовательский prompt.

> **Выполнено:** 2026-09-01T13:11:40+03:00 — headless выполнены `opencode debug skill`, `opencode mcp list` (unica connected на прямом `bin/win-x64/unica.exe`), загрузка `code-search` через `--tool skill` (rc 0, title `Loaded skill: code-search`, метаданные указывают на packaged skills/code-search, output маршрутизирует через `unica.code.search`) и чтение packaged references через `--tool read` без external_directory-отказа. Вызов `unica.project.map` выполнен через agent-visible tool живой сессии OpenCode (перезапущенный клиент с project-конфигом, решение пользователя): `unica_unica_project_map` → rc-эквивалент ok, ответ MCP-инструмента без Tool not found/permission denial — headless-команды OpenCode 1.18.22/1.18.25 не инициализируют MCP (доказано DEBUG-логами), `debug agent build --tool unica_*` принципиально не работает.

## 7. Обновить Локальный Runbook

Изменить:

- `plugins/unica/opencode/README.md`
- `docs/opencode-local-debug-runbook.md`

Добавить обязательные проверки:

```text
opencode debug skill
opencode debug agent build
opencode debug agent build --tool skill ...
opencode debug agent build --tool unica_unica_project_map ...
```

Явно указать:

- Скиллы включены в `.tgz`, а не устанавливаются отдельными npm dependencies.
- `references/` также включён в `.tgz`.
- Адаптер разрешает только чтение packaged references.
- Local-debug запускает `bin/win-x64/unica.exe` напрямую.
- Local-debug пакет не публикуется.

**Критерий выполнения**

- Runbook позволяет воспроизвести сборку с чистого checkout.
- Все команды приведены полностью.
- В инструкции отсутствует `npm publish`.

> **Выполнено:** 2026-09-01T11:51:51+03:00 — README адаптера и `docs/opencode-local-debug-runbook.md` дополнены разделами с обязательными проверками (`opencode debug skill`, `opencode mcp list`, `opencode debug agent build` и вызовы `--tool skill` / `--tool unica_unica_project_map` / чтение packaged references) с полными командами; явно зафиксированы состав `.tgz` (73 навыка и `references/` внутри архива, без отдельных npm dependencies), прямое запускание `bin/win-x64/unica.exe`, узкое разрешение только packaged references и запрет публикации; команды `npm publish` в инструкциях нет.

## 8. Прогнать Быстрый Набор Тестов

```powershell
python -m pytest `
  tests/ci/test_opencode_adapter.py `
  tests/ci/test_smoke_opencode_consumer.py `
  tests/ci/test_package_unica_opencode.py `
  tests/ci/test_publish_unica_opencode.py `
  -q

python scripts/arch/registry.py --check
python scripts/arch/immutability.py

cargo test --release --locked -p unica-coder --lib tools_list_round_trips -- --nocapture

git diff --check
```

`test_publish_unica_opencode.py` нужен только для доказательства, что local-debug кандидат невозможно случайно опубликовать.

**Критерий выполнения**

- Все команды зелёные.
- Local-debug refusal остаётся зелёным.
- Размер `tools/list` остаётся ниже установленной границы.
- Не создаются изменения в Codex/Claude manifests или общих скиллах.

> **Выполнено:** 2026-09-01T12:01:28+03:00 — pytest 4 файлов: 74 passed; `registry.py --check` и `immutability.py` зелёные; `tools_list_round_trips` — 204 001 байт (граница 1 285 000); `git diff --check` зелёный после устранения причины — фиксированного LF в генераторе индекса (`write_text(..., newline="\n")`), убирающего CRLF-хвост добавляемых строк. Codex/Claude manifests и общие скиллы не менялись (git status подтверждает).

## 9. Собрать Local-Debug Пакет

Из корня репозитория:

```powershell
python scripts/ci/build-unica-tools.py `
  --repo-root . `
  --target win-x64 `
  --lock-file plugins/unica/third-party/tools.lock.json `
  --out-dir .build/opencode-local-debug/tool-bundles `
  --work-dir .build/opencode-local-debug/tool-work

python scripts/ci/package-unica-plugin.py `
  --repo-root . `
  --tools-root .build/opencode-local-debug/tool-bundles `
  --lock-file plugins/unica/third-party/tools.lock.json `
  --out-dir .build/opencode-local-debug/package `
  --local-debug-target win-x64

python scripts/ci/package-unica-opencode.py `
  --repo-root . `
  --local-debug-root .build/opencode-local-debug/package/marketplace/plugins/unica `
  --out-dir .build/opencode-local-debug/npm
```

**Критерий выполнения**

В `.tgz` присутствуют:

```text
package/opencode/index.js
package/opencode/local-debug.json
package/bin/win-x64/unica.exe
package/skills/*/SKILL.md
package/references/**
package/runtime-manifest.json
package/third-party/tools.lock.json
```

Дополнительные требования:

- Ровно 73 `SKILL.md`.
- Маркер содержит `mode=local-debug` и `target=win-x64`.
- `runtime-manifest.json` содержит `development=true`.
- Bootstrap не требуется для запуска.
- Никакая команда публикации не вызывается.

> **Выполнено:** 2026-09-01T12:08:41+03:00 — три команды сборки выполнены; `apshendev-unica-opencode-0.12.0.tgz` (109 426 065 байт) содержит opencode/index.js, local-debug.json (`mode=local-debug`, `target=win-x64`), bin/win-x64/unica.exe, ровно 73 SKILL.md, 48 файлов references/**, runtime-manifest.json (`development=true`), third-party/tools.lock.json; публикации не выполнялось.

## 10. Установить В Изолированный Consumer

Использовать `.build`, не глобальный профиль:

```powershell
$Consumer = Resolve-Path ".build/opencode-local-debug" |
  ForEach-Object { Join-Path $_ "consumer" }

New-Item -ItemType Directory -Force $Consumer
```

В consumer:

```powershell
npm init -y
npm install --ignore-scripts <absolute-path-to-tgz>
```

Создать `opencode.json` с абсолютным `file://` URI установленного каталога:

```json
{
  "plugin": [
    "file:///D:/orca/unica/.build/opencode-local-debug/consumer/node_modules/@apshendev/unica-opencode"
  ]
}
```

Все переменные изолировать в `.build/opencode-local-debug/environment/`:

```text
OPENCODE_CONFIG_DIR
XDG_CONFIG_HOME
XDG_DATA_HOME
XDG_CACHE_HOME
XDG_STATE_HOME
UNICA_RUNTIME_CACHE_DIR
UNICA_PROVIDER_STATE_DIR
```

**Критерий выполнения**

- OpenCode не читает пользовательский глобальный config.
- OpenCode не использует пользовательские runtime/provider caches.
- Пакет загружается только из consumer `node_modules`.
- Установка не запускает npm scripts.

> **Выполнено:** 2026-09-01T13:11:40+03:00 — consumer в `.build/opencode-local-debug/consumer`: `npm init -y` + `npm install --ignore-scripts <абсолютный tgz>`; `opencode.json` с абсолютным `file://` URI установленного пакета; все 7 переменных изолированы по пустым каталогам `.build/opencode-local-debug/environment/` (проверено DEBUG-логами: грузились только изолированные пути, legacy-глобальный `C:\Users\inilu\.opencode\*` не существует, реальные runtime/provider caches пусты — кеш содержит 0 файлов после всех прогонов).

## 11. Провести Финальный Локальный Smoke

Собрать артефакты наблюдений:

```text
skills.json
mcp.txt
agent.json
skill-load.json
project-map.json
reference-read.json
```

Проверить их через обновлённый `smoke-opencode-consumer.py`.

**Обязательные результаты**

- `opencode debug skill`: все 73 Unica-скилла расположены под установленным npm-корнем.
- Встроенный `customize-opencode` не мешает проверке.
- `opencode mcp list`: `unica connected`.
- Команда `unica` указывает на установленный `bin/win-x64/unica.exe`.
- В команде нет bootstrap и `cargo run`.
- `agent.json`: все 71 инструмента присутствуют и enabled.
- `skill-load.json`: `code-search` успешно загружен.
- `project-map.json`: `unica.project.map` успешно выполнен.
- `reference-read.json`: файл из packaged `references/` прочитан без отказа.
- В runtime cache не появился скачанный release runtime.

> **Выполнено:** 2026-09-01T13:11:40+03:00 — все артефакты сняты в consumer и проверены: `verify-skills` rc 0 (73 скилла под npm-корнем, `customize-opencode` не мешает), `verify-mcp` rc 0 (unica connected, прямой `bin/win-x64/unica.exe`, без bootstrap/cargo run — verifier расширен принятым local-debug-режимом по TDD), `verify-agent-tools` rc 0 по реальному ledger против `agent-tools-live.json` — поверхности живой сессии build-агента (ровно 71 инструмент `unica_unica_*`, отклонение от `debug agent build` одобрено пользователем: headless-хост MCP не инициализирует), `skill-load.json`/`reference-read.json`/`project-map.json` содержат обязательные результаты; runtime cache пуст — release runtime не скачивался.

## Definition Of Done

Локальная задача завершена, когда одновременно выполнено следующее:

1. Получен локальный `.tgz` текущего checkout.
2. Пакет установлен в изолированный consumer.
3. Все 73 скилла зарегистрированы OpenCode.
4. Все 27 скиллов с общими ссылками имеют доступ к `references/`.
5. Все 71 `unica.*` инструмента видны build-агенту.
6. Один скилл загружен штатным `skill` tool.
7. `unica.project.map` вызван через OpenCode и вернул ответ.
8. `mcp.unica` запускает локальный `unica.exe`.
9. Быстрый набор тестов и архитектурные проверки зелёные.
10. Не выполнено ни одной публикации и не изменена глобальная установка OpenCode.
