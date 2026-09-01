# Runbook: local-debug кандидат OpenCode-плагина и постоянная локальная установка

Запись о том, как собрана и постоянно установлена версия
`@apshendev/unica-opencode 0.12.0` (local-debug, win-x64), и как повторить
это для новой версии. Нормативная архитектура режима —
`DEC.2026-08-25.OPENCODE-LOCAL-DEBUG-RUNTIME`,
`CTR.HOST.OPENCODE-LAUNCH-MODES`, `CTR.PKG.OPENCODE-LOCAL-DEBUG-COMPOSITION`,
`INV.PKG.OPENCODE-DEV-CANDIDATE-UNPUBLISHABLE`; происхождение решения —
`docs/design/2026-08-25-opencode-local-debug-runtime-design.md`.

## Что такое local-debug кандидат

npm-пакет, собранный из текущего checkout: адаптер, навыки и ядро `unica`
бинарно совпадают с рабочим деревом. Маркер `opencode/local-debug.json`
переключает адаптер на прямой запуск упаковленного ядра
`bin/<target>/unica(.exe)` — bootstrap не используется, runtime не
скачивается. Публикация такого кандидата в npm запрещена до первого вызова
npm (`scripts/ci/publish-unica-opencode.py`).

## Окружение сборки

- Windows x64, MSVC-тулчейн Rust (`cargo` из `$env:USERPROFILE\.cargo\bin`);
- Python 3.12 (uv-окружение `unica-dev`);
- Node/npm для `npm pack` и установки;
- OpenCode `1.18.23` для проверок (минимум — `1.18.22`).

## Сборка (три команды из корня репозитория)

```sh
# 1. release-сборка ядра и инструментов текущей цели
python scripts/ci/build-unica-tools.py \
  --repo-root . \
  --target win-x64 \
  --lock-file plugins/unica/third-party/tools.lock.json \
  --out-dir .build/opencode-local-debug/tool-bundles \
  --work-dir .build/opencode-local-debug/tool-work

# 2. local-debug корень плагина текущей цели
python scripts/ci/package-unica-plugin.py \
  --repo-root . \
  --tools-root .build/opencode-local-debug/tool-bundles \
  --lock-file plugins/unica/third-party/tools.lock.json \
  --out-dir .build/opencode-local-debug/package \
  --local-debug-target win-x64

# 3. npm-кандидат от local-debug корня (взаимоисключаемо с --thin-root)
python scripts/ci/package-unica-opencode.py \
  --repo-root . \
  --local-debug-root .build/opencode-local-debug/package/marketplace/plugins/unica \
  --out-dir .build/opencode-local-debug/npm
```

## Состав кандидата

- Все 73 навыка (`skills/*/SKILL.md`) и общий `references/` включены в `.tgz`
  целиком и устанавливаются вместе с пакетом — отдельных npm dependencies для
  навыков и справочников нет.
- Ядро лежит в `bin/win-x64/unica.exe` и запускается адаптером напрямую по
  маркеру `opencode/local-debug.json`: bootstrap не используется, runtime не
  скачивается.
- Адаптер разрешает чтение только упакованного `references/*`
  (`CTR.HOST.OPENCODE-REFERENCE-ACCESS`); доступ к остальным внешним каталогам
  не открывается.
- Local-debug кандидат — development-сборка: `npm publish` для него запрещён
  (`scripts/ci/publish-unica-opencode.py` отказывает до первого вызова npm),
  и никакая команда публикации в этом runbook не используется.

## Проверка кандидата до установки

- `python -m pytest tests/ci/test_package_unica_opencode.py tests/ci/test_opencode_adapter.py tests/ci/test_smoke_opencode_consumer.py tests/ci/test_publish_unica_opencode.py tests/ci/test_design_documents.py tests/arch -q`;
- `python scripts/arch/registry.py --check`; `python scripts/arch/immutability.py`;
- `cargo test --release --locked -p unica-coder --lib tools_list_round_trips -- --nocapture`
  (ratchet на размер `tools/list`: 204 001 байт, граница 1 285 000).

## Изолированный consumer: обязательные host-проверки

Consumer живёт в `.build/opencode-local-debug/consumer` (никак не в профиле
пользователя): `npm init -y` и `npm install --ignore-scripts <абсолютный путь
к tgz>`. Переменные изолируются по пустым каталогам в
`.build/opencode-local-debug/environment/`: `OPENCODE_CONFIG_DIR`,
`XDG_CONFIG_HOME`, `XDG_DATA_HOME`, `XDG_CACHE_HOME`, `XDG_STATE_HOME`,
`UNICA_RUNTIME_CACHE_DIR`, `UNICA_PROVIDER_STATE_DIR`. После полного
Запуска OpenCode собираются headless-артефакты наблюдений (из каталога
потребителя, без LLM-провайдера и пользовательского prompt):

```sh
opencode debug skill > skills.json
opencode mcp list > mcp.txt
opencode debug agent build --tool skill --params '{"name":"code-search"}' > skill-load.json
opencode debug agent build --tool read --params '{"filePath":"<plugin-root>/references/platform/platform-mechanics.md"}' > reference-read.json
```

