# Unica для OpenCode

Этот npm-пакет добавляет рабочие процессы разработки
[1С:Предприятия](https://github.com/apshendev/unica) в
[OpenCode](https://opencode.ai): полный упакованный набор навыков и единственный
публичный MCP-сервер `unica` с инструментами `unica.*`.

**Статус:** npm-пакет `@apshendev/unica-opencode` пока не опубликован. Рабочий
способ использовать Unica в OpenCode сегодня — локальная проверка собранного
`.tgz` (раздел ниже). Раздел «Установка из npm» вступает в силу после первой
публикации.

## Локальная проверка собранного пакета

Полная процедура рассчитана на OpenCode `1.18.22` или новее и повторяет
проверенный рецепт локального тестирования выпуска.

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
  закреплённый runtime (хеши архива и файлов) перед запуском `unica`.

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
