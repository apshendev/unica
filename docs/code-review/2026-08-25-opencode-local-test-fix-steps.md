# Пошаговый порядок исправлений по плану локального OpenCode-пакета

- Date: `2026-08-25`
- Status: `approved`
- Decision: `none — no architectural contract changed`

Базовый план: `2026-08-25-opencode-local-test-fix-plan.md`. Здесь — точная
последовательность действий: по каждому пункту сначала тест (красный), потом
правка (зелёный).

---

## Шаг 1. Разбор `opencode mcp list` (P1)

### 1.1. Красный: новые фикстуры в `tests/ci/test_smoke_opencode_consumer.py`

Обновить существующие смысловые тесты `VerifyMcpTests` и дополнить их формой,
наблюдаемой у реального OpenCode 1.18.22 (байты из
`C:\Users\inilu\AppData\Local\Temp\opencode\mcp-probe\mcp-raw.txt`,
`mcp-nocolor.txt`):

- рамка, ANSI, подключённый `context7`, упавший `unica` и формат строк деталей
  берутся из записанного вывода без изменения;
- работающего опубликованного `unica` в записи нет, поэтому позитивная фикстура
  использует записанную рамку, но конкретную строку `✓ unica connected` и
  конкретную команду упакованного bootstrap формирует тест;
- в фикстурах не использовать многоточия или псевдопути: Windows-вариант
  содержит полный путь
  `C:\consumer\node_modules\@apshendev\unica-opencode\bootstrap\bin\win-x64\unica-bootstrap.exe run --plugin-root C:\consumer\node_modules\@apshendev\unica-opencode`,
  Linux-вариант — полный путь
  `/consumer/node_modules/@apshendev/unica-opencode/bootstrap/bin/linux-x64/unica-bootstrap run --plugin-root /consumer/node_modules/@apshendev/unica-opencode`;
- Windows-путь в Python-тесте записывать только raw string, чтобы `\n`, `\b` и
  `\u` не интерпретировались как escape-последовательности:
  ```python
  windows_command = (
      r"C:\consumer\node_modules\@apshendev\unica-opencode"
      r"\bootstrap\bin\win-x64\unica-bootstrap.exe run --plugin-root "
      r"C:\consumer\node_modules\@apshendev\unica-opencode"
  )
  ```
  `C:\consumer` — данные фикстуры, моделирующие Windows-транскрипт, а не путь
  к checkout репозитория;
- сохранить существующие проверки connected, failed, отсутствующего bootstrap,
  bootstrap в блоке другого сервера и отсутствующего `unica`, заменив только
  их нереалистичную форму вывода;
- добавить `test_no_color_output_is_still_parsed` — форма из
  `mcp-nocolor.txt`, где ANSI на статусе/деталях остаётся и при `NO_COLOR=1`;
- добавить `test_exact_server_name_match` — сервер `unica-backup` оформлен
  полноценным connected-блоком со своей bootstrap-деталью:
  ```text
  ●  ✓ unica-backup connected
  │      C:\consumer\...\unica-bootstrap.exe run --plugin-root ...
  ```
  Ожидание — `SystemExit` именно потому, что точного сервера `unica` нет.
  На текущем коде тест обязан быть красным: подстрочный поиск ошибочно
  принимает `unica-backup`, видит bootstrap и завершается успешно;
- добавить `test_a_listing_without_a_server_frame_fails_closed` — пустой
  файл/мусор;
- новых проверок `VerifySkillsTests` не добавлять: это не относится к
  исправляемому дефекту.

Запуск: `python -m unittest tests.ci.test_smoke_opencode_consumer -v` — фиксы
с ANSI/`│` падают с «unica server is not launched through the packaged
bootstrap» или «does not mention the unica server» — это воспроизведение
дефекта.

### 1.2. Зелёный: `scripts/ci/smoke-opencode-consumer.py`, только `verify_mcp`

- добавить в начало модуля `import re` (сейчас он не импортирован), затем
  `_ANSI = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]")` и очистку OSC
  `\x1b\].*?(?:\x07|\x1b\\)`; каждую строку чистить, `\r` игнорировать;
- классификация по первому непробельному символу: `●` — строка сервера,
  `│` с непустым содержимым — деталь текущего сервера, `│` пустая —
  разделитель, `┌`/`└` — границы рамки;
- из строки сервера выделять статус (`connected|disabled|failed` — последнее
  слово) и имя (точное сравнение `== "unica"`, не подстрока);
- проверки по существу те же: unica есть → статус `connected` → в деталях её
  блока есть `unica-bootstrap`;
- любое структурное неожидание (нет ни одной `●`-строки, имя не выделяется) —
  `SystemExit` (fail closed);
