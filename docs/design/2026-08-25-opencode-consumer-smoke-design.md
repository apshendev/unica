- Date: `2026-08-25`
- Status: `approved`
- Decision: `DEC.2026-08-25.OPENCODE-CONSUMER-SMOKE`

# OpenCode consumer smoke design

## Problem

Issue #4 made the npm publication a release-gated step, but nothing proves
that the published tarball works for a real OpenCode consumer. A broken
adapter, a skill path the host does not discover, or an MCP entry that never
connects would surface only in a user's editor after the release is done.

## Solution shape

Two release-workflow jobs — `smoke-opencode-windows` (blocking) and
`smoke-opencode-linux` (`continue-on-error: true`, observed but
non-blocking) — run after `publish-opencode-npm` on tagged fork releases
only. Each job:

1. installs a pinned OpenCode `opencode-ai@1.18.22` globally — the declared
   support floor, exact version so a newer CLI cannot mask a floor
   regression;
2. resolves the release version from the checked-out `plugins/unica/package.json`
   and adds the plugin as `opencode plugin "@apshendev/unica-opencode@<version>"`
   from the npm registry — the exact published version, never a checkout;
3. redirects the runtime cache (`UNICA_RUNTIME_CACHE_DIR`) into the job's
   temp directory so the consumer exercises a genuine cold start;
4. runs `opencode debug skill`, captures the JSON, and verifies every
   packaged skill (`skills/*/SKILL.md`) is listed — fail-closed on missing
   skills and on non-JSON output;
5. runs `opencode mcp list`, captures the text, and verifies `unica` is
   reported connected with `unica-bootstrap` in its command.

The verifier is `scripts/ci/smoke-opencode-consumer.py` with two subcommands
(`verify-skills`, `verify-mcp`); its logic is covered by unit tests with
synthetic inputs, and the workflow wiring by workflow-contract tests.

## Alternatives rejected

- **Smoke against a checkout instead of the registry** — would not prove the
  published artifact; the spec requires the exact published version.
- **`opencode-ai@latest`** — the support promise is a floor (1.18.22), and a
  moving CLI version would make failures un attributable to the release.
- **A blocking Linux job** — Linux support is best-effort by specification;
  the job stays visible via `continue-on-error` without gating.
- **A macOS OpenCode consumer** — macOS is outside the OpenCode support
  promise; the Codex/Claude macOS jobs remain untouched.
- **Sharing one matrix job** — the blocking asymmetry (Windows blocks, Linux
  does not) plus distinct runner defaults made two explicit jobs clearer than
  a matrix with conditional `continue-on-error`.

## Deferred

The floor value lives in the workflow job and the package README; a future
change may centralize it if a second consumer surface appears.
