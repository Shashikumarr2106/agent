"""Unit tests for Analysis SDK deterministic calculations."""
import unittest
from backend.sdk import sdk, execute_sandboxed_code

class TestAnalysisSDK(unittest.TestCase):

    def setUp(self):
        self.data_xy = [
            {"sales": 100, "profit": 20},
            {"sales": 200, "profit": 40},
            {"sales": 300, "profit": 60},
            {"sales": 400, "profit": 80}
        ]
        self.values = [10.0, 20.0, 30.0, 40.0, 50.0]

    def test_mean(self):
        res = sdk.run("mean", self.values)
        self.assertEqual(res.status, "success")
        self.assertEqual(res.value, 30.0)

    def test_std_and_cv(self):
        res_cv = sdk.run("coefficient_of_variation", self.values)
        self.assertEqual(res_cv.status, "success")
        self.assertAlmostEqual(res_cv.value, 52.70, places=1)

    def test_pearson_correlation(self):
        res = sdk.run("pearson_correlation", self.data_xy, x_col="sales", y_col="profit")
        self.assertEqual(res.status, "success")
        self.assertEqual(res.value, 1.0)
        self.assertEqual(res.metric, "pearson_r")

    def test_linear_regression(self):
        res = sdk.run("linear_regression", self.data_xy, x_col="sales", y_col="profit")
        self.assertEqual(res.status, "success")
        self.assertEqual(res.value["slope"], 0.2)
        self.assertEqual(res.value["intercept"], 0.0)
        self.assertEqual(res.value["r_squared"], 1.0)

    def test_group_aggregation(self):
        grouped_data = [
            {"region": "North", "sales": 100},
            {"region": "North", "sales": 200},
            {"region": "South", "sales": 300}
        ]
        res = sdk.run("group_aggregation", grouped_data, group_col="region", value_col="sales", agg_func="sum")
        self.assertEqual(res.status, "success")
        results = {r["region"]: r["metric"] for r in res.value}
        self.assertEqual(results["North"], 300)
        self.assertEqual(results["South"], 300)

    def test_sandbox_safety(self):
        # Disallow imports
        bad_res1 = execute_sandboxed_code("import os", [])
        self.assertEqual(bad_res1.status, "error")
        self.assertIn("Security policy violation", bad_res1.error)

        # Disallow open
        bad_res2 = execute_sandboxed_code("open('/etc/passwd')", [])
        self.assertEqual(bad_res2.status, "error")

        # Allow safe math
        good_res = execute_sandboxed_code("result = sum(d['sales'] for d in data) / len(data)", self.data_xy)
        self.assertEqual(good_res.status, "success")
        self.assertEqual(good_res.value, 250.0)

if __name__ == "__main__":
    unittest.main()
