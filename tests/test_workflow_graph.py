"""End-to-end tests for the complete LangGraph analysis workflow."""
import unittest
import uuid
from backend.services.ingestion import ingestion_service
from backend.graph.state import AnalysisState
from backend.graph.graph import workflow_engine

class TestWorkflowGraph(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        csv_data = b"""region,product,sales,profit
North,Widget,1000,200
North,Gadget,1200,240
South,Widget,800,160
South,Gadget,900,180
East,Widget,600,120
West,Gadget,1500,300
"""
        cls.schema, cls.suggestions = ingestion_service.ingest_csv(csv_data, "sales_pipeline.csv")

    def test_existing_skill_execution(self):
        state = AnalysisState(
            session_id=str(uuid.uuid4()),
            job_id=str(uuid.uuid4()),
            dataset_id=self.schema.dataset_id,
            question="Find correlation between sales and profit"
        )
        res = workflow_engine.run(state)
        self.assertEqual(res.status, "completed")
        self.assertTrue(res.skill_found)
        self.assertEqual(res.skill_id, "correlation_001")
        self.assertIsNotNone(res.sql_query)
        self.assertIsNotNone(res.sdk_output)
        self.assertEqual(res.sdk_output["value"], 1.0)
        self.assertIsNotNone(res.chart_spec)
        self.assertIn("chart:", res.markdown)

    def test_irrelevant_question_handling(self):
        state = AnalysisState(
            session_id=str(uuid.uuid4()),
            job_id=str(uuid.uuid4()),
            dataset_id=self.schema.dataset_id,
            question="What is tomorrow's weather in Tokyo?"
        )
        res = workflow_engine.run(state)
        self.assertEqual(res.status, "completed")
        self.assertFalse(res.is_relevant)
        self.assertTrue(len(res.suggested_analyses) > 0)
        self.assertIn("Not Directly Relevant", res.markdown)

    def test_human_approval_pause_and_resume(self):
        unique_metric = f"herfindahl_index_{uuid.uuid4().hex[:6]}"
        state = AnalysisState(
            session_id=str(uuid.uuid4()),
            job_id=str(uuid.uuid4()),
            dataset_id=self.schema.dataset_id,
            question=f"Compute {unique_metric} for sales"
        )
        # Step 1: Pauses for human approval
        res = workflow_engine.run(state)
        self.assertEqual(res.status, "awaiting_approval")
        self.assertTrue(res.requires_approval)
        self.assertIsNotNone(res.analysis_method)

        # Step 2: User approves -> resumes execution
        res.user_approved = True
        res_approved = workflow_engine.run(res)
        self.assertEqual(res_approved.status, "completed")
        self.assertFalse(res_approved.requires_approval)
        self.assertIsNotNone(res_approved.markdown)

if __name__ == "__main__":
    unittest.main()
