---
id: INV.PKG.VERSION-BUMP-ATOMIC
status: active
governs: product
decision: DEC.2026-08-25.RULE-CLAIMS-TIGHTENED
check: tests/ci/test_version_contract.py::test_a_render_failure_leaves_every_contract_file_untouched
scope: [pkg, product]
supersedes: [INV.PKG.VERSION-LOCKSTEP]
---

# Отказ бампа не оставляет частичной записи

Повреждение любой из пяти контрактных локаций до записи оставляет все пять
файлов байт-в-байт неизменными: рендер каждого файла завершается до первого
касания диска.
