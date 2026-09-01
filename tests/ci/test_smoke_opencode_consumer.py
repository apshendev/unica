"""Unit tests for the OpenCode consumer smoke verifier.

The verifier turns raw OpenCode CLI output into a release decision: every
packaged skill must be discoverable under the installed plugin root, and the
`unica` MCP server must report connected through the packaged bootstrap of
that same root. The OpenCode CLI itself is never run here; tests feed recorded
output shapes.

Path normalization follows `--target`, never the host OS: a `win-x64` suite
checks Windows-style paths and a `linux-x64` suite checks POSIX-style paths in
one process, so the suite result is identical on any runner.
"""

from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "ci" / "smoke-opencode-consumer.py"

WINDOWS_PLUGIN_ROOT = r"C:\consumer\node_modules\@apshendev\unica-opencode"
LINUX_PLUGIN_ROOT = "/consumer/node_modules/@apshendev/unica-opencode"


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

    def location(self, name: str, *, root: str | None = None) -> str:
        base = root if root is not None else str(self.root)
        return f"{base}/skills/{name}"

    def write_skills_json(self, payload) -> Path:
        path = self.root / "skills.json"
        if isinstance(payload, str):
            path.write_text(payload, encoding="utf-8")
        else:
            path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def run_verify(
        self,
        payload,
        plugin_root: Path | str | None = None,
        target: str = "win-x64",
    ) -> None:
        module = load_verifier_module()
        json_path = self.write_skills_json(payload)
        module.main(
            [
                "verify-skills",
                "--json",
                str(json_path),
                "--plugin-root",
                str(plugin_root if plugin_root is not None else self.root),
                "--target",
                target,
            ]
        )

    def expected_listing(self, *, root: str | None = None):
        return [
            {
                "name": "code-search",
                "location": self.location("code-search", root=root),
            },
            {
                "name": "format-profile",
                "location": self.location("format-profile", root=root),
            },
            {"name": "release", "location": self.location("release", root=root)},
        ]

    def test_every_packaged_skill_must_be_listed(self) -> None:
        payload = self.expected_listing()
        payload.append({"name": "team-extra", "location": self.location("team-extra")})
        self.run_verify(payload)

    def test_a_missing_packaged_skill_fails_the_smoke(self) -> None:
        payload = self.expected_listing()
        del payload[1]

        with self.assertRaises(SystemExit) as ctx:
            self.run_verify(payload)

        self.assertIn("format-profile", str(ctx.exception))

    def test_malformed_skill_listing_fails_closed(self) -> None:
        with self.assertRaises(SystemExit):
            self.run_verify("not json at all")

    def test_string_entries_are_refused(self) -> None:
        with self.assertRaises(SystemExit) as ctx:
            self.run_verify(["code-search", "format-profile", "release"])

        self.assertIn("location", str(ctx.exception))

    def test_a_skill_listing_without_locations_is_refused(self) -> None:
        with self.assertRaises(SystemExit) as ctx:
            self.run_verify(
                [
                    {"name": "code-search"},
                    {"name": "format-profile"},
                    {"name": "release"},
                ]
            )

        self.assertIn("location", str(ctx.exception))

    def test_a_skill_location_outside_the_plugin_root_is_refused(self) -> None:
        payload = self.expected_listing()
        payload[0] = {
            "name": "code-search",
            "location": r"C:\other\package\skills\code-search",
        }

        with self.assertRaises(SystemExit) as ctx:
            self.run_verify(payload)

        self.assertIn("plugin root", str(ctx.exception))

    def test_foreign_entries_do_not_fail_the_smoke(self) -> None:
        # Посторонние записи — встроенные скиллы хоста и пользовательские
        # каталоги — проверка не касается: их расположение вне
        # установленного корня не отказ (план 2026-09-01, п. 2).
        payload = self.expected_listing()
        payload.append(
            {
                "name": "team-extra",
                "location": r"C:\other\package\skills\team-extra",
            }
        )

        self.run_verify(payload)

    def test_locations_in_posix_syntax_pass_for_the_linux_target(self) -> None:
        posix_root = self.root.as_posix()
        payload = [
            {"name": name, "location": f"{posix_root}/skills/{name}"}
            for name in ("code-search", "format-profile", "release")
        ]

        self.run_verify(payload, plugin_root=posix_root, target="linux-x64")


