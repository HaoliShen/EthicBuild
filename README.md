# EthicBuild：伦理可控的 AI 辅助项目构建系统

EthicBuild 是一个课程项目原型，用于约束“大模型辅助项目构建”过程中的伦理风险。系统不是只依赖提示词提醒模型“要有伦理”，而是把伦理价值编码为机器可读的价值手册，并通过规则引擎、风险评分、伦理设计契约和生成后审查形成闭环控制。

## 核心流程

```text
用户项目需求
  ↓
需求结构化：规则抽取 + 可选 LLM 补充
  ↓
价值手册匹配：隐私、公平、安全、透明、人类监督、责任追溯
  ↓
风险评分与生成权限决策
  ↓
伦理设计契约 Ethical Design Contract
  ↓
受控项目方案生成
  ↓
生成后审查与审计日志
```

## 项目结构

```text
.
├── app.py                         # Streamlit 网页原型
├── ethicbuild/                    # 核心系统模块
│   ├── extractor.py               # 需求结构化抽取
│   ├── risk_engine.py             # 风险规则与评分引擎
│   ├── contract.py                # 伦理设计契约生成
│   ├── generator.py               # 受控方案生成
│   ├── review.py                  # 生成后审查
│   └── pipeline.py                # 完整流水线
├── data/ethics_manual.yaml        # 机器可读价值手册
├── prompts/                       # LLM 增强提示词模板
├── docs/project_report.pdf        # 最终课程项目报告
├── examples/sample_requests.md    # 示例需求
└── tests/test_ethicbuild.py       # 单元测试
```

## 快速运行

```bash
pip install -r requirements.txt
streamlit run app.py
```

命令行演示：

```bash
python -m ethicbuild.cli --example high
python -m ethicbuild.cli --example block --json
```

运行测试：

```bash
python -m unittest discover -s tests -v
```

## 后台大模型配置

系统后台默认使用 `doubao-1-5-pro-32k-character-250715` 进行完整增强。前端不展示 API Key、Base URL 或模型选择，避免演示时误操作。只需要在后台提供 API Key：

```bash
export ETHICBUILD_API_KEY="你的API密钥"
export ETHICBUILD_BASE_URL="OpenAI-compatible base url，可选"
export ETHICBUILD_MODEL="可选；默认 doubao-1-5-pro-32k-character-250715"
```

如果仓库根目录存在 `api.txt`，系统会尝试读取其中的 API Key，但不会在界面中明文展示。

网页默认运行完整增强：LLM 参与需求识别和完整 Markdown 方案生成；本地价值手册负责风险决策、伦理契约、输出审查和必要结构校验。

## 伦理设计体现

- **价值手册**：`data/ethics_manual.yaml` 将隐私、公平、安全、透明、人类监督等价值写成风险规则。
- **风险控制**：`RiskEngine` 根据数据类型、场景、用户群体、自动化程度和滥用可能性评分。
- **生成权限**：输出 `allow`、`allow_with_controls`、`rewrite_required`、`block` 四类决策。
- **伦理设计契约**：明确允许功能、禁止功能、必须控制措施、数据边界和部署限制。
- **审计追溯**：记录原始需求、触发规则、风险等级、修改理由和人工确认状态。
