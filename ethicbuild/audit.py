from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from .models import EthicalContract, RiskAnalysis, ReviewResult


class AuditLogger:
    def __init__(self, output_dir: str | Path = "outputs/audit_logs"):
        self.output_dir = Path(output_dir)

    def build_record(
        self,
        analysis: RiskAnalysis,
        contract: EthicalContract,
        review: ReviewResult,
        generated_plan: str,
    ) -> dict:
        request_id = f"ethicbuild-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{uuid4().hex[:8]}"
        return {
            "request_id": request_id,
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "project_name": contract.project_name,
            "original_request": analysis.requirement.original_text,
            "risk_level": analysis.risk_level.value,
            "risk_level_label": analysis.risk_level.label,
            "decision": analysis.decision.value,
            "decision_label": analysis.decision.label,
            "score": analysis.score.to_dict() | {"total": analysis.score.total},
            "triggered_rule_ids": [rule.id for rule in analysis.triggered_rules],
            "required_controls": analysis.required_controls,
            "forbidden_outputs": analysis.forbidden_outputs,
            "review_passed": review.passed,
            "review_issues": review.issues,
            "generated_plan_digest": generated_plan[:500],
            "human_confirmed": False,
            "human_feedback_placeholder": "",
        }

    def save(self, record: dict) -> Path:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        path = self.output_dir / f"{record['request_id']}.json"
        path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
        return path
