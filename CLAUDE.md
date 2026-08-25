See [AGENTS.md](AGENTS.md) for entry points, source-of-truth ordering, search
hygiene, and development rules. That file applies to Claude Code unchanged.

## Claude-specific notes

- Unica ships as one plugin directory for two hosts. Claude Code reads
  `plugins/unica/.claude-plugin/plugin.json` and ignores `.codex-plugin/`.
- Load the source tree directly with `claude --plugin-dir ./plugins/unica`; no
  marketplace or install step is involved.
- Skills are namespaced by the plugin, so `meta-info` is invoked as
  `/unica:meta-info`.
- MCP tools are exposed as `mcp__plugin_unica_unica__<tool>`, with every
  character outside `A-Za-z0-9_-` replaced by `_`. The skill prose names tools in
  their canonical dotted form, so `unica.meta.info` is callable as
  `mcp__plugin_unica_unica__unica_meta_info`.

## Agent skills

### Issue tracker

Issues live in GitHub Issues of the fork (`apshendev/unica`) via `gh`. See `docs/agents/issue-tracker.md`.

### Triage labels

Canonical five; label strings equal role names. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context, adapted to the existing `arch/` registry: decisions live in
`arch/decisions/` (`DEC.*`), glossary lazily in root `CONTEXT.md`. See `docs/agents/domain.md`.