class VerifySkillsConsumerListingTests(unittest.TestCase):
    """Реальный листинг потребителя: 73 упакованных скилла плюс встроенные.

    `opencode debug skill` показывает не только скиллы установленного плагина,
    но и встроенные скиллы хоста (`customize-opencode` с location
    `<built-in>`) и пользовательские каталоги. Проверка обязана требовать
    только упакованные имена и их расположение, игнорируя посторонние записи.
    """

    BUILT_IN = {"name": "customize-opencode", "location": "<built-in>"}

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        # Ровно 73 упакованных скилла — численность реального плагина.
        self.packaged = [f"unica-{index:02d}" for index in range(1, 74)]
        skills = self.root / "skills"
        for name in self.packaged:
            (skills / name).mkdir(parents=True)
            (skills / name / "SKILL.md").write_text(
                f"---\nname: {name}\n---\n", encoding="utf-8"
            )

    def entry(self, name: str, *, root: str | None = None) -> dict:
        base = root if root is not None else str(self.root)
        return {"name": name, "location": f"{base}\\skills\\{name}"}

    def consumer_listing(self) -> list[dict]:
        return [self.entry(name) for name in self.packaged] + [dict(self.BUILT_IN)]

    def run_verify(self, payload, *, plugin_root: Path | None = None) -> None:
        module = load_verifier_module()
        json_path = self.root / "skills.json"
        json_path.write_text(json.dumps(payload), encoding="utf-8")
        module.main(
            [
                "verify-skills",
                "--json",
                str(json_path),
                "--plugin-root",
                str(plugin_root if plugin_root is not None else self.root),
                "--target",
                "win-x64",
            ]
        )

    def test_the_builtin_customize_opencode_skill_does_not_fail_the_smoke(self) -> None:
        self.run_verify(self.consumer_listing())

    def test_a_foreign_same_name_skill_displaces_a_packaged_one_and_fails(
        self,
    ) -> None:
        payload = self.consumer_listing()
        payload[0] = self.entry(self.packaged[0], root=r"C:\other\package")

        with self.assertRaises(SystemExit) as ctx:
            self.run_verify(payload)

        self.assertIn(self.packaged[0], str(ctx.exception))
        self.assertIn("plugin root", str(ctx.exception))

    def test_an_empty_packaged_skills_directory_fails_closed(self) -> None:
        # Пустой (но существующий) каталог skills не должен давать
        # вакуумный успех: без упакованных скиллов проверять нечего.
        empty_root = self.root / "empty-plugin"
        (empty_root / "skills").mkdir(parents=True)

        with self.assertRaises(SystemExit) as ctx:
            self.run_verify([], plugin_root=empty_root)

        self.assertIn("no packaged skills", str(ctx.exception))


