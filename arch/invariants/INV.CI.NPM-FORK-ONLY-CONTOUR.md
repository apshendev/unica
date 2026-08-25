---
id: INV.CI.NPM-FORK-ONLY-CONTOUR
status: active
governs: product
decision: DEC.2026-08-25.NPM-DIST-TAG-PROMOTION
check: tests/ci/test_evaluate_ci_gate.py::test_the_fork_expects_npm_publication_and_upstream_skips_it
scope: [ci]
supersedes: [INV.PKG.NPM-PUBLICATION-GATE]
---

# npm-контур целиком принадлежит только форку

Агрегатный гейт ждёт от npm-контура (стадирование, оба дымовых
потребителя, promotion) успех только на теговом прогоне форка; upstream
ожидает все эти работы пропущенными, а падение любой из них на форке —
красный выпуск.
