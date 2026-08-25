---
id: CTR.PKG.OPENCODE-LOCAL-DEBUG-COMPOSITION
status: active
governs: product
version: 1
decision: DEC.2026-08-25.OPENCODE-LOCAL-DEBUG-RUNTIME
producer: scripts/ci/package-unica-opencode.py
consumers: [review, docs]
check: tests/ci/test_package_unica_opencode.py::test_local_debug_candidate_carries_current_host_binaries_and_marker
scope: [pkg]
---

# Состав local-debug кандидата — development-корень плюс маркер

Кандидат local-debug собирается только из plugin-корня
`package-unica-plugin.py --local-debug-target`: его файлы доезжают теми же
байтами, добавляются ровно `package.json` и `opencode/**` из отслеживаемых
файлов, корневой `README.md` заменяется руководством установки OpenCode, и
упаковщик порождает единственный новый файл — маркер
`opencode/local-debug.json` с режимом, целью и версией. Вход обязан нести
development-манифест и ровно одну цель `bin/<target>` с бинарником ядра;
корень без development-манифеста кандидатом не становится.
