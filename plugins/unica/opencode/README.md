# Unica for OpenCode

This npm package installs the [Unica](https://github.com/apshendev/unica)
1C:Enterprise development workflows into
[OpenCode](https://opencode.ai): the complete packaged skill set and the
single public `unica` MCP server with its `unica.*` tools.

## Installation

Add the package to the `plugin` array in your OpenCode configuration
(`opencode.json` in the project, or `~/.config/opencode/opencode.json`
globally):

```json
{
  "plugin": ["@apshendev/unica-opencode"]
}
```

Then **quit and restart OpenCode**. OpenCode installs npm plugins at startup
and configuration-time changes only take effect after a restart.

The documentation uses the unpinned package name so OpenCode follows the
current release. To pin a version, use ordinary npm syntax:
`"@apshendev/unica-opencode@0.12.0"`.

OpenCode `1.18.22` or newer is required.

## What the adapter does on initialization

- Adds its packaged `skills/` directory to your skill paths **once**;
  your own skill paths and remote skill URLs are preserved.
- Takes ownership of the `mcp.unica` entry: the value present at
  `mcp.unica` **is always replaced** by the packaged definition. A stale or
  incompatible manual entry cannot keep the packaged server from starting.
  Every other MCP server entry is preserved.
- Starts the packaged native bootstrap directly
  (`unica-bootstrap run --plugin-root <package root>`), which verifies the
  pinned runtime (archive and file hashes) before launching `unica`.

The adapter does not wrap `unica.*` tools as native OpenCode tools and does
not add any other hooks.

## Supported platforms

- Windows x64
- Linux x64 (best-effort compatibility)

macOS and other architectures fail clearly during initialization instead of
launching a wrong binary.

## First startup and caches

The first start downloads the verified core runtime, which can take minutes
on a slow link; the MCP startup timeout is raised to 15 minutes so a cold
install is not killed mid-download. Later starts reuse the verified runtime
cache and start quickly.

Runtime cache and provider state live in an OpenCode-specific area of your
cache home (`<cache>/opencode/unica/runtime` and
`<cache>/opencode/unica/provider-state`), where `<cache>` is
`$XDG_CACHE_HOME` (or `%LOCALAPPDATA%` on Windows, or `~/.cache`).
Set `UNICA_RUNTIME_CACHE_DIR` or `UNICA_PROVIDER_STATE_DIR` in the
environment to override these locations; existing values always win.

## License

LGPL-3.0-or-later, as Unica. See `LICENSE` and `ATTRIBUTIONS.md` inside the
package.
