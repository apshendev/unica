"""Unit tests for the OpenCode consumer smoke verifier.

The verifier turns raw OpenCode CLI output into a release decision: every
packaged skill must be discoverable, and the `unica` MCP server must report
connected through the packaged bootstrap. The OpenCode CLI itself is never
run here; tests feed recorded output shapes.
"""

from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "ci" / "smoke-opencode-consumer.py"


def load_verifier_module():
    spec = importlib.util.spec_from_file_location(
        "smoke_opencode_consumer", SCRIPT_PATH
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to load {SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class VerifySkillsTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)

        skills = self.root / "skills"
        for name in ("code-search", "format-profile", "release"):
            (skills / name).mkdir(parents=True)
            (skills / name / "SKILL.md").write_text(
                f"---\nname: {name}\n---\n", encoding="utf-8"
            )

    def write_skills_json(self, payload) -> Path:
        path = self.root / "skills.json"
        if isinstance(payload, str):
            path.write_text(payload, encoding="utf-8")
        else:
            path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def run_verify(self, payload, plugin_root: Path | None = None) -> None:
        module = load_verifier_module()
        json_path = self.write_skills_json(payload)
        module.main(
            [
                "verify-skills",
                "--json",
                str(json_path),
                "--plugin-root",
                str(plugin_root or self.root),
            ]
        )

    def test_every_packaged_skill_must_be_listed(self) -> None:
        self.run_verify(
            [
                {"name": "code-search"},
                {"name": "format-profile"},
                {"name": "release"},
                {"name": "team-extra"},
            ]
        )

    def test_a_missing_packaged_skill_fails_the_smoke(self) -> None:
        module = load_verifier_module()

        with self.assertRaises(SystemExit) as ctx:
            self.run_verify([{"name": "code-search"}, {"name": "release"}])

        self.assertIn("format-profile", str(ctx.exception))

    def test_malformed_skill_listing_fails_closed(self) -> None:
        module = load_verifier_module()

        with self.assertRaises(SystemExit):
            self.run_verify("not json at all")

    def test_string_entries_are_accepted_as_names(self) -> None:
        self.run_verify(["code-search", "format-profile", "release"])


class VerifyMcpTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)

    def run_verify(self, text: str) -> None:
        module = load_verifier_module()
        output = self.root / "mcp.txt"
        output.write_text(text, encoding="utf-8")
        module.main(["verify-mcp", "--output", str(output)])

    def test_a_connected_unica_server_through_the_packaged_bootstrap_passes(
        self,
    ) -> None:
        self.run_verify(
            "MCP Servers\n"
            "✓ unica connected\n"
            "    unica-bootstrap run --plugin-root /consumer/pkg\n"
            "1 server(s)\n"
        )

    def test_a_unica_server_that_is_not_connected_fails(self) -> None:
        with self.assertRaises(SystemExit) as ctx:
            self.run_verify(
                "MCP Servers\n"
                "✗ unica failed\n"
                "    unica-bootstrap run --plugin-root /consumer/pkg\n"
            )

        self.assertIn("unica", str(ctx.exception))

    def test_a_unica_line_without_the_packaged_bootstrap_fails(self) -> None:
        with self.assertRaises(SystemExit) as ctx:
            self.run_verify("✓ unica connected\n    npx something-else\n")

        self.assertIn("bootstrap", str(ctx.exception))

    def test_the_bootstrap_command_must_belong_to_the_unica_entry(self) -> None:
        # Глобальный поиск по всему выводу пропустил бы подмену: bootstrap
        # назван в блоке другого сервера, а unica подключена без него.
        with self.assertRaises(SystemExit) as ctx:
            self.run_verify(
                "MCP Servers\n"
                "✓ unica connected\n"
                "✓ replica connected\n"
                "    unica-bootstrap run --plugin-root /other/package\n"
            )

        self.assertIn("bootstrap", str(ctx.exception))

    def test_a_listing_without_unica_fails(self) -> None:
        with self.assertRaises(SystemExit) as ctx:
            self.run_verify("✓ other-server connected\n    npx -y @example/server\n")

        self.assertIn("unica", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
