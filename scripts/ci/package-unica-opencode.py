#!/usr/bin/env python3
"""Assemble the OpenCode npm candidate from the verified thin plugin root.

The candidate is not a second product: it is the same thin package bytes the
Codex and Claude Code hosts consume, plus the npm metadata and the OpenCode
adapter entry from the tracked source. Release identity is validated before
npm is invoked, so a development manifest or a version mismatch can never
become a publishable tarball.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import subprocess
from pathlib import Path


NPM_PACKAGE_NAME = "@apshendev/unica-opencode"
OPENCODE_ADAPTER_DIR = "opencode"


def load_thin_packager():
    path = Path(__file__).with_name("package-unica-plugin.py")
    spec = importlib.util.spec_from_file_location("package_unica_plugin_shared", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run(cmd, *, cwd=None):
    # On Windows npm is npm.cmd: resolve through PATH so the invocation stays
    # shell-free and identical on POSIX.
    executable = shutil.which(cmd[0])
    argv = [executable, *cmd[1:]] if executable else cmd
    subprocess.run(argv, cwd=cwd, check=True)


def load_source_package(repo_root: Path) -> dict:
    path = repo_root / "plugins" / "unica" / "package.json"
    if not path.is_file():
        raise SystemExit(f"source npm metadata not found: {path}")
    package = json.loads(path.read_text(encoding="utf-8"))
    if package.get("name") != NPM_PACKAGE_NAME:
        raise SystemExit(
            f"source npm package must be named {NPM_PACKAGE_NAME}, found {package.get('name')}"
        )
    return package


def validate_release_identity(
    thin_root: Path, source_package: dict, version: str
) -> None:
    manifest_path = thin_root / "runtime-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("development"):
        raise SystemExit(
            f"{manifest_path} is a development manifest: a release candidate must be release-pinned"
        )
    if manifest.get("pluginVersion") != version:
        raise SystemExit(
            f"runtime manifest pluginVersion {manifest.get('pluginVersion')} "
            f"differs from the release version {version}"
        )
    if manifest.get("release", {}).get("tag") != f"v{version}":
        raise SystemExit(
            f"runtime manifest release tag {manifest.get('release', {}).get('tag')} "
            f"differs from v{version}"
        )
    if source_package.get("version") != version:
        raise SystemExit(
            f"npm package version {source_package.get('version')} differs from "
            f"the release version {version}"
        )


def validate_required_contents(thin_root: Path, supported_targets: dict) -> None:
    for target, (_triple, executable) in sorted(supported_targets.items()):
        bootstrap = thin_root / "bootstrap" / "bin" / target / executable
        if not bootstrap.is_file():
            raise SystemExit(
                f"thin root is missing the {target} bootstrap: {bootstrap}"
            )
    required_dirs = ("skills", "references")
    for name in required_dirs:
        if not (thin_root / name).is_dir():
            raise SystemExit(f"thin root is missing the shared {name} directory")
    required_files = (
        "runtime-manifest.json",
        ".mcp.json",
        "ATTRIBUTIONS.md",
        "LICENSE",
        "third-party/tools.lock.json",
    )
    for name in required_files:
        if not (thin_root / name).is_file():
            raise SystemExit(f"thin root is missing {name}")
    if not any((thin_root / "skills").glob("*/SKILL.md")):
        raise SystemExit("thin root carries no prompt-visible skills")


def copy_npm_sources_from_tracked(
    repo_root: Path, plugin_src: Path, staging: Path, thin_module
) -> None:
    """Copy npm metadata and the adapter through the tracked-source rules."""
    included_roots = {"package.json", OPENCODE_ADAPTER_DIR}
    copied = []
    for rel in thin_module.git_tracked_plugin_files(repo_root, plugin_src):
        rel_path = Path(rel)
        if rel_path.parts[0] not in included_roots:
            continue
        source = plugin_src / rel_path
        if source.is_symlink():
            raise SystemExit(
                f"tracked plugin source symlink is not allowed: {rel_path.as_posix()}"
            )
        thin_module.validate_tracked_plugin_source_path(rel_path)
        target = staging / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        copied.append(rel_path)

    if Path("package.json") not in copied:
        raise SystemExit(f"tracked npm metadata not found under {plugin_src}")
    if Path(OPENCODE_ADAPTER_DIR) / "index.js" not in copied:
        raise SystemExit(f"tracked adapter entry not found under {plugin_src}")


def assemble_staging(thin_root: Path, repo_root: Path, staging: Path, thin_module) -> None:
    if staging.exists():
        shutil.rmtree(staging)
    shutil.copytree(thin_root, staging)
    plugin_src = repo_root / "plugins" / "unica"
    copy_npm_sources_from_tracked(repo_root, plugin_src, staging, thin_module)

    # The npm page belongs to the OpenCode consumer: the product README from
    # the shared root is replaced by the installation guide.
    readme_src = staging / OPENCODE_ADAPTER_DIR / "README.md"
    if not readme_src.is_file():
        raise SystemExit(f"OpenCode installation guide not found: {readme_src}")
    shutil.copy2(readme_src, staging / "README.md")

    # VCS ignore files must not steer npm's own packing rules, and npm build
    # output must stay out of the candidate.
    for ignore_name in (".gitignore", ".npmignore"):
        for ignore_path in sorted(staging.rglob(ignore_name)):
            ignore_path.unlink()
    for forbidden in ("node_modules", "package-lock.json"):
        if (staging / forbidden).exists():
            raise SystemExit(f"candidate staging contains {forbidden}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--thin-root", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    thin_root = args.thin_root.resolve()
    if not thin_root.is_dir():
        raise SystemExit(f"thin plugin root not found: {thin_root}")

    thin_module = load_thin_packager()
    version = thin_module.read_release_version(thin_root)
    source_package = load_source_package(repo_root)
    validate_release_identity(thin_root, source_package, version)
    thin_module.assert_host_manifests_present(thin_root)
    validate_required_contents(thin_root, thin_module.SUPPORTED_TARGETS)

    out_dir = args.out_dir.resolve()
    staging = out_dir / "staging"
    assemble_staging(thin_root, repo_root, staging, thin_module)
    thin_module.assert_archive_clean(staging)

    out_dir.mkdir(parents=True, exist_ok=True)
    run(
        [
            "npm",
            "pack",
            "--json",
            "--ignore-scripts",
            "--pack-destination",
            str(out_dir),
        ],
        cwd=staging,
    )


if __name__ == "__main__":
    main()
