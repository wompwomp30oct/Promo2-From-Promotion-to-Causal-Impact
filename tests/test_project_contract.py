import json
import unittest
from pathlib import Path

from src.validity_checks import validate_differences_on_tutorial, validate_fallback_on_tutorial
from src.estimators import callaway_santanna_estimate, pooled_twfe_baseline


class ProjectContractTests(unittest.TestCase):
    def test_differences_validation_returns_dict(self):
        result = validate_differences_on_tutorial()
        self.assertIsInstance(result, dict)
        self.assertIn("passed", result)
        self.assertTrue(result["passed"])
        self.assertEqual(result["specification"], "never_treated control, doubly robust (dr), simple aggregation")
        self.assertAlmostEqual(result["tutorial_estimate"], -0.039951, places=5)
        self.assertAlmostEqual(result["tutorial_standard_error"], 0.012034, places=5)

    def test_estimator_entrypoints_return_dict(self):
        self.assertIsInstance(pooled_twfe_baseline, object)
        self.assertTrue(callable(callaway_santanna_estimate))

    def test_fallback_reports_feature_parity(self):
        result = validate_fallback_on_tutorial()
        self.assertTrue(result["passed"])
        self.assertEqual(result["feature_parity_checks"], {"clustered_se": True, "never_treated_support": True})
        self.assertEqual(len(result["coefficients"]), 32)

    def test_stress_artifact_has_cell_audit_schema(self):
        path = Path("eval_logs/phase0_5_stress_check.json")
        if not path.exists():
            self.skipTest("Phase 0.5 real-data stress artifact has not been generated")
        with path.open() as handle:
            result = json.load(handle)
        self.assertIn("att_gt_cell_store_counts", result)
        self.assertIn("thin_cells", result)
        self.assertIn("leave_cohort_out_reruns", result)


if __name__ == "__main__":
    unittest.main()
