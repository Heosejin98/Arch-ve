from pydantic import BaseModel
from typing import Optional


class ViolationItem(BaseModel):
    from_module: str
    to_module: str
    from_layer: str
    to_layer: str


class ArchCheckRequest(BaseModel):
    repo: str
    author: str
    branch: str = "main"
    commit_sha: Optional[str] = None
    pr_number: Optional[int] = None
    violation_count: int = 0
    violations: list[ViolationItem] = []
    total_files: Optional[int] = None
    total_dependencies: Optional[int] = None
    raw_result: Optional[str] = None


class ArchCheckResponse(BaseModel):
    id: int
    repo: str
    pr_number: Optional[int] = None
    branch: str
    commit_sha: Optional[str] = None
    author: str
    checked_at: str
    violation_count: int
    prev_violation_count: Optional[int] = None
    delta: Optional[int] = None
    total_files: Optional[int] = None
    total_dependencies: Optional[int] = None
    raw_result: Optional[str] = None


class LayerViolationStat(BaseModel):
    from_layer: str
    to_layer: str
    count: int
    ratio: float


class AuthorStat(BaseModel):
    author: str
    pr_count: int
    total_improved: int
    best_delta: Optional[int] = None


class TrendPoint(BaseModel):
    checked_at: str
    violation_count: int
    author: str
    pr_number: Optional[int] = None
    delta: Optional[int] = None
