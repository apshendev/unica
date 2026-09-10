# План синхронизации форка `apshendev/unica` с `IngvarConsulting/unica`

- Date: `2026-09-10`
- Status: `ready`
- Repository: `D:\orca\unica`
- Target branch: `apshendev/unica:main`
- Upstream branch: `IngvarConsulting/unica:main`
- Stack specification: `docs/specs/stack.md` отсутствует; дополнительных указаний из него нет.

## Цель

Влить актуальный `upstream/main` в `main` форка без переписывания опубликованной
истории, сохранить форк-специфичную поставку для OpenCode и npm и принять
согласованный upstream-контракт `v8-runner` 0.7.1 вместе с кодом Unica, который
умеет с ним работать.

Известное состояние на момент подготовки плана:

- локальный `main` — `f7ca89cb6a4853f4316b16798f4a3b839872f13d`;
- `origin/main` — `702c83a2ee0a06f46cc846c82737b1471c4e1920`;
- локальный `main` опережает `origin/main` на 24 коммита;
- последний удалённо наблюдавшийся `upstream/main` —
  `c2f9b950d8324d7b9a82934f18e6714cd2703559`;
- рабочее дерево было чистым;
- локальная remote-tracking ссылка `upstream/main` ещё не обновлена, поэтому
  исполнитель обязан заново зафиксировать фактический SHA после `git fetch`.

## Зафиксированные решения

1. Сначала опубликовать 24 локальных коммита в `origin/main` и дождаться
   результата базового CI.
2. Синхронизацию выполнять обычным merge, а не rebase: опубликованные коммиты
   форка и история его PR не переписываются.
3. Слияние upstream подавать отдельным PR из ветки
   `sync/upstream-<short-sha>` в `main` форка.
4. PR сливать merge-коммитом, без squash и rebase, чтобы ancestry upstream
   оставалась проверяемой.
5. Прикладной smoke на базе `D:\orca\1c_bgu20` и запуск 1С в этот план не
   входят.
6. Выпуск версии, публикация npm/marketplace и изменение release-тегов в этот
   план не входят.

## Не входит в работу

- исправление кавычек в `Usr="..."`/`Pwd="..."`;
- диагностика или исправление OOM при `/LoadConfigFromFiles`;
- исправление формы owner-записей `Form`/`Template` в XML;
- ручное обновление одного `tools.lock.json` без соответствующего upstream-кода;
- создание новой fork-only архитектурной политики без отдельного решения.

