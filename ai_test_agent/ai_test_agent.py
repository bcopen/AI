"""
Web AI 自动化测试 Agent 核心主类
基于 Python + Playwright + AI 大模型实现
"""

import os
import time
import uuid
import json
from datetime import datetime
from typing import Callable, Dict, List, Any, Optional
from pathlib import Path

from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext
from dotenv import load_dotenv
from jinja2 import Template
from openai import OpenAI

# 加载环境变量
load_dotenv()


class BugInfo:
    """缺陷信息类"""
    
    def __init__(self, bug_id: str, test_case_name: str, error_message: str,
                 screenshot_path: str, timestamp: str):
        self.bug_id = bug_id
        self.test_case_name = test_case_name
        self.error_message = error_message
        self.screenshot_path = screenshot_path
        self.timestamp = timestamp
        self.ai_analysis: Optional[Dict[str, Any]] = None


class TestCaseResult:
    """测试结果类"""
    
    def __init__(self, test_case_name: str, status: str, duration: float,
                 timestamp: str, error_message: Optional[str] = None,
                 bug_info: Optional[BugInfo] = None):
        self.test_case_name = test_case_name
        self.status = status  # PASSED, FAILED, SKIPPED
        self.duration = duration
        self.timestamp = timestamp
        self.error_message = error_message
        self.bug_info = bug_info


