---
id: CTR.PKG.NPM-CANDIDATE-COMPOSITION
status: active
governs: product
version: 1
decision: DEC.2026-08-25.RULE-CLAIMS-TIGHTENED
producer: scripts/ci/package-unica-opencode.py
consumers: [review, docs]
check: tests/ci/test_package_unica_opencode.py::test_the_candidate_carries_the_thin_root_plus_npm_metadata
scope: [pkg]
supersedes: [INV.PKG.NPM-CANDIDATE-FROM-THIN-ROOT]
---

# Состав npm-кандидата — тонкий корень плюс два класса добавлений

Каждый файл тонкого корня доезжает до кандидата теми же байтами, кроме
двух намеренных отличий: корневой `README.md` заменяется руководством
установки OpenCode байт-в-байт, а VCS-ignore файлы удаляются, чтобы не
править правила упаковки npm. Настоящие добавления — ровно `package.json`
(npm-метаданные) и `opencode/**` из отслеживаемых файлов; всё прочее в
кандидате невозможно.
