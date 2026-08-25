"""Contract tests for the OpenCode npm staging step.

The staging script is the only writer to npm. Its seams are the process
environment it gates on and the npm invocations it makes; tests fake the
process boundaries (publish attempt, registry query, registry download) and
never talk to npm. Publication only stages the candidate: the `latest`/
`next` dist-tags are moved by the separate promotion script.
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
PROMOTE_SCRIPT_PATH = REPO_ROOT / "scripts" / "ci" / "promote-unica-opencode.py"

FORK_ENV = {
    "GITHUB_REPOSITORY": "apshendev/unica",
    "GITHUB_EVENT_NAME": "push",
    "GITHUB_REF": "refs/tags/v0.12.0",
    "GITHUB_REF_NAME": "v0.12.0",
}

REGISTRY_URL = "https://registry.npmjs.org/x.tgz"


def load_publish_module():
    spec = importlib.util.spec_from_file_location("publish_unica_opencode", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to load {SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeProcess:
    """Answers subprocess calls from a per-prefix queue and records argv.

    A prefix maps to one `(returncode, stdout, stderr)` tuple consumed per
    call, or to a list of them consumed in order; an exhausted or unknown
    prefix is a test failure, not a silent repeat.
    """

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
            patch.object(module, "REGISTRY_VISIBILITY_ATTEMPTS", 2),
            patch.object(module.time, "sleep", lambda seconds: None),
        ):
            module.main(["--npm-root", str(self.npm_root)])
        return module, downloads

    def publish_calls(self, process: FakeProcess) -> list[tuple[list[str], str | None]]:
        return [call for call in process.calls if call[0][:2] == ["npm", "publish"]]

    def visibility_ok_process(self) -> FakeProcess:
        # Первый опрос реестра — версия ещё не видна, второй — URL тарбола.
        return FakeProcess(
            {
                ("npm", "publish"): (0, "", ""),
                ("npm", "view"): [
                    (1, "", "npm error code E404 not found"),
                    (0, json.dumps(REGISTRY_URL), ""),
                ],
            }
        )

    def test_a_tagged_fork_release_publishes_with_provenance(self) -> None:
        process = self.visibility_ok_process()

        self.run_publish_step(process, registry_bytes=self.tarball.read_bytes())

        calls = self.publish_calls(process)
        self.assertEqual(len(calls), 1)
        argv, cwd = calls[0]
        self.assertIn("--provenance", argv)
        self.assertIn("--access", argv)
        self.assertIn("public", argv)
        self.assertIn(str(self.tarball), argv)
        self.assertEqual(cwd, str(REPO_ROOT))
        # Успех ещё не конец: публикация подтверждается видимостью в реестре.
        self.assertEqual(2, len(process.calls) - 1)

    def test_stable_and_prerelease_publish_under_the_staging_dist_tag(self) -> None:
        scenarios = {
            "stable": ("0.12.0", FORK_ENV),
            "prerelease": (
                "0.13.0-rc.1",
                {
                    "GITHUB_REPOSITORY": "apshendev/unica",
                    "GITHUB_EVENT_NAME": "push",
                    "GITHUB_REF": "refs/tags/v0.13.0-rc.1",
                    "GITHUB_REF_NAME": "v0.13.0-rc.1",
                },
            ),
        }
        for label, (version, env) in scenarios.items():
            with self.subTest(label=label):
                self.make_candidate(version)
                self.env = dict(env)
                process = self.visibility_ok_process()

                self.run_publish_step(process, registry_bytes=self.tarball.read_bytes())

                argv, _cwd = self.publish_calls(process)[0]
                self.assertIn("--tag", argv)
                self.assertEqual("staging", argv[argv.index("--tag") + 1])

    def test_a_prerelease_never_publishes_under_next(self) -> None:
        self.make_candidate("0.13.0-rc.1")
        self.env.update(
            {"GITHUB_REF": "refs/tags/v0.13.0-rc.1", "GITHUB_REF_NAME": "v0.13.0-rc.1"}
        )
        process = self.visibility_ok_process()

        self.run_publish_step(process, registry_bytes=self.tarball.read_bytes())

        argv, _cwd = self.publish_calls(process)[0]
        self.assertNotIn("next", argv)
        self.assertEqual("staging", argv[argv.index("--tag") + 1])

    def test_the_staging_tag_literal_is_shared_by_stage_and_promotion(self) -> None:
        publish_text = SCRIPT_PATH.read_text(encoding="utf-8")
        promote_text = PROMOTE_SCRIPT_PATH.read_text(encoding="utf-8")

        self.assertIn('STAGING_DIST_TAG = "staging"', publish_text)
        self.assertIn('STAGING_DIST_TAG = "staging"', promote_text)

    def test_a_successful_publish_waits_for_registry_visibility(self) -> None:
        """Единый фальсификатор visibility-обязательства стадии.

        Успех `npm publish` ничего не доказывает, пока реестр не начал
        отдавать эту версию байт-в-байт; timeout, мусор вместо ответа и
        чужие байты фатальны, и rerun проверяет те же байты.
        """
        # Успех: первый опрос E404, второй отдаёт URL, байты совпадают.
        success = self.visibility_ok_process()
        _module, downloads = self.run_publish_step(
            success, registry_bytes=self.tarball.read_bytes()
        )
        self.assertEqual(downloads, [REGISTRY_URL])

        # Постоянный E404: попытки исчерпаны — visibility timeout.
        timeout = FakeProcess(
            {
                ("npm", "publish"): (0, "", ""),
                ("npm", "view"): [
                    (1, "", "npm error code E404 not found"),
                    (1, "", "npm error code E404 not found"),
                ],
            }
        )
        with self.assertRaises(SystemExit) as ctx:
            self.run_publish_step(timeout)
        self.assertIn("visibility timeout", str(ctx.exception))

        # `npm view` ответил не-JSON — фатально, это не «пока не видна».
        garbage = FakeProcess(
            {
                ("npm", "publish"): (0, "", ""),
                ("npm", "view"): (0, "not json at all", ""),
            }
        )
        with self.assertRaises(SystemExit):
            self.run_publish_step(garbage)

        # `npm view` вернул JSON-строку, не являющуюся URL тарбола.
        banana = FakeProcess(
            {
                ("npm", "publish"): (0, "", ""),
                ("npm", "view"): (0, json.dumps("banana"), ""),
            }
        )
        with self.assertRaises(SystemExit) as ctx:
            self.run_publish_step(banana)
        self.assertIn("banana", str(ctx.exception))

        # SHA-512 ответа реестра расходится с кандидатом.
        mismatch = FakeProcess(
            {
                ("npm", "publish"): (0, "", ""),
                ("npm", "view"): (0, json.dumps(REGISTRY_URL), ""),
            }
        )
        with self.assertRaises(SystemExit) as ctx:
            self.run_publish_step(mismatch, registry_bytes=b"other-bytes")
        self.assertIn("differ", str(ctx.exception))

        # Rerun-ветка сверяет те же байты тем же механизмом.
        rerun = FakeProcess(
            {
                ("npm", "publish"): [
                    (1, "", "npm error code E403 forbidden"),
                ],
                ("npm", "view"): (0, json.dumps(REGISTRY_URL), ""),
            }
        )
        _module, downloads = self.run_publish_step(
            rerun, registry_bytes=self.tarball.read_bytes()
        )
        self.assertEqual(downloads, [REGISTRY_URL])

    def test_a_rerun_is_accepted_only_with_identical_registry_bytes(self) -> None:
        # Реестр отдаёт версию, но с другими байтами.
        differing = FakeProcess(
            {
                ("npm", "publish"): (1, "", "npm error code E403 forbidden"),
                ("npm", "view"): (0, json.dumps(REGISTRY_URL), ""),
            }
        )
        with self.assertRaises(SystemExit) as ctx:
            self.run_publish_step(differing, registry_bytes=b"other-bytes")
        self.assertIn("differ", str(ctx.exception))
        self.assertEqual(self.publish_calls(differing), differing.calls[:1])

        # Реестр отдаёт те же байты: rerun принят.
        identical = FakeProcess(
            {
                ("npm", "publish"): (1, "", "npm error code E403 forbidden"),
                ("npm", "view"): (0, json.dumps(REGISTRY_URL), ""),
            }
        )
        _module, downloads = self.run_publish_step(
            identical, registry_bytes=self.tarball.read_bytes()
        )
        self.assertEqual(downloads, [REGISTRY_URL])

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

    def test_a_publish_failure_without_a_published_version_stays_failed(self) -> None:
        # Версии в реестре нет: что бы npm ни сказал, это не уже
        # опубликованный rerun, и восстановление не смягчает отказ.
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
