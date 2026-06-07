from __future__ import annotations

import re
from typing import Any

from .llm import LLMClient, LLMUnavailableError
from .manual import ValueManual
from .models import StructuredRequirement


SENSITIVE_ATTRIBUTE_TYPES = {"age", "gender", "ethnicity", "region", "school", "health", "finance"}
RIGHTS_BY_DOMAIN = {
    "hiring": "就业机会",
    "education": "教育评价与学习机会",
    "healthcare": "健康与医疗权益",
    "finance": "金融机会与信用权益",
    "justice": "法律权利与程序正义",
    "security": "行动自由与隐私权益",
}


class RequirementExtractor:
    def __init__(self, manual: ValueManual, llm_client: LLMClient | None = None):
        self.manual = manual
        self.llm_client = llm_client

    def extract(self, text: str, use_llm: bool = False) -> StructuredRequirement:
        heuristic = self._heuristic_extract(text)
        if not use_llm or not self.llm_client or not self.llm_client.available:
            return heuristic

        try:
            llm_data = self._llm_extract(text)
        except (LLMUnavailableError, ValueError, RuntimeError) as exc:
            heuristic.extraction_notes.append(f"LLM抽取失败，已回退到规则抽取：{exc}")
            return heuristic
        return self._merge(heuristic, llm_data)

    def _heuristic_extract(self, text: str) -> StructuredRequirement:
        requirement = StructuredRequirement(
            original_text=text.strip(),
            project_name=self._infer_project_name(text),
            summary=text.strip()[:120],
        )
        taxonomy = self.manual.taxonomy
        requirement.domains = self._match_section(text, taxonomy.get("domains", {}))
        requirement.data_types = self._match_section(text, taxonomy.get("data_types", {}))
        requirement.target_users = self._match_section(text, taxonomy.get("sensitive_groups", {}))
        requirement.capabilities = self._match_section(text, taxonomy.get("capabilities", {}))
        requirement.abuse_indicators = [
            word for word in taxonomy.get("abuse_indicators", []) if word.lower() in text.lower()
        ]
        requirement.sensitive_attributes = [
            item for item in requirement.data_types if item in SENSITIVE_ATTRIBUTE_TYPES
        ]
        requirement.decision_types = self._infer_decision_types(requirement.capabilities)
        requirement.affected_rights = [
            RIGHTS_BY_DOMAIN[domain] for domain in requirement.domains if domain in RIGHTS_BY_DOMAIN
        ]
        if requirement.abuse_indicators:
            requirement.extraction_notes.append("检测到可能诱导绕过规则或未授权行为的表达。")
        if not requirement.domains:
            requirement.domains = ["software_dev"]
            requirement.extraction_notes.append("未识别到特定高风险领域，按普通软件项目处理。")
        return requirement

    def _llm_extract(self, text: str) -> dict[str, Any]:
        domains = list(self.manual.taxonomy.get("domains", {}).keys())
        data_types = list(self.manual.taxonomy.get("data_types", {}).keys())
        groups = list(self.manual.taxonomy.get("sensitive_groups", {}).keys())
        capabilities = list(self.manual.taxonomy.get("capabilities", {}).keys())
        system = """你是 EthicBuild 的需求结构化模块，只能输出 JSON。
你的任务是从用户的项目需求中抽取伦理审查所需字段，不负责最终伦理判断。
必须保留原始需求中的关键功能，不得因为安全考虑删除字段；不确定时放入 constraints 或 extraction_notes。
输出字段必须包括：
project_name, summary, domains, target_users, data_types, sensitive_attributes,
capabilities, decision_types, affected_rights, abuse_indicators, constraints, extraction_notes。
所有列表字段必须是数组，使用给定枚举值；无法映射时可使用中文短语。"""
        user = f"""可用 domains: {domains}
可用 data_types: {data_types}
可用 target_users: {groups}
可用 capabilities: {capabilities}

用户需求：
{text}

请只输出 JSON 对象。"""
        return self.llm_client.json_complete(system=system, user=user, temperature=0.0, max_tokens=700)  # type: ignore[union-attr]

    def _merge(self, heuristic: StructuredRequirement, llm_data: dict[str, Any]) -> StructuredRequirement:
        merged = StructuredRequirement(
            original_text=heuristic.original_text,
            project_name=str(llm_data.get("project_name") or heuristic.project_name),
            summary=str(llm_data.get("summary") or heuristic.summary),
        )
        for field_name in (
            "domains",
            "target_users",
            "data_types",
            "sensitive_attributes",
            "capabilities",
            "decision_types",
            "affected_rights",
            "constraints",
            "extraction_notes",
        ):
            values = []
            values.extend(getattr(heuristic, field_name))
            llm_values = llm_data.get(field_name, [])
            if isinstance(llm_values, str):
                llm_values = [llm_values]
            if isinstance(llm_values, list):
                values.extend(str(item) for item in llm_values if item)
            setattr(merged, field_name, _dedupe(values))
        abuse_keywords = set(self.manual.taxonomy.get("abuse_indicators", []))
        llm_abuse_values = llm_data.get("abuse_indicators", [])
        if isinstance(llm_abuse_values, str):
            llm_abuse_values = [llm_abuse_values]
        valid_llm_abuse = [
            str(item)
            for item in llm_abuse_values
            if str(item) in abuse_keywords or str(item).lower() in {keyword.lower() for keyword in abuse_keywords}
        ]
        merged.abuse_indicators = _dedupe(heuristic.abuse_indicators + valid_llm_abuse)
        if not merged.sensitive_attributes:
            merged.sensitive_attributes = [
                item for item in merged.data_types if item in SENSITIVE_ATTRIBUTE_TYPES
            ]
        if not merged.decision_types:
            merged.decision_types = self._infer_decision_types(merged.capabilities)
        return merged

    def _match_section(self, text: str, section: dict[str, list[str]]) -> list[str]:
        lowered = text.lower()
        matches = []
        for key, keywords in section.items():
            if any(keyword.lower() in lowered for keyword in keywords):
                matches.append(key)
        return matches

    def _infer_project_name(self, text: str) -> str:
        patterns = [
            r"做一个(?P<name>[^，。,.]{2,30})",
            r"开发一个(?P<name>[^，。,.]{2,30})",
            r"设计一个(?P<name>[^，。,.]{2,30})",
            r"build (?:a|an) (?P<name>[^,.]{2,40})",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                return match.group("name").strip()
        return "AI辅助项目"

    def _infer_decision_types(self, capabilities: list[str]) -> list[str]:
        decisions = []
        if "automated_scoring" in capabilities:
            decisions.append("automated_decision_or_scoring")
        if "recommendation" in capabilities:
            decisions.append("recommendation")
        if "identification" in capabilities:
            decisions.append("identity_verification")
        return decisions


def _dedupe(items: list[str]) -> list[str]:
    seen = set()
    result = []
    for item in items:
        normalized = item.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return result
