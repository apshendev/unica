# Результат code review issues #2-#5

Ниже полный backlog по code review относительно `upstream/main`, включая новые
замечания по README и ранее подтверждённые дефекты release-контура.

## P1: Release

### 1. npm-теги меняются до consumer smoke

**Проблема:** `scripts/ci/publish-unica-opencode.py:114-130` публикует stable без
`--tag`, поэтому npm немедленно двигает `latest`. Prerelease сразу публикуется
под `next`. Блокирующий Windows smoke выполняется позже.

Красный smoke уже не может предотвратить получение сломанной версии обычными
пользователями.

**Затрагивает:** #4, #5.

**Критерии приёмки:**

- Stable и prerelease публикуются через OIDC только под служебным тегом
  `staging`.
- Smoke устанавливает точную версию, а не dist-tag.
- `latest` перемещается только после успешного Windows smoke.
- Prerelease аналогично перемещает `next`.
- Linux остаётся best-effort.
- Promotion идемпотентен и не двигает тег назад по SemVer.
- Publish job не получает npm token.
- Promotion job получает package-scoped token только после будущего bootstrap
  пакета.
- Тест workflow доказывает порядок `publish → smoke → promotion`.

### 2. После успешного `npm publish` не ожидается registry visibility

**Проблема:** `publish-unica-opencode.py:127-130` сразу завершает job. Следующий
smoke может получить временный `E404`, хотя публикация успешна. Registry tarball
проверяется только после неуспешного `npm publish`.

**Затрагивает:** #4, #5.

**Критерии приёмки:**

- После успешного publish выполняется bounded polling точной версии.
- `E404 → версия появилась → байты совпали` завершается успешно.
- Постоянный `E404` завершается timeout-ошибкой.
- Malformed JSON или malformed tarball URL завершается ошибкой.
- Отличающиеся SHA-512 байты завершаются ошибкой.
- Rerun использует тот же механизм проверки registry bytes.
- Consumer jobs запускаются только после успешной visibility-проверки.

### 3. Smoke не доказывает установленный package root

**Проблема:** `scripts/ci/smoke-opencode-consumer.py:121-125` принимает любую
команду, содержащую `unica-bootstrap`.

Например, `C:\tools\unica-bootstrap.exe` будет принят.

Кроме того, workflow передаёт `verify-skills --plugin-root plugins/unica`, то
есть checkout, а не пакет, установленный из registry:
`.github/workflows/unica-plugin-release.yml:795-803,853-861`.

**Затрагивает:** #5.

**Критерии приёмки:**

- Наблюдаемые skill locations определяют один установленный root
  `@apshendev/unica-opencode`.
- Все ожидаемые `SKILL.md` находятся именно под `<installed-root>/skills`.
- Команда `mcp.unica` запускает bootstrap под тем же `<installed-root>`.
- Допускаются только:
  - `bootstrap/bin/win-x64/unica-bootstrap.exe`;
  - `bootstrap/bin/linux-x64/unica-bootstrap`.
- Bootstrap с тем же именем вне установленного package root отвергается.
- Checkout `plugins/unica` не используется как доказательство содержимого
  установленного пакета.
- Windows- и Linux-негативные тесты сначала падают на текущем verifier.
- `opencode mcp list | tee mcp.txt` запускается под `set -euo pipefail`.

## P1: Documentation

### 4. npm README не соответствует пользовательскому контуру

**Проблема:** `plugins/unica/opencode/README.md` и, следовательно,
`dist/local-opencode/staging/README.md` полностью на английском. README
описывает только установку несуществующего npm-пакета:

```json
{
  "plugin": ["@apshendev/unica-opencode"]
}
```

Локальный `.tgz`, который уже существует и успешно проверен, использовать по
этой инструкции нельзя.

**Затрагивает:** #3, #5.

**Критерии приёмки:**

- `plugins/unica/opencode/README.md` написан на русском.
- Сгенерированный `staging/README.md` побайтово совпадает с ним.
- Явно указано, что публичный npm-пакет пока не опубликован.
- Публичная установка и локальная проверка разделены на разные разделы.
- Локальная инструкция включает:
  - сборку или путь к `.tgz`;
  - создание пустого consumer-каталога;
  - `npm install --ignore-scripts <absolute-tarball>`;
  - абсолютный `file://` URI установленного
    `node_modules/@apshendev/unica-opencode`;
  - пример `opencode.json`;
  - требование OpenCode `1.18.22` или новее;
  - перезапуск OpenCode;
  - `opencode debug skill`;
  - `opencode mcp list`;
  - ожидаемое `unica connected`;
  - предупреждение о долгой первой загрузке runtime.
