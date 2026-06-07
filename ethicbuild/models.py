from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class Decision(str, Enum):
    ALLOW = "allow"
    ALLOW_WITH_CONTROLS = "allow_with_controls"
    REWRITE_REQUIRED = "rewrite_required"
    BLOCK = "block"

    @property
    def label(self) -> str:
        return {
            Decision.ALLOW: "允许生成",
            Decision.ALLOW_WITH_CONTROLS: "允许生成但必须加入控制措施",
            Decision.REWRITE_REQUIRED: "必须重写为低风险方案",
            Decision.BLOCK: "拒绝生成并提供安全替代方案",
        }[self]


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

    @property
    def label(self) -> str:
        return {
            RiskLevel.LOW: "低风险",
            RiskLevel.MEDIUM: "中风险",
            RiskLevel.HIGH: "高风险",
            RiskLevel.CRITICAL: "严重风险",
        }[self]


@dataclass
class StructuredRequirement:
    original_text: str
    project_name: str = "未命名项目"
    summary: str = ""
    domains: list[str] = field(default_factory=list)
    target_users: list[str] = field(default_factory=list)
    data_types: list[str] = field(default_factory=list)
    sensitive_attributes: list[str] = field(default_factory=list)
    capabilities: list[str] = field(default_factory=list)
    decision_types: list[str] = field(default_factory=list)
    affected_rights: list[str] = field(default_factory=list)
    abuse_indicators: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    extraction_notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ScoreBreakdown:
    data_sensitivity: int = 0
    impact_severity: int = 0
    automation: int = 0
    vulnerable_groups: int = 0
    abuse_potential: int = 0

    @property
    def total(self) -> int:
        return (
            self.data_sensitivity
            + self.impact_severity
            + self.automation
            + self.vulnerable_groups
            + self.abuse_potential
        )

    def clamp(self) -> "ScoreBreakdown":
        for field_name in (
            "data_sensitivity",
            "impact_severity",
            "automation",
            "vulnerable_groups",
            "abuse_potential",
        ):
            value = getattr(self, field_name)
            setattr(self, field_name, max(0, min(3, int(value))))
        return self

    def update_max(self, values: dict[str, Any]) -> None:
        for field_name in (
            "data_sensitivity",
            "impact_severity",
            "automation",
            "vulnerable_groups",
            "abuse_potential",
        ):
            if field_name in values:
                setattr(self, field_name, max(getattr(self, field_name), int(values[field_name])))
        self.clamp()

    def to_dict(self) -> dict[str, int]:
        return asdict(self)


@dataclass
class TriggeredRule:
    id: str
    name: str
    values: list[str]
    severity: str
    decision: Decision
    required_controls: list[str] = field(default_factory=list)
    forbidden_outputs: list[str] = field(default_factory=list)
    safe_alternatives: list[str] = field(default_factory=list)
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["decision"] = self.decision.value
        return data


@dataclass
class RiskAnalysis:
    requirement: StructuredRequirement
    risk_level: RiskLevel
    decision: Decision
    score: ScoreBreakdown
    triggered_rules: list[TriggeredRule] = field(default_factory=list)
    required_controls: list[str] = field(default_factory=list)
    forbidden_outputs: list[str] = field(default_factory=list)
    safe_alternatives: list[str] = field(default_factory=list)
    explanation: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "requirement": self.requirement.to_dict(),
            "risk_level": self.risk_level.value,
            "risk_level_label": self.risk_level.label,
            "decision": self.decision.value,
            "decision_label": self.decision.label,
            "score": self.score.to_dict() | {"total": self.score.total},
            "triggered_rules": [rule.to_dict() for rule in self.triggered_rules],
            "required_controls": self.required_controls,
            "forbidden_outputs": self.forbidden_outputs,
            "safe_alternatives": self.safe_alternatives,
            "explanation": self.explanation,
        }


@dataclass
class EthicalContract:
    project_name: str
    decision: Decision
    allowed_functions: list[str]
    forbidden_functions: list[str]
    required_controls: list[str]
    data_boundaries: list[str]
    transparency_requirements: list[str]
    human_review_requirements: list[str]
    deployment_limits: list[str]

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["decision"] = self.decision.value
        return data


@dataclass
class ReviewResult:
    passed: bool
    issues: list[str] = field(default_factory=list)
    missing_controls: list[str] = field(default_factory=list)
    forbidden_hits: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PipelineResult:
    analysis: RiskAnalysis
    contract: EthicalContract
    generated_plan: str
    review: ReviewResult
    audit_record: dict[str, Any]
    timings: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "analysis": self.analysis.to_dict(),
            "contract": self.contract.to_dict(),
            "generated_plan": self.generated_plan,
            "review": self.review.to_dict(),
            "audit_record": self.audit_record,
            "timings": self.timings,
        }
