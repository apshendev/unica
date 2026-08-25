#!/usr/bin/env python3
"""Promote the staged OpenCode npm candidate to the consumer dist-tag.

Runs only inside the fork's tagged release workflow, after the consumer
smokes have passed. The gates mirror the staging script: repository, event,
ref, and package identity are checked before the first npm call, and the
npm token must arrive as NODE_AUTH_TOKEN from the `NPM_PROMOTION_TOKEN`
environment secret — a missing token fails closed instead of degrading to
anonymous access.

The script never publishes. Its only mutation is a single
`npm dist-tag add <name>@<version> <target>`, and only forward by SemVer
precedence; an already promoted version is a no-op, and the final state is
reread from the registry and required to name the exact promoted version.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import tarfile
from pathlib import Path
from urllib.request import urlopen


FORK_REPOSITORY = "apshendev/unica"
NPM_PACKAGE_NAME = "@apshendev/unica-opencode"
STAGING_DIST_TAG = "staging"
STABLE_DIST_TAG = "latest"
PRERELEASE_DIST_TAG = "next"
# Одноразовая служебная версия, без которой реестр не отдаёт dist-tags
# несуществующего пакета; собирается вручную по release-runbook.
BOOTSTRAP_VERSION = "0.0.0-bootstrap.1"


def run_process(argv, *, cwd=None):
    """Run one subprocess and report; the caller decides what failure means."""
    executable = shutil.which(argv[0])
    resolved = [executable, *argv[1:]] if executable else argv
    return subprocess.run(resolved, cwd=cwd, capture_output=True, text=True)


def download_registry_tarball(url: str) -> bytes:
    with urlopen(url) as response:
        return response.read()


def _sha512(data: bytes) -> str:
    return hashlib.sha512(data).hexdigest()


def semver_precedence(version: str) -> tuple:
    """Sort key honouring SemVer precedence, not string order.

    Numeric components compare numerically (`0.9.0` < `0.10.0`), and any
    prerelease sorts below its release (`0.13.0-rc.1` < `0.13.0`); among
    prereleases numeric identifiers rank below alphanumeric ones and a
    longer identifier list ranks higher when the common prefix is equal.
    """
    core_text, _, prerelease_text = version.partition("-")
    core = tuple(int(part) for part in core_text.split("."))
    if not prerelease_text:
        return (core, 1, ())
    identifiers = tuple(
        (0, int(part), "") if part.isdigit() else (1, 0, part)
        for part in prerelease_text.split(".")
    )
    return (core, 0, identifiers)


def read_candidate(npm_root: Path) -> tuple[str, str, Path]:
    """Name and version from the single candidate tarball, unpacked."""
    tarballs = sorted(npm_root.glob("*.tgz"))
    if not tarballs:
        raise SystemExit(f"no candidate tarball found under {npm_root}")
    if len(tarballs) > 1:
        raise SystemExit(
            "expected exactly one candidate tarball, found "
            + ", ".join(path.name for path in tarballs)
        )
    tarball = tarballs[0]
    try:
        with tarfile.open(tarball, "r:gz") as archive:
            package_stream = archive.extractfile("package/package.json")
            manifest_stream = archive.extractfile("package/runtime-manifest.json")
            if package_stream is None or manifest_stream is None:
                raise SystemExit(
                    f"candidate tarball {tarball.name} lacks the package payload"
                )
            package = json.loads(package_stream.read().decode("utf-8"))
            manifest = json.loads(manifest_stream.read().decode("utf-8"))
    except (tarfile.TarError, json.JSONDecodeError) as error:
        raise SystemExit(
            f"candidate tarball {tarball.name} is unreadable: {error}"
        ) from error
    if manifest.get("pluginVersion") != package.get("version"):
        raise SystemExit(
            f"runtime manifest pluginVersion {manifest.get('pluginVersion')} "
            f"differs from the candidate version {package.get('version')}"
        )
    return package.get("name"), package.get("version"), tarball


def validate_gating(name: str, version: str, env: dict) -> None:
    if env.get("GITHUB_REPOSITORY") != FORK_REPOSITORY:
        raise SystemExit(
            f"refusing to promote from {env.get('GITHUB_REPOSITORY')!r}: "
            f"npm promotion belongs to {FORK_REPOSITORY} only"
        )
    if env.get("GITHUB_EVENT_NAME") != "push":
        raise SystemExit(
            f"refusing to promote on event {env.get('GITHUB_EVENT_NAME')!r}: "
            "npm promotion requires a tagged push"
        )
    expected_ref = f"refs/tags/v{version}"
    if (
        env.get("GITHUB_REF") != expected_ref
        or env.get("GITHUB_REF_NAME") != f"v{version}"
    ):
        raise SystemExit(
            f"refusing to promote: candidate version {version} requires ref "
            f"{expected_ref}, build runs {env.get('GITHUB_REF')!r}"
        )
    if name != NPM_PACKAGE_NAME:
        raise SystemExit(
            f"refusing to promote {name!r}: "
            f"the fork promotes exactly {NPM_PACKAGE_NAME}"
        )
    if not env.get("NODE_AUTH_TOKEN"):
        raise SystemExit(
            "refusing to promote without the npm token: the promotion step "
            "must receive NPM_PROMOTION_TOKEN as NODE_AUTH_TOKEN"
        )


def read_dist_tags(name: str) -> dict:
    completed = run_process(["npm", "view", name, "dist-tags", "--json"])
    if completed.returncode != 0:
        raise SystemExit(
            f"cannot read dist-tags of {name}: the package is missing from "
            f"the registry; publish the one-time bootstrap "
            f"{BOOTSTRAP_VERSION} first (see docs/release-runbook.md)"
        )
    try:
        tags = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise SystemExit(
            f"registry answered dist-tags of {name} with non-JSON: "
            f"{completed.stdout.strip()!r}"
        ) from error
    if not isinstance(tags, dict):
        raise SystemExit(f"registry answered dist-tags of {name} with {tags!r}")
    return tags


def registry_tarball_url(name: str, version: str) -> str | None:
    """The registry's tarball url, or None when the version is not there."""
    completed = run_process(
        ["npm", "view", f"{name}@{version}", "dist.tarball", "--json"]
    )
    if completed.returncode != 0:
        return None
    try:
        url = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise SystemExit(
            f"registry answered {name}@{version} with non-JSON: "
            f"{completed.stdout.strip()!r}"
        ) from error
    if not (isinstance(url, str) and url.startswith(("http://", "https://"))):
        raise SystemExit(f"registry answered {name}@{version} with a non-url: {url!r}")
    return url


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
    name, version, tarball = read_candidate(npm_root)
    validate_gating(name, version, dict(os.environ))

    dist_tags = read_dist_tags(name)
    if dist_tags.get(STAGING_DIST_TAG) != version:
        raise SystemExit(
            "stage did not complete: "
            f"{name}@{version} is not under the {STAGING_DIST_TAG} dist-tag"
        )

    url = registry_tarball_url(name, version)
    if url is None:
        raise SystemExit(
            f"stage did not complete: {name}@{version} has no registry tarball"
        )
    registry_bytes = download_registry_tarball(url)
    candidate_bytes = tarball.read_bytes()
    if _sha512(registry_bytes) != _sha512(candidate_bytes):
        raise SystemExit(
            "registry tarball bytes differ from the candidate: the staged "
            f"{name}@{version} is not this build; refusing to promote"
        )

    target = PRERELEASE_DIST_TAG if "-" in version else STABLE_DIST_TAG
    current = dist_tags.get(target)
    if current == version:
        print(f"{target} already points at {name}@{version}; promotion is a no-op")
        return
    if current is not None and semver_precedence(version) < semver_precedence(current):
        raise SystemExit(
            f"refusing to move {target} backwards: {current} -> {version} "
            "is not a forward SemVer move"
        )

    completed = run_process(
        ["npm", "dist-tag", "add", f"{name}@{version}", target],
        cwd=str(args.repo_root),
    )
    if completed.returncode != 0:
        raise SystemExit(
            f"npm dist-tag add failed: {(completed.stdout + completed.stderr).strip()}"
        )

    reread = read_dist_tags(name)
    if reread.get(target) != version:
        raise SystemExit(
            f"postcondition failed: {target} is {reread.get(target)!r} after "
            f"the write, expected {version}"
        )
    print(f"promoted {name}@{version} to the {target} dist-tag")


if __name__ == "__main__":
    main()
