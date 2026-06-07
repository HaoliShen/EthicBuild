from __future__ import annotations

import json
from typing import Any

from .llm import LLMClient, LLMUnavailableError
from .models import Decision, EthicalContract, RiskAnalysis


class ProjectGenerator:
    def __init__(self, llm_client: LLMClient | None = None):
        self.llm_client = llm_client

    def generate(
        self,
        analysis: RiskAnalysis,
        contract: EthicalContract,
        use_llm: bool = False,
    ) -> str:
        if use_llm and self.llm_client and self.llm_client.available:
            try:
                return self._llm_generate(analysis, contract)
            except (LLMUnavailableError, RuntimeError, ValueError, Exception) as exc:
                fallback = self._template_generate(analysis, contract)
                return fallback + f"\n\n> 注：LLM生成失败，已回退到模板生成。错误摘要：{exc}\n"
        return self._template_generate(analysis, contract)

    def _llm_generate(self, analysis: RiskAnalysis, contract: EthicalContract) -> str:
        system = """你是资深中文系统架构师与AI伦理设计专家，正在为课程项目生成可直接展示的完整Markdown方案。

硬性要求：
1. 不能只讨论伦理，必须先给出真实可实现的项目方案。
2. 内容比例：产品/技术设计约60%，伦理控制约30%，使用边界与验证约10%。
3. 必须严格遵守输入中的伦理设计契约，不得放宽禁止功能。
4. 如果 decision 是“必须重写”或“拒绝”，需要把原需求改写成可实现的安全替代方案，但仍要给出完整代码架构。
5. 不要输出空泛口号；每个模块要说明职责、输入输出或实现方式。
6. 必须包含代码目录树，必须包含人工复核、审计日志和数据边界的实现位置。
7. 代码目录树必须包含 app.py、domain_service.py、ethics_contract.json、data_policy.md、review_workflow.py、audit_log.py、tests/test_ethics_controls.py。
8. 第7节必须明确列出 required_controls 中所有控制项ID，例如 human_review、audit_log。
9. 对招聘场景：不得把年龄、性别、毕业学校/学校名称作为评分因子；应改为技能、岗位资格、工作经历、项目经历等任务相关因子。
10. 对拒绝类隐私需求：安全替代方案必须是“本人自愿提交/明确授权”的数据收集；不得设计由用户代替他人录入手机号、位置、身份证等个人数据的流程。
11. 第5节必须使用 ```text 代码块输出目录树，不能只用项目符号列模块。
12. 如果 decision 是“拒绝生成并提供安全替代方案”，第1节必须说明原始需求被拒绝；第2节只能设计安全替代功能，如本人自愿提交链接、授权记录、撤回删除、模拟数据演示、审计日志。不得设计“用户手动输入同学手机号”“通讯录导出分享”等功能。
13. 技术方案要专业，排序/检索等常规工程实现应写数据库排序、向量检索、pandas排序或服务层排序，不要写冒泡排序等教学玩具算法。

请按以下固定Markdown结构输出：
# 项目名称：伦理可控项目构建方案
## 1. 项目定位
## 2. 功能需求设计
## 3. 系统架构设计
## 4. 数据流程与数据边界
## 5. 代码架构与核心模块
## 6. 核心实现逻辑
## 7. 伦理控制设计
## 8. 使用边界、验证与交付物

写作要求：
- 第2-6节应明显多于第7节。
- 第7节按“隐私与数据、公平与反歧视、透明与追责、人类监督、安全部署”分组。
- 输出中文Markdown，不要输出JSON。"""
        user = json.dumps(
            self._full_generation_payload(analysis, contract),
            ensure_ascii=False,
            indent=2,
        )
        text = self.llm_client.stream_complete(  # type: ignore[union-attr]
            system=system,
            user=user,
            temperature=0.2,
            max_tokens=3600,
            timeout=90,
        )
        if not text.strip():
            raise ValueError("LLM returned empty output.")
        return self._ensure_minimum_structure(text, analysis, contract)

    def _full_generation_payload(self, analysis: RiskAnalysis, contract: EthicalContract) -> dict[str, Any]:
        requirement = analysis.requirement
        return {
            "original_request": requirement.original_text,
            "safe_task_override": self._safe_task_override(analysis),
            "structured_requirement": requirement.to_dict(),
            "risk_level": analysis.risk_level.label,
            "risk_score": analysis.score.to_dict() | {"total": analysis.score.total},
            "decision": analysis.decision.label,
            "triggered_rules": [
                {
                    "id": rule.id,
                    "name": rule.name,
                    "reason": rule.reason,
                    "values": rule.values,
                }
                for rule in analysis.triggered_rules
            ],
            "ethical_design_contract": contract.to_dict(),
            "generation_guidance": {
                "technical_goal": "输出一个能作为课程系统实现原型的真实方案，包含模块、数据流、代码目录和实现步骤。",
                "rewrite_guidance": "高风险需求要改写成低风险替代方案，例如简历筛选改成技能匹配+人工复核；不得生成歧视性评分。",
                "blocked_privacy_guidance": "如果原需求是未授权收集个人信息，替代方案必须要求数据主体本人自愿提交或明确授权；管理员不得代录他人手机号等敏感个人信息。",
                "balance": "技术/产品设计约60%，伦理控制约30%，边界与验证约10%。",
                "required_code_files": [
                    "app.py",
                    "domain_service.py",
                    "ethics_contract.json",
                    "data_policy.md",
                    "review_workflow.py",
                    "audit_log.py",
                    "tests/test_ethics_controls.py",
                ],
                "required_control_ids": [control.split(":", 1)[0] for control in contract.required_controls],
            },
        }

    def _safe_task_override(self, analysis: RiskAnalysis) -> dict[str, Any] | None:
        requirement = analysis.requirement
        if analysis.decision != Decision.BLOCK:
            return None
        if "phone" in requirement.data_types or "scraping" in requirement.capabilities:
            return {
                "safe_project_name": "自愿授权通讯录管理原型",
                "must_refuse_original": "拒绝批量爬取或代录他人手机号的原始需求。",
                "allowed_safe_features": [
                    "本人通过邀请链接自愿提交联系方式",
                    "提交前展示数据用途、保存期限和删除方式",
                    "用户可撤回授权并删除自己的联系方式",
                    "管理员只能查看已授权记录和审计日志",
                    "课程演示优先使用模拟数据",
                ],
                "forbidden_safe_features": [
                    "用户手动输入他人手机号",
                    "批量导入或爬取同学联系方式",
                    "隐藏数据收集目的",
                    "导出分享未经授权的通讯录",
                ],
            }
        return {
            "safe_project_name": "合规安全替代原型",
            "must_refuse_original": "拒绝原始高风险需求。",
            "allowed_safe_features": analysis.safe_alternatives,
            "forbidden_safe_features": analysis.forbidden_outputs,
        }

    def _ensure_minimum_structure(
        self,
        text: str,
        analysis: RiskAnalysis,
        contract: EthicalContract,
    ) -> str:
        required_headings = [
            "## 1. 项目定位",
            "## 2. 功能需求设计",
            "## 3. 系统架构设计",
            "## 4. 数据流程与数据边界",
            "## 5. 代码架构与核心模块",
            "## 6. 核心实现逻辑",
            "## 7. 伦理控制设计",
            "## 8. 使用边界、验证与交付物",
        ]
        missing = [heading for heading in required_headings if heading not in text]
        has_code_tree = "```" in text and ("├──" in text or "app.py" in text)
        required_files = [
            "app.py",
            "domain_service.py",
            "ethics_contract.json",
            "data_policy.md",
            "review_workflow.py",
            "audit_log.py",
            "test_ethics_controls.py",
        ]
        missing_files = [file_name for file_name in required_files if file_name not in text]
        required_control_ids = [control.split(":", 1)[0].strip() for control in contract.required_controls]
        missing_control_ids = [control_id for control_id in required_control_ids if control_id not in text]
        if missing_control_ids:
            text = self._insert_control_id_mapping(text, missing_control_ids)

        if not missing and has_code_tree:
            if not missing_files:
                return text

        supplement = [
            "",
            "## 生成后结构补全",
            "以下内容由本地结构校验器补充，用于保证完整增强结果满足项目展示要求。",
        ]
        if missing:
            supplement.append("- 缺失章节：" + "、".join(missing))
        if not has_code_tree:
            supplement.extend(
                [
                    "- 补充代码架构：",
                    "```text",
                    "controlled_project/",
                    "├── app.py                  # 页面入口与交互",
                    "├── domain_service.py       # 领域业务逻辑",
                    "├── ethics_contract.json    # 伦理设计契约",
                    "├── data_policy.md          # 数据边界和用户告知",
                    "├── review_workflow.py      # 人工复核与申诉流程",
                    "├── audit_log.py            # 审计记录",
                    "└── tests/",
                    "    └── test_ethics_controls.py",
                    "```",
                ]
            )
        elif missing_files:
            supplement.extend(
                [
                    "- 代码架构需补充以下文件：" + "、".join(missing_files),
                    "```text",
                    "controlled_project/",
                    "├── app.py                  # 页面入口与交互",
                    "├── domain_service.py       # 领域业务逻辑",
                    "├── ethics_contract.json    # 伦理设计契约",
                    "├── data_policy.md          # 数据边界和用户告知",
                    "├── review_workflow.py      # 人工复核与申诉流程",
                    "├── audit_log.py            # 审计记录",
                    "└── tests/",
                    "    └── test_ethics_controls.py",
                    "```",
                ]
            )
        if analysis.required_controls:
            supplement.append("- 必须保留的伦理控制：" + "；".join(analysis.required_controls))
        supplement.extend(f"- 部署限制：{item}" for item in contract.deployment_limits)
        return text.rstrip() + "\n" + "\n".join(supplement)

    def _insert_control_id_mapping(self, text: str, missing_control_ids: list[str]) -> str:
        mapping_lines = [
            "",
            "### 控制项ID映射",
            "- 以下控制项ID用于保证方案可被系统审查和追溯：",
        ]
        mapping_explanations = {
            "remove_sensitive_attributes": "在简历解析后剔除敏感属性及明显代理变量。",
            "explainable_score": "在技能匹配报告中展示主要匹配依据。",
            "fairness_test": "在测试中检查不同群体结果差异。",
            "human_review": "在 review_workflow.py 中实现人工复核。",
            "appeal_channel": "在申诉流程中提供纠错和复议入口。",
            "audit_log": "在 audit_log.py 中记录触发规则和人工确认状态。",
            "ai_disclosure": "在页面和文档中标注AI参与环节与局限。",
            "deployment_limit": "在部署文档中标注课程原型和真实场景限制。",
            "informed_consent": "在数据提交前展示知情同意说明。",
            "data_minimization": "只保留岗位匹配必需字段。",
            "anonymization": "对身份信息和联系方式做脱敏处理。",
            "user_opt_out": "提供退出个性化和撤回授权入口。",
            "safe_refusal": "对明显侵权需求拒绝并给出替代方案。",
            "prompt_injection_guard": "识别忽略规则或绕过限制类输入。",
        }
        for control_id in missing_control_ids:
            mapping_lines.append(f"- `{control_id}`：{mapping_explanations.get(control_id, '按伦理设计契约落实该控制措施。')}")
        mapping = "\n".join(mapping_lines) + "\n"
        marker = "## 8. 使用边界、验证与交付物"
        if marker in text:
            return text.replace(marker, mapping + "\n" + marker, 1)
        return text.rstrip() + "\n" + mapping

    def _llm_design_brief(self, analysis: RiskAnalysis, contract: EthicalContract) -> dict[str, Any]:
        system = """你是 EthicBuild 的系统设计补全模块，只输出 JSON。
你只负责补全真实项目设计要点；伦理边界以输入的 contract 为准，不得放宽。
如果 decision 是 block，只能设计安全替代原型，不能设计原始违规功能。
输出字段：
safe_project_name, project_goal, core_features, architecture_layers, data_flow,
code_structure, implementation_steps, ethics_summary, limitations。
所有列表字段必须是数组，每项不超过35个中文字符。只输出JSON对象。"""
        user = json.dumps(
            self._compact_payload(analysis, contract),
            ensure_ascii=False,
            separators=(",", ":"),
        )
        design = self.llm_client.json_complete(system=system, user=user, temperature=0.1, max_tokens=1200)  # type: ignore[union-attr]
        return self._normalize_design(design, analysis, contract)

    def _compact_payload(self, analysis: RiskAnalysis, contract: EthicalContract) -> dict:
        requirement = analysis.requirement
        return {
            "project": contract.project_name,
            "request": requirement.original_text,
            "domains": requirement.domains,
            "data_types": requirement.data_types,
            "capabilities": requirement.capabilities,
            "risk_level": analysis.risk_level.label,
            "decision": analysis.decision.label,
            "score": analysis.score.total,
            "rules": [
                {"id": rule.id, "name": rule.name, "reason": rule.reason}
                for rule in analysis.triggered_rules
            ],
            "allowed_functions": contract.allowed_functions,
            "forbidden_functions": contract.forbidden_functions,
            "required_controls": contract.required_controls,
            "data_boundaries": contract.data_boundaries,
            "human_review": contract.human_review_requirements,
            "deployment_limits": contract.deployment_limits,
        }

    def _template_generate(self, analysis: RiskAnalysis, contract: EthicalContract) -> str:
        return self._render_balanced_plan(
            analysis,
            contract,
            self._fallback_design(analysis, contract),
            source="本地模板",
        )

    def _render_balanced_plan(
        self,
        analysis: RiskAnalysis,
        contract: EthicalContract,
        design: dict[str, Any],
        source: str,
    ) -> str:
        requirement = analysis.requirement
        project_name = design.get("safe_project_name") or contract.project_name
        lines = [
            f"# {project_name}：伦理可控项目构建方案",
            "",
            "## 1. 项目定位",
            f"- 原始需求摘要：{requirement.summary or requirement.original_text}",
            f"- 风险等级：{analysis.risk_level.label}（{analysis.score.total}/15）",
            f"- 生成权限：{analysis.decision.label}",
            f"- 方案来源：{source}",
            f"- 设计目标：{design.get('project_goal')}",
            "",
            "## 2. 真实功能设计",
        ]
        lines.extend(f"- {item}" for item in design.get("core_features", []))

        lines.extend(
            [
                "",
                "## 3. 系统架构与数据流程",
                "### 架构层次",
            ]
        )
        lines.extend(f"- {item}" for item in design.get("architecture_layers", []))
        lines.append("### 数据流程")
        lines.extend(f"- {item}" for item in design.get("data_flow", []))

        lines.extend(
            [
                "",
                "## 4. 代码架构建议",
                "```text",
            ]
        )
        lines.extend(design.get("code_structure", []))
        lines.extend(
            [
                "```",
                "",
                "## 5. 实现步骤",
            ]
        )
        lines.extend(f"- {item}" for item in design.get("implementation_steps", []))

        lines.extend(
            [
                "",
                "## 6. 伦理控制设计",
                "### 风险判断",
            ]
        )
        lines.extend(f"- {item}" for item in analysis.explanation[:3])
        if analysis.triggered_rules:
            lines.append("- 触发规则：" + "；".join(f"{rule.id}（{rule.name}）" for rule in analysis.triggered_rules[:4]) + "。")
        lines.append("### 允许与禁止边界")
        lines.extend(f"- 允许：{item}" for item in contract.allowed_functions[:4])
        lines.extend(f"- 禁止：{item}" for item in contract.forbidden_functions[:5])
        lines.append("### 必须控制措施")
        lines.extend(f"- {item}" for item in self._group_controls(contract.required_controls))

        if analysis.decision == Decision.BLOCK:
            lines.extend(
                [
                    "",
                    "## 7. 安全替代方案",
                ]
            )
            alternatives = analysis.safe_alternatives or ["改为使用模拟数据、公开授权数据或用户自愿提交数据的课程原型。"]
            lines.extend(f"- {item}" for item in alternatives)

        lines.extend(
            [
                "",
                "## 8. 使用边界与交付物",
            ]
        )
        lines.extend(f"- {item}" for item in contract.deployment_limits)
        lines.extend(f"- {item}" for item in design.get("limitations", []))
        lines.append("- 系统输出是伦理辅助分析和项目原型建议，不替代法律、伦理委员会或项目负责人的最终判断。")
        return "\n".join(lines)

    def _fallback_design(self, analysis: RiskAnalysis, contract: EthicalContract) -> dict[str, Any]:
        requirement = analysis.requirement
        is_hiring = "hiring" in requirement.domains
        is_education = "education" in requirement.domains
        is_blocked = analysis.decision == Decision.BLOCK

        if is_blocked:
            safe_name = "合规自愿数据管理原型"
            goal = "将原始高风险需求改写为自愿提交、明确告知、可撤回授权的低风险课程原型。"
            features = [
                "自愿填写与授权确认表单",
                "模拟数据导入与本地分析",
                "数据用途、保存期限和删除入口展示",
                "拒绝原因和替代方案审计记录",
            ]
        elif is_hiring:
            safe_name = "AI简历辅助匹配与人工复核系统"
            goal = "将歧视性自动筛选改写为基于岗位技能的辅助匹配系统，AI只提供可解释建议。"
            features = [
                "岗位要求与技能关键词配置",
                "简历经历与岗位要求辅助匹配",
                "匹配依据高亮和解释说明",
                "人工复核工作台与申诉记录",
            ]
        elif is_education:
            safe_name = "可解释课程推荐辅助系统"
            goal = "基于最小化学习数据提供课程推荐，并允许用户理解、关闭和修正推荐。"
            features = [
                "学习目标和课程目录管理",
                "学习行为最小化采集与脱敏",
                "可解释课程推荐列表",
                "关闭个性化与人工调整入口",
            ]
        else:
            safe_name = contract.project_name
            goal = "在满足用户合理需求的同时，将伦理规则转化为项目边界和工程控制。"
            features = [
                "项目需求录入与模块化分析",
                "核心业务流程和结果展示",
                "伦理风险提示与用户告知",
                "审计日志和人工确认入口",
            ]

        return self._normalize_design(
            {
                "safe_project_name": safe_name,
                "project_goal": goal,
                "core_features": features,
                "architecture_layers": [
                    "表现层：Streamlit/网页表单、结果展示和下载",
                    "业务层：项目需求解析、领域功能服务和人工复核",
                    "伦理控制层：价值手册、风险评分、契约和审查",
                    "模型层：LLM适配器，仅在授权模式下调用",
                    "数据层：模拟数据、用户授权数据和审计日志",
                ],
                "data_flow": [
                    "用户输入需求和必要业务数据",
                    "需求先经过伦理契约和数据边界检查",
                    "业务模块只处理允许字段并生成辅助结果",
                    "人工复核确认后再展示或导出结论",
                    "审计日志记录触发规则、修改理由和输出版本",
                ],
                "code_structure": [
                    "controlled_project/",
                    "├── app.py                  # 页面入口与交互",
                    "├── domain_service.py       # 领域业务逻辑",
                    "├── ethics_contract.json    # 伦理设计契约",
                    "├── data_policy.md          # 数据边界和用户告知",
                    "├── review_workflow.py      # 人工复核与申诉流程",
                    "├── audit_log.py            # 审计记录",
                    "└── tests/",
                    "    └── test_ethics_controls.py",
                ],
                "implementation_steps": [
                    "先实现输入表单、模拟数据和结果页面",
                    "接入价值手册检查允许字段与禁止功能",
                    "实现核心业务模块和解释说明",
                    "加入人工复核、审计日志和下载报告",
                    "用低/中/高/拒绝案例进行测试",
                ],
                "ethics_summary": [],
                "limitations": [
                    "课程原型优先使用模拟数据，不直接接入真实高风险场景。",
                    "上线前需要人工负责人复核伦理契约和数据处理说明。",
                ],
            },
            analysis,
            contract,
        )

    def _normalize_design(
        self,
        design: dict[str, Any],
        analysis: RiskAnalysis,
        contract: EthicalContract,
    ) -> dict[str, Any]:
        fallback = {
            "safe_project_name": contract.project_name,
            "project_goal": "在保留合理项目目标的同时，将伦理边界转化为可执行的系统设计。",
            "core_features": [],
            "architecture_layers": [],
            "data_flow": [],
            "code_structure": [],
            "implementation_steps": [],
            "ethics_summary": [],
            "limitations": [],
        }
        normalized = fallback | {key: value for key, value in design.items() if value}
        for key in (
            "core_features",
            "architecture_layers",
            "data_flow",
            "code_structure",
            "implementation_steps",
            "ethics_summary",
            "limitations",
        ):
            normalized[key] = _as_list(normalized.get(key))

        if len(normalized["core_features"]) < 3:
            normalized["core_features"].extend(self._fallback_design(analysis, contract)["core_features"])
        if len(normalized["architecture_layers"]) < 3:
            normalized["architecture_layers"] = self._fallback_design(analysis, contract)["architecture_layers"]
        if len(normalized["data_flow"]) < 3:
            normalized["data_flow"] = self._fallback_design(analysis, contract)["data_flow"]
        if len(normalized["code_structure"]) < 5:
            normalized["code_structure"] = self._fallback_design(analysis, contract)["code_structure"]
        if len(normalized["implementation_steps"]) < 3:
            normalized["implementation_steps"] = self._fallback_design(analysis, contract)["implementation_steps"]
        if len(normalized["limitations"]) < 2:
            normalized["limitations"].extend([
                "课程原型优先使用模拟数据，不直接接入真实高风险场景。",
                "上线前需要人工负责人复核伦理契约和数据处理说明。",
            ])
        return normalized

    def _group_controls(self, controls: list[str]) -> list[str]:
        groups = {
            "隐私与数据": [],
            "公平与人工复核": [],
            "透明与追责": [],
            "安全与部署": [],
        }
        for control in controls:
            control_id = control.split(":", 1)[0].strip()
            if control_id in {"informed_consent", "data_minimization", "anonymization", "retention_limit", "local_or_encrypted_storage", "user_opt_out"}:
                groups["隐私与数据"].append(control)
            elif control_id in {"remove_sensitive_attributes", "fairness_test", "explainable_score", "human_review", "appeal_channel"}:
                groups["公平与人工复核"].append(control)
            elif control_id in {"ai_disclosure", "audit_log"}:
                groups["透明与追责"].append(control)
            else:
                groups["安全与部署"].append(control)
        result = []
        for group_name, items in groups.items():
            if items:
                result.append(f"{group_name}：" + "；".join(items))
        return result


def _as_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []
