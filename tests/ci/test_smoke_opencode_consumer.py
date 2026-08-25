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


# OpenCode 1.18.22 печатает `opencode mcp list` clack-рамкой с ANSI-цветами.
# Форма ниже записана с реального CLI (mcp-raw.txt / mcp-nocolor.txt):
# рамка, подключённый `context7`, упавший `unica` и строки деталей взяты
# без изменения; работающего опубликованного `unica` в записи нет, поэтому
# его строку и команду упакованного bootstrap формирует тест.

COLORED_HEADER = "\x1b[0m\r\n\x1b[90m┌\x1b[39m  MCP Servers\n\x1b[90m│\x1b[39m\n"

PLAIN_HEADER = "\x1b[0m\r\n┌  MCP Servers\n│\n"

WINDOWS_BOOTSTRAP_COMMAND = (
    r"C:\consumer\node_modules\@apshendev\unica-opencode"
    r"\bootstrap\bin\win-x64\unica-bootstrap.exe run --plugin-root "
    r"C:\consumer\node_modules\@apshendev\unica-opencode"
)

LINUX_BOOTSTRAP_COMMAND = (
    "/consumer/node_modules/@apshendev/unica-opencode"
    "/bootstrap/bin/linux-x64/unica-bootstrap run --plugin-root "
    "/consumer/node_modules/@apshendev/unica-opencode"
)


def colored_server(name: str, status: str, glyph: str) -> str:
    return f"\x1b[34m●\x1b[39m  {glyph} {name} \x1b[90m{status}\n"


def colored_detail(text: str, *, emphasized: bool = True) -> str:
    inner = "\x1b[90m" if emphasized else ""
    return f"\x1b[90m│\x1b[39m      {inner}{text}\n"


def colored_separator() -> str:
    return "\x1b[90m│\x1b[39m\n"


def colored_footer(servers: int) -> str:
    return f"\x1b[90m└\x1b[39m  {servers} server(s)\n\n"


def plain_server(name: str, status: str, glyph: str) -> str:
    return f"●  {glyph} {name} \x1b[90m{status}\n"


def plain_detail(text: str, *, emphasized: bool = True) -> str:
    inner = "\x1b[90m" if emphasized else ""
    return f"│      {inner}{text}\n"


def plain_separator() -> str:
    return "│\n"


def plain_footer(servers: int) -> str:
    return f"└  {servers} server(s)\n\n"


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
        for platform, command in (
            ("windows", WINDOWS_BOOTSTRAP_COMMAND),
            ("linux", LINUX_BOOTSTRAP_COMMAND),
        ):
            with self.subTest(platform=platform):
                self.run_verify(
                    COLORED_HEADER
                    + colored_server("unica", "connected", "✓")
                    + colored_detail(command)
                    + colored_separator()
                    + colored_footer(1)
                )

    def test_a_unica_server_that_is_not_connected_fails(self) -> None:
        with self.assertRaises(SystemExit) as ctx:
            self.run_verify(
                COLORED_HEADER
                + colored_server("context7", "connected", "✓")
                + colored_detail("https://mcp.context7.com/mcp")
                + colored_separator()
                + colored_server("unica", "failed", "✗")
                + colored_detail(
                    "MCP error -32000: Connection closed", emphasized=False
                )
                + colored_detail("cmd /c echo hello")
                + colored_separator()
                + colored_footer(2)
            )

        self.assertIn("not connected", str(ctx.exception))

    def test_a_unica_line_without_the_packaged_bootstrap_fails(self) -> None:
        with self.assertRaises(SystemExit) as ctx:
            self.run_verify(
                COLORED_HEADER
                + colored_server("unica", "connected", "✓")
                + colored_detail("npx something-else")
                + colored_separator()
                + colored_footer(1)
            )

        self.assertIn("bootstrap", str(ctx.exception))

    def test_the_bootstrap_command_must_belong_to_the_unica_entry(self) -> None:
        # Глобальный поиск по всему выводу пропустил бы подмену: bootstrap
        # назван в блоке другого сервера, а unica подключена без него.
        with self.assertRaises(SystemExit) as ctx:
            self.run_verify(
                COLORED_HEADER
                + colored_server("unica", "connected", "✓")
                + colored_detail("https://unica.example/mcp")
                + colored_separator()
                + colored_server("replica", "connected", "✓")
                + colored_detail("unica-bootstrap run --plugin-root /other/package")
                + colored_separator()
                + colored_footer(2)
            )

        self.assertIn("bootstrap", str(ctx.exception))

    def test_a_detail_after_a_separator_does_not_count_for_the_previous_server(
        self,
    ) -> None:
        # Пустая `│` закрывает блок: деталь после разделителя не принадлежит
        # предыдущему серверу, и его запись остаётся без bootstrap.
        with self.assertRaises(SystemExit) as ctx:
            self.run_verify(
                COLORED_HEADER
                + colored_server("unica", "connected", "✓")
                + colored_separator()
                + colored_detail(WINDOWS_BOOTSTRAP_COMMAND)
                + colored_footer(1)
            )

        self.assertIn("bootstrap", str(ctx.exception))

    def test_a_listing_without_unica_fails(self) -> None:
        with self.assertRaises(SystemExit) as ctx:
            self.run_verify(
                COLORED_HEADER
                + colored_server("context7", "connected", "✓")
                + colored_detail("https://mcp.context7.com/mcp")
                + colored_separator()
                + colored_footer(1)
            )

        self.assertIn("does not mention the unica server", str(ctx.exception))

    def test_no_color_output_is_still_parsed(self) -> None:
        # NO_COLOR=1 снимает цвет с глифов рамки, но ANSI на статусе и
        # деталях остаётся — форма из записи mcp-nocolor.txt.
        self.run_verify(
            PLAIN_HEADER
            + plain_server("unica", "connected", "✓")
            + plain_detail(WINDOWS_BOOTSTRAP_COMMAND)
            + plain_separator()
            + plain_footer(1)
        )

    def test_exact_server_name_match(self) -> None:
        # `unica-backup` — другой сервер с полноценным connected-блоком и
        # своей bootstrap-деталью: точного сервера `unica` в листинге нет,
        # и проверка обязана отказаться от такого вывода.
        with self.assertRaises(SystemExit) as ctx:
            self.run_verify(
                COLORED_HEADER
                + colored_server("unica-backup", "connected", "✓")
                + colored_detail(WINDOWS_BOOTSTRAP_COMMAND)
                + colored_separator()
                + colored_footer(1)
            )

        self.assertIn("does not mention the unica server", str(ctx.exception))

    def test_a_listing_without_a_server_frame_fails_closed(self) -> None:
        for listing, text in (("empty", ""), ("garbage", "not an opencode listing\n")):
            with self.subTest(listing=listing):
                with self.assertRaises(SystemExit):
                    self.run_verify(text)


if __name__ == "__main__":
    unittest.main()
