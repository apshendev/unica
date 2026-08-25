#!/usr/bin/env python3
"""Turn raw OpenCode consumer output into a release decision.

Two verifications, one script:

- ``verify-skills``: the JSON listing of ``opencode debug skill`` must
  contain every prompt-visible packaged skill of the installed plugin root,
  each with a location under ``<plugin-root>/skills``.
- ``verify-mcp``: the text of ``opencode mcp list`` must show ``unica``
  connected and launched through the packaged bootstrap of the same root.

Path normalization follows ``--target``, never the host OS: ``win-x64``
normalizes with ``ntpath`` semantics (both separators, case-insensitive),
``linux-x64`` with ``posixpath``. Both verifications fail closed: malformed
or incomplete consumer evidence fails the smoke.
"""

from __future__ import annotations

import argparse
import json
import ntpath
import posixpath
import re
import sys
from pathlib import Path, PurePosixPath, PureWindowsPath

TARGETS = ("win-x64", "linux-x64")

_ANSI = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]")
_ANSI_OSC = re.compile(r"\x1b\].*?(?:\x07|\x1b\\)")
_SERVER_LINE = re.compile(
    r"^●\s+[○✓✗]\s+(?P<name>\S+)\s+(?P<status>connected|disabled|failed)$"
)


def _components(path_text: str, target: str) -> tuple[str, ...]:
    """Normalized path components of `path_text` in the target's syntax."""
    module = ntpath if target == "win-x64" else posixpath
    normalized = module.normpath(path_text)
    pure = (
        PureWindowsPath(normalized)
        if target == "win-x64"
        else PurePosixPath(normalized)
    )
    parts = [part for part in pure.parts if part not in ("/", "\\")]
    if target == "win-x64":
        parts = [part.casefold() for part in parts]
    return tuple(parts)


def packaged_skill_names(plugin_root: Path) -> set[str]:
    skills = plugin_root / "skills"
    if not skills.is_dir():
        raise SystemExit(f"packaged skills directory not found: {skills}")
    return {
        entry.name
        for entry in sorted(skills.iterdir())
        if (entry / "SKILL.md").is_file()
    }


def listed_skill_entries(payload) -> list[tuple[str, str]]:
    """(name, location) pairs; every entry must be an object with both."""
    if isinstance(payload, str):
        payload_object = json.loads(payload)
    else:
        payload_object = payload
    if not isinstance(payload_object, list):
        raise SystemExit("skill listing is not a JSON array")
    entries: list[tuple[str, str]] = []
    for item in payload_object:
        if not isinstance(item, dict):
            raise SystemExit(
                f"skill listing entry is not an object with a location: {item!r}"
            )
        name = item.get("name")
        location = item.get("location")
        if not isinstance(name, str) or not name:
            raise SystemExit(f"skill listing entry has no name: {item!r}")
        if not isinstance(location, str) or not location:
            raise SystemExit(f"skill {name} has no location")
        entries.append((name, location))
    return entries


