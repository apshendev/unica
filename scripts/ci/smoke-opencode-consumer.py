#!/usr/bin/env python3
"""Turn raw OpenCode consumer output into a release decision.

Two verifications, one script:

- ``verify-skills``: the JSON listing of ``opencode debug skill`` must
  contain every prompt-visible packaged skill of the plugin source.
- ``verify-mcp``: the text of ``opencode mcp list`` must show ``unica``
  connected and launched through the packaged bootstrap.

Both fail closed: malformed or incomplete consumer evidence fails the smoke.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def packaged_skill_names(plugin_root: Path) -> set[str]:
    skills = plugin_root / "skills"
    if not skills.is_dir():
        raise SystemExit(f"packaged skills directory not found: {skills}")
    return {
        entry.name
        for entry in sorted(skills.iterdir())
        if (entry / "SKILL.md").is_file()
    }


def listed_skill_names(payload) -> set[str]:
    if isinstance(payload, str):
        payload_object = json.loads(payload)
    else:
        payload_object = payload
    if not isinstance(payload_object, list):
        raise SystemExit("skill listing is not a JSON array")
    names: set[str] = set()
    for item in payload_object:
        if isinstance(item, str):
            names.add(item)
        elif isinstance(item, dict) and isinstance(item.get("name"), str):
            names.add(item["name"])
    return names


def verify_skills(json_path: Path, plugin_root: Path) -> None:
    try:
        payload = json.loads(json_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise SystemExit(f"consumer skill listing is unreadable: {error}") from error
    listed = listed_skill_names(payload)
    missing = sorted(packaged_skill_names(plugin_root) - listed)
    if missing:
        raise SystemExit(
            "consumer did not discover packaged skills: " + ", ".join(missing)
        )


def verify_mcp(output_path: Path) -> None:
    try:
        text = output_path.read_text(encoding="utf-8")
    except OSError as error:
        raise SystemExit(f"consumer mcp listing is unreadable: {error}") from error
    # `opencode mcp list` печатает каждый сервер блоком: строка состояния и
    # отступы с деталями команды. Владение bootstrap проверяется внутри блока
    # unica, а не по всему выводу.
    blocks: list[list[str]] = []
    for line in text.splitlines():
        if not line.strip():
            continue
        if line[:1] in (" ", "\t"):
            if blocks:
                blocks[-1].append(line)
        else:
            blocks.append([line])
    unica_blocks = [block for block in blocks if "unica" in block[0]]
    if not unica_blocks:
        raise SystemExit("mcp listing does not mention the unica server at all")
    connected = [block for block in unica_blocks if "connected" in block[0]]
    if not connected:
        raise SystemExit(
            "unica server is not connected in the consumer: "
            + " | ".join(block[0].strip() for block in unica_blocks)
        )
    if not any("unica-bootstrap" in "\n".join(block) for block in connected):
        raise SystemExit(
            "unica server is not launched through the packaged bootstrap: "
            "no unica-bootstrap command in the unica entry"
        )


def main(argv=None) -> None:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    skills_parser = subparsers.add_parser("verify-skills")
    skills_parser.add_argument("--json", type=Path, required=True)
    skills_parser.add_argument("--plugin-root", type=Path, required=True)

    mcp_parser = subparsers.add_parser("verify-mcp")
    mcp_parser.add_argument("--output", type=Path, required=True)

    args = parser.parse_args(argv)
    if args.command == "verify-skills":
        verify_skills(args.json, args.plugin_root)
    else:
        verify_mcp(args.output)


if __name__ == "__main__":
    main()
