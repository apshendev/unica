#!/usr/bin/env python3
"""Форк-оверлей: применяет декларативные правки к упаковочной копии плагина.

Git-дерево форка не расходится с upstream: все кастомизации живут в
``fork/overlay.json`` и применяются к staged-копии (выходу упаковщика)
перед ``npm pack``. Правило, чей anchor перестал матчиться после обновления
upstream, падает громко — exit 1 со списком несовпавших правил, а не тихий
пропуск правки.

Действия:
  remove_lines — удалить строки, подпадающие под regex (построчно, re.I нет);
  remove_block — удалить span'ы по всему тексту (компиляция с re.M | re.S);
  replace      — заменить span'ы по regex (re.M | re.S); replacement понимает
                 ``\\n`` и группы ``\\1`` в семантике re.sub;
  delete_path  — удалить файл или каталог из корня упаковки.

CLI:
  apply_overlay.py --root <staged-root> [--manifest <overlay.json>] [--dry-run]
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import re
import shutil
import sys
from pathlib import Path

MANIFEST_VERSION = 1
MULTILINE_ACTIONS = ("remove_block", "replace")


def load_manifest(path: Path) -> dict:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest.get("version") != MANIFEST_VERSION:
        raise SystemExit(
            f"unsupported overlay manifest version: {manifest.get('version')!r}, "
            f"expected {MANIFEST_VERSION}"
        )
    return manifest


def iter_files(root: Path, patterns: list) -> list:
    matched = {}
    for path in root.rglob("*"):
        if not path.is_file() or path.is_symlink():
            continue
        rel = path.relative_to(root).as_posix()
        for pattern in patterns:
            if fnmatch.fnmatchcase(rel, pattern):
                matched[rel] = path
                break
    return [matched[rel] for rel in sorted(matched)]


def read_text(path: Path):
    raw = path.read_bytes().decode("utf-8")
    crlf = "\r\n" in raw
    return raw.replace("\r\n", "\n"), crlf


def write_text(path: Path, text: str, crlf: bool) -> None:
    if crlf:
        text = text.replace("\n", "\r\n")
    path.write_bytes(text.encode("utf-8"))


def apply_rule(rule: dict, root: Path, dry_run: bool) -> dict:
    action = rule["action"]

    if action == "delete_path":
        target = root / rule["path"]
        exists = target.exists()
        if exists and not dry_run:
            if target.is_dir():
                shutil.rmtree(target)
            else:
                target.unlink()
        return {
            "id": rule["id"],
            "ok": exists,
            "files": 1 if exists else 0,
            "matches": 1 if exists else 0,
            "note": rule["path"],
        }

    patterns = rule.get("files", [])
    regex = re.compile(rule["match"], re.M | re.S if action in MULTILINE_ACTIONS else 0)
    replacement = rule.get("replacement", "")
    total = 0
    files_touched = 0

    for path in iter_files(root, patterns):
        text, crlf = read_text(path)
        if action in MULTILINE_ACTIONS:
            new_text, hits = regex.subn(replacement, text)
        else:
            lines = text.split("\n")
            kept = [line for line in lines if not regex.search(line)]
            hits = len(lines) - len(kept)
            new_text = "\n".join(kept)
        if hits:
            total += hits
            if new_text != text:
                files_touched += 1
                if not dry_run:
                    write_text(path, new_text, crlf)

    return {
        "id": rule["id"],
        "ok": total >= rule.get("minMatches", 1),
        "files": files_touched,
        "matches": total,
    }


def apply_overlay(root: Path, manifest_path: Path, dry_run: bool = False):
    """Применить манифест к корню упаковки. Возвращает (отчёт, успех)."""
    manifest = load_manifest(manifest_path)
    report = [apply_rule(rule, root, dry_run) for rule in manifest.get("rules", [])]
    ok = all(entry["ok"] for entry in report)
    return report, ok


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Форк-оверлей: применяет декларативные правки к упаковочной копии плагина."
    )
    parser.add_argument(
        "--root",
        type=Path,
        required=True,
        help="корень упаковки (staged-копия плагина)",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path(__file__).resolve().parents[2] / "fork" / "overlay.json",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="посчитать совпадения и отчёт без записи"
    )
    args = parser.parse_args()

    root = args.root.resolve()
    if not root.is_dir():
        raise SystemExit(f"root not found: {root}")
    if not args.manifest.is_file():
        raise SystemExit(f"manifest not found: {args.manifest}")

    report, ok = apply_overlay(root, args.manifest, args.dry_run)

    mode = "DRY-RUN" if args.dry_run else "APPLIED"
    for entry in report:
        status = "ok  " if entry["ok"] else "FAIL"
        note = f"  [{entry['note']}]" if entry.get("note") else ""
        print(
            f"{status} {entry['id']}: files={entry['files']} matches={entry['matches']}{note}"
        )

    if not ok:
        failed = [entry["id"] for entry in report if not entry["ok"]]
        print(f"\noverlay {mode}: FAILED rules: {', '.join(failed)}", file=sys.stderr)
        print(
            "anchor drift: upstream переписал текст — обнови regex в манифесте",
            file=sys.stderr,
        )
        sys.exit(1)
    print(f"\noverlay {mode}: all rules satisfied")


if __name__ == "__main__":
    main()
