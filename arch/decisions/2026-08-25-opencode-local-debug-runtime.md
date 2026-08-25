---
id: DEC.2026-08-25.OPENCODE-LOCAL-DEBUG-RUNTIME
status: active
governs: product
realized: tests/ci/test_opencode_adapter.py::test_local_debug_marker_switches_to_direct_binary_launch
supersedes: []
superseded-by: null
establishes: [CTR.HOST.OPENCODE-LAUNCH-MODES, CTR.PKG.OPENCODE-LOCAL-DEBUG-COMPOSITION, INV.PKG.OPENCODE-DEV-CANDIDATE-UNPUBLISHABLE]
design: docs/design/2026-08-25-opencode-local-debug-runtime-design.md
---

# npm-пакет OpenCode получает local-debug режим с текущим бинарником

**Решение.** Упаковщик OpenCode-кандидата получает второй явный режим:
`--local-debug-root` принимает plugin-корень, собранный
`package-unica-plugin.py --local-debug-target`, и требует development-манифест
— зеркальный отказ release-режима. Кандидат этого режима несёт те же два
класса tracked-добавлений плюс один сгенерированный маркер
`opencode/local-debug.json`; адаптер по маркеру запускает упакованный
current-host бинарник напрямую вместо bootstrap, сохраняя владение `mcp.unica`,
вывод окружения и таймаут; рассогласование цели маркера с хостом отказывает
при инициализации. Стадирование npm отвергает кандидата с маркером или
development-манифестом до любого npm-вызова.

**Почему.** Рабочий способ проверить адаптер сегодня собирает его поверх
release thin-корня, и bootstrap скачывает закреплённый runtime v0.12.0: его
`tools/list` в 1.12 МБ с описаниями загружает контекст OpenCode до
неудовлетворительного compaction-цикла. Текущий HEAD отдаёт 204 КБ без
описаний, и изолированный прогон с прямым запуском бинарника завершает тот же
сценарий без compaction — но ни один существующий путь не доставляет текущий
бинарник в npm-пакет. Маркер, а не development-манифест, выбирает режим:
адаптер-тесты грузят живое development-дерево исходников, и переключение по
манифесту перевернуло бы каждое release-утверждение.

**Цена.** Вторая композиция кандидата и вторая ветка запуска в адаптере;
release-путь остаётся байт-в-байт прежним, а публикация получает ещё один
запирающий отказ. Local-debug пакет не является установочным артефактом
продукта: он не публикуется и живёт только в изолированном потребителе.

**Что не меняется.** Release-композиция тонкого корня, bootstrap-путь
проверки и доставки рантайма, идентичность MCP-сервера и поверхность
`unica.*`, каталоги Codex и Claude Code, пайплайн выпуска.
