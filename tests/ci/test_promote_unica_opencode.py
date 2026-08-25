"""Contract tests for the OpenCode npm promotion step.

Promotion is the only writer of the consumer-facing dist-tags. Its seams are
the process environment it gates on and the npm invocations it makes; tests
fake the process boundaries (dist-tag reads, the single dist-tag write, the
registry download) and never talk to npm. The candidate is a real gzip tar
built by the fixture, so the artifact validation is exercised for bytes.
"""

from __future__ import annotations

import importlib.util
import io
import json
import subprocess
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "ci" / "promote-unica-opencode.py"

NPM_PACKAGE_NAME = "@apshendev/unica-opencode"
REGISTRY_URL = "https://registry.npmjs.org/x.tgz"

FORK_ENV = {
    "GITHUB_REPOSITORY": "apshendev/unica",
    "GITHUB_EVENT_NAME": "push",
    "GITHUB_REF": "refs/tags/v0.13.0",
    "GITHUB_REF_NAME": "v0.13.0",
    "NODE_AUTH_TOKEN": "promotion-secret",
}


def load_promote_module():
    spec = importlib.util.spec_from_file_location("promote_unica_opencode", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to load {SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeProcess:
    """Answers subprocess calls from a per-prefix queue and records argv."""

    def __init__(self, results) -> None:
        # results: dict command-prefix -> single result or list of results
        self.results = {
            prefix: (list(result) if isinstance(result, list) else [result])
            for prefix, result in results.items()
        }
        self.calls: list[tuple[list[str], str | None]] = []

    def __call__(self, argv, *, cwd=None):
        self.calls.append((list(argv), cwd))
        for prefix, queue in self.results.items():
            if list(argv[: len(prefix)]) == list(prefix):
                if not queue:
                    raise AssertionError(
                        f"subprocess prefix {prefix} exhausted by call: {argv}"
                    )
                returncode, stdout, stderr = queue.pop(0)
                return subprocess.CompletedProcess(argv, returncode, stdout, stderr)
        raise AssertionError(f"unexpected subprocess call: {argv}")


class OpenCodeNpmPromotionTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)

        self.npm_root = self.root / "dist" / "npm"
        self.npm_root.mkdir(parents=True)

        self.env = dict(FORK_ENV)

    def make_candidate(self, version: str) -> bytes:
        """Собрать настоящий gzip tar кандидата и вернуть его байты."""
        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode="w:gz") as archive:

            def add(name: str, data: bytes) -> None:
                info = tarfile.TarInfo(name)
                info.size = len(data)
                archive.addfile(info, io.BytesIO(data))

            add(
                "package/package.json",
                json.dumps({"name": NPM_PACKAGE_NAME, "version": version}).encode(
                    "utf-8"
                ),
            )
            add(
                "package/runtime-manifest.json",
                json.dumps({"pluginVersion": version, "development": False}).encode(
                    "utf-8"
                ),
            )
        archive_bytes = buffer.getvalue()
        (self.npm_root / f"apshendev-unica-opencode-{version}.tgz").write_bytes(
            archive_bytes
        )
        return archive_bytes

    def set_candidate_version(self, version: str) -> None:
        self.env.update(
            {"GITHUB_REF": f"refs/tags/v{version}", "GITHUB_REF_NAME": f"v{version}"}
        )

    def run_promotion(
        self,
        process: FakeProcess,
        registry_bytes: bytes | None = None,
        env: dict | None = None,
    ):
        module = load_promote_module()
        downloads: list[str] = []

        def fake_download(url: str) -> bytes:
            downloads.append(url)
            assert registry_bytes is not None
            return registry_bytes

        with (
            patch.dict("os.environ", env or self.env, clear=False),
            patch.object(module, "run_process", process),
            patch.object(module, "download_registry_tarball", fake_download),
        ):
            module.main(
                ["--repo-root", str(REPO_ROOT), "--npm-root", str(self.npm_root)]
            )
        return module, downloads

    def dist_tags_process(
        self, initial: dict, reread: dict | None = None
    ) -> FakeProcess:
        return FakeProcess(
            {
                ("npm", "view"): [
                    (0, json.dumps(initial), ""),
                    (0, json.dumps(REGISTRY_URL), ""),
                    (0, json.dumps(reread if reread is not None else initial), ""),
                ],
                ("npm", "dist-tag"): (0, "", ""),
            }
        )

    def add_calls(self, process: FakeProcess) -> list[list[str]]:
        return [
            argv for argv, _ in process.calls if argv[:3] == ["npm", "dist-tag", "add"]
        ]

    def test_the_stable_release_promotes_latest(self) -> None:
        archive_bytes = self.make_candidate("0.13.0")
        process = self.dist_tags_process(
            {"latest": "0.12.0", "staging": "0.13.0"},
            reread={"latest": "0.13.0", "staging": "0.13.0"},
        )

        self.run_promotion(process, registry_bytes=archive_bytes)

        self.assertEqual(
            [
                [
                    "npm",
                    "dist-tag",
                    "add",
                    f"{NPM_PACKAGE_NAME}@0.13.0",
                    "latest",
                ]
            ],
            self.add_calls(process),
        )

    def test_a_prerelease_promotes_next(self) -> None:
        archive_bytes = self.make_candidate("0.13.0-rc.1")
        self.set_candidate_version("0.13.0-rc.1")
        process = self.dist_tags_process(
            {"latest": "0.12.0", "next": "0.13.0-beta.2", "staging": "0.13.0-rc.1"},
            reread={
                "latest": "0.12.0",
                "next": "0.13.0-rc.1",
                "staging": "0.13.0-rc.1",
            },
        )

        self.run_promotion(process, registry_bytes=archive_bytes)

        self.assertEqual(
            [
                [
                    "npm",
                    "dist-tag",
                    "add",
                    f"{NPM_PACKAGE_NAME}@0.13.0-rc.1",
                    "next",
                ]
            ],
            self.add_calls(process),
        )

    def test_an_already_promoted_version_is_idempotent(self) -> None:
        archive_bytes = self.make_candidate("0.13.0")
        process = self.dist_tags_process({"latest": "0.13.0", "staging": "0.13.0"})

        self.run_promotion(process, registry_bytes=archive_bytes)

        self.assertEqual([], self.add_calls(process))

    def test_promotion_refuses_to_move_a_dist_tag_backwards(self) -> None:
        """Единый агрегатный фальсификатор forward-only.

        Отказ обратного хода и полная матрица SemVer-порядка — префиксы,
        числовые компоненты, старшинство пре-релиза перед релизом — идут
        subTest'ами одного теста.
        """
        archive_bytes = self.make_candidate("0.12.0")
        self.set_candidate_version("0.12.0")
        process = self.dist_tags_process({"latest": "0.13.0", "staging": "0.12.0"})

        with self.assertRaises(SystemExit) as ctx:
            self.run_promotion(process, registry_bytes=archive_bytes)
        self.assertIn("backwards", str(ctx.exception))
        self.assertEqual([], self.add_calls(process))

        module = load_promote_module()
        matrix = {
            "0.13.0-rc.1 < 0.13.0": ("0.13.0-rc.1", "0.13.0"),
            "0.13.0-alpha < 0.13.0-alpha.1": ("0.13.0-alpha", "0.13.0-alpha.1"),
            "0.13.0-alpha.1 < 0.13.0-beta": ("0.13.0-alpha.1", "0.13.0-beta"),
            "0.13.0-beta < 0.13.0-rc.1": ("0.13.0-beta", "0.13.0-rc.1"),
            "0.9.0 < 0.10.0": ("0.9.0", "0.10.0"),
            "0.13.0 < 0.13.1": ("0.13.0", "0.13.1"),
            "1.2.3 < 2.0.0": ("1.2.3", "2.0.0"),
        }
        for label, (lower, higher) in matrix.items():
            with self.subTest(order=label):
                self.assertLess(
                    module.semver_precedence(lower), module.semver_precedence(higher)
                )

    def test_promotion_refuses_an_unpublished_version(self) -> None:
        archive_bytes = self.make_candidate("0.13.0")
        process = FakeProcess(
            {
                ("npm", "view"): [
                    (0, json.dumps({"latest": "0.12.0", "staging": "0.13.0"}), ""),
                    (1, "", "npm error code E404 not found"),
                ],
            }
        )

        with self.assertRaises(SystemExit) as ctx:
            self.run_promotion(process, registry_bytes=archive_bytes)

        self.assertIn("stage did not complete", str(ctx.exception))
        self.assertEqual([], self.add_calls(process))

    def test_promotion_refuses_when_the_package_is_missing(self) -> None:
        archive_bytes = self.make_candidate("0.13.0")
        process = FakeProcess(
            {
                ("npm", "view"): (1, "", "npm error code E404 not found"),
            }
        )

        with self.assertRaises(SystemExit) as ctx:
            self.run_promotion(process, registry_bytes=archive_bytes)

        self.assertIn("bootstrap", str(ctx.exception))
        self.assertEqual([], self.add_calls(process))

    def test_promotion_gates_mirror_publishing(self) -> None:
        archive_bytes = self.make_candidate("0.13.0")

        # Upstream-репозиторий, не-пуш и чужой тег — отказ до любого npm.
        for label, overrides in (
            ("upstream", {"GITHUB_REPOSITORY": "IngvarConsulting/unica"}),
            ("non-push", {"GITHUB_EVENT_NAME": "pull_request"}),
            (
                "foreign tag",
                {"GITHUB_REF": "refs/tags/v0.12.0", "GITHUB_REF_NAME": "v0.12.0"},
            ),
        ):
            with self.subTest(gate=label):
                process = FakeProcess({})
                with self.assertRaises(SystemExit):
                    self.run_promotion(
                        process,
                        registry_bytes=archive_bytes,
                        env={**self.env, **overrides},
                    )
                self.assertEqual(process.calls, [])

        # Нет npm-токена — отказ fail-closed с именем секрета promotion.
        no_token = {
            key: value for key, value in self.env.items() if key != "NODE_AUTH_TOKEN"
        }
        process = FakeProcess({})
        with self.assertRaises(SystemExit) as ctx:
            self.run_promotion(process, registry_bytes=archive_bytes, env=no_token)
        self.assertIn("NPM_PROMOTION_TOKEN", str(ctx.exception))
        self.assertEqual(process.calls, [])

    def test_promotion_never_publishes(self) -> None:
        archive_bytes = self.make_candidate("0.13.0")
        stable = self.dist_tags_process(
            {"latest": "0.12.0", "staging": "0.13.0"},
            reread={"latest": "0.13.0", "staging": "0.13.0"},
        )
        self.run_promotion(stable, registry_bytes=archive_bytes)

        for path in self.npm_root.glob("*.tgz"):
            path.unlink()
        archive_bytes = self.make_candidate("0.13.0-rc.1")
        self.set_candidate_version("0.13.0-rc.1")
        prerelease = self.dist_tags_process(
            {"next": "0.13.0-beta.2", "staging": "0.13.0-rc.1"},
            reread={"next": "0.13.0-rc.1", "staging": "0.13.0-rc.1"},
        )
        self.run_promotion(prerelease, registry_bytes=archive_bytes)

        for process in (stable, prerelease):
            for argv, _cwd in process.calls:
                self.assertNotEqual(argv[:2], ["npm", "publish"])

    def test_promotion_rereads_dist_tags_after_the_write(self) -> None:
        archive_bytes = self.make_candidate("0.13.0")

        # Перечитанное состояние обязано показать точную цель; запись,
        # которую реестр «не заметил», — красный promotion.
        stale = self.dist_tags_process(
            {"latest": "0.12.0", "staging": "0.13.0"},
            reread={"latest": "0.12.0", "staging": "0.13.0"},
        )
        with self.assertRaises(SystemExit) as ctx:
            self.run_promotion(stale, registry_bytes=archive_bytes)
        self.assertIn("0.13.0", str(ctx.exception))

        confirmed = self.dist_tags_process(
            {"latest": "0.12.0", "staging": "0.13.0"},
            reread={"latest": "0.13.0", "staging": "0.13.0"},
        )
        self.run_promotion(confirmed, registry_bytes=archive_bytes)
        self.assertEqual(1, len(self.add_calls(confirmed)))

    def test_promotion_refuses_when_no_tarball_is_present(self) -> None:
        process = FakeProcess({})

        with self.assertRaises(SystemExit):
            self.run_promotion(process)

        self.assertEqual(process.calls, [])

    def test_promotion_refuses_when_two_tarballs_are_present(self) -> None:
        self.make_candidate("0.13.0")
        self.make_candidate("0.14.0")
        self.set_candidate_version("0.13.0")
        process = FakeProcess({})

        with self.assertRaises(SystemExit):
            self.run_promotion(process)

        self.assertEqual(process.calls, [])

    def test_promotion_refuses_a_corrupt_tarball(self) -> None:
        (self.npm_root / "apshendev-unica-opencode-0.13.0.tgz").write_bytes(
            b"not a tarball at all"
        )
        process = FakeProcess({})

        with self.assertRaises(SystemExit):
            self.run_promotion(process)

        self.assertEqual(process.calls, [])


if __name__ == "__main__":
    unittest.main()
