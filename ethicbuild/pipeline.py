from __future__ import annotations

from time import perf_counter

from .audit import AuditLogger
from .config import LLMConfig, load_llm_config
from .contract import ContractBuilder
from .extractor import RequirementExtractor
from .generator import ProjectGenerator
from .llm import LLMClient
from .manual import ValueManual
from .models import PipelineResult
from .review import OutputReviewer
from .risk_engine import RiskEngine


class EthicBuildPipeline:
    def __init__(
        self,
        manual: ValueManual | None = None,
        llm_config: LLMConfig | None = None,
        audit_logger: AuditLogger | None = None,
    ):
        self.manual = manual or ValueManual.load()
        self.llm_config = llm_config or load_llm_config()
        self.llm_client = LLMClient(self.llm_config)
        self.extractor = RequirementExtractor(self.manual, self.llm_client)
        self.risk_engine = RiskEngine(self.manual)
        self.contract_builder = ContractBuilder(self.manual)
        self.generator = ProjectGenerator(self.llm_client)
        self.reviewer = OutputReviewer()
        self.audit_logger = audit_logger or AuditLogger()

    def run(
        self,
        user_request: str,
        use_llm: bool = False,
        save_audit: bool = False,
        llm_mode: str | None = None,
    ) -> PipelineResult:
        mode = llm_mode or ("full" if use_llm else "off")
        use_llm_for_extract = mode in {"extract", "full"}
        use_llm_for_generate = mode == "full"
        timings: dict[str, float] = {}

        start = perf_counter()
        requirement = self.extractor.extract(user_request, use_llm=use_llm_for_extract)
        timings["requirement_extraction"] = round(perf_counter() - start, 3)

        start = perf_counter()
        analysis = self.risk_engine.analyze(requirement)
        timings["risk_analysis"] = round(perf_counter() - start, 3)

        start = perf_counter()
        contract = self.contract_builder.build(analysis)
        timings["contract_building"] = round(perf_counter() - start, 3)

        start = perf_counter()
        generated_plan = self.generator.generate(analysis, contract, use_llm=use_llm_for_generate)
        timings["project_generation"] = round(perf_counter() - start, 3)

        start = perf_counter()
        review = self.reviewer.review(generated_plan, contract)
        if not review.passed:
            generated_plan = self._append_review_corrections(generated_plan, review)
            review = self.reviewer.review(generated_plan, contract)
        timings["output_review"] = round(perf_counter() - start, 3)

        start = perf_counter()
        audit_record = self.audit_logger.build_record(
            analysis=analysis,
            contract=contract,
            review=review,
            generated_plan=generated_plan,
        )
        if save_audit:
            audit_path = self.audit_logger.save(audit_record)
            audit_record["audit_path"] = str(audit_path)
        timings["audit"] = round(perf_counter() - start, 3)
        timings["total"] = round(sum(timings.values()), 3)
        audit_record["llm_mode"] = mode
        audit_record["timings"] = timings
        return PipelineResult(
            analysis=analysis,
            contract=contract,
            generated_plan=generated_plan,
            review=review,
            audit_record=audit_record,
            timings=timings,
        )

    def _append_review_corrections(self, generated_plan: str, review) -> str:
        lines = [generated_plan, "", "## 生成后审查修正补充"]
        if review.missing_controls:
            lines.append("- 以下控制措施在初稿中不够明确，已强制补充：")
            lines.extend(f"  - {item}" for item in review.missing_controls)
        if review.forbidden_hits:
            lines.append("- 以下内容不得作为实现功能，只能作为风险说明或禁止项呈现：")
            lines.extend(f"  - {item}" for item in review.forbidden_hits)
        return "\n".join(lines)
