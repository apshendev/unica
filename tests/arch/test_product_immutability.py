"""Guards for the immutability of accepted product records.

The live tree cannot exercise this one yet: `arch/` has not reached `main`, so
a comparison against the base branch sees zero records and would report green
having looked at nothing. That is the failure mode this repository has already
paid for twice, so the rule is proved against fixtures — a real git repository
built per case — and the live check asserts what it actually compared rather
than only that it found nothing wrong.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "arch" / "immutability.py"
SPEC = importlib.util.spec_from_file_location("arch_immutability", SCRIPT)
IMMUTABILITY = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = IMMUTABILITY
SPEC.loader.exec_module(IMMUTABILITY)

PRODUCT = """---
id: DEC.2026-01-01.PROMISE
status: planned
governs: product
realized: null
supersedes: []
superseded-by: null
establishes: []
---

# Обещание

**Решение.** Поверхность отвечает так, а не иначе.
"""

PROCESS = """---
id: DEC.2026-01-01.HABIT
status: active
governs: process
realized: null
supersedes: []
superseded-by: null
establishes: []
---

# Привычка

**Решение.** Работаем так, а не иначе.
"""


RULE = """---
id: INV.WIRE.PROMISE
status: active
governs: product
decision: DEC.2026-01-01.PROMISE
check: tests/ci/test_x.py::test_y
scope: [wire]
---

# Правило

Поверхность отвечает так, а не иначе.
"""

GROUND = """---
id: DEC.2026-03-03.WHY-IT-CHANGES
status: active
governs: product
realized: tests/evidence.py::test_reason
supersedes: []
superseded-by: null
establishes: []
---

# Почему правило меняется

**Решение.** Замер показал, что прежняя формулировка не покрывала случай.
"""

SURFACE_GROUND = GROUND.replace(
    "establishes: []",
    "changes: [CTR.WIRE.TOOL-SURFACE]\nestablishes: [INV.WIRE.SURFACE-CHANGE]",
)
UNRELATED_SURFACE_GROUND = SURFACE_GROUND.replace(
    "CTR.WIRE.TOOL-SURFACE", "CTR.WIRE.UNRELATED"
)
SURFACE_RULE = RULE.replace(
    "id: INV.WIRE.PROMISE",
    "id: INV.WIRE.SURFACE-CHANGE",
).replace(
    "decision: DEC.2026-01-01.PROMISE",
    "decision: DEC.2026-03-03.WHY-IT-CHANGES",
)

INVARIANT_GROUND = """---
id: INV.WIRE.WHY-IT-CHANGES
status: active
governs: product
decision: DEC.2026-01-01.PROMISE
check: tests/evidence.py::test_reason
scope: [wire]
---

