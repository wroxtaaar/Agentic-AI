from dataclasses import dataclass, field
from typing import Any, Callable

@dataclass
class AgentResult:
    success: bool
    summary: str
    evidence: list[str] = field(default_factory=list)
    actions: list[dict[str, Any]] = field(default_factory=list)
    data: dict[str, Any] = field(default_factory=dict)

@dataclass
class Tool:
    name: str
    description: str
    function: Callable[..., dict]
    schema: dict

@dataclass
class Approval:
    id: str
    kind: str
    description: str
    payload: dict[str, Any]
    status: str = "pending"
