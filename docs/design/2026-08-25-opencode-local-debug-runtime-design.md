- Date: `2026-08-25`
- Status: `approved`
- Decision: `DEC.2026-08-25.OPENCODE-LOCAL-DEBUG-RUNTIME`

# OpenCode local-debug runtime design

## Problem

The local npm adapter verification recipe assembles the OpenCode candidate
from a released thin root, so the packaged bootstrap downloads the pinned
release runtime (v0.12.0). That runtime still serves the pre-2026-08-17
`tools/list` wire: 1,115,772 bytes with full per-argument descriptions, which
tokenizes to roughly 250k+ tokens that OpenCode re-attaches to every model
request — the observed endless-compaction loop. The current HEAD serves
204,036 bytes with no wire descriptions, and an isolated OpenCode run against
a directly launched `target/release/unica.exe` completes the same
`unica.project.status` scenario in 27.5 s with zero compaction events. There
is no supported way to put the current-host binary into the npm package: the
release packager refuses development manifests by contract.

## Solution shape

A second, explicitly development-only candidate mode in
`scripts/ci/package-unica-opencode.py`, selected by a mutually exclusive
input:

- `--thin-root` keeps the release path byte-for-byte as
  `CTR.PKG.NPM-CANDIDATE-COMPOSITION` requires.
- `--local-debug-root` consumes the plugin root produced by
  `scripts/ci/package-unica-plugin.py --local-debug-target <target>`: tracked
  plugin sources without npm parts, `bin/<target>/` with current-built
  binaries, the tracked development `runtime-manifest.json`, and the
  direct-launch `.mcp.json`. The mode requires `development: true` — the
  mirror gate of the release refusal — plus exactly one `bin/<target>` with
  the `unica(.exe)` core binary.

The local-debug staging adds the same two tracked classes as the release
candidate (`package.json`, `opencode/**`), replaces the root README with the
OpenCode guide, and writes one generated marker:
`opencode/local-debug.json` with `{"mode": "local-debug", "target": <target>,
"pluginVersion": <version>}`. The marker is generated content — it never
exists in the tracked tree, which is what keeps the adapter's release
behavior the default everywhere except a package built in this mode.

The adapter (`plugins/unica/opencode/index.js`) reads the marker once at
initialization. Without a marker (release packages, source checkout, broken
read) it launches the packaged bootstrap exactly as before. With a valid
marker it launches `<package-root>/bin/<target>/<unica(.exe)>` directly — no
args, stdio MCP — with the same environment derivation, ownership
replacement, and 900000 ms timeout. A marker whose `target` differs from the
host target refuses during initialization, mirroring the existing platform
refusal.

`scripts/ci/publish-unica-opencode.py` refuses to publish any staging that
carries the local-debug marker or a development manifest, before any npm
invocation.

## Alternatives rejected

- **Switch the launch mode off `runtime-manifest.json` `development`** — the
  adapter tests load the real source tree, whose manifest is a development
  manifest; every existing bootstrap-command assertion would flip. The mode
  is a property of npm packaging, not of the Rust workspace, so the marker
  belongs to the packaging step.
- **An environment variable** (`UNICA_LOCAL_DEBUG=1`) — the installed package
  must not silently change behavior because of a leaked variable, and env
  switches are invisible in the shipped artifact.
- **Pointing the dev adapter at `cargo run`** — requires a Rust toolchain
  inside the consumer, which the isolated consumer must not have; the
  packaged current-host binary is the artifact under test.
- **Reusing the installed v0.12 consumer with a swapped cache** — the
  bootstrap verifies the pinned manifest and would re-download the release
  runtime; the runtime identity is owned by the package, not the cache.
- **Narrowing the published tool surface here** — a real follow-up candidate
  (204 KB is still schema-dense), but it is a wire-surface change with its
  own contract path; this design only fixes which runtime the local npm
  package launches.

## Deferred

A local-debug-aware README variant and a Windows helper script mirroring
`install-local-unica.sh` are deferred until the recipe is used beyond this
fork's verification loop.
