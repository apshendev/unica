#!/usr/bin/env python3
"""Stage the OpenCode npm candidate through npm trusted publishing.

Runs only inside the fork's tagged release workflow: the repository, event,
and ref gates live here as well as in the workflow, so a job that somehow
starts elsewhere refuses before npm is invoked. Authentication is the
short-lived OIDC token of trusted publishing — no long-lived npm token exists
anywhere in the repository.

Publication only stages the candidate under the `staging` dist-tag: moving
the consumer-facing `latest`/`next` tags is the job of
`promote-unica-opencode.py`, which runs after the consumer smokes. A
successful publish is not trusted blindly: the script polls the registry
until it serves this exact version with byte-identical tarball bytes, and a
failed publish recovers by the same byte comparison rather than by parsing
npm's wording.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import time
from pathlib import Path
from urllib.request import urlopen


FORK_REPOSITORY = "apshendev/unica"
NPM_PACKAGE_NAME = "@apshendev/unica-opencode"
STAGING_DIST_TAG = "staging"
REGISTRY_VISIBILITY_ATTEMPTS = 30
REGISTRY_VISIBILITY_PAUSE_SECONDS = 10


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


def _registry_serves_identical_bytes(url: str, candidate_bytes: bytes) -> bool:
    registry_bytes = download_registry_tarball(url)
    if _sha512(registry_bytes) != _sha512(candidate_bytes):
        raise SystemExit(
            "registry tarball bytes differ from the candidate: the published "
            f"{NPM_PACKAGE_NAME} is not this build; refusing to continue"
        )
    return True


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
    """The registry's tarball url, or None when the version is not there.

    npm failing means the version is not visible yet. npm succeeding with
    anything but a JSON http(s) tarball url is a broken answer, not
    invisibility, and is fatal.
    """
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


def wait_for_registry_visibility(
    name: str,
    version: str,
    candidate_bytes: bytes,
    *,
    attempts: int = 30,
    pause_seconds: float = 10.0,
) -> None:
    """Poll until the registry serves this version with identical bytes."""
    for attempt in range(1, attempts + 1):
        url = registry_tarball_url(name, version)
        if url is not None:
            _registry_serves_identical_bytes(url, candidate_bytes)
            return
        if attempt < attempts:
            time.sleep(pause_seconds)
    raise SystemExit(
        f"registry visibility timeout: {name}@{version} did not appear after "
        f"{attempts} attempts"
    )


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
        # Стадирование, а не выпуск: под `staging` версию ставят только
        # smoke-потребители, потребительские `latest`/`next` двигает
        # promotion после их отчёта.
        "--tag",
        STAGING_DIST_TAG,
    ]

    candidate_bytes = tarball.read_bytes()
    completed = run_process(publish_argv, cwd=str(args.repo_root))
    if completed.returncode == 0:
        wait_for_registry_visibility(
            NPM_PACKAGE_NAME,
            version,
            candidate_bytes,
            attempts=REGISTRY_VISIBILITY_ATTEMPTS,
            pause_seconds=REGISTRY_VISIBILITY_PAUSE_SECONDS,
        )
        print(
            f"staged {NPM_PACKAGE_NAME}@{version} under the "
            f"{STAGING_DIST_TAG} dist-tag with provenance"
        )
        return
    # Recovery asks the registry, never npm's wording: a rerun is accepted
    # only when this exact version is already served with identical bytes.
    url = registry_tarball_url(NPM_PACKAGE_NAME, version)
    if url is None:
        raise SystemExit(
            f"npm publish failed and {NPM_PACKAGE_NAME}@{version} is not in "
            f"the registry: {(completed.stdout + completed.stderr).strip()}"
        )
    _registry_serves_identical_bytes(url, candidate_bytes)
    print(
        f"{NPM_PACKAGE_NAME}@{version} is already published with identical "
        "bytes; rerun accepted"
    )


if __name__ == "__main__":
    main()
