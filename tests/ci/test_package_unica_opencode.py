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

        # Полный inventory обоих деревьев: сравнение не выборочное, а
        # побайтовое по каждому файлу.
        def inventory(root: Path) -> dict[str, bytes]:
            return {
                path.relative_to(root).as_posix(): path.read_bytes()
                for path in sorted(root.rglob("*"))
                if path.is_file()
            }

        thin_files = inventory(thin_root)
        staging_files = inventory(staging)

        # Полный inventory различает три намеренных класса отличий: перенос,
        # преобразование и удаление; всё прочее невозможно.
        carried = set(thin_files) & set(staging_files)
        transformed = {
            name for name in carried if thin_files[name] != staging_files[name]
        }
        removed = set(thin_files) - set(staging_files)
        added = set(staging_files) - set(thin_files)

        # Каждый переносимый файл тонкого корня доезжает теми же байтами.
        self.assertEqual(transformed, {"README.md"})
        for name in sorted(carried - transformed):
            with self.subTest(carried=name):
                self.assertEqual(staging_files[name], thin_files[name])

        # Единственное преобразование существующего файла — корневой README:
        # он есть в обоих деревьях, а версия кандидата байт-в-байт равна
        # руководству установки OpenCode, но не продукт-README.
        self.assertIn("README.md", thin_files)
        self.assertEqual(
            staging_files["README.md"],
            (PLUGIN_SOURCE / "opencode" / "README.md").read_bytes(),
        )
        self.assertNotEqual(staging_files["README.md"], thin_files["README.md"])

        # Единственные удаления — VCS-ignore файлы: они не должны править
        # правила упаковки самого npm.
        self.assertEqual(
            removed,
            {
                name
                for name in thin_files
                if Path(name).name in {".gitignore", ".npmignore"}
            },
        )

        # Настоящие добавления — ровно два класса: npm-метаданные и адаптер
        # из отслеживаемых файлов; всё прочее в кандидате невозможно.
        thin_module = load_thin_packager()
        tracked = thin_module.git_tracked_plugin_files(REPO_ROOT, PLUGIN_SOURCE)
        expected_additions = {"package.json"} | {
            rel for rel in tracked if Path(rel).parts[0] == "opencode"
        }
        self.assertEqual(added, expected_additions)

        package_json = json.loads(staging_files["package.json"].decode("utf-8"))
        self.assertEqual(package_json["name"], NPM_PACKAGE_NAME)
        self.assertEqual(package_json["version"], version)

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

    def test_the_readme_is_russian_and_names_local_verification(self) -> None:
        readme = (PLUGIN_SOURCE / "opencode" / "README.md").read_text(encoding="utf-8")

        # Статус и разделы руководства: локальная проверка — рабочий способ,
        # npm-установка — отдельный раздел про будущую публикацию.
        self.assertIn("пока не опубликован", readme)
        self.assertIn("Локальная проверка собранного пакета", readme)
        self.assertIn("Установка из npm", readme)
        # Локальный рецепт называет свои команды целиком.
        self.assertIn("npm install --ignore-scripts", readme)
        self.assertIn("file://", readme)
        self.assertIn("node_modules/@apshendev/unica-opencode", readme)
        self.assertIn("opencode debug skill", readme)
        self.assertIn("opencode mcp list", readme)
        self.assertIn("1.18.22", readme)
        self.assertIn("или новее", readme)

    def test_the_readme_documents_ownership_platform_and_caches_in_russian(
        self,
    ) -> None:
        readme = (PLUGIN_SOURCE / "opencode" / "README.md").read_text(encoding="utf-8")

        # Владение сервером, платформы и адреса кешей задокументированы.
        self.assertIn("mcp.unica", readme)
        self.assertIn("заменяется", readme)
        self.assertIn("Windows x64", readme)
        self.assertIn("Linux x64", readme)
        self.assertIn("UNICA_RUNTIME_CACHE_DIR", readme)
        self.assertIn("UNICA_PROVIDER_STATE_DIR", readme)
        self.assertIn("первый запуск", readme.lower())

    def test_the_packed_tarball_carries_the_local_verification_readme(self) -> None:
        if shutil.which("npm") is None:
            self.skipTest("npm is not available")
        thin_root, _version = self.build_thin_root()
        out_dir = self.root / "npm-readme-out"

        self.package_candidate(thin_root, out_dir, runs=None)

        tarball = out_dir / [p.name for p in out_dir.glob("*.tgz")][0]
        self.assertTrue(tarball.is_file(), sorted(p.name for p in out_dir.iterdir()))
        with tarfile.open(tarball, "r:gz") as archive:
            packed = archive.extractfile("package/README.md").read().decode("utf-8")

        self.assertIn("Локальная проверка собранного пакета", packed)
        self.assertIn("npm install --ignore-scripts", packed)
        self.assertIn("opencode debug skill", packed)
        self.assertIn("opencode mcp list", packed)

    def test_the_candidate_documents_a_version_floor_not_a_ceiling(self) -> None:
        readme = (PLUGIN_SOURCE / "opencode" / "README.md").read_text(encoding="utf-8")
        adapter = (PLUGIN_SOURCE / "opencode" / "index.js").read_text(encoding="utf-8")

        # Пол заявлен, перезапуск и первый старт описаны.
        self.assertIn("1.18.22", readme)
        self.assertIn("или новее", readme)
        self.assertIn("перезапустите OpenCode", readme)
        self.assertIn("первый запуск", readme.lower())
        # Адаптер не ограничивает версии OpenCode сверху: гейт — только
        # платформенный.
        self.assertNotIn("opencode-ai@", adapter)
        self.assertNotIn("OPENCODE_VERSION", adapter)

    def test_the_opencode_guide_is_reachable_from_both_readmes(self) -> None:
        guide = "plugins/unica/opencode/README.md"

        root_readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        plugin_readme = (PLUGIN_SOURCE / "README.md").read_text(encoding="utf-8")
        package_json = json.loads(
            (PLUGIN_SOURCE / "package.json").read_text(encoding="utf-8")
        )

        self.assertIn("OpenCode", root_readme)
        self.assertIn(guide, root_readme)
        self.assertIn(guide, plugin_readme)
        self.assertEqual(
            package_json["homepage"],
            "https://github.com/apshendev/unica/blob/main/plugins/unica/opencode/README.md",
        )

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

    # --- local-debug режим: кандидат из текущего хоста -------------------

    def build_local_debug_root(self, *, target: str = "win-x64") -> Path:
        """Построить настоящий local-debug корень реальным thin-упаковщиком.

        Повторяет приемлемый минимум fixtures `test_package_unica_plugin.py`
        (см. test_local_debug_mode_remains_current_host_only...): bundle с
        поддельными бинарниками всех залоченных инструментов + core.
        """
        thin_module = load_thin_packager()
        lock = json.loads(
            (REPO_ROOT / "plugins/unica/third-party/tools.lock.json").read_text(
                encoding="utf-8"
            )
        )
        triple = lock["targets"][target]["targetTriple"]
        bundle = self.root / "debug-tools" / f"unica-tools-{target}"
        bin_dir = bundle / "bin" / target
        bin_dir.mkdir(parents=True)
        tools = []
        for locked in lock["tools"]:
            binary = bin_dir / locked["binaryName"]
            binary.write_bytes(locked["name"].encode())
            tools.append(
                {
                    "name": locked["name"],
                    "version": locked["version"],
                    "repository": locked["repository"],
                    "upstreamUrl": f"{locked['repository']}/releases/tag/{locked['sourceTag']}",
                    "sourceTag": locked["sourceTag"],
                    "sourceCommit": locked["sourceCommit"],
                    "license": locked["license"],
                    "targetTriple": triple,
                    "binaryPath": f"bin/{target}/{locked['binaryName']}",
                    "sha256": thin_module.sha256(binary),
                }
            )
        core_exe = "unica.exe" if target == "win-x64" else "unica"
        core = bin_dir / core_exe
        core.write_bytes(b"current-host unica core")
        locked_core = next(
            locked for locked in lock["tools"] if locked["name"] == "unica"
        )
        tools.append(
            {
                "name": "unica",
                "version": locked_core["version"],
                "repository": locked_core["repository"],
                "upstreamUrl": f"{locked_core['repository']}/releases/tag/{locked_core['sourceTag']}",
                "sourceTag": locked_core["sourceTag"],
                "sourceCommit": locked_core["sourceCommit"],
                "license": locked_core["license"],
                "targetTriple": triple,
                "binaryPath": f"bin/{target}/{core_exe}",
                "sha256": thin_module.sha256(core),
            }
        )
        (bundle / "tools.json").write_text(
            json.dumps({"target": target, "targetTriple": triple, "tools": tools}),
            encoding="utf-8",
        )
        out_dir = self.root / "debug-plugin-out"
        argv = [
            "package-unica-plugin.py",
            "--repo-root",
            str(REPO_ROOT),
            "--tools-root",
            str(self.root / "debug-tools"),
            "--lock-file",
            "plugins/unica/third-party/tools.lock.json",
            "--out-dir",
            str(out_dir),
            "--local-debug-target",
            target,
        ]
        with patch("sys.argv", argv):
            thin_module.main()
        return out_dir / "marketplace" / "plugins" / "unica"

    def package_local_debug(self, debug_root: Path, out_dir: Path, *, runs) -> None:
        module = load_opencode_packager()
        argv = [
            "package-unica-opencode.py",
            "--repo-root",
            str(REPO_ROOT),
            "--local-debug-root",
            str(debug_root),
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

    def test_local_debug_candidate_carries_current_host_binaries_and_marker(
        self,
    ) -> None:
        debug_root = self.build_local_debug_root()
        out_dir = self.root / "debug-npm-out"
        runs: list = []

        self.package_local_debug(debug_root, out_dir, runs=runs)

        staging = out_dir / "staging"
        self.assertEqual(len(runs), 1)
        cmd, cwd = runs[0]
        self.assertEqual(cmd[:2], ["npm", "pack"])
        self.assertEqual(cwd, staging)

        # Вход доезжает теми же байтами, кроме классов переноса, описанных
        # контрактом CTR.PKG.OPENCODE-LOCAL-DEBUG-COMPOSITION.
        def inventory(root: Path) -> dict[str, bytes]:
            return {
                path.relative_to(root).as_posix(): path.read_bytes()
                for path in sorted(root.rglob("*"))
                if path.is_file()
            }

        source_files = inventory(debug_root)
        staged_files = inventory(staging)
        carried = set(source_files) & set(staged_files)
        transformed = {
            name for name in carried if source_files[name] != staged_files[name]
        }
        removed = set(source_files) - set(staged_files)
        added = set(staged_files) - set(source_files)

        self.assertEqual(transformed, {"README.md"})
        self.assertEqual(
            removed,
            {
                name
                for name in source_files
                if Path(name).name in {".gitignore", ".npmignore"}
            },
        )
        thin_module = load_thin_packager()
        tracked = thin_module.git_tracked_plugin_files(REPO_ROOT, PLUGIN_SOURCE)
        expected_additions = {"package.json", "opencode/local-debug.json"} | {
            rel for rel in tracked if Path(rel).parts[0] == "opencode"
        }
        self.assertEqual(added, expected_additions)

        # Текущий бинарник ядра присутствует; tracked bootstrap/launch.sh
        # доезжает, но бинарной матрицы bootstrap в local-debug кандидате нет.
        self.assertIn("bin/win-x64/unica", staged_files)
        self.assertFalse(
            any(name.startswith("bootstrap/bin/") for name in staged_files)
        )

        # Маркер — единственная сгенерированная строка режима: он называет
        # режим, цель и версию пакета, с которым собран кандидат.
        marker = json.loads(staged_files["opencode/local-debug.json"])
        self.assertEqual(marker["mode"], "local-debug")
        self.assertEqual(marker["target"], "win-x64")
        self.assertEqual(
            marker["pluginVersion"],
            json.loads(staged_files["package.json"].decode("utf-8"))["version"],
        )

    def test_a_release_root_is_refused_as_local_debug_input(self) -> None:
        thin_root, _version = self.build_thin_root()
        runs: list = []

        with self.assertRaises(SystemExit) as ctx:
            self.package_local_debug(
                thin_root, self.root / "debug-release-out", runs=runs
            )

        self.assertIn("development", str(ctx.exception))
        self.assertEqual(runs, [])

    def test_local_debug_input_without_a_core_binary_is_refused(self) -> None:
        debug_root = self.build_local_debug_root()
        # На win-x64 binaryName ядра из lock — `unica` без суффикса.
        for name in ("unica", "unica.exe"):
            core = debug_root / "bin" / "win-x64" / name
            if core.is_file():
                core.unlink()
        runs: list = []

        with self.assertRaises(SystemExit) as ctx:
            self.package_local_debug(
                debug_root, self.root / "debug-nobin-out", runs=runs
            )

        self.assertIn("core binary", str(ctx.exception))
        self.assertEqual(runs, [])

    def test_both_candidate_inputs_at_once_are_refused(self) -> None:
        thin_root, _version = self.build_thin_root()
        debug_root = self.build_local_debug_root()
        module = load_opencode_packager()
        argv = [
            "package-unica-opencode.py",
            "--repo-root",
            str(REPO_ROOT),
            "--thin-root",
            str(thin_root),
            "--local-debug-root",
            str(debug_root),
            "--out-dir",
            str(self.root / "both-out"),
        ]
        runs: list = []

        with (
            patch("sys.argv", argv),
            self.assertRaises(SystemExit) as ctx,
            patch.object(
                module,
                "run",
                side_effect=lambda cmd, *, cwd=None: runs.append((cmd, cwd)),
            ),
        ):
            module.main()

        self.assertIn("--thin-root", str(ctx.exception))
        self.assertEqual(runs, [])


if __name__ == "__main__":
    unittest.main()
