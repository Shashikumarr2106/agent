"""Skill Management and Vector Retrieval Service."""
import json
import re
from typing import Any, Dict, List, Optional
from ..models.skill import Skill, SkillVersion, SkillSearchResult
from .database import db_service
from .embedding import embedding_service, cosine_similarity

class SkillService:
    def __init__(self):
        self.seed_default_skills()

    def search_skills(self, query: str, threshold: float = 0.5, top_k: int = 3) -> List[SkillSearchResult]:
        """Perform semantic vector similarity search against active skills."""
        query_vec = embedding_service.get_embedding(query)
        conn = db_service._get_connection()
        cursor = conn.cursor()

        # Retrieve all latest active skill versions
        cursor.execute("""
            SELECT sv.*, s.current_version
            FROM skill_versions sv
            JOIN skills s ON sv.skill_id = s.skill_id
            WHERE s.status = 'active' AND sv.version = s.current_version
        """)
        rows = cursor.fetchall()
        conn.close()

        results = []
        STOPWORDS = {"for", "the", "and", "with", "from", "between", "calculate", "compute", "find", "get", "show", "what", "which", "how", "across", "over", "into", "each", "per"}
        query_words = set(w.lower() for w in re.findall(r'\b[a-zA-Z]{3,}\b', query)) - STOPWORDS
        for r in rows:
            emb_json = r["embedding_json"]
            if not emb_json:
                continue
            emb = json.loads(emb_json)
            sim = cosine_similarity(query_vec, emb)

            # Keyword boost for direct concept matches (excluding stopwords)
            name_words = set(w.lower() for w in re.findall(r'\b[a-zA-Z]{3,}\b', r["name"])) - STOPWORDS
            desc_words = set(w.lower() for w in re.findall(r'\b[a-zA-Z]{3,}\b', r["description"])) - STOPWORDS

            common_name = query_words.intersection(name_words)
            common_desc = query_words.intersection(desc_words)

            if common_name:
                sim = min(1.0, sim + 0.35 * len(common_name))
            elif common_desc:
                sim = min(1.0, sim + 0.20 * len(common_desc))

            if sim >= threshold:
                sv = SkillVersion(
                    skill_id=r["skill_id"],
                    version=r["version"],
                    name=r["name"],
                    description=r["description"],
                    required_inputs=json.loads(r["required_inputs"]) if r["required_inputs"] else [],
                    formula=r["formula"],
                    logic=r["logic"],
                    code=r["code"],
                    examples=json.loads(r["examples_json"]) if r["examples_json"] else [],
                    validation_rules=json.loads(r["validation_rules_json"]) if r["validation_rules_json"] else [],
                    created_from_job=r["created_from_job"]
                )
                results.append(SkillSearchResult(
                    skill_id=r["skill_id"],
                    name=r["name"],
                    description=r["description"],
                    version=r["version"],
                    similarity=round(sim, 4),
                    skill_version=sv
                ))

        results.sort(key=lambda x: x.similarity, reverse=True)
        return results[:top_k]

    def get_skill(self, skill_id: str) -> Optional[Skill]:
        conn = db_service._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM skills WHERE skill_id = ?", (skill_id,))
        s_row = cursor.fetchone()
        if not s_row:
            conn.close()
            return None

        cursor.execute("SELECT * FROM skill_versions WHERE skill_id = ? ORDER BY version ASC", (skill_id,))
        v_rows = cursor.fetchall()
        conn.close()

        versions = {}
        for r in v_rows:
            versions[r["version"]] = SkillVersion(
                skill_id=r["skill_id"],
                version=r["version"],
                name=r["name"],
                description=r["description"],
                required_inputs=json.loads(r["required_inputs"]) if r["required_inputs"] else [],
                formula=r["formula"],
                logic=r["logic"],
                code=r["code"],
                examples=json.loads(r["examples_json"]) if r["examples_json"] else [],
                validation_rules=json.loads(r["validation_rules_json"]) if r["validation_rules_json"] else [],
                created_from_job=r["created_from_job"]
            )

        return Skill(
            skill_id=s_row["skill_id"],
            name=s_row["name"],
            description=s_row["description"],
            current_version=s_row["current_version"],
            versions=versions,
            status=s_row["status"]
        )

    def get_skill_version(self, skill_id: str, version: int) -> Optional[SkillVersion]:
        conn = db_service._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM skill_versions WHERE skill_id = ? AND version = ?", (skill_id, version))
        r = cursor.fetchone()
        conn.close()
        if not r:
            return None
        return SkillVersion(
            skill_id=r["skill_id"],
            version=r["version"],
            name=r["name"],
            description=r["description"],
            required_inputs=json.loads(r["required_inputs"]) if r["required_inputs"] else [],
            formula=r["formula"],
            logic=r["logic"],
            code=r["code"],
            examples=json.loads(r["examples_json"]) if r["examples_json"] else [],
            validation_rules=json.loads(r["validation_rules_json"]) if r["validation_rules_json"] else [],
            created_from_job=r["created_from_job"]
        )

    def save_new_skill(self, skill_version: SkillVersion) -> Skill:
        """Section 25 of Flow.md: Save a newly approved skill with embedding."""
        text_for_embedding = f"{skill_version.name} {skill_version.description} {skill_version.logic}"
        vec = embedding_service.get_embedding(text_for_embedding)

        conn = db_service._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO skills (skill_id, name, description, current_version, status, updated_at)
            VALUES (?, ?, ?, ?, 'active', CURRENT_TIMESTAMP)
        """, (skill_version.skill_id, skill_version.name, skill_version.description, skill_version.version))

        cursor.execute("""
            INSERT OR REPLACE INTO skill_versions (
                skill_id, version, name, description, required_inputs, formula, logic, code,
                examples_json, validation_rules_json, embedding_json, created_from_job
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            skill_version.skill_id,
            skill_version.version,
            skill_version.name,
            skill_version.description,
            json.dumps(skill_version.required_inputs),
            skill_version.formula,
            skill_version.logic,
            skill_version.code,
            json.dumps(skill_version.examples),
            json.dumps(skill_version.validation_rules),
            json.dumps(vec),
            skill_version.created_from_job
        ))

        conn.commit()
        conn.close()
        return self.get_skill(skill_version.skill_id)

    def update_skill_version(
        self,
        skill_id: str,
        modifications: Dict[str, Any],
        feedback: str = None
    ) -> SkillVersion:
        """Section 26 & 27: Create a new version (e.g. v2, v3) without overwriting v1."""
        existing = self.get_skill(skill_id)
        if not existing:
            raise ValueError(f"Skill '{skill_id}' does not exist.")

        new_version_num = existing.current_version + 1
        current = existing.versions[existing.current_version]

        updated_version = SkillVersion(
            skill_id=skill_id,
            version=new_version_num,
            name=modifications.get("name", current.name),
            description=modifications.get("description", current.description),
            required_inputs=modifications.get("required_inputs", current.required_inputs),
            formula=modifications.get("formula", current.formula),
            logic=modifications.get("logic", f"{current.logic} (Updated: {feedback})"),
            code=modifications.get("code", current.code),
            examples=modifications.get("examples", current.examples),
            validation_rules=modifications.get("validation_rules", current.validation_rules),
            created_from_job=modifications.get("job_id", current.created_from_job)
        )

        self.save_new_skill(updated_version)
        return updated_version

    def seed_default_skills(self):
        """Seed predefined standard skills specified in Flow.md."""
        seeds = [
            SkillVersion(
                skill_id="correlation_001",
                version=1,
                name="Pearson Correlation Analysis",
                description="Find linear correlation and statistical association between two numerical columns (e.g., sales and profit)",
                required_inputs=["x", "y"],
                formula="r = Σ((x - x̄)(y - ȳ)) / sqrt(Σ(x - x̄)² Σ(y - ȳ)²)",
                logic="Use Analysis SDK method 'pearson_correlation' on paired numerical observations.",
                code="result = sdk.run('pearson_correlation', data, x_col=x_col, y_col=y_col)",
                examples=[{"input": {"x": [1, 2, 3], "y": [2, 4, 6]}, "output": 1.0}],
                validation_rules=["Result must be in range [-1.0, 1.0]", "Sample size >= 3"]
            ),
            SkillVersion(
                skill_id="coefficient_variation_001",
                version=1,
                name="Coefficient of Variation",
                description="Calculate relative dispersion and volatility (CV = std / mean * 100) for a metric such as revenue or profit",
                required_inputs=["values"],
                formula="CV = (standard_deviation / mean) * 100",
                logic="Use Analysis SDK method 'coefficient_of_variation' with sample standard deviation (ddof=1).",
                code="result = sdk.run('coefficient_of_variation', data, column=column)",
                examples=[{"input": {"values": [10, 20, 30]}, "output": 50.0}],
                validation_rules=["Mean must not be zero", "CV must be >= 0"]
            ),
            SkillVersion(
                skill_id="summary_stats_001",
                version=1,
                name="Descriptive Summary Statistics",
                description="Compute mean, median, standard deviation, quartiles, IQR, min, and max for a column",
                required_inputs=["values"],
                formula="Descriptive parametric and non-parametric summary measures",
                logic="Use Analysis SDK method 'summary_statistics'.",
                code="result = sdk.run('summary_statistics', data, column=column)",
                examples=[],
                validation_rules=["Sample count > 0"]
            ),
            SkillVersion(
                skill_id="linear_regression_001",
                version=1,
                name="Linear Regression Analysis",
                description="Model relationship between independent variable X and dependent variable Y (y = mx + b)",
                required_inputs=["x", "y"],
                formula="y = slope * x + intercept",
                logic="Use Analysis SDK method 'linear_regression'.",
                code="result = sdk.run('linear_regression', data, x_col=x_col, y_col=y_col)",
                examples=[],
                validation_rules=["R-squared in [0.0, 1.0]"]
            ),
            SkillVersion(
                skill_id="group_aggregation_001",
                version=1,
                name="Category Group Aggregation",
                description="Compute sum, average, min, or max of a numeric column grouped across a categorical dimension",
                required_inputs=["group_by", "metric_column"],
                formula="Aggregate value by category dimension",
                logic="Use Analysis SDK method 'group_aggregation'.",
                code="result = sdk.run('group_aggregation', data, group_col=group_col, value_col=value_col, agg_func=agg_func)",
                examples=[],
                validation_rules=["Category groups >= 1"]
            )
        ]

        for s in seeds:
            conn = db_service._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM skill_versions WHERE skill_id = ? AND version = ?", (s.skill_id, s.version))
            exists = cursor.fetchone()
            conn.close()
            if not exists:
                self.save_new_skill(s)

skill_service = SkillService()