`<plugin-root>` — абсолютный путь
`<consumer>/node_modules/@apshendev/unica-opencode`. `skill` и `read` —
нативные инструменты OpenCode, они работают headless.

MCP-инструменты `unica_*` headless-хост не инициализирует (доказано
DEBUG-логами на OpenCode 1.18.22 и 1.18.25: `debug agent build` и `serve`
не поднимают MCP-подключения плагина, `--tool unica_*` даёт
`Tool not found`). Поэтому поверхность агента и живой вызов MCP-инструмента
собираются в перезапущенной живой сессии OpenCode с тем же project-конфигом
(`plugin` с `file://` URI установленного пакета):

- `agent-tools-live.json` — поверхность инструментов живой сессии в форме
  `{"tools": {"unica_unica_project_map": true, ...}}` (каждый видимый
  инструмент — ключ со значением `true`);
- `project-map.json` — JSON-ответ вызова `unica_unica_project_map` из живой
  сессии.

Артефакты проверяются верификатором репозитория (`--plugin-root` —
абсолютный путь установленного пакета):

```sh
python scripts/ci/smoke-opencode-consumer.py verify-skills --json skills.json --plugin-root <plugin-root> --target win-x64
python scripts/ci/smoke-opencode-consumer.py verify-mcp --output mcp.txt --plugin-root <plugin-root> --target win-x64
python scripts/ci/smoke-opencode-consumer.py verify-agent-tools --agent-json agent-tools-live.json --ledger arch/tool-surface-review.json --server unica
```

Обязательные результаты: `opencode debug skill` перечисляет все 73 навыка под
установленным npm-корнем (встроенный `customize-opencode` проверке не мешает);
`opencode mcp list` показывает `unica connected` с командой прямого запуска
`bin/win-x64/unica.exe` — без bootstrap и `cargo run`; `agent-tools-live.json`
несёт все 71 инструмент `unica_unica_*` из ledger со значением `true`;
`skill-load.json` — `Loaded skill: code-search` с маршрутизацией через
`unica.code.search`; `project-map.json` — ответ MCP-инструмента без
`Tool not found`, permission denial и MCP transport error; `reference-read.json`
— файл packaged references, прочитанный без запроса external_directory; в
runtime cache не появляется скачанный release runtime.

## Идентичность собранной версии 0.12.0

- архив: `apshendev-unica-opencode-0.12.0.tgz`, 109 426 065 байт;
- SHA-256: `D816AA602BA9EC95D46A174892B8E407818B7BE5FFBBD8FC1DB030AF5293AFB8`;
- маркер: `mode=local-debug`, `target=win-x64`, `pluginVersion=0.12.0`;
- ядро `bin/win-x64/unica.exe` — 22 897 152 байта.

## Постоянная локальная установка (профиль пользователя)

Постоянное хранилище живёт вне репозитория, поэтому survives `git clean` и
пересборками `.build`:

```text
C:\Users\<user>\.local\share\opencode\packages\unica-opencode\
  artifacts\apshendev-unica-opencode-0.12.0-win-x64-fac0951285d6.tgz
  installs\0.12.0-win-x64-fac0951285d6\node_modules\@apshendev\unica-opencode\
```

Шаги:

1. Сверить SHA-256 архива с протестированным (см. выше).
2. Скопировать `.tgz` из `.build\...\npm` в `artifacts\` с именем
   `<имя>-<версия>-<target>-<первые 12 hex хеша>.tgz`.
3. В `installs\<версия>-<target>-<12 hex>\` создать `package.json`-заглушку
   (`{"name":"unica-opencode-permanent","private":true}`) и выполнить
   `npm install --ignore-scripts <абсолютный путь к tgz>`.
4. В глобальном `~\.config\opencode\opencode.jsonc` добавить в массив
   `plugin` абсолютный `file://` URI каталога
   `node_modules/@apshendev/unica-opencode` из шага 3 (прямыми слешами):
   ```jsonc
   "file:///C:/Users/<user>/.local/share/opencode/packages/unica-opencode/installs/0.12.0-win-x64-fac0951285d6/node_modules/@apshendev/unica-opencode"
   ```
   Отдельная запись `mcp.unica` не нужна: адаптер сам владеет ею.
5. Полностью перезапустить OpenCode и проверить:
   `opencode mcp list` → `unica connected` с командой на постоянный
   `bin/win-x64/unica.exe`; `opencode debug skill` → упакованные навыки;
   контрольный `opencode run` с вызовом `unica.project.status`.
6. Открытые до правки конфига сессии OpenCode перезапустить; временную
   копию в `.build\opencode-local-debug` удалить.

## Обновление на новую версию

Повторить сборку и проверку, положить новый архив в `artifacts\`, установить
в новый `installs\<версия>-<target>-<hash12>\`, переключить `file://` URI в
`opencode.jsonc`, перезапустить OpenCode, проверить, затем удалить старый
`installs\<...>` и его архив. Одновременное наличие нескольких установок в
`installs\` позволяет откатиться заменой одной строки конфига.