class AITestAgent:
    """AI 测试 Agent 核心类"""
    
    def __init__(self, headless: bool = True):
        """
        初始化测试 Agent
        
        Args:
            headless: 是否无头模式，默认 True
        """
        self.test_web_url = os.getenv("TEST_WEB_URL", "http://localhost:8080")
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "")
        self.openai_base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        self.report_title = os.getenv("REPORT_TITLE", "Web AI 自动化测试报告")
        
        self.headless = headless
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        
        self.test_results: List[TestCaseResult] = []
        self.bugs: List[BugInfo] = []
        
        # 目录初始化
        self.base_dir = Path(__file__).parent
        self.reports_dir = self.base_dir / "reports"
        self.screenshots_dir = self.base_dir / "screenshots"
        
        self.reports_dir.mkdir(exist_ok=True)
        self.screenshots_dir.mkdir(exist_ok=True)
        
        # 初始化 AI 客户端
        self.ai_client: Optional[OpenAI] = None
        if self.openai_api_key:
            self.ai_client = OpenAI(
                api_key=self.openai_api_key,
                base_url=self.openai_base_url
            )
    
    def start_browser(self):
        """启动浏览器"""
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=self.headless)
        self.context = self.browser.new_context(
            viewport={"width": 1920, "height": 1080}
        )
        self.page = self.context.new_page()
        print(f"[INFO] 浏览器已启动，模式：{'无头' if self.headless else '可视化'}")
    
    def close_browser(self):
        """关闭浏览器"""
        if self.page:
            self.page.close()
        if self.context:
            self.context.close()
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
        print("[INFO] 浏览器已关闭")
    
    def open_web_system(self, url: Optional[str] = None):
        """
        打开被测 Web 系统
        
        Args:
            url: 可选的自定义 URL，默认使用环境变量中的地址
        """
        target_url = url or self.test_web_url
        if self.page is None:
            self.start_browser()
        self.page.goto(target_url, timeout=30000)
        print(f"[INFO] 已打开页面：{target_url}")
    
    def execute_test_case(self, test_case_name: str, 
                          page_operation: Callable[[Page], None]) -> TestCaseResult:
        """
        执行单条测试用例
        
        Args:
            test_case_name: 用例名称
            page_operation: 页面操作函数，接收 Page 对象作为参数
            
        Returns:
            TestCaseResult: 测试结果对象
        """
        start_time = time.time()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if self.page is None:
            self.start_browser()
        
        try:
            # 执行测试操作
            page_operation(self.page)
            
            end_time = time.time()
            duration = round(end_time - start_time, 2)
            
            result = TestCaseResult(
                test_case_name=test_case_name,
                status="PASSED",
                duration=duration,
                timestamp=timestamp
            )
            
            print(f"[PASS] {test_case_name} (耗时：{duration}s)")
            
        except Exception as e:
            end_time = time.time()
            duration = round(end_time - start_time, 2)
            
            # 捕获异常，生成 Bug
            bug_info = self._capture_bug(test_case_name, str(e))
            
            result = TestCaseResult(
                test_case_name=test_case_name,
                status="FAILED",
                duration=duration,
                timestamp=timestamp,
                error_message=str(e),
                bug_info=bug_info
            )
            
            print(f"[FAIL] {test_case_name} (耗时：{duration}s) - {str(e)}")
        
        self.test_results.append(result)
        return result
    
    def _capture_bug(self, test_case_name: str, error_message: str) -> BugInfo:
        """
        捕获缺陷信息并截图
        
        Args:
            test_case_name: 用例名称
            error_message: 错误信息
            
        Returns:
            BugInfo: 缺陷信息对象
        """
        bug_id = f"BUG-{uuid.uuid4().hex[:8].upper()}"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        screenshot_filename = f"{bug_id}_{timestamp}.png"
        screenshot_path = self.screenshots_dir / screenshot_filename
        
        # 保存全屏截图
        if self.page:
            self.page.screenshot(path=str(screenshot_path), full_page=True)
            print(f"[SCREENSHOT] 已保存截图：{screenshot_path}")
        
        bug_info = BugInfo(
            bug_id=bug_id,
            test_case_name=test_case_name,
            error_message=error_message,
            screenshot_path=str(screenshot_path),
            timestamp=timestamp
        )
        
        # 调用 AI 分析缺陷
        self._analyze_bug_with_ai(bug_info)
        
        self.bugs.append(bug_info)
        return bug_info
    
    def _analyze_bug_with_ai(self, bug_info: BugInfo):
        """
        使用 AI 分析缺陷原因、复现步骤、修复建议
        
        Args:
            bug_info: 缺陷信息对象
        """
        if not self.ai_client:
            print("[WARN] AI 客户端未配置，跳过智能分析")
            return
        
        try:
            prompt = f"""
你是一个专业的软件测试专家。请分析以下 Web 自动化测试中发现的缺陷：

【缺陷编号】{bug_info.bug_id}
【测试用例】{bug_info.test_case_name}
【错误信息】{bug_info.error_message}
【发现时间】{bug_info.timestamp}

请提供以下分析内容（使用 JSON 格式返回）：
{{
    "root_cause": "问题根本原因分析",
    "reproduction_steps": ["复现步骤 1", "复现步骤 2", ...],
    "fix_suggestion": "修复建议",
    "severity": "严重程度（Critical/High/Medium/Low）",
    "affected_module": "受影响的模块"
}}
"""
            
            response = self.ai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "你是一个专业的软件测试专家，擅长分析 Web 应用缺陷并提供修复建议。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1000
            )
            
            ai_response = response.choices[0].message.content
            
            # 尝试解析 JSON 响应
            try:
                # 清理可能的 markdown 标记
                ai_response_clean = ai_response.replace("```json", "").replace("```", "").strip()
                analysis_result = json.loads(ai_response_clean)
                bug_info.ai_analysis = analysis_result
                print(f"[AI ANALYSIS] 已完成缺陷 {bug_info.bug_id} 的智能分析")
            except json.JSONDecodeError:
                bug_info.ai_analysis = {"raw_analysis": ai_response}
                print(f"[AI ANALYSIS] 解析失败，保存原始分析结果")
                
        except Exception as e:
            print(f"[ERROR] AI 分析失败：{str(e)}")
            bug_info.ai_analysis = {"error": f"AI 分析出错：{str(e)}"}
    
    def generate_test_report(self, output_format: str = "all"):
        """
        生成测试报告
        
        Args:
            output_format: 输出格式，可选 "html", "markdown", "all"
        """
        if not self.test_results:
            print("[WARN] 没有测试结果，无法生成报告")
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 统计数据
        total_cases = len(self.test_results)
        passed_cases = sum(1 for r in self.test_results if r.status == "PASSED")
        failed_cases = sum(1 for r in self.test_results if r.status == "FAILED")
        pass_rate = round((passed_cases / total_cases * 100), 2) if total_cases > 0 else 0
        
        report_data = {
            "title": self.report_title,
            "generate_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_cases": total_cases,
            "passed_cases": passed_cases,
            "failed_cases": failed_cases,
            "pass_rate": pass_rate,
            "test_results": self.test_results,
            "bugs": self.bugs
        }
        
        if output_format in ["html", "all"]:
            self._generate_html_report(report_data, timestamp)
        
        if output_format in ["markdown", "all"]:
            self._generate_markdown_report(report_data, timestamp)
        
        print(f"[REPORT] 测试报告已生成")
    
    def _generate_html_report(self, report_data: Dict, timestamp: str):
        """生成 HTML 可视化报告"""
        
        html_template = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }}</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f5f7fa; padding: 20px; }
        .container { max-width: 1200px; margin: 0 auto; background: white; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); overflow: hidden; }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; }
        .header h1 { font-size: 28px; margin-bottom: 10px; }
        .header p { opacity: 0.9; }
        .summary { display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; padding: 30px; background: #f8f9fa; border-bottom: 1px solid #e9ecef; }
        .summary-item { text-align: center; padding: 20px; background: white; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
        .summary-item .value { font-size: 32px; font-weight: bold; color: #667eea; }
        .summary-item .label { color: #6c757d; margin-top: 5px; }
        .section { padding: 30px; }
        .section h2 { color: #333; margin-bottom: 20px; padding-bottom: 10px; border-bottom: 2px solid #667eea; }
        table { width: 100%; border-collapse: collapse; margin-bottom: 20px; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #e9ecef; }
        th { background: #f8f9fa; color: #495057; font-weight: 600; }
        tr:hover { background: #f8f9fa; }
        .status-passed { color: #28a745; font-weight: bold; }
        .status-failed { color: #dc3545; font-weight: bold; }
        .bug-card { background: #fff5f5; border-left: 4px solid #dc3545; padding: 15px; margin-bottom: 15px; border-radius: 0 8px 8px 0; }
        .bug-id { font-weight: bold; color: #dc3545; }
        .ai-analysis { background: #f0f7ff; border-left: 4px solid #667eea; padding: 15px; margin-top: 10px; border-radius: 0 8px 8px 0; }
        .ai-analysis h4 { color: #667eea; margin-bottom: 10px; }
        .severity-Critical { color: #dc3545; font-weight: bold; }
        .severity-High { color: #fd7e14; font-weight: bold; }
        .severity-Medium { color: #ffc107; font-weight: bold; }
        .severity-Low { color: #28a745; font-weight: bold; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{{ title }}</h1>
            <p>生成时间：{{ generate_time }}</p>
        </div>
        
        <div class="summary">
            <div class="summary-item">
                <div class="value">{{ total_cases }}</div>
                <div class="label">总用例数</div>
            </div>
            <div class="summary-item">
                <div class="value" style="color: #28a745;">{{ passed_cases }}</div>
                <div class="label">通过数</div>
            </div>
            <div class="summary-item">
                <div class="value" style="color: #dc3545;">{{ failed_cases }}</div>
                <div class="label">失败数</div>
            </div>
            <div class="summary-item">
                <div class="value">{{ pass_rate }}%</div>
                <div class="label">通过率</div>
            </div>
        </div>
        
        <div class="section">
            <h2>测试用例执行结果</h2>
            <table>
                <thead>
                    <tr>
                        <th>用例名称</th>
                        <th>状态</th>
                        <th>耗时 (秒)</th>
                        <th>执行时间</th>
                        <th>错误信息</th>
                    </tr>
                </thead>
                <tbody>
                    {% for result in test_results %}
                    <tr>
                        <td>{{ result.test_case_name }}</td>
                        <td class="status-{{ result.status|lower }}">{{ result.status }}</td>
                        <td>{{ result.duration }}</td>
                        <td>{{ result.timestamp }}</td>
                        <td>{{ result.error_message or '-' }}</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
        
        {% if bugs %}
        <div class="section">
            <h2>缺陷详情 & AI 分析</h2>
            {% for bug in bugs %}
            <div class="bug-card">
                <p><span class="bug-id">【{{ bug.bug_id }}】</span> {{ bug.test_case_name }}</p>
                <p><strong>错误信息：</strong>{{ bug.error_message }}</p>
                <p><strong>截图路径：</strong>{{ bug.screenshot_path }}</p>
                <p><strong>发现时间：</strong>{{ bug.timestamp }}</p>
                
                {% if bug.ai_analysis %}
                <div class="ai-analysis">
                    <h4>🤖 AI 智能分析</h4>
                    {% if bug.ai_analysis.severity %}
                    <p><strong>严重程度：</strong><span class="severity-{{ bug.ai_analysis.severity }}">{{ bug.ai_analysis.severity }}</span></p>
                    {% endif %}
                    {% if bug.ai_analysis.root_cause %}
                    <p><strong>根本原因：</strong>{{ bug.ai_analysis.root_cause }}</p>
                    {% endif %}
                    {% if bug.ai_analysis.reproduction_steps %}
                    <p><strong>复现步骤：</strong></p>
                    <ol>
                        {% for step in bug.ai_analysis.reproduction_steps %}
                        <li>{{ step }}</li>
                        {% endfor %}
                    </ol>
                    {% endif %}
                    {% if bug.ai_analysis.fix_suggestion %}
                    <p><strong>修复建议：</strong>{{ bug.ai_analysis.fix_suggestion }}</p>
                    {% endif %}
                    {% if bug.ai_analysis.affected_module %}
                    <p><strong>影响模块：</strong>{{ bug.ai_analysis.affected_module }}</p>
                    {% endif %}
                </div>
                {% endif %}
            </div>
            {% endfor %}
        </div>
        {% endif %}
    </div>
</body>
</html>
"""
        
        template = Template(html_template)
        html_content = template.render(**report_data)
        
        report_path = self.reports_dir / f"test_report_{timestamp}.html"
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        # 同时生成最新报告（覆盖）
        latest_path = self.reports_dir / "test_report.html"
        with open(latest_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"[HTML REPORT] 已生成：{report_path}")
    
    def _generate_markdown_report(self, report_data: Dict, timestamp: str):
        """生成 Markdown 文档报告"""
        
        md_template = """# {{ title }}

**生成时间：** {{ generate_time }}

## 📊 测试概览

| 指标 | 数值 |
|------|------|
| 总用例数 | {{ total_cases }} |
| 通过数 | {{ passed_cases }} |
| 失败数 | {{ failed_cases }} |
| 通过率 | {{ pass_rate }}% |

## 📋 测试用例执行结果

| 用例名称 | 状态 | 耗时 (秒) | 执行时间 | 错误信息 |
|----------|------|-----------|----------|----------|
{% for result in test_results %}| {{ result.test_case_name }} | {{ result.status }} | {{ result.duration }} | {{ result.timestamp }} | {{ result.error_message or '-' }} |
{% endfor %}

{% if bugs %}
## 🐛 缺陷详情 & AI 分析

{% for bug in bugs %}
### 【{{ bug.bug_id }}】{{ bug.test_case_name }}

- **错误信息：** {{ bug.error_message }}
- **截图路径：** `{{ bug.screenshot_path }}`
- **发现时间：** {{ bug.timestamp }}

{% if bug.ai_analysis %}
#### 🤖 AI 智能分析

{% if bug.ai_analysis.severity %}
- **严重程度：** {{ bug.ai_analysis.severity }}
{% endif %}
{% if bug.ai_analysis.root_cause %}
- **根本原因：** {{ bug.ai_analysis.root_cause }}
{% endif %}
{% if bug.ai_analysis.reproduction_steps %}
- **复现步骤：**
{% for step in bug.ai_analysis.reproduction_steps %}
  {{ loop.index }}. {{ step }}
{% endfor %}
{% endif %}
{% if bug.ai_analysis.fix_suggestion %}
- **修复建议：** {{ bug.ai_analysis.fix_suggestion }}
{% endif %}
{% if bug.ai_analysis.affected_module %}
- **影响模块：** {{ bug.ai_analysis.affected_module }}
{% endif %}
{% endif %}

---

{% endfor %}
{% endif %}

*本报告由 Web AI 自动化测试 Agent 自动生成*
"""
        
        template = Template(md_template)
        md_content = template.render(**report_data)
        
        report_path = self.reports_dir / f"test_report_{timestamp}.md"
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(md_content)
        
        # 同时生成最新报告（覆盖）
        latest_path = self.reports_dir / "test_report.md"
        with open(latest_path, 'w', encoding='utf-8') as f:
            f.write(md_content)
        
        print(f"[MD REPORT] 已生成：{report_path}")


# 便捷函数
def create_agent(headless: bool = True) -> AITestAgent:
    """创建测试 Agent 实例"""
    return AITestAgent(headless=headless)
