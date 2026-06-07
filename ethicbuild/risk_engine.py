from __future__ import annotations

from typing import Any

from .manual import ValueManual
from .models import Decision, RiskAnalysis, RiskLevel, ScoreBreakdown, StructuredRequirement, TriggeredRule


DECISION_PRECEDENCE = {
    Decision.ALLOW: 0,
    Decision.ALLOW_WITH_CONTROLS: 1,
    Decision.REWRITE_REQUIRED: 2,
    Decision.BLOCK: 3,
}


class RiskEngine:
    def __init__(self, manual: ValueManual):
        self.manual = manual

    def analyze(self, requirement: StructuredRequirement) -> RiskAnalysis:
        score = self._baseline_score(requirement)
        triggered_rules: list[TriggeredRule] = []

        for rule in self.manual.rules:
            matched, reason = self._rule_matches(rule, requirement)
            if not matched:
                continue
            score.update_max(rule.get("score", {}))
            triggered_rules.append(
                TriggeredRule(
                    id=rule.get("id", ""),
                    name=rule.get("name", ""),
                    values=list(rule.get("values", [])),
                    severity=rule.get("severity", "low"),
                    decision=Decision(rule.get("decision", "allow")),
                    required_controls=list(rule.get("required_controls", [])),
                    forbidden_outputs=list(rule.get("forbidden_outputs", [])),
                    safe_alternatives=list(rule.get("safe_alternatives", [])),
                    reason=reason,
                )
            )

        decision = self._decide(triggered_rules, score)
        risk_level = self._risk_level(triggered_rules, score)
        required_controls = _dedupe(
            control for rule in triggered_rules for control in rule.required_controls
        )
        if "ai_disclosure" not in required_controls:
            required_controls.append("ai_disclosure")
        forbidden_outputs = _dedupe(
            item for rule in triggered_rules for item in rule.forbidden_outputs
        )
        safe_alternatives = _dedupe(
            item for rule in triggered_rules for item in rule.safe_alternatives
        )
        explanation = self._explain(requirement, triggered_rules, score, risk_level, decision)

        return RiskAnalysis(
            requirement=requirement,
            risk_level=risk_level,
            decision=decision,
            score=score,
            triggered_rules=triggered_rules,
            required_controls=required_controls,
            forbidden_outputs=forbidden_outputs,
            safe_alternatives=safe_alternatives,
            explanation=explanation,
        )

    def _baseline_score(self, requirement: StructuredRequirement) -> ScoreBreakdown:
        score = ScoreBreakdown()
        sensitive_data = {"phone", "id_number", "location", "face", "voice", "fingerprint", "health", "finance"}
        high_impact_domains = {"hiring", "education", "healthcare", "finance", "justice"}
        highly_vulnerable_groups = {"minors", "patients", "elderly"}
        contextually_vulnerable_groups = {"students", "job_applicants"}

        if any(data_type in sensitive_data for data_type in requirement.data_types):
            score.data_sensitivity = 2
        if any(data_type in {"face", "voice", "fingerprint", "health"} for data_type in requirement.data_types):
            score.data_sensitivity = 3
        if any(domain in high_impact_domains for domain in requirement.domains):
            score.impact_severity = 2
        if any(capability in {"automated_scoring", "identification", "monitoring"} for capability in requirement.capabilities):
            score.automation = 2
        if any(user in highly_vulnerable_groups for user in requirement.target_users):
            score.vulnerable_groups = 2
        elif any(user in contextually_vulnerable_groups for user in requirement.target_users):
            score.vulnerable_groups = 1
        if requirement.abuse_indicators:
            score.abuse_potential = 3
        return score.clamp()

    def _rule_matches(self, rule: dict[str, Any], requirement: StructuredRequirement) -> tuple[bool, str]:
        condition = rule.get("condition", {})
        reasons = []

        checks = [
            ("domain_any", requirement.domains, "领域"),
            ("data_any", requirement.data_types, "数据类型"),
            ("target_user_any", requirement.target_users, "目标用户"),
            ("capability_any", requirement.capabilities, "功能能力"),
            ("decision_type_any", requirement.decision_types, "决策类型"),
        ]
        for key, values, label in checks:
            if key not in condition:
                continue
            expected = set(condition[key])
            actual = set(values)
            intersection = sorted(expected & actual)
            if not intersection:
                return False, ""
            reasons.append(f"{label}命中：{', '.join(intersection)}")

        if condition.get("abuse_indicator") is True:
            if not requirement.abuse_indicators:
                return False, ""
            reasons.append(f"滥用/绕过表达命中：{', '.join(requirement.abuse_indicators)}")

        if "keyword_any" in condition:
            text = requirement.original_text.lower()
            hits = [word for word in condition["keyword_any"] if word.lower() in text]
            if not hits:
                return False, ""
            reasons.append(f"关键词命中：{', '.join(hits)}")

        return True, "；".join(reasons) or "满足规则条件"

    def _decide(self, rules: list[TriggeredRule], score: ScoreBreakdown) -> Decision:
        if not rules:
            return Decision.ALLOW
        decision = max((rule.decision for rule in rules), key=lambda item: DECISION_PRECEDENCE[item])
        if score.total >= 12 and DECISION_PRECEDENCE[decision] < DECISION_PRECEDENCE[Decision.REWRITE_REQUIRED]:
            return Decision.REWRITE_REQUIRED
        if score.total >= 8 and DECISION_PRECEDENCE[decision] < DECISION_PRECEDENCE[Decision.ALLOW_WITH_CONTROLS]:
            return Decision.ALLOW_WITH_CONTROLS
        return decision

    def _risk_level(self, rules: list[TriggeredRule], score: ScoreBreakdown) -> RiskLevel:
        if any(rule.severity == "critical" for rule in rules) or score.total >= 12:
            return RiskLevel.CRITICAL
        if any(rule.severity == "high" for rule in rules) or score.total >= 8:
            return RiskLevel.HIGH
        if any(rule.severity == "medium" for rule in rules) or score.total >= 4:
            return RiskLevel.MEDIUM
        return RiskLevel.LOW

    def _explain(
        self,
        requirement: StructuredRequirement,
        rules: list[TriggeredRule],
        score: ScoreBreakdown,
        risk_level: RiskLevel,
        decision: Decision,
    ) -> list[str]:
        lines = [
            f"综合风险等级为{risk_level.label}，五维评分合计 {score.total}/15。",
            f"生成权限决策为：{decision.label}。",
        ]
        if requirement.data_types:
            lines.append(f"识别到数据类型：{', '.join(requirement.data_types)}。")
        if requirement.capabilities:
            lines.append(f"识别到功能能力：{', '.join(requirement.capabilities)}。")
        if requirement.domains:
            lines.append(f"识别到应用领域：{', '.join(requirement.domains)}。")
        if rules:
            lines.append("触发规则：" + "；".join(f"{rule.id}（{rule.name}）" for rule in rules) + "。")
        else:
            lines.append("未触发高风险规则，仅保留基础透明性提醒。")
        return lines


def _dedupe(items) -> list[str]:
    seen = set()
    result = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result
