---
id: INV.PKG.NPM-CANDIDATE-FROM-THIN-ROOT
status: superseded
governs: product
decision: DEC.2026-08-24.OPENCODE-ADAPTER-DELIVERY
check: tests/ci/test_package_unica_opencode.py::test_the_packed_tarball_carries_the_candidate
scope: [pkg]
superseded-by: [CTR.PKG.NPM-CANDIDATE-COMPOSITION, INV.PKG.NPM-CANDIDATE-DEV-MANIFEST-REFUSED, INV.PKG.NPM-CANDIDATE-VERSION-REFUSED, INV.PKG.NPM-CANDIDATE-BOOTSTRAP-REFUSED]
---

# npm-кандидат собирается из тонкого корня

Кандидат `@apshendev/unica-opencode` — байты тонкого корня плюс
отслеживаемые npm-метаданные и адаптер из исходного корня (продуктовый README
замещается руководством установки OpenCode); идентичность выпуска проверяется
до вызова npm, npm-источники копируются только из отслеживаемых файлов без
симлинков. Тонкие host-пакеты npm-метаданных не несут
(tests/ci/test_package_unica_plugin.py::test_marketplace_packages_stay_free_of_opencode_npm_metadata);
отказные пути кандидата — development-манифест, рассинхрон версии,
отсутствующий bootstrap — покрыты именованными тестами в
tests/ci/test_package_unica_opencode.py.