- Описаны Windows x64, Linux x64 best-effort и отказ остальных платформ.
- Описано владение `mcp.unica`.
- Описаны cache/state directories и `UNICA_*` overrides.
- Package test проверяет присутствие локальных команд в README внутри
  настоящего `.tgz`.

### 5. Инструкция существует, но не обнаруживается из основных README

**Проблема:**

- `README.md:9-24` называет только Codex и Claude Code.
- `plugins/unica/README.md` не ссылается на OpenCode.
- `plugins/unica/package.json:7` ведёт на root README без OpenCode.
- npm-страницы пока нет.

**Затрагивает:** #3, #5.

**Критерии приёмки:**

- Root README содержит отдельный раздел OpenCode.
- В разделе показано текущее состояние: локальный candidate доступен, публичный
  npm-пакет ещё нет.
- Root README ссылается на подробное руководство.
- `plugins/unica/README.md` содержит такую же явную ссылку.
- `package.json.homepage` ведёт на страницу, где инструкция действительно
  доступна.
- Тест документационного контракта закрепляет обе ссылки.

## P1: External Acceptance

### 6. #4 и #5 не имеют живого опубликованного доказательства

**Проблема:** package отсутствует в npm, trusted publisher не настроен, fork tag
release не запускался, registry consumer smoke не выполнялся. Локальный тест
использовал upstream runtime v0.12.0.

**Затрагивает:** #4, #5.

**Критерии приёмки:**

- После завершения кодовых исправлений вручную публикуется служебный
  `0.0.0-bootstrap.1` под тегом `bootstrap`, не `latest`/`next`.
- Bootstrap помечен как служебный и затем может быть deprecated.
- Настроен trusted publisher для `apshendev/unica` и
  `unica-plugin-release.yml`.
- Только после появления пакета создаётся package-scoped promotion token.
- Первый реальный prerelease публикуется через OIDC с provenance.
- Registry tarball совпадает с candidate.
- Windows consumer устанавливает точную registry-версию и проходит.
- Наблюдаемый runtime manifest указывает на `apshendev/unica`, не upstream.
- Linux smoke отчитывается, но не блокирует.
- До выполнения этих пунктов документация не заявляет npm delivery готовой.

### 7. Runbook неправильно предлагает вручную опубликовать настоящий tagged candidate

**Проблема:** `docs/release-runbook.md:41-46` предлагает первый tagged candidate
опубликовать вручную. Такая версия обойдёт OIDC/provenance, хотя это требование
#4.

**Критерии приёмки:**

- Runbook предписывает отдельную служебную bootstrap-версию.
- Bootstrap получает отдельный dist-tag `bootstrap`.
- Реальная release-версия не публикуется вручную.
- Последовательность явно указана: bootstrap → trusted publisher → package
  token → первый prerelease.
- Runbook не предлагает включать npm `disallow tokens`, пока promotion
  использует token.

## P1: Architecture

### 8. Активные записи шире своих единственных `check`

Это нарушает `DEC.2026-08-19.RULE-CLAIMS-ONLY-WHAT-IT-CHECKS`.

| Запись | Недоказанная часть |
| --- | --- |
| `CTR.PKG.CORE-PROVENANCE-SELECTABLE` | default origin, compile-time bootstrap seam, mismatch refusal |
| `CTR.HOST.OPENCODE-CONFIG` | skills paths, cache/state locations |
| `INV.PKG.VERSION-LOCKSTEP` | atomic bump |
| `INV.HOST.OPENCODE-PLATFORM-GATE` | положительный выбор Windows/Linux |
| `INV.PKG.NPM-PUBLICATION-GATE` | часть token/upstream-skip claims |
| `INV.PKG.NPM-RERUN-INTEGRITY` | absent version, deletion, gating, identity |
| `INV.CI.OPENCODE-CONSUMER-SMOKE` | exact installed version/root и tag conditions |
| `INV.HOST.OPENCODE-CLIENT-FLOOR` | фактическое отсутствие ceiling |
| `INV.HOST.OPENCODE-SHARED-SURFACE` | происхождение общей product surface |
| `INV.PKG.NPM-CANDIDATE-FROM-THIN-ROOT` | полный inventory и refusal paths |

