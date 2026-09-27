"""Unit tests for CSV ingestion, schema detection, and SQL security enforcement."""
import unittest
from backend.services.ingestion import ingestion_service
from backend.services.database import db_service

class TestIngestionAndSQL(unittest.TestCase):

    def setUp(self):
        self.csv_bytes = b"""region,category,revenue,margin
North,Electronics,50000,12000
North,Clothing,30000,8000
South,Electronics,40000,10000
South,Clothing,25000,6000
"""
        self.schema, self.suggestions = ingestion_service.ingest_csv(self.csv_bytes, "test_sales.csv")

    def test_schema_detection(self):
        self.assertEqual(self.schema.row_count, 4)
        self.assertEqual(self.schema.column_count, 4)
        self.assertIn("revenue", self.schema.numeric_columns)
        self.assertIn("region", self.schema.categorical_columns)
        self.assertTrue(len(self.suggestions) > 0)

    def test_sql_security_blocks_dangerous_queries(self):
        # DROP blocked
        ok, err = db_service.validate_sql_security(f'DROP TABLE "{self.schema.table_name}"')
        self.assertFalse(ok)
        self.assertIn("Only SELECT", err)

        # DELETE blocked
        ok, err = db_service.validate_sql_security(f'DELETE FROM "{self.schema.table_name}"')
        self.assertFalse(ok)

        # INSERT blocked
        ok, err = db_service.validate_sql_security(f'INSERT INTO "{self.schema.table_name}" VALUES (1, "East", "Food", 10, 2)')
        self.assertFalse(ok)

        # SELECT allowed
        ok, err = db_service.validate_sql_security(f'SELECT region, AVG(revenue) FROM "{self.schema.table_name}" GROUP BY region')
        self.assertTrue(ok)
        self.assertIsNone(err)

    def test_sql_execution(self):
        sql = f'SELECT region, SUM(revenue) as total_rev FROM "{self.schema.table_name}" GROUP BY region ORDER BY total_rev DESC'
        rows, err = db_service.execute_dataset_sql(sql)
        self.assertIsNone(err)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["region"], "North")
        self.assertEqual(rows[0]["total_rev"], 80000.0)

if __name__ == "__main__":
    unittest.main()
