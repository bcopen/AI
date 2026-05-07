# Web AI 自动化测试 Agent

本项目构建 **Web 系统 AI 自动化测试 Agent**，基于 Python + Playwright + AI 大模型实现，可全自动操控浏览器执行 Web 业务功能测试、自动捕获页面异常、保存错误截图、智能分析缺陷，测试结束后自动生成 HTML 可视化报告 + Markdown 文档报告。

## 🚀 核心能力

- ✅ 全自动启动浏览器，模拟真人操作 Web 系统（输入、点击、跳转、断言校验）
- ✅ 批量执行自定义功能测试用例，支持用例自由扩展
- ✅ 测试失败自动全屏截图、记录错误日志、生成唯一 Bug 编号
- ✅ 接入 AI 大模型，智能分析 Bug 成因、复现步骤、修复建议
- ✅ 自动产出双格式测试报告：HTML 精美可视化报告 + Markdown 标准文档报告
- ✅ 支持无头 / 可视化浏览器模式切换，兼容 Chrome 主流内核
- ✅ 模块化架构，可扩展接口测试、数据库校验、定时任务、消息推送等

## 🛠️ 技术栈

| 组件 | 技术 |
|------|------|
| 编程语言 | Python 3.8+ |
| Web 自动化 | Playwright |
| AI 能力 | OpenAI 兼容大模型（GPT / 国产大模型均可适配） |
| 报告渲染 | Jinja2 |
| 环境配置 | python-dotenv |

## 📁 项目结构

```
ai_test_agent/
├── .env                  # 环境配置：被测地址、AI 密钥、代理
├── requirements.txt      # 依赖包清单
├── ai_test_agent.py      # AI 测试 Agent 核心主类
├── test_cases/           # 自定义业务测试用例目录
│   └── test_web_system.py
├── reports/              # 自动生成测试报告存放目录
└── screenshots/          # 测试失败自动截图存放目录
```

## 🚀 快速开始

### 1. 安装依赖

```bash
cd ai_test_agent
pip install -r requirements.txt
```

### 2. 安装 Playwright 浏览器驱动

```bash
playwright install
```

### 3. 配置环境变量

编辑 `.env` 文件：

```env
# 被测 Web 系统地址
TEST_WEB_URL=http://localhost:8080

# AI 大模型配置（兼容 OpenAI 格式接口）
OPENAI_API_KEY=你的大模型 API 密钥
OPENAI_BASE_URL=https://api.openai.com/v1

# 浏览器模式：headless（无头模式）或 false（可视化模式）
BROWSER_HEADLESS=true

# 测试报告配置
REPORT_TITLE=Web AI 自动化测试报告
```

### 4. 运行测试

```bash
python test_cases/test_web_system.py
```

## 📝 测试用例编写规范

在 `test_cases` 目录新增/编写业务用例，支持两种写法：

### 方式一：Lambda 匿名函数（简单场景）

```python
agent.execute_test_case(
    "访问首页并验证标题",
    lambda page: (
        page.goto("/"),
        expect(page).to_have_title(".*Welcome.*")
    )[-1]
)
```

### 方式二：自定义函数（复杂流程）

```python
def test_login(page: Page):
    page.goto("/login")
    page.locator('input[name="username"]').fill("test_user")
    page.locator('input[name="password"]').fill("password123")
    page.locator('button[type="submit"]').click()
    expect(page).to_have_url("**/dashboard")

agent.execute_test_case("登录功能测试", test_login)
```

### 内置封装方法

| 方法 | 说明 |
|------|------|
| `execute_test_case(名称，操作函数)` | 执行单条测试用例 |
| `open_web_system(url)` | 打开被测首页 |
| `generate_test_report(format)` | 生成测试报告 |
| `start_browser()` | 启动浏览器 |
| `close_browser()` | 关闭浏览器 |

## 📊 输出产物

运行完成后自动生成：

| 文件/目录 | 说明 |
|-----------|------|
| `reports/test_report.html` | 可视化 HTML 测试报告 |
| `reports/test_report.md` | Markdown 测试报告 |
| `screenshots/` | 所有失败用例的全屏截图 |

## 🤖 AI 智能分析

当测试用例失败时，Agent 会自动：

1. 生成唯一 Bug ID（如 `BUG-A1B2C3D4`）
2. 保存全屏截图
3. 调用 AI 大模型分析：
   - 问题根本原因
   - 复现步骤
   - 修复建议
   - 严重程度评估
   - 受影响模块

## 🔧 可扩展功能

可在现有 Agent 基础上快速迭代：

- [ ] 接入 Excel/JSON 数据驱动测试
- [ ] 增加接口自动化、前后端联合校验
- [ ] 新增数据库结果校验
- [ ] 接入钉钉/企业微信，自动推送报告
- [ ] 增加定时任务，每日凌晨自动回归
- [ ] 对接 Jira/禅道，自动创建缺陷工单
- [ ] 增加测试过程视频录制

## 🎯 适配定制

只需提供以下 3 项信息，即可快速适配任意 Web 系统：

1. **被测 Web 系统访问地址**、登录账号密码
2. **需要测试的核心业务功能清单**
3. **报告交付要求**（HTML/Markdown/PDF、是否需要消息推送）

## 📄 License

MIT License

---

*本报告由 Web AI 自动化测试 Agent 自动生成*
