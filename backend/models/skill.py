from typing import Any, Dict, List, Optional
from ..core.compat import BaseModel, Field
from datetime import datetime

class SkillVersion(BaseModel):
    skill_id: str
    version: int
    name: str
    description: str
    required_inputs: List[str] = Field(default_factory=list)
    formula: Optional[str] = None
    logic: str
    code: Optional[str] = None
    examples: List[Dict[str, Any]] = Field(default_factory=list)
    validation_rules: List[str] = Field(default_factory=list)
    created_from_job: Optional[str] = None
    embedding: Optional[List[float]] = None
    created_at: datetime = Field(default_factory=datetime.now)

class Skill(BaseModel):
    skill_id: str
    name: str
    description: str
    current_version: int = 1
    versions: Dict[int, SkillVersion] = Field(default_factory=dict)
    status: str = "active"  # "active" | "deprecated"
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

class SkillSearchResult(BaseModel):
    skill_id: str
    name: str
    description: str
    version: int
    similarity: float
    skill_version: SkillVersion
