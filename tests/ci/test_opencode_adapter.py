"""Contract tests for the packaged OpenCode adapter.

The seam is the adapter's public OpenCode plugin hook: a complete
configuration object goes in, the effective configuration comes out. The
adapter file is loaded by a real Node process, so the tests exercise exactly
the module OpenCode would load, with no private helpers involved.
"""

from __future__ import annotations

import json
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
        for platform, arch in combinations:
            with self.subTest(platform=platform, arch=arch):
                report = run_adapter(
                    {
                        "adapterPath": str(ADAPTER_PATH),
                        "config": {},
                        "platform": platform,
                        "arch": arch,
                    }
                )

                self.assertFalse(report["ok"], report)
                self.assertIn("Windows x64", report["error"])
                self.assertIn("Linux x64", report["error"])
                self.assertIn(f"{platform}-{arch}", report["error"])


if __name__ == "__main__":
    unittest.main()
