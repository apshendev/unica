---
id: CTR.HOST.OPENCODE-SKILLS-PATHS
status: active
governs: product
version: 1
decision: DEC.2026-08-25.RULE-CLAIMS-TIGHTENED
producer: plugins/unica/opencode/index.js
consumers: [host, review, docs]
check: tests/ci/test_opencode_adapter.py::test_the_packaged_skills_root_is_appended_once_and_others_survive
scope: [host, pkg]
supersedes: [CTR.HOST.OPENCODE-CONFIG]
---

# Упакованный корень скиллов попадает в skills.paths один раз

Конфигурационный хук добавляет упакованный корень скиллов в `skills.paths`
ровно один раз, сохраняя прочие пути и URL.
