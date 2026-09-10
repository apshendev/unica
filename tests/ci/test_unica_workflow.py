"""Стражи workflow: разбор структуры, а не байтов YAML.

Проверяется то, что видит GitHub: триггеры, джобы, `needs`, условия, шаги, их
`with`, `env` и скрипты. Перенос строки в условии, стиль списка или кавычки
поведения не меняют — и стража не красят. Текстом остаются две вещи:
комментарий версии у пина действия (его читает Dependabot, а не GitHub) и
маркеры, которых в файле быть не должно вовсе.
"""

from __future__ import annotations

import re
import unittest
from collections.abc import Iterator
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS_DIR = REPO_ROOT / ".github" / "workflows"
RELEASE_WORKFLOW = WORKFLOWS_DIR / "unica-plugin-release.yml"
NIGHTLY_WORKFLOW = WORKFLOWS_DIR / "unica-nightly.yml"
PAGES_WORKFLOW = WORKFLOWS_DIR / "unica-pages.yml"
PUBLISH_WORKFLOW = WORKFLOWS_DIR / "publish-unica-marketplace.yml"
LEGACY_WORKFLOW = WORKFLOWS_DIR / "unica-legacy-migration.yml"


def load(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def triggers(workflow: dict) -> dict:
    """`on:` — PyYAML читает ключ по YAML 1.1 как булево `True`."""
    return workflow.get("on") or workflow.get(True) or {}


def jobs(workflow: dict) -> dict:
    return workflow["jobs"]


def job(workflow: dict, job_id: str) -> dict:
    found = jobs(workflow).get(job_id)
    assert found is not None, f"в workflow нет джобы {job_id}"
    return found


def needs(node: dict) -> list[str]:
    value = node.get("needs", [])
    return [value] if isinstance(value, str) else list(value)


def steps(node: dict) -> list[dict]:
    return list(node.get("steps", []))


def scripts(node: dict) -> list[str]:
    return [step["run"] for step in steps(node) if "run" in step]


def script(node: dict) -> str:
    return "\n".join(scripts(node))


def all_scripts(workflow: dict) -> str:
    return "\n".join(script(found) for found in jobs(workflow).values())


def normalized(value: object) -> str:
    """Выражение без переносов и лишних пробелов: перенос строки — не смысл."""
    return " ".join(str(value).split())


def condition(node: dict) -> str:
    return normalized(node.get("if", ""))


def expressions(node: dict) -> list[str]:
    """Всё, что вычисляет GitHub в джобе: условия, `env` и `with` джобы и шагов."""
    found = [condition(node), *(normalized(value) for value in (node.get("env") or {}).values())]
    for step in steps(node):
        found.append(condition(step))
        found.extend(normalized(value) for value in (step.get("env") or {}).values())
        found.extend(normalized(value) for value in (step.get("with") or {}).values())
    return found


def strings(node: object) -> Iterator[str]:
    """Каждый скаляр и ключ дерева — для маркеров, которых быть не должно."""
    if isinstance(node, dict):
        for key, value in node.items():
            yield str(key)
            yield from strings(value)
    elif isinstance(node, list):
        for item in node:
            yield from strings(item)
    elif node is not None:
        yield str(node)


def action(step: dict) -> str:
    return step.get("uses", "").split("@", 1)[0]


def steps_using(node: dict, prefix: str) -> list[dict]:
    return [step for step in steps(node) if action(step) == prefix]


def step_named(node: dict, name: str) -> dict:
    for step in steps(node):
        if step.get("name") == name:
            return step
    raise AssertionError(f"нет шага {name!r}")


def step_by_id(node: dict, step_id: str) -> dict:
    for step in steps(node):
        if step.get("id") == step_id:
            return step
    raise AssertionError(f"нет шага с id {step_id!r}")


def step_index(node: dict, name: str) -> int:
    return steps(node).index(step_named(node, name))


def step_text(step: dict) -> str:
    """Шаг одной строкой: имя, действие, `with` и скрипт — для порядка шагов."""
    return "\n".join([step.get("name", ""), step.get("uses", ""), *map(str, (step.get("with") or {}).values()), step.get("run", "")])


def uploads(node: dict) -> list[dict]:
    return [step.get("with") or {} for step in steps_using(node, "actions/upload-artifact")]


def downloads(node: dict) -> list[dict]:
    return [step.get("with") or {} for step in steps_using(node, "actions/download-artifact")]


def matrix_include(node: dict) -> list[dict]:
    return list((node.get("strategy") or {}).get("matrix", {}).get("include", []))


def targets(node: dict) -> list[tuple[str, str]]:
    return [(entry["target"], entry["runner"]) for entry in matrix_include(node)]


def pinned(action_name: str, major: str) -> str:
    """Действие закреплено хешем коммита, а версия названа комментарием рядом.

    Dependabot двигает хеш вместе с комментарием, поэтому тест держит только
    мажорную версию: минорный сдвиг проходит, смена мажора требует правки.
    Комментарий не видит ни GitHub, ни разбор YAML — это единственная проверка
    по тексту файла.
    """
    return rf"uses: {re.escape(action_name)}@[0-9a-f]{{40}} # {re.escape(major)}(\.\d+)*\b"


def job_block(workflow: str, job_id: str) -> str:
    """Текстовый блок job по имени — для fork-тестов npm-контура."""
    marker = f"  {job_id}:\n"
    start = workflow.find(marker)
    if start == -1:
        return ""
    next_job = re.search(r"(?m)^  [a-zA-Z0-9_-]+:\n", workflow[start + len(marker) :])
    if next_job is None:
        return workflow[start:]
    end = start + len(marker) + next_job.start()
    return workflow[start:end]


def assert_pinned(test: unittest.TestCase, path: Path, step: dict, major: str) -> None:
    """Шаг закреплён хешем, и комментарий рядом с этим самым хешем называет мажор."""
    action_name, _, ref = step.get("uses", "").partition("@")
    test.assertRegex(ref, r"^[0-9a-f]{40}$", step.get("uses"))
    test.assertRegex(
        path.read_text(encoding="utf-8"),
        rf"uses: {re.escape(action_name)}@{ref} # {re.escape(major)}(\.\d+)*\b",
    )


class UnicaWorkflowGuardrailTests(unittest.TestCase):
    def setUp(self) -> None:
        self.release = load(RELEASE_WORKFLOW)
        self.nightly = load(NIGHTLY_WORKFLOW)
        self.pages = load(PAGES_WORKFLOW)
        self.publish = load(PUBLISH_WORKFLOW)

    def test_source_gate_checks_the_full_rust_and_python_workspace(self) -> None:
        text = all_scripts(self.release)

        self.assertIn("cargo clippy --workspace --all-targets --all-features --message-format=json -- -D warnings", text)
        # Наборы гоняет шов; сами команды закреплены тестом `test_run_tests`.
        self.assertIn('python3 scripts/ci/run-tests.py --profile "$GATE_PROFILE" --ecosystem rust --results', text)
        self.assertIn('python scripts/ci/run-tests.py --profile "$GATE_PROFILE" --ecosystem python --suite "$SUITE" --only-size "$LANE" --results', text)
        self.assertNotIn("cargo test --workspace", text)
        self.assertNotIn("unittest discover", text)
        self.assertIn("python -m py_compile scripts/dev/*.py tests/dev/*.py", text)
        self.assertIn("python scripts/ci/check-version-contract.py", text)

    def test_every_pull_request_gets_a_stable_aggregate_gate(self) -> None:
        on = triggers(self.release)
        gate = job(self.release, "unica-ci")

        self.assertIn("labeled", on["pull_request"]["types"])
        self.assertIn("unlabeled", on["pull_request"]["types"])
        self.assertNotIn("paths", on["pull_request"])
        self.assertNotIn("paths", on["push"])
        self.assertEqual(gate["name"], "Unica CI")
        self.assertEqual(condition(gate), "always()")
        self.assertIn("python scripts/ci/evaluate-ci-gate.py", script(gate))
        for upstream in (
            "classify-changes",
            "guards",
            "test-python",
            "test-rust-platforms",
            "build-tools",
            "package-thin",
            "probe-thin-bootstrap",
            "release-assessment",
            "publish-release-assets",
            "smoke-thin-plugin",
            "verify-published-assets",
            "publish-opencode-npm",
            "smoke-opencode-windows",
            "smoke-opencode-linux",
            "promote-opencode-npm",
        ):
            with self.subTest(upstream=upstream):
                self.assertIn(upstream, needs(gate))

    def test_p0_dry_release_proof_is_read_only_and_aggregated(self) -> None:
        proof = job(self.release, "p0-release-proof")

        self.assertEqual(set(needs(proof)), {"build-tools", "package-thin", "release-assessment"})
        for argument in (
            "scripts/ci/release-proof.py",
            "--mode dry",
            "--wire-dir",
            "--package-dir",
            "--asset-verification-dir",
            "--source-commit",
            "--baseline",
            "--out-dir dist/p0-proof",
        ):
            self.assertIn(argument, script(proof))
        self.assertEqual(proof["permissions"], {"contents": "read"})
        self.assertEqual(steps_using(proof, "softprops/action-gh-release"), [])
        self.assertNotIn("git tag", script(proof))
        self.assertIn("p0-release-proof", needs(job(self.release, "unica-ci")))

    def test_wire_probes_embed_the_matrix_target_in_their_evidence(self) -> None:
        self.assertEqual(2, script(job(self.release, "build-tools")).count('--target "$TARGET"'))

    def test_classifier_exposes_typed_contours_and_ci_full_override(self) -> None:
        classifier = job(self.release, "classify-changes")

        for output in (
            "rust_changed",
            "platform_changed",
            "toolchain_changed",
            "search_integration_changed",
            "package_changed",
            "plugin_content_changed",
            "ci_changed",
            "release_required",
            "assessment_required",
        ):
            with self.subTest(output=output):
                self.assertIn(output, classifier["outputs"])
        scope = step_by_id(classifier, "scope")
        self.assertIn("contains(github.event.pull_request.labels.*.name, 'ci:full')", scope["env"]["FORCE_FULL"])
        self.assertIn("--force-full", script(classifier))

    def test_classifier_preserves_merge_base_for_triple_dot_diff(self) -> None:
        classifier = job(self.release, "classify-changes")
        checkout = steps_using(classifier, "actions/checkout")[0]
        scope = step_by_id(classifier, "scope")

        self.assertEqual(checkout["with"]["fetch-depth"], 0)
        self.assertEqual(scope["env"]["BASE_REF"], "${{ github.base_ref }}")
        self.assertIn('git fetch --no-tags origin "$BASE_REF"', scope["run"])
        self.assertNotIn("--depth", scope["run"])
        self.assertIn("FORCE_FULL", scope["run"])
        self.assertIn("git diff --name-only FETCH_HEAD...HEAD", scope["run"])

    def test_a_ref_name_never_reaches_the_shell_as_script_text(self) -> None:
        """A ref name is data, so it crosses into `run:` through `env:`.

        Git ref rules forbid spaces but allow `;`, `$`, backticks and
        parentheses, so a ref name pasted into a `run:` block through `${{ }}`
        is a command-injection sink. Passing it as an environment variable keeps
        the shell from ever parsing it.

        Branch and tag names are the same sink: `github.ref_name` obeys exactly
        the rules `github.base_ref` does, so pinning only the name the review
        happened to cite would leave the defect a second way back in.
        """
        # Имя ветки прогона-источника приходит из того же класса значений:
        # его выбирает тот, кто может завести ветку или тег.
        refs = (
            "github.base_ref",
            "github.ref_name",
            "github.head_ref",
            "github.event.workflow_run.head_branch",
        )
        scanned = 0
        # GitHub accepts either extension, so a guard that scans one of them
        # leaves the other as a blind spot.
        for workflow in sorted((*WORKFLOWS_DIR.glob("*.yml"), *WORKFLOWS_DIR.glob("*.yaml")), key=lambda path: path.name):
            for job_id, found in jobs(load(workflow)).items():
                for index, step in enumerate(steps(found)):
                    if "run" not in step:
                        continue
                    scanned += sum(1 for line in step["run"].splitlines() if line.strip())
                    # Скрипт видит только то, что GitHub подставил: `${{ }}` в
                    # `run:` — единственное место, где данные становятся кодом.
                    for expression in re.findall(r"\$\{\{(.*?)\}\}", step["run"], re.S):
                        context = next((ref for ref in refs if ref in expression), None)
                        with self.subTest(workflow=workflow.name, job=job_id, step=index):
                            self.assertIsNone(
                                context,
                                f"{context} is interpolated into a run block; bind it "
                                'to an env variable and read it as "$NAME"',
                            )

        # A scanner that silently matched nothing would pass this test forever.
        # The workflows have far more shell than this.
        self.assertGreater(scanned, 50)

    def test_rust_jobs_run_the_full_matrix_for_any_rust_change(self) -> None:
        source = job(self.release, "test-python")
        platforms = job(self.release, "test-rust-platforms")

        self.assertNotIn("cargo test", script(source))
        self.assertEqual(steps_using(source, "dtolnay/rust-toolchain"), [])
        # Список раннеров считает classify-changes: Windows — только в ночном ярусе large.
        self.assertEqual(platforms["strategy"]["matrix"]["runner"], "${{ fromJSON(needs.classify-changes.outputs.runners) }}")
        for flag in ("rust_changed", "platform_changed", "toolchain_changed", "ci_changed"):
            with self.subTest(flag=flag):
                self.assertIn(f"needs.classify-changes.outputs.{flag} == 'true'", condition(platforms))
        # Форматирование от цели не зависит — оно в `guards`. Линт зависит:
        # `#[cfg]` решает, какие элементы существуют, поэтому clippy идёт на
        # каждом раннере матрицы, а его находки — в Code Scanning.
        self.assertNotIn("cargo fmt", script(platforms))
        self.assertIn("cargo fmt --all -- --check", script(job(self.release, "guards")))
        sarif = steps_using(platforms, "github/codeql-action/upload-sarif")[0]
        self.assertEqual(sarif["with"]["category"], "clippy-${{ matrix.runner }}")
        self.assertEqual(needs(platforms), ["classify-changes", "guards"])
        # Подпись и план выгружаются раньше clippy: раннер, упавший на линте,
        # оставляет подпись, и его тесты не исчезают из отчёта.
        order = [index for index, step in enumerate(steps(platforms)) if "--plan-only" in step.get("run", "") or "cargo clippy" in step.get("run", "")]
        self.assertEqual(len(order), 2)
        plan_index, clippy_index = order
        self.assertIn("--plan-only", steps(platforms)[plan_index]["run"])
        self.assertLess(plan_index, clippy_index)
        # Любая правка Rust гоняет Rust-джобу; отдельной джобы на одном раннере нет.
        self.assertNotIn("test-rust-primary", jobs(self.release))
        # Команда линта закреплена дословно: `-D warnings` красит джобу, JSON
        # идёт в SARIF, и убрать одно из двух молча не выйдет.
        clippy = next(text for text in scripts(platforms) if "cargo clippy" in text)
        self.assertEqual(
            normalized(clippy),
            "set -o pipefail cargo clippy --workspace --all-targets --all-features"
            " --message-format=json -- -D warnings \\ | clippy-sarif | tee clippy.sarif | sarif-fmt",
        )

    def test_package_contour_and_pr_smoke_do_not_publish_release_assets(self) -> None:
        build = condition(job(self.release, "build-tools"))
        probe = condition(job(self.release, "probe-thin-bootstrap"))
        publish = condition(job(self.release, "publish-release-assets"))

        self.assertIn("needs.classify-changes.outputs.release_required == 'true'", build)
        self.assertIn("needs.classify-changes.outputs.ci_changed == 'true'", build)
        # Сборка и холодный старт сняты с pull request и с push в ветку: там они
        # не давали прослеживаемости, а гейт красили. Тег и ручной запуск их
        # сохраняют.
        self.assertIn("(github.event_name == 'workflow_dispatch' || startsWith(github.ref, 'refs/tags/'))", build)
        self.assertNotIn("github.event_name != 'pull_request'", build)
        self.assertIn("github.event_name == 'workflow_dispatch'", probe)
        self.assertNotIn("github.event_name == 'pull_request'", probe)
        self.assertIn("startsWith(github.ref, 'refs/tags/')", publish)

    def test_release_line_push_is_the_gate_the_site_reports_from(self) -> None:
        """Push в релизную линию гоняет все тесты: очереди там нет, отсюда сайт берёт отчёт линии."""
        push = triggers(self.release)["push"]

        self.assertEqual(push["branches"], ["main", "release-v*"])
        self.assertEqual(push["tags"], ["v*"])

    def test_main_push_after_the_queue_only_refreshes_the_dependency_cache(self) -> None:
        """Дерево `main` проверила очередь: push в него тестов не гоняет.

        Rust-джоба на нём поднимается только ради кэша зависимостей, который
        pull request читают лишь с ветки по умолчанию, и только когда сменился
        его ключ (toolchain) или сам конвейер. Наборы Python кэша не пишут и
        на push в `main` не идут. Диапазон push классифицируется по прежней
        вершине, а не силой полного контура.
        """
        main_push = "(github.event_name == 'push' && github.ref == 'refs/heads/main')"
        python = job(self.release, "test-python")
        platforms = job(self.release, "test-rust-platforms")
        classify = job(self.release, "classify-changes")

        self.assertEqual(normalized(python["if"]), "${{ !" + main_push + " }}")
        rust = normalized(condition(platforms))
        self.assertIn(main_push + " && ( needs.classify-changes.outputs.toolchain_changed == 'true' || needs.classify-changes.outputs.ci_changed == 'true' )", rust)
        self.assertIn("!" + main_push + " && ( needs.classify-changes.outputs.rust_changed == 'true'", rust)

        scope = next(step for step in steps(classify) if step.get("id") == "scope")
        self.assertEqual(normalized(scope["env"]["MAIN_PUSH"]), "${{ " + main_push.strip("()") + " }}")
        self.assertEqual(scope["env"]["PUSH_BEFORE"], "${{ github.event.before }}")
        self.assertIn("!" + main_push, scope["env"]["FORCE_FULL"])
        self.assertIn('git diff --name-only "$PUSH_BEFORE" "$GITHUB_SHA"', scope["run"])
        # Прежней вершины может не быть: тогда полный контур, а не пустой диапазон.
        self.assertIn('git cat-file -e "$PUSH_BEFORE^{commit}"', scope["run"])

    def test_release_assessment_uses_affected_mechanism_contour(self) -> None:
        assessment = job(self.release, "release-assessment")

        self.assertEqual(needs(assessment), ["classify-changes", "build-tools"])
        self.assertIn("needs.classify-changes.outputs.assessment_required == 'true'", condition(assessment))
        self.assertIn("needs.build-tools.result == 'success'", condition(assessment))

    def test_release_assessment_uses_the_candidate_release_identity(self) -> None:
        assessment = job(self.release, "release-assessment")
        resolve = step_named(assessment, "Resolve the release tag for non-tag builds")

        self.assertEqual(
            normalized(assessment["env"]["RELEASE_TAG"]),
            "${{ github.event_name == 'push' && startsWith(github.ref, 'refs/tags/') && github.ref_name || '' }}",
        )
        self.assertEqual(condition(resolve), "${{ env.RELEASE_TAG == '' }}")
        self.assertIn('echo "RELEASE_TAG=v${version}" >> "$GITHUB_ENV"', resolve["run"])
        self.assertIn('--release-tag "$RELEASE_TAG"', script(assessment))
        self.assertNotIn("RELEASE_REF", assessment["env"])

    def test_only_tag_pushes_enable_release_behavior(self) -> None:
        for job_id in ("build-tools", "package-thin"):
            with self.subTest(job_id=job_id):
                self.assertTrue(
                    any(
                        "github.event_name == 'push' && startsWith(github.ref, 'refs/tags/')" in expression
                        for expression in expressions(job(self.release, job_id))
                    ),
                    f"{job_id}: тег отличается от push в ветку только в этом выражении",
                )
        for job_id in ("publish-release-assets", "smoke-thin-plugin", "verify-published-assets"):
            with self.subTest(job_id=job_id):
                gate = condition(job(self.release, job_id))
                self.assertIn("github.event_name == 'push'", gate)
                self.assertIn("startsWith(github.ref, 'refs/tags/')", gate)

    def test_conditional_pipeline_breaks_transitive_skip_propagation(self) -> None:
        dependencies = {
            "package-thin": ("needs.build-tools.result == 'success'",),
            "probe-thin-bootstrap": ("needs.package-thin.result == 'success'",),
            "release-assessment": ("needs.build-tools.result == 'success'",),
            "publish-release-assets": ("needs.build-tools.result == 'success'",),
            "smoke-thin-plugin": (
                "needs.package-thin.result == 'success'",
                "needs.publish-release-assets.result == 'success'",
            ),
            "verify-published-assets": (
                "needs.package-thin.result == 'success'",
                "needs.publish-release-assets.result == 'success'",
            ),
            "promote-opencode-npm": (
                "needs.publish-opencode-npm.result == 'success'",
                "needs.smoke-opencode-windows.result == 'success'",
            ),
        }

        for job_id, dependency_results in dependencies.items():
            with self.subTest(job_id=job_id):
                gate = condition(job(self.release, job_id))
                self.assertIn("always()", gate)
                for dependency_result in dependency_results:
                    self.assertIn(dependency_result, gate)

    def test_javascript_actions_use_node24_compatible_majors(self) -> None:
        release = RELEASE_WORKFLOW.read_text(encoding="utf-8")
        combined = "".join(path.read_text(encoding="utf-8") for path in (RELEASE_WORKFLOW, PUBLISH_WORKFLOW, NIGHTLY_WORKFLOW, PAGES_WORKFLOW))

        self.assertRegex(combined, pinned("actions/checkout", "v7"))
        self.assertRegex(release, pinned("actions/setup-python", "v7"))
        self.assertRegex(release, pinned("actions/cache", "v6"))
        self.assertRegex(release, pinned("actions/upload-artifact", "v7"))
        self.assertRegex(release, pinned("actions/download-artifact", "v8"))
        self.assertRegex(release, pinned("softprops/action-gh-release", "v3"))
        self.assertRegex(release, pinned("github/codeql-action/upload-sarif", "v4"))
        for stale in (
            "actions/checkout@v4",
            "actions/setup-python@v5",
            "actions/cache@v4",
            "actions/upload-artifact@v4",
            "actions/download-artifact@v4",
            "softprops/action-gh-release@v2",
            "github/codeql-action/upload-sarif@v3",
        ):
            with self.subTest(stale=stale):
                self.assertNotIn(stale, combined)

    def test_heavy_and_external_jobs_have_timeouts(self) -> None:
        expected_release_timeouts = {
            "classify-changes": 10,
            "guards": 15,
            "test-python": 90,
            # Час всем воротам, три — ночному `large`: там Windows гоняет весь
            # набор вместе с контрактом ReceiptLedger.
            "test-rust-platforms": "${{ github.event_name == 'workflow_dispatch' && inputs.profile == 'large' && 180 || 60 }}",
            "build-tools": 90,
            "package-thin": 30,
            "probe-thin-bootstrap": 30,
            "release-assessment": 60,
            "publish-release-assets": 15,
            "smoke-thin-plugin": 30,
            "verify-published-assets": 15,
            "publish-opencode-npm": 15,
            "smoke-opencode-windows": 40,
            "smoke-opencode-linux": 40,
            "promote-opencode-npm": 10,
            "unica-ci": 5,
        }
        for job_id, minutes in expected_release_timeouts.items():
            with self.subTest(job_id=job_id):
                self.assertEqual(job(self.release, job_id).get("timeout-minutes"), minutes)

        expected_publish_timeouts = {
            "stage": 20,
            "tag": 10,
            "verify-fresh-install": 30,
            "verify-upgrade": 30,
            "promote": 10,
        }
        for job_id, minutes in expected_publish_timeouts.items():
            with self.subTest(job_id=job_id):
                self.assertEqual(job(self.publish, job_id).get("timeout-minutes"), minutes)

    def test_registry_guards_run_in_the_source_contour(self) -> None:
        """Стражи реестра идут в `guards` первыми, наборы Python — в `test-python` за ними."""
        guards = job(self.release, "guards")
        python = job(self.release, "test-python")

        self.assertIn("python -m py_compile scripts/arch/*.py tests/arch/*.py", script(guards))
        self.assertIn("python scripts/arch/registry.py --check", script(guards))
        self.assertIn('python scripts/ci/run-tests.py --profile "$GATE_PROFILE" --ecosystem python --suite "$SUITE" --only-size "$LANE" --results', script(python))
        self.assertEqual(needs(python), ["classify-changes", "guards"])
        # Матрицу джоб Python считает шов по воротам; джоба знает набор и полосу.
        self.assertEqual(python["strategy"]["matrix"]["include"], "${{ fromJSON(needs.classify-changes.outputs.python_matrix) }}")
        self.assertEqual(python["env"]["SUITE"], "${{ matrix.suite }}")
        self.assertEqual(python["env"]["LANE"], "${{ matrix.lane }}")
        self.assertEqual(python["name"], "Python tests (${{ matrix.slug }})")
        classify = job(self.release, "classify-changes")
        self.assertEqual(classify["outputs"]["python_matrix"], "${{ steps.python-matrix.outputs.python_matrix }}")
        self.assertIn('run-tests.py --profile "$GATE_PROFILE" --python-matrix', step_by_id(classify, "python-matrix")["run"])
        for run_line in [step["run"] for step in steps(python) if "run-tests.py" in step.get("run", "")]:
            self.assertIn('--suite "$SUITE" --only-size "$LANE"', run_line)
        self.assertEqual([upload["name"] for upload in uploads(python)], ["plan-python-${{ matrix.slug }}", "results-python-${{ matrix.slug }}"])
        # План выгружается до тестов, как у Rust.
        plan_index = next(index for index, step in enumerate(steps(python)) if "--plan-only" in step.get("run", ""))
        run_index = next(index for index, step in enumerate(steps(python)) if "run-tests.py" in step.get("run", "") and "--plan-only" not in step["run"])
        self.assertLess(plan_index, run_index)

    def test_gate_profile_follows_the_event_not_the_job(self) -> None:
        """Ворота → профиль: pull request — `pr`, push в ветку — `main`, тег — `release`."""
        self.assertEqual(
            normalized(self.release["env"]["GATE_PROFILE"]),
            "${{ github.event_name == 'pull_request' && 'pr' || github.event_name == 'merge_group' && 'queue' || "
            "github.event_name == 'workflow_dispatch' && inputs.profile || "
            "(github.event_name == 'push' && startsWith(github.ref, 'refs/tags/')) && 'release' || 'main' }}",
        )
        # Очередь слияния: конвейер отвечает на merge_group, иначе очередь ждёт вечно.
        self.assertEqual(triggers(self.release)["merge_group"], {"types": ["checks_requested"]})
        self.assertNotIn("run-tests.py --profile all", all_scripts(self.release))

    def test_line_rides_in_the_signature_and_tags_resolve_to_a_release_line(self) -> None:
        """Линия прогона — из resolve-line.py, в подписи результатов и плана."""
        classify = job(self.release, "classify-changes")

        self.assertIn(
            'python scripts/ci/resolve-line.py --ref-type "$REF_TYPE" --ref-name "$REF_NAME" --sha "$GITHUB_SHA"',
            script(classify),
        )
        self.assertEqual(classify["outputs"]["line"], "${{ steps.line.outputs.line }}")
        # Подпись линии: план и прогон Rust, план и прогон Python.
        self.assertEqual(4, all_scripts(self.release).count('--line "$RUN_LINE"'))
        signed_jobs = [
            job_id
            for job_id, found in jobs(self.release).items()
            if (found.get("env") or {}).get("RUN_LINE") == "${{ needs.classify-changes.outputs.line }}"
        ]
        self.assertEqual(sorted(signed_jobs), ["test-python", "test-rust-platforms"])
        # План едет каталогом вместе с подписью, а не одним файлом.
        for found in jobs(self.release).values():
            for upload in uploads(found):
                self.assertNotEqual(upload.get("path"), ".build/results/plan.json")

    def test_nightly_dispatches_the_manual_contour_with_the_large_profile(self) -> None:
        """Ночь перечисляет и запускает ручной контур сборки на линии; Windows — только там."""
        lines = job(self.nightly, "lines")
        classify = job(self.release, "classify-changes")
        platforms = job(self.release, "test-rust-platforms")

        self.assertIn("schedule", triggers(self.nightly))
        # Круглые минуты GitHub исполняет с наибольшим опозданием.
        minute = triggers(self.nightly)["schedule"][0]["cron"].split()[0]
        self.assertNotIn(minute, ("0", "30"))
        # Ручной и ночной запуск идут своей группой: push их не вытесняет.
        self.assertIn("format('-dispatch-{0}', inputs.profile)", normalized(self.release["concurrency"]["group"]))
        self.assertEqual(lines["permissions"].get("actions"), "write")
        self.assertIn("--dispatch --follow .build/large", script(lines))
        self.assertEqual([upload["name"] for upload in uploads(lines)], ["results-nightly"])
        for step in steps_using(lines, "actions/checkout"):
            self.assertNotIn("ref", step.get("with") or {})
        self.assertEqual(triggers(self.release)["workflow_dispatch"]["inputs"]["profile"]["options"], ["main", "large"])
        self.assertIn("github.event_name == 'workflow_dispatch' && inputs.profile", normalized(self.release["env"]["GATE_PROFILE"]))
        self.assertEqual(classify["outputs"]["runners"], "${{ steps.runners.outputs.runners }}")
        self.assertIn('runners=["ubuntu-latest", "macos-14", "windows-latest"]', script(classify))
        # Две полосы: pull request — ubuntu, полная матрица — в очереди, на push
        # и по кнопке; метка ci:full возвращает её на pull request.
        runners = step_by_id(classify, "runners")
        self.assertIn('runners=["ubuntu-latest"]', runners["run"])
        self.assertIn('runners=["ubuntu-latest", "macos-14"]', runners["run"])
        self.assertEqual(
            normalized(runners["env"]["FULL_MATRIX"]),
            "${{ github.event_name != 'pull_request' || contains(github.event.pull_request.labels.*.name, 'ci:full') }}",
        )
        self.assertEqual(platforms["strategy"]["matrix"]["runner"], "${{ fromJSON(needs.classify-changes.outputs.runners) }}")
        self.assertEqual(platforms["defaults"]["run"]["shell"], "bash")
        # Кэш зависимостей пишут push в ветку и ручной запуск; pull request и очередь читают.
        cache = steps_using(platforms, "Swatinem/rust-cache")[0]
        assert_pinned(self, RELEASE_WORKFLOW, cache, "v2")
        self.assertEqual(
            normalized(cache["with"]["save-if"]),
            "${{ github.ref_type == 'branch' && (github.event_name == 'push' || github.event_name == 'workflow_dispatch') }}",
        )
        assert_pinned(self, RELEASE_WORKFLOW, steps_using(platforms, "actions/setup-python")[0], "v7")
        # Консоль Windows — cp1252; сбой Windows виден, но упаковку ночи не блокирует.
        self.assertEqual(platforms["env"]["PYTHONUTF8"], "1")
        self.assertEqual(normalized(platforms["continue-on-error"]), "${{ matrix.runner == 'windows-latest' }}")
        self.assertFalse((WORKFLOWS_DIR / "unica-large.yml").exists())

    def test_pages_take_results_from_the_queue_red_runs_and_the_nightly(self) -> None:
        """Отчёт `main` приходит с очереди; красный прогон — тоже результат; ночь и тег — тоже источники."""
        on = triggers(self.pages)
        build = job(self.pages, "build")

        self.assertEqual(on["workflow_run"]["workflows"], ["Build Unica Codex Plugin", "Unica Nightly"])
        self.assertEqual(on["workflow_run"]["branches"], ["main", "gh-readonly-queue/main/*", "release-v*", "v*"])
        self.assertIn("github.event.workflow_run.conclusion == 'failure'", condition(build))
        self.assertIn("github.event.workflow_run.event == 'merge_group'", condition(build))
        # Push в `main` тестов не гоняет и источником не бывает; push в релизную линию и тег — бывают.
        self.assertIn("(github.event.workflow_run.event == 'push' && github.event.workflow_run.head_branch != 'main')", normalized(condition(build)))
        self.assertIn("github.event.workflow_run.event == 'schedule'", condition(build))
        self.assertIn("github.event.workflow_run.head_repository.full_name == github.repository", condition(build))
        # Критерии конвейера сайт больше не считает: страница снята 08.09.2026.
        self.assertNotIn("--metrics", script(build))
        self.assertFalse((REPO_ROOT / "docs" / "pages" / "pipeline.html").exists())
        # Очередь даёт по прогону на каждый pull request партии, и деплои идут
        # друг за другом: неудачный деплой повторяется один раз после паузы.
        deploy = job(self.pages, "deploy")
        attempts = steps_using(deploy, "actions/deploy-pages")
        self.assertEqual(len(attempts), 2)
        self.assertTrue(attempts[0].get("continue-on-error"))
        self.assertEqual(normalized(attempts[1]["if"]), "steps.deployment.outcome == 'failure'")
        # Прямой триггер push снят: в очереди без отмены он заменял бы ожидающий
        # прогон с результатами, и они не доехали бы до сайта.
        self.assertNotIn("push", on)
        for found in jobs(self.pages).values():
            for expression in expressions(found):
                self.assertNotIn("github.event_name == 'push'", expression)
        self.assertIn("jobs?per_page=100", script(build))

    def test_guards_ship_findings_to_code_scanning_not_the_gate(self) -> None:
        """Находка линтера — не исход теста: SARIF в Code Scanning, гейт не краснеет."""
        guards = job(self.release, "guards")
        sarif = steps_using(guards, "github/codeql-action/upload-sarif")[0]

        self.assertIn("zizmor@1.30.0", [step["with"]["tool"] for step in steps_using(guards, "taiki-e/install-action")])
        self.assertIn("zizmor --config .github/zizmor.yml --format sarif --no-exit-codes .github/workflows > zizmor.sarif", script(guards))
        assert_pinned(self, RELEASE_WORKFLOW, sarif, "v4")
        self.assertEqual(sarif["with"]["category"], "zizmor")
        self.assertEqual(guards["permissions"].get("security-events"), "write")
        # Токен pull request из форка писать в Code Scanning не вправе.
        self.assertIn("github.event.pull_request.head.repo.full_name == github.repository", condition(sarif))

    def test_platform_build_uses_exact_cargo_cache_and_reports_outcome(self) -> None:
        build = job(self.release, "build-tools")
        step_by_id(build, "rust-toolchain")
        cache = step_by_id(build, "cargo-cache")

        self.assertIs(cache.get("continue-on-error"), True)
        assert_pinned(self, RELEASE_WORKFLOW, cache, "v6")
        self.assertEqual(cache["with"]["path"], ".build/tool-work/${{ matrix.target }}/cargo-target")
        self.assertEqual(
            normalized(cache["with"]["key"]),
            "cargo-${{ runner.os }}-${{ matrix.target }}-${{ steps.rust-toolchain.outputs.cachekey }}-${{ hashFiles('Cargo.lock') }}",
        )
        self.assertNotIn("restore-keys", cache["with"])
        first_build = next(index for index, step in enumerate(steps(build)) if "scripts/ci/build-unica-tools.py" in step.get("run", ""))
        self.assertLess(steps(build).index(cache), first_build)
        self.assertIn("--metrics-file", script(build))
        report = step_named(build, "Report Cargo cache and build metrics")
        self.assertEqual(condition(report), "always()")
        self.assertIn("steps.cargo-cache.outcome", " ".join(expressions(build)))
        self.assertIn("steps.cargo-cache.outputs.cache-hit", " ".join(expressions(build)))
        for outcome in ("exact-hit", "miss", "error"):
            with self.subTest(outcome=outcome):
                self.assertIn(outcome, report["run"])
        self.assertIn("cargoBuildSeconds", script(build))
        self.assertIn("archiveDownloadSeconds", script(build))
        self.assertIn("RLM archive download duration", script(build))
        self.assertIn("GITHUB_STEP_SUMMARY", script(build))

    def test_runtime_matrix_builds_verifies_and_exports_narrow_artifacts(self) -> None:
        build = job(self.release, "build-tools")
        names = [upload.get("name") for upload in uploads(build)]
        paths = [upload.get("path") for upload in uploads(build)]

        self.assertEqual({target for target, _ in targets(build)}, {"darwin-arm64", "linux-x64", "win-x64"})
        self.assertNotIn("package-runtime", jobs(self.release))
        self.assertFalse(any("unica-tools-" in value for value in strings(self.release)))
        for tool in ("scripts/ci/build-unica-tools.py", "scripts/ci/package-unica-runtime.py", "scripts/ci/verify-release-assets.py"):
            self.assertIn(tool, script(build))
        self.assertIn('--target "${{ matrix.target }}"', script(build))
        for name in ("unica-runtime-metadata-${{ matrix.target }}", "unica-bootstrap-${{ matrix.target }}", "unica-runtime-${{ matrix.target }}"):
            with self.subTest(name=name):
                self.assertIn(name, names)
        # Узость здесь — про цель, а не про артефакт: разрез поставки дал по
        # архиву на артефакт, и выгрузка обязана нести их все.
        for path in (
            ".build/runtime-assets/${{ matrix.target }}/*-runtime-${{ matrix.target }}.json",
            ".build/runtime-assets/${{ matrix.target }}/*-runtime-${{ matrix.target }}.tar.gz",
            ".build/bootstrap-artifacts/${{ matrix.target }}",
        ):
            with self.subTest(path=path):
                self.assertTrue(any(path in uploaded for uploaded in paths), path)
        self.assertIn("matrix.target == 'linux-x64'", " ".join(expressions(build)))
        self.assertIn("startsWith(github.ref, 'refs/tags/')", " ".join(expressions(build)))
        self.assertGreaterEqual(sum(1 for upload in uploads(build) if upload.get("retention-days") == 1), 3)

    def test_mcp_smoke_runs_against_extracted_deterministic_runtime(self) -> None:
        build = job(self.release, "build-tools")
        smoke = step_named(build, "Smoke packaged Unica MCP")

        self.assertLess(step_index(build, "Package deterministic runtime"), step_index(build, "Extract deterministic runtime for MCP smoke"))
        self.assertLess(step_index(build, "Extract deterministic runtime for MCP smoke"), step_index(build, "Smoke packaged Unica MCP"))
        self.assertIn('runtime_root=".build/runtime-smoke/${{ matrix.target }}"', script(build))
        self.assertIn(
            'tar -xzf ".build/runtime-assets/${{ matrix.target }}/unica-runtime-${{ matrix.target }}.tar.gz"',
            script(build),
        )
        self.assertIn('--plugin-root "$runtime_root"', script(build))
        self.assertIn('executable="$runtime_root/bin/${{ matrix.target }}/unica"', script(build))
        self.assertEqual(smoke.get("timeout-minutes"), 3)
        self.assertIn("--total-timeout-seconds 120", smoke["run"])

    def test_thin_payload_downloads_only_metadata_and_bootstrap(self) -> None:
        thin = job(self.release, "package-thin")
        patterns = [download.get("pattern") for download in downloads(thin)]
        marketplace = next(upload for upload in uploads(thin) if upload.get("name") == "unica-thin-marketplace")

        self.assertEqual(needs(thin), ["build-tools"])
        self.assertIn("unica-runtime-metadata-*", patterns)
        self.assertIn("unica-bootstrap-*", patterns)
        self.assertNotIn("unica-tools-*", patterns)
        self.assertNotIn("unica-runtime-*", patterns)
        self.assertIn("scripts/ci/package-unica-plugin.py", script(thin))
        self.assertIn("--runtime-metadata-root", script(thin))
        self.assertIn("--bootstrap-root", script(thin))
        self.assertIs(marketplace.get("include-hidden-files"), True)
        self.assertEqual(marketplace.get("retention-days"), 90)
        self.assertNotIn("unica-codex-marketplace-${{ matrix.target }}", list(strings(self.release)))

    def test_intermediate_non_marketplace_artifacts_expire_after_one_day(self) -> None:
        assessment = job(self.release, "release-assessment")

        self.assertEqual([(upload["name"], upload["retention-days"]) for upload in uploads(assessment)], [("unica-release-assessment", 1)])

    def test_packaged_bootstrap_is_smoked_on_every_supported_host(self) -> None:
        probe = job(self.release, "probe-thin-bootstrap")
        smoke = job(self.release, "smoke-thin-plugin")
        expected_targets = {
            "linux-x64": "ubuntu-latest",
            "win-x64": "windows-2022",
            "darwin-arm64": "macos-14",
        }

        self.assertEqual(dict(targets(probe)), expected_targets)
        self.assertEqual(dict(targets(smoke)), expected_targets)
        step_named(probe, "Probe packaged bootstrap through the downloader")
        step_named(smoke, "Smoke packaged bootstrap against published runtime")
        self.assertIn("scripts/ci/smoke-unica-bootstrap.py", script(smoke))
        self.assertIn(" --plugin-root .build/thin/plugins/unica", script(smoke))
        self.assertIn(' --target "${{ matrix.target }}"', script(smoke))
        self.assertEqual(needs(probe), ["package-thin"])
        self.assertEqual(needs(smoke), ["package-thin", "publish-release-assets"])
        self.assertIn("--expect-download-failure", script(probe))

    def test_v080_source_release_has_no_executable_legacy_migration_jobs(self) -> None:
        for job_id in ("legacy-migration-preflight", "verify-installers", "installer"):
            with self.subTest(job_id=job_id):
                self.assertNotIn(job_id, jobs(self.release))
        for marker in ("test-unica-upgrade.ps1", "unica-installer", "install-unica.sh", "install-unica.ps1"):
            with self.subTest(marker=marker):
                self.assertFalse(any(marker in value for value in strings(self.release)), marker)

    def test_source_repo_has_no_manual_or_scheduled_full_migration_workflow(self) -> None:
        violations: dict[str, list[str]] = {}
        workflows = sorted((*WORKFLOWS_DIR.glob("*.yml"), *WORKFLOWS_DIR.glob("*.yaml")), key=lambda path: path.name)

        for workflow in workflows:
            text = workflow.read_text(encoding="utf-8")
            markers = [marker for marker in ("-Mode Full", "legacy-migration-full") if marker in text]
            if markers:
                violations[workflow.name] = markers

        self.assertFalse(LEGACY_WORKFLOW.exists())
        self.assertNotIn("unica-legacy-migration.yml", RELEASE_WORKFLOW.read_text(encoding="utf-8"))
        self.assertEqual({}, violations, f"source workflows own full migration policy: {violations}")

    def test_release_assets_are_published_without_pages_dependency_and_redownloaded(self) -> None:
        publish = job(self.release, "publish-release-assets")
        verify = job(self.release, "verify-published-assets")
        release = steps_using(publish, "softprops/action-gh-release")[0]

        self.assertNotIn("publish-assessment-pages", jobs(self.release))
        self.assertEqual(needs(publish), ["build-tools"])
        assert_pinned(self, RELEASE_WORKFLOW, release, "v3")
        self.assertIn("unica-runtime-*.tar.gz", release["with"]["files"])
        self.assertIn("unica-runtime-*.json", release["with"]["files"])
        self.assertFalse(any("install-unica" in value for value in strings(publish)))
        self.assertIn("gh release download", script(verify))
        self.assertIn("verify-release-assets.py", script(verify))

    def test_release_notes_are_generated_without_repository_docs(self) -> None:
        release = steps_using(job(self.release, "publish-release-assets"), "softprops/action-gh-release")[0]

        self.assertIs(release["with"].get("generate_release_notes"), True)
        self.assertNotIn("body_path", release["with"])
        self.assertFalse(any("docs/releases" in value for value in strings(self.release)))

    def test_assessment_is_independent_from_runtime_publication(self) -> None:
        assessment = job(self.release, "release-assessment")
        upload = steps_using(assessment, "actions/upload-artifact")[0]

        self.assertIn("always()", condition(assessment))
        self.assertIn("unica-runtime-linux-x64.tar.gz", "\n".join(strings(assessment)))
        self.assertNotIn("publish-release-assets", needs(assessment))
        self.assertFalse(any("publish-release-assets" in value for value in strings(assessment)))
        self.assertEqual(upload["with"]["name"], "unica-release-assessment")
        self.assertEqual(condition(upload), "always()")

    def test_pr_permissions_are_read_only_and_cross_repo_write_uses_secret(self) -> None:
        self.assertEqual(self.release["permissions"], {"contents": "read"})
        self.assertEqual(self.publish["permissions"], {"contents": "read"})
        tokens = {job_id: (found.get("env") or {}).get("GH_TOKEN") for job_id, found in jobs(self.publish).items()}
        self.assertIn("${{ secrets.UNICA_MARKETPLACE_TOKEN }}", tokens.values())
        for job_id, found in jobs(self.publish).items():
            with self.subTest(job_id=job_id):
                self.assertNotEqual((found.get("permissions") or {}).get("pull-requests"), "write")

    def test_cross_repository_push_configures_git_credentials(self) -> None:
        self.assertGreaterEqual(all_scripts(self.publish).count("gh auth setup-git"), 2)

    def test_the_build_names_its_own_core_release_repository(self) -> None:
        """Выпуск зовёт упаковку с адресом ядра этого репозитория.

        Умолчание упаковщика — upstream-адрес; молчаливое умолчание в форке
        собрало бы манифест, указывающий на чужой выпуск. Адрес обязана
        назвать сама сборка (CTR.PKG.CORE-PROVENANCE-SELECTABLE).
        """
        workflow = RELEASE_WORKFLOW.read_text(encoding="utf-8")

        self.assertIn(
            "CORE_RELEASE_REPOSITORY: https://github.com/${{ github.repository }}",
            workflow,
        )
        for job_id in ("build-tools", "package-thin"):
            block = job_block(workflow, job_id)
            self.assertTrue(block, f"job {job_id} not found")
            self.assertIn('"$CORE_RELEASE_REPOSITORY"', block)
            self.assertIn("--core-release-repository", block)

    def test_the_bootstrap_proves_its_compiled_core_repository(self) -> None:
        """Сборка доказывает compile-time seam происхождения ядра.

        Тестовый бинарь компилируется уже с `UNICA_BOOTSTRAP_CORE_REPOSITORY`,
        названным сборкой, и обычный `RuntimeManifest::validate` следует
        запечённому владельцу, а не значению, подсунутому тестом в рантайме.
        """
        workflow = RELEASE_WORKFLOW.read_text(encoding="utf-8")
        build = job_block(workflow, "build-tools")
        self.assertTrue(build, "job build-tools not found")

        proof_steps = [
            step
            for step in build.split("- name:")
            if "cargo test -p unica-bootstrap --test manifest_contract" in step
        ]
        self.assertEqual(
            len(proof_steps), 1, "exactly one compiled-repository proof step"
        )
        step = proof_steps[0]
        self.assertIn(
            'UNICA_BOOTSTRAP_CORE_REPOSITORY="$CORE_RELEASE_REPOSITORY"', step
        )
        self.assertIn(
            "ordinary_validation_uses_the_repository_compiled_into_the_bootstrap",
            step,
        )
        self.assertIn("--exact", step)
        self.assertIn("if: matrix.target == 'linux-x64'", step)

    def test_opencode_npm_publication_is_fork_gated_and_trusted(self) -> None:
        """npm-этапирование — только теговый пуш форка, после проверенных ассетов.

        Стадия публикует кандидата короткоживущим OIDC-токеном trusted
        publishing под служебным dist-tag: долгоживущий npm-токен у publish
        job не появляется (INV.PKG.NPM-PUBLICATION-FORK-TAG-OIDC).
        Перемещение `latest`/`next` выполняет отдельный promotion job.
        """
        workflow = RELEASE_WORKFLOW.read_text(encoding="utf-8")
        block = job_block(workflow, "publish-opencode-npm")

        self.assertTrue(block, "job publish-opencode-npm not found")
        self.assertIn("needs: [package-thin, verify-published-assets]", block)
        self.assertIn("github.event_name == 'push'", block)
        self.assertIn("startsWith(github.ref, 'refs/tags/')", block)
        self.assertIn("github.repository == 'apshendev/unica'", block)
        self.assertIn("needs.package-thin.result == 'success'", block)
        self.assertIn("needs.verify-published-assets.result == 'success'", block)
        self.assertIn("id-token: write", block)
        self.assertIn("package-unica-opencode.py", block)
        self.assertIn("publish-unica-opencode.py", block)
        self.assertNotIn("NODE_AUTH_TOKEN", block)
        self.assertNotIn("NPM_PROMOTION_TOKEN", block)
        self.assertNotIn("secrets.", block)
        # Promotion — отдельная работа: публикация не двигает dist-tag.
        self.assertTrue(
            job_block(workflow, "promote-opencode-npm"),
            "job promote-opencode-npm not found",
        )
        # Литерал владельца одинаков в workflow, скрипте публикации и гейте.
        publish_script = (
            REPO_ROOT / "scripts" / "ci" / "publish-unica-opencode.py"
        ).read_text(encoding="utf-8")
        gate_script = (REPO_ROOT / "scripts" / "ci" / "evaluate-ci-gate.py").read_text(
            encoding="utf-8"
        )
        self.assertIn('FORK_REPOSITORY = "apshendev/unica"', publish_script)
        self.assertIn('FORK_REPOSITORY = "apshendev/unica"', gate_script)

    def test_opencode_consumer_smoke_gates_the_release(self) -> None:
        """Реальный потребитель пола 1.18.22 проверяет npm-кандидата.

        Windows x64 — блокирующий: без него выпуск не зелёный. Linux x64 —
        best effort: `continue-on-error`, но его падение видно в отчёте.
        OpenCode-потребителя под macOS нет, а существующие Codex/Claude
        проверки macOS не тронуты. Обе подкоманды верификатора получают
        установленный root пакета и target.
        """
        workflow = RELEASE_WORKFLOW.read_text(encoding="utf-8")
        windows = job_block(workflow, "smoke-opencode-windows")
        linux = job_block(workflow, "smoke-opencode-linux")

        for job_id, block, target in (
            ("smoke-opencode-windows", windows, "win-x64"),
            ("smoke-opencode-linux", linux, "linux-x64"),
        ):
            with self.subTest(job=job_id):
                self.assertTrue(block, f"job {job_id} not found")
                self.assertIn("needs: publish-opencode-npm", block)
                self.assertIn("github.repository == 'apshendev/unica'", block)
                self.assertIn("npm install -g opencode-ai@1.18.22", block)
                # Пол, не потолок: потребитель ставит ровно версию пола.
                self.assertNotIn("opencode-ai@latest", block)
                self.assertIn("opencode debug skill", block)
                self.assertIn("opencode mcp list", block)
                self.assertIn("smoke-opencode-consumer.py", block)
                # Потребитель изолирован вне checkout: каталог во временном
                # хранилище раннера, а не в рабочем дереве репозитория.
                self.assertNotIn(".build/consumer", block)
                self.assertIn(
                    "working-directory: ${{ runner.temp }}/opencode-consumer", block
                )
                # Обе подкоманды верификатора доказывают установленный root
                # пакета потребителя и target-специфичную раскладку bootstrap.
                installed_root = (
                    '"$RUNNER_TEMP/opencode-consumer/node_modules'
                    '/@apshendev/unica-opencode"'
                )
                self.assertEqual(2, block.count(installed_root))
                self.assertEqual(2, block.count(f"--target {target}"))
                self.assertIn('"$RUNNER_TEMP/opencode-consumer/skills.json"', block)
                self.assertIn('"$RUNNER_TEMP/opencode-consumer/mcp.txt"', block)
                # Сбор наблюдений mcp тоже отказоустойчиво закрыт: провал
                # `opencode mcp list` не должен прятаться за кодом tee.
                self.assertIn(
                    "set -euo pipefail",
                    block.split("opencode mcp list")[0].split("Collect mcp")[-1],
                )

        self.assertNotIn("continue-on-error", windows)
        self.assertIn("continue-on-error: true", linux)
        # Никакого OpenCode-потребителя под macOS.
        for job_id in ("smoke-opencode-darwin", "smoke-opencode-macos"):
            self.assertFalse(job_block(workflow, job_id))

    def test_the_consumer_installs_the_exact_registry_version(self) -> None:
        """Установка потребителя доказуема: npm ставит точную версию из реестра.

        `opencode plugin` не оставляет проверяемого пути `node_modules`, а
        checkout `plugins/unica` не доказывает содержимое публикации. Блок
        установки ставит пакет npm'ом с `--ignore-scripts` и подключает его
        абсолютным `file://` URI (INV.CI.OPENCODE-CONSUMER-INSTALLED-ROOT).
        """
        workflow = RELEASE_WORKFLOW.read_text(encoding="utf-8")

        for job_id in ("smoke-opencode-windows", "smoke-opencode-linux"):
            block = job_block(workflow, job_id)
            with self.subTest(job=job_id):
                self.assertTrue(block, f"job {job_id} not found")
                self.assertIn("npm install --ignore-scripts", block)
                self.assertIn('"@apshendev/unica-opencode@${version}"', block)
                self.assertIn("npm init -y", block)
                self.assertIn("pathToFileURL", block)
                self.assertIn("file://", block)
                # Установка идёт npm'ом из реестра, а не командой плагина:
                # checkout исходников не подменяет проверку публикации.
                self.assertNotIn('opencode plugin "', block)
                self.assertIn("node_modules/@apshendev/unica-opencode", block)

    def test_opencode_npm_publication_stages_smokes_then_promotes(self) -> None:
        """Контур npm-выпуска: staging → потребители → promotion.

        Publish job не двигает потребительские dist-tag и выгружает кандидата
        артефактом; smoke-потребители ставят его из реестра; promotion
        перемещает dist-tag только после зелёных Windows-проверок
        (DEC.2026-08-25.NPM-DIST-TAG-PROMOTION).
        """
        workflow = RELEASE_WORKFLOW.read_text(encoding="utf-8")
        publish = job_block(workflow, "publish-opencode-npm")
        promote = job_block(workflow, "promote-opencode-npm")

        self.assertTrue(publish, "job publish-opencode-npm not found")
        self.assertTrue(promote, "job promote-opencode-npm not found")

        # Publish: этапирует кандидата и не двигает потребительские теги.
        self.assertIn("id-token: write", publish)
        self.assertIn("contents: read", publish)
        self.assertNotIn("NPM_PROMOTION_TOKEN", publish)
        self.assertNotIn("NODE_AUTH_TOKEN", publish)
        self.assertNotIn("dist-tag", publish)
        self.assertIn("name: Stage OpenCode npm candidate (staging)", publish)
        upload = publish[publish.index("actions/upload-artifact@v7") :]
        self.assertIn("name: opencode-npm-candidate", upload)
        self.assertIn("path: dist/npm", upload)
        self.assertIn("retention-days: 1", upload)
        self.assertIn("compression-level: 0", upload)

        # Promote: контракт работы.
        self.assertIn(
            "needs: [publish-opencode-npm, smoke-opencode-windows, smoke-opencode-linux]",
            promote,
        )
        self.assertIn("always()", promote)
        self.assertIn("needs.publish-opencode-npm.result == 'success'", promote)
        self.assertIn("needs.smoke-opencode-windows.result == 'success'", promote)
        # Linux в needs ждёт отчёта, но его результат выпуск не гейтит.
        self.assertNotIn("needs.smoke-opencode-linux.result", promote)
        self.assertIn("github.event_name == 'push'", promote)
        self.assertIn("startsWith(github.ref, 'refs/tags/')", promote)
        self.assertIn("github.repository == 'apshendev/unica'", promote)
        self.assertIn("permissions:", promote)
        self.assertIn("contents: read", promote)
        self.assertIn("environment: npm-promotion", promote)
        self.assertIn("timeout-minutes: 10", promote)
        self.assertNotIn("id-token", promote)
        self.assertNotIn("publish-unica-opencode.py", promote)

        # Порядок шагов promotion фиксирован: registry-url обязан прийти до
        # npm-вызова, артефакт — до скрипта, токен — только в шаге скрипта.
        steps = [
            line.strip()
            for line in promote.splitlines()
            if line.strip().startswith("- uses:") or line.strip().startswith("- name:")
        ]
        self.assertEqual(
            [
                "- uses: actions/checkout@v7",
                "- uses: actions/setup-python@v7",
                "- uses: actions/setup-node@v7",
                "- uses: actions/download-artifact@v8",
            ],
            [step for step in steps if step.startswith("- uses:")],
        )
        self.assertIn('python-version: "3.12"', promote)
        self.assertIn('node-version: "24"', promote)
        self.assertIn("registry-url: https://registry.npmjs.org", promote)
        self.assertIn("name: opencode-npm-candidate", promote)
        self.assertIn("path: dist/npm", promote)
        self.assertIn("promote-unica-opencode.py", promote)
        self.assertEqual(1, promote.count("NODE_AUTH_TOKEN"))
        self.assertEqual(
            1,
            promote.count("NODE_AUTH_TOKEN: ${{ secrets.NPM_PROMOTION_TOKEN }}"),
        )
        # Токен живёт только на уровне шага promotion, не всей работы.
        token_line_index = promote.index("NODE_AUTH_TOKEN: ${{")
        promotion_step_index = promote.index("promote-unica-opencode.py")
        self.assertLess(token_line_index, promotion_step_index)

        # Порядок контура: smokes нуждаются в publish, promote — в smokes.
        self.assertIn(
            "needs: publish-opencode-npm",
            job_block(workflow, "smoke-opencode-windows"),
        )

    def test_opencode_promotion_credentials_are_isolated_from_publishing(self):
        """Токен promotion изолирован от публикации (INV.PKG.NPM-CREDENTIAL-SPLIT).

        Статически проверяемое: у publish job нет npm-токенов ни на каком
        уровне; promotion читает `NODE_AUTH_TOKEN` только из environment
        secret `NPM_PROMOTION_TOKEN` и только в шаге promotion; работа
        promotion объявляет environment. Scope токена и защита Environment —
        живое evidence внешнего этапа, в статическую заявку не входят.
        """
        workflow = RELEASE_WORKFLOW.read_text(encoding="utf-8")
        publish = job_block(workflow, "publish-opencode-npm")
        promote = job_block(workflow, "promote-opencode-npm")

        self.assertTrue(publish)
        self.assertTrue(promote)
        self.assertNotIn("NODE_AUTH_TOKEN", publish)
        self.assertNotIn("NPM_PROMOTION_TOKEN", publish)
        self.assertIn("environment: npm-promotion", promote)
        # Единственное упоминание NODE_AUTH_TOKEN — шаг promotion скрипта.
        self.assertEqual(1, promote.count("NODE_AUTH_TOKEN"))
        self.assertIn("secrets.NPM_PROMOTION_TOKEN", promote)

    def test_windows_smoke_blocks_the_release(self) -> None:
        """Windows-потребитель блокирует выпуск (INV.CI.OPENCODE-CONSUMER-WINDOWS-BLOCKS)."""
        workflow = RELEASE_WORKFLOW.read_text(encoding="utf-8")
        windows = job_block(workflow, "smoke-opencode-windows")
        promote = job_block(workflow, "promote-opencode-npm")

        self.assertTrue(windows)
        self.assertTrue(promote)
        self.assertNotIn("continue-on-error", windows)
        self.assertIn("needs.smoke-opencode-windows.result == 'success'", promote)

    def test_linux_smoke_is_best_effort(self) -> None:
        """Linux-потребитель — best effort (INV.CI.OPENCODE-CONSUMER-LINUX-BEST-EFFORT).

        Linux остаётся в needs promotion, чтобы отчёт о сбое дожил до
        агрегатного гейта, но результат Linux выпуск не гейтит.
        """
        workflow = RELEASE_WORKFLOW.read_text(encoding="utf-8")
        linux = job_block(workflow, "smoke-opencode-linux")
        promote = job_block(workflow, "promote-opencode-npm")

        self.assertTrue(linux)
        self.assertTrue(promote)
        self.assertIn("continue-on-error: true", linux)
        self.assertIn("smoke-opencode-linux", promote)
        self.assertIn(
            "needs: [publish-opencode-npm, smoke-opencode-windows, smoke-opencode-linux]",
            promote,
        )
        self.assertNotIn("needs.smoke-opencode-linux.result", promote)

    def test_publication_is_one_linear_pass_ordered_by_needs(self) -> None:
        """ADR-0068: stage → tag → verify → promote, no pull requests, no warden.

        The order is the contract: the anchor tag exists before the install
        checks run, and the catalog moves only behind their green result. A
        rerun of the whole workflow resumes a partial publication, so every
        stage states its idempotent escape.
        """
        on = triggers(self.publish)
        text = all_scripts(self.publish)
        gate = job(self.publish, "gate")

        self.assertIn("workflow_run", on)
        self.assertIn("source_run_id", on["workflow_dispatch"]["inputs"])
        # Сборка запускается и по push в main; публикацию открывает только тег.
        self.assertIn("startsWith(github.event.workflow_run.head_branch, 'v')", condition(gate))
        for job_id in ("stage", "tag", "verify-fresh-install", "verify-upgrade", "promote"):
            with self.subTest(job_id=job_id):
                self.assertIn(job_id, jobs(self.publish))
        self.assertEqual(needs(job(self.publish, "tag")), ["stage"])
        self.assertEqual(needs(job(self.publish, "verify-fresh-install")), ["stage", "tag"])
        self.assertEqual(needs(job(self.publish, "verify-upgrade")), ["stage", "tag"])
        self.assertEqual(needs(job(self.publish, "promote")), ["stage", "tag", "verify-fresh-install", "verify-upgrade"])
        # The PR ceremony is gone with the warden: nothing opens pull requests
        # and no metadata travels in branch names.
        self.assertNotIn("pr create", text)
        self.assertNotIn("codex/stage-", text)
        self.assertNotIn("codex/promote-", text)
        self.assertNotIn("mode", on["workflow_dispatch"]["inputs"])
        # Idempotent escapes: a completed stage and a completed promote are
        # detected, and an existing tag is proven identical, never moved.
        self.assertEqual(text.count("diff --cached --quiet"), 2)
        self.assertIn('rev-parse --verify --quiet "refs/tags/${RELEASE_TAG}"', text)
        self.assertNotIn("git tag -f", text)
        self.assertNotIn("--force", text)
        # Two releases must not interleave, and a stale straggler must fail
        # forward-only instead of rolling the catalog back — in both writers,
        # over both host catalogs, and again after a rebase retry in promote.
        self.assertEqual(self.publish["concurrency"], {"group": "publish-unica-marketplace", "cancel-in-progress": False})
        self.assertEqual(text.count("require_forward()"), 2)
        self.assertEqual(text.count('test "$newest" = "$RELEASE_TAG"'), 2)
        self.assertEqual(
            text.count(
                ".agents/plugins/marketplace.json .claude-plugin/marketplace.json"
            ),
            3,  # both guard loops and the promote `git add`
        )
        self.assertIn('require_forward "HEAD~1"', text)
        # The payload is trusted only from the successful push build of the
        # very tag its manifest declares — dispatch cannot smuggle another one.
        self.assertIn('test "$run_event" = "push"', text)
        self.assertIn('test "$run_branch" = "$RELEASE_TAG"', text)
        self.assertIn(
            'gh api "repos/IngvarConsulting/unica/git/ref/tags/${RELEASE_TAG}" --silent',
            text,
        )
        self.assertIn("payload/plugins/unica/.codex-plugin/plugin.json", text)
        self.assertIn("payload/plugins/unica/.mcp.json", text)
        self.assertIn("payload/.agents/plugins/marketplace.json", text)
        # Consumer verification installs the candidate the way a consumer does,
        # on every supported host, before the catalog moves.
        self.assertEqual(text.count("plugin marketplace add $candidate --json"), 2)
        # The upgrade gate seeds the previous stable and then moves that same
        # install to the candidate. The candidate is a directory marketplace, so
        # the move is a reinstall against the rewritten catalog: `plugin
        # marketplace upgrade` fetches a Git remote and refuses one.
        self.assertNotIn("plugin marketplace upgrade unica", text)
        self.assertIn("plugin remove unica@unica --json", text)
        self.assertEqual(text.count("plugin add unica@unica --json"), 3)
        self.assertIn("verify --plugin-root $pluginRoot", text)


    def test_the_build_names_its_own_core_release_repository(self) -> None:
        """Выпуск зовёт упаковку с адресом ядра этого репозитория.

        Умолчание упаковщика — upstream-адрес; молчаливое умолчание в форке
        собрало бы манифест, указывающий на чужой выпуск. Адрес обязана
        назвать сама сборка (CTR.PKG.CORE-PROVENANCE-SELECTABLE).
        """
        workflow = RELEASE_WORKFLOW.read_text(encoding="utf-8")

        self.assertIn(
            "CORE_RELEASE_REPOSITORY: https://github.com/${{ github.repository }}",
            workflow,
        )
        for job_id in ("build-tools", "package-thin"):
            block = job_block(workflow, job_id)
            self.assertTrue(block, f"job {job_id} not found")
            self.assertIn('"$CORE_RELEASE_REPOSITORY"', block)
            self.assertIn("--core-release-repository", block)

    def test_the_bootstrap_proves_its_compiled_core_repository(self) -> None:
        """Сборка доказывает compile-time seam происхождения ядра.

        Тестовый бинарь компилируется уже с `UNICA_BOOTSTRAP_CORE_REPOSITORY`,
        названным сборкой, и обычный `RuntimeManifest::validate` следует
        запечённому владельцу, а не значению, подсунутому тестом в рантайме.
        """
        workflow = RELEASE_WORKFLOW.read_text(encoding="utf-8")
        build = job_block(workflow, "build-tools")
        self.assertTrue(build, "job build-tools not found")

        proof_steps = [
            step
            for step in build.split("- name:")
            if "cargo test -p unica-bootstrap --test manifest_contract" in step
        ]
        self.assertEqual(
            len(proof_steps), 1, "exactly one compiled-repository proof step"
        )
        step = proof_steps[0]
        self.assertIn(
            'UNICA_BOOTSTRAP_CORE_REPOSITORY="$CORE_RELEASE_REPOSITORY"', step
        )
        self.assertIn(
            "ordinary_validation_uses_the_repository_compiled_into_the_bootstrap",
            step,
        )
        self.assertIn("--exact", step)
        self.assertIn("if: matrix.target == 'linux-x64'", step)

    def test_opencode_npm_publication_is_fork_gated_and_trusted(self) -> None:
        """npm-этапирование — только теговый пуш форка, после проверенных ассетов.

        Стадия публикует кандидата короткоживущим OIDC-токеном trusted
        publishing под служебным dist-tag: долгоживущий npm-токен у publish
        job не появляется (INV.PKG.NPM-PUBLICATION-FORK-TAG-OIDC).
        Перемещение `latest`/`next` выполняет отдельный promotion job.
        """
        workflow = RELEASE_WORKFLOW.read_text(encoding="utf-8")
        block = job_block(workflow, "publish-opencode-npm")

        self.assertTrue(block, "job publish-opencode-npm not found")
        self.assertIn("needs: [package-thin, verify-published-assets]", block)
        self.assertIn("github.event_name == 'push'", block)
        self.assertIn("startsWith(github.ref, 'refs/tags/')", block)
        self.assertIn("github.repository == 'apshendev/unica'", block)
        self.assertIn("needs.package-thin.result == 'success'", block)
        self.assertIn("needs.verify-published-assets.result == 'success'", block)
        self.assertIn("id-token: write", block)
        self.assertIn("package-unica-opencode.py", block)
        self.assertIn("publish-unica-opencode.py", block)
        self.assertNotIn("NODE_AUTH_TOKEN", block)
        self.assertNotIn("NPM_PROMOTION_TOKEN", block)
        self.assertNotIn("secrets.", block)
        # Promotion — отдельная работа: публикация не двигает dist-tag.
        self.assertTrue(
            job_block(workflow, "promote-opencode-npm"),
            "job promote-opencode-npm not found",
        )
        # Литерал владельца одинаков в workflow, скрипте публикации и гейте.
        publish_script = (
            REPO_ROOT / "scripts" / "ci" / "publish-unica-opencode.py"
        ).read_text(encoding="utf-8")
        gate_script = (REPO_ROOT / "scripts" / "ci" / "evaluate-ci-gate.py").read_text(
            encoding="utf-8"
        )
        self.assertIn('FORK_REPOSITORY = "apshendev/unica"', publish_script)
        self.assertIn('FORK_REPOSITORY = "apshendev/unica"', gate_script)

    def test_opencode_consumer_smoke_gates_the_release(self) -> None:
        """Реальный потребитель пола 1.18.22 проверяет npm-кандидата.

        Windows x64 — блокирующий: без него выпуск не зелёный. Linux x64 —
        best effort: `continue-on-error`, но его падение видно в отчёте.
        OpenCode-потребителя под macOS нет, а существующие Codex/Claude
        проверки macOS не тронуты. Обе подкоманды верификатора получают
        установленный root пакета и target.
        """
        workflow = RELEASE_WORKFLOW.read_text(encoding="utf-8")
        windows = job_block(workflow, "smoke-opencode-windows")
        linux = job_block(workflow, "smoke-opencode-linux")

        for job_id, block, target in (
            ("smoke-opencode-windows", windows, "win-x64"),
            ("smoke-opencode-linux", linux, "linux-x64"),
        ):
            with self.subTest(job=job_id):
                self.assertTrue(block, f"job {job_id} not found")
                self.assertIn("needs: publish-opencode-npm", block)
                self.assertIn("github.repository == 'apshendev/unica'", block)
                self.assertIn("npm install -g opencode-ai@1.18.22", block)
                # Пол, не потолок: потребитель ставит ровно версию пола.
                self.assertNotIn("opencode-ai@latest", block)
                self.assertIn("opencode debug skill", block)
                self.assertIn("opencode mcp list", block)
                self.assertIn("smoke-opencode-consumer.py", block)
                # Потребитель изолирован вне checkout: каталог во временном
                # хранилище раннера, а не в рабочем дереве репозитория.
                self.assertNotIn(".build/consumer", block)
                self.assertIn(
                    "working-directory: ${{ runner.temp }}/opencode-consumer", block
                )
                # Обе подкоманды верификатора доказывают установленный root
                # пакета потребителя и target-специфичную раскладку bootstrap.
                installed_root = (
                    '"$RUNNER_TEMP/opencode-consumer/node_modules'
                    '/@apshendev/unica-opencode"'
                )
                self.assertEqual(2, block.count(installed_root))
                self.assertEqual(2, block.count(f"--target {target}"))
                self.assertIn('"$RUNNER_TEMP/opencode-consumer/skills.json"', block)
                self.assertIn('"$RUNNER_TEMP/opencode-consumer/mcp.txt"', block)
                # Сбор наблюдений mcp тоже отказоустойчиво закрыт: провал
                # `opencode mcp list` не должен прятаться за кодом tee.
                self.assertIn(
                    "set -euo pipefail",
                    block.split("opencode mcp list")[0].split("Collect mcp")[-1],
                )

        self.assertNotIn("continue-on-error", windows)
        self.assertIn("continue-on-error: true", linux)
        # Никакого OpenCode-потребителя под macOS.
        for job_id in ("smoke-opencode-darwin", "smoke-opencode-macos"):
            self.assertFalse(job_block(workflow, job_id))

    def test_the_consumer_installs_the_exact_registry_version(self) -> None:
        """Установка потребителя доказуема: npm ставит точную версию из реестра.

        `opencode plugin` не оставляет проверяемого пути `node_modules`, а
        checkout `plugins/unica` не доказывает содержимое публикации. Блок
        установки ставит пакет npm'ом с `--ignore-scripts` и подключает его
        абсолютным `file://` URI (INV.CI.OPENCODE-CONSUMER-INSTALLED-ROOT).
        """
        workflow = RELEASE_WORKFLOW.read_text(encoding="utf-8")

        for job_id in ("smoke-opencode-windows", "smoke-opencode-linux"):
            block = job_block(workflow, job_id)
            with self.subTest(job=job_id):
                self.assertTrue(block, f"job {job_id} not found")
                self.assertIn("npm install --ignore-scripts", block)
                self.assertIn('"@apshendev/unica-opencode@${version}"', block)
                self.assertIn("npm init -y", block)
                self.assertIn("pathToFileURL", block)
                self.assertIn("file://", block)
                # Установка идёт npm'ом из реестра, а не командой плагина:
                # checkout исходников не подменяет проверку публикации.
                self.assertNotIn('opencode plugin "', block)
                self.assertIn("node_modules/@apshendev/unica-opencode", block)

    def test_opencode_npm_publication_stages_smokes_then_promotes(self) -> None:
        """Контур npm-выпуска: staging → потребители → promotion.

        Publish job не двигает потребительские dist-tag и выгружает кандидата
        артефактом; smoke-потребители ставят его из реестра; promotion
        перемещает dist-tag только после зелёных Windows-проверок
        (DEC.2026-08-25.NPM-DIST-TAG-PROMOTION).
        """
        workflow = RELEASE_WORKFLOW.read_text(encoding="utf-8")
        publish = job_block(workflow, "publish-opencode-npm")
        promote = job_block(workflow, "promote-opencode-npm")

        self.assertTrue(publish, "job publish-opencode-npm not found")
        self.assertTrue(promote, "job promote-opencode-npm not found")

        # Publish: этапирует кандидата и не двигает потребительские теги.
        self.assertIn("id-token: write", publish)
        self.assertIn("contents: read", publish)
        self.assertNotIn("NPM_PROMOTION_TOKEN", publish)
        self.assertNotIn("NODE_AUTH_TOKEN", publish)
        self.assertNotIn("dist-tag", publish)
        self.assertIn("name: Stage OpenCode npm candidate (staging)", publish)
        upload = publish[publish.index("actions/upload-artifact@v7") :]
        self.assertIn("name: opencode-npm-candidate", upload)
        self.assertIn("path: dist/npm", upload)
        self.assertIn("retention-days: 1", upload)
        self.assertIn("compression-level: 0", upload)

        # Promote: контракт работы.
        self.assertIn(
            "needs: [publish-opencode-npm, smoke-opencode-windows, smoke-opencode-linux]",
            promote,
        )
        self.assertIn("always()", promote)
        self.assertIn("needs.publish-opencode-npm.result == 'success'", promote)
        self.assertIn("needs.smoke-opencode-windows.result == 'success'", promote)
        # Linux в needs ждёт отчёта, но его результат выпуск не гейтит.
        self.assertNotIn("needs.smoke-opencode-linux.result", promote)
        self.assertIn("github.event_name == 'push'", promote)
        self.assertIn("startsWith(github.ref, 'refs/tags/')", promote)
        self.assertIn("github.repository == 'apshendev/unica'", promote)
        self.assertIn("permissions:", promote)
        self.assertIn("contents: read", promote)
        self.assertIn("environment: npm-promotion", promote)
        self.assertIn("timeout-minutes: 10", promote)
        self.assertNotIn("id-token", promote)
        self.assertNotIn("publish-unica-opencode.py", promote)

        # Порядок шагов promotion фиксирован: registry-url обязан прийти до
        # npm-вызова, артефакт — до скрипта, токен — только в шаге скрипта.
        steps = [
            line.strip()
            for line in promote.splitlines()
            if line.strip().startswith("- uses:") or line.strip().startswith("- name:")
        ]
        self.assertEqual(
            [
                "- uses: actions/checkout@v7",
                "- uses: actions/setup-python@v7",
                "- uses: actions/setup-node@v7",
                "- uses: actions/download-artifact@v8",
            ],
            [step for step in steps if step.startswith("- uses:")],
        )
        self.assertIn('python-version: "3.12"', promote)
        self.assertIn('node-version: "24"', promote)
        self.assertIn("registry-url: https://registry.npmjs.org", promote)
        self.assertIn("name: opencode-npm-candidate", promote)
        self.assertIn("path: dist/npm", promote)
        self.assertIn("promote-unica-opencode.py", promote)
        self.assertEqual(1, promote.count("NODE_AUTH_TOKEN"))
        self.assertEqual(
            1,
            promote.count("NODE_AUTH_TOKEN: ${{ secrets.NPM_PROMOTION_TOKEN }}"),
        )
        # Токен живёт только на уровне шага promotion, не всей работы.
        token_line_index = promote.index("NODE_AUTH_TOKEN: ${{")
        promotion_step_index = promote.index("promote-unica-opencode.py")
        self.assertLess(token_line_index, promotion_step_index)

        # Порядок контура: smokes нуждаются в publish, promote — в smokes.
        self.assertIn(
            "needs: publish-opencode-npm",
            job_block(workflow, "smoke-opencode-windows"),
        )

    def test_opencode_promotion_credentials_are_isolated_from_publishing(self):
        """Токен promotion изолирован от публикации (INV.PKG.NPM-CREDENTIAL-SPLIT).

        Статически проверяемое: у publish job нет npm-токенов ни на каком
        уровне; promotion читает `NODE_AUTH_TOKEN` только из environment
        secret `NPM_PROMOTION_TOKEN` и только в шаге promotion; работа
        promotion объявляет environment. Scope токена и защита Environment —
        живое evidence внешнего этапа, в статическую заявку не входят.
        """
        workflow = RELEASE_WORKFLOW.read_text(encoding="utf-8")
        publish = job_block(workflow, "publish-opencode-npm")
        promote = job_block(workflow, "promote-opencode-npm")

        self.assertTrue(publish)
        self.assertTrue(promote)
        self.assertNotIn("NODE_AUTH_TOKEN", publish)
        self.assertNotIn("NPM_PROMOTION_TOKEN", publish)
        self.assertIn("environment: npm-promotion", promote)
        # Единственное упоминание NODE_AUTH_TOKEN — шаг promotion скрипта.
        self.assertEqual(1, promote.count("NODE_AUTH_TOKEN"))
        self.assertIn("secrets.NPM_PROMOTION_TOKEN", promote)

    def test_windows_smoke_blocks_the_release(self) -> None:
        """Windows-потребитель блокирует выпуск (INV.CI.OPENCODE-CONSUMER-WINDOWS-BLOCKS)."""
        workflow = RELEASE_WORKFLOW.read_text(encoding="utf-8")
        windows = job_block(workflow, "smoke-opencode-windows")
        promote = job_block(workflow, "promote-opencode-npm")

        self.assertTrue(windows)
        self.assertTrue(promote)
        self.assertNotIn("continue-on-error", windows)
        self.assertIn("needs.smoke-opencode-windows.result == 'success'", promote)

    def test_linux_smoke_is_best_effort(self) -> None:
        """Linux-потребитель — best effort (INV.CI.OPENCODE-CONSUMER-LINUX-BEST-EFFORT).

        Linux остаётся в needs promotion, чтобы отчёт о сбое дожил до
        агрегатного гейта, но результат Linux выпуск не гейтит.
        """
        workflow = RELEASE_WORKFLOW.read_text(encoding="utf-8")
        linux = job_block(workflow, "smoke-opencode-linux")
        promote = job_block(workflow, "promote-opencode-npm")

        self.assertTrue(linux)
        self.assertTrue(promote)
        self.assertIn("continue-on-error: true", linux)
        self.assertIn("smoke-opencode-linux", promote)
        self.assertIn(
            "needs: [publish-opencode-npm, smoke-opencode-windows, smoke-opencode-linux]",
            promote,
        )
        self.assertNotIn("needs.smoke-opencode-linux.result", promote)



class ArtifactSplitPublicationTests(unittest.TestCase):
    """Разрез поставки делит сборку и выкладку по-разному.

    Сборка несёт все артефакты: их метаданные нужны упаковщику, чтобы манифест
    объявил каждый. Выкладка несёт одно ядро: движки издал тулчейн, и вторая
    публикация тех же байтов стоила 439 МБ на выпуск.
    """

    def setUp(self) -> None:
        self.release = load(RELEASE_WORKFLOW)
        self.build = job(self.release, "build-tools")

    def test_the_release_publishes_the_core_and_only_it(self) -> None:
        # Выкладывается то, у чего есть читатель: пару ядра перекачивает и
        # перехеширует `verify-release-assets.py`. Описания поставок читает
        # только упаковщик, и берёт он их из артефакта сборки.
        release = steps_using(job(self.release, "publish-release-assets"), "softprops/action-gh-release")[0]

        self.assertIn("dist/runtime/unica-runtime-*.tar.gz", release["with"]["files"])
        self.assertIn("dist/runtime/unica-runtime-*.json", release["with"]["files"])
        self.assertFalse(any("dist/runtime/*-runtime-*" in value for value in strings(self.release)))

    def test_the_manifest_still_names_the_artifacts_the_release_does_not_carry(self) -> None:
        # Не выложить и не назвать — разные вещи. Движки объявлены адресом, и
        # каждый адрес выпуск проверяет.
        self.assertIn("verify-delivery-reachable.py", all_scripts(self.release))
        self.assertIn("prefetch --plugin-root", all_scripts(self.release))

    def test_packaging_uploads_every_artifact_of_the_target(self) -> None:
        paths = [upload.get("path", "") for upload in uploads(self.build)]
        for glob in (
            "runtime-assets/${{ matrix.target }}/*-runtime-${{ matrix.target }}.tar.gz",
            "runtime-assets/${{ matrix.target }}/*-runtime-${{ matrix.target }}.json",
        ):
            with self.subTest(glob=glob):
                self.assertTrue(any(glob in path for path in paths), glob)

    def test_bsp_runtime_assessment_receives_the_engine_its_search_requires(self) -> None:
        assessment = job(self.release, "release-assessment")

        self.assertIn("unica-assessment-engine-linux-x64", [upload.get("name") for upload in uploads(self.build)])
        self.assertIn("stage-unica-assessment-engine.py", script(self.build))
        self.assertIn("--artifact bsl-analyzer", script(self.build))
        self.assertIn("--artifact rlm-tools-bsl", script(self.build))
        self.assertIn("--out-archive .build/unica-assessment-engine-linux-x64.tar.gz", script(self.build))
        self.assertIn("unica-assessment-engine-linux-x64", [download.get("name") for download in downloads(assessment)])
        self.assertIn(
            "--engine-overlay .build/assessment-engine/unica-assessment-engine-linux-x64.tar.gz",
            script(assessment),
        )

    def test_the_direct_mcp_smoke_is_given_the_engines_it_asserts_on(self) -> None:
        extract = step_named(self.build, "Extract deterministic runtime for MCP smoke")

        self.assertIn("unica-runtime-${{ matrix.target }}.tar.gz", extract["run"])
        self.assertIn(".build/tool-bundles/${{ matrix.target }}/bin/", extract["run"])

    def test_every_supported_target_must_pass_before_publication(self) -> None:
        authoritative = targets(self.build)
        self.assertEqual(
            authoritative,
            [
                ("linux-x64", "ubuntu-latest"),
                ("win-x64", "windows-latest"),
                ("darwin-arm64", "macos-14"),
            ],
        )
        authoritative_targets = {target for target, _ in authoritative}
        for contour in ("probe-thin-bootstrap", "smoke-thin-plugin"):
            self.assertEqual({target for target, _ in targets(job(self.release, contour))}, authoritative_targets, contour)

        ordered_steps = (
            "Build target bundle and bootstrap",
            "Package deterministic runtime",
            "Verify local runtime asset pair",
            "Upload runtime metadata",
            "Upload bootstrap payload",
            "Upload required runtime archive",
        )
        positions = [step_index(self.build, name) for name in ordered_steps]
        self.assertEqual(positions, sorted(positions))
        self.assertIn("tools.json", script(self.build))
        self.assertIn('manifest["runtimeFiles"]', script(self.build))
        self.assertIn('--target "${{ matrix.target }}"', script(self.build))

        expected_needs = {
            "package-thin": ["build-tools"],
            "publish-release-assets": ["build-tools"],
            "probe-thin-bootstrap": ["package-thin"],
            "smoke-thin-plugin": ["package-thin", "publish-release-assets"],
            "verify-published-assets": ["publish-release-assets", "package-thin"],
            "publish-opencode-npm": ["package-thin", "verify-published-assets"],
        }
        for job_id, dependencies in expected_needs.items():
            found = job(self.release, job_id)
            self.assertEqual(needs(found), dependencies, job_id)
            for dependency in dependencies:
                self.assertIn(f"needs.{dependency}.result == 'success'", condition(found))

        local_verifier = "python scripts/ci/verify-release-assets.py"
        self.assertIn(local_verifier, script(self.build))
        self.assertIn('--asset-dir ".build/runtime-assets/${{ matrix.target }}"', script(self.build))

        published = job(self.release, "verify-published-assets")
        published_lifecycle = (
            "gh release download \"$GITHUB_REF_NAME\" --pattern 'unica-runtime-*' --dir published",
            local_verifier + " --asset-dir published",
            "unica-thin-marketplace",
            "python scripts/ci/verify-delivery-reachable.py",
        )
        texts = [step_text(step) for step in steps(published)]
        published_positions = [next(index for index, text in enumerate(texts) if marker in text) for marker in published_lifecycle]
        self.assertEqual(published_positions, sorted(published_positions))
        self.assertNotIn("--target", "\n".join(texts), "published verification must cover every target")

        smoke = job(self.release, "smoke-thin-plugin")
        smoke_lifecycle = (
            "Smoke packaged bootstrap against published runtime",
            "Prefetch the whole delivery once, end to end",
        )
        smoke_positions = [step_index(smoke, name) for name in smoke_lifecycle]
        self.assertEqual(smoke_positions, sorted(smoke_positions))
        self.assertIn("matrix.target == 'linux-x64'", condition(step_named(smoke, "Prefetch the whole delivery once, end to end")))
        self.assertIn("prefetch --plugin-root .build/thin/plugins/unica", script(smoke))


class PrereleaseNeverReachesConsumersTests(unittest.TestCase):
    """Предвыпуск собирается и публикует ассеты, но каталога не касается.

    Замерить доставку можно только на настоящем релизе: адрес архива прибит к
    релизам репозитория. Значит нужен выпуск, который существует для нас и не
    существует для пользователей, — и решать это должен конвейер, а не память
    того, кто его запускал.
    """

    def setUp(self) -> None:
        self.release = load(RELEASE_WORKFLOW)
        self.publish = load(PUBLISH_WORKFLOW)

    def test_a_prerelease_tag_marks_the_github_release_as_such(self) -> None:
        # Иначе предвыпуск станет «последним релизом» и его начнут находить
        # те, кто ищет свежее.
        release = steps_using(job(self.release, "publish-release-assets"), "softprops/action-gh-release")[0]

        self.assertEqual(normalized(release["with"]["prerelease"]), "${{ contains(github.ref_name, '-') }}")

    def test_publication_asks_first_whether_this_release_is_for_consumers(self) -> None:
        self.assertIn("gate", jobs(self.publish))
        self.assertIn("promote", jobs(self.publish))

    def test_every_publishing_stage_waits_for_that_answer(self) -> None:
        # Достаточно загейтить первую стадию: остальные ждут её через `needs`.
        stage = job(self.publish, "stage")

        self.assertEqual(needs(stage), ["gate"])
        self.assertEqual(condition(stage), "needs.gate.outputs.promote == 'true'")


if __name__ == "__main__":
    unittest.main()
