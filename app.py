from __future__ import annotations

import json

import streamlit as st

from ethicbuild.cli import EXAMPLES
from ethicbuild.pipeline import EthicBuildPipeline


st.set_page_config(page_title="EthicBuild", page_icon="🛡️", layout="wide")


EXAMPLE_LABELS = {
    "low": "低风险 · 学习计划生成器",
    "medium": "中风险 · 学习行为课程推荐",
    "high": "高风险 · 简历自动筛选",
    "block": "拒绝类 · 批量爬取手机号",
}

RISK_BADGE_COLORS = {
    "low": "#16a34a",
    "medium": "#d97706",
    "high": "#dc2626",
    "critical": "#7f1d1d",
}

DECISION_TEXT = {
    "allow": "允许",
    "allow_with_controls": "加控制后允许",
    "rewrite_required": "重写为低风险方案",
    "block": "拒绝原需求",
}


def inject_style() -> None:
    st.markdown(
        """
        <style>
        [data-testid="stSidebar"] {
            display: none;
        }
        [data-testid="collapsedControl"] {
            display: none;
        }
        body {
            background: #f8fafc;
        }
        .block-container {
            padding-top: 1.45rem;
            max-width: 1260px;
        }
        .hero {
            position: relative;
            overflow: hidden;
            padding: 2.05rem 2.2rem;
            border-radius: 30px;
            background:
                radial-gradient(circle at 15% 20%, rgba(56, 189, 248, .32), transparent 28%),
                radial-gradient(circle at 88% 15%, rgba(45, 212, 191, .30), transparent 30%),
                linear-gradient(135deg, #0f172a 0%, #1d4ed8 48%, #0f766e 100%);
            color: white;
            margin-bottom: 1rem;
            box-shadow: 0 24px 70px rgba(15, 23, 42, 0.20);
        }
        .hero::after {
            content: "";
            position: absolute;
            right: -70px;
            bottom: -80px;
            width: 260px;
            height: 260px;
            border-radius: 999px;
            background: rgba(255,255,255,.10);
            border: 1px solid rgba(255,255,255,.18);
        }
        .hero-kicker {
            display: inline-flex;
            align-items: center;
            gap: .45rem;
            padding: .32rem .7rem;
            border-radius: 999px;
            background: rgba(255,255,255,.13);
            color: #dbeafe;
            font-size: .84rem;
            font-weight: 700;
            margin-bottom: .75rem;
        }
        .hero h1 {
            margin: 0;
            font-size: 2.32rem;
            letter-spacing: -0.04em;
            line-height: 1.12;
        }
        .hero p {
            max-width: 820px;
            margin: .78rem 0 0 0;
            color: #dbeafe;
            font-size: 1.02rem;
            line-height: 1.65;
        }
        .pipeline {
            display: grid;
            grid-template-columns: repeat(6, 1fr);
            gap: .65rem;
            margin: 1rem 0 1.3rem 0;
        }
        .pipe-step {
            background: rgba(255,255,255,.88);
            border: 1px solid rgba(226, 232, 240, .92);
            border-radius: 18px;
            padding: .78rem .85rem;
            color: #1e293b;
            font-size: .88rem;
            font-weight: 650;
            text-align: center;
            box-shadow: 0 8px 22px rgba(15,23,42,.05);
        }
        .panel {
            border: 1px solid #e2e8f0;
            border-radius: 24px;
            padding: 1.15rem 1.18rem;
            background: rgba(255,255,255,.96);
            box-shadow: 0 12px 34px rgba(15, 23, 42, 0.06);
        }
        .input-shell {
            border: 1px solid #e2e8f0;
            border-radius: 24px;
            padding: 1.15rem;
            background: #ffffff;
            box-shadow: 0 14px 38px rgba(15,23,42,.07);
        }
        .section-title {
            display: flex;
            align-items: center;
            gap: .55rem;
            margin: .1rem 0 .85rem 0;
            font-size: 1.13rem;
            font-weight: 800;
            color: #0f172a;
        }
        .section-dot {
            width: 10px;
            height: 10px;
            border-radius: 999px;
            background: linear-gradient(135deg, #2563eb, #14b8a6);
        }
        .status-card {
            border-radius: 18px;
            padding: 1rem 1.1rem;
            border: 1px solid #e2e8f0;
            background: #ffffff;
            min-height: 112px;
        }
        .status-label {
            color: #64748b;
            font-size: .82rem;
            margin-bottom: .35rem;
        }
        .status-value {
            font-size: 1.22rem;
            font-weight: 750;
            color: #0f172a;
            line-height: 1.25;
        }
        .badge {
            display: inline-flex;
            align-items: center;
            padding: .22rem .58rem;
            border-radius: 999px;
            color: white;
            font-size: .78rem;
            font-weight: 700;
        }
        .small-muted {
            color: #64748b;
            font-size: .86rem;
        }
        .feature-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: .72rem;
        }
        .feature-card {
            border-radius: 18px;
            padding: .9rem .95rem;
            background: #f8fafc;
            border: 1px solid #e2e8f0;
        }
        .feature-card b {
            color: #0f172a;
        }
        .contract-list li {
            margin-bottom: .35rem;
        }
        div[data-testid="stTabs"] button {
            font-weight: 650;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


@st.cache_resource
def build_pipeline() -> EthicBuildPipeline:
    return EthicBuildPipeline()


def render_hero() -> None:
    st.markdown(
        """
        <div class="hero">
          <div class="hero-kicker">🛡️ Value Manual · Risk Engine · LLM Guardrails</div>
          <h1>EthicBuild · 伦理可控的 AI 辅助项目构建系统</h1>
          <p>
          面向“大模型辅助项目开发”的伦理风险控制原型：用户输入项目需求后，
          系统先进行需求识别、价值手册匹配和风险决策，再生成兼顾真实实现与伦理约束的项目方案。
          </p>
        </div>
        <div class="pipeline">
          <div class="pipe-step">需求输入</div>
          <div class="pipe-step">LLM需求识别</div>
          <div class="pipe-step">价值手册匹配</div>
          <div class="pipe-step">伦理设计契约</div>
          <div class="pipe-step">完整方案生成</div>
          <div class="pipe-step">审查与审计</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_status_cards(result) -> None:
    analysis = result.analysis
    review = result.review
    risk_color = RISK_BADGE_COLORS.get(analysis.risk_level.value, "#475569")
    cards = st.columns(4)
    cards[0].markdown(
        f"""
        <div class="status-card">
          <div class="status-label">伦理风险等级</div>
          <div class="status-value">
            <span class="badge" style="background:{risk_color};">{analysis.risk_level.label}</span>
          </div>
          <div class="small-muted" style="margin-top:.55rem;">五维评分 {analysis.score.total}/15</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    cards[1].markdown(
        f"""
        <div class="status-card">
          <div class="status-label">生成权限决策</div>
          <div class="status-value">{DECISION_TEXT.get(analysis.decision.value, analysis.decision.label)}</div>
          <div class="small-muted" style="margin-top:.55rem;">由本地价值手册决定</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    cards[2].markdown(
        f"""
        <div class="status-card">
          <div class="status-label">输出审查</div>
          <div class="status-value">{"通过" if review.passed else "需修正"}</div>
          <div class="small-muted" style="margin-top:.55rem;">禁止项与控制项校验</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    cards[3].markdown(
        f"""
        <div class="status-card">
          <div class="status-label">总耗时</div>
          <div class="status-value">{result.timings.get("total", 0)}s</div>
          <div class="small-muted" style="margin-top:.55rem;">完整增强模式</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_contract(contract) -> None:
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("#### 允许功能")
        for item in contract.allowed_functions:
            st.markdown(f"- {item}")
        st.markdown("#### 数据边界")
        for item in contract.data_boundaries:
            st.markdown(f"- {item}")
    with col_b:
        st.markdown("#### 禁止功能")
        for item in contract.forbidden_functions:
            st.markdown(f"- {item}")
        st.markdown("#### 必须控制措施")
        for item in contract.required_controls:
            st.markdown(f"- `{item.split(':', 1)[0]}`：{item.split(':', 1)[1].strip() if ':' in item else item}")


inject_style()
render_hero()

save_audit = True

input_col, guide_col = st.columns([1.28, 0.92], gap="large")

with input_col:
    st.markdown('<div class="input-shell">', unsafe_allow_html=True)
    st.markdown('<div class="section-title"><span class="section-dot"></span>输入项目需求</div>', unsafe_allow_html=True)
    selected_example = st.segmented_control(
        "选择示例或自定义输入",
        options=["custom", "low", "medium", "high", "block"],
        format_func=lambda key: "自定义" if key == "custom" else EXAMPLE_LABELS[key],
        default="high",
        label_visibility="collapsed",
    )
    default_text = "" if selected_example == "custom" else EXAMPLES[selected_example]
    request_text = st.text_area(
        "项目需求",
        value=default_text,
        height=210,
        placeholder="例如：帮我做一个自动筛选简历的AI系统，可以根据年龄、性别、毕业学校和工作经历给候选人打分。",
        label_visibility="collapsed",
    )
    run_button = st.button(
        "生成伦理可控项目方案",
        type="primary",
        use_container_width=True,
        disabled=not request_text.strip(),
    )
    st.markdown('</div>', unsafe_allow_html=True)

with guide_col:
    st.markdown('<div class="section-title"><span class="section-dot"></span>系统能力</div>', unsafe_allow_html=True)
    st.markdown(
        """
        <div class="panel">
          <div class="feature-grid">
            <div class="feature-card"><b>需求识别</b><br><span class="small-muted">抽取领域、数据、能力和影响权益</span></div>
            <div class="feature-card"><b>风险决策</b><br><span class="small-muted">根据价值手册输出允许、重写或拒绝</span></div>
            <div class="feature-card"><b>方案生成</b><br><span class="small-muted">生成真实功能、架构、代码模块和实现逻辑</span></div>
            <div class="feature-card"><b>伦理审查</b><br><span class="small-muted">检查禁止功能、控制措施和审计记录</span></div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

if run_button:
    pipeline = build_pipeline()
    with st.spinner("正在调用后台模型并执行伦理控制链路，完整增强通常需要 20–40 秒..."):
        result = pipeline.run(
            request_text,
            use_llm=True,
            save_audit=save_audit,
            llm_mode="full",
        )

    analysis = result.analysis
    contract = result.contract

    st.markdown("---")
    st.markdown("### 3. 风险与决策总览")
    render_status_cards(result)

    st.markdown("### 4. 结果详情")
    tabs = st.tabs(["完整项目方案", "伦理风险分析", "伦理设计契约", "审计记录"])

    with tabs[0]:
        st.markdown(result.generated_plan)
        st.download_button(
            "下载 Markdown 方案",
            data=result.generated_plan,
            file_name="ethicbuild_generated_plan.md",
            mime="text/markdown",
            use_container_width=True,
        )

    with tabs[1]:
        left, right = st.columns([0.95, 1.05])
        with left:
            st.markdown("#### 结构化需求")
            st.json(analysis.requirement.to_dict(), expanded=False)
        with right:
            st.markdown("#### 触发规则")
            if analysis.triggered_rules:
                for rule in analysis.triggered_rules:
                    st.markdown(f"- **{rule.id}**：{rule.name}  \n  <span class='small-muted'>{rule.reason}</span>", unsafe_allow_html=True)
            else:
                st.info("未触发高风险规则。")
            st.markdown("#### 风险解释")
            for item in analysis.explanation:
                st.markdown(f"- {item}")

    with tabs[2]:
        render_contract(contract)

    with tabs[3]:
        st.json(result.audit_record, expanded=False)
        st.download_button(
            "下载完整 JSON 结果",
            data=json.dumps(result.to_dict(), ensure_ascii=False, indent=2),
            file_name="ethicbuild_result.json",
            mime="application/json",
            use_container_width=True,
        )
else:
    st.markdown("---")
    st.markdown(
        """
        <div class="panel">
          <b>演示建议</b>
          <p class="small-muted" style="margin-bottom:0;">
          可先选择“高风险 · 简历自动筛选”，观察系统如何把歧视性自动决策需求重写为
          技能匹配、人工复核、可解释评分和申诉机制并存的项目方案。
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
