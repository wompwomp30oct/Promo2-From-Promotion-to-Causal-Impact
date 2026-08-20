import unittest

from src.validity_checks import validate_differences_on_tutorial
from src.estimators import callaway_santanna_estimate, pooled_twfe_baseline


class ProjectContractTests(unittest.TestCase):
    def test_differences_validation_returns_dict(self):
        result = validate_differences_on_tutorial()
        self.assertIsInstance(result, dict)
        self.assertIn("passed", result)

    def test_estimator_entrypoints_return_dict(self):
        self.assertIsInstance(pooled_twfe_baseline, object)
        self.assertTrue(callable(callaway_santanna_estimate))


if __name__ == "__main__":
    unittest.main()
