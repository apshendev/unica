## Problem Statement

The maintainer uses a fork of Unica and needs the same Unica product to work as an OpenCode plugin without turning the fork into a permanently divergent distribution. Today the shared plugin package is consumable by Codex CLI and Claude Code, but OpenCode uses a different plugin model: it loads JavaScript or TypeScript modules from npm or local configuration directories and expects those modules to mutate its merged configuration. An OpenCode user therefore cannot install the fork with one normal OpenCode plugin entry and receive the packaged skills plus the single public `unica` MCP server.

The fork must add this capability as an isolated host adapter so that upstream updates remain easy to merge. The adapter must use the existing thin-package and bootstrap delivery model, publish runtime assets from the fork rather than accidentally downloading upstream binaries, keep every release identity in lockstep, and avoid weakening the existing Codex and Claude Code contracts. Windows is the supported development and release platform; Linux receives a best-effort compatibility smoke; macOS is not part of the OpenCode support promise.

## Solution

Publish a scoped npm plugin named `@apshendev/unica-opencode`. An OpenCode user adds that unpinned package name to the `plugin` array in OpenCode configuration and restarts OpenCode. The plugin's configuration hook discovers its packaged Unica root, adds the shared skills directory to OpenCode's skill paths, and installs a local MCP definition named `unica` that starts the packaged native bootstrap directly.

The OpenCode adapter is another delivery adapter for the same Unica product, not a separate product and not a second MCP implementation. It exposes the existing skills and the existing single public `unica` server with its `unica.*` tool surface. It does not wrap those tools as native OpenCode tools.

The npm artifact is generated from the same verified thin plugin root used by the existing host packages. It carries the common skills, references, manifests, runtime manifest, licenses, and bootstrap matrix. Its version stays equal to the Cargo workspace version, the Codex and Claude Code manifest versions, and the Unica lock entry. Tagged releases of the fork publish their own runtime assets and then publish the npm artifact through npm trusted publishing. A failure to publish or verify npm keeps the release workflow unsuccessful, but does not modify the upstream Codex or Claude Code marketplaces.

## User Stories

