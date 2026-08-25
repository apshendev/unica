# Пошаговый план исправлений по code review issues #2-#5 (редакция 3, тестовый режим)

- Date: `2026-08-25`
- Status: `draft`
- Decision: `none` — план контракта не меняет; контрактные изменения оформляются решениями своих этапов (этап 4 заводит продуктовое `DEC.2026-08-25.NPM-DIST-TAG-PROMOTION`, этап 5 — продуктовое `DEC.2026-08-25.RULE-CLAIMS-TIGHTENED`; этап 3 новое решение не заводит — обновляет существующее процессное)

Источник замечаний: `docs/plans/2026-08-25-opencode-issues-2-5-code-review.md`
(далее «ревью», замечания 1–12) плюс раунды ревью предыдущих редакций плана
(13 замечаний второй редакции и 3 блокирующих замечания тестовой эксплуатации
третьей — включены ниже). Режим работы — тестовый: сначала убедиться, что идея
вообще работает, и только потом полировать поставку. Правило каждого шага: сначала
красный тест, наблюдение ожидаемого падения, потом правка, потом зелёный
прогон. Осознанные исключения, где дефект — пробел доказательства, а не
поведение, названы на месте (этапы 5.1, часть 3.2).

## Замечания ревью плана и их адресация

| # | Замечание ревью | Где закрыто |
| --- | --- | --- |
| R1 | Lifecycle product-rule противоречит действующим process-контрактам и тестам перезаземления | Этап 3 |
| R2 | `check`-адреса записей не разрешаются (нет `tests/…`, `Class::method`) | Этапы 3–5, таблицы front matter |
| R3 | Новые записи шире своего единственного `check` (stamp, visibility, composition) | Этапы 3–5 |
| R4 | Credential-тест заявляет непроверяемое статически (scope токена, «protected») | Этап 4.5 |
| R5 | Promotion job без checkout/toolchain/npm-конфигурации | Этап 4.5 |
| R6 | `verify-skills` без `--target`; нет Linux-негатива outside-root | Этап 4.1 |
| R7 | Служебный bootstrap-пакет нечем собрать | Этап 7.2 |
| R8 | Successor-план не использует буквально run `31950933025` | Этап 6 |
| R9 | Этап переноса описывает уже несуществующее состояние `git mv` | Этап 6 |
| R10 | Version-тесты ошибочно заявлены RED | Этап 5.1 |
| R11 | Топология PR не считает текущие 11 локальных коммитов | Этап 0 и топология |
| R12 | Clean-clone проверка не ставит тестовые зависимости | Финальная проверка |
| R13 | Переоткрытие issues и пост-публикация README не расписаны по жизненному циклу | Этапы 7.0, 7.5 |
| R14 | `actions/upload-artifact@v8` не существует — promotion-контур не запустится | Этап 4.5 |
| R15 | Inventory-тест противоречит намеренной замене корневого README | Этап 5.7 |

## Топология поставки

Тестовый режим: этапы выполняются последовательно ЛОКАЛЬНО на текущем `HEAD`
(`0075b905`), проверка этапа — его зелёные команды из плана. Ничего не пушится.
Разбивка на самостоятельно проверяемые PR с базой `main` выполняется позже,
отдельным решением пользователя, после подтверждения тестового контура; колонка
PR в таблице — будущее имя PR, в тестовом режиме просто метка этапа.
Зависимости: этап 4 требует этап 3 (штамп supersession для product-правил),
этап 5 требует этапы 2 и 3 (русский README с сохранённым именем floor-теста;
штамп для замен записей).

| Этап | PR | Содержание | Замечания |
| --- | --- | --- | --- |
| 0 | — | prerequisite: тестовый режим на текущем HEAD; PR-разбивка откладывается | R11 |
| 1 | uv-tooling | non-package tooling project | 10 |
| 2 | opencode-docs | русский README + локальная инструкция + обнаруживаемость | 4, 5 |
| 3 | registry-rule-supersession | процессный enabler: штамп замены product-правил | 8 (prereq), R1, R3 |
| 4 | npm-staging-promotion | smoke-binding, staging, visibility, promotion, runbook, arch npm | 1, 2, 3, 7, R4, R5, R6 |
| 5 | evidence-tightening | version bump, OPENCODE-CONFIG, PLATFORM-GATE, CORE-PROVENANCE, CLIENT-FLOOR, SHARED-SURFACE, NPM-CANDIDATE | 8, 9, R2, R3, R10 |
| 6 | plans-relocation | фиксация переноса планов, pointer'ы, successor-план | 11, 12, R8, R9 |
| 7 | — | внешние действия (issues, npm bootstrap, live evidence, docs после публикации) | 6, R7, R13 |

Открывать PR, пушить ветки, переоткрывать issues и любые npm-действия — только
после отдельного разрешения пользователя на каждом шаге.

---

## Этап 0. Prerequisite: тестовый режим на текущем HEAD (замечание R11)

Текущий `HEAD` (`0075b905`) опережает `origin/main` (`702c83a2`) на 11 коммитов;
рядом лежат непрослеживаемые планы. Для тестовой эксплуатации это НЕ блокер:
все этапы выполняются локально поверх текущего `HEAD`, ничего не пушится.

- Тестовая реализация идёт локально на текущем `HEAD`; доставка локальных
  коммитов и планов в `origin/main` не является предусловием запуска и не
  блокирует ни один этап.
- Этапы выполняются последовательно; проверка этапа — его зелёные команды.
- Разбивка на independently проверяемые PR с базой `main` и способ доставки
  текущих 11 коммитов согласуются отдельно, ПОСЛЕ подтверждения тестового
  контура; до этого контроль `git diff origin/main...HEAD` на «только изменения
  этапа» не требуется.
- Контур живой проверки идеи: локальный `.tgz` → `npm install --ignore-scripts`
  → `opencode debug skill` / `opencode mcp list` → `verify-skills` /
  `verify-mcp`; publish/promotion проверяются только моками — без npm-записей,
  токенов, trusted publisher и bootstrap-пакета.

> Выполнено: 2026-08-25 15:43 (этап 0 — prerequisite подтверждён: HEAD `0075b905`, тестовый режим, ничего не пушится)

---

## Этап 1. uv как non-package tooling project (замечание 10)

### 1.1. Красный: контракт tooling-окружения

Новый класс `ToolingProjectTests` в `tests/ci/test_version_contract.py`:

- `test_the_tooling_project_is_not_a_python_package` — корневой
  `pyproject.toml`: `name == "unica-dev"`; `version == "0.0.0"`;
  `requires-python == ">=3.12"`; `[tool.uv] package = false`; нет
  `[build-system]`; нет `[project.scripts]`.
- `test_the_python_pin_matches_the_development_floor` — `.python-version`
  содержит ровно `3.12`.

Ожидаемое падение сейчас: `name == "unica"`, `requires-python == ">=3.14"`,
присутствуют `[build-system]` и `[project.scripts]`, пин `3.14`.

> Выполнено: 2026-08-25 15:47 (1.1 — RED подтверждён: 'unica' != 'unica-dev', '3.14' != '3.12')

### 1.2. Зелёный

- `pyproject.toml`:

  ```toml
  [project]
  name = "unica-dev"
  version = "0.0.0"
  description = "Development tooling for the Unica repository"
  readme = "README.md"
  requires-python = ">=3.12"
  dependencies = []

  [tool.uv]
  package = false
  ```

- `.python-version` → `3.12`.
- Локально удалить непрослеживаемый placeholder `src/unica`
  (`src/unica/__init__.py` с `print("Hello from unica!")`). Это локальная
  очистка вне диффа PR: файла нет в git, на clean clone его не будет.
- Пересоздать lock: `uv lock` (текущий `uv.lock` закрепляет Python `>=3.14` и
  editable-пакет `unica`). Закоммитить свежий `uv.lock`.

Замечание для PR: `uv.lock` сегодня непрослеживаемый файл пользователя; его
  перезапись и добавление в git — прямое следствие критерия ревью 10, отметить
  это в описании PR. Удаление `src/` в PR не входит и не заявляется изменением.

> Выполнено: 2026-08-25 15:47 (1.2 — pyproject/пин/удаление src/unica/uv lock)

### 1.3. Проверка

```text
uv sync --locked
uv run python scripts/ci/smoke-opencode-consumer.py --help
uv run python -c "import sys; print(sys.prefix)"
uv run python -m unittest tests.ci.test_version_contract -v
```

Критерии (по ревью 10 — доказательство проектного окружения):

- `uv sync --locked` проходит на clean clone с закоммиченным lock;
- `uv run python scripts/ci/smoke-opencode-consumer.py --help` — отслеживаемый
  скрипт репозитория успешно выполняется в проектном окружении;
- вывод `sys.prefix` указывает в `.venv` проектного окружения — сравнение
  фиксируется в описании PR;
- прочие команды плана выполняются обычным `python`; «все дальнейшие прогоны
  через uv» план не заявляет.

> Выполнено: 2026-08-25 15:47 (1.3 — uv sync --locked OK; smoke --help OK; sys.prefix = D:\Projects\develop\unica\.venv-win; 17 тестов зелёные)

---

## Этап 2. Документация пользователя (замечания 4, 5)

### 2.1. Красный: контракт содержания README

В `tests/ci/test_package_unica_opencode.py` переписать
`test_the_candidate_documents_a_version_floor_not_a_ceiling` (имя сохранить
без изменений — на него ссылается действующая запись
`INV.HOST.OPENCODE-CLIENT-FLOOR` до этапа 5) и добавить:

