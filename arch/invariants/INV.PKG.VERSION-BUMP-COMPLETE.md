---
id: INV.PKG.VERSION-BUMP-COMPLETE
status: active
governs: product
decision: DEC.2026-08-25.RULE-CLAIMS-TIGHTENED
check: tests/ci/test_version_contract.py::test_bump_updates_every_contract_location
scope: [pkg, product]
supersedes: [INV.PKG.VERSION-LOCKSTEP]
---

# Успешный бамп обновляет все контрактные места одной операцией

Бампер переводит все пять контрактных мест на новую версию за один вызов;
список изменённых файлов называет ровно эти пять путей и ничего больше.