- публичный шов `main(["verify-mcp", "--output", …])` не менять — workflow и
  тесты зовут как раньше.

Запуск повторно — зелёный. Затем
`python -m py_compile scripts/ci/smoke-opencode-consumer.py`.

---

## Шаг 2. Частичная мутация конфигурации (P2)

### 2.1. Красный: драйвер и тест

- `tests/ci/opencode_adapter_driver.mjs`: в `catch` возвращать
  `{ ok: false, error: …, config: instruction.config }` — конфиг виден даже
  когда импорт/инициализация упали (объект передан по ссылке, мутации видны);
- `tests/ci/test_opencode_adapter.py::test_unsupported_platforms_fail_during_initialization`:
  для каждой неподдерживаемой пары (darwin/arm64, darwin/x64, linux/arm64,
  win32/arm64) прогнать два конфига:
  1. `{}`;
  2. заранее заполненный
     `{"skills": {"paths": ["~/team"], "urls": ["https://example.com/s/"]},
     "mcp": {"other-server": {…}}}`.

  Утверждение: `report["ok"] is False` и `report["config"] == <исходный конфиг
  дословно>` (deep equality).

Запуск: `python -m unittest tests.ci.test_opencode_adapter -v` — на текущем
адаптере `{}` получает `skills`, а заполненный конфиг получает мутированный
`skills.paths` (и `installMcp` успевает создать `config.mcp = {}` для `{}`
до броска `hostTarget()`) — тест красный.

### 2.2. Зелёный: `plugins/unica/opencode/index.js`

- в области модульных констант: `const HOST_TARGET = hostTarget()` (объявление
  функции хойстится, вызов при загрузке модуля корректен);
- `installMcp` использует `const { target, executable } = HOST_TARGET` вместо
  вызова `hostTarget()` внутри;
- порядок `installSkills` → `installMcp` в hook становится нечувствительным к
  отказу: неподдерживаемая платформа падает при `import`, до любого hook и до
  любой мутации. Переставлять вызовы в hook не нужно — отказ происходит раньше.

Повторный запуск — зелёный (в т.ч. все существующие позитивные тесты, т.к.
драйвер ставит `process.platform/arch` до `import`).

---

## Шаг 3. Compile-time seam происхождения bootstrap (P2)

### 3.1. Новый Rust-тест

В `crates/unica-bootstrap/tests/manifest_contract.rs` (рядом с существующими
`fork_fixture()` и `FORK_REPOSITORY`) добавить общий helper и один тест
`ordinary_validation_uses_the_repository_compiled_into_the_bootstrap`:

- объявить `UPSTREAM_REPOSITORY` со значением
  `https://github.com/IngvarConsulting/unica`;
- вынести построение манифеста в
  `fixture_for_repository(repository: &str)`: helper меняет
  `source.repository`, `release.repository` и URL ядра для всех трёх целей;
- существующий `fork_fixture()` сохранить как вызов
  `fixture_for_repository(FORK_REPOSITORY)`;
- в тесте получить владельца через
  `option_env!("UNICA_BOOTSTRAP_CORE_REPOSITORY").unwrap_or(UPSTREAM_REPOSITORY)`;
- `parse(fixture_for_repository(compiled_repository)).validate("0.7.0")`
  обязан пройти;
- для отрицательной проверки выбрать upstream, если сборка названа любым
  форком, и `FORK_REPOSITORY`, если сборка названа upstream;
- `parse(fixture_for_repository(different_repository)).validate("0.7.0")`
  обязан вернуть ошибку с `repository identity`;
- тест использует только публичный `RuntimeManifest::validate`, без
  `validate_with_core_repository`.

Одна функция проходит при отсутствующей переменной, при явно переданном
upstream и при любом адресе форка. Отдельного «красного» прогона самого
Rust-теста здесь нет — это новое доказательство, а не репродукция дефекта;
отсутствующее включение этого доказательства в CI воспроизводит красный
workflow-тест следующего пункта.

### 3.2. Workflow: `.github/workflows/unica-plugin-release.yml`

В job `build-tools`, только `matrix.target == 'linux-x64'`, отдельный шаг после
сборки:

```yaml
- name: Prove the compiled bootstrap honors the named core repository
  if: matrix.target == 'linux-x64'
  run: >
    UNICA_BOOTSTRAP_CORE_REPOSITORY="$CORE_RELEASE_REPOSITORY"
    cargo test -p unica-bootstrap --test manifest_contract
    ordinary_validation_uses_the_repository_compiled_into_the_bootstrap -- --exact
```

Шаг использует дефолтный `target/` (не кешируется в этом job), поэтому тестовый
бинарь компилируется уже с нужной переменной. Публикационные jobs не трогать.

### 3.3. Красный, затем фиксация в `tests/ci/test_unica_workflow.py`

