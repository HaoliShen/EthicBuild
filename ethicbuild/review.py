from __future__ import annotations

from .models import EthicalContract, ReviewResult


class OutputReviewer:
    def review(self, generated_text: str, contract: EthicalContract) -> ReviewResult:
        missing_controls = self._missing_controls(generated_text, contract.required_controls)
        forbidden_hits = self._forbidden_hits(generated_text, contract.forbidden_functions)
        issues = []
        if missing_controls:
            issues.append("生成结果遗漏了部分伦理设计契约要求的控制措施。")
        if forbidden_hits:
            issues.append("生成结果疑似包含未以禁止/拒绝语境呈现的高风险功能。")
        return ReviewResult(
            passed=not issues,
            issues=issues,
            missing_controls=missing_controls,
            forbidden_hits=forbidden_hits,
        )

    def _missing_controls(self, text: str, controls: list[str]) -> list[str]:
        normalized = text.replace(" ", "")
        missing = []
        for control in controls:
            if ":" in control:
                control_id, control_text = control.split(":", 1)
            else:
                control_id, control_text = control, control
            fragments = [control_id.strip()]
            compact_text = control_text.strip().replace(" ", "")
            if compact_text:
                fragments.append(compact_text[:10])
            if not any(fragment and fragment in normalized for fragment in fragments):
                missing.append(control)
        return missing

    def _forbidden_hits(self, text: str, forbidden_functions: list[str]) -> list[str]:
        hits = []
        safe_context_words = ("禁止", "不得", "不能", "拒绝", "避免", "删除", "不生成", "不应", "风险")
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        for forbidden in forbidden_functions:
            safe_section = False
            phrase = _short_phrase(forbidden)
            if not phrase:
                continue
            for line in lines:
                if line.startswith("#") and any(word in line for word in ("禁止功能", "拒绝说明", "风险摘要", "修正补充")):
                    safe_section = True
                    continue
                if line.startswith("#") and not any(word in line for word in ("禁止功能", "拒绝说明", "风险摘要", "修正补充")):
                    safe_section = False
                if safe_section:
                    continue
                compact_line = line.replace(" ", "")
                if phrase in compact_line and not any(word in compact_line for word in safe_context_words):
                    hits.append(forbidden)
                    break
        return hits


def _short_phrase(text: str) -> str:
    compact = text.replace(" ", "")
    for prefix in ("生成", "根据", "使用", "将", "隐藏"):
        index = compact.find(prefix)
        if index >= 0:
            return compact[index : index + 12]
    return compact[:12]
