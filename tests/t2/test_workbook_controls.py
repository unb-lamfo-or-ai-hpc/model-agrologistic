"""Approved workbook controls: standard-library validation without a solver."""

import importlib.util
import pathlib
import unittest
from types import SimpleNamespace
from unittest.mock import patch

PATH = pathlib.Path(__file__).resolve().parents[2] / "scripts/t2/workbook_controls.py"
spec = importlib.util.spec_from_file_location("workbook_controls", PATH)
controls = importlib.util.module_from_spec(spec)
spec.loader.exec_module(controls)


def rows(**changes):
    values = dict(
        scenario_id="baseline",
        K=1,
        beta_enabled=0,
        beta=None,
        alpha_enabled=0,
        alpha=None,
        justification="Reference case.",
    )
    values.update(changes)
    return list(values.items())


class WorkbookControls(unittest.TestCase):
    def test_reader_requires_v2_and_closes_on_rejection(self):
        class Book(dict):
            closed = False

            def close(self):
                self.closed = True

        book = Book(
            Identification=SimpleNamespace(
                values=[
                    ("item", "value"),
                    ("schema", "agrologistic-effective-baseline-v1"),
                    ("workbook_version", 1),
                ]
            )
        )
        loader = SimpleNamespace(load_workbook=lambda *a, **kw: book)
        with patch.dict("sys.modules", {"openpyxl": loader}):
            with self.assertRaisesRegex(ValueError, "version-two"):
                controls.read_specification("unused.xlsx")
        self.assertTrue(book.closed)

    def test_reader_returns_the_one_authoritative_control_selection(self):
        class Book(dict):
            def close(self):
                pass

        book = Book(
            Identification=SimpleNamespace(
                values=[
                    ("item", "value"),
                    ("schema", "agrologistic-effective-baseline-v1"),
                    ("workbook_version", 2),
                ]
            ),
            Controls=SimpleNamespace(
                values=[
                    ("parameter", "value", "unit", "meaning", "reference"),
                    *rows(scenario_id="K2", K=2),
                ]
            ),
        )
        with patch.dict(
            "sys.modules", {"openpyxl": SimpleNamespace(load_workbook=lambda *a, **kw: book)}
        ):
            got = controls.read_specification("unused.xlsx")
        self.assertEqual(got["multipliers"], {"candidate_limit": 2, "expansion_limit": 2})

    def test_neutral_disables_policies(self):
        got = controls.specification(rows())
        self.assertEqual(got["multipliers"], {"candidate_limit": 1, "expansion_limit": 1})
        self.assertIsNone(got["beta"])
        self.assertIsNone(got["alpha"])

    def test_one_K_scales_only_two_limits(self):
        got = controls.specification(rows(scenario_id="K2", K=2))
        self.assertEqual(got["multipliers"], {"candidate_limit": 2, "expansion_limit": 2})
        with self.assertRaisesRegex(ValueError, "Unknown control"):
            controls.specification(rows() + [("candidate_limit", 2)])

    def test_policies_activate_zero_and_one_as_valid_fractions(self):
        got = controls.specification(
            rows(scenario_id="policy", beta_enabled=1, beta=1, alpha_enabled=1, alpha=0)
        )
        self.assertEqual((got["beta"], got["alpha"]), (1, 0))

    def test_disabled_policy_values_do_not_activate(self):
        got = controls.specification(rows(beta=0.9, alpha=0.6))
        self.assertIsNone(got["beta"])
        self.assertIsNone(got["alpha"])

    def test_invalid_K(self):
        for value in (0, -1, True, None, float("nan"), float("inf"), "2"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                controls.specification(rows(K=value))

    def test_invalid_fraction_or_missing_enabled_input(self):
        for name in ("beta", "alpha"):
            for value in (-0.1, 1.1, True, float("nan"), None):
                with self.subTest(name=name, value=value), self.assertRaises(ValueError):
                    controls.specification(
                        rows(scenario_id="policy", **{name + "_enabled": 1, name: value})
                    )

    def test_duplicate_missing_unknown_and_invalid_switch(self):
        cases = [
            rows() + [("K", 2)],
            rows()[1:],
            rows() + [("new_parameter", 1)],
            rows(beta_enabled=2),
        ]
        for case in cases:
            with self.assertRaises(ValueError):
                controls.specification(case)

    def test_nonneutral_case_cannot_be_baseline(self):
        for change in (
            {"K": 2},
            {"beta_enabled": 1, "beta": 0.9},
            {"alpha_enabled": 1, "alpha": 0.6},
        ):
            with self.assertRaisesRegex(ValueError, "own scenario"):
                controls.specification(rows(**change))


if __name__ == "__main__":
    unittest.main()