class VerifyAgentToolsTests(unittest.TestCase):
    """Проверка agent-visible инструментов build-агента потребителя.

    Ledger задаёт канонические имена `unica.*`; OpenCode показывает их как
    `<server>_<имя с заменой недопустимых символов>`. Проверка требует
    каждое имя в `agent.tools` со значением `true`: подключённый MCP с
    пустым или частичным `tools/list` исправным не считается.
    """

    LEDGER = {
        "unica.project.map": {"scope": "in"},
        "unica.cf.info": {"scope": "in"},
        "unica.mxl.decompile": {"scope": "retiring"},
    }

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.ledger_path = self.root / "tool-surface-review.json"
        self.ledger_path.write_text(json.dumps(self.LEDGER), encoding="utf-8")

    def agent_path(self, tools: dict) -> Path:
        path = self.root / "agent.json"
        payload = {"model": "test/model", "tools": tools}
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def complete_tools(self) -> dict:
        return {
            "read": True,
            "skill": True,
            "unica_unica_project_map": True,
            "unica_unica_cf_info": True,
            "unica_unica_mxl_decompile": True,
        }

    def run_verify(self, tools: dict, *, ledger: Path | None = None) -> None:
        module = load_verifier_module()
        module.main(
            [
                "verify-agent-tools",
                "--agent-json",
                str(self.agent_path(tools)),
                "--ledger",
                str(ledger if ledger is not None else self.ledger_path),
                "--server",
                "unica",
            ]
        )

    def test_the_complete_enabled_tool_set_passes(self) -> None:
        self.run_verify(self.complete_tools())

    def test_a_missing_tool_fails_the_smoke(self) -> None:
        tools = self.complete_tools()
        del tools["unica_unica_project_map"]

        with self.assertRaises(SystemExit) as ctx:
            self.run_verify(tools)

        self.assertIn("unica_unica_project_map", str(ctx.exception))
        self.assertIn("unica.project.map", str(ctx.exception))

    def test_a_disabled_tool_fails_the_smoke(self) -> None:
        tools = self.complete_tools()
        tools["unica_unica_cf_info"] = False

        with self.assertRaises(SystemExit) as ctx:
            self.run_verify(tools)

        self.assertIn("not enabled", str(ctx.exception))
        self.assertIn("unica_unica_cf_info", str(ctx.exception))

    def test_an_empty_tools_map_fails_closed(self) -> None:
        with self.assertRaises(SystemExit):
            self.run_verify({})

    def test_a_foreign_name_variant_does_not_satisfy_the_canonical_tool(
        self,
    ) -> None:
        tools = self.complete_tools()
        del tools["unica_unica_project_map"]
        # Другая транслитерация того же инструмента не подменяет ожидаемое
        # имя: точечная замена символа должна была стать `_`.
        tools["unica_unica-project-map"] = True

        with self.assertRaises(SystemExit) as ctx:
            self.run_verify(tools)

        self.assertIn("missing the tool unica_unica_project_map", str(ctx.exception))


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
    return f"\x1b[90m│\x1b[39m\n"


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

    def run_verify(
        self,
        text: str,
        *,
        plugin_root: str = WINDOWS_PLUGIN_ROOT,
        target: str = "win-x64",
    ) -> None:
        module = load_verifier_module()
        output = self.root / "mcp.txt"
        output.write_text(text, encoding="utf-8")
        module.main(
            [
                "verify-mcp",
                "--output",
                str(output),
                "--plugin-root",
                plugin_root,
                "--target",
                target,
            ]
        )

    def unica_frame(self, command: str) -> str:
        return (
            colored_server("unica", "connected", "✓")
            + colored_detail(command)
            + colored_separator()
            + colored_footer(1)
        )

    def test_a_connected_unica_server_through_the_packaged_core_binary_passes(
        self,
    ) -> None:
        # Local-debug кандидат: маркер переключает mcp.unica на прямой запуск
        # упакованного ядра bin/<target>/unica(.exe) без bootstrap
        # (CTR.HOST.OPENCODE-LAUNCH-MODES).
        for target, plugin_root, binary in (
            ("win-x64", WINDOWS_PLUGIN_ROOT, "unica.exe"),
            ("linux-x64", LINUX_PLUGIN_ROOT, "unica"),
        ):
            with self.subTest(target=target):
                separator = "\\" if target == "win-x64" else "/"
                command = (
                    f"{plugin_root}{separator}bin{separator}{target}{separator}{binary}"
                )
                self.run_verify(
                    COLORED_HEADER + self.unica_frame(command),
                    plugin_root=plugin_root,
                    target=target,
                )

    def test_a_core_binary_outside_the_installed_package_root_is_refused(
        self,
    ) -> None:
        with self.assertRaises(SystemExit) as ctx:
            self.run_verify(COLORED_HEADER + self.unica_frame(r"D:\tools\unica.exe"))

        self.assertIn("packaged", str(ctx.exception))

    def test_a_cargo_run_core_command_is_refused(self) -> None:
        with self.assertRaises(SystemExit) as ctx:
            self.run_verify(
                COLORED_HEADER
                + self.unica_frame("cargo run --release -p unica-coder --bin unica")
            )

        self.assertIn("packaged", str(ctx.exception))

    def test_a_connected_unica_server_through_the_packaged_bootstrap_passes(
        self,
    ) -> None:
        for target, plugin_root, command in (
            ("win-x64", WINDOWS_PLUGIN_ROOT, WINDOWS_BOOTSTRAP_COMMAND),
            ("linux-x64", LINUX_PLUGIN_ROOT, LINUX_BOOTSTRAP_COMMAND),
        ):
            with self.subTest(target=target):
                self.run_verify(
                    COLORED_HEADER + self.unica_frame(command),
                    plugin_root=plugin_root,
                    target=target,
                )

    def test_a_bootstrap_outside_the_installed_package_root_is_refused(
        self,
    ) -> None:
        with self.assertRaises(SystemExit) as ctx:
            self.run_verify(
                COLORED_HEADER
                + self.unica_frame(
                    r"C:\tools\unica-bootstrap.exe run --plugin-root C:\tools"
                )
            )

        self.assertIn("bootstrap", str(ctx.exception))

    def test_a_linux_bootstrap_outside_the_installed_package_root_is_refused(
        self,
    ) -> None:
        with self.assertRaises(SystemExit) as ctx:
            self.run_verify(
                COLORED_HEADER
                + self.unica_frame("/tools/unica-bootstrap run --plugin-root /tools"),
                plugin_root=LINUX_PLUGIN_ROOT,
                target="linux-x64",
            )

        self.assertIn("bootstrap", str(ctx.exception))

    def test_the_packaged_bootstrap_under_the_plugin_root_is_accepted(self) -> None:
        for target, plugin_root, binary in (
            ("win-x64", WINDOWS_PLUGIN_ROOT, "unica-bootstrap.exe"),
            ("linux-x64", LINUX_PLUGIN_ROOT, "unica-bootstrap"),
        ):
            with self.subTest(target=target):
                separator = "\\" if target == "win-x64" else "/"
                command = (
                    f"{plugin_root}{separator}bootstrap{separator}bin"
                    f"{separator}{target}{separator}{binary}"
                    f" run --plugin-root {plugin_root}"
                )
                self.run_verify(
                    COLORED_HEADER + self.unica_frame(command),
                    plugin_root=plugin_root,
                    target=target,
                )

    def test_a_foreign_target_layout_is_refused(self) -> None:
        command = (
            r"C:\consumer\node_modules\@apshendev\unica-opencode"
            r"\bootstrap\bin\linux-x64\unica-bootstrap.exe run --plugin-root "
            r"C:\consumer\node_modules\@apshendev\unica-opencode"
        )

        with self.assertRaises(SystemExit) as ctx:
            self.run_verify(COLORED_HEADER + self.unica_frame(command))

        self.assertIn("bootstrap", str(ctx.exception))

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
            self.run_verify(COLORED_HEADER + self.unica_frame("npx something-else"))

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
                + colored_detail(
                    LINUX_BOOTSTRAP_COMMAND,
                )
                + colored_separator()
                + colored_footer(2),
                plugin_root=LINUX_PLUGIN_ROOT,
                target="linux-x64",
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
