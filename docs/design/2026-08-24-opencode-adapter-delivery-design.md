- Date: `2026-08-24`
- Status: `approved`
- Decision: `DEC.2026-08-24.OPENCODE-ADAPTER-DELIVERY`

# OpenCode delivery adapter design

## Problem

OpenCode consumes plugins as JavaScript modules installed from npm that
mutate its merged configuration. The fork's shared thin plugin root serves
Codex CLI and Claude Code, so an OpenCode user has no one-step installation
that yields the packaged skills plus the single public `unica` MCP server.

## Solution shape

Unica stays the product; the JavaScript module is only the OpenCode **host
adapter**, and npm is its **delivery address**. The adapter lives in the
tracked source root of the plugin (`plugins/unica/opencode/index.js`) next to
the npm metadata (`plugins/unica/package.json`), so the normal tracked-source
copy feeds the generated artifact naturally. Nothing about OpenCode enters
the Rust host descriptor registry, the orchestrator, or the runtime
installation algorithm.

### Configuration hook

The module exports one plugin, `UnicaOpenCodePlugin`, with a single `config`
hook (the shape OpenCode 1.18.22 provides). The hook:

- appends `<package root>/skills` to `skills.paths` exactly once (existing
  duplicates of the same packaged path are removed; other paths and all
  remote skill URLs are preserved);
- always replaces `config.mcp.unica` with a local, enabled entry whose
  command is the packaged native bootstrap invoked as
  `unica-bootstrap run --plugin-root <package root>` and whose timeout is
  900,000 ms so the verified cold runtime acquisition fits the budget;
- passes `UNICA_RUNTIME_CACHE_DIR` and `UNICA_PROVIDER_STATE_DIR` to the
  child: existing process values win, otherwise the values are derived from
  the user's cache home into `<cache>/opencode/unica/{runtime,provider-state}`
  so state never leaks into a Codex-named fallback directory.

Every other MCP entry and skill path is preserved. Paths in the produced
configuration are POSIX-normalized for stable assertions across platforms.

### Platform gate

Only `win32-x64` and `linux-x64` select a bootstrap target. Every other
platform/architecture combination throws during initialization with a message
naming the supported pair and the offending combination. macOS is explicitly
outside the OpenCode support promise.

### npm candidate packaging

`scripts/ci/package-unica-opencode.py` consumes the already assembled thin
plugin root (release-pinned runtime manifest, bootstrap matrix, host
manifests, skills, references, licenses) produced by the existing thin
packager, validates the release identity (no development manifest, versions
and tag agree), copies the npm metadata and the adapter directory in from the
tracked source, replaces the package README with the OpenCode installation
guide, and invokes `npm pack` on the staging tree. The thin packager
excludes the npm delivery sources (`package.json`, `package-lock.json`,
`opencode/`, `node_modules`) from marketplace packages, so the Codex and
Claude Code packages stay byte-identical to their current shape.

### Version lockstep

`plugins/unica/package.json` joins the release version contract:
`check-version-contract.py` reads it, `bump-version.py` writes it in the same
render-before-write pass (now pinned to LF endings), and the npm candidate is
refused when its version disagrees with the thin root.

## Alternatives rejected

- **A second MCP implementation in JavaScript** — would fork the verified
  atomic installation path the bootstrap owns.
- **Teaching the Rust host registry about OpenCode** — couples upstream merges
  to a host only the fork needs.
- **Wrapping `unica.*` tools as native OpenCode tools** — duplicates the tool
  surface and lets behavior diverge between hosts.
- **A separate `apshendev/unica-marketplace`** — out of scope by
  specification; the existing Git catalogs are untouched.
- **Keeping the darwin bootstrap out of the npm artifact** — the runtime
  manifest and bootstrap matrix travel as one thin-root byte stream; the
  platform gate belongs to the adapter, not to artifact surgery.

## Deferred

- npm trusted publishing, integrity-checked reruns, and the release workflow
  jobs are the next issue; nothing here publishes anything.
- The client floor (OpenCode 1.18.22) is documented in the package README and
  enforced by minimum-version consumer smoke jobs in a later issue, which
  will carry its own invariant.