# Не решение
"""

PLANNED_GROUND = GROUND.replace("status: active", "status: planned").replace(
    "realized: tests/evidence.py::test_reason", "realized: null"
)
PROCESS_GROUND = GROUND.replace("governs: product", "governs: process")
UNREALIZED_GROUND = GROUND.replace(
    "realized: tests/evidence.py::test_reason", "realized: null"
)
MISSING_EVIDENCE_GROUND = GROUND.replace("test_reason", "test_missing")
NON_DEFINITION_EVIDENCE_GROUND = GROUND.replace(
    "tests/evidence.py::test_reason", "scripts/arch/immutability.py::active"
)
PYTHON_STRING_EVIDENCE_GROUND = GROUND.replace(
    "tests/evidence.py::test_reason", "tests/fake_string.py::test_fake_python_reason"
)
RUST_STRING_EVIDENCE_GROUND = GROUND.replace(
    "tests/evidence.py::test_reason",
    "crates/fake_string.rs::test_fake_rust_string_reason",
)
RUST_DECLARATION_EVIDENCE_GROUND = GROUND.replace(
    "tests/evidence.py::test_reason",
    "crates/fake_declaration.rs::test_fake_rust_declaration_reason",
)
RUST_MACRO_DECLARATION_EVIDENCE_GROUND = GROUND.replace(
    "tests/evidence.py::test_reason",
    "crates/fake_macro_declaration.rs::test_fake_rust_macro_reason",
)


class Fixture:
    """A real git repository with a base commit holding two records."""

    def __init__(self, stack: tempfile.TemporaryDirectory) -> None:
        self.root = Path(stack.name)
        self._git("init", "--quiet", "--initial-branch=base")
        self._git("config", "user.email", "guard@example.test")
        self._git("config", "user.name", "Guard")
        (self.root / "arch" / "decisions").mkdir(parents=True)
        self.product = self.root / "arch" / "decisions" / "2026-01-01-promise.md"
        self.process = self.root / "arch" / "decisions" / "2026-01-01-habit.md"
        self.product.write_text(PRODUCT, encoding="utf-8")
        self.process.write_text(PROCESS, encoding="utf-8")
        (self.root / "arch" / "invariants").mkdir(parents=True)
        self.rule = self.root / "arch" / "invariants" / "INV.WIRE.PROMISE.md"
        self.rule.write_text(RULE, encoding="utf-8")
        self.surface = self.root / "arch" / "tool-surface.md"
        self.surface.write_text("# Surface\n\nunica.old\n", encoding="utf-8")
        (self.root / "tests").mkdir()
        (self.root / "tests" / "evidence.py").write_text(
            "def test_reason(): pass\n\nclass Evidence:\n    async def test_async_reason(self): pass\n",
            encoding="utf-8",
        )
        (self.root / "tests" / "fake_string.py").write_text(
            'FAKE = """\ndef test_fake_python_reason():\n    pass\n"""\n',
            encoding="utf-8",
        )
        script = self.root / "scripts" / "arch" / "immutability.py"
        script.parent.mkdir(parents=True)
        script.write_text("status = 'active'\n", encoding="utf-8")
        rust = self.root / "crates" / "evidence.rs"
        rust.parent.mkdir(parents=True)
        rust.write_text(
            'const MULTILINE: &str = "first line\nsecond line";\n'
            'const LABEL: &\'static str = "evidence";\n'
            "    #[test]\n    fn test_rust_reason() {}\n",
            encoding="utf-8",
        )
        (self.root / "crates" / "fake_string.rs").write_text(
            'const FAKE: &str = r#"\n    #[test]\n    fn test_fake_rust_string_reason() {}\n"#;\n',
            encoding="utf-8",
        )
        (self.root / "crates" / "fake_declaration.rs").write_text(
            "trait Evidence {\n    #[test]\n"
            "    fn test_fake_rust_declaration_reason() -> Marker<{ 1 }>;\n}\n",
            encoding="utf-8",
        )
        (self.root / "crates" / "fake_macro_declaration.rs").write_text(
            "trait Evidence {\n    #[test]\n"
            "    fn test_fake_rust_macro_reason() -> Marker!{ u32 };\n}\n",
            encoding="utf-8",
        )
        self._git("add", "arch", "tests", "scripts", "crates")
        self._git("commit", "--quiet", "--no-gpg-sign", "-m", "base")

    def _git(self, *args: str) -> None:
        subprocess.run(["git", *args], cwd=self.root, check=True, capture_output=True)

    def inspect(self):
        return IMMUTABILITY.inspect(self.root, "base")


class ProductImmutabilityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.stack = tempfile.TemporaryDirectory()
        self.addCleanup(self.stack.cleanup)
        self.fixture = Fixture(self.stack)

    def write_ground(self) -> None:
        """Write the new ground decision used by the checks below."""
        decision = (
            self.fixture.root / "arch" / "decisions" / "2026-03-03-why-it-changes.md"
        )
        decision.write_text(GROUND, encoding="utf-8")

    def surface_ground_error(self, text: str):
        """The ground mechanism survives only for surface changes."""
        self.write_ground()
        decision = (
            self.fixture.root / "arch" / "decisions" / "2026-03-03-why-it-changes.md"
        )
        decision.write_text(text, encoding="utf-8")
        props, _ = IMMUTABILITY._split(text)
        record = IMMUTABILITY.IntroducedRecord(
            kind="decision",
            path="arch/decisions/2026-03-03-why-it-changes.md",
            props=props,
        )
        return IMMUTABILITY._ground_error(self.fixture.root, record)

    def test_an_untouched_tree_is_clean_and_says_what_it_compared(self) -> None:
        verdict = self.fixture.inspect()
        self.assertEqual(verdict.offenders, ())
        self.assertEqual(
            verdict.compared,
            2,
            "both product records count, and the process one does not",
        )

    def test_editing_an_accepted_product_decision_is_caught(self) -> None:
        self.fixture.product.write_text(
            PRODUCT.replace("так, а не иначе", "уже совсем иначе"), encoding="utf-8"
        )
        verdict = self.fixture.inspect()
        self.assertEqual(len(verdict.offenders), 1)
        self.assertIn("отредактировано", verdict.offenders[0])

    def test_deleting_an_accepted_product_record_is_caught(self) -> None:
        self.fixture.product.unlink()
        verdict = self.fixture.inspect()
        self.assertEqual(len(verdict.offenders), 1)
        self.assertIn("удалена", verdict.offenders[0])

    def test_stamping_a_supersession_is_allowed(self) -> None:
        """Replacement is the one legitimate edit, and it touches two fields."""
        stamped = PRODUCT.replace("status: planned", "status: superseded").replace(
            "superseded-by: null", "superseded-by: DEC.2026-02-02.BETTER-PROMISE"
        )
        self.fixture.product.write_text(stamped, encoding="utf-8")
        self.assertEqual(self.fixture.inspect().offenders, ())

    def test_a_supersession_stamp_may_not_smuggle_a_body_edit(self) -> None:
        stamped = (
            PRODUCT.replace("status: planned", "status: superseded")
            .replace(
                "superseded-by: null", "superseded-by: DEC.2026-02-02.BETTER-PROMISE"
            )
            .replace("так, а не иначе", "уже совсем иначе")
        )
        self.fixture.product.write_text(stamped, encoding="utf-8")
        self.assertEqual(len(self.fixture.inspect().offenders), 1)

    def test_supersession_status_without_successor_is_caught(self) -> None:
        self.fixture.product.write_text(
            PRODUCT.replace("status: planned", "status: superseded"), encoding="utf-8"
        )
        self.assertEqual(len(self.fixture.inspect().offenders), 1)

    def test_successor_without_supersession_status_is_caught(self) -> None:
        self.fixture.product.write_text(
            PRODUCT.replace(
                "superseded-by: null", "superseded-by: DEC.2026-02-02.BETTER-PROMISE"
            ),
            encoding="utf-8",
        )
        self.assertEqual(len(self.fixture.inspect().offenders), 1)

    def test_stamping_a_realization_is_allowed(self) -> None:
        """A planned decision becomes active atomically with its evidence."""
        stamped = PRODUCT.replace("status: planned", "status: active").replace(
            "realized: null",
            "realized: tests/arch/test_product_immutability.py::test_stamping_a_realization_is_allowed",
        )
        self.assertNotEqual(
            stamped, PRODUCT, "the fixture must carry an unrealized decision"
        )
        self.fixture.product.write_text(stamped, encoding="utf-8")
        self.assertEqual(self.fixture.inspect().offenders, ())

    def test_realization_without_activation_is_caught(self) -> None:
        stamped = PRODUCT.replace(
            "realized: null",
            "realized: tests/arch/test_product_immutability.py::test_stamping_a_realization_is_allowed",
        )
        self.fixture.product.write_text(stamped, encoding="utf-8")
        self.assertEqual(len(self.fixture.inspect().offenders), 1)

    def test_activation_without_realization_is_caught(self) -> None:
        self.fixture.product.write_text(
            PRODUCT.replace("status: planned", "status: active"), encoding="utf-8"
        )
        self.assertEqual(len(self.fixture.inspect().offenders), 1)

    def test_a_realization_stamp_may_not_smuggle_a_body_edit(self) -> None:
        stamped = (
            PRODUCT.replace("status: planned", "status: active")
            .replace(
                "realized: null",
                "realized: tests/arch/test_product_immutability.py::test_stamping_a_realization_is_allowed",
            )
            .replace("так, а не иначе", "уже совсем иначе")
        )
        self.fixture.product.write_text(stamped, encoding="utf-8")
        self.assertEqual(len(self.fixture.inspect().offenders), 1)

    def test_editing_a_product_rule_without_a_new_ground_is_caught(self) -> None:
        """Any edit that is not a supersession stamp refuses the rule."""
        self.fixture.rule.write_text(
            RULE.replace("так, а не иначе", "уже совсем иначе"), encoding="utf-8"
        )
        verdict = self.fixture.inspect()
        self.assertEqual(len(verdict.offenders), 1)
        self.assertIn("без штампа замены", verdict.offenders[0])

    def test_surface_ledger_change_without_new_product_ground_is_caught(self) -> None:
        self.fixture.surface.write_text("# Surface\n\nunica.new\n", encoding="utf-8")

        verdict = self.fixture.inspect()

        self.assertEqual(len(verdict.offenders), 1)
        self.assertIn("arch/tool-surface.md", verdict.offenders[0])
        self.assertIn("нового продуктового решения", verdict.offenders[0])

    def test_surface_ledger_change_with_new_wire_ground_is_allowed(self) -> None:
        self.fixture.surface.write_text("# Surface\n\nunica.new\n", encoding="utf-8")
        decision = (
            self.fixture.root / "arch" / "decisions" / "2026-03-03-why-it-changes.md"
        )
        decision.write_text(SURFACE_GROUND, encoding="utf-8")
        rule = self.fixture.root / "arch" / "invariants" / "INV.WIRE.SURFACE-CHANGE.md"
        rule.write_text(SURFACE_RULE, encoding="utf-8")

        self.assertEqual(self.fixture.inspect().offenders, ())

    def test_surface_ledger_change_rejects_unrelated_wire_ground(self) -> None:
        self.fixture.surface.write_text("# Surface\n\nunica.new\n", encoding="utf-8")
        decision = (
            self.fixture.root / "arch" / "decisions" / "2026-03-03-why-it-changes.md"
        )
        decision.write_text(UNRELATED_SURFACE_GROUND, encoding="utf-8")
        rule = self.fixture.root / "arch" / "invariants" / "INV.WIRE.SURFACE-CHANGE.md"
        rule.write_text(SURFACE_RULE, encoding="utf-8")

        verdict = self.fixture.inspect()

        self.assertEqual(len(verdict.offenders), 1)
        self.assertIn("arch/tool-surface.md", verdict.offenders[0])

    def test_the_rule_supersession_stamp_shape(self) -> None:
        """One falsifier for the rule-stamp contract, all scenarios as subTests."""
        stamped = RULE.replace("status: active", "status: superseded").replace(
            "check: tests/ci/test_x.py::test_y",
            "check: tests/ci/test_x.py::test_y\nsuperseded-by: [INV.X.Y, INV.X.Z]",
        )

        def offenders_for(rule_text: str):
            self.fixture.rule.write_text(rule_text, encoding="utf-8")
            return self.fixture.inspect().offenders

        with self.subTest(scenario="positive stamp is accepted"):
            self.assertEqual(offenders_for(stamped), ())

        with self.subTest(scenario="body edit is refused"):
            self.assertEqual(
                len(
                    offenders_for(
                        stamped.replace("так, а не иначе", "уже совсем иначе")
                    )
                ),
                1,
            )

        original_fields = {
            "check": "check: tests/ci/test_x.py::test_y",
            "scope": "scope: [wire]",
            "decision": "decision: DEC.2026-01-01.PROMISE",
            "governs": "governs: product",
            "id": "id: INV.WIRE.PROMISE",
        }
        for field, replacement in (
            ("check", "check: tests/ci/test_other.py::test_other"),
            ("scope", "scope: [docs]"),
            ("decision", "decision: DEC.2026-01-01.OTHER"),
            ("governs", "governs: process"),
            ("id", "id: INV.WIRE.OTHER"),
        ):
            with self.subTest(scenario=f"stamp may not move {field}"):
                mutated = stamped.replace(original_fields[field], replacement)
                self.assertEqual(len(offenders_for(mutated)), 1, field)

        with self.subTest(scenario="superseded without a successor list is refused"):
            self.assertEqual(
                len(
                    offenders_for(RULE.replace("status: active", "status: superseded"))
                ),
                1,
            )

        with self.subTest(scenario="successor list on an active rule is refused"):
            listed = RULE.replace(
                "check: tests/ci/test_x.py::test_y",
                "check: tests/ci/test_x.py::test_y\nsuperseded-by: [INV.X.Y]",
            )
            self.assertEqual(len(offenders_for(listed)), 1)

        with self.subTest(scenario="chained stamps stay valid"):
            rule_b = self.fixture.root / "arch" / "invariants" / "INV.WIRE.PROMISE-B.md"
            rule_b.write_text(
                RULE.replace("id: INV.WIRE.PROMISE", "id: INV.WIRE.PROMISE-B"),
                encoding="utf-8",
            )
            self.fixture.rule.write_text(RULE, encoding="utf-8")
            self.fixture._git("add", "arch")
            self.fixture._git(
                "commit", "--quiet", "--no-gpg-sign", "-m", "rule B joins the base"
            )

            self.fixture.rule.write_text(
                stamped.replace("[INV.X.Y, INV.X.Z]", "[INV.WIRE.PROMISE-B]"),
                encoding="utf-8",
            )
            rule_b.write_text(
                RULE.replace("id: INV.WIRE.PROMISE", "id: INV.WIRE.PROMISE-B")
                .replace("status: active", "status: superseded")
                .replace(
                    "check: tests/ci/test_x.py::test_y",
                    "check: tests/ci/test_x.py::test_y"
                    "\nsuperseded-by: [INV.WIRE.PROMISE-C]",
                ),
                encoding="utf-8",
            )
            self.assertEqual(self.fixture.inspect().offenders, ())

    def test_regrounding_an_existing_rule_is_refused(self) -> None:
        """Pointing a rule at a new decision is a silent promise move."""
        self.write_ground()
        self.fixture.rule.write_text(
            RULE.replace("DEC.2026-01-01.PROMISE", "DEC.2026-03-03.WHY-IT-CHANGES"),
            encoding="utf-8",
        )
        verdict = self.fixture.inspect()
        self.assertEqual(len(verdict.offenders), 1)
        self.assertIn("штампа замены", verdict.offenders[0])

    def test_a_surface_ground_with_an_invariant_is_refused(self) -> None:
        error = self.surface_ground_error(INVARIANT_GROUND)
        self.assertIsNotNone(error)
        self.assertIn("decision", error or "")

    def test_a_surface_ground_with_a_planned_decision_is_refused(self) -> None:
        error = self.surface_ground_error(PLANNED_GROUND)
        self.assertIsNotNone(error)
        self.assertIn("planned", error or "")

    def test_a_surface_ground_with_a_process_decision_is_refused(self) -> None:
        error = self.surface_ground_error(PROCESS_GROUND)
        self.assertIsNotNone(error)
        self.assertIn("process", error or "")

    def test_a_surface_ground_with_an_unrealized_decision_is_refused(self) -> None:
        error = self.surface_ground_error(UNREALIZED_GROUND)
        self.assertIsNotNone(error)
        self.assertIn("realized", error or "")

    def test_a_surface_ground_with_missing_evidence_is_refused(self) -> None:
        error = self.surface_ground_error(MISSING_EVIDENCE_GROUND)
        self.assertIsNotNone(error)
        self.assertIn("realized", error or "")

    def test_a_surface_ground_with_a_non_definition_token_is_refused(self) -> None:
        error = self.surface_ground_error(NON_DEFINITION_EVIDENCE_GROUND)
        self.assertIsNotNone(error)
        self.assertIn("realized", error or "")

    def test_a_surface_ground_with_a_python_string_definition_is_refused(
        self,
    ) -> None:
        error = self.surface_ground_error(PYTHON_STRING_EVIDENCE_GROUND)
        self.assertIsNotNone(error)
        self.assertIn("realized", error or "")

    def test_a_surface_ground_with_a_rust_string_function_is_refused(
        self,
    ) -> None:
        error = self.surface_ground_error(RUST_STRING_EVIDENCE_GROUND)
        self.assertIsNotNone(error)
        self.assertIn("realized", error or "")

    def test_a_surface_ground_with_a_rust_declaration_is_refused(self) -> None:
        error = self.surface_ground_error(RUST_DECLARATION_EVIDENCE_GROUND)
        self.assertIsNotNone(error)
        self.assertIn("realized", error or "")

    def test_a_surface_ground_with_a_rust_macro_declaration_is_refused(
        self,
    ) -> None:
        error = self.surface_ground_error(RUST_MACRO_DECLARATION_EVIDENCE_GROUND)
        self.assertIsNotNone(error)
        self.assertIn("realized", error or "")

    def test_an_edit_accepted_on_the_trusted_tip_is_history_not_a_live_change(
        self,
    ) -> None:
        """Edits that already reached origin/main are history; live edits are not."""
        original = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=self.fixture.root,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        regrounded = RULE.replace(
            "decision: DEC.2026-01-01.PROMISE", "decision: DEC.2026-01-01.REPLACED"
        ).replace("так, а не иначе", "уже совсем иначе")
        self.fixture.rule.write_text(regrounded, encoding="utf-8")
        self.fixture._git("add", "arch")
        self.fixture._git(
            "commit", "--quiet", "--no-gpg-sign", "-m", "reground accepted upstream"
        )
        self.fixture._git("branch", "older-base", original)
        self.fixture._git("branch", "origin/main")

        with self.subTest(scenario="accepted state equals the working tree"):
            self.assertEqual(
                IMMUTABILITY.inspect(self.fixture.root, "older-base").offenders, ()
            )

        with self.subTest(scenario="stamp on top of the accepted state"):
            self.fixture.rule.write_text(
                regrounded.replace("status: active", "status: superseded").replace(
                    "scope: [wire]",
                    "scope: [wire]\nsuperseded-by: [INV.WIRE.NEXT]",
                ),
                encoding="utf-8",
            )
            self.assertEqual(
                IMMUTABILITY.inspect(self.fixture.root, "older-base").offenders, ()
            )

        with self.subTest(scenario="a local commit ahead of the trusted tip"):
            self.fixture.rule.write_text(
                regrounded.replace("уже совсем иначе", "иначе вовсе"), encoding="utf-8"
            )
            self.fixture._git("add", "arch")
            self.fixture._git(
                "commit", "--quiet", "--no-gpg-sign", "-m", "local unaccepted edit"
            )
            verdict = IMMUTABILITY.inspect(self.fixture.root, "older-base")
            self.assertEqual(len(verdict.offenders), 1)
            self.assertIn("без штампа замены", verdict.offenders[0])

    def test_an_existing_ground_does_not_cover_a_new_change(self) -> None:
        """A decision written earlier did not foresee today's edit."""
        self.fixture.rule.write_text(
            RULE.replace("так, а не иначе", "уже совсем иначе"), encoding="utf-8"
        )
        verdict = self.fixture.inspect()
        self.assertEqual(len(verdict.offenders), 1)

    def test_editing_a_process_record_is_allowed(self) -> None:
        """A process rule exists to be rebuilt when development gets awkward."""
        self.fixture.process.write_text(
            PROCESS.replace("так, а не иначе", "уже совсем иначе"), encoding="utf-8"
        )
        self.assertEqual(self.fixture.inspect().offenders, ())

    def test_the_side_is_read_from_the_base_not_from_the_edit(self) -> None:
        """Otherwise the rule is escaped by relabelling the record on the way out."""
        self.fixture.product.write_text(
            PRODUCT.replace("governs: product", "governs: process").replace(
                "так, а не иначе", "уже совсем иначе"
            ),
            encoding="utf-8",
        )
        self.assertEqual(len(self.fixture.inspect().offenders), 1)


class LiveTreeTests(unittest.TestCase):
    def test_the_live_tree_holds_no_edited_product_record(self) -> None:
        """Green here is worth only as much as the count it reports.

        `arch/` has not reached `main`, so today this compares nothing. The
        assertion states that plainly instead of letting an empty comparison
        read as a clean one.
        """
        base = subprocess.run(
            ["git", "rev-parse", "--verify", "--quiet", "origin/main"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        if base.returncode != 0:
            self.skipTest("origin/main is not fetched in this checkout")

        verdict = IMMUTABILITY.inspect(REPO_ROOT, "origin/main")
        self.assertEqual(verdict.offenders, ())

        on_base = subprocess.run(
            ["git", "ls-tree", "-r", "--name-only", "origin/main", "--", "arch/"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.split()
        if not on_base:
            self.assertEqual(
                verdict.compared,
                0,
                "no registry on the base branch, so nothing can be compared yet",
            )
        else:
            self.assertGreater(
                verdict.compared,
                0,
                "the base branch carries records, so the guard must have compared some",
            )


if __name__ == "__main__":
    unittest.main()
