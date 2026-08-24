---
id: DEC.2026-08-24.OPENCODE-ADAPTER-DELIVERY
status: active
governs: product
realized: tests/ci/test_opencode_adapter.py::test_the_adapter_takes_ownership_of_mcp_unica_and_preserves_neighbours
supersedes: []
superseded-by: null
establishes: [CTR.HOST.OPENCODE-CONFIG, INV.HOST.OPENCODE-SHARED-SURFACE, INV.HOST.OPENCODE-PLATFORM-GATE, INV.PKG.NPM-CANDIDATE-FROM-THIN-ROOT, INV.PKG.VERSION-LOCKSTEP]
design: docs/design/2026-08-24-opencode-adapter-delivery-design.md
---

# OpenCode — хост-адаптер с npm-адресом доставки

**Решение.** OpenCode — ещё один хост того же продукта Unica. Адаптер —
небольшой JavaScript-модуль в исходном корне плагина (`opencode/index.js`),
который выставляет один конфигурационный хук: добавляет упакованный корень
скиллов в `skills.paths` и владеет записью `mcp.unica`, запуская упакованный
нативный bootstrap напрямую. Пакет `@apshendev/unica-opencode` — адрес
доставки, а не второй продукт и не вторая реализация MCP.

**Почему.** Модель плагинов OpenCode отличается от манифестных хостов: она
ожидает мутирующий конфигурацию модуль из npm. Держать адаптер вне реестра
хостов Rust и вне фасада хоста — условие лёгких сливов с upstream: Rust не
узнаёт про OpenCode, а JavaScript не переизобретает установку рантайма.
Версия npm-пакета входит в общий контракт версий, поэтому адрес доставки не
может отстать от выпуска.

**Цена.** `mcp.unica` замещается всегда: пользовательская запись под этим
именем не может помешать упакованному серверу стартовать — и не может его
настроить. Поддержка — только Windows x64 и Linux x64: macOS и прочие
архитектуры получают явный отказ при инициализации. Пол потребителя
(OpenCode 1.18.22) фиксируется дымовыми потребителями выпуска, а не кодом
адаптера.

**Что не меняется.** Идентичность публичного MCP-сервера, поверхность
`unica.*`, оркестратор, реестр хостов Rust и алгоритм установки рантайма.
Адаптер не оборачивает инструменты как нативные инструменты OpenCode и не
добавляет иных хуков. Каталоги Codex и Claude Code не затронуты.
