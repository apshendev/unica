---
id: DEC.2026-09-01.OPENCODE-PACKAGED-REFERENCE-ACCESS
status: active
governs: product
realized: tests/ci/test_opencode_adapter.py::test_existing_permission_rules_survive_and_gain_the_references_rule
supersedes: []
superseded-by: null
establishes: [CTR.HOST.OPENCODE-REFERENCE-ACCESS]
---

# Адаптер OpenCode разрешает чтение упакованного references/

**Решение.** Конфигурационный хук адаптера добавляет в
`permission.external_directory` ровно одно узкое правило:
`<package-root>/references/*` получает `allow`. Строковая политика
потребителя преобразуется в карту, где исходная политика остаётся правилом
`"*"`; существующая карта сохраняет все прочие правила; адаптер владеет
точным ключом glob'а, поэтому повторный запуск хука не дублирует запись и
заменяет любое прежнее значение этого ключа. Доступ к остальным внешним
каталогам, всему пакету и `node_modules` не открывается.

**Почему.** Скиллы читают общие материалы по ссылкам `../../references/...`,
а установленный npm-корень для OpenCode — внешний каталог: без правила
каждое чтение требует external_directory-подтверждение, и упакованные скиллы
теряют бесшовный доступ к упакованным же справочным файлам.

**Цена.** Адаптер получает вторую мутацию конфигурации потребителя рядом с
`skills.paths` и `mcp.unica`; её форма закреплена контрактом
`CTR.HOST.OPENCODE-REFERENCE-ACCESS`.

**Что не меняется.** Владение `mcp.unica`, композиция `skills.paths`,
режимы запуска, поверхность `unica.*` и политика потребителя для путей вне
упакованного references/.
