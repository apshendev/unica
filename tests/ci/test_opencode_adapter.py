"""Contract tests for the packaged OpenCode adapter.

The seam is the adapter's public OpenCode plugin hook: a complete
configuration object goes in, the effective configuration comes out. The
adapter file is loaded by a real Node process, so the tests exercise exactly
the module OpenCode would load, with no private helpers involved.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
ADAPTER_PATH = REPO_ROOT / "plugins" / "unica" / "opencode" / "index.js"
DRIVER_PATH = Path(__file__).resolve().parent / "opencode_adapter_driver.mjs"

PACKAGE_NAME = "@apshendev/unica-opencode"
MCP_TIMEOUT_MS = 900_000
CACHE_ENV_KEYS = ("UNICA_RUNTIME_CACHE_DIR", "UNICA_PROVIDER_STATE_DIR")


def run_adapter(instruction: dict) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        instruction_path = Path(tmp) / "instruction.json"
        instruction_path.write_text(json.dumps(instruction), encoding="utf-8")
        completed = subprocess.run(
            ["node", str(DRIVER_PATH), str(instruction_path)],
            capture_output=True,
            text=True,
            check=False,
            cwd=REPO_ROOT,
        )
        if completed.returncode != 0:
            raise AssertionError(
                f"driver failed ({completed.returncode}):\n{completed.stderr}"
            )
        return json.loads(completed.stdout)


def package_root() -> str:
    return str((REPO_ROOT / "plugins" / "unica").resolve()).replace("\\", "/")


class OpenCodeAdapterConfigTests(unittest.TestCase):
    def test_the_module_exports_one_plugin_whose_only_hook_is_config(self) -> None:
        report = run_adapter({"adapterPath": str(ADAPTER_PATH), "config": {}})

        self.assertTrue(report["ok"], report)
        self.assertEqual(report["exports"], ["UnicaOpenCodePlugin"])
        self.assertEqual(report["hooks"], ["config"])

    def test_the_packaged_skills_root_is_appended_once_and_others_survive(self) -> None:
        skills_root = f"{package_root()}/skills"
        config = {
            "skills": {
                "paths": ["~/team-skills", "/abs/shared", skills_root, skills_root],
                "urls": ["https://example.com/.well-known/skills/"],
            }
        }

        report = run_adapter({"adapterPath": str(ADAPTER_PATH), "config": config})

        self.assertTrue(report["ok"], report)
        paths = report["config"]["skills"]["paths"]
        # Exactly one occurrence of the packaged root, appended after the
        # user's own paths, whose order and remote URLs stay untouched.
        self.assertEqual(
            paths,
            ["~/team-skills", "/abs/shared", skills_root],
        )
        self.assertEqual(
            report["config"]["skills"]["urls"],
            ["https://example.com/.well-known/skills/"],
        )

    def test_a_config_without_a_skills_section_gains_only_the_packaged_root(
        self,
    ) -> None:
        report = run_adapter({"adapterPath": str(ADAPTER_PATH), "config": {}})

        self.assertTrue(report["ok"], report)
        self.assertEqual(
            report["config"]["skills"],
            {"paths": [f"{package_root()}/skills"], "urls": []},
        )

    def test_repeated_initialization_still_adds_the_skill_path_once(self) -> None:
        config = {}
        report = None
        for _ in range(3):
            report = run_adapter({"adapterPath": str(ADAPTER_PATH), "config": config})
            self.assertTrue(report["ok"], report)

        report = run_adapter({"adapterPath": str(ADAPTER_PATH), "config": config})
        assert isinstance(report, dict)
        self.assertEqual(
            report["config"]["skills"]["paths"],
            [f"{package_root()}/skills"],
        )

    def test_the_adapter_takes_ownership_of_mcp_unica_and_preserves_neighbours(
        self,
    ) -> None:
        neighbour = {
            "type": "local",
            "command": ["npx", "-y", "@example/server"],
            "enabled": True,
        }
        config = {
            "mcp": {
                "other-server": neighbour,
                "unica": {"type": "remote", "url": "https://stale.example/"},
            }
        }

        report = run_adapter(
            {
                "adapterPath": str(ADAPTER_PATH),
                "config": config,
                "platform": "linux",
                "arch": "x64",
            }
        )

        self.assertTrue(report["ok"], report)
        self.assertEqual(report["config"]["mcp"]["other-server"], neighbour)
        unica = report["config"]["mcp"]["unica"]
        self.assertEqual(unica["type"], "local")
        self.assertEqual(unica["enabled"], True)
        self.assertEqual(unica["timeout"], MCP_TIMEOUT_MS)
        self.assertEqual(
            unica["command"],
            [
                f"{package_root()}/bootstrap/bin/linux-x64/unica-bootstrap",
                "run",
                "--plugin-root",
                package_root(),
            ],
        )

    def test_a_config_without_mcp_gains_only_the_unica_server(self) -> None:
        report = run_adapter(
            {
                "adapterPath": str(ADAPTER_PATH),
                "config": {},
                "platform": "win32",
                "arch": "x64",
            }
        )

        self.assertTrue(report["ok"], report)
        unica = report["config"]["mcp"]["unica"]
        self.assertEqual(
            unica["command"][0],
            f"{package_root()}/bootstrap/bin/win-x64/unica-bootstrap.exe",
        )

    def test_existing_process_overrides_win_over_derived_locations(self) -> None:
        report = run_adapter(
            {
                "adapterPath": str(ADAPTER_PATH),
                "config": {},
                "platform": "linux",
                "arch": "x64",
                "env": {
                    "UNICA_RUNTIME_CACHE_DIR": "/managed/runtime",
                    "UNICA_PROVIDER_STATE_DIR": "/managed/state",
                },
            }
        )

        self.assertTrue(report["ok"], report)
        environment = report["config"]["mcp"]["unica"]["environment"]
        self.assertEqual(environment["UNICA_RUNTIME_CACHE_DIR"], "/managed/runtime")
        self.assertEqual(environment["UNICA_PROVIDER_STATE_DIR"], "/managed/state")

    def test_locations_are_derived_from_the_cache_home_when_unset(self) -> None:
        report = run_adapter(
            {
                "adapterPath": str(ADAPTER_PATH),
                "config": {},
                "platform": "linux",
                "arch": "x64",
                "env": {key: None for key in CACHE_ENV_KEYS}
                | {"XDG_CACHE_HOME": "/xdg-cache"},
            }
        )

        self.assertTrue(report["ok"], report)
        environment = report["config"]["mcp"]["unica"]["environment"]
        self.assertEqual(
            environment["UNICA_RUNTIME_CACHE_DIR"], "/xdg-cache/opencode/unica/runtime"
        )
        self.assertEqual(
            environment["UNICA_PROVIDER_STATE_DIR"],
            "/xdg-cache/opencode/unica/provider-state",
        )

    def test_windows_locations_derive_from_localappdata(self) -> None:
        report = run_adapter(
            {
                "adapterPath": str(ADAPTER_PATH),
                "config": {},
                "platform": "win32",
                "arch": "x64",
                "env": {key: None for key in CACHE_ENV_KEYS}
                | {"XDG_CACHE_HOME": None, "LOCALAPPDATA": "C:/Users/u/AppData/Local"},
            }
        )

        self.assertTrue(report["ok"], report)
        environment = report["config"]["mcp"]["unica"]["environment"]
        self.assertEqual(
            environment["UNICA_RUNTIME_CACHE_DIR"],
            "C:/Users/u/AppData/Local/opencode/unica/runtime",
        )
        self.assertEqual(
            environment["UNICA_PROVIDER_STATE_DIR"],
            "C:/Users/u/AppData/Local/opencode/unica/provider-state",
        )

    def test_unsupported_platforms_fail_during_initialization(self) -> None:
        combinations = (
            ("darwin", "arm64"),
            ("darwin", "x64"),
            ("linux", "arm64"),
            ("win32", "arm64"),
        )
        preexisting = {
            "skills": {"paths": ["~/team"], "urls": ["https://example.com/s/"]},
            "mcp": {
                "other-server": {
                    "type": "local",
                    "command": ["npx", "-y", "@example/server"],
                    "enabled": True,
                }
            },
        }
        for platform, arch in combinations:
            for label, config in (("empty", {}), ("preexisting", preexisting)):
                with self.subTest(platform=platform, arch=arch, config=label):
                    report = run_adapter(
                        {
                            "adapterPath": str(ADAPTER_PATH),
                            "config": config,
                            "platform": platform,
                            "arch": arch,
                        }
                    )

                    self.assertFalse(report["ok"], report)
                    self.assertIn("Windows x64", report["error"])
                    self.assertIn("Linux x64", report["error"])
                    self.assertIn(f"{platform}-{arch}", report["error"])
                    # Initialization refusal must not leave partial mutations:
                    # the configuration object is byte-for-byte what it was.
                    self.assertEqual(report["config"], config)


class OpenCodeAdapterLocalDebugTests(unittest.TestCase):
    """Маркер local-debug переключает команду mcp.unica на прямой бинарник.

    Стенд — полная постановочная копия корня плагина: адаптер читает маркер
    относительно собственного расположения, поэтому проверяется именно
    упакованная форма, а не исходное дерево, где маркера нет никогда.
    """

    MARKER_NAME = "local-debug.json"

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)

    def staged_plugin(self, *, marker: dict | None, with_binary: bool = True) -> Path:
        staging = self.root / "staged"
        if staging.exists():
            shutil.rmtree(staging)
        shutil.copytree(REPO_ROOT / "plugins" / "unica", staging)
        # В исходном дереве нет npm-артефактов и маркера; тестовый стенд
        # повторяет упакованный корень без них.
        for name in ("package.json", "package-lock.json"):
            target = staging / name
            if target.exists():
                target.unlink()
        if with_binary:
            binary = staging / "bin" / "win-x64" / "unica.exe"
            binary.parent.mkdir(parents=True, exist_ok=True)
            binary.write_bytes(b"staged core binary")
        if marker is not None:
            (staging / "opencode" / self.MARKER_NAME).write_text(
                json.dumps(marker), encoding="utf-8"
            )
        return staging

    def adapter_report(self, staging: Path, instruction: dict) -> dict:
        instruction = {
            "adapterPath": str(staging / "opencode" / "index.js"),
            **instruction,
        }
        with tempfile.TemporaryDirectory() as tmp:
            instruction_path = Path(tmp) / "instruction.json"
            instruction_path.write_text(json.dumps(instruction), encoding="utf-8")
            completed = subprocess.run(
                ["node", str(DRIVER_PATH), str(instruction_path)],
                capture_output=True,
                text=True,
                check=False,
                cwd=REPO_ROOT,
            )
            if completed.returncode != 0:
                raise AssertionError(
                    f"driver failed ({completed.returncode}):\n{completed.stderr}"
                )
            return json.loads(completed.stdout)

    def test_local_debug_marker_switches_to_direct_binary_launch(self) -> None:
        staging = self.staged_plugin(
            marker={
                "mode": "local-debug",
                "target": "win-x64",
                "pluginVersion": "0.12.0",
            }
        )

        report = self.adapter_report(
            staging,
            {
                "config": {},
                "platform": "win32",
                "arch": "x64",
            },
        )

        self.assertTrue(report["ok"], report)
        unica = report["config"]["mcp"]["unica"]
        self.assertEqual(unica["type"], "local")
        self.assertEqual(unica["enabled"], True)
        self.assertEqual(unica["timeout"], MCP_TIMEOUT_MS)
        # Прямой запуск ядра без аргументов: MCP stdio не требует ни флагов,
        # ни cwd, ни bootstrap-обёртки.
        self.assertEqual(
            unica["command"],
            [f"{to_posix(str(staging))}/bin/win-x64/unica.exe"],
        )

    def test_a_marker_for_another_target_fails_during_initialization(self) -> None:
        staging = self.staged_plugin(
            marker={
                "mode": "local-debug",
                "target": "linux-x64",
                "pluginVersion": "0.12.0",
            }
        )
        config = {
            "skills": {"paths": ["~/team"], "urls": []},
            "mcp": {"other": {"type": "local", "command": ["x"], "enabled": True}},
        }

        report = self.adapter_report(
            staging,
            {"config": config, "platform": "win32", "arch": "x64"},
        )

        self.assertFalse(report["ok"], report)
        self.assertIn("linux-x64", report["error"])
        self.assertIn("win-x64", report["error"])
        # Отказ инициализации не мутирует конфигурацию.
        self.assertEqual(report["config"], config)

    def test_a_corrupt_marker_falls_back_to_the_release_bootstrap(self) -> None:
        staging = self.staged_plugin(marker=None)
        (staging / "opencode" / self.MARKER_NAME).write_text(
            "{not json", encoding="utf-8"
        )

        report = self.adapter_report(
            staging,
            {"config": {}, "platform": "win32", "arch": "x64"},
        )

        # Битый маркер не может доказать режим: адаптер ведёт себя как
        # release-пакет и запускает bootstrap.
        self.assertTrue(report["ok"], report)
        unica = report["config"]["mcp"]["unica"]
        self.assertEqual(
            unica["command"][1:], ["run", "--plugin-root", to_posix(str(staging))]
        )


def to_posix(value: str) -> str:
    return value.replace("\\", "/")


class OpenCodeAdapterReferenceAccessTests(unittest.TestCase):
    """Точечный доступ к упакованному references/ из конфигурационного хука.

    Скиллы читают общие материалы по ссылкам `../../references/...`; без
    явного permission OpenCode требует external_directory на каждое чтение
    из установленного npm-пакета. Адаптер обязан добавить ровно одно узкое
    правило для упакованного references/, сохраняя пользовательскую политику
    остальных путей и не расширяя доступ наружу пакета.
    """

    def references_rule(self) -> str:
        return f"{package_root()}/references/*"

    def run_hook(self, config: dict) -> dict:
        report = run_adapter({"adapterPath": str(ADAPTER_PATH), "config": config})
        self.assertTrue(report["ok"], report)
        return report["config"]

    def external_directory(self, config: dict) -> dict:
        self.assertIn("permission", config)
        self.assertIn("external_directory", config["permission"])
        return config["permission"]["external_directory"]

    def test_a_config_without_permissions_gains_only_the_references_rule(self) -> None:
        config = self.run_hook({})

        self.assertEqual(
            self.external_directory(config), {self.references_rule(): "allow"}
        )

    def test_existing_permission_rules_survive_and_gain_the_references_rule(
        self,
    ) -> None:
        config = self.run_hook(
            {
                "permission": {
                    "external_directory": {
                        "/work/projects/*": "allow",
                        "*": "ask",
                    }
                }
            }
        )

        self.assertEqual(
            self.external_directory(config),
            {
                "/work/projects/*": "allow",
                "*": "ask",
                self.references_rule(): "allow",
            },
        )

    def test_a_string_external_directory_policy_becomes_a_map(self) -> None:
        config = self.run_hook({"permission": {"external_directory": "ask"}})

        # Исходная политика остаётся правилом "*", узкое разрешение
        # добавляется после него; пользовательская политика остальных путей
        # не меняется.
        self.assertEqual(
            self.external_directory(config),
            {"*": "ask", self.references_rule(): "allow"},
        )

    def test_a_preexisting_rule_for_the_exact_glob_is_owned_not_duplicated(
        self,
    ) -> None:
        config = self.run_hook(
            {"permission": {"external_directory": {self.references_rule(): "deny"}}}
        )

        # Адаптер владеет точным правилом packaged references, как владеет
        # `mcp.unica`: существующее значение заменяется, записи не дублируются.
        self.assertEqual(
            self.external_directory(config), {self.references_rule(): "allow"}
        )

    def test_repeated_hook_runs_do_not_duplicate_the_references_rule(self) -> None:
        # Каждый запуск драйвера — отдельный Node-процесс: повторный запуск
        # хука моделируется обратной подачей мутированной конфигурации.
        config: dict = {}
        for _ in range(3):
            report = run_adapter({"adapterPath": str(ADAPTER_PATH), "config": config})
            self.assertTrue(report["ok"], report)
            config = report["config"]

        rules = self.external_directory(config)
        self.assertEqual(list(rules).count(self.references_rule()), 1)
        self.assertEqual(rules[self.references_rule()], "allow")

    def test_every_packaged_skill_reference_link_resolves_inside_the_package_root(
        self,
    ) -> None:
        """Ссылки `../../references/...` из SKILL.md ведут внутрь пакета.

        Правило доступа бессмысленно, если относительные ссылки скиллов
        разрешаются наружу упакованного корня: проверка фиксирует, что каждая
        ссылка попадает в существующий файл `references/` того же корня.
        """
        package = REPO_ROOT / "plugins" / "unica"
        references = (package / "references").resolve()
        pattern = re.compile(r"\.\./\.\./references/([^\s)`\"'\]]+)")
        resolved = 0
        for skill_md in sorted((package / "skills").glob("*/SKILL.md")):
            for match in pattern.finditer(skill_md.read_text(encoding="utf-8")):
                rel = match.group(1).rstrip(".,);:")
                target = (references / rel).resolve()
                with self.subTest(skill=skill_md.parent.name, link=rel):
                    self.assertTrue(
                        target.exists(), f"reference target does not exist: {rel}"
                    )
                    self.assertTrue(
                        target.is_relative_to(references),
                        f"reference target escapes the packaged references/: {rel}",
                    )
                resolved += 1
        # 27 скиллов несут общие ссылки; пустой обход сделал бы проверку
        # бессильной.
        self.assertGreaterEqual(resolved, 27)


if __name__ == "__main__":
    unittest.main()
