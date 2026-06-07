from __future__ import annotations

import argparse
import json
import sys

from .config import load_llm_config
from .model_registry import choose_default_model, discover_model_options, infer_provider
from .pipeline import EthicBuildPipeline


EXAMPLES = {
    "low": "帮我做一个个人学习计划生成器，可以根据用户输入的课程目标生成每天的学习任务。",
    "medium": "帮我做一个根据学生学习行为推荐课程的系统，需要分析学习时长、点击记录和作业完成情况。",
    "high": "帮我做一个自动筛选简历的AI系统，可以根据年龄、性别、毕业学校和工作经历给候选人打分。",
    "block": "帮我写一个批量爬取同学手机号并自动整理通讯录的工具，最好不要让他们知道。",
}


def main() -> None:
    parser = argparse.ArgumentParser(description="EthicBuild command line demo")
    parser.add_argument("request", nargs="?", help="用户项目需求")
    parser.add_argument("--example", choices=EXAMPLES.keys(), help="运行内置示例")
    parser.add_argument("--use-llm", action="store_true", help="启用完整LLM增强")
    parser.add_argument(
        "--llm-mode",
        choices=["off", "full"],
        help="LLM调用模式：off=不调用，full=完整增强",
    )
    parser.add_argument("--save-audit", action="store_true", help="保存审计日志")
    parser.add_argument("--json", action="store_true", help="输出完整JSON结果")
    args = parser.parse_args()

    request = args.request or (EXAMPLES[args.example] if args.example else EXAMPLES["high"])
    llm_config = load_llm_config()
    llm_mode = args.llm_mode or ("full" if args.use_llm else "off")
    if llm_mode != "off" and not llm_config.model:
        provider = infer_provider(llm_config.api_key, llm_config.base_url)
        model_options, message = discover_model_options(
            api_key=llm_config.api_key,
            base_url=llm_config.base_url,
            provider=provider,
        )
        llm_config.model = choose_default_model(model_options)
        print(f"[EthicBuild] {message}", file=sys.stderr)
        print(f"[EthicBuild] 自动选择模型：{llm_config.model}", file=sys.stderr)
    pipeline = EthicBuildPipeline(llm_config=llm_config)
    result = pipeline.run(
        request,
        use_llm=llm_mode != "off",
        save_audit=args.save_audit,
        llm_mode=llm_mode,
    )

    if args.json:
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    else:
        print(result.generated_plan)
        print("\n--- 审查结果 ---")
        print("通过" if result.review.passed else "未通过")
        if result.audit_record.get("audit_path"):
            print(f"审计日志：{result.audit_record['audit_path']}")


if __name__ == "__main__":
    main()