def verify_skills(json_path: Path, plugin_root: Path, target: str) -> None:
    try:
        payload = json.loads(json_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise SystemExit(f"consumer skill listing is unreadable: {error}") from error
    entries = listed_skill_entries(payload)
    listed = {name for name, _ in entries}
    missing = sorted(packaged_skill_names(plugin_root) - listed)
    if missing:
        raise SystemExit(
            "consumer did not discover packaged skills: " + ", ".join(missing)
        )

    # Аргумент — реальный каталог: его текст обязан прийти в синтаксисе
    # target, иначе posix-нормализация не увидит в нём разделителей.
    root_text = plugin_root.as_posix() if target == "linux-x64" else str(plugin_root)
    root = _components(root_text, target)
    expected_prefix = root + ("skills",)
    for name, location in entries:
        components = _components(location, target)
        if (
            len(components) <= len(expected_prefix)
            or components[: len(expected_prefix)] != expected_prefix
        ):
            raise SystemExit(
                f"skill {name} location is outside the installed plugin root: "
                f"{location}"
            )


def _strip_ansi(line: str) -> str:
    line = _ANSI_OSC.sub("", line)
    line = _ANSI.sub("", line)
    return line.replace("\r", "")


def _bootstrap_is_packaged(details: list[str], plugin_root: str, target: str) -> bool:
    """The first detail is the launch command of the packaged bootstrap."""
    if not details:
        return False
    tokens = details[0].split()
    if len(tokens) != 4 or tokens[1] != "run" or tokens[2] != "--plugin-root":
        return False
    root = _components(plugin_root, target)
    binary = "unica-bootstrap.exe" if target == "win-x64" else "unica-bootstrap"
    expected_command = root + ("bootstrap", "bin", target, binary)
    if _components(tokens[0], target) != expected_command:
        return False
    return _components(tokens[3], target) == root


def verify_mcp(output_path: Path, plugin_root: str, target: str) -> None:
    try:
        text = output_path.read_text(encoding="utf-8")
    except OSError as error:
        raise SystemExit(f"consumer mcp listing is unreadable: {error}") from error
    # `opencode mcp list` печатает clack-рамку: `●` открывает запись сервера,
    # `│` продолжает её деталями, пустая `│` и границы `┌`/`└` закрывают
    # запись. Владение bootstrap проверяется внутри записи unica, а не по
    # всему выводу.
    records: list[tuple[str, str, list[str]]] = []
    current: tuple[str, str, list[str]] | None = None
    for raw_line in text.splitlines():
        line = _strip_ansi(raw_line).strip()
        if not line:
            continue
        marker = line[0]
        if marker in "┌└":
            current = None
            continue
        if marker == "●":
            match = _SERVER_LINE.match(line)
            if match is None:
                raise SystemExit(f"unparsable mcp server line: {line}")
            current = (match.group("name"), match.group("status"), [])
            records.append(current)
        elif marker == "│":
            detail = line[1:].strip()
            if not detail:
                current = None
                continue
            if current is None:
                raise SystemExit(f"mcp detail line outside any server block: {line}")
            current[2].append(detail)
        else:
            raise SystemExit(f"unexpected line in mcp listing: {line}")
    if not records:
        raise SystemExit("mcp listing carries no server records at all")
    unica_records = [record for record in records if record[0] == "unica"]
    if not unica_records:
        raise SystemExit("mcp listing does not mention the unica server at all")
    connected = [record for record in unica_records if record[1] == "connected"]
    if not connected:
        raise SystemExit(
            "unica server is not connected in the consumer: "
            + " | ".join(f"{name} {status}" for name, status, _ in unica_records)
        )
    if not any(
        _bootstrap_is_packaged(details, plugin_root, target)
        for _, _, details in connected
    ):
        raise SystemExit(
            "unica server is not launched through the packaged bootstrap of "
            f"the installed plugin root (expected "
            f"<plugin-root>/bootstrap/bin/{target}/unica-bootstrap run "
            "--plugin-root <plugin-root>)"
        )


def main(argv=None) -> None:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    skills_parser = subparsers.add_parser("verify-skills")
    skills_parser.add_argument("--json", type=Path, required=True)
    skills_parser.add_argument("--plugin-root", type=Path, required=True)
    skills_parser.add_argument("--target", choices=TARGETS, required=True)

    mcp_parser = subparsers.add_parser("verify-mcp")
    mcp_parser.add_argument("--output", type=Path, required=True)
    mcp_parser.add_argument("--plugin-root", required=True)
    mcp_parser.add_argument("--target", choices=TARGETS, required=True)

    args = parser.parse_args(argv)
    if args.command == "verify-skills":
        verify_skills(args.json, args.plugin_root, args.target)
    else:
        verify_mcp(args.output, args.plugin_root, args.target)


if __name__ == "__main__":
    main()
