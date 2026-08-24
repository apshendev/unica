"""Contract tests for the OpenCode npm publication step.

The publication script is the only writer to npm. Its seams are the process
environment it gates on and the npm invocations it makes; tests fake the
process boundaries (publish attempt, registry query, registry download) and
never talk to npm.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "ci" / "publish-unica-opencode.py"

FORK_ENV = {
    "GITHUB_REPOSITORY": "apshendev/unica",
    "GITHUB_EVENT_NAME": "push",
    "GITHUB_REF": "refs/tags/v0.12.0",
    "GITHUB_REF_NAME": "v0.12.0",
}


def load_publish_module():
    spec = importlib.util.spec_from_file_location("publish_unica_opencode", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to load {SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeProcess:
    """Answers one kind of subprocess call and records every argv."""

    def __init__(self, results) -> None:
        # results: dict command-prefix -> (returncode, stdout, stderr)
        self.results = results
        self.calls: list[tuple[list[str], str | None]] = []

    def __call__(self, argv, *, cwd=None):
        self.calls.append((list(argv), cwd))
        for prefix, result in self.results.items():
            if list(argv[: len(prefix)]) == list(prefix):
                returncode, stdout, stderr = result
                return subprocess.CompletedProcess(argv, returncode, stdout, stderr)
        raise AssertionError(f"unexpected subprocess call: {argv}")


class OpenCodeNpmPublicationTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)

        self.npm_root = self.root / "dist" / "npm"
        self.make_candidate("0.12.0")

        self.env = dict(FORK_ENV)

    def make_candidate(self, version: str) -> None:
        staging = self.npm_root / "staging"
        staging.mkdir(parents=True, exist_ok=True)
        (staging / "package.json").write_text(
            json.dumps({"name": "@apshendev/unica-opencode", "version": version}),
            encoding="utf-8",
        )
        (staging / "runtime-manifest.json").write_text(
            json.dumps({"pluginVersion": version, "development": False}),
            encoding="utf-8",
        )
        self.tarball = self.npm_root / f"apshendev-unica-opencode-{version}.tgz"
        self.tarball.write_bytes(b"candidate-bytes")

    def run_publish_step(self, process: FakeProcess, registry_bytes=None):
        module = load_publish_module()
        downloads: list[str] = []

        def fake_download(url: str) -> bytes:
            downloads.append(url)
            assert registry_bytes is not None
            return registry_bytes

        with (
            patch.dict("os.environ", self.env, clear=False),
            patch.object(module, "run_process", process),
            patch.object(module, "download_registry_tarball", fake_download),
        ):
            module.main(["--npm-root", str(self.npm_root)])
        return module, downloads

    def publish_calls(self, process: FakeProcess) -> list[tuple[list[str], str | None]]:
        return [call for call in process.calls if call[0][:2] == ["npm", "publish"]]

    def test_a_tagged_fork_release_publishes_with_provenance(self) -> None:
        process = FakeProcess({("npm", "publish"): (0, "", "")})

        self.run_publish_step(process)

        calls = self.publish_calls(process)
        self.assertEqual(len(calls), 1)
        argv, cwd = calls[0]
        self.assertIn("--provenance", argv)
        self.assertIn("--access", argv)
        self.assertIn("public", argv)
        self.assertNotIn("--tag", argv)
        self.assertIn(str(self.tarball), argv)
        self.assertEqual(cwd, str(REPO_ROOT))
        self.assertEqual(len(process.calls), 1, "no registry query after success")

    def test_a_prerelease_publishes_under_the_next_dist_tag(self) -> None:
        self.make_candidate("0.13.0-rc.1")
        self.env.update(
            {"GITHUB_REF": "refs/tags/v0.13.0-rc.1", "GITHUB_REF_NAME": "v0.13.0-rc.1"}
        )
        process = FakeProcess({("npm", "publish"): (0, "", "")})

        self.run_publish_step(process)

        argv, _cwd = self.publish_calls(process)[0]
        tag_index = argv.index("--tag")
        self.assertEqual(argv[tag_index + 1], "next")

    def test_publication_refuses_to_run_from_the_upstream_repository(self) -> None:
        self.env["GITHUB_REPOSITORY"] = "IngvarConsulting/unica"
        process = FakeProcess({})

        with self.assertRaises(SystemExit) as ctx:
            self.run_publish_step(process)

        self.assertIn("apshendev/unica", str(ctx.exception))
        self.assertEqual(process.calls, [])

    def test_publication_refuses_non_tag_events(self) -> None:
        process = FakeProcess({})
        for overrides in (
            {"GITHUB_EVENT_NAME": "pull_request"},
            {"GITHUB_REF": "refs/heads/main", "GITHUB_REF_NAME": "main"},
        ):
            with self.subTest(overrides=overrides):
                env = {**self.env, **overrides}
                module = load_publish_module()
                with (
                    patch.dict("os.environ", env, clear=False),
                    patch.object(module, "run_process", process),
                ):
                    with self.assertRaises(SystemExit):
                        module.main(["--npm-root", str(self.npm_root)])

        self.assertEqual(process.calls, [])

    def test_publication_refuses_a_tag_that_disagrees_with_the_candidate(self) -> None:
        self.env.update(
            {"GITHUB_REF": "refs/tags/v0.11.0", "GITHUB_REF_NAME": "v0.11.0"}
        )
        process = FakeProcess({})

        with self.assertRaises(SystemExit) as ctx:
            self.run_publish_step(process)

        self.assertIn("0.12.0", str(ctx.exception))
        self.assertEqual(process.calls, [])

    def test_publication_refuses_a_foreign_package_identity(self) -> None:
        staging = self.npm_root / "staging"
        (staging / "package.json").write_text(
            json.dumps({"name": "@example/unica", "version": "0.12.0"}),
            encoding="utf-8",
        )
        process = FakeProcess({})

        with self.assertRaises(SystemExit) as ctx:
            self.run_publish_step(process)

        self.assertIn("@apshendev/unica-opencode", str(ctx.exception))
        self.assertEqual(process.calls, [])

    def test_a_rerun_is_accepted_only_with_identical_registry_bytes(self) -> None:
        registry_url = "https://registry.npmjs.org/x.tgz"

        # The registry serves the version, but with different bytes.
        differing = FakeProcess(
            {
                ("npm", "publish"): (1, "", "npm error code E403 forbidden"),
                ("npm", "view"): (0, json.dumps(registry_url), ""),
            }
        )
        with self.assertRaises(SystemExit) as ctx:
            self.run_publish_step(differing, registry_bytes=b"other-bytes")
        self.assertIn("differ", str(ctx.exception))
        self.assertEqual(self.publish_calls(differing), differing.calls[:1])

        # The registry serves the same bytes: the rerun is accepted.
        identical = FakeProcess(
            {
                ("npm", "publish"): (1, "", "npm error code E403 forbidden"),
                ("npm", "view"): (0, json.dumps(registry_url), ""),
            }
        )
        _module, downloads = self.run_publish_step(
            identical, registry_bytes=self.tarball.read_bytes()
        )
        self.assertEqual(downloads, [registry_url])

    def test_a_publish_failure_without_a_published_version_stays_failed(self) -> None:
        # The version is not in the registry: whatever npm said, this was not
        # an already-published rerun, and no recovery may soften the failure.
        process = FakeProcess(
            {
                ("npm", "publish"): (1, "", "npm error code EPERM nope"),
                ("npm", "view"): (1, "", "npm error code E404 not found"),
            }
        )
        downloads: list[str] = []
        module = load_publish_module()
        with (
            patch.dict("os.environ", self.env, clear=False),
            patch.object(module, "run_process", process),
            patch.object(
                module,
                "download_registry_tarball",
                side_effect=lambda url: downloads.append(url),
            ),
        ):
            with self.assertRaises(SystemExit) as ctx:
                module.main(["--npm-root", str(self.npm_root)])

        self.assertIn("npm publish failed", str(ctx.exception))
        self.assertEqual(downloads, [])


if __name__ == "__main__":
    unittest.main()