Сначала написать утверждение (шага в YAML ещё нет → красный): в блоке
`build-tools` есть `cargo test -p unica-bootstrap --test manifest_contract` с
`--exact`, имя теста-цель, shell-префикс
`UNICA_BOOTSTRAP_CORE_REPOSITORY="$CORE_RELEASE_REPOSITORY"`, и шаг ограничен
`matrix.target == 'linux-x64'`. Потом добавить шаг в YAML → зелёный.

### 3.4. Локальная проверка форка (PowerShell)

```powershell
$env:UNICA_BOOTSTRAP_CORE_REPOSITORY="https://github.com/apshendev/unica"
cargo test -p unica-bootstrap --test manifest_contract ordinary_validation_uses_the_repository_compiled_into_the_bootstrap -- --exact
Remove-Item Env:UNICA_BOOTSTRAP_CORE_REPOSITORY
cargo test -p unica-bootstrap --test manifest_contract   # default-ветка теста
```

---

## Шаг 4. Сборка локального `.tgz` (ручной, без изменений репозитория)

1. Скачать проверенный thin-артефакт:
   ```powershell
   gh run download 32766639619 --repo IngvarConsulting/unica --name unica-thin-marketplace --dir .build/opencode-local/thin
   ```
2. Sanity-проверка перед упаковкой: `runtime-manifest.json` в
   `.build/opencode-local/thin/plugins/unica` должен иметь
   `pluginVersion == 0.12.0` и `release.tag == v0.12.0` — иначе
   `package-unica-opencode.py` откажет (сравнение с
   `plugins/unica/package.json`). Если артефакт недоступен или значение не
   совпало, остановиться и сообщить фактическое расхождение; другой run
   самостоятельно не выбирать.
3. Собрать кандидат:
   ```powershell
   python scripts/ci/package-unica-opencode.py --repo-root . --thin-root .build/opencode-local/thin/plugins/unica --out-dir dist/local-opencode
   ```

Ожидаемо: `dist/local-opencode/apshendev-unica-opencode-0.12.0.tgz`
(адаптер и npm-метаданные — из текущего checkout, уже с фиксами шагов 1–2).

`.build/` и `dist/` не коммитить.

---

## Шаг 5. Проверка настоящим OpenCode 1.18.22 (ручной, без изменений репозитория)

Шаг 5 — одноразовая ручная проверка на текущем Windows-хосте. PowerShell-команды
не добавляются в репозиторий как скрипты; все изменяемые Python-, JavaScript- и
Rust-компоненты остаются кроссплатформенными.

Сначала один раз вычислить пути — никакого хардкода корня checkout:

```powershell
$repo = (git rev-parse --show-toplevel).Trim()
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$root = Join-Path $repo ".build\opencode-local"
$consumer = Join-Path $root "consumer"
$package = Join-Path `
    $repo `
    "dist\local-opencode\apshendev-unica-opencode-0.12.0.tgz"
$pluginRoot = Join-Path `
    $consumer `
    "node_modules\@apshendev\unica-opencode"
```

1. Проверить версию: `opencode --version` → `1.18.22`. Вывод capture-ом
    сначала, `.Trim()` — только после проверки кода возврата, чтобы отказ
    команды не упал раньше предусмотренного контроля. Если версия отличается,
    остановиться и сообщить; ничего глобально не устанавливать и не обновлять:
   ```powershell
   $opencodeOutput = opencode --version
   if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

   $opencodeVersion = "$opencodeOutput".Trim()
   if ($opencodeVersion -ne "1.18.22") {
       throw "OpenCode 1.18.22 is required, found $opencodeVersion"
   }
   ```
2. Потребитель — заведомо генерируемый каталог под `.build/opencode-local`,
   поэтому перед созданием очистить только его (при повторном запуске старые
   `node_modules`, `opencode.json` и наблюдения не должны пережить прогон);
   другие каталоги не удалять:
   ```powershell
   if (Test-Path -LiteralPath $consumer) {
       Remove-Item -LiteralPath $consumer -Recurse -Force
   }

   New-Item -ItemType Directory -Path $consumer | Out-Null
   Set-Location $consumer

   npm init -y
   if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

   npm install --ignore-scripts $package
   if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
   ```
3. `opencode.json` в каталоге потребителя — плагин локальным файлом (загрузчик
   1.18.22 трактует `file://` как file-source, без npm и без compat-гейта;
   entry берётся из `main`). Абсолютный URI вычислить из установленного
   package root; расположение checkout нигде не зашито:
   ```powershell
   $pluginPath = (Resolve-Path -LiteralPath $pluginRoot).Path
   $pluginUri = [System.Uri]::new($pluginPath).AbsoluteUri

   $config = @{
       plugin = @($pluginUri)
   } | ConvertTo-Json -Depth 3

   $utf8 = New-Object System.Text.UTF8Encoding($false)
   [System.IO.File]::WriteAllText(
       (Join-Path $consumer "opencode.json"),
       $config,
       $utf8
   )
   ```