1. As an OpenCode user, I want to install Unica by adding one npm package to my OpenCode configuration, so that I do not have to copy plugin files manually.
2. As an OpenCode user, I want the package to work without adapter-specific options, so that first-time setup is predictable.
3. As an OpenCode user, I want all packaged Unica skills to be discoverable, so that OpenCode can use the same workflow guidance as Codex CLI and Claude Code.
4. As an OpenCode user, I want one MCP server named `unica`, so that the public server identity is consistent across host applications.
5. As an OpenCode user, I want the existing `unica.*` tools exposed through MCP, so that OpenCode behavior matches the other hosts.
6. As an OpenCode user, I want the adapter to avoid duplicate native tool wrappers, so that tool names and behavior do not diverge.
7. As an OpenCode user, I want the adapter to preserve unrelated MCP servers, so that installing Unica does not break my other integrations.
8. As an OpenCode user, I want the adapter to preserve unrelated skill paths and remote skill URLs, so that installing Unica composes with my existing configuration.
9. As an OpenCode user, I want repeated initialization to add the Unica skill path only once, so that configuration remains idempotent.
10. As an OpenCode user, I want the plugin to take ownership of `mcp.unica`, so that a stale or incompatible user entry cannot prevent the packaged Unica server from starting.
11. As an OpenCode user, I want an existing `mcp.unica` value to be replaced deterministically, so that the effective configuration does not depend on its previous shape.
12. As a Windows x64 user, I want the adapter to select the packaged Windows bootstrap automatically, so that I do not need Git shell or a manual executable path.
13. As a Linux x64 user, I want the same package to select the packaged Linux bootstrap automatically, so that basic use remains portable where the best-effort smoke passes.
14. As a user on an unsupported operating system or architecture, I want a clear initialization failure, so that the package does not silently launch the wrong binary.
15. As an OpenCode user, I want a cold runtime download to have enough startup time, so that a slow first installation is not killed after the host default timeout.
16. As an OpenCode user, I want later starts to reuse a verified runtime cache, so that normal startup remains fast.
17. As an advanced user, I want existing `UNICA_*` cache and provider-state overrides respected, so that centrally managed storage policies continue to work.
18. As an OpenCode user without overrides, I want runtime and provider state kept in an OpenCode-specific cache area, so that data does not leak into a Codex-named fallback directory.
19. As an OpenCode user, I want runtime archive and file hashes verified before execution, so that the npm adapter preserves Unica's verified atomic installation guarantees.
20. As an OpenCode user, I want package updates to follow the current npm release automatically when I use the unpinned package name, so that staying current is easy.
21. As a user who needs reproducibility, I want a published version to remain addressable explicitly, so that I can pin it even though the primary documentation uses the unpinned form.
22. As the fork maintainer, I want OpenCode packaging isolated from the Rust host facade, so that upstream Rust changes merge with minimal conflict.
23. As the fork maintainer, I want the adapter to reuse the existing bootstrap command, so that there is no second runtime installation implementation to maintain.
24. As the fork maintainer, I want npm packages generated from the existing thin plugin root, so that every host consumes the same product bytes rather than copied skill trees.
25. As the fork maintainer, I want the npm package version included in the release version contract, so that a version bump cannot leave one delivery address behind.
26. As the fork maintainer, I want one version-bump operation to update every contract location atomically, so that malformed input cannot leave a partially bumped tree.
27. As the fork maintainer, I want generated runtime manifests to point at fork releases, so that fork code never downloads a same-version upstream core by accident.
28. As the fork maintainer, I want upstream repository defaults to remain available to the packager, so that the fork-specific change stays additive and upstream-friendly.
29. As the fork maintainer, I want npm publication restricted to tagged releases of `apshendev/unica`, so that an upstream checkout cannot publish the fork-owned npm name.
30. As the fork maintainer, I want npm trusted publishing with provenance, so that no long-lived npm token is needed in repository secrets.
31. As the fork maintainer, I want a rerun to accept an already published version only when its registry integrity matches the candidate bytes, so that release recovery is safe.
32. As the fork maintainer, I want an integrity mismatch to burn the version rather than overwrite it, so that immutable npm releases remain trustworthy.
33. As the fork maintainer, I want npm failure to keep the release workflow red, so that a release is never reported complete without its OpenCode delivery address.
34. As the fork maintainer, I want existing GitHub tag and runtime assets retained after npm failure, so that publication can be resumed rather than destructively restarted.
35. As the fork maintainer, I want the official upstream marketplace publication workflow left unchanged, so that the fork cannot modify IngvarConsulting catalogs or require their credentials.
36. As the fork maintainer, I want existing Codex and Claude Code macOS checks left intact, so that adding OpenCode does not weaken upstream package coverage.
37. As the fork maintainer, I want the OpenCode Windows smoke to block release success, so that the platform used for development is proven before delivery.
38. As the fork maintainer, I want the OpenCode Linux smoke to report failures without blocking publication, so that compatibility information is collected without expanding the support promise.
39. As the fork maintainer, I want the minimum supported OpenCode version fixed at `1.18.22`, so that the plugin API floor is explicit and tested rather than moving with latest.
40. As the fork maintainer, I want current newer OpenCode releases accepted, so that the minimum is a floor rather than an exact runtime pin.
41. As a contributor, I want package-contract tests to fail before implementation when behavior is absent, so that the implementation is driven by observable requirements.
42. As a contributor, I want adapter tests to operate on complete configuration input and output, so that they do not couple to internal helper functions.
43. As a contributor, I want release workflow contracts checked without publishing on every pull request, so that most failures are found before a tag exists.
44. As a contributor, I want architecture records to identify the OpenCode adapter boundary, so that a future refactor does not accidentally move host knowledge into the orchestrator.
45. As a contributor, I want the observable OpenCode configuration shape recorded as a contract, so that changes to skill discovery or MCP startup are deliberate.
46. As a contributor, I want existing package and wire invariants preserved, so that the public tool surface and single-server identity do not change as a side effect.
47. As a user reading the plugin documentation, I want exact installation, restart, support, cache, and conflict behavior documented, so that operational surprises are visible before installation.
48. As the fork maintainer, I want the first-publication prerequisite documented, so that npm package ownership and trusted-publisher configuration are completed before tagging.

## Implementation Decisions