**Затрагивает:** #2-#5.

**Критерии приёмки:**

- Сначала реестр получает поддерживаемый lifecycle supersession для product
  rules.
- Старые записи получают только разрешённый supersession stamp.
- Каждая новая запись заявляет один независимо нарушаемый контракт.
- Каждый `check` падает при нарушении всей формулировки своей записи.
- Inline-ссылки на дополнительные тесты не используются как замена `check`.
- `registry.py --check`, `fate.py` и
  `immutability.py --base upstream/main` проходят.

## P2: Versioning

### 9. Atomic version bump фактически не доказан

**Проблема:** `tests/ci/test_version_contract.py:292-305` портит только
`package.json`, а после ошибки проверяет только Codex manifest.

**Затрагивает:** #3.

**Критерии приёмки:**

- В subtests по очереди повреждаются все пять contract locations.
- Перед вызовом сохраняются байты всех пяти файлов.
- После каждого отказа все пять файлов побайтово неизменны.
- Успешный bump обновляет все пять мест одной операцией.
- Static equality и bump atomicity закреплены разными архитектурными правилами.

## P2: uv

### 10. Проектный uv настроен как второй продукт, а не tooling project

Использование `uv` принято. Замечание относится только к текущей форме.

**Критерии приёмки:**

```toml
[project]
name = "unica-dev"
version = "0.0.0"
requires-python = ">=3.12"
dependencies = []

[tool.uv]
package = false
```

- `.python-version` содержит `3.12`.
- `[build-system]` удалён.
- `[project.scripts] unica = "unica:main"` удалён.
- Placeholder `src/unica` не требуется.
- `uv.lock` закоммичен.
- `uv sync --locked` проходит на fresh clone.
- `uv run python scripts/ci/...` использует проектное окружение.
- Python-проект не участвует в product version lockstep, потому что явно
  является virtual tooling project.

## P2: Plans

### 11. Утверждённый план продолжает предписывать неправильный run

**Проблема:**
`docs/code-review/2026-08-25-opencode-local-test-fix-steps.md:214-224`
по-прежнему предписывает run `32766639619`. Поздние отметки объясняют
исправление, но исполнитель, следующий самим шагам, снова получит checksum
mismatch.

**Критерии приёмки:**

- Старый документ не переписывается задним числом.
- Он помечается superseded либо получает явного successor.
- Новый исполняемый план использует tag-run `31950933025`.
- Перед упаковкой обязательно сравниваются все три manifest SHA с release
  digests.
- Одних `pluginVersion` и `release.tag` недостаточно.
- Красный старый artifact даёт 3/3 mismatch; правильный даёт 3/3 match.

### 12. Планы находятся не в нормативном каталоге

**Проблема:** `AGENTS.md:104-107` требует `docs/plans/`, но документы лежат в
`docs/code-review/`.

**Критерии приёмки:**

- Исполняемые планы находятся в `docs/plans/YYYY-MM-DD-*.md`.
- Формулировки утверждённых планов при переносе не меняются.
- Старые пути либо удалены, либо содержат только короткий pointer.
- Внутренние ссылки обновлены.
- Design-document checks и поиск маршрутов проходят.

## Закрытие Issues

| Issue | Вердикт |
| --- | --- |
| #2 | Поведение реализовано; оставить закрытым можно после отдельного устранения overclaim в provenance-контрактах |
| #3 | Переоткрыть: пользовательская документация, uv-конфигурация, atomic bump и архитектурные записи не готовы |
| #4 | Переоткрыть: преждевременные dist-tags, propagation race, runbook и отсутствие live OIDC evidence |
| #5 | Переоткрыть: smoke не привязан к установленному package root и registry E2E не выполнен |

Локальное функциональное тестирование продолжать можно: `.tgz` уже запускается
в OpenCode 1.18.22. Закрывать #3-#5 до выполнения критериев выше нельзя.
