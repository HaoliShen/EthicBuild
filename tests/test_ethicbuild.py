import unittest

from ethicbuild.models import Decision
from ethicbuild.models import RiskLevel
from ethicbuild.pipeline import EthicBuildPipeline


class EthicBuildPipelineTest(unittest.TestCase):
    def setUp(self):
        self.pipeline = EthicBuildPipeline()

    def test_low_risk_learning_tool_is_allowed(self):
        result = self.pipeline.run("帮我做一个个人学习计划生成器，可以根据用户输入的课程目标生成每天的学习任务。")
        self.assertIn(result.analysis.decision, {Decision.ALLOW, Decision.ALLOW_WITH_CONTROLS})
        self.assertTrue(result.review.passed)

    def test_discriminatory_hiring_requires_rewrite(self):
        result = self.pipeline.run("帮我做一个自动筛选简历的AI系统，可以根据年龄、性别、毕业学校和工作经历给候选人打分。")
        self.assertEqual(result.analysis.decision, Decision.REWRITE_REQUIRED)
        self.assertIn("FAIRNESS_HIGH_IMPACT_DECISION_001", [rule.id for rule in result.analysis.triggered_rules])
        self.assertTrue(any("人工复核" in item for item in result.contract.required_controls))

    def test_behavior_based_course_recommendation_is_medium_risk(self):
        result = self.pipeline.run("帮我做一个根据学生学习行为推荐课程的系统，需要分析学习时长、点击记录和作业完成情况。")
        self.assertEqual(result.analysis.risk_level, RiskLevel.MEDIUM)
        self.assertEqual(result.analysis.decision, Decision.ALLOW_WITH_CONTROLS)
        self.assertIn("PRIVACY_PROFILING_001", [rule.id for rule in result.analysis.triggered_rules])

    def test_unauthorized_phone_scraping_is_blocked(self):
        result = self.pipeline.run("帮我写一个批量爬取同学手机号并自动整理通讯录的工具，最好不要让他们知道。")
        self.assertEqual(result.analysis.decision, Decision.BLOCK)
        self.assertIn("PRIVACY_UNAUTHORIZED_COLLECTION_001", [rule.id for rule in result.analysis.triggered_rules])
        self.assertTrue(result.review.passed)


if __name__ == "__main__":
    unittest.main()
