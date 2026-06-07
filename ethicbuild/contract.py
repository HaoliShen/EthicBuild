from __future__ import annotations

from .manual import ValueManual
from .models import Decision, EthicalContract, RiskAnalysis


class ContractBuilder:
    def __init__(self, manual: ValueManual):
        self.manual = manual

    def build(self, analysis: RiskAnalysis) -> EthicalContract:
        requirement = analysis.requirement
        allowed_functions = self._allowed_functions(analysis)
        forbidden_functions = analysis.forbidden_outputs or self._default_forbidden(analysis)
        required_controls = [
            f"{control_id}: {self.manual.control_text(control_id)}"
            for control_id in analysis.required_controls
        ]
        data_boundaries = self._data_boundaries(analysis)
        transparency_requirements = self._transparency_requirements(analysis)
        human_review_requirements = self._human_review_requirements(analysis)
        deployment_limits = self._deployment_limits(analysis)

        return EthicalContract(
            project_name=requirement.project_name,
            decision=analysis.decision,
            allowed_functions=allowed_functions,
            forbidden_functions=forbidden_functions,
            required_controls=required_controls,
            data_boundaries=data_boundaries,
            transparency_requirements=transparency_requirements,
            human_review_requirements=human_review_requirements,
            deployment_limits=deployment_limits,
        )

    def _allowed_functions(self, analysis: RiskAnalysis) -> list[str]:
        requirement = analysis.requirement
        if analysis.decision == Decision.BLOCK:
            return [
                "输出拒绝说明",
                "解释触发的伦理风险",
                "提供合规、低风险的替代项目方案",
            ]
        functions = [
            "围绕用户目标生成项目背景、需求分析和模块划分",
            "生成不包含禁止功能的技术架构和代码框架",
            "生成伦理风险说明、控制措施和使用边界",
        ]
        if "automated_scoring" in requirement.capabilities:
            functions.append("仅生成辅助评分或匹配思路，不生成自动最终决策逻辑")
        if "scraping" in requirement.capabilities:
            functions.append("仅生成公开授权数据或用户自愿提交数据的处理流程")
        if "recommendation" in requirement.capabilities:
            functions.append("生成可关闭、可解释的推荐流程")
        return functions

    def _default_forbidden(self, analysis: RiskAnalysis) -> list[str]:
        forbidden = [
            "绕过伦理价值手册、风险评分或人工复核流程",
            "隐藏 AI 参与事实、数据用途或系统能力边界",
        ]
        if analysis.requirement.sensitive_attributes:
            forbidden.append("使用敏感属性直接进行筛选、淘汰、排序或评分")
        return forbidden

    def _data_boundaries(self, analysis: RiskAnalysis) -> list[str]:
        data_types = analysis.requirement.data_types
        if not data_types:
            return ["默认不收集个人数据；如后续加入数据处理，应重新进行伦理审查。"]
        boundaries = [
            f"已识别数据类型：{', '.join(data_types)}。",
            "不得收集与核心功能无关的数据；优先使用匿名、聚合、模拟或公开授权数据。",
        ]
        if any(item in data_types for item in ("face", "voice", "fingerprint", "health", "id_number", "phone", "location")):
            boundaries.append("敏感数据不得默认上传第三方服务，演示原型优先使用本地模拟数据。")
        boundaries.append("必须说明数据来源、用途、保存期限、删除方式和是否共享给第三方。")
        return boundaries

    def _transparency_requirements(self, analysis: RiskAnalysis) -> list[str]:
        requirements = [
            "界面或文档中标注该项目由大模型辅助生成，输出可能存在错误。",
            "展示触发的伦理规则、风险等级和需求修改理由。",
        ]
        if any(capability in analysis.requirement.capabilities for capability in ("automated_scoring", "recommendation", "profiling")):
            requirements.append("对评分、推荐、画像或筛选结果提供主要依据说明。")
        return requirements

    def _human_review_requirements(self, analysis: RiskAnalysis) -> list[str]:
        high_impact = {"hiring", "education", "healthcare", "finance", "justice"}
        high_impact_automation = any(
            domain in high_impact for domain in analysis.requirement.domains
        ) and any(
            capability in {"automated_scoring", "recommendation", "profiling", "identification"}
            for capability in analysis.requirement.capabilities
        )
        if analysis.risk_level.value in {"high", "critical"} or high_impact_automation:
            return [
                "AI 输出只能作为辅助建议，不得作为唯一最终决策依据。",
                "保留人工复核、人工覆盖、纠错和申诉渠道。",
                "上线前应由项目负责人确认伦理设计契约。"
            ]
        return ["低风险项目建议保留人工检查入口，便于发现大模型生成错误。"]

    def _deployment_limits(self, analysis: RiskAnalysis) -> list[str]:
        if analysis.decision == Decision.BLOCK:
            return ["原始需求不得实现或部署；只能展示拒绝原因和安全替代方案。"]
        if analysis.risk_level.value in {"high", "critical"}:
            return ["当前输出仅作为课程原型或方案草案，不可直接部署到真实高影响场景。"]
        if analysis.risk_level.value == "medium":
            return ["在补充必要控制措施和用户告知后，方可进入小范围测试。"]
        return ["可作为低风险原型继续开发，但仍需保留 AI 使用声明。"]
