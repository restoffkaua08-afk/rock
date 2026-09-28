from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ExecutionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"
    DENIED = "denied"


class PermissionDecision(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    ASK = "ask"


class TaskMode(str, Enum):
    QUICK = "quick"
    COUNCIL = "council"
    DEEP = "deep"
    RESEARCH = "research"
    AGENT = "agent"


class CouncilProtocol(str, Enum):
    PARALLEL = "parallel"
    CRITIQUE_SYNTHESIS = "critique_synthesis"
    DEBATE = "debate"
    RED_TEAM = "red_team"
    VOTE = "vote"


class Budget(BaseModel):
    max_cost: float | None = None
    max_parallel: int = 5
    max_rounds: int = 3
    max_tool_calls: int = 20


class Policy(BaseModel):
    timeout_seconds: float = 60
    max_retries: int = 2
    budget: Budget = Field(default_factory=Budget)
    approval_required: bool = False
    allow_tools: bool = True
    require_verification: bool = True


class Capability(str, Enum):
    TEXT = "text"
    VISION = "vision"
    TOOLS = "tools"
    STRUCTURED_OUTPUT = "structured_output"
    WEB_SEARCH = "web_search"
    STREAMING = "streaming"
    LONG_CONTEXT = "long_context"
    LOCAL = "local"


class Task(BaseModel):
    id: str
    prompt: str
    mode: TaskMode = TaskMode.COUNCIL
    context: dict[str, Any] = Field(default_factory=dict)
    requested_capabilities: set[Capability] = Field(default_factory=lambda: {Capability.TEXT})
    policy: Policy = Field(default_factory=Policy)
    created_at: datetime = Field(default_factory=utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)


class Model(BaseModel):
    id: str
    provider: str
    model_name: str
    capabilities: set[Capability] = Field(default_factory=lambda: {Capability.TEXT})
    context_window: int | None = None
    pricing: dict[str, float] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class Claim(BaseModel):
    id: str
    statement: str
    source: str
    evidence_id: str | None = None
    polarity: str | None = None
    confidence: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class Evidence(BaseModel):
    id: str
    source: str
    content: str
    relevance: float | None = None
    provider: str | None = None
    timestamp: datetime = Field(default_factory=utc_now)
    claims: list[Claim] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class Response(BaseModel):
    provider: str
    model: str
    content: str
    latency_ms: float | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    estimated_cost: float | None = None
    error: str | None = None
    evidence: list[Evidence] = Field(default_factory=list)


class Conflict(BaseModel):
    id: str
    topic: str
    claims: list[str] = Field(default_factory=list)
    claim_ids: list[str] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)
    severity: float = 0.5
    resolved: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class AdjudicationStatus(str, Enum):
    RESOLVED = "resolved"
    INCONCLUSIVE = "inconclusive"
    ESCALATE = "escalate"


class Adjudication(BaseModel):
    conflict_id: str
    claim_ids: list[str] = Field(default_factory=list)
    status: AdjudicationStatus
    decision: str
    rationale: str = ""
    supporting_sources: list[str] = Field(default_factory=list)
    rejected_sources: list[str] = Field(default_factory=list)
    confidence: float = 0.0


class ProtocolResult(BaseModel):
    protocol: CouncilProtocol
    response: Response
    evidence: list[Evidence] = Field(default_factory=list)
    disagreements: list[str] = Field(default_factory=list)
    confidence: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class Verification(BaseModel):
    target: str
    verifier: str
    checks: list[str] = Field(default_factory=list)
    passed: bool
    findings: list[str] = Field(default_factory=list)
    confidence: float | None = None


class Artifact(BaseModel):
    id: str
    type: str
    content: str
    source: str
    task_id: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class Execution(BaseModel):
    id: str
    task_id: str
    actor: str
    action: str
    status: ExecutionStatus = ExecutionStatus.PENDING
    started_at: datetime | None = None
    finished_at: datetime | None = None
    duration_ms: float | None = None
    input: dict[str, Any] = Field(default_factory=dict)
    output: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None


class Permission(BaseModel):
    resource: str
    action: str
    decision: PermissionDecision = PermissionDecision.ASK
    reason: str | None = None


class Skill(BaseModel):
    id: str
    name: str
    description: str = ""
    instructions: str = ""
    required_capabilities: set[Capability] = Field(default_factory=set)
    tools: list[str] = Field(default_factory=list)
    source: str = "rock"


class Tool(BaseModel):
    id: str
    name: str
    description: str = ""
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)
    permissions: list[Permission] = Field(default_factory=list)


class Agent(BaseModel):
    id: str
    name: str
    model: Model | None = None
    system_policy: str = ""
    capabilities: set[Capability] = Field(default_factory=set)
    tools: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    max_iterations: int = 8


class Council(BaseModel):
    id: str
    members: list[str]
    protocol: CouncilProtocol = CouncilProtocol.PARALLEL
    rounds: int = 1
    critic: str = "critic"
    synthesizer: str = "synthesizer"
    verifier: str = "verifier"
    judge: str = "judge"
    red_team: str = "red_team"
    voter: str = "voter"


class Workflow(BaseModel):
    id: str
    name: str
    steps: list[str] = Field(default_factory=list)


class Session(BaseModel):
    id: str
    task_ids: list[str] = Field(default_factory=list)
    executions: list[str] = Field(default_factory=list)
    artifact_ids: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)