- `test_the_readme_is_russian_and_names_local_verification` — README
  `plugins/unica/opencode/README.md`: русские заголовки «Локальная проверка
  собранного пакета» и «Установка из npm»; `npm install --ignore-scripts`;
  `file://`; `node_modules/@apshendev/unica-opencode`; `opencode debug skill`;
  `opencode mcp list`; `1.18.22` и «или новее»; «пока не опубликован».
- `test_the_readme_documents_ownership_platform_and_caches_in_russian` —
  `mcp.unica`; «заменяется»; `Windows x64`; `Linux x64`;
  `UNICA_RUNTIME_CACHE_DIR`; `UNICA_PROVIDER_STATE_DIR`; предупреждение о
  долгом первом старте.
- `test_the_packed_tarball_carries_the_local_verification_readme` — в реальном
  `.tgz` (после `npm pack`) `package/README.md` содержит команды локальной
  проверки.

Переписанный floor-тест читает тот же README и адаптирует утверждения под
русский текст: пол `1.18.22`, «или новее», перезапуск, первый старт; проверка
адаптера на отсутствие потолка версий (`assertNotIn("opencode-ai@", adapter)`,
`assertNotIn("OPENCODE_VERSION", adapter)`) остаётся без изменений.

Ожидаемое падение: английский README без локального раздела.

> Выполнено: 2026-08-25 16:02 (2.1 — RED: 4 ожидаемых падения на английском README)

### 2.2. Зелёный: русский README

Переписать `plugins/unica/opencode/README.md` на русском. Структура:

1. Статус: npm-пакет `@apshendev/unica-opencode` пока не опубликован; рабочий
   способ — локальная проверка собранного `.tgz`.
2. «Локальная проверка собранного пакета» — полный рецепт шага 5 документа
   `docs/plans/2026-08-25-opencode-local-test-fix-steps.md` (файл уже
   перенесён этапом 0): сборка `.tgz` (`package-unica-opencode.py` от thin-корня
   tag-run), пустой consumer, `npm init -y`,
   `npm install --ignore-scripts <абсолютный путь к .tgz>`, `opencode.json` с
   абсолютным `file://` URI установленного
   `node_modules/@apshendev/unica-opencode`, изоляция env
   (`OPENCODE_CONFIG_DIR`, XDG-переменные, `UNICA_RUNTIME_CACHE_DIR`,
   `UNICA_PROVIDER_STATE_DIR`), OpenCode `1.18.22` или новее, перезапуск,
   `opencode debug skill`, `opencode mcp list`, ожидание `unica connected`,
   предупреждение о холодной загрузке runtime.
3. «Установка из npm» — вступает после первой публикации:
   `"plugin": ["@apshendev/unica-opencode"]`, пин версии обычным
   npm-синтаксисом.
4. «Что делает адаптер» — skills один раз, владение `mcp.unica` (запись
   заменяется), прямой запуск упакованного bootstrap, без нативных обёрток.
5. «Поддерживаемые платформы» — Windows x64; Linux x64 best-effort; остальные
   — явный отказ при инициализации.
6. «Первый запуск и кеши» — бюджет холодной доставки; адреса кешей;
   `UNICA_*` overrides.
7. Лицензия.

Статус «пока не опубликован» — временный: этап 7.5 заменяет его после живого
prerelease; тест этапа 2.1 сформулирован под текущий статус и обновляется
этапом 7.5 тем же PR, что и README.

> Выполнено: 2026-08-25 16:02 (2.2 — русский README по структуре 1–7 написан)

### 2.3. Красный: обнаруживаемость

Новый тест `test_the_opencode_guide_is_reachable_from_both_readmes` (в
`tests/ci/test_package_unica_opencode.py`):

- корневой `README.md` содержит раздел «OpenCode» со ссылкой на
  `plugins/unica/opencode/README.md`;
- `plugins/unica/README.md` содержит явную ссылку на тот же файл;
- `plugins/unica/package.json` `homepage` равен
  `https://github.com/apshendev/unica/blob/main/plugins/unica/opencode/README.md`.

Ожидаемое падение: ссылок нет, homepage ведёт на корень.

> Выполнено: 2026-08-25 16:02 (2.3 — RED: 'OpenCode' not found в корневом README)

### 2.4. Зелёный

- Корневой `README.md`: раздел «OpenCode» после «Claude Code» — статус
  (локальный candidate; npm-публикация готовится), ссылка на руководство.
- `plugins/unica/README.md`: секция «OpenCode» со ссылкой.
- `plugins/unica/package.json`: `homepage` как выше.

> Выполнено: 2026-08-25 16:02 (2.4 — разделы OpenCode и homepage установлены)

### 2.5. Проверка этапа

```text
python -m unittest tests.ci.test_package_unica_opencode -v
```

Критерии ревью 4 и 5 закрыты: README русский, локальный способ описан,
`staging/README.md` порождается байт-в-байт (существующий ассерт остаётся
зелёным), обе ссылки и homepage закреплены тестом.

> Выполнено: 2026-08-25 16:02 (2.5 — tests.ci.test_package_unica_opencode: Ran 11 tests, OK)

---

## Этап 3. Процессный enabler: штамп замены product-правил (prereq замечания 8; R1, R3)

Контракт сегодняшнего дня: `immutability.py` разрешает штамп
`(status: superseded, superseded-by)` только решениям и только со скаляром;
правила `superseded-by` не несут вовсе. Разрешённый штамп правила — смена
`status: active → superseded` плюс добавление отсутствующего поля
`superseded-by` со списком преемников, без иных изменений. Перезаземление
действующего правила (смена поля `decision`) после этого этапа запрещено:
замена идёт штампом старого правила плюс новыми записями-преемниками под
новыми решениями.

Владелец жизненного цикла — процессное `DEC.2026-08-19.PRODUCT-RECORD-IS-HISTORY`;
новое решение не заводится, процессные записи обновляются свободно.

### 3.1. Красный: `tests/arch/test_product_immutability.py`

Фикстура правила воспроизводит текущую форму: front matter БЕЗ поля
`superseded-by`.

