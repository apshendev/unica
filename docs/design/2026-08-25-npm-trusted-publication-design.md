- Date: `2026-08-25`
- Status: `approved`
- Decision: `DEC.2026-08-25.NPM-TRUSTED-PUBLICATION`

# npm trusted publication design

## Problem

Issue #3 produces a version-locked npm candidate for OpenCode, but nothing
delivers it to the registry. Publication must run from tagged fork releases,
authenticate without a long-lived npm token, never run from the upstream
repository, never publish a different package identity, and stay safely
resumable — all without touching the upstream Codex/Claude marketplace
promotion.

## Solution shape

### Job placement and gating

A new `publish-opencode-npm` job in `unica-plugin-release.yml` needs
`package-thin` and `verify-published-assets`, so runtime assets are published
**and** re-downloaded and byte-verified before npm is contacted. The job
condition additionally requires a tag push and
`github.repository == 'apshendev/unica'`. The aggregate gate
(`unica-ci`/`evaluate-ci-gate.py`) learns the job: expected `success` only
for a tag contour **in the fork repository**, `skipped` otherwise — so the
same workflow file on upstream (or after an upstream merge) skips the job
silently instead of failing its own release. The fork literal appears in
exactly three gated places (workflow condition, publish script, gate script);
a contract test pins all three to the same bytes.

### Trusted publishing instead of a token

The job carries `permissions: id-token: write` and Node 24's npm (>= 11.5)
exchanges the short-lived OIDC token for the publish. `npm publish <tarball>
--provenance --access public` runs from the repository root so provenance
attestation binds to the tag's git context. No `NODE_AUTH_TOKEN`, no npm
secret anywhere. One-time prerequisite (documented in the release runbook):
the package owner links the trusted publisher (repo, workflow filename,
default branch) to `@apshendev/unica-opencode` in the npm UI before the first
release.

### Defense in depth in the publish script

`scripts/ci/publish-unica-opencode.py` re-validates before invoking npm:
repository is the fork, event is `push`, `GITHUB_REF` is
`refs/tags/v{version}` for the candidate's version, the staging
`package.json` names exactly `@apshendev/unica-opencode`, the runtime
manifest's `pluginVersion` agrees, and the candidate tarball exists. A job
that somehow starts elsewhere refuses before npm hears about it.

### Resumable reruns with integrity

A failed publish recovers by asking the registry, never by parsing npm's
error wording: the script queries `npm view <name>@<version> dist.tarball`;
if the version is absent, the failure stands as a failure. If the registry
serves the version, the tarball is downloaded and compared byte for byte
(SHA-512) with the candidate — identical bytes accept the rerun as complete,
different bytes fail hard ("the published version is not this build").
SemVer prereleases publish under the `next` dist-tag so `latest` never
serves one, mirroring the GitHub prerelease marking. Nothing in this
pipeline deletes or rewrites the git tag or the runtime assets; a red
release stays red until a human decides.

## Alternatives rejected

- **A long-lived `NODE_AUTH_TOKEN` secret** — the exact supply-chain risk
  trusted publishing exists to remove.
- **Gating only in the workflow condition** — a renamed job, a reused
  workflow, or a manual dispatch would bypass it; the script and the gate
  each enforce their own copy of the rule.
- **Deleting and republishing the npm version on rerun** — npm forbids
  republishing a released version, and attempting it would silently replace
  provenance; integrity comparison is the only safe resume.
- **A separate workflow file** — it would need to re-derive the thin root and
  re-implement the ordering guarantees the release workflow already owns.

## What stays untouched

`publish-unica-marketplace.yml` (upstream Codex/Claude catalog promotion),
the two-phase stage/promote publication, thin packaging, and the
`unica.*` tool surface.
