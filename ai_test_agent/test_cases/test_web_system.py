"""
Web 系统功能测试用例示例
演示如何使用 AI Test Agent 编写和执行测试用例
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from ai_test_agent import AITestAgent, create_agent
from playwright.sync_api import Page, expect


def test_login_functionality(page: Page):
    """
    测试用例 1：登录功能测试
    模拟用户登录操作并验证
    """
    # 打开登录页面（假设有一个 /login 路径）
    page.goto("/login")
    
    # 输入用户名
    login_input = page.locator('input[name="username"]')
    login_input.fill("test_user")
    
    # 输入密码
    password_input = page.locator('input[name="password"]')
    password_input.fill("test_password")
    
    # 点击登录按钮
    login_button = page.locator('button[type="submit"]')
    login_button.click()
    
    # 等待跳转并断言
    page.wait_for_url("**/dashboard")
    expect(page).to_have_url("**/dashboard")
    
    # 验证欢迎信息
    welcome_text = page.locator(".welcome-message")
    expect(welcome_text).to_be_visible()


def test_navigation_menu(page: Page):
    """
    测试用例 2：导航菜单测试
    验证主导航菜单的各项功能
    """
    # 打开首页
    page.goto("/")
    
    # 点击导航菜单项
    nav_item = page.locator('nav a[href="/products"]')
    nav_item.click()
    
    # 验证页面跳转
    page.wait_for_url("**/products")
    expect(page).to_have_url("**/products")
    
    # 验证页面标题
    page_title = page.locator("h1")
    expect(page_title).to_contain_text("Products")


def test_search_function(page: Page):
    """
    测试用例 3：搜索功能测试
    验证搜索框的输入和结果展示
    """
    # 打开首页
    page.goto("/")
    
    # 输入搜索关键词
    search_input = page.locator('input[placeholder="Search..."]')
    search_input.fill("test product")
    
    # 点击搜索按钮
    search_button = page.locator('button.search-btn')
    search_button.click()
    
    # 等待搜索结果
    page.wait_for_selector(".search-results")
    
    # 验证有搜索结果
    results = page.locator(".search-results .result-item")
    expect(results).not_to_have_count(0)


def test_form_submission(page: Page):
    """
    测试用例 4：表单提交测试
    验证表单填写和提交流程
    """
    # 打开表单页面
    page.goto("/contact")
    
    # 填写表单
    name_input = page.locator('input[name="name"]')
    name_input.fill("John Doe")
    
    email_input = page.locator('input[name="email"]')
    email_input.fill("john@example.com")
    
    message_input = page.locator('textarea[name="message"]')
    message_input.fill("This is a test message")
    
    # 提交表单
    submit_button = page.locator('button[type="submit"]')
    submit_button.click()
    
    # 验证提交成功提示
    success_message = page.locator(".success-message")
    expect(success_message).to_be_visible()
    expect(success_message).to_contain_text("Thank you")


# ==================== 主执行入口 ====================

if __name__ == "__main__":
    # 创建测试 Agent 实例
    # headless=False 表示可视化模式，可以看到浏览器操作过程
    # headless=True 表示无头模式，后台静默运行
    agent = create_agent(headless=True)
    
    try:
        # 启动浏览器并打开被测系统
        agent.open_web_system()
        
        # 执行测试用例（使用 lambda 匿名函数方式）
        
        # 用例 1：简单的页面访问测试
        agent.execute_test_case(
            "访问首页并验证标题",
            lambda page: (
                page.goto("/"),
                expect(page).to_have_title(".*Welcome.*")
            )[-1]  # 取最后一个表达式的值
        )
        
        # 用例 2：使用自定义函数执行复杂流程
        agent.execute_test_case(
            "登录功能测试",
            lambda page: test_login_functionality(page) if False else None  # 跳过实际执行，仅演示
        )
        
        # 用例 3：直接编写操作步骤
        def simple_click_test(page: Page):
            page.goto("/")
            button = page.locator('button.cta-button')
            button.click()
            page.wait_for_timeout(1000)
        
        agent.execute_test_case(
            "CTA 按钮点击测试",
            simple_click_test
        )
        
        # 用例 4：模拟一个会失败的测试（演示错误捕获）
        def failing_test(page: Page):
            page.goto("/")
            # 故意查找不存在的元素，触发失败
            non_existent = page.locator('#this-element-does-not-exist')
            non_existent.click(timeout=2000)
        
        agent.execute_test_case(
            "预期失败的测试用例",
            failing_test
        )
        
        # 生成测试报告
        print("\n" + "="*50)
        print("正在生成测试报告...")
        agent.generate_test_report(output_format="all")
        print("="*50)
        
    finally:
        # 关闭浏览器
        agent.close_browser()
    
    print("\n✅ 测试执行完成！")
    print(f"📄 HTML 报告：{agent.reports_dir}/test_report.html")
    print(f"📄 Markdown 报告：{agent.reports_dir}/test_report.md")
    print(f"📸 截图目录：{agent.screenshots_dir}")
