#!/usr/bin/env python3
"""Assemble the OpenCode npm candidate from a verified plugin root.

The candidate is not a second product: it is the same thin package bytes the
Codex and Claude Code hosts consume, plus the npm metadata and the OpenCode
adapter entry from the tracked source. Release identity is validated before
npm is invoked, so a development manifest or a version mismatch can never
become a publishable tarball.

A second, mutually exclusive input builds the local-debug candidate from a
current-host plugin root (see ``--local-debug-root``): the same overlay of
npm metadata and the OpenCode adapter, plus one generated marker file that
switches the adapter to the packaged core binary. The local-debug candidate
is a development artifact and is refused by the publish step.
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
LOCAL_DEBUG_MARKER = "local-debug.json"
LOCAL_DEBUG_MARKER_MODE = "local-debug"
# Имена ядра на всех целях: binaryName в lock на win-x64 — `unica` без .exe,
# поэтому ядро опознаётся по любому из двух написаний.
_CORE_BINARY_NAMES = ("unica", "unica.exe")


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


def assemble_staging(
    thin_root: Path, repo_root: Path, staging: Path, thin_module
) -> None:
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


def validate_local_debug_input(debug_root: Path, thin_module) -> str:
    """Проверить local-debug корень и вернуть цель текущего хоста.

    Вход приходит из ``package-unica-plugin.py --local-debug-target``: его
    манифест обязан быть development-манифестом, а ровно одна цель несёт
    бинарник ядра, который адаптер запустит напрямую.
    """
    manifest_path = debug_root / "runtime-manifest.json"
    if not manifest_path.is_file():
        raise SystemExit(
            f"local-debug root is missing runtime-manifest.json: {manifest_path}"
        )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not manifest.get("development"):
        raise SystemExit(
            f"{manifest_path} is not a development manifest: "
            "--local-debug-root consumes a package-unica-plugin.py "
            "--local-debug-target output, not a release thin root"
        )
    targets_with_core = sorted(
        target
        for target in thin_module.SUPPORTED_TARGETS
        if any(
            (debug_root / "bin" / target / name).is_file()
            for name in _CORE_BINARY_NAMES
        )
    )
    if not targets_with_core:
        raise SystemExit(
            "local-debug root carries no core binary: expected bin/<target>/unica(.exe)"
        )
    if len(targets_with_core) > 1:
        raise SystemExit(
            "local-debug root must carry exactly one host target, found: "
            + ", ".join(targets_with_core)
        )
    return targets_with_core[0]


def write_local_debug_marker(staging: Path, target: str, version: str) -> None:
    marker_path = staging / OPENCODE_ADAPTER_DIR / LOCAL_DEBUG_MARKER
    marker_path.parent.mkdir(parents=True, exist_ok=True)
    marker_path.write_text(
        json.dumps(
            {
                "mode": LOCAL_DEBUG_MARKER_MODE,
                "target": target,
                "pluginVersion": version,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def assemble_local_debug_staging(
    debug_root: Path, repo_root: Path, staging: Path, thin_module
) -> None:
    if staging.exists():
        shutil.rmtree(staging)
    shutil.copytree(debug_root, staging)
    plugin_src = repo_root / "plugins" / "unica"
    copy_npm_sources_from_tracked(repo_root, plugin_src, staging, thin_module)

    readme_src = staging / OPENCODE_ADAPTER_DIR / "README.md"
    if not readme_src.is_file():
        raise SystemExit(f"OpenCode installation guide not found: {readme_src}")
    shutil.copy2(readme_src, staging / "README.md")

    for ignore_name in (".gitignore", ".npmignore"):
        for ignore_path in sorted(staging.rglob(ignore_name)):
            ignore_path.unlink()
    for forbidden in ("node_modules", "package-lock.json"):
        if (staging / forbidden).exists():
            raise SystemExit(f"candidate staging contains {forbidden}")


def load_overlay_applier():
    path = Path(__file__).resolve().parents[1] / "fork" / "apply_overlay.py"
    if not path.is_file():
        raise SystemExit(f"fork overlay applier not found: {path}")
    spec = importlib.util.spec_from_file_location("unica_fork_overlay", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def apply_fork_overlay(staging: Path, overlay_path: Path) -> None:
    """Применить форк-оверлей к staged-копии; см. fork/OVERLAY.md."""
    applier = load_overlay_applier()
    report, ok = applier.apply_overlay(staging, overlay_path, dry_run=False)
    for entry in report:
        status = "ok  " if entry["ok"] else "FAIL"
        note = f"  [{entry['note']}]" if entry.get("note") else ""
        print(
            f"fork-overlay {status} {entry['id']}: "
            f"files={entry['files']} matches={entry['matches']}{note}"
        )
    if not ok:
        raise SystemExit(
            "fork overlay failed: anchor drift after upstream sync — "
            "обнови regex в fork/overlay.json (см. fork/OVERLAY.md)"
        )
    print("fork-overlay: all rules satisfied")


def resolve_overlay_path(args, repo_root: Path):
    if args.no_fork_overlay:
        return None
    if args.fork_overlay is not None:
        return args.fork_overlay
    default = repo_root / "fork" / "overlay.json"
    return default if default.is_file() else None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--thin-root", type=Path)
    parser.add_argument("--local-debug-root", type=Path)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument(
        "--fork-overlay",
        type=Path,
        default=None,
        help="путь к форк-оверлею (умолчание: <repo>/fork/overlay.json, если существует)",
    )
    parser.add_argument(
        "--no-fork-overlay",
        action="store_true",
        help="не применять форк-оверлей к упаковке",
    )
    args = parser.parse_args()

    if (args.thin_root is None) == (args.local_debug_root is None):
        raise SystemExit(
            "exactly one input root is required: --thin-root for a release "
            "candidate or --local-debug-root for a current-host development "
            "candidate"
        )

    repo_root = args.repo_root.resolve()
    thin_module = load_thin_packager()

    if args.local_debug_root is not None:
        debug_root = args.local_debug_root.resolve()
        if not debug_root.is_dir():
            raise SystemExit(f"local-debug plugin root not found: {debug_root}")
        load_source_package(repo_root)
        target = validate_local_debug_input(debug_root, thin_module)

        out_dir = args.out_dir.resolve()
        staging = out_dir / "staging"
        assemble_local_debug_staging(debug_root, repo_root, staging, thin_module)
        version = json.loads((staging / "package.json").read_text(encoding="utf-8"))[
            "version"
        ]
        write_local_debug_marker(staging, target, version)
        overlay_path = resolve_overlay_path(args, repo_root)
        if overlay_path is not None:
            apply_fork_overlay(staging, overlay_path)
        elif args.fork_overlay is not None:
            raise SystemExit(f"fork overlay not found: {args.fork_overlay}")
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
        return

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
    overlay_path = resolve_overlay_path(args, repo_root)
    if overlay_path is not None:
        apply_fork_overlay(staging, overlay_path)
    elif args.fork_overlay is not None:
        raise SystemExit(f"fork overlay not found: {args.fork_overlay}")
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
