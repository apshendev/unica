---
id: INV.PKG.NPM-PROMOTION-FORWARD-ONLY
status: active
governs: product
decision: DEC.2026-08-25.NPM-DIST-TAG-PROMOTION
check: tests/ci/test_promote_unica_opencode.py::test_promotion_refuses_to_move_a_dist_tag_backwards
scope: [pkg, ci]
supersedes: []
---

# Dist-tag двигается только вперёд по SemVer

Promotion отказывается двигать потребительский dist-tag на версию
ниже текущей. Полная матрица SemVer-порядка — числовые компоненты,
префиксы, старшинство пре-релиза перед релизом — и отказ обратного хода
прогоняются subTest'ами одного агрегатного теста.
