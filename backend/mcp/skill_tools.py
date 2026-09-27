"""Skill MCP Tools exposing skill search, retrieval, saving, and versioning."""
from typing import Any, Dict, List, Optional
from ..services.skill_service import skill_service
from ..models.skill import SkillVersion

def search_skills(query: str, threshold: float = 0.65, top_k: int = 3) -> Dict[str, Any]:
    """Semantic vector search for reusable analysis skills."""
    matches = skill_service.search_skills(query=query, threshold=threshold, top_k=top_k)
    return {
        "found": len(matches) > 0,
        "count": len(matches),
        "matches": [m.model_dump() for m in matches]
    }

def get_skill(skill_id: str) -> Dict[str, Any]:
    """Retrieve an existing skill and all its version history."""
    s = skill_service.get_skill(skill_id)
    if not s:
        return {"error": f"Skill '{skill_id}' not found."}
    return s.model_dump()

def get_skill_version(skill_id: str, version: int) -> Dict[str, Any]:
    """Retrieve a specific version of a skill."""
    sv = skill_service.get_skill_version(skill_id, version)
    if not sv:
        return {"error": f"Skill '{skill_id}' version {version} not found."}
    return sv.model_dump()

def save_skill(
    skill_id: str,
    name: str,
    description: str,
    logic: str,
    formula: Optional[str] = None,
    code: Optional[str] = None,
    required_inputs: List[str] = None,
    validation_rules: List[str] = None,
    job_id: Optional[str] = None
) -> Dict[str, Any]:
    """Persist a newly approved analysis method as a reusable skill v1 in pgvector/PostgreSQL."""
    sv = SkillVersion(
        skill_id=skill_id,
        version=1,
        name=name,
        description=description,
        formula=formula,
        logic=logic,
        code=code,
        required_inputs=required_inputs or [],
        validation_rules=validation_rules or [],
        created_from_job=job_id
    )
    saved = skill_service.save_new_skill(sv)
    return {"status": "success", "skill": saved.model_dump()}

def update_skill(
    skill_id: str,
    modifications: Dict[str, Any],
    feedback: str = None
) -> Dict[str, Any]:
    """Create a new version (e.g. v2) for a skill after user feedback or correction."""
    try:
        new_version = skill_service.update_skill_version(skill_id, modifications, feedback)
        return {"status": "success", "new_version": new_version.model_dump()}
    except Exception as e:
        return {"status": "error", "error": str(e)}
