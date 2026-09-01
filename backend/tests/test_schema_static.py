import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class SchemaStaticTest(unittest.TestCase):
    def test_all_planned_tables_are_declared(self) -> None:
        tables: set[str] = set()
        for path in (ROOT / "app" / "models").glob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in tree.body:
                if not isinstance(node, ast.ClassDef):
                    continue
                for statement in node.body:
                    if (
                        isinstance(statement, ast.Assign)
                        and any(isinstance(t, ast.Name) and t.id == "__tablename__" for t in statement.targets)
                        and isinstance(statement.value, ast.Constant)
                    ):
                        tables.add(str(statement.value.value))

        expected = {
            "users", "user_contacts", "password_credentials", "auth_challenges", "sessions",
            "roles", "permissions", "role_permissions", "user_roles", "organizations",
            "organization_memberships", "user_preferences", "businesses", "business_memberships",
            "skills", "business_skills", "business_goals", "business_channels",
            "diagnostic_sessions", "diagnostic_answers", "formalization_routes",
            "formalization_steps", "consent_purposes", "consent_versions", "user_consents",
            "data_export_requests", "deletion_requests", "financial_categories",
            "financial_movements", "cost_items", "pricing_scenarios", "pricing_scenario_costs",
            "conversations", "messages", "ai_runs", "ai_retrievals", "message_citations",
            "response_feedback", "generated_contents", "audio_artifacts", "escalation_events",
            "source_publishers", "sources", "source_versions", "source_status_history",
            "ingestion_jobs", "source_chunks", "embedding_models", "source_chunk_embeddings",
            "source_checks", "audit_events", "security_alerts", "system_settings",
            "background_jobs", "evaluation_sets", "evaluation_cases", "evaluation_runs",
            "evaluation_results", "research_participants", "usability_sessions", "task_results",
            "survey_responses",
        }
        self.assertEqual(tables, expected)

    def test_mariadb_specific_objects_exist(self) -> None:
        migration = (ROOT / "alembic" / "versions" / "0001_initial_schema.py").read_text(
            encoding="utf-8"
        )
        for token in (
            "CREATE FULLTEXT INDEX idx_source_chunks_fulltext",
            "CREATE VECTOR INDEX idx_chunk_embedding",
            "M=8 DISTANCE=cosine",
            "CREATE VIEW v_monthly_financial_summary",
            "trg_audit_events_no_update",
            "trg_audit_events_no_delete",
        ):
            self.assertIn(token, migration)

    def test_sensitive_binary_files_are_external(self) -> None:
        model_text = "\n".join(
            path.read_text(encoding="utf-8")
            for path in (ROOT / "app" / "models").glob("*.py")
        )
        self.assertNotIn("LargeBinary", model_text)
        self.assertIn("storage_key", model_text)
        self.assertIn("content_encrypted", model_text)

    def test_api_contract_routes_are_present(self) -> None:
        main = (ROOT / "app" / "main.py").read_text(encoding="utf-8")
        for route in (
            "/businesses",
            "/consents",
            "/finance/movements",
            "/finance/pricing",
            "/assistant/query",
            "/feedback",
            "/source-versions",
        ):
            self.assertIn(route, main)


if __name__ == "__main__":
    unittest.main()

