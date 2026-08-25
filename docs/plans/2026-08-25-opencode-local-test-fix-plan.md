# Минимальный план исправлений замечаний код-ревью: локальный OpenCode-пакет

- Date: `2026-08-25`
- Status: `approved`
- Decision: `none — no architectural contract changed`

## Цель

Один минимальный changeset, результат которого:

- исправляет дефекты, мешающие локальному тесту;
- собирает настоящий `.tgz` из текущего адаптера;
- устанавливает его в изолированный OpenCode 1.18.22;
- не публикует ничего в npm или GitHub Releases.

Никаких `NPM_PROMOTION_TOKEN`, OIDC, dist-tags, bootstrap-публикации и release-тегов.

## План

1. Исправить разбор `opencode mcp list`.

Сначала дополнить `tests/ci/test_smoke_opencode_consumer.py` реальными ANSI/clack-транскриптами OpenCode 1.18.22:

- `●  ✓ unica connected`;
- строки команды с префиксом `│`;
- Windows- и Linux-пути к `unica-bootstrap`;
- состояние `failed`;
- остаточный ANSI при `NO_COLOR`;
- точное имя сервера: `unica-backup` не считается `unica`;
- bootstrap другого сервера не засчитывается.

Запустить тест и зафиксировать ожидаемое падение текущего парсера.

Затем изменить `scripts/ci/smoke-opencode-consumer.py`:

- удалить ANSI CSI/OSC-последовательности;
- разбирать clack-строки `●` и продолжения `│`;
- связывать детали только со своим сервером;
- сравнивать имя `unica` точно;
- падать закрыто при неизвестной или пустой структуре.

Проверка:

```text
python -m unittest tests.ci.test_smoke_opencode_consumer -v
```

2. Устранить частичную мутацию конфигурации на неподдерживаемой платформе.

Сначала изменить:

- `tests/ci/opencode_adapter_driver.mjs`;
- `tests/ci/test_opencode_adapter.py`.

Driver должен возвращать `config` даже при ошибке импорта или инициализации. Тест `test_unsupported_platforms_fail_during_initialization` должен для `{}` и конфигурации с существующими `skills`/`mcp` проверять полное равенство до и после ошибки.

Запустить тест и увидеть, что текущий адаптер добавляет `skills` и/или пустой `mcp`.

Затем изменить `plugins/unica/opencode/index.js`:

```js
const HOST_TARGET = hostTarget()
```

Вычислять целевую платформу при загрузке модуля и использовать готовую константу в `installMcp`. Неподдерживаемая платформа тогда отклоняется до вызова hook и до любых мутаций.

Проверка:

```text
python -m unittest tests.ci.test_opencode_adapter -v
```

3. Закрыть compile-time seam происхождения bootstrap.

В `crates/unica-bootstrap/tests/manifest_contract.rs` добавить тест, который:

- вызывает обычный `RuntimeManifest::validate`, а не `validate_with_core_repository`;
- принимает манифест владельца, записанного через `UNICA_BOOTSTRAP_CORE_REPOSITORY` при компиляции;
- отклоняет манифест другого владельца.

В `.github/workflows/unica-plugin-release.yml` добавить только read/build-проверку на Linux:

```text
UNICA_BOOTSTRAP_CORE_REPOSITORY="$CORE_RELEASE_REPOSITORY" \
cargo test -p unica-bootstrap --test manifest_contract \
  ordinary_validation_uses_the_repository_compiled_into_the_bootstrap -- --exact
```

В `tests/ci/test_unica_workflow.py` закрепить наличие этой команды и передачу переменной. Публикационные jobs не менять.

Проверка локально для форка:

```text
$env:UNICA_BOOTSTRAP_CORE_REPOSITORY="https://github.com/apshendev/unica"
cargo test -p unica-bootstrap --test manifest_contract `
  ordinary_validation_uses_the_repository_compiled_into_the_bootstrap -- --exact
```

4. Собрать локальный `.tgz`.

Не создавать новый формат пакета и не ослаблять проверки `package-unica-opencode.py`.

Для первого теста использовать существующий проверенный thin-артефакт upstream run `32766639619`. Он содержит bootstrap-матрицу и указывает на существующие runtime-ассеты `v0.12.0`. Адаптер и npm-метаданные упаковщик возьмёт из текущего checkout, включая внесённые исправления.

Исполнитель должен:

```text
gh run download 32766639619 \
  --repo IngvarConsulting/unica \
  --name unica-thin-marketplace \
  --dir .build/opencode-local/thin

python scripts/ci/package-unica-opencode.py \
  --repo-root . \
  --thin-root .build/opencode-local/thin/plugins/unica \
  --out-dir dist/local-opencode
```

Ожидаемый результат:

```text
dist/local-opencode/apshendev-unica-opencode-0.12.0.tgz
```

`dist/` и `.build/` не коммитить.

5. Проверить `.tgz` настоящим OpenCode.

В `.build/opencode-local/consumer`:

- создать пустой npm-проект;
- установить локальный `.tgz` через `npm install --ignore-scripts`;
- записать в `opencode.json` абсолютный путь к установленному каталогу `node_modules/@apshendev/unica-opencode`;
- изолировать конфигурацию и кеши через `OPENCODE_CONFIG_DIR`, XDG-переменные, `UNICA_RUNTIME_CACHE_DIR` и `UNICA_PROVIDER_STATE_DIR`;
- запускать OpenCode строго версии `1.18.22`;
- сохранить результаты `opencode debug skill` и `opencode mcp list`;
- проверить их исправленным `smoke-opencode-consumer.py`, причём `--plugin-root` должен указывать на установленный пакет, а не checkout.

Успех означает:

- OpenCode загрузил entry point из установленного `.tgz`;
- все упакованные skills обнаружены;
- `unica` имеет статус `connected`;
- команда сервера содержит bootstrap именно из установленного пакета.

## Общая проверка

```text
python -m unittest tests.ci.test_smoke_opencode_consumer -v
python -m unittest tests.ci.test_opencode_adapter -v
python -m unittest tests.ci.test_package_unica_opencode -v
python -m unittest tests.ci.test_unica_workflow -v
python -m unittest tests.ci.test_build_unica_tools -v
python -m py_compile scripts/ci/*.py tests/ci/*.py
cargo test -p unica-bootstrap --test manifest_contract
```

## Не входит

Сейчас не исправляются и не проверяются:

- `npm publish`;
- изменение `latest`/`next`;
- ожидание распространения версии в npm registry;
- promotion job и `NPM_PROMOTION_TOKEN`;
- trusted publisher;
- архитектурное разделение публикационных правил;
- реальный fork runtime release.

Локальный smoke использует существующие upstream runtime-ассеты. Он доказывает упаковку, установку и работу OpenCode-адаптера, но не готовность npm-релиза. Публикационные замечания остаются отдельной последующей работой.

Не трогать пользовательские `CLAUDE.md`, `docs/agents/` и `docs/specs/`.
