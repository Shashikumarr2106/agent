"""End-to-end unit tests for all REST API endpoints using FastAPI TestClient."""
import unittest
import io
import uuid
from backend.main import app

try:
    from fastapi.testclient import TestClient
    HAS_TESTCLIENT = True
except ImportError:
    HAS_TESTCLIENT = False

class TestAPIEndpoints(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if not HAS_TESTCLIENT or app is None:
            raise unittest.SkipTest("FastAPI TestClient not available")
        cls.client = TestClient(app)

    def test_01_health_and_stats(self):
        # Root health
        res = self.client.get("/health")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "healthy")
        self.assertIn("database", data)

        # Versioned health
        res_v1 = self.client.get("/api/v1/health")
        self.assertEqual(res_v1.status_code, 200)

        # Stats
        stats = self.client.get("/stats").json()
        self.assertIn("total_datasets", stats)
        self.assertIn("total_skills", stats)

    def test_02_dataset_lifecycle(self):
        # 1. Upload CSV
        csv_content = b"region,sales,profit\nNorth,100,20\nSouth,200,40\nEast,300,60\nWest,400,80\n"
        upload_res = self.client.post(
            "/datasets/upload",
            files={"file": ("test_sales.csv", io.BytesIO(csv_content), "text/csv")}
        )
        self.assertEqual(upload_res.status_code, 200)
        ds_data = upload_res.json()
        dataset_id = ds_data["dataset_id"]
        self.assertEqual(ds_data["row_count"], 4)
        self.assertEqual(ds_data["filename"], "test_sales.csv")

        # 2. List datasets
        list_res = self.client.get("/datasets")
        self.assertEqual(list_res.status_code, 200)
        datasets = list_res.json()
        self.assertTrue(any(d["dataset_id"] == dataset_id for d in datasets))

        # 3. Get dataset schema & sample
        get_res = self.client.get(f"/datasets/{dataset_id}")
        self.assertEqual(get_res.status_code, 200)
        self.assertEqual(len(get_res.json()["sample_data"]), 4)

        # 4. Preview dataset with pagination
        preview_res = self.client.get(f"/datasets/{dataset_id}/preview?limit=2&offset=1")
        self.assertEqual(preview_res.status_code, 200)
        prev = preview_res.json()
        self.assertEqual(len(prev["rows"]), 2)
        self.assertEqual(prev["total_rows"], 4)

        # 5. Summary statistics via Analysis SDK
        summary_res = self.client.get(f"/datasets/{dataset_id}/summary")
        self.assertEqual(summary_res.status_code, 200)
        summary = summary_res.json()
        self.assertIn("sales", summary["summaries"])
        self.assertEqual(summary["summaries"]["sales"]["mean"], 250.0)

        # 6. Delete dataset
        del_res = self.client.delete(f"/datasets/{dataset_id}")
        self.assertEqual(del_res.status_code, 200)
        self.assertTrue(del_res.json()["success"])

    def test_03_chat_and_analysis_workflow(self):
        # Ingest a dataset for chat testing
        csv_content = b"x,y\n1,2\n2,4\n3,6\n4,8\n5,10\n"
        upload_res = self.client.post(
            "/datasets/upload",
            files={"file": ("linear_data.csv", io.BytesIO(csv_content), "text/csv")}
        )
        dataset_id = upload_res.json()["dataset_id"]

        # Run chat with existing skill (correlation)
        chat_res = self.client.post("/chat", json={
            "dataset_id": dataset_id,
            "question": "What is the correlation between x and y?"
        })
        self.assertEqual(chat_res.status_code, 200)
        chat_data = chat_res.json()
        job_id = chat_data["job_id"]
        self.assertEqual(chat_data["status"], "completed")
        self.assertIsNotNone(chat_data["sdk_output"])
        self.assertEqual(chat_data["sdk_output"]["value"], 1.0)
        self.assertIsNotNone(chat_data["chart"])

        # Inspect job via GET /jobs/{job_id}
        job_res = self.client.get(f"/jobs/{job_id}")
        self.assertEqual(job_res.status_code, 200)
        self.assertEqual(job_res.json()["job_id"], job_id)

        # Inspect execution logs via GET /jobs/{job_id}/logs
        logs_res = self.client.get(f"/jobs/{job_id}/logs")
        self.assertEqual(logs_res.status_code, 200)
        self.assertTrue(logs_res.json()["logs_count"] > 0)

        # Test feedback endpoint on completed job
        fb_res = self.client.post("/analysis/feedback", json={
            "job_id": job_id,
            "feedback": "Use non-parametric Spearman rank correlation"
        })
        self.assertEqual(fb_res.status_code, 200)
        self.assertIn("revised_skill", fb_res.json())

    def test_04_direct_sdk_execution(self):
        csv_content = b"val\n10\n20\n30\n40\n50\n"
        upload_res = self.client.post(
            "/datasets/upload",
            files={"file": ("stats_data.csv", io.BytesIO(csv_content), "text/csv")}
        )
        dataset_id = upload_res.json()["dataset_id"]

        res = self.client.post("/analysis/direct-execute", json={
            "dataset_id": dataset_id,
            "method": "summary_statistics",
            "params": {"column": "val"}
        })
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["value"]["mean"], 30.0)

    def test_05_skills_api(self):
        # 1. List skills
        list_res = self.client.get("/skills")
        self.assertEqual(list_res.status_code, 200)
        skills = list_res.json()
        self.assertTrue(len(skills) >= 5)

        # 2. Search skills
        search_res = self.client.post("/skills/search", json={
            "query": "linear correlation between two variables",
            "threshold": 0.4
        })
        self.assertEqual(search_res.status_code, 200)
        self.assertTrue(len(search_res.json()) > 0)

        # 3. Create a new skill
        new_skill_payload = {
            "name": "IQR Outlier Analysis",
            "description": "Identify extreme values using Tukey 1.5 IQR fences",
            "required_inputs": ["column"],
            "formula": "IQR = Q3 - Q1; Lower = Q1 - 1.5*IQR; Upper = Q3 + 1.5*IQR",
            "logic": "Compute 25th and 75th percentiles and tag values outside bounds",
            "validation_rules": ["Non-empty sample"]
        }
        create_res = self.client.post("/skills", json=new_skill_payload)
        self.assertEqual(create_res.status_code, 200)
        created_skill = create_res.json()
        skill_id = created_skill["skill_id"]

        # 4. Update skill (version bump)
        update_res = self.client.put(f"/skills/{skill_id}", json={
            "description": "Identify extreme values using Tukey 3.0 IQR extreme fences",
            "feedback": "Updated fence multiplier to 3.0 for extreme outliers"
        })
        self.assertEqual(update_res.status_code, 200)
        self.assertEqual(update_res.json()["version"], 2)

    def test_06_sessions_api(self):
        # 1. Create session
        create_res = self.client.post("/sessions", json={
            "user_id": "test_user_42"
        })
        self.assertEqual(create_res.status_code, 200)
        session_id = create_res.json()["session_id"]

        # 2. Get session
        get_res = self.client.get(f"/sessions/{session_id}")
        self.assertEqual(get_res.status_code, 200)
        self.assertEqual(get_res.json()["session_id"], session_id)

        # 3. Delete session
        del_res = self.client.delete(f"/sessions/{session_id}")
        self.assertEqual(del_res.status_code, 200)
        self.assertTrue(del_res.json()["success"])

if __name__ == "__main__":
    unittest.main()
