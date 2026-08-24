#!/usr/bin/env python3
"""Publish the OpenCode npm candidate through npm trusted publishing.

Runs only inside the fork's tagged release workflow: the repository, event,
and ref gates live here as well as in the workflow, so a job that somehow
starts elsewhere refuses before npm is invoked. Authentication is the
short-lived OIDC token of trusted publishing — no long-lived npm token exists
anywhere in the repository.

A failed publish recovers by asking the registry, not by parsing npm's
wording: the rerun is accepted only when the registry already serves this
exact version with byte-identical tarball bytes. A SemVer prerelease
publishes under the `next` dist-tag so `latest` never serves a prerelease.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path
from urllib.request import urlopen


FORK_REPOSITORY = "apshendev/unica"
NPM_PACKAGE_NAME = "@apshendev/unica-opencode"
PRERELEASE_DIST_TAG = "next"


def run_process(argv, *, cwd=None):
    """Run one subprocess and report; the caller decides what failure means."""
    executable = shutil.which(argv[0])
    resolved = [executable, *argv[1:]] if executable else argv
    return subprocess.run(resolved, cwd=cwd, capture_output=True, text=True)


def download_registry_tarball(url: str) -> bytes:
    with urlopen(url) as response:
        return response.read()


def validate_gating(package: dict, tarball: Path, env: dict) -> str:
    if env.get("GITHUB_REPOSITORY") != FORK_REPOSITORY:
        raise SystemExit(
            f"refusing to publish from {env.get('GITHUB_REPOSITORY')!r}: "
            f"npm publication belongs to {FORK_REPOSITORY} only"
        )
    if env.get("GITHUB_EVENT_NAME") != "push":
        raise SystemExit(
            f"refusing to publish on event {env.get('GITHUB_EVENT_NAME')!r}: "
            "npm publication requires a tagged push"
        )
    version = package["version"]
    expected_ref = f"refs/tags/v{version}"
    if (
        env.get("GITHUB_REF") != expected_ref
        or env.get("GITHUB_REF_NAME") != f"v{version}"
    ):
        raise SystemExit(
            f"refusing to publish: candidate version {version} requires ref "
            f"{expected_ref}, build runs {env.get('GITHUB_REF')!r}"
        )
    if package.get("name") != NPM_PACKAGE_NAME:
        raise SystemExit(
            f"refusing to publish {package.get('name')!r}: "
            f"the fork publishes exactly {NPM_PACKAGE_NAME}"
        )
    if not tarball.is_file():
        raise SystemExit(f"candidate tarball not found: {tarball}")
    return version


def registry_tarball_url(name: str, version: str) -> str | None:
    """The registry's tarball url, or None when the version is not there."""
    completed = run_process(
        ["npm", "view", f"{name}@{version}", "dist.tarball", "--json"]
    )
    if completed.returncode != 0:
        return None
    url = json.loads(completed.stdout)
    return url if isinstance(url, str) and url else None


def main(argv=None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[2],
    )
    parser.add_argument("--npm-root", type=Path, required=True)
    args = parser.parse_args(argv)

    npm_root = args.npm_root.resolve()
    staging = npm_root / "staging"
    package = json.loads((staging / "package.json").read_text(encoding="utf-8"))
    manifest = json.loads(
        (staging / "runtime-manifest.json").read_text(encoding="utf-8")
    )
    if manifest.get("pluginVersion") != package["version"]:
        raise SystemExit(
            f"runtime manifest pluginVersion {manifest.get('pluginVersion')} "
            f"differs from the candidate version {package['version']}"
        )
    tarball = npm_root / (
        f"{NPM_PACKAGE_NAME.removeprefix('@').replace('/', '-')}"
        f"-{package['version']}.tgz"
    )
    version = validate_gating(package, tarball, dict(os.environ))

    publish_argv = [
        "npm",
        "publish",
        str(tarball),
        "--provenance",
        "--access",
        "public",
    ]
    # A prerelease must never answer `npm install @apshendev/unica-opencode`:
    # `latest` stays on the newest stable version, prereleases land on `next`.
    if "-" in version:
        publish_argv += ["--tag", PRERELEASE_DIST_TAG]

    completed = run_process(publish_argv, cwd=str(args.repo_root))
    if completed.returncode == 0:
        print(f"published {NPM_PACKAGE_NAME}@{version} with provenance")
        return
    # Recovery asks the registry, never npm's wording: a rerun is accepted
    # only when this exact version is already served with identical bytes.
    url = registry_tarball_url(NPM_PACKAGE_NAME, version)
    if url is None:
        raise SystemExit(
            f"npm publish failed and {NPM_PACKAGE_NAME}@{version} is not in "
            f"the registry: {(completed.stdout + completed.stderr).strip()}"
        )
    registry_bytes = download_registry_tarball(url)
    candidate_bytes = tarball.read_bytes()
    if (
        hashlib.sha512(registry_bytes).digest()
        != hashlib.sha512(candidate_bytes).digest()
    ):
        raise SystemExit(
            "registry tarball bytes differ from the candidate: the published "
            f"{NPM_PACKAGE_NAME}@{version} is not this build; refusing to "
            "accept the rerun"
        )
    print(
        f"{NPM_PACKAGE_NAME}@{version} is already published with identical "
        "bytes; rerun accepted"
    )


if __name__ == "__main__":
    main()