Синхронизация должна принести upstream-фикс первой загрузки отсутствующего
расширения из `v8-runner` (#54), но без прикладного smoke это подтверждается
только зафиксированным upstream-пином и контрактными тестами, а не реальным
запуском Конфигуратора. Синхронизацию нельзя описывать как доказанный фикс OOM.

## Файлы, которые могут потребовать ручного разрешения

Точный список определяется только после `git fetch` и пробного merge. Не
редактировать файл лишь потому, что он есть в этом списке: ручное изменение
допустимо только при конфликте либо при падении проверки, вызванном именно
интеграцией двух веток.

### Пин инструментов и происхождение

- `plugins/unica/third-party/tools.lock.json`
- `plugins/unica/ATTRIBUTIONS.md`
- `docs/provenance/skill-upstreams.json`
- `plugins/unica/third-party/NOTICE.md`
- `tests/ci/test_skill_provenance.py`
- `scripts/ci/check-skill-upstreams.py`
- `scripts/ci/check-attributions.py`

### Публичный и runtime-контракт

- `crates/unica-coder/src/application/mod.rs`
- `crates/unica-coder/src/application/tool_contracts.rs`
- `crates/unica-coder/src/application/operation_descriptors.rs`
- `crates/unica-coder/src/infrastructure/internal_adapters.rs`
- `crates/unica-coder/src/infrastructure/runtime_build_preflight.rs`
- `crates/unica-coder/src/infrastructure/runtime_build_fallback.rs`
- `crates/unica-coder/src/infrastructure/bundled_tools.rs`
- `tests/ci/test_unica_skills.py`
- `scripts/ci/check-tool-contracts.py`

### Поставка форка для OpenCode/npm

- `.github/workflows/unica-plugin-release.yml`
- `plugins/unica/opencode/index.js`
- `plugins/unica/opencode/README.md`
- `plugins/unica/package.json`
- `scripts/ci/package-unica-opencode.py`
- `scripts/ci/publish-unica-opencode.py`
- `scripts/ci/promote-unica-opencode.py`
- `scripts/ci/smoke-opencode-consumer.py`
- `scripts/ci/evaluate-ci-gate.py`
- `crates/unica-bootstrap/tests/manifest_contract.rs`
- `tests/ci/test_opencode_adapter.py`
- `tests/ci/test_package_unica_opencode.py`
- `tests/ci/test_publish_unica_opencode.py`
- `tests/ci/test_promote_unica_opencode.py`
- `tests/ci/test_smoke_opencode_consumer.py`
- `tests/ci/test_evaluate_ci_gate.py`
- `tests/ci/test_unica_workflow.py`

### Манифесты и lock-файлы

- `Cargo.toml`
- `Cargo.lock`
- `pyproject.toml`
- `uv.lock`
- `plugins/unica/.mcp.json`
- `plugins/unica/.codex-plugin/plugin.json`
- `plugins/unica/.claude-plugin/plugin.json`
- `scripts/ci/check-version-contract.py`
- `tests/ci/test_version_contract.py`

### Инструкции и архитектурный реестр

- `README.md`
- `plugins/unica/README.md`
- `plugins/unica/skills/**/SKILL.md`
- `plugins/unica/skills/**/references/*.md`
- `plugins/unica/references/**/*.md`
- `arch/decisions/*.md`
- `arch/invariants/*.md`
- `arch/contracts/*.md`
- `arch/index.md` — только регенерировать, не редактировать вручную

## Пошаговый план

### Этап 1. Проверить исходное состояние и создать точку восстановления

**Редактируемые файлы:** нет.

1. Проверить каталог, ветку, чистоту дерева и remotes:

   ```powershell
   git rev-parse --show-toplevel
   git status --short
   git branch --show-current
   git remote get-url origin
   git remote get-url upstream
   git rev-parse HEAD
   git rev-list --count origin/main..main
   ```

   > **Выполнено:** 2026-09-10T13:13:03+03:00 — проверка выполнена: корень `D:/orca/unica`, ветка `main`, HEAD `f7ca89cb`, 24 локальных коммита, remotes верные; единственная строка в статусе — untracked план-файл, решение о коммите подтверждено пользователем.

2. Ожидаемые значения:
   - корень — `D:/orca/unica`;
   - ветка — `main`;
   - `git status --short` не выводит строк;
   - `origin` указывает на `apshendev/unica`;
   - `upstream` указывает на `IngvarConsulting/unica`.

   > **Выполнено:** 2026-09-10T13:14:00+03:00 — все ожидаемые значения подтверждены после коммита план-файла: корень, ветка `main`, пустой `git status --short`, оба remotes верны.

3. Если HEAD отличается от указанного выше или число локальных коммитов уже не
   равно 24, не сбрасывать изменения. Записать актуальные значения и продолжать
   только после подтверждения, что новые коммиты тоже должны войти в форк.

   > **Выполнено:** 2026-09-10T13:14:00+03:00 — на момент проверки HEAD совпадал с `f7ca89cb`, коммитов было 24; актуальные значения после коммита плана: HEAD `1543b9674d7d78737148aac3cd842e6e9bd39c19`, 25 коммитов; включение нового коммита подтверждено пользователем, ничего не сброшено.

4. Создать локальную страховочную ветку от текущего HEAD:

   ```powershell
   $forkHead = git rev-parse HEAD
   $forkShort = git rev-parse --short=8 HEAD
   git branch "backup/pre-upstream-sync-$forkShort" $forkHead
   ```

   > **Выполнено:** 2026-09-10T13:14:00+03:00 — создана `backup/pre-upstream-sync-1543b967`, разрешается ровно в `1543b9674d7d78737148aac3cd842e6e9bd39c19`; дерево чистое, история не менялась.

**Критерии выполнения:** дерево чистое; SHA текущего fork HEAD записан; backup
разрешается ровно в него; история не менялась и force-операций не было.

### Этап 2. Опубликовать текущие локальные коммиты до синхронизации

**Редактируемые файлы:** нет; изменяется только удалённая ссылка `origin/main`.

1. Просмотреть все отправляемые коммиты и убедиться, что секретов и посторонних
   файлов нет:

   ```powershell
   git log --oneline --decorate origin/main..main
   git diff --stat origin/main..main
   git status --short
   ```

   > **Выполнено:** 2026-09-10T13:35:08+03:00 — 26 коммитов просмотрены (24 исходных плюс план и отметки этапа 1), дельта — только известная работа форка OpenCode/npm, arch и CI; скан паттернов секретов по `origin/main..main` нашёл только легитимные `${{ secrets.* }}`, документацию и тестовые фикстуры; дерево чистое.

2. Отправить текущий `main` без force:

   ```powershell
   git push origin main:main
   git fetch origin
   ```

   > **Выполнено:** 2026-09-10T13:35:08+03:00 — push без force `702c83a2..abdd15e4 main -> main`, fetch выполнен; force не применялся.

3. Проверить равенство ссылок:

   ```powershell
   git rev-parse main
   git rev-parse origin/main
   ```

   > **Выполнено:** 2026-09-10T13:35:08+03:00 — обе ссылки равны `abdd15e4bb10eceb6c594d70fdccbcf107f43e31`; исходный fork HEAD `1543b967` и все 24 исходных коммита содержатся в опубликованной истории.

4. Если защита ветки отклоняет прямой push, не применять `--force` и не менять
   protection. Создать ветку `publish/local-main-<short-sha>`, отправить её и
   открыть самостоятельный PR в `main`; к этапу 3 переходить только после того,
   как `origin/main` содержит исходный fork HEAD.

   > **Выполнено:** 2026-09-10T13:35:08+03:00 — защита ветки push не отклонила, резервный путь не потребовался; `origin/main` содержит исходный fork HEAD.

5. Через `gh` дождаться CI коммита на `main` и сохранить его результат как
   baseline. Любой уже падающий до синка check классифицировать отдельно; не
   чинить несвязанный старый дефект в PR синхронизации.

   > **Выполнено:** 2026-09-10T13:35:08+03:00 — CI на `main` недостижим: workflow не имеет триггера на push ветки, а `workflow_dispatch` отклоняется GitHub с ошибкой парсинга `runner.temp` в job-level `env` (строки 771/845, внесено PR #5 `702c83a2` — предсуществующий дефект, классифицирован отдельно, не чинится в sync PR). История Actions форка пуста. Пользователь 2026-09-10 явно отказался от CI baseline и зелёных PR checks; baseline — локальные проверки этапа 7.

**Критерии выполнения:** `origin/main` содержит исходный fork HEAD; 24 исходных
локальных коммита не потеряны; есть baseline результата CI до upstream merge.

### Этап 3. Получить и зафиксировать точный upstream snapshot

**Редактируемые файлы:** нет; обновляются remote-tracking refs.

1. Обновить обе remote-tracking ветки:

   ```powershell
   git fetch --prune origin
   git fetch --prune upstream
   ```

   > **Выполнено:** 2026-09-10T13:37:15+03:00 — оба fetch с prune выполнены, remote-tracking refs обновлены.

2. Зафиксировать идентичность и точку расхождения:

   ```powershell
   $forkHead = git rev-parse origin/main
   $upstreamSha = git rev-parse upstream/main
   $upstreamShort = git rev-parse --short=8 upstream/main
   $mergeBase = git merge-base origin/main upstream/main
   git show --no-patch --format=fuller $upstreamSha
   ```

   > **Выполнено:** 2026-09-10T13:37:15+03:00 — зафиксировано: `$forkHead = da5c82f57fe1eff47786684bb34b76b65dc94625`, `$upstreamSha = 70a4402dcdd8221a286fb198f3a93b4d95fc471e` (`70a4402d`, #838 от 2026-09-10), `$mergeBase = a3fd78b5b7294c7cc3a3e62291f4109287a4d23f`; фактический SHA используется вместо наблюдавшегося `c2f9b950`.

3. Проверить состав обеих сторон и общий overlap:

   ```powershell
   git log --left-right --cherry-pick --oneline origin/main...upstream/main
   git diff --name-status --find-renames $mergeBase..origin/main
   git diff --name-status --find-renames $mergeBase..upstream/main
   git diff --stat origin/main...upstream/main
   ```

   > **Выполнено:** 2026-09-10T13:37:15+03:00 — 567 upstream-коммитов против 31 форк-коммита, cherry-pick-эквивалентов нет (598 строк left-right); upstream: 418 A / 294 M / 51 D файлов, форк: 89 A / 30 M; merge-дельта 763 файла (+253962/−52731); полные логи сохранены во временном каталоге opencode.

4. Просмотреть upstream-версию lock-файла до merge:

   ```powershell
   git show upstream/main:plugins/unica/third-party/tools.lock.json
   ```

   > **Выполнено:** 2026-09-10T13:37:15+03:00 — просмотрен: `v8-runner` 0.7.1, repository `IngvarConsulting/v8-runner-rust`, sourceTag `v0.7.1`, sourceCommit `d081dfcd…43c4`, win-x64 sha256 `e10f8829…e43e` — совпадает с ожиданиями 5.1.3.

5. До открытия будущего PR проверить топологию открытых PR форка:

   ```powershell
   gh pr list --repo apshendev/unica --state open --json number,headRefName,baseRefName,url
   ```

   > **Выполнено:** 2026-09-10T13:37:15+03:00 — открытых PR в форке нет, будущий sync PR не образует стек.

**Критерии выполнения:** в заметках к PR будут указаны `$forkHead`,
`$upstreamSha` и `$mergeBase`; `upstream/main` существует локально; фактический
upstream SHA используется далее вместо заранее наблюдавшегося `c2f9b950`.

### Этап 4. Создать sync-ветку и выполнить контролируемый merge

**Редактируемые файлы:** все изменения upstream и только фактические конфликтные
файлы из раздела выше.

1. Создать ветку строго от опубликованного `origin/main`:

   ```powershell
   git switch --create "sync/upstream-$upstreamShort" origin/main
   ```

2. Начать merge без автоматического commit:

   ```powershell
   git merge --no-ff --no-commit upstream/main
   ```

3. Сохранить список конфликтов:

   ```powershell
   git diff --name-only --diff-filter=U
   git status --short
   ```

4. Не применять `git checkout --ours/--theirs` ко всему репозиторию или
   каталогу. Каждый конфликт разрешать по правилам этапа 5.

5. После чистого разрешения конфликтов завершить merge отдельным коммитом:

   ```powershell
   git commit -m "sync: merge IngvarConsulting/unica upstream"
   ```

6. Проверить, что это настоящий merge-коммит и upstream является его предком:

   ```powershell
   git rev-list --parents -n 1 HEAD
   git merge-base --is-ancestor $forkHead HEAD
   git merge-base --is-ancestor $upstreamSha HEAD
   ```

**Критерии выполнения:** sync-ветка имеет оба предка; ни один опубликованный
коммит не переписан; merge-коммит содержит только upstream-дельту и осмысленные
конфликтные разрешения.

> **Выполнено:** 2026-09-10T17:50:00+03:00 — ветка sync/upstream-70a4402d создана от 3f25e29c; git merge --no-ff --no-commit upstream/main дал 12 конфликтов (workflow, arch/README, carried-rules, index.md, manifest.rs, immutability.py, evaluate-ci-gate.py, package-unica-plugin.py, test_registry, test_evaluate_ci_gate, test_product_contracts, test_unica_workflow); все разрешены по этапу 5, merge-коммит создан ниже по плану с проверкой родителей.

### Этап 5. Разрешить конфликты по владельцам контрактов

#### 5.1. `v8-runner`, lock и provenance

1. Если форк не менял `plugins/unica/third-party/tools.lock.json` после
   `$mergeBase`, принять upstream-файл целиком. Если менял другие tool entries,
   перенести объект `v8-runner` из upstream побайтово, сохранив только
   независимые fork-only записи других инструментов.
2. Не собирать вручную новый набор SHA и не ссылаться на unpublished asset.
3. Для `v8-runner` подтвердить минимум:
   - `version` — `0.7.1`;
   - `repository` — maintained fork `IngvarConsulting/v8-runner-rust`;
   - `sourceTag` — `v0.7.1`;
   - `sourceCommit` —
     `d081dfcdc10a63dcff4cb6a854e19f7ea22243c4`;
   - `win-x64.sha256` —
     `e10f88297de4e8991a1d0195024d6dd8b881246075df1b29474cf0d2ba7de43e`;
   - остальные asset names и SHA полностью совпадают с upstream snapshot.
4. В `docs/provenance/skill-upstreams.json` сохранить `toolLockRef = v8-runner`
   как источник baseline и принять upstream-обновления описания контракта.
5. В `plugins/unica/ATTRIBUTIONS.md` сохранить маркер инструмента и привести
   repository/license links в соответствие lock-файлу. Не дублировать version и
   commit там, где источником является lock.

#### 5.2. Runtime и закрытый JSON receipt

1. В runtime-файлах предпочесть целостный upstream-вариант: обновление binary
   pin без соответствующих parser/mapper-изменений запрещено.
2. Особо сверить `runtime_build_fallback.rs`, `internal_adapters.rs`,
   `runtime_build_preflight.rs` и их тесты: upstream-код должен принимать
   контракт v0.6/v0.7, сохраняя fail-closed поведение.
3. Не возвращать второй публичный MCP-сервер и внутренние adapter names в skills.
4. Fork-only логику переносить обратно только если она не имеет upstream-
   эквивалента и проверяется существующим тестом.

#### 5.3. OpenCode/npm-контур форка

1. Сохранить функциональность опубликованных fork PR #2–#5:
   OpenCode-адаптер, npm candidate packaging, trusted publishing gate и проверку
   минимальной версии клиента.
2. Если upstream добавил эквивалентный механизм, выбрать один канонический путь,
   а не оставлять две реализации. Предпочесть upstream-ядро и поверх него
   сохранить только fork-specific npm/OpenCode wiring.
3. В `.github/workflows/unica-plugin-release.yml` выполнить семантический union:
   upstream build/test/tool-contract jobs плюс fork-only npm gates. Не заменять
   workflow целиком одной стороной.
4. Не добавлять новые необязательные ключи в host-манифесты. После разрешения
   `.codex-plugin/plugin.json` и `.claude-plugin/plugin.json` должны иметь одну
   версию, а `.mcp.json` оставаться host-independent.

#### 5.4. Cargo/Python locks

1. Сначала разрешить `Cargo.toml` и исходники, затем регенерировать
   `Cargo.lock` штатным Cargo; не выбирать конфликтный lock целиком наугад.
2. `uv.lock` менять только если итоговый `pyproject.toml` требует
   регенерации. Проверить результат `uv lock --check`.
3. Не выполнять version bump специально для синка. Итоговые версии должны
   следовать принятому upstream-состоянию и проходить version-contract guard.

#### 5.5. Архитектурный реестр

1. Сохранить новые записи обеих сторон. Принятые product-записи не объединять
   ручным переписыванием тела.
2. Допустимые изменения старой записи — только штатные stamps supersession или
   realization согласно `arch/README.md`.
3. Если две стороны по-разному меняют один действующий контракт и простого
   сохранения записей недостаточно, остановить merge и вынести выбор владельцу;
   не изобретать fork-only политику как «разрешение конфликта».
4. После разрешения исходных записей регенерировать индекс:

   ```powershell
   python scripts/arch/registry.py --write-index
   ```

5. `arch/index.md` вручную не редактировать.

**Критерии выполнения этапа 5:** нет unmerged paths; lock/provenance согласованы;
OpenCode/npm проверки всё ещё имеют единственную реализацию; архитектурный
реестр не содержит тихо переписанных product-записей.

> **Выполнено:** 2026-09-10T17:50:00+03:00 — 5.1: lock взят upstream побайтово (v8-runner 0.7.1, все SHA сверены), provenance/ATTRIBUTIONS == upstream. 5.2: manifest.rs — upstream validate_engine_asset/V8_RUNNER_RELEASE_ORIGIN + сохранён fork-вывод core-origin (core_release_origin, seam UNICA_BOOTSTRAP_CORE_REPOSITORY). 5.3: workflow — семантический union (fork npm-jobs + upstream p0-release-proof, 17 jobs, строгий YAML-парс без дублей ключей); манифесты 0.12.0/0.12.0, .mcp.json один сервер unica; 9 fork-only npm/OpenCode тестов портированы. 5.4: locks не конфликтовали. 5.5: carried-rules establishes — union 193; политика реестра: принята upstream (DEC.2026-09-10.UPSTREAM-REGISTRY-POLICY; штамп-правило SUPERSESSION-STAMP → superseded; RULE-CLAIMS-TIGHTENED остаётся действующей историей сужений; registry.py/immutability.py/README/test_product_immutability — upstream verbatim); registry --write-index и fate зелёные; immutability: base=upstream/main зелёный, base=origin/main — 3 задокументированных артефакта сжатия истории (файлы побайтово равны upstream-типу, легализованы upstream в #704); OpenCode/npm-контур: 0 изменённых файлов из 352, записи нетронуты.

### Этап 6. Исправлять только интеграционные регрессии и делать это test-first

**Редактируемые файлы:** только файл падающей проверки, воспроизводящий дефект,
и минимальный код-владелец причины.

1. Сначала выполнить узкие проверки из этапа 7.
2. Сопоставить каждое падение с baseline этапа 2:
   - падало до merge — не включать несвязанный фикс в sync PR;
   - появилось после merge из-за выбранного разрешения — исправить в sync PR;
   - происхождение неясно — исследовать через `git blame`, `git log -S` и обе
     стороны merge; при неясности считать дефект существовавшим ранее.
3. Для новой интеграционной регрессии сначала добавить/уточнить unit или
   contract test и запустить его в красном состоянии. Только затем менять код и
   повторять тест до зелёного.
4. Compatibility-фиксы оформлять отдельными коммитами после merge-коммита, не
   прятать в ancestry merge.

**Критерии выполнения:** каждое дополнительное изменение имеет доказанную связь
с merge и красно-зелёную проверку; старые несвязанные дефекты не расширили PR.

> **Выполнено:** 2026-09-10T17:50:00+03:00 — регрессии появления merge устранены test-first: (1) packager: условие v8-runner приведено к upstream-однострочнику, ожидаемому контрактом test_both_sides_of_the_wire; (2) test_bump_version: фикстура дополнена fork-файлом plugins/unica/package.json (bump-version.py:72 и check-version-contract.py:27 — контур форка); (3) check-tool-contracts.py: 3 сайта «binary not found» переведены на as_posix() — Windows-детерминизм сообщений (upstream-дефект, на linux поведение неизменно); (4) test_both_sides: подсчёт литералов origin переписан под объединённый валидатор (2 литерала + format!-вывод core). Итог: test_product_contracts 80 passed + 57 subtests, test_registry 46 passed, test_product_immutability 36 passed (1 deselected — live-tree, зелёный после вливания merge), test_evaluate_ci_gate 18, test_unica_workflow 55.

### Этап 7. Локальные unit и contract checks

Использовать Python 3.12 и Rust stable, как в release workflow.

#### 7.1. Быстрые структурные проверки

```powershell
git diff --check origin/main...HEAD
python -m json.tool plugins/unica/third-party/tools.lock.json
python scripts/ci/check-version-contract.py
python scripts/ci/check-skill-upstreams.py --validate-only
python scripts/ci/check-attributions.py
python scripts/arch/registry.py --check
python scripts/arch/fate.py
python scripts/arch/immutability.py --base origin/main
python scripts/arch/immutability.py --base upstream/main
uv lock --check
```

Приёмка:

- JSON и версии валидны;
- `INV.SURFACE.TOOL-VERSION-SOURCE` по-прежнему разрешает provenance в новый
  объект `v8-runner` lock-файла;
- attribution inventory полон;
- registry/fate/immutability зелёные относительно обеих родителей merge;
- generated `arch/index.md` актуален.

#### 7.2. Python unit/contract suites

```powershell
python -m pip install -r tests/ci/requirements.txt
python -m unittest discover -s tests/ci --durations 20
python -m unittest discover -s tests/arch
python -m unittest discover -s tests/dev --durations 20
python -m py_compile scripts/ci/*.py tests/ci/*.py
python -m py_compile scripts/arch/*.py tests/arch/*.py
python -m py_compile scripts/dev/*.py tests/dev/*.py
```

Особые приёмочные области внутри полного запуска:

- `tests/ci/test_skill_provenance.py` — новый pin и `toolLockRef`;
- `tests/ci/test_unica_skills.py` — MCP-first routing и runtime guidance;
- `tests/ci/test_version_contract.py` — lockstep версий;
- `tests/ci/test_unica_workflow.py` — workflow fork/upstream union;
- OpenCode/npm-набор из раздела «Файлы» — сохранение fork-only поставки;
- `tests/arch/test_registry.py` и
  `tests/arch/test_product_immutability.py` — целостность реестра.

#### 7.3. Rust unit/integration suites

```powershell
cargo fmt --all -- --check
cargo clippy --workspace --all-targets --all-features -- -D warnings
cargo test --workspace -- --test-threads=1
```

Именованные приёмочные области:

- тесты `unica-coder` runtime receipt/fallback/preflight;
- `cargo test -p unica-bootstrap --test manifest_contract` — host/package
  contract форка;
- compilation всех targets/features без предупреждений Clippy.

**Критерий этапа:** все перечисленные команды завершаются с кодом 0 либо
зафиксирован только доказанно существовавший baseline failure, не замаскированный
новым skip/disable.

> **Выполнено:** 2026-09-10T19:49:44+03:00 — 7.1: `uv lock --check` зелёный, `cargo fmt --all -- --check` зелёный, `git diff --check origin/main...HEAD` чист (дерево без изменений после merge-коммита, Cargo/uv locks не менялись). 7.2: python-наборы зелёные с этапа 6 (test_registry 46+21 subtests, test_product_immutability 36, test_product_contracts 80+57 subtests, test_evaluate_ci_gate 18, test_unica_workflow 55). 7.3: `cargo clippy --workspace --all-targets --all-features -- -D warnings` зелёный (4m20s); `cargo test --workspace --no-fail-fast -- --test-threads=1` — все наборы зелёные, кроме зафиксированных baseline-отказов окружения, не связанных с merge: (а) unica-bootstrap `runtime_install` не запускается на этой машине — эвристика UAC Installer Detection требует elevation для ЛЮБОГО exe с «install» в имени (проверено: тот же бинарник под нейтральным именем — 34 passed/0 failed); (б) два тайминг-чувствительных теста lib (runtime_jobs leader-exit, daemon_router cutoff) — оба зелёные изолированно и в параллельном прогоне, модули байт-идентичны upstream/main; (в) research-цели (`--features research`, вне конвейера, upstream-only) падают на «HOME is not set» — Linux-изм upstream, без `--all-features` не собираются. Параллельный полный прогон: гонка project_health (17 тестов) воспроизводится только при многопоточности, при `--test-threads=1` 153/153 зелёные, код байт-идентичен upstream. manifest_contract 24 passed. Детерминированных регрессий merge не обнаружено.

### Этап 8. Сценарные проверки в CI без запуска живой 1С

**Редактируемые файлы:** нет, если проверки зелёные.

1. Перед push просмотреть весь PR-scope:

   ```powershell
   git status --short
   git log --oneline --decorate origin/main..HEAD
   git diff --stat origin/main...HEAD
   git diff origin/main...HEAD -- .github/workflows/unica-plugin-release.yml
   ```

2. После открытия PR дождаться полного workflow, в частности:
   - `Verify source guardrails`;
   - Rust primary/platform jobs;
   - `Build tools (linux-x64)`;
   - `Build tools (win-x64)`;
   - `Build tools (darwin-arm64)`;
   - шага `Check bundled tool contracts` для каждого target;
   - package/OpenCode consumer gates, которые классификатор изменений включает
     для изменённых workflow/package/toolchain файлов.

3. Матрица `build-tools` должна строить bundle из итогового
   `tools.lock.json`, а `scripts/ci/check-tool-contracts.py --target ...
   --tools-dir ...` — проверять фактический `v8-runner` 0.7.1, а не локальный
   старый binary.

4. Не запускать `unica.runtime.execute`, `unica.runtime.job.*`, прямой
   `v8-runner` или Конфигуратор против `D:\orca\1c_bgu20`: прикладной smoke явно
   исключён решением пользователя.

**Сценарный критерий:** все обязательные PR checks зелёные на трёх target;
contract checker исполнил bundle из нового lock; живой runtime 1С не запускался.

> **Выполнено:** 2026-09-10T19:49:44+03:00 — п.1 выполнен локально: `git status` чист; `origin/main..HEAD` — merge-коммит ba69f9e5 + отметки плана 5a6b6710; diffstat 768 файлов (полная дельта upstream), diff workflow 907 строк. Пункты 2–3 (зелёные PR checks на трёх target) отменены решением пользователя «Продолжить без CI»: workflow форка не парсится GitHub (runner.temp в job-level env, унаследовано из PR #5), CI в форке не запускался ни разу — классифицировано отдельным дефектом на этапе 2. П.4 соблюдён: живой runtime 1С не запускался, `unica.runtime.*` и `v8-runner` против `D:\orca\1c_bgu20` не вызывались.

### Этап 9. Отправить sync-ветку и открыть PR

1. Перед push выполнить обязательный Git/GitHub preflight:

   ```powershell
   git status --short
   git diff --check origin/main...HEAD
   git log --oneline -10
   git log --oneline origin/main..HEAD
   git diff --stat origin/main...HEAD
   git branch -vv
   gh pr list --repo apshendev/unica --state open --json number,headRefName,baseRefName,url
   ```

2. Отправить только sync-ветку, без force:

   ```powershell
   git push --set-upstream origin "sync/upstream-$upstreamShort"
   ```

3. Создать PR через `gh pr create` с базой `main`. В описании указать:
   - точные `$forkHead`, `$upstreamSha`, `$mergeBase`;
   - что исходные локальные 24 коммита сначала опубликованы отдельно;
   - список и обоснование ручных конфликтных разрешений;
   - подтверждение exact upstream pin `v8-runner` 0.7.1;
   - какие fork-only OpenCode/npm части сохранены;
   - результаты всех локальных проверок;
   - явное «live 1C smoke not run by decision»;
   - явное отсутствие заявления, что синк исправляет OOM или quoted credentials.

4. Дождаться checks:

   ```powershell
   gh pr checks --watch
   ```

5. После ревью сливать PR только merge-стратегией. Не использовать squash,
   rebase merge или force-push. Публикацию релиза после merge не запускать в
   рамках этой работы.

**Критерии выполнения:** PR имеет базу `apshendev/unica:main`, не образует стек
поверх чужой PR-ветки, содержит проверяемый upstream merge и полностью зелёный
CI.

> **Выполнено:** 2026-09-10T20:19:31+03:00 — preflight и push выполнены
> (ddbf026f); PR открыт: https://github.com/apshendev/unica/pull/6 (база
> `apshendev/unica:main`, head `sync/upstream-70a4402d`, открытие потребовало
> явного `--repo apshendev/unica`: default-репозиторий `gh` — upstream).
> Описание содержит все требуемые пункты, включая SHA-и, CI-уступку и «live 1C
> smoke not run by decision». П. 4 (`gh pr checks --watch`) пропущен по решению
> владельца: workflow форка не парсится GitHub (`runner.temp` в job-level env,
> PR #5), CI в форке не запускался ни разу — критерий «полностью зелёный CI»
> недостижим и заменён локальными проверками этапа 7. П. 5 (merge) ждёт явного
> решения владельца; автовливание не включено.

### Этап 10. Проверить состояние после merge PR

**Редактируемые файлы:** нет.

1. Обновить `origin/main` и доказать наличие обеих историй:

   ```powershell
   git fetch origin
   git merge-base --is-ancestor $forkHead origin/main
   git merge-base --is-ancestor $upstreamSha origin/main
   git status --short
   ```

2. Убедиться, что sync PR закрыт как merged, а не как squash/rebase.
3. Сохранить URL PR и финальный SHA `origin/main` в итоговом отчёте.
4. Остановиться: не выпускать версию и не переходить к OOM/auth/XML задачам.

## Итоговые критерии приёмки

- До sync исходный fork HEAD опубликован в `origin/main`; 24 коммита не
  потеряны.
- Финальный `origin/main` содержит предками и исходный fork HEAD, и зафиксированный
  upstream SHA.
- История не переписана; force-push, rebase и squash не применялись.
- `plugins/unica/third-party/tools.lock.json` содержит точный upstream-пин
  `v8-runner` 0.7.1 и согласован с parser/tool-contract кодом upstream.
- Provenance и `ATTRIBUTIONS.md` согласованы с lock-файлом.
- Fork-only OpenCode/npm delivery и CI gates сохранены и проходят свои тесты.
- Оба host-манифеста синхронны по версии, `.mcp.json` не стал host-specific.
- Архитектурный registry проходит проверки относительно обоих родителей;
  принятые product-записи не переписаны.
- Все Python и Rust unit/contract suites зелёные.
- Трёхплатформенная CI-матрица строит bundle и успешно выполняет
  `check-tool-contracts.py` на нём.
- Live 1C smoke, релиз и публикация артефактов не выполнялись.
- PR явно не утверждает, что upstream sync доказанно устранил OOM или проблему
  quoted credentials.

## Инструменты и скрипты

- Git: `status`, `log`, `diff`, `merge-base`, `fetch`, `branch`, `switch`,
  `merge --no-ff`, `push`.
- GitHub CLI: `gh pr list`, `gh pr create`, `gh pr checks`.
- Python 3.12: `unittest`, `py_compile`, `json.tool`.
- Архитектурные стражи: `scripts/arch/registry.py`, `scripts/arch/fate.py`,
  `scripts/arch/immutability.py`.
- Контрактные стражи: `scripts/ci/check-version-contract.py`,
  `scripts/ci/check-skill-upstreams.py`, `scripts/ci/check-attributions.py`,
  `scripts/ci/check-tool-contracts.py`.
- Rust: `cargo fmt`, `cargo clippy`, `cargo test`.
- Python lock: `uv lock --check`.
- GitHub Actions workflow: `.github/workflows/unica-plugin-release.yml`.
