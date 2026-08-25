# Unica для OpenCode

Этот npm-пакет добавляет рабочие процессы разработки
[1С:Предприятия](https://github.com/apshendev/unica) в
[OpenCode](https://opencode.ai): полный упакованный набор навыков и единственный
публичный MCP-сервер `unica` с инструментами `unica.*`.

**Статус:** npm-пакет `@apshendev/unica-opencode` пока не опубликован. Рабочий
способ использовать Unica в OpenCode сегодня — локальная проверка собранного
`.tgz` (раздел ниже). Раздел «Установка из npm» вступает в силу после первой
публикации.

## Локальная проверка собранного пакета (release-кандидат)

Проверяет выпускной артефакт: thin-корень tag-run выпуска плюс текущие npm-метаданные
и адаптер. Полная процедура рассчитана на OpenCode `1.18.22` или новее и повторяет
проверенный рецепт локального тестирования выпуска. Чтобы проверить текущий Rust-код
форка, а не закреплённый выпуск, используйте рецепт «Локальная проверка текущего
checkout (local-debug)» ниже.

1. Соберите `.tgz` упаковщиком `scripts/ci/package-unica-opencode.py` от
   thin-корня артефакта tag-run выпуска (см. план
   `docs/plans/2026-08-25-opencode-local-test-fix-steps.md`):
   ```sh
   python scripts/ci/package-unica-opencode.py \
     --repo-root . \
     --thin-root <путь к thin-корню>/plugins/unica \
     --out-dir dist/local-opencode
   ```
2. Создайте пустой каталог-потребитель и установите пакет из локального
   архива:
   ```sh
   mkdir consumer && cd consumer
   npm init -y
   npm install --ignore-scripts <абсолютный путь к .tgz>
   ```
3. Создайте `opencode.json` в каталоге потребителя со ссылкой на установленный
   пакет через абсолютный `file://` URI каталога
   `node_modules/@apshendev/unica-opencode`:
   ```json
   {
     "plugin": ["file:///abs/path/to/consumer/node_modules/@apshendev/unica-opencode"]
   }
   ```
4. Изолируйте окружение от пользовательских конфигураций и кешей:
   `OPENCODE_CONFIG_DIR`, `XDG_CONFIG_HOME`, `XDG_DATA_HOME`, `XDG_CACHE_HOME`,
   `XDG_STATE_HOME`, а также `UNICA_RUNTIME_CACHE_DIR` и
   `UNICA_PROVIDER_STATE_DIR` — каждое на свой пустой каталог.
5. Полностью перезапустите OpenCode: плагины npm загружаются при старте,
   изменения конфигурации действуют только после перезапуска. Требуется
   OpenCode `1.18.22` или новее.
6. Соберите наблюдения:
   ```sh
   opencode debug skill
   opencode mcp list
   ```
   Ожидаемый результат — `unica connected`; в деталях её блока — команда
   упакованного bootstrap из
   `node_modules/@apshendev/unica-opencode/bootstrap/bin/<target>/unica-bootstrap`.

Первый запуск может надолго задержаться: адаптер скачивает и проверяет ядро
runtime с нуля (подробности в разделе «Первый запуск и кеши»). Это ожидаемое
поведение холодной доставки, а не зависание.

## Локальная проверка текущего checkout (local-debug)

Проверяет текущее состояние форка: адаптер, навыки и ядро `unica` собираются из
рабочего дерева, без закреплённого выпуска и без bootstrap-доставки runtime
(проектная записка `docs/design/2026-08-25-opencode-local-debug-runtime-design.md`,
решение `DEC.2026-08-25.OPENCODE-LOCAL-DEBUG-RUNTIME`).

1. Соберите tool-bundle текущей цели (требуется Rust с MSVC-тулчейном; на
   win-x64 выходит `bin/win-x64/unica.exe`):
   ```sh
   python scripts/ci/build-unica-tools.py \
     --repo-root . \
     --target win-x64 \
     --lock-file plugins/unica/third-party/tools.lock.json \
     --out-dir .build/opencode-local-debug/tool-bundles \
     --work-dir .build/opencode-local-debug/tool-work
   ```
2. Соберите local-debug корень плагина текущей цели:
   ```sh
   python scripts/ci/package-unica-plugin.py \
     --repo-root . \
     --tools-root .build/opencode-local-debug/tool-bundles \
     --lock-file plugins/unica/third-party/tools.lock.json \
     --out-dir .build/opencode-local-debug/package \
     --local-debug-target win-x64
   ```
3. Соберите `.tgz` npm-кандидата от local-debug корня (взаимоисключаемо с
   `--thin-root`):
   ```sh
   python scripts/ci/package-unica-opencode.py \
     --repo-root . \
     --local-debug-root .build/opencode-local-debug/package/marketplace/plugins/unica \
     --out-dir .build/opencode-local-debug/npm
   ```
4. Шаги 2–6 рецепта release-кандидата выше без изменений: каталог-потребитель,
   `npm install --ignore-scripts <абсолютный путь к .tgz>`, `file://` URI
   установленного пакета в `opencode.json`, изоляция окружения, полный
   перезапуск OpenCode и наблюдения `opencode debug skill` / `opencode mcp list`.

Отличия от release-кандидата: упаковщик записывает маркер
`opencode/local-debug.json`, по которому адаптер запускает упакованное ядро
`bin/<target>/unica(.exe)` напрямую — bootstrap не используется, ядро runtime
не скачивается, и `opencode mcp list` показывает команду установленного
бинарника вместо bootstrap. Маркер с чужой целью (например, `linux-x64` на
Windows-хосте) даёт явный отказ при инициализации. Такой кандидат —
development-сборка: публикация в npm отказывает ему до первого вызова npm.

## Установка из npm

Раздел вступает в силу после первой публикации пакета. Добавьте пакет в массив
`plugin` конфигурации OpenCode (`opencode.json` в проекте или
`~/.config/opencode/opencode.json` глобально):

```json
{
  "plugin": ["@apshendev/unica-opencode"]
}
```

Затем **полностью перезапустите OpenCode**. Чтобы закрепить конкретную версию,
используйте обычный npm-синтаксис: `"@apshendev/unica-opencode@0.12.0"`.

## Что делает адаптер

- один раз добавляет упакованный каталог `skills/` в пути навыков; собственные
  пути и удалённые URL навыков пользователя сохраняются;
- берёт владение записью `mcp.unica`: значение `mcp.unica` заменяется
  упакованным определением, поэтому устаревшая или несовместимая ручная запись
  не помешает запуску упакованного сервера; остальные записи MCP-серверов
  сохраняются;
- запускает упакованный native bootstrap напрямую
  (`unica-bootstrap run --plugin-root <корень пакета>`), который проверяет
  закреплённый runtime (хеши архива и файлов) перед запуском `unica`;
- в пакете с маркером `opencode/local-debug.json` вместо bootstrap запускает
  упаковленное ядро `bin/<target>/unica(.exe)` напрямую
  (`CTR.HOST.OPENCODE-LAUNCH-MODES`).

Адаптер не оборачивает инструменты `unica.*` как нативные инструменты OpenCode и
не добавляет других хуков.

## Поддерживаемые платформы

- Windows x64;
- Linux x64 (best-effort совместимость).

macOS и прочие архитектуры получают явный отказ при инициализации вместо
запуска неподходящего бинарника.

## Первый запуск и кеши

Первый запуск скачивает проверяемое ядро runtime — на медленном канале это
может занять минуты. Таймаут старта MCP поднят до 15 минут, чтобы холодная
установка не обрывалась на середине загрузки. Последующие запуски используют
проверенный кеш и стартуют быстро.

Кеш runtime и состояние провайдера живут в области OpenCode вашего
каталога кешей (`<cache>/opencode/unica/runtime` и
`<cache>/opencode/unica/provider-state`), где `<cache>` — это
`$XDG_CACHE_HOME` (или `%LOCALAPPDATA%` на Windows, или `~/.cache`).
Переменные `UNICA_RUNTIME_CACHE_DIR` и `UNICA_PROVIDER_STATE_DIR` переопределяют
эти адреса; уже заданные значения всегда имеют приоритет.

## Лицензия

LGPL-3.0-or-later, как и Unica. См. `LICENSE` и `ATTRIBUTIONS.md` внутри пакета.