4. Изолированные каталоги создать до запуска OpenCode и назначить в тот же
   shell:
   ```powershell
   $ocConfig = Join-Path $root "oc-config"
   $xdgConfig = Join-Path $root "xdg\config"
   $xdgData = Join-Path $root "xdg\data"
   $xdgCache = Join-Path $root "xdg\cache"
   $xdgState = Join-Path $root "xdg\state"
   $runtimeCache = Join-Path $root "unica\cache\runtime"
   $providerState = Join-Path $root "unica\cache\provider-state"

   New-Item -ItemType Directory -Force -Path `
       $ocConfig, `
       $xdgConfig, `
       $xdgData, `
       $xdgCache, `
       $xdgState, `
       $runtimeCache, `
       $providerState | Out-Null

   $env:OPENCODE_CONFIG_DIR = $ocConfig
   $env:XDG_CONFIG_HOME = $xdgConfig
   $env:XDG_DATA_HOME = $xdgData
   $env:XDG_CACHE_HOME = $xdgCache
   $env:XDG_STATE_HOME = $xdgState
   $env:UNICA_RUNTIME_CACHE_DIR = $runtimeCache
   $env:UNICA_PROVIDER_STATE_DIR = $providerState
   ```
5. Сбор наблюдений — из каталога consumer, редирекция только через `cmd /c`,
   чтобы файлы stdout остались байт-в-байт UTF-8. stderr сохранять отдельно:
   смешивание stderr с `skills.json` сделает JSON невалидным. После каждой
   команды явно проверить код возврата:
   ```powershell
   Set-Location $consumer

   cmd /d /s /c "opencode debug skill 1>skills.json 2>skills.stderr.txt"
   if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

   cmd /d /s /c "opencode mcp list 1>mcp.txt 2>mcp.stderr.txt"
   if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
   ```
   Холодная загрузка runtime с upstream-релиза v0.12.0 укладывается в
   15-минутный MCP-таймаут адаптера — это часть проверки.
6. Верификация исправленным скриптом через `uv` из корня проекта:
   `--directory $repo` задаёт и проектное окружение, и рабочий каталог
   checkout, поэтому путь к скрипту остаётся относительным (локальный
   `pyproject.toml` от `uv init` используется, но не коммитится).
   `--plugin-root` — на установленный пакет, не на checkout:
   ```powershell
   uv run --directory $repo python scripts/ci/smoke-opencode-consumer.py `
       verify-skills `
       --json (Join-Path $consumer "skills.json") `
       --plugin-root $pluginRoot
   if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

   uv run --directory $repo python scripts/ci/smoke-opencode-consumer.py `
       verify-mcp `
       --output (Join-Path $consumer "mcp.txt")
   if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
   ```
7. Критерии успеха: все упакованные скиллы обнаружены; `unica … connected`;
   в её блоке — `unica-bootstrap` с путём внутри
   `node_modules\@apshendev\unica-opencode`.

Известный риск шага 5: это первая живая загрузка адаптера OpenCode (до сих пор
пакет в реестре отсутствовал и живого прогона не было). Если загрузчик 1.18.22
не примет форму экспорта (`UnicaOpenCodePlugin` → hooks `{config}`),
зафиксировать точный текст ошибки и вернуться на согласование — самовольно
менять форму экспорта нельзя.

---

## Финальная проверка всего changeset

```text
python -m unittest tests.ci.test_smoke_opencode_consumer -v
python -m unittest tests.ci.test_opencode_adapter -v
python -m unittest tests.ci.test_package_unica_opencode -v
python -m unittest tests.ci.test_unica_workflow -v
python -m unittest tests.ci.test_build_unica_tools -v
python -m py_compile scripts/ci/*.py tests/ci/*.py
cargo test -p unica-bootstrap --test manifest_contract
```

## Что не трогать

- `publish-unica-opencode.py`, публикационные/smoke-jobs, `evaluate-ci-gate.py`,
  архитектурные записи — publishing-замечания отложены;
- не создавать `.ps1`/`.cmd` orchestration script: PowerShell — только
  одноразовый локальный запуск шага 5; постоянный кроссплатформенный `uv`
  entrypoint не входит в утверждённый минимальный план;
- пользовательские `CLAUDE.md`, `docs/agents/`, `docs/specs/` и побочные файлы
  от `uv init` (`pyproject.toml` и пр. в корне — используются локально для
  `uv run`, но в changeset не входят);
- никаких npm-записей, тегов, релизов.