Один агрегатный тест формы штампа (единый фальсификатор будущей записи
`INV.REGISTRY.PRODUCT-RULE-SUPERSESSION-STAMP`, все сценарии — subTest'ы):

- `test_the_rule_supersession_stamp_shape` — покрывает:
  - положительный штамп `status: active → superseded` + добавление
    `superseded-by: [INV.X.Y, INV.X.Z]` принимается;
  - штамп с правкой тела отвергается;
  - штамп, меняющий вдобавок `check`/`scope`/`decision`/`governs`/`id`,
    отвергается — в том числе перезаземление на новое решение;
  - `status: superseded` без добавления списка отвергается;
  - `superseded-by` при `status: active` отвергается;
  - цепочка: в одном коммите штамп `A → [B]`, в следующем — штамп `B → [C]`;
    исторический штамп A остаётся валидным без повторной правки A.
  Сегодня RED: штамп правил не разрешён вовсе.

Сопровождающие изменения существующих тестов (источники R1):

- `test_an_active_realized_product_decision_is_a_ground`,
  `test_an_active_product_decision_with_an_async_python_method_is_a_ground`,
  `test_an_active_product_decision_with_an_attributed_rust_function_is_a_ground`
  — удаляются: они закрепляют разрешённое перезаземление, которое этот этап
  запрещает. Вместо них — негативный
  `test_regrounding_an_existing_rule_is_refused` (правило с изменённым полем
  `decision` на новое валидное решение — offender).
- Десять тестов вида `test_an_active_decision_with_*_is_not_a_ground` —
  сохраняются как прямые юнит-проверки `_ground_error` на тех же фикстурах
  (механизм проверки основания остаётся нужен для surface-изменений):
  переименовать в `test_a_surface_ground_with_*_is_refused` и вызывать
  `_ground_error` напрямую; положительный
  `test_surface_ledger_change_with_new_wire_ground_is_allowed` остаётся.
- `test_editing_a_product_rule_without_a_new_ground_is_caught` сохраняется под
  своим именем (check действующей записи
  `INV.REGISTRY.PRODUCT-RULE-NEEDS-GROUND`): обычная правка без штампа
  по-прежнему отвергается.

> Выполнено: 2026-08-25 16:21 (3.1 — RED подтверждён: 'positive stamp is accepted' и 'chained stamps stay valid' падают как «продуктовое правило изменено без нового решения о причине»; test_regrounding_an_existing_rule_is_refused падает 0 != 1; ассерт сообщения обновлён на «без штампа замены»; 10 тестов переименованы в test_a_surface_ground_with_*_is_refused с прямым вызовом _ground_error)

### 3.2. Красный: `tests/arch/test_registry.py` (шов `validation_errors`)

Сочетания полей — дело схемы реестра, а не сравнения с базой:

- `test_a_superseded_rule_without_a_successor_is_caught`;
- `test_an_active_rule_cannot_carry_a_successor`;
- `test_rule_supersession_targets_must_exist`;
- `test_rule_supersession_targets_must_be_rules` — цель не может быть
  решением;
- `test_rule_supersession_is_mutual` — расширение существующего
  `test_supersession_is_mutual`: каждый преемник-правило несёт `supersedes`,
  включающий заменённое правило;
- цель преемника может быть `active` или `superseded` (цепочки A → B → C
  легальны) — закрепляется фикстурами этих тестов.

Все RED на текущем коде: парсер правил не знает `superseded-by`-список,
валидатор не различает эти состояния. Для новых полей фикстур RED — это
падение парсинга/валидации, а не поведенческий дефект; наблюдаемое падение
фиксируется в выводе этапа.

> Выполнено: 2026-08-25 16:21 (3.2 — RED подтверждён: все 5 новых тестов validation_errors падают False is not true — валидатор не различает состояния; существующий test_supersession_is_mutual расширен списочной формой)

### 3.3. Зелёный

- `scripts/arch/immutability.py`:
  - ветка правил: разрешена ровно комбинация
    `{status: active → superseded, +superseded-by: непустой список}`; набор
    полей после правки отличается от исходного только добавленным
    `superseded-by`; тело и прочие поля побайтово неизменны; всё остальное,
    включая перезаземление, — offender;
  - решения сохраняют скалярную форму `superseded-by`;
  - механизм `_ground_error`/`introduced` остаётся только для
    surface-изменений `arch/tool-surface.md`.
- `scripts/arch/registry.py`: `superseded-by` правила парсится как список;
  валидация — цель существует, является правилом, взаимность через `supersedes`
  преемника; статус цели — `active` или `superseded`; неактивное правило
  продолжает ссылаться на своего (возможно superseded) владельца — reciprocity
  владельца не трогается; проверка «active rule cites a non-active decision»
  по-прежнему касается только активных правил.
- Согласование процессных записей с новой моделью (источник R1):
  - `arch/decisions/2026-08-19-product-record-is-history.md` (процессное,
    правится свободно): проза «Правило править можно — вместе с решением…»
    заменяется на «Правило меняют только заменой: штамп плюс преемники»;
    `establishes` += `INV.REGISTRY.PRODUCT-RULE-SUPERSESSION-STAMP`;
  - `arch/invariants/INV.REGISTRY.PRODUCT-RULE-NEEDS-GROUND.md` (процессное):
    тело сужается до «правка продуктового правила без штампа замены
    отвергается»; `check` не меняется;
  - `arch/README.md`, раздел «Как менять»: пункт «Правило править можно…»
    переписан под модель «только замена».
- Новая запись (полный front matter; источник R2):

  ```yaml
  id: INV.REGISTRY.PRODUCT-RULE-SUPERSESSION-STAMP
  status: active
  governs: process
  decision: DEC.2026-08-19.PRODUCT-RECORD-IS-HISTORY
  check: tests/arch/test_product_immutability.py::test_the_rule_supersession_stamp_shape
  scope: [docs]
  ```

  Тело заявляет только форму неизменяемого штампа правила: разрешённый
  переход, запрет правки тела и иных полей, запрет перезаземления, легальность
  цепочек — ровно то, что покрывает агрегатный `check` субтестами (источник
  R3). Схемные ограничения (существование/вид/взаимность целей) проверяются
  тестами 3.2 и в заявку этой записи не входят.
- `python scripts/arch/registry.py --write-index`.

> Выполнено: 2026-08-25 16:21 (3.3 — зелёная реализация immutability.py/registry.py, процессные записи согласованы, INV.REGISTRY.PRODUCT-RULE-SUPERSESSION-STAMP создана, индекс перегенерирован; сопутствующее: стражу добавлен якорь последнего принятого состояния origin/main — историческая перезаземлённая VERSION-LOCKSTEP из d4734f54 иначе делала upstream/main красной; механизм покрыт фикстурным test_an_edit_accepted_on_the_trusted_tip_is_history_not_a_live_change)

### 3.4. Проверка

```text
python -m unittest discover -s tests/arch -v
python scripts/arch/registry.py --check
python scripts/arch/fate.py
python scripts/arch/immutability.py --base origin/main
python scripts/arch/immutability.py --base upstream/main
```

Immutability выполняется против обеих баз: `origin/main` содержит текущие
OpenCode/npm-записи (их будущие штампы обязаны сверяться), `upstream/main` —
база из критерия ревью 8. Продуктового поведения не меняется; после этапа в
реестре нет двух active-правил с противоположными требованиями к правке
product-правил (источник R1).

> Выполнено: 2026-08-25 16:21 (3.4 — Ran 122 tests OK; registry --check, fate (233 subjects), immutability против origin/main (218 записей) и upstream/main (205 записей) — все зелёные)

---

## Этап 4. Релизный контур: staging → smoke → promotion (замечания 1, 2, 3, 7; R4–R6)

### 4.1. Smoke привязан к установленному package root (замечание 3; R6)

Существующие тесты `tests/ci/test_smoke_opencode_consumer.py` перестраиваются
вместе с verifier'ом:

- `VerifySkillsTests.run_verify` получает `plugin_root` и `target`; все
  положительные фикстуры навыка получают реальные поля `location` вида
  `<plugin-root>/skills/<name>` (в синтаксисе, соответствующем target);
- `test_string_entries_are_accepted_as_names` заменяется негативным
  `test_string_entries_are_refused` — строки больше не принимаются.

Красные тесты (`VerifySkillsTests`):

- `test_a_skill_listing_without_locations_is_refused` — объекты без
  `location` отвергаются: каждый ожидаемый skill обязан быть объектом с
  непустым `location`;
- `test_a_skill_location_outside_the_plugin_root_is_refused` — нормализованный
  `location` вне `<plugin-root>/skills` отвергается;
- `test_skill_locations_from_two_roots_are_refused` — все нормализованные
  `location` обязаны давать один установленный root.

Красные тесты (`VerifyMcpTests`; helper `run_verify` теперь всегда передаёт
`--plugin-root` и `--target`, поэтому негативные тесты доходят до семантической
проверки, а не падают на argparse):

- `test_a_bootstrap_outside_the_installed_package_root_is_refused` — блок
  `unica connected` с деталью `C:\tools\unica-bootstrap.exe run --plugin-root
  C:\tools` при `--plugin-root
  C:\consumer\node_modules\@apshendev\unica-opencode --target win-x64` обязан
  давать SystemExit с семантическим сообщением;
- `test_a_linux_bootstrap_outside_the_installed_package_root_is_refused` —
  POSIX-негатив (источник R6): блок с деталью
  `/tools/unica-bootstrap run --plugin-root /tools` при `--plugin-root
  /consumer/node_modules/@apshendev/unica-opencode --target linux-x64`
  отвергается;
- `test_the_packaged_bootstrap_under_the_plugin_root_is_accepted` —
  положительный: команда
  `<plugin-root>\bootstrap\bin\win-x64\unica-bootstrap.exe run --plugin-root
  <plugin-root>`; отдельные subTest'ы `--target linux-x64` с
  `bootstrap/bin/linux-x64/unica-bootstrap`;
- `test_a_foreign_target_layout_is_refused` —
  `<plugin-root>\bootstrap\bin\linux-x64\unica-bootstrap.exe` при
  `--target win-x64` отвергается;
- cross-host фикстуры: Windows-стиль пути проверяется при `--target win-x64`,
  POSIX-стиль при `--target linux-x64` в одном процессе; suite даёт одинаковый
  результат на Windows и Linux независимо от ОС прогона.

Зелёное в `scripts/ci/smoke-opencode-consumer.py`:

- ОБА подкоманды — `verify-skills` и `verify-mcp` — получают обязательные
  `--plugin-root` и `--target {win-x64,linux-x64}` (источник R6);
- нормализация зависит от target, а не от ОС прогона: для `win-x64` —
  `ntpath`/`PureWindowsPath` (принимает `/` и `\`, сравнение
  регистронезависимо через `casefold`), для `linux-x64` —
  `posixpath`/`PurePosixPath`;
- `verify-mcp`: в записи `unica` первый элемент деталей — команда; её
  покомпонентный разбор обязан равняться
  `<plugin-root>/bootstrap/bin/<target>/unica-bootstrap(.exe)` в нормализации
  target, далее `run --plugin-root <plugin-root>` с тем же нормализованным
  root;
- `verify-skills`: каждый ожидаемый skill — объект с непустым `location`;
  нормализованный `location` покомпонентно лежит под `<plugin-root>/skills`;
  все нормализованные `location` дают один root;
- `main()` передаёт аргументы; шов CLI расширяется, не заменяется.

Красный workflow-тест → зелёный: в
`test_opencode_consumer_smoke_gates_the_release` добавить утверждения, что ОБА
`verify-*` вызова получают
`--plugin-root "$RUNNER_TEMP/opencode-consumer/node_modules/@apshendev/unica-opencode"`
и `--target` (`win-x64`/`linux-x64` по job'у), и что
`opencode mcp list | tee mcp.txt` выполняется в блоке с `set -euo pipefail`.
Затем в `.github/workflows/unica-plugin-release.yml` (оба smoke-job'а):

- шаг установки пакета заменяется на доказуемую npm-схему (см. 4.1.1);
- шаг Verify: `--plugin-root` на установленный consumer-пакет и `--target`
  для обеих подкоманд;
- шаг Collect mcp: `set -euo pipefail; opencode mcp list | tee mcp.txt`.

#### 4.1.1. Установка потребителя в smoke

Текущий `opencode plugin "@apshendev/unica-opencode@${version}"` не создаёт
доказуемого пути `node_modules/@apshendev/unica-opencode`. Заменить в обоих
smoke-job'ах на схему локальной процедуры:

```bash
set -euo pipefail
version="$(python -c 'import json; print(json.load(open("plugins/unica/package.json"))["version"])')"
consumer="${RUNNER_TEMP}/opencode-consumer"
mkdir -p "$consumer"
cd "$consumer"
npm init -y
npm install --ignore-scripts "@apshendev/unica-opencode@${version}"
plugin_root="${consumer}/node_modules/@apshendev/unica-opencode"
plugin_uri="$(node -e 'const p=require("path").resolve(process.argv[1]); console.log(require("url").pathToFileURL(p).href)' "$plugin_root")"
printf '{"plugin":["%s"]}\n' "$plugin_uri" > opencode.json
```

Точная версия из реестра, `--ignore-scripts`, абсолютный `file://` URI.
Тест 4.1 закрепляет эти строки (`npm install --ignore-scripts`,
`pathToFileURL`/`file://`, отсутствие `opencode plugin "` в блоке установки) и
что checkout `plugins/unica` не используется как доказательство содержимого.
> Выполнено: 2026-08-25 17:12 (4.1 — RED→GREEN: verifier и тесты переписаны под --plugin-root/--target обеих подкоманд (21 тест); workflow-ассерты 4.1 в составе 4.5)


### 4.2. Staging dist-tag (замечание 1, первая половина)

Красный тест в `tests/ci/test_publish_unica_opencode.py`:

- `test_stable_and_prerelease_publish_under_the_staging_dist_tag` — один
  агрегатный тест с subTest `stable`/`prerelease`: оба публикуются с
  `["--tag", "staging"]`; после успешного publish идёт visibility-проверка
  (см. 4.3), поэтому `FakeProcess` расширяется очередью ответов на один
  префикс (первый `npm view` — E404, второй — URL) вместо одного кортежа.

Существующий `test_a_tagged_fork_release_publishes_with_provenance`
адаптируется (`--tag staging`, visibility-вызовы после успеха) и сохраняется
под тем же именем; `test_a_prerelease_publishes_under_the_next_dist_tag`
переименовывается в `test_a_prerelease_never_publishes_under_next` —
архитектурные записи на это имя не ссылаются.

Дополнительно:

- `test_the_staging_tag_literal_is_shared_by_stage_and_promotion` — литерал
  `staging` одинаков в `publish-unica-opencode.py` и
  `promote-unica-opencode.py` (паттерн закрепления `FORK_REPOSITORY`).

Зелёное в `scripts/ci/publish-unica-opencode.py`:

- `STAGING_DIST_TAG = "staging"`, `PRERELEASE_DIST_TAG` удалить;
- `publish_argv` всегда содержит `["--tag", STAGING_DIST_TAG]`;
- docstring: публикация только готовит кандидата; `latest`/`next` двигает
> Выполнено: 2026-08-25 17:12 (4.2 — STAGING_DIST_TAG='staging' в publish-скрипте, стабильный и пре-релиз идут под staging; тест test_stable_and_prerelease_publish_under_the_staging_dist_tag)
  promotion.


### 4.3. Ожидание registry visibility (замечание 2; R3)

Красный агрегатный тест — ЕДИНЫЙ фальсификатор записи
`INV.PKG.NPM-REGISTRY-VISIBILITY` (источник R3: один check на всю заявку):

- `test_a_successful_publish_waits_for_registry_visibility` — один тест,
  покрывающий subTest'ами все сценарии:
  - успех: после returncode 0 первый `npm view` E404, второй отдаёт URL,
    SHA-512 байтов реестра совпадает с кандидатом → успех;
  - постоянный E404: попытки исчерпаны → SystemExit с сообщением про
    visibility timeout;
  - `npm view` вернул не-JSON → SystemExit;
  - `npm view` вернул JSON-строку, не являющуюся URL (например `"banana"`) →
    SystemExit (текущий `registry_tarball_url` пропускает такую строку);
  - SHA-512 расходится → SystemExit;
  - rerun-ветка использует ту же проверку байтов.

Число попыток и пауза — аргументы функции со значениями по умолчанию, чтобы
тесты не ждали. Существующие
`test_a_rerun_is_accepted_only_with_identical_registry_bytes` (check
заменяемой записи `INV.PKG.NPM-RERUN-INTEGRITY`) и
`test_a_publish_failure_without_a_published_version_stays_failed` адаптируются
к staging-контуру и сохраняются под своими именами.

Зелёное в `publish-unica-opencode.py`:

- после успешного `npm publish` — bounded-цикл
  `registry_tarball_url(NPM_PACKAGE_NAME, version)` → download → SHA-512 ==
  кандидат; иначе SystemExit;
> Выполнено: 2026-08-25 17:12 (4.3 — wait_for_registry_visibility c bounded-опросом и побайтовой сверкой; timeout/не-JSON/не-URL/расхождение фатальны; агрегатный test_a_successful_publish_waits_for_registry_visibility)
- rerun-ветка переиспользует ту же функцию сравнения байтов.


### 4.4. Promotion-скрипт (замечание 1, вторая половина)

Красные тесты — новый `tests/ci/test_promote_unica_opencode.py`. Каркас как у
`test_publish_unica_opencode.py` (загрузка модуля, `FakeProcess` с очередью,
`FORK_ENV`), но кандидат — настоящий gzip tar, собранный фикстурой через
`tarfile` (`w:gz`) с валидным `package/package.json` (имя/версия) и
`package/runtime-manifest.json`; те же байты архива возвращаются как
registry-ответ. Positive-тесты реально распаковывают архив; негативные
`test_promotion_refuses_when_no_tarball_is_present`,
`test_promotion_refuses_when_two_tarballs_are_present`,
`test_promotion_refuses_a_corrupt_tarball` дают SystemExit до любого npm
вызова.

Сценарии:

- `test_the_stable_release_promotes_latest`;
- `test_a_prerelease_promotes_next`;
- `test_an_already_promoted_version_is_idempotent` — цель уже равна версии,
  ноль вызовов `dist-tag add`;
- `test_promotion_refuses_to_move_a_dist_tag_backwards` — один агрегатный
  фальсификатор forward-only: отказ обратного хода + полная матрица
  SemVer-порядка (включая `0.13.0-rc.1 < 0.13.0`, сортировку префиксов и
  числовых компонентов) как subTest'ы этого же теста;
- `test_promotion_refuses_an_unpublished_version` — нет `dist.tarball` →
  «stage did not complete»;
- `test_promotion_refuses_when_the_package_is_missing` — E404 dist-tags →
  сообщение про bootstrap-prerequisite;
- `test_promotion_gates_mirror_publishing` — upstream/не-push/не-`refs/tags/v
  <version>` → отказ до любого npm-вызова; нет `NODE_AUTH_TOKEN` → отказ
  fail-closed с именем секрета `NPM_PROMOTION_TOKEN`;
- `test_promotion_never_publishes` — ни в одном сценарии нет `npm publish`;
- `test_promotion_rereads_dist_tags_after_the_write` — postcondition: точное
  значение цели после записи.

Зелёное — новый `scripts/ci/promote-unica-opencode.py`:

- вход — `--npm-root` (артефактный каталог promotion-job'а); в нём обязан
  лежать ровно один `.tgz`, имя/версия читаются из распакованного
  `package/package.json`;
- валидация гейтов как в publish (репозиторий/событие/ref/identity) до
  первого вызова npm;
- подтверждает, что реестр отдаёт эту версию байт-идентично артефакту;
- читает `dist-tags --json`, цель `latest` (stable) / `next` (prerelease);
- SemVer-precedence comparator в модуле (не `sort -V`);
- единственная мутация — `npm dist-tag add <name>@<version> <target>`;
> Выполнено: 2026-08-25 17:12 (4.4 — scripts/ci/promote-unica-opencode.py + tests/ci/test_promote_unica_opencode.py: настоящий gzip-tar фикстурный кандидат, SemVer-компаратор в модуле, единственная мутация npm dist-tag add, перечитывание postcondition; 12 тестов)
- перечитывает dist-tags и требует точного postcondition.


### 4.5. Workflow (замечания 1, 3; R4, R5)

Красные тесты в `tests/ci/test_unica_workflow.py`.

Сохраняемые и адаптируемые (на них ссылаются действующие и будущие
superseded-записи — исторические check обязаны разрешаться):

- `test_opencode_npm_publication_is_fork_gated_and_trusted` (check решения
  `DEC.2026-08-25.NPM-TRUSTED-PUBLICATION`) — адаптируется к новому контуру:
  publish job без токенов, staging, артефакт, promote job существует;
- `test_opencode_consumer_smoke_gates_the_release` (check
  `INV.CI.OPENCODE-CONSUMER-SMOKE`) — расширяется утверждениями 4.1
  (installed root, `--target` у обеих подкоманд, pipefail, npm-схема
  установки).

Новые:

- `test_opencode_npm_publication_stages_smokes_then_promotes`:
  - publish job: `id-token: write`, `contents: read`, нет `NPM_PROMOTION_TOKEN`
    и `NODE_AUTH_TOKEN`, нет `dist-tag`;
  - publish job выгружает артефакт: `actions/upload-artifact@v7` (источник
    R14: мажор v8 у upload-artifact не существует; v7 — действующая версия в
    workflow и его контракте, v8 есть только у download-artifact), имя
    `opencode-npm-candidate`, путь — единственный `.tgz` из `dist/npm`,
    `retention-days: 1`, `compression-level: 0`;
  - новый job `promote-opencode-npm`, шаги в порядке (источник R5):
    1. `actions/checkout@v7`;
    2. `actions/setup-python@v7` (`python-version: "3.12"`);
    3. `actions/setup-node@v7` (`node-version: "24"`,
       `registry-url: https://registry.npmjs.org`) — npm-токен из
       `NODE_AUTH_TOKEN` работает только при настроенном registry;
    4. `actions/download-artifact@v8` (name `opencode-npm-candidate`, path
       `dist/npm`);
    5. шаг promotion: `NODE_AUTH_TOKEN: ${{ secrets.NPM_PROMOTION_TOKEN }}`
       только на уровне шага; вызывает `scripts/ci/promote-unica-opencode.py`;
       без `id-token`;
  - job-контракт: `needs: [publish-opencode-npm, smoke-opencode-windows,
    smoke-opencode-linux]`, `if: always() &&
    needs.publish-opencode-npm.result == 'success' &&
    needs.smoke-opencode-windows.result == 'success' && push && tag && fork`
    — Linux в `needs` ждёт отчёта, но его результат не гейтит;
    `permissions: contents: read`; `environment: npm-promotion`;
    `timeout-minutes: 10`;
  - порядок: smokes нуждаются в publish; promote нуждается в smokes;
  - добавить promote в
    `test_conditional_pipeline_breaks_transitive_skip_propagation`;
- `test_opencode_promotion_credentials_are_isolated_from_publishing`
  (источник R4; переименован с «scoped/protected») — заявляет только
  статически проверяемое: у publish job нет `NODE_AUTH_TOKEN` и
  `NPM_PROMOTION_TOKEN` ни на каком уровне; promotion читает `NODE_AUTH_TOKEN`
  только из environment secret и только в шаге promotion; promotion job
  объявляет `environment: npm-promotion`. Ни «package-scoped», ни «protected»
  в статическую заявку не входят: scope токена и защита Environment
  проверяются живым evidence этапа 7.4 и проза решения;
- `test_the_consumer_installs_the_exact_registry_version` — блок установки
  обоих smoke-job'ов ставит `@apshendev/unica-opencode@<version>` через
  `npm install --ignore-scripts`, без `opencode plugin`, с `file://` URI;
- `test_windows_smoke_blocks_the_release` — у Windows job нет
  `continue-on-error`, promotion требует
  `needs.smoke-opencode-windows.result == 'success'`;
- `test_linux_smoke_is_best_effort` — три свойства в одном тесте: Linux job
  сохраняет `continue-on-error: true`; promotion включает Linux в `needs`;
  условие promotion не проверяет результат Linux;
- `test_every_pull_request_gets_a_stable_aggregate_gate`:
  `unica-ci.needs` += `promote-opencode-npm`;
- `test_heavy_and_external_jobs_have_timeouts`: `promote-opencode-npm: 10`.

Зелёное в `.github/workflows/unica-plugin-release.yml`:

- display name publish job → «Stage OpenCode npm candidate (staging)»; id
  прежний;
- шаг Upload artifact после сборки кандидата;
- новый job `promote-opencode-npm` по контракту тестов (шаги 1–5 в порядке;
  Linux остаётся в `needs`, `continue-on-error: true` у Linux job не
  снимается);
> Выполнено: 2026-08-25 17:12 (4.5 — workflow: publish → 'Stage OpenCode npm candidate (staging)' + артефакт opencode-npm-candidate; smoke-job'ы на npm install --ignore-scripts + file:// URI; новый job promote-opencode-npm (5 шагов, environment npm-promotion, step-level NODE_AUTH_TOKEN из NPM_PROMOTION_TOKEN); unica-ci.needs += promote)
- `unica-ci.needs` += promote.


### 4.6. Агрегатный гейт

Красный → зелёный: `tests/ci/test_evaluate_ci_gate.py` —

- `PUBLISH_SKIPPED` += `promote-opencode-npm: skipped`;
- теговый прогон форка ждёт от promote `success` (его падение — красный
  выпуск);
- падение `promote-opencode-npm` на форке попадает в `fork.unexpected`.

`scripts/ci/evaluate-ci-gate.py`: `FORK_TAG_ONLY_JOBS +=
("promote-opencode-npm",)`.

Специальная ветка «Linux failure допустим» НЕ добавляется: Linux job
сохраняет `continue-on-error: true`, поэтому наблюдаемый через
`needs.smoke-opencode-linux.result` conclusion остаётся `success` даже при
> Выполнено: 2026-08-25 17:12 (4.6 — evaluate-ci-gate.py FORK_TAG_ONLY_JOBS += promote-opencode-npm; PUBLISH_SKIPPED расширен; падение promotion на форке — fork.unexpected)
падении шагов; видимым отчёт о сбое делает сам job.


### 4.7. Runbook (замечание 7)

`docs/release-runbook.md`, раздел OpenCode npm:

- этапирование: staging → потребители → promotion;
- одноразовый bootstrap: служебная версия `0.0.0-bootstrap.1` под dist-tag
  `bootstrap` (не `latest`/`next`), вручную с 2FA; процедура сборки — этап 7.2;
- затем trusted publisher (`apshendev/unica`, `unica-plugin-release.yml`,
  allowed action `npm publish`);
- затем package-scoped `NPM_PROMOTION_TOKEN` → только GitHub Environment
  `npm-promotion`;
- только потом первый реальный prerelease;
- предупреждение: не включать npm «disallow tokens», пока promotion использует
  токен;
> Выполнено: 2026-08-25 17:12 (4.7 — раздел OpenCode npm release-runbook'а переписан под stage→smoke→promote: bootstrap 0.0.0-bootstrap.1 под dist-tag bootstrap, trusted publisher, NPM_PROMOTION_TOKEN в environment npm-promotion, предупреждение про disallow tokens)
- deprecated bootstrap-версии и удаление её dist-tag — по мере надобности.


### 4.8. Архитектура npm-контрактов (требует этап 3)

Принцип: существующие правила не перезаземляются; замена — штамп старого
правила (по механизму этапа 3) плюс преемники под новым решением. Штамп решения
`arch/decisions/2026-08-25-npm-trusted-publication.md`: `status: superseded`,
`superseded-by: DEC.2026-08-25.NPM-DIST-TAG-PROMOTION` (тело, `realized` и
`establishes` не трогаются — исторический check
`test_opencode_npm_publication_is_fork_gated_and_trusted` остаётся
разрешимым).

Новый design-документ
`docs/design/2026-08-25-npm-dist-tag-promotion-design.md`
(заголовок `Decision: DEC.2026-08-25.NPM-DIST-TAG-PROMOTION`).

Полный front matter новых записей (источники R2, R3; адреса — строго
`путь-от-корня::имя_объявления`, без `Class::`; у каждого инварианта
`decision`/`check`/`scope`, у каждого контракта дополнительно
`version`/`producer`/`consumers`; каждый преемник несёт `supersedes`, старое
правило — reciprocal `superseded-by` списком):

| Запись | Вид | decision | check | scope | supersedes |
| --- | --- | --- | --- | --- | --- |
| `DEC.2026-08-25.NPM-DIST-TAG-PROMOTION` | решение | — | — | — | governs: product; realized: `tests/ci/test_unica_workflow.py::test_opencode_npm_publication_stages_smokes_then_promotes`; supersedes: `[DEC.2026-08-25.NPM-TRUSTED-PUBLICATION]`; establishes: все INV ниже |
| `INV.PKG.NPM-STAGING-DIST-TAG` | инвариант | DEC выше | `tests/ci/test_publish_unica_opencode.py::test_stable_and_prerelease_publish_under_the_staging_dist_tag` | [pkg, ci] | — |
| `INV.PKG.NPM-PUBLICATION-FORK-TAG-OIDC` | инвариант | DEC выше | `tests/ci/test_unica_workflow.py::test_opencode_npm_publication_is_fork_gated_and_trusted` | [pkg, ci] | — |
| `INV.CI.NPM-FORK-ONLY-CONTOUR` | инвариант | DEC выше | `tests/ci/test_evaluate_ci_gate.py::test_the_fork_expects_npm_publication_and_upstream_skips_it` | [ci] | — |
| `INV.PKG.NPM-CREDENTIAL-SPLIT` | инвариант | DEC выше | `tests/ci/test_unica_workflow.py::test_opencode_promotion_credentials_are_isolated_from_publishing` | [pkg, ci] | — |
| `INV.PKG.NPM-REGISTRY-VISIBILITY` | инвариант | DEC выше | `tests/ci/test_publish_unica_opencode.py::test_a_successful_publish_waits_for_registry_visibility` | [pkg, ci] | — |
| `INV.PKG.NPM-PROMOTION-FORWARD-ONLY` | инвариант | DEC выше | `tests/ci/test_promote_unica_opencode.py::test_promotion_refuses_to_move_a_dist_tag_backwards` | [pkg, ci] | — |
| `INV.PKG.NPM-PROMOTION-IDEMPOTENT` | инвариант | DEC выше | `tests/ci/test_promote_unica_opencode.py::test_an_already_promoted_version_is_idempotent` | [pkg, ci] | — |
| `INV.PKG.NPM-RERUN-BYTE-IDENTITY` | инвариант | DEC выше | `tests/ci/test_publish_unica_opencode.py::test_a_rerun_is_accepted_only_with_identical_registry_bytes` | [pkg, ci] | — |
| `INV.CI.OPENCODE-CONSUMER-INSTALLED-ROOT` | инвариант | DEC выше | `tests/ci/test_unica_workflow.py::test_the_consumer_installs_the_exact_registry_version` | [ci] | — |
| `INV.CI.OPENCODE-CONSUMER-WINDOWS-BLOCKS` | инвариант | DEC выше | `tests/ci/test_unica_workflow.py::test_windows_smoke_blocks_the_release` | [ci] | — |
| `INV.CI.OPENCODE-CONSUMER-LINUX-BEST-EFFORT` | инвариант | DEC выше | `tests/ci/test_unica_workflow.py::test_linux_smoke_is_best_effort` | [ci] | — |

Формулировки заявок (тело каждой записи — ровно то, что фальсифицирует её
`check`; источник R3):

- `NPM-STAGING-DIST-TAG`: stable и prerelease публикуются только под
  `staging` (агрегатный subTest-тест);
- `NPM-PUBLICATION-FORK-TAG-OIDC`: только теговый пуш форка, OIDC, без
  npm-токена у publish job;
- `NPM-CREDENTIAL-SPLIT`: publish job не получает npm-токенов; promotion
  читает `NODE_AUTH_TOKEN` только в шаге promotion внутри environment
  `npm-promotion`. Scope токена и защита Environment — проза решения и живое
  evidence этапа 7.4, в заявку не входят (источник R4);
- `NPM-REGISTRY-VISIBILITY`: после успешного publish выполняется bounded
  polling точной версии с побайтовой сверкой; timeout, не-JSON, не-URL и
  расхождение байтов фатальны; rerun использует тот же механизм (агрегатный
  тест);
- `NPM-PROMOTION-FORWARD-ONLY`: назад по SemVer не двигается (агрегатная
  матрица);
- `NPM-PROMOTION-IDEMPOTENT`: повторный promotion — no-op;
- `NPM-RERUN-BYTE-IDENTITY`: rerun принят только при побайтовом совпадении;
- `OPENCODE-CONSUMER-INSTALLED-ROOT`: точная registry-версия, установленный
  root как доказательство;
- `OPENCODE-CONSUMER-WINDOWS-BLOCKS`: Windows smoke без `continue-on-error`;
  promotion требует его success;
- `OPENCODE-CONSUMER-LINUX-BEST-EFFORT`: Linux в `needs`, результат не гейтит.

Штампы старых записей (тела не трогать; `superseded-by` добавляется по
механизму этапа 3):

- `INV.PKG.NPM-PUBLICATION-GATE` → `[INV.PKG.NPM-PUBLICATION-FORK-TAG-OIDC,
  INV.CI.NPM-FORK-ONLY-CONTOUR, INV.PKG.NPM-STAGING-DIST-TAG]`;
- `INV.PKG.NPM-RERUN-INTEGRITY` → `[INV.PKG.NPM-RERUN-BYTE-IDENTITY,
  INV.PKG.NPM-REGISTRY-VISIBILITY]`;
- `INV.CI.OPENCODE-CONSUMER-SMOKE` →
  `[INV.CI.OPENCODE-CONSUMER-INSTALLED-ROOT,
  INV.CI.OPENCODE-CONSUMER-WINDOWS-BLOCKS,
  INV.CI.OPENCODE-CONSUMER-LINUX-BEST-EFFORT]`.

Недоказуемое «не удаляет тег и ассеты» переносится прозой нового решения.
Порядок `publish → smoke → promotion` доказывается агрегатным тестом,
являющимся `realized` решения; отдельная запись на порядок не заводится.
> Выполнено: 2026-08-25 17:12 (4.8 — DEC.2026-08-25.NPM-TRUSTED-PUBLICATION → superseded (штамп, тела нетронуты); новый DEC.2026-08-25.NPM-DIST-TAG-PROMOTION + 11 INV-преемников; штампы NPM-PUBLICATION-GATE/NPM-RERUN-INTEGRITY/OPENCODE-CONSUMER-SMOKE со взаимными supersedes; design-документ написан; индекс перегенерирован)
`python scripts/arch/registry.py --write-index`; стражи этапа 3 зелёные против

обеих баз.

### 4.9. Проверка этапа

```text
python -m unittest tests.ci.test_smoke_opencode_consumer -v
python -m unittest tests.ci.test_publish_unica_opencode -v
python -m unittest tests.ci.test_promote_unica_opencode -v
python -m unittest tests.ci.test_unica_workflow -v
python -m unittest tests.ci.test_evaluate_ci_gate -v
python -m unittest discover -s tests/arch -v
python -m compileall -q scripts/ci scripts/arch
python scripts/arch/registry.py --check
python scripts/arch/fate.py
python scripts/arch/immutability.py --base origin/main
python scripts/arch/immutability.py --base upstream/main
```

Никаких npm-записей: все новые тесты работают на фикстурах и mocker'ах.
> Выполнено: 2026-08-25 17:12 (4.9 — 102 CI-теста OK (smoke 21 + publish 11 + promote 12 + workflow 41 + gate 17... суммарно Ran 102 OK); tests/arch Ran 122 OK; compileall OK; registry --check OK; fate 233 subjects; immutability origin/main 218 + upstream/main 205 — зелёные)

---

## Этап 5. Ужесточение доказательств (замечания 8, 9; требует этапы 2 и 3; R2, R3, R10)

Ground-решение `DEC.2026-08-25.RULE-CLAIMS-TIGHTENED` (governs: product;
design-документ `docs/design/2026-08-25-rule-claims-tightened-design.md`
фиксирует: наблюдаемая форма контрактов не меняется — сужаются заявки
записей). `realized` решения — новый агрегатный тест
`tests/arch/test_registry.py::test_the_ten_widened_rules_are_replaced_by_narrow_successors`:
проверяет точное отображение десяти старых записей ревью 8 на перечисленных
ниже преемников (никто не забыт, лишних нет, у каждого преемника один
фальсифицирующий `check`, адреса разрешаются).

Все замены — штамп + преемник; ни одно действующее правило не редактируется и
не перезаземляется. Исторические `check` заменённых записей остаются
разрешимыми (тесты не удаляются, только адаптируются при необходимости).

### 5.1. VERSION-LOCKSTEP → три правила (замечание 9; R10)

Тесты в `tests/ci/test_version_contract.py`:

- новый `test_bump_updates_every_contract_location` — успешный бамп
  `0.12.0 → 0.13.0` обновляет все пять мест (`Cargo.toml`,
  `.codex-plugin/plugin.json`, `.claude-plugin/plugin.json`,
  `third-party/tools.lock.json`, `package.json`);
- усиленный `test_a_render_failure_leaves_every_contract_file_untouched` —
  `subTest` по каждой из пяти повреждаемых локаций; перед bump — снапшот байтов
  всех пяти; после отказа — все пять байт-в-байт неизменны.

Честная запись в PR (источник R10): ОБА теста, вероятно, зелёные сразу —
`bump()` уже рендерит все файлы до первой записи
(`scripts/dev/bump-version.py:58-89`). Дефект — недостающее доказательство, а
не поведение: красный воспроизвести нельзя, причина — отсутствие проверок,
компенсация — закрытие пробела тестами и разделение правил. Искусственное
падение не создаётся; факт немедленного зелёного фиксируется в описании PR.

Архитектурно: штамп `INV.PKG.VERSION-LOCKSTEP` → superseded-by
`[INV.PKG.VERSION-DECLARED-LOCKSTEP, INV.PKG.VERSION-BUMP-COMPLETE,
INV.PKG.VERSION-BUMP-ATOMIC]`. Front matter:

| Запись | decision | check | scope |
| --- | --- | --- | --- |
| `INV.PKG.VERSION-DECLARED-LOCKSTEP` | `DEC.2026-08-25.RULE-CLAIMS-TIGHTENED` | `tests/ci/test_version_contract.py::test_every_contract_location_declares_the_same_version` | [pkg, product] |
| `INV.PKG.VERSION-BUMP-COMPLETE` | тот же | `tests/ci/test_version_contract.py::test_bump_updates_every_contract_location` | [pkg, product] |
| `INV.PKG.VERSION-BUMP-ATOMIC` | тот же | `tests/ci/test_version_contract.py::test_a_render_failure_leaves_every_contract_file_untouched` | [pkg, product] |

> Выполнено: 2026-08-25 17:12 (5.1 — оба теста добавлены и немедленно зелёные,
> как план и предсказывал (R10): красный воспроизвести нельзя, дефект —
> недостающее доказательство; атомарность теперь subTest по всем пяти
> локациям со снапшотом байтов; test_version_contract — Ran 18 OK)

### 5.2. OPENCODE-CONFIG → пять контрактов

Штамп `CTR.HOST.OPENCODE-CONFIG` → пять преемников. Front matter (у каждого
`status: active`, `governs: product`, `decision:
DEC.2026-08-25.RULE-CLAIMS-TIGHTENED`, `supersedes` не указан в таблице —
преемники одного старого контракта перечислены в его `superseded-by` списке;
проза решения называет отображение):

| Запись | check | scope | version/producer/consumers |
| --- | --- | --- | --- |
| `CTR.HOST.OPENCODE-MCP-OWNERSHIP` | `tests/ci/test_opencode_adapter.py::test_the_adapter_takes_ownership_of_mcp_unica_and_preserves_neighbours` | [host, pkg] | 1; `plugins/unica/opencode/index.js`; [host, review, docs] |
| `CTR.HOST.OPENCODE-SKILLS-PATHS` | `tests/ci/test_opencode_adapter.py::test_the_packaged_skills_root_is_appended_once_and_others_survive` | [host, pkg] | 1; тот же producer; [host, review, docs] |
| `CTR.HOST.OPENCODE-STATE-PROCESS-OVERRIDES` | `tests/ci/test_opencode_adapter.py::test_existing_process_overrides_win_over_derived_locations` | [host, pkg] | 1; тот же; [host, docs] |
| `CTR.HOST.OPENCODE-STATE-XDG-DERIVATION` | `tests/ci/test_opencode_adapter.py::test_locations_are_derived_from_the_cache_home_when_unset` | [host, pkg] | 1; тот же; [host, docs] |
| `CTR.HOST.OPENCODE-STATE-WINDOWS-DERIVATION` | `tests/ci/test_opencode_adapter.py::test_windows_locations_derive_from_localappdata` | [host, pkg] | 1; тот же; [host, docs] |

> Выполнено: 2026-08-25 17:12 (5.2 — штамп CTR.HOST.OPENCODE-CONFIG и пять
> контрактов-преемников; все пять адресов проверок существовали и остались
> зелёными; test_opencode_adapter — Ran 10 OK)

### 5.3. PLATFORM-GATE → отказ

Штамп `INV.HOST.OPENCODE-PLATFORM-GATE` →
`INV.HOST.OPENCODE-PLATFORM-REFUSAL` (decision
`DEC.2026-08-25.RULE-CLAIMS-TIGHTENED`; check:
`tests/ci/test_opencode_adapter.py::test_unsupported_platforms_fail_during_initialization`;
scope [host, platform]). Заявка — только отказ неподдерживаемым комбинациям;
положительный выбор платформ — проза решения.

> Выполнено: 2026-08-25 17:12 (5.3 — штамп INV.HOST.OPENCODE-PLATFORM-GATE и
> INV.HOST.OPENCODE-PLATFORM-REFUSAL; положительный выбор платформ — проза
> решения)

### 5.4. CORE-PROVENANCE → три контракта

Штамп `CTR.PKG.CORE-PROVENANCE-SELECTABLE` → три преемника:

| Запись | check | scope | version/producer/consumers |
| --- | --- | --- | --- |
| `CTR.PKG.CORE-PROVENANCE-BY-BUILD-INPUT` | `tests/ci/test_package_unica_plugin.py::test_core_release_repository_override_names_the_fork_as_owner` | [ci, pkg] | 1; `scripts/ci/package-unica-plugin.py`; [review, docs] |
| `CTR.PKG.CORE-PROVENANCE-DEFAULT-ADDRESSES` | `tests/ci/test_package_unica_plugin.py::test_generated_marketplace_is_thin_pinned_and_target_neutral` | [ci, pkg] | 1; тот же; [review, docs] |
| `CTR.PKG.CORE-PROVENANCE-REFUSED-BY-MISMATCH` | `crates/unica-bootstrap/tests/manifest_contract.rs::ordinary_validation_uses_the_repository_compiled_into_the_bootstrap` | [ci, pkg] | 1; `crates/unica-bootstrap`; [review] |

«Третий адрес требует новой записи» остаётся прозой решения
`DEC.2026-08-24.CORE-PROVENANCE-NAMED-BY-BUILD` (не переписывается).

> Выполнено: 2026-08-25 17:12 (5.4 — штамп CTR.PKG.CORE-PROVENANCE-SELECTABLE
> и три контракта-преемника, включая Rust-адрес manifest_contract.rs;
> test_package_unica_plugin — Ran 43 OK)

### 5.5. CLIENT-FLOOR → документированный пол

Штамп `INV.HOST.OPENCODE-CLIENT-FLOOR` →
`INV.HOST.OPENCODE-CLIENT-FLOOR-DOCUMENTED` (decision
`DEC.2026-08-25.RULE-CLAIMS-TIGHTENED`; check:
`tests/ci/test_package_unica_opencode.py::test_the_candidate_documents_a_version_floor_not_a_ceiling`
— имя сохранено этапом 2, check действующей записи не ломается между этапами
2 и 5; scope [host, docs]). Заявка — только задокументированный минимум;
утверждение об отсутствии потолка остаётся прозой решения.

> Выполнено: 2026-08-25 17:12 (5.5 — штамп INV.HOST.OPENCODE-CLIENT-FLOOR и
> INV.HOST.OPENCODE-CLIENT-FLOOR-DOCUMENTED; имя check сохранено с этапа 2)

### 5.6. SHARED-SURFACE → форма экспорта

Штамп `INV.HOST.OPENCODE-SHARED-SURFACE` →
`INV.HOST.OPENCODE-SINGLE-CONFIG-HOOK` (decision
`DEC.2026-08-25.RULE-CLAIMS-TIGHTENED`; check:
`tests/ci/test_opencode_adapter.py::test_the_module_exports_one_plugin_whose_only_hook_is_config`;
scope [host, wire]). Заявка — один плагин, единственный хук `config`;
происхождение общей поставки и отсутствие нативных обёрток — проза решения.

> Выполнено: 2026-08-25 17:12 (5.6 — штамп INV.HOST.OPENCODE-SHARED-SURFACE и
> INV.HOST.OPENCODE-SINGLE-CONFIG-HOOK; происхождение общей поставки — проза
> решения)

### 5.7. NPM-CANDIDATE → четыре контракта (R3)

Штамп `INV.PKG.NPM-CANDIDATE-FROM-THIN-ROOT` → четыре преемника. Ревью 8
требует полный inventory, поэтому существующий тест
`test_the_candidate_carries_the_thin_root_plus_npm_metadata` ПЕРЕПИСЫВАЕТСЯ в
полное сравнение:

- обход обоих деревьев (`thin_root` и `staging`) со сбором относительных путей;
- каждый файл thin_root, КРОМЕ корневого `README.md`, присутствует в staging
  по тому же пути с теми же байтами;
- корневой `README.md` — единственное намеренное преобразование существующего
  файла (источник R15): он есть в обоих деревьях, но staging-версия
  байт-в-байт равна `plugins/unica/opencode/README.md` — упаковщик
  сознательно заменяет им продукт-README (`assemble_staging` в
  `package-unica-opencode.py`);
- настоящие добавления — ровно два класса: `package.json` (npm metadata) и
  `opencode/**` (адаптер из отслеживаемых файлов);
- всё прочее в staging — SystemExit/AssertionError.

| Запись | вид | check | scope | version/producer/consumers |
| --- | --- | --- | --- | --- |
| `CTR.PKG.NPM-CANDIDATE-COMPOSITION` | контракт | `tests/ci/test_package_unica_opencode.py::test_the_candidate_carries_the_thin_root_plus_npm_metadata` | [pkg] | 1; `scripts/ci/package-unica-opencode.py`; [review, docs] |
| `INV.PKG.NPM-CANDIDATE-DEV-MANIFEST-REFUSED` | инвариант | `tests/ci/test_package_unica_opencode.py::test_a_development_manifest_never_becomes_a_candidate` | [pkg] | — |
| `INV.PKG.NPM-CANDIDATE-VERSION-REFUSED` | инвариант | `tests/ci/test_package_unica_opencode.py::test_a_version_that_disagrees_with_the_source_is_refused` | [pkg] | — |
| `INV.PKG.NPM-CANDIDATE-BOOTSTRAP-REFUSED` | инвариант | `tests/ci/test_package_unica_opencode.py::test_a_thin_root_without_a_bootstrap_is_refused` | [pkg] | — |

Правила копирования npm-источников из отслеживаемых файлов без симлинков —
проза решения.

> Выполнено: 2026-08-25 17:12 (5.7 — штамп INV.PKG.NPM-CANDIDATE-FROM-THIN-ROOT
> на CTR.PKG.NPM-CANDIDATE-COMPOSITION + три refusal-инварианта;
> test_the_candidate_carries_the_thin_root_plus_npm_metadata переписан в полную
> инвентаризацию. Найден и закрыт тестом третий класс намеренных отличий,
> пропущенный прозой плана: тонкий корень несёт VCS-ignore файлы
> (skills/.gitignore), упаковщик сознательно удаляет их из staging; удаления —
> ровно ignore-файлы; зафиксировано в дизайн-документе. Попутно найден и
> исправлен дефект этапа 2: бэктик-путь plugins/unica/opencode/README.md в
> README плагина ломал test_all_active_packaged_documentation_links (упаковщик
> исключает opencode/ из тонкого пакета, ссылка ведёт на GitHub;
> тест этапа 2 на литерал сохранён); Ran 11 OK)

### 5.8. Проверка этапа

```text
python -m unittest tests.ci.test_version_contract -v
python -m unittest tests.ci.test_opencode_adapter -v
python -m unittest tests.ci.test_package_unica_opencode -v
python -m unittest tests.ci.test_package_unica_plugin -v
python -m unittest discover -s tests/arch -v
python scripts/arch/registry.py --check
python scripts/arch/fate.py
python scripts/arch/immutability.py --base origin/main
python scripts/arch/immutability.py --base upstream/main
```

`test_every_rule_names_a_check_that_exists` обязан пройти: исторические
check заменённых записей и решений сохранены.

> Выполнено: 2026-08-25 17:12 (5.8 — version_contract 18 OK, opencode_adapter
> 10 OK, package_unica_opencode 11 OK, package_unica_plugin 43 OK (5
> POSIX-skip — прежние), tests/arch Ran 123 OK, registry --check OK, fate 233
> subjects, immutability origin/main 218 + upstream/main 205 — зелёные;
> агрегатный тест test_the_ten_widened_rules_are_replaced_by_narrow_successors
> написал RED → GREEN; DEC.2026-08-25.RULE-CLAIMS-TIGHTENED + 18 преемников +
> дизайн-документ; arch/index.md перегенерирован)

---

## Этап 6. Планы (замечания 11, 12; R8, R9)

Текущее состояние уже содержит перенос: старые пути
`docs/code-review/2026-08-25-opencode-local-test-fix-{plan,steps}.md` удалены
из отслеживаемых (`D`), полные копии лежат в `docs/plans/` как непрослеживаемые
(`??`). `git mv` не применим — этап описывает фиксацию состоявшегося переноса
(источник R9):

- `git add` четыре файла `docs/plans/2026-08-25-opencode-*.md` (два
  перенесённых плана, ревью, настоящий план) — при условии, что этап 0 не
  сделал это раньше;
- по двум старым tracked-путям создать короткие pointer-файлы («перенесён в
  `docs/plans/<имя>`; формулировки не менялись»); неизменяемое ревью
  ссылается на старый путь — pointer сохраняет достижимость;
- формулировки перенесённых планов не меняются; в перенесённый steps-файл
  добавить датированную отметку (паттерн уже используется): шаг 4 с run
  `32766639619` superseded процедурой нового плана; `Status` не трогать;
- новый `docs/plans/2026-08-25-opencode-local-tgz-from-tag-run.md` —
  исполняемая процедура (источник R8), дословно:
  - тонкий артефакт берётся только из run, чей head SHA совпадает с
    `targetCommitish` релиза;
  - точная команда: `gh run download 31950933025 --repo IngvarConsulting/unica
    --name unica-thin-marketplace --dir .build/opencode-local/thin`;
  - проверка: run `31950933025` — event `push`, branch `v0.12.0`, head SHA
    `6f2acb27ee47b559e782003a62ac9abf8f4c7d71` == targetCommitish релиза
    `v0.12.0`;
  - ОБЯЗАТЕЛЬНЫЙ префлайт до упаковки: сравнение трёх manifest SHA (darwin/
    linux/win) с `digest` ассетов релиза; красный сигнал закреплён: артефакт
    старого run `32766639619` даёт 3/3 mismatch (`dc090553…`/`e8fb673f…`/
    `c0bb6b3e…` против `d1fc9ffe…`/`fdea1e1f…`/`3fc92984…`), правильный
    артефакт `31950933025` даёт 3/3 match;
  - одного совпадения `pluginVersion`/`release.tag` недостаточно;
  - затем сборка `.tgz` и шаги потребителя как в steps-файле;
- обновить внутренние ссылки на новые пути: pointer-файлы, раздел 2.2
  настоящего плана и любые отслеживаемые упоминания; поиск —
  `git grep -n "docs/code-review/2026-08-25"` по всему отслеживаемому дереву;
- проверка этапа:
  - `git grep -n "docs/code-review/2026-08-25"` показывает только
    pointer-упоминания и исторические записи ревью (ревью не переписывается);
  - `git status --short` по этим путям чист: один полный tracked-файл каждого
    плана, один tracked pointer на каждом старом пути;
  - `python -m unittest tests.ci.test_design_documents -v` зелёный.

---

## Этап 7. Внешние действия (только после отдельного согласования каждого шага)

### 7.0. Переоткрытие issues (источник R13)

Сразу после утверждения плана и до начала этапа 1, отдельным разрешением:

```text
gh issue reopen 3 --repo apshendev/unica --comment "..."
gh issue reopen 4 --repo apshendev/unica --comment "..."
gh issue reopen 5 --repo apshendev/unica --comment "..."
```

Комментарии ссылаются на файл ревью и этот план. #2 остаётся закрытым.
Закрытие #3–#5 возможно только после соответствующего evidence: #3 — этапы
1–3, 5 (документация, uv, архитектура), #4 — этап 4 + 7.4, #5 — этап 4 + 7.4.

### 7.1. Служебный bootstrap-пакет: процедура сборки (R7)

Продуктовый packager не годится: он требует равенства версий npm metadata,
thin manifest и release tag (`package-unica-opencode.py:55-78`). Служебный
пакет — это заявка имени в реестре, а не продукт. Процедура (выполняет
владелец, не агент):

```bash
tmp="$(mktemp -d)"
cd "$tmp"
cat > package.json <<'EOF'
{
  "name": "@apshendev/unica-opencode",
  "version": "0.0.0-bootstrap.1",
  "description": "Placeholder to claim the package name; real deliveries come from the release workflow.",
  "license": "LGPL-3.0-or-later"
}
EOF
printf '# Служебный пакет\n\nЗаявка имени для trusted publishing. Реальные версии публикует CI.\n' > README.md
npm publish --access public --tag bootstrap
```

- отдельный временный каталог вне репозитория; product version-lockstep не
  затрагивается; упаковщик плагина не используется;
- публикация вручную с 2FA только под dist-tag `bootstrap`
  (не `latest`/`next`);
- после настройки trusted publisher — `npm deprecate
  @apshendev/unica-opencode@0.0.0-bootstrap.1 "service placeholder"` и
  удаление dist-tag по мере надобности.

### 7.2. Trusted publisher

В настройках пакета на npmjs.com: trusted publisher для `apshendev/unica`,
workflow `unica-plugin-release.yml`, allowed action `npm publish`.

### 7.3. Promotion token

Package-scoped `NPM_PROMOTION_TOKEN` (создать можно только после появления
пакета); secret только в GitHub Environment `npm-promotion`; защита
Environment (required reviewers) настраивается там же — проверяется живым
прогоном этапа 7.4, статических претворений в записи нет (источник R4).

### 7.4. Первый реальный prerelease и живое доказательство (замечание 6)

Первый prerelease публикуется тегом; живой прогон проверяет:

- staging publish → оба smoke → promotion;
- тарболл реестра байт-идентичен кандидату;
- `runtime-manifest.json` опубликованного тарболла называет
  `https://github.com/apshendev/unica` в `source`/`release` (не upstream);
- у версии есть npm provenance;
- Windows consumer устанавливает точную registry-версию и проходит;
- Linux job отчитывается, но не блокирует;
- повторный запуск promotion идемпотентен (`next` не двигается);
- токен promotion — package-scoped (виден в npm UI), Environment
  `npm-promotion` защищена.

До этого пункта ни один документ не заявляет npm-доставку готовой.

### 7.5. Документация после живой публикации (источник R13)

После подтверждённого 7.4, отдельным docs-PR с собственным red/green:

- README `plugins/unica/opencode/README.md`: статус меняется на
  «опубликован», раздел «Установка из npm» становится основным, локальная
  проверка — вспомогательной;
- `test_the_readme_is_russian_and_names_local_verification` и floor-тест
  адаптируются под новый статус тем же PR;
- `test_the_packed_tarball_carries_the_local_verification_readme` проверяет
  README внутри реального `.tgz` новой версии;
- корневой README и `plugins/unica/README.md` обновляют статусную строку.

---

## Финальная проверка всего набора (R12)

```text
uv sync --locked
uv pip install -r tests/ci/requirements.txt
uv run python -m unittest discover -s tests/ci
uv run python -m unittest discover -s tests/arch -v
uv run python -m compileall -q scripts/ci scripts/arch
cargo test -p unica-bootstrap --test manifest_contract
python scripts/arch/registry.py --check
python scripts/arch/fate.py
python scripts/arch/immutability.py --base origin/main
python scripts/arch/immutability.py --base upstream/main
```

Порядок обязателен (источник R12): сначала `uv sync --locked`, затем
установка `tests/ci/requirements.txt` в проектное окружение (`lxml`, `PyYAML`,
`tree-sitter`, `tree-sitter-rust` — suite безусловно их импортирует), только
потом Python-прогоны через `uv run`. `dependencies = []` в `pyproject.toml`
сохраняется: тестовые зависимости — окружение прогона, не проекта.

Политика падений: целевые наборы и полная сюита обязаны быть зелёными.
Безымянные «существующие окруженческие падения» не допускаются. Если
окруженческое падение воспроизводится, оно называется поимённо и сравнивается
с базой безопасным способом:

- `git stash`, checkout и любые изменения основного рабочего дерева не
  используются;
- базовый прогон выполняется в отдельном detached worktree
  (`git worktree add --detach <tmp> <base>`) или временном clean clone в
  `C:\Users\inilu\AppData\Local\Temp\opencode`;
- в отчёте называются точный тест, результат HEAD, результат базы и окружение;
- после сравнения в основной рабочей директории ничего не меняется, временный
  worktree удаляется;
- дефект либо исправляется по причине (с красным тестом), либо фиксируется в
  PR-описании с доказательством равенства на базе. Общего исключения нет.

## Что не трогать

- `CLAUDE.md`, `docs/agents/`, `docs/specs/` — пользовательские.
- Формулировки перенесённых планов (только новые датированные отметки).
- Тела, `decision`-, `check`- и `realized`-поля существующих продуктовых
  arch-записей: замена идёт только штампом и преемниками; `establishes`
  принятых продуктовых решений не редактируется (процессное
  `DEC.2026-08-19.PRODUCT-RECORD-IS-HISTORY` и его процессные инварианты
  обновляются свободно как процессные).
- `publish-unica-marketplace.yml`, upstream-каталоги, Codex/Claude macOS.
- До этапа 7: никаких npm-записей, токенов, trusted publisher, тегов,
  релизов, PR и переоткрытия issues без отдельного разрешения.
- `.build/`, `dist/` не коммитить.