- OpenCode is a host application for the same Unica product. The host adapter is a small JavaScript module loaded by OpenCode; the npm package is a delivery address, not a separate product identity.
- The public npm package name is `@apshendev/unica-opencode`. Primary installation documentation uses the unpinned package name so OpenCode can follow the current release; explicit version pinning remains possible through ordinary npm syntax.
- The minimum supported versions of both OpenCode and its plugin API package are `1.18.22`. This is a compatibility floor, not an exact-version restriction.
- The adapter uses OpenCode's configuration hook. It does not add event hooks, custom tools, commands, agents, authentication providers, or provider integrations.
- The adapter appends the packaged skills root to `skills.paths`, preserves existing paths and URLs, and removes duplicate occurrences of the same packaged path.
- The adapter owns the `unica` key in the OpenCode MCP map and always replaces the value present when its configuration hook runs. It preserves every other MCP entry.
- The effective MCP definition is local, enabled, and named `unica`. It starts the packaged native bootstrap with the existing `run --plugin-root` behavior and uses an absolute package-root-derived command path.
- The adapter selects only Windows x64 and Linux x64 bootstrap targets. OpenCode use on macOS and all unsupported architectures fails explicitly during initialization.
- The MCP timeout is 900,000 milliseconds. In the supported OpenCode API this timeout covers connection startup as well as requests, allowing the verified cold runtime acquisition to complete.
- The child process receives `UNICA_RUNTIME_CACHE_DIR` and `UNICA_PROVIDER_STATE_DIR`. Existing process values win; otherwise the adapter derives OpenCode-specific locations from the user's cache home.
- The npm artifact is assembled from the generated thin plugin root after bootstrap binaries and the release-pinned runtime manifest have been produced. Source-checkout placeholders are never published as a release package.
- The npm artifact contains the common skills, references, assets, licenses, attribution, bootstrap matrix, runtime manifest, tool metadata, and the existing Codex and Claude Code manifests needed by installed-package verification. Test files, build directories, and unrelated generated files are excluded.
- The source plugin root carries npm package metadata and the adapter entry point so the normal tracked-source copy naturally feeds the generated artifact. The production entry point has no runtime dependency on the OpenCode type package.
- A dedicated OpenCode packaging step consumes the already assembled thin root and produces a `.tgz`. It validates release identity and required package contents before invoking npm packaging.
- The core release repository used in generated runtime URLs becomes an explicit packager input with the current upstream repository as its compatibility default. Fork workflows pass the fork repository URL.
- The existing Git marketplace URLs and catalogs remain unchanged. The OpenCode package does not introduce an OpenCode marketplace catalog.
- The npm package version joins the existing lockstep contract. The version reader, validator, and atomic bump operation treat it as another required contract location.
- A tagged fork release publishes runtime assets before npm publication. The npm package and runtime manifest use the same semantic version and source tag.
- npm publication uses GitHub Actions trusted publishing through OIDC with provenance. It is enabled only for the fork repository and public, non-prerelease release policy selected by the existing release flow.
- Publication is resumable. If the npm version already exists, the workflow compares registry integrity with the candidate tarball and succeeds only on an exact match; a mismatch fails without attempting replacement.
- Successful npm publication and the blocking Windows consumer smoke are required for the fork's release workflow to succeed. Linux smoke is non-blocking. Existing Codex and Claude Code checks, including their macOS coverage, remain unchanged.
- The upstream marketplace promotion workflow is not expanded or forked. It continues to reject execution outside the upstream repository, and OpenCode delivery does not alter either existing host catalog.
- The change modifies the host and release architecture contract. It requires a new decision record, an observable OpenCode adapter contract, and checkable invariants for shared surface, version lockstep, client floor, platform gate, and npm publication gate.
- The public MCP server identity, public `unica.*` tool contracts, Rust orchestrator, Rust host descriptor registry, and runtime installation algorithm remain unchanged.
- User documentation states that OpenCode must be restarted after configuration changes, that `mcp.unica` is replaced, which operating systems are supported, where cache/state live, and why the first startup may take longer.
- A separate root glossary is not created merely for this implementation. New canonical terminology is captured in the design and architecture records; a root glossary remains a lazy domain-modeling artifact.

## Testing Decisions

