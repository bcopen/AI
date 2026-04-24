"""
Web 自动化测试 Agent - 主应用
基于 Playwright 构建，支持可视化配置界面
"""

import os
import json
import time
import logging
from datetime import datetime
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_from_directory
from playwright.sync_api import sync_playwright

app = Flask(__name__)

# 配置目录
BASE_DIR = Path(__file__).parent
REPORTS_DIR = BASE_DIR / "reports"
LOGS_DIR = BASE_DIR / "logs"
SCREENSHOTS_DIR = BASE_DIR / "screenshots"

# 确保目录存在
for directory in [REPORTS_DIR, LOGS_DIR, SCREENSHOTS_DIR]:
    directory.mkdir(exist_ok=True)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOGS_DIR / f"test_{datetime.now().strftime('%Y%m%d')}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class TestAgent:
    """Web 自动化测试 Agent"""
    
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.page = None
        self.results = []
        self.screenshots = []
        
    def start(self):
        """启动浏览器"""
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=False)
        self.page = self.browser.new_page()
        logger.info("浏览器启动成功")
        
    def stop(self):
        """关闭浏览器"""
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
        logger.info("浏览器已关闭")
        
    def take_screenshot(self, step_name):
        """截取屏幕截图"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{step_name}.png"
        filepath = SCREENSHOTS_DIR / filename
        self.page.screenshot(path=str(filepath))
        self.screenshots.append(filename)
        logger.info(f"截图保存：{filename}")
        return filename
        
    def execute_step(self, step):
        """执行单个测试步骤"""
        action = step.get("action")
        params = step.get("params", {})
        result = {"action": action, "status": "success", "timestamp": datetime.now().isoformat()}
        
        try:
            if action == "navigate":
                url = params.get("url")
                self.page.goto(url)
                result["message"] = f"导航到 {url}"
                
            elif action == "click":
                selector = params.get("selector")
                self.page.click(selector)
                result["message"] = f"点击 {selector}"
                
            elif action == "input":
                selector = params.get("selector")
                value = params.get("value")
                self.page.fill(selector, value)
                result["message"] = f"输入 {value} 到 {selector}"
                
            elif action == "wait":
                timeout = params.get("timeout", 1000)
                time.sleep(timeout / 1000)
                result["message"] = f"等待 {timeout}ms"
                
            elif action == "waitForSelector":
                selector = params.get("selector")
                timeout = params.get("timeout", 5000)
                self.page.wait_for_selector(selector, timeout=timeout)
                result["message"] = f"等待元素 {selector}"
                
            elif action == "screenshot":
                filename = self.take_screenshot(step.get("name", "step"))
                result["message"] = f"截图 {filename}"
                result["screenshot"] = filename
                
            elif action == "assert":
                selector = params.get("selector")
                expected = params.get("expected")
                element = self.page.query_selector(selector)
                actual = element.inner_text() if element else ""
                if expected in actual:
                    result["message"] = f"断言通过：{selector} 包含 {expected}"
                else:
                    result["status"] = "failed"
                    result["message"] = f"断言失败：期望 '{expected}'，实际 '{actual}'"
                    
            elif action == "login":
                username_selector = params.get("usernameSelector")
                password_selector = params.get("passwordSelector")
                submit_selector = params.get("submitSelector")
                username = params.get("username")
                password = params.get("password")
                self.page.fill(username_selector, username)
                self.page.fill(password_selector, password)
                self.page.click(submit_selector)
                result["message"] = f"登录操作完成"
                
            else:
                result["status"] = "failed"
                result["message"] = f"未知动作：{action}"
                
        except Exception as e:
            result["status"] = "error"
            result["message"] = str(e)
            logger.error(f"步骤执行错误：{e}")
            
        # 每个步骤后自动截图
        if action not in ["screenshot"]:
            screenshot = self.take_screenshot(f"{action}_{int(time.time())}")
            result["screenshot"] = screenshot
            
        self.results.append(result)
        return result
        
    def run_test(self, test_config):
        """运行完整测试"""
        try:
            self.start()
            steps = test_config.get("steps", [])
            
            for i, step in enumerate(steps):
                logger.info(f"执行步骤 {i+1}/{len(steps)}: {step.get('action')}")
                self.execute_step(step)
                
        finally:
            self.stop()
            
        return self.results
        
    def generate_report(self, test_name="Test"):
        """生成 HTML 测试报告"""
        total = len(self.results)
        passed = sum(1 for r in self.results if r["status"] == "success")
        failed = sum(1 for r in self.results if r["status"] in ["failed", "error"])
        pass_rate = (passed / total * 100) if total > 0 else 0
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_filename = f"{test_name}_{timestamp}.html"
        report_path = REPORTS_DIR / report_filename
        
        html_content = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>测试报告 - {test_name}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        h1 {{ color: #333; border-bottom: 2px solid #4CAF50; padding-bottom: 10px; }}
        .summary {{ display: flex; gap: 20px; margin: 20px 0; }}
        .stat {{ padding: 15px 25px; border-radius: 8px; color: white; }}
        .stat-total {{ background: #2196F3; }}
        .stat-passed {{ background: #4CAF50; }}
        .stat-failed {{ background: #f44336; }}
        .stat-rate {{ background: #FF9800; }}
        .step {{ border: 1px solid #ddd; margin: 10px 0; padding: 15px; border-radius: 4px; }}
        .step.success {{ border-left: 4px solid #4CAF50; }}
        .step.failed {{ border-left: 4px solid #f44336; }}
        .step.error {{ border-left: 4px solid #ff9800; }}
        .step-header {{ display: flex; justify-content: space-between; align-items: center; }}
        .status {{ padding: 4px 12px; border-radius: 4px; font-size: 12px; font-weight: bold; }}
        .status.success {{ background: #e8f5e9; color: #4CAF50; }}
        .status.failed {{ background: #ffebee; color: #f44336; }}
        .status.error {{ background: #fff3e0; color: #ff9800; }}
        .screenshot {{ margin-top: 10px; }}
        .screenshot img {{ max-width: 100%; height: auto; border: 1px solid #ddd; border-radius: 4px; }}
        .timestamp {{ color: #666; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 测试报告 - {test_name}</h1>
        <p class="timestamp">生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        
        <div class="summary">
            <div class="stat stat-total">总步骤：{total}</div>
            <div class="stat stat-passed">通过：{passed}</div>
            <div class="stat stat-failed">失败：{failed}</div>
            <div class="stat stat-rate">通过率：{pass_rate:.1f}%</div>
        </div>
        
        <h2>测试步骤详情</h2>
"""
        
        for i, result in enumerate(self.results, 1):
            status_class = result["status"]
            status_text = "✓ 通过" if result["status"] == "success" else ("✗ 失败" if result["status"] == "failed" else "⚠ 错误")
            screenshot_html = ""
            if result.get("screenshot"):
                screenshot_html = f'<div class="screenshot"><img src="../screenshots/{result["screenshot"]}" alt="Screenshot"></div>'
                
            html_content += f"""
        <div class="step {status_class}">
            <div class="step-header">
                <strong>步骤 {i}: {result["action"]}</strong>
                <span class="status {status_class}">{status_text}</span>
            </div>
            <p>{result["message"]}</p>
            <p class="timestamp">时间：{result["timestamp"]}</p>
            {screenshot_html}
        </div>
"""
        
        html_content += """
    </div>
</body>
</html>
"""
        
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(html_content)
            
        logger.info(f"测试报告已生成：{report_path}")
        return str(report_path), {
            "total": total,
            "passed": passed,
            "failed": failed,
            "pass_rate": pass_rate
        }


# 全局测试代理实例
agent = TestAgent()


@app.route("/")
def index():
    """首页 - 可视化配置界面"""
    return render_template("index.html")


@app.route("/api/run", methods=["POST"])
def run_test():
    """运行测试"""
    try:
        data = request.json
        test_config = data.get("config", {})
        test_name = data.get("name", "Test")
        
        logger.info(f"开始执行测试：{test_name}")
        results = agent.run_test(test_config)
        report_path, summary = agent.generate_report(test_name)
        
        return jsonify({
            "success": True,
            "results": results,
            "report": report_path,
            "summary": summary
        })
        
    except Exception as e:
        logger.error(f"测试执行失败：{e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/reports/<path:filename>")
def serve_report(filename):
    """提供测试报告"""
    return send_from_directory(REPORTS_DIR, filename)


@app.route("/screenshots/<path:filename>")
def serve_screenshot(filename):
    """提供截图"""
    return send_from_directory(SCREENSHOTS_DIR, filename)


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
