"""Skill Library and pgvector retrieval API endpoints."""
import uuid
from typing import Any, Dict, List, Optional
from ..services.skill_service import skill_service
from ..models.skill import SkillVersion
from .schemas import SkillCreateRequest, SkillUpdateRequest, SkillSearchRequest

try:
    from fastapi import APIRouter, HTTPException, Query, Body
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False
    APIRouter = object

router = APIRouter(prefix="/skills", tags=["Skills & Vector Store"]) if HAS_FASTAPI else None

def handle_list_skills() -> List[Dict[str, Any]]:
    """List all registered skills."""
    return skill_service.list_skills()

def handle_get_skill(skill_id: str) -> Dict[str, Any]:
    """Retrieve skill definition and all historical versions."""
    sk = skill_service.get_skill(skill_id)
    if not sk:
        return {"error": f"Skill '{skill_id}' not found", "status": 404}
    return sk.model_dump()

def handle_create_skill(req: SkillCreateRequest) -> Dict[str, Any]:
    """Register a new skill with auto-generated embedding."""
    skill_id = f"skill_{uuid.uuid4().hex[:8]}"
    sv = SkillVersion(
        skill_id=skill_id,
        version=1,
        name=req.name,
        description=req.description,
        required_inputs=req.required_inputs,
        formula=req.formula,
        logic=req.logic,
        code=req.code,
        validation_rules=req.validation_rules
    )
    skill = skill_service.save_new_skill(sv)
    return skill.model_dump()

def handle_update_skill(skill_id: str, req: SkillUpdateRequest) -> Dict[str, Any]:
    """Section 26: Create new version of existing skill without overwriting previous versions."""
    modifications = {k: v for k, v in req.model_dump().items() if v is not None and k != "feedback"}
    try:
        new_ver = skill_service.update_skill_version(
            skill_id=skill_id,
            modifications=modifications,
            feedback=req.feedback
        )
        return new_ver.model_dump()
    except Exception as e:
        return {"error": str(e), "status": 400}

def handle_delete_skill(skill_id: str) -> Dict[str, Any]:
    """Mark a skill as deprecated."""
    ok = skill_service.delete_skill(skill_id)
    if not ok:
        return {"error": f"Skill '{skill_id}' not found", "status": 404}
    return {"success": True, "message": f"Skill '{skill_id}' deactivated."}

def handle_search_skills(query: str, threshold: float = 0.5, top_k: int = 5) -> List[Dict[str, Any]]:
    """Semantic vector similarity search across registered skills."""
    results = skill_service.search_skills(query, threshold=threshold, top_k=top_k)
    return [r.model_dump() for r in results]

if HAS_FASTAPI:
    @router.get("")
    @router.get("/")
    async def list_skills_endpoint():
        """List all analysis skills registered in the vector database."""
        return handle_list_skills()

    @router.post("/search")
    async def search_skills_endpoint(payload: SkillSearchRequest):
        """Perform semantic similarity / vector retrieval for skills matching an analysis request."""
        return handle_search_skills(payload.query, threshold=payload.threshold, top_k=payload.top_k)

    @router.get("/{skill_id}")
    async def get_skill_endpoint(skill_id: str):
        """Retrieve full skill specification and its version history."""
        res = handle_get_skill(skill_id)
        if res.get("error"):
            raise HTTPException(status_code=404, detail=res["error"])
        return res

    @router.post("")
    @router.post("/")
    async def create_skill_endpoint(payload: SkillCreateRequest):
        """Register a new analysis methodology in the vector store."""
        return handle_create_skill(payload)

    @router.put("/{skill_id}")
    async def update_skill_endpoint(skill_id: str, payload: SkillUpdateRequest):
        """Publish a new version of an existing skill (v1 -> v2) with modified logic or formula."""
        res = handle_update_skill(skill_id, payload)
        if res.get("error"):
            raise HTTPException(status_code=400, detail=res["error"])
        return res

    @router.delete("/{skill_id}")
    async def delete_skill_endpoint(skill_id: str):
        """Deprecate / archive a skill from active retrieval."""
        res = handle_delete_skill(skill_id)
        if res.get("error"):
            raise HTTPException(status_code=404, detail=res["error"])
        return res