- Good tests assert externally observable package and host behavior rather than helper names, private functions, or exact implementation structure. A refactor that preserves generated bytes, effective configuration, release gates, and OpenCode behavior should not require test rewrites.
- The primary seam is a real minimum-version OpenCode consumer installing the published npm version in an isolated configuration. The smoke proves both `opencode debug skill` discovery and an MCP status that reports `unica` connected.
- The Windows x64 consumer smoke is blocking. The Linux x64 consumer smoke executes the same scenario as best effort and reports its result without blocking. No OpenCode macOS smoke is created.
- The package-contract seam operates on the generated npm tarball and the adapter's public configuration hook. It verifies the full effective configuration from representative pre-populated input, including unconditional `mcp.unica` replacement, preservation of other servers, skill-path deduplication, timeout, cache overrides, and unsupported-target failure.
- The package-contract seam verifies the artifact inventory, executable target selection, release-pinned runtime manifest, required existing host manifests, licensing files, and exclusion of test/build content.
- Version-contract tests include npm metadata and continue to reject malformed semantic versions, mismatches, and partially updated trees. Version-bump tests prove render-before-write atomicity across all contract locations.
- Packager tests prove that the fork repository input changes only runtime asset addresses and that the upstream default remains stable for existing callers.
- Product workflow tests prove repository gating, OIDC permissions, provenance, publication ordering, integrity-based rerun behavior, Windows blocking status, Linux best-effort status, and the absence of OpenCode macOS jobs.
- Architecture registry checks prove that every new rule names an active decision and an executable named check, and that the generated index is current.
- Existing package tests for the shared thin root, launcher, manifests, oldest Claude client, release pins, source hygiene, and platform matrix remain regression coverage and must stay green.
- Existing bootstrap integration tests remain the authority for verified atomic runtime acquisition and package metadata verification. The OpenCode adapter does not duplicate those assertions at lower levels.
- Existing product-contract and version-contract suites are the prior art for static release checks. Existing thin-package and published-bootstrap smoke jobs are the prior art for artifact-level and consumer-level tests.
- New behavior is introduced test-first: each missing behavior is demonstrated by a focused failing contract or consumer test before production code satisfies it.

## Out of Scope

- Publishing or modifying issues, catalogs, releases, or credentials in `IngvarConsulting/unica` or `IngvarConsulting/unica-marketplace`.
- Creating and maintaining an `apshendev/unica-marketplace` fork for Codex or Claude Code.
- Changing the existing Codex CLI or Claude Code installation experience, manifests, catalogs, support floors, or macOS checks except where shared version metadata must remain consistent.
- Adding OpenCode to the Rust host descriptor registry or teaching the Rust orchestrator about OpenCode.
- Changing the public MCP server name, protocol surface, tool names, tool schemas, skill routing, or tool result payloads.
- Reimplementing runtime download, verification, cache publication, engine acquisition, or bootstrap behavior in JavaScript.
- Wrapping `unica.*` calls as native OpenCode custom tools.
- Adding adapter-specific public options for binary paths, skill enablement, release URLs, cache locations, or runtime versions in the first release.
- Supporting OpenCode on macOS, Windows ARM, Linux ARM, or other operating-system/architecture targets.
- Guaranteeing Linux as a blocking supported platform in the first release.
- Running the npm package directly from a source checkout with `cargo run`; release packaging is the supported consumer path.
- Automatically editing a user's OpenCode configuration file or selecting global versus project scope on the user's behalf.
- Preventing a later-loaded third-party OpenCode plugin from replacing `mcp.unica` after the Unica hook has run; normal OpenCode plugin ordering still applies.
- Creating npm ownership or trusted-publisher settings through repository code. Those are one-time external registry prerequisites.
- Publishing a release as part of implementing this specification.

## Further Notes

- OpenCode's plugin model is materially different from the Codex and Claude Code host-manifest model. The canonical distinction is: Unica is the product plugin; the JavaScript module is the OpenCode host adapter; npm is its delivery address.
- OpenCode installs npm plugins with Bun at startup and caches them under its cache tree. Configuration-time changes require quitting and restarting OpenCode.
- OpenCode `1.18.22` accepts a configuration hook that mutates both `skills.paths` and local MCP entries, discovers arbitrary `SKILL.md` files below configured paths, and ignores additional Unica frontmatter fields beyond the required name and description.
- The decision to overwrite `mcp.unica` is deliberate and user-approved. Documentation must make this ownership rule conspicuous.
- The fork currently has no OpenCode package, npm metadata, OpenCode release job, or active OpenCode architecture record. Existing source and packaged delivery support only the two manifest hosts, while the adapter is intentionally kept outside that manifest registry.
- The first public release requires the maintainer to reserve `@apshendev/unica-opencode` and configure the GitHub Actions trusted publisher for the release workflow before creating the tag.
