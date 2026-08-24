"""Contract tests for the OpenCode npm package candidate.

The seam is the generated candidate itself: the packaging step consumes an
assembled thin plugin root, validates release identity, adds the npm metadata
and adapter from the tracked source, and hands the staging tree to npm. Tests
run the real thin packager first so the candidate is proven against genuine
release bytes rather than a hand-built lookalike.
"""

from __future__ import annotations

import importlib.util
import json
import shutil
import tarfile
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[2]
PLUGIN_SOURCE = REPO_ROOT / "plugins" / "unica"

NPM_PACKAGE_NAME = "@apshendev/unica-opencode"


def load_script_module(name: str, script: Path):
    spec = importlib.util.spec_from_file_location(name, script)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to load {script}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_thin_packager():
    return load_script_module(
        "package_unica_plugin_for_opencode",
        REPO_ROOT / "scripts" / "ci" / "package-unica-plugin.py",
    )


def load_opencode_packager():
    return load_script_module(
        "package_unica_opencode",
        REPO_ROOT / "scripts" / "ci" / "package-unica-opencode.py",
    )


def load_release_fixture_maker():
    from tests.ci.test_package_unica_plugin import PackageUnicaPluginTests

    return PackageUnicaPluginTests()


class OpenCodePackageCandidateTests(unittest.TestCase):
    """The candidate is assembled from real thin-package bytes."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)

    def build_thin_root(self) -> tuple[Path, str]:
        """Produce a genuine thin plugin root with the real thin packager."""
        thin_module = load_thin_packager()
        version = thin_module.read_release_version(PLUGIN_SOURCE)
        maker = load_release_fixture_maker()
        inputs = self.root / "inputs"
        inputs.mkdir()
        metadata_root, bootstrap_root, _targets = maker.write_release_fixture(
            inputs, version
        )
        out_dir = self.root / "thin-out"
        argv = [
            "package-unica-plugin.py",
            "--repo-root",
            str(REPO_ROOT),
            "--runtime-metadata-root",
            str(metadata_root),
            "--bootstrap-root",
            str(bootstrap_root),
            "--release-tag",
            f"v{version}",
            "--source-commit",
            "a" * 40,
            "--out-dir",
            str(out_dir),
        ]
        with patch("sys.argv", argv):
            thin_module.main()
        return out_dir / "marketplace" / "plugins" / "unica", version

    def package_candidate(self, thin_root: Path, out_dir: Path, *, runs) -> None:
        module = load_opencode_packager()
        argv = [
            "package-unica-opencode.py",
            "--repo-root",
            str(REPO_ROOT),
            "--thin-root",
            str(thin_root),
            "--out-dir",
            str(out_dir),
        ]
        with patch("sys.argv", argv):
            if runs is None:
                module.main()
            else:
                with patch.object(
                    module,
                    "run",
                    side_effect=lambda cmd, *, cwd=None: runs.append((cmd, cwd)),
                ):
                    module.main()

    def test_the_candidate_carries_the_thin_root_plus_npm_metadata(self) -> None:
        thin_root, version = self.build_thin_root()
        out_dir = self.root / "npm-out"
        runs: list = []

        self.package_candidate(thin_root, out_dir, runs=runs)

        staging = out_dir / "staging"
        # npm packaging is invoked exactly once, on the staging tree, with the
        # tarball destination outside the package.
        self.assertEqual(len(runs), 1)
        cmd, cwd = runs[0]
        self.assertEqual(cmd[:2], ["npm", "pack"])
        self.assertIn("--pack-destination", cmd)
        self.assertEqual(cwd, staging)

        package_json = json.loads(
            (staging / "package.json").read_text(encoding="utf-8")
        )
        self.assertEqual(package_json["name"], NPM_PACKAGE_NAME)
        self.assertEqual(package_json["version"], version)

        # The adapter entry and its user documentation ship with the package;
        # the npm-facing README is the OpenCode installation guide.
        self.assertTrue((staging / "opencode" / "index.js").is_file())
        self.assertEqual(
            (staging / "README.md").read_bytes(),
            (PLUGIN_SOURCE / "opencode" / "README.md").read_bytes(),
        )

        # Release-pinned runtime manifest and the shared bootstrap matrix come
        # from the thin root byte for byte.
        manifest = json.loads(
            (staging / "runtime-manifest.json").read_text(encoding="utf-8")
        )
        self.assertFalse(manifest["development"])
        self.assertEqual(manifest["pluginVersion"], version)
        self.assertEqual(manifest["release"]["tag"], f"v{version}")
        for target, executable in (
            ("win-x64", "unica-bootstrap.exe"),
            ("linux-x64", "unica-bootstrap"),
            ("darwin-arm64", "unica-bootstrap"),
        ):
            self.assertTrue(
                (staging / "bootstrap" / "bin" / target / executable).is_file(), target
            )
        self.assertEqual(
            (staging / "runtime-manifest.json").read_bytes(),
            (thin_root / "runtime-manifest.json").read_bytes(),
        )

        # The existing host manifests travel along for installed-package
        # verification, and the shared consumer content stays in place.
        for required in (
            ".mcp.json",
            ".codex-plugin/plugin.json",
            ".claude-plugin/plugin.json",
            "ATTRIBUTIONS.md",
            "LICENSE",
            "third-party/tools.lock.json",
        ):
            self.assertTrue((staging / required).is_file(), required)
        self.assertTrue(any((staging / "skills").iterdir()))
        self.assertTrue((staging / "skills" / "code-search" / "SKILL.md").is_file())
        self.assertTrue(any((staging / "references").iterdir()))

        # Test and build content stays out of the candidate.
        for forbidden in ("node_modules", "package-lock.json", ".build", "dist"):
            self.assertFalse((staging / forbidden).exists(), forbidden)

    def test_the_thin_root_itself_stays_free_of_npm_metadata(self) -> None:
        thin_root, _version = self.build_thin_root()

        self.assertFalse((thin_root / "package.json").exists())
        self.assertFalse((thin_root / "opencode").exists())

    def test_the_packed_tarball_carries_the_candidate(self) -> None:
        if shutil.which("npm") is None:
            self.skipTest("npm is not available")
        thin_root, version = self.build_thin_root()
        out_dir = self.root / "npm-real-out"

        self.package_candidate(thin_root, out_dir, runs=None)

        tarball = out_dir / f"apshendev-unica-opencode-{version}.tgz"
        self.assertTrue(tarball.is_file(), sorted(p.name for p in out_dir.iterdir()))
        with tarfile.open(tarball, "r:gz") as archive:
            names = archive.getnames()
            package_json = json.loads(
                archive.extractfile("package/package.json").read().decode("utf-8")
            )
            manifest_bytes = archive.extractfile("package/runtime-manifest.json").read()

        self.assertEqual(package_json["name"], NPM_PACKAGE_NAME)
        self.assertEqual(package_json["version"], version)
        self.assertIn("package/opencode/index.js", names)
        self.assertIn("package/skills/code-search/SKILL.md", names)
        self.assertIn("package/.mcp.json", names)
        self.assertIn("package/third-party/tools.lock.json", names)
        self.assertEqual(
            manifest_bytes, (thin_root / "runtime-manifest.json").read_bytes()
        )

    def test_the_candidate_documents_a_version_floor_not_a_ceiling(self) -> None:
        readme = (PLUGIN_SOURCE / "opencode" / "README.md").read_text(encoding="utf-8")
        adapter = (PLUGIN_SOURCE / "opencode" / "index.js").read_text(encoding="utf-8")

        # Пол заявлен, перезапуск и медленный первый старт описаны.
        self.assertIn("`1.18.22` or newer is required", readme)
        self.assertIn("restart OpenCode", readme)
        self.assertIn("first start", readme)
        # Платформенный гейт, владение mcp.unica и адреса кеша задокументированы.
        self.assertIn("Windows x64", readme)
        self.assertIn("Linux x64", readme)
        self.assertIn("mcp.unica", readme)
        self.assertIn("is always replaced", readme)
        self.assertIn("UNICA_RUNTIME_CACHE_DIR", readme)
        # Адаптер не ограничивает версии OpenCode сверху: гейт — только
        # платформенный.
        self.assertNotIn("opencode-ai@", adapter)
        self.assertNotIn("OPENCODE_VERSION", adapter)

    def test_a_development_manifest_never_becomes_a_candidate(self) -> None:
        thin_root, _version = self.build_thin_root()
        mutable = self.root / "dev-thin"
        shutil.copytree(thin_root, mutable)
        manifest_path = mutable / "runtime-manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["development"] = True
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        runs: list = []

        with self.assertRaises(SystemExit) as ctx:
            self.package_candidate(mutable, self.root / "dev-out", runs=runs)

        self.assertIn("development", str(ctx.exception))
        self.assertEqual(runs, [])

    def test_a_version_that_disagrees_with_the_source_is_refused(self) -> None:
        thin_root, _version = self.build_thin_root()
        mutable = self.root / "offversion-thin"
        shutil.copytree(thin_root, mutable)
        manifest_path = mutable / "runtime-manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["pluginVersion"] = "0.0.0"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        runs: list = []

        with self.assertRaises(SystemExit) as ctx:
            self.package_candidate(mutable, self.root / "offversion-out", runs=runs)

        self.assertIn("version", str(ctx.exception))
        self.assertEqual(runs, [])

    def test_a_thin_root_without_a_bootstrap_is_refused(self) -> None:
        thin_root, _version = self.build_thin_root()
        mutable = self.root / "nobootstrap-thin"
        shutil.copytree(thin_root, mutable)
        (mutable / "bootstrap" / "bin" / "linux-x64" / "unica-bootstrap").unlink()
        runs: list = []

        with self.assertRaises(SystemExit) as ctx:
            self.package_candidate(mutable, self.root / "nobootstrap-out", runs=runs)

        self.assertIn("bootstrap", str(ctx.exception))
        self.assertEqual(runs, [])


if __name__ == "__main__":
    unittest.main()
