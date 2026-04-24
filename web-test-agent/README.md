# Web 自动化测试 Agent

一个完整的 Web 自动化测试 Agent，支持可视化配置界面，可以像人工一样执行测试操作。基于 Playwright 构建，提供 8 种测试动作，自动生成测试报告。

## ✨ 核心功能

- 🌐 **可视化配置界面**：Web 界面输入 URL、配置测试步骤
- 🎭 **8 种测试动作**：navigate、click、input、wait、waitForSelector、screenshot、assert、login
- 📷 **自动截图**：每个步骤自动保存截图
- 📊 **HTML 测试报告**：生成美观的测试报告，包含通过率、步骤详情
- 📝 **完整日志系统**：执行日志、错误日志、性能日志、系统日志

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
playwright install chromium
```

### 2. 启动应用

```bash
python app.py
```

### 3. 访问界面

打开浏览器访问 `http://localhost:5000`

## 📋 测试动作说明

| 动作 | 说明 | 参数 |
|------|------|------|
| 🌐 navigate | 导航到指定 URL | url |
| 🖱️ click | 点击元素 | selector |
| ⌨️ input | 输入文本 | selector, value |
| ⏳ wait | 等待指定时间 | timeout (ms) |
| 🎯 waitForSelector | 等待元素出现 | selector, timeout |
| 📷 screenshot | 截取屏幕 | - |
| ✅ assert | 断言文本 | selector, expected |
| 🔐 login | 登录操作 | usernameSelector, passwordSelector, submitSelector, username, password |

## 📁 项目结构

```
web-test-agent/
├── app.py              # 主应用
├── templates/
│   └── index.html      # 可视化配置界面
├── static/
│   ├── css/
│   │   └── style.css   # 样式文件
│   └── js/
│       └── app.js      # 前端逻辑
├── reports/            # 测试报告目录
├── logs/               # 日志目录
└── screenshots/        # 截图目录
```

## 💡 使用示例

1. 在界面中添加测试步骤
2. 选择动作类型（如 navigate）
3. 填写相应参数（如 URL）
4. 继续添加其他步骤（click、input、assert 等）
5. 点击"运行测试"按钮
6. 查看生成的测试报告和截图

## 🛠️ 技术栈

- **后端**: Python + Flask
- **自动化**: Playwright
- **前端**: HTML/CSS/JavaScript
- **报告**: 自定义 HTML 模板

## 📄 License

MIT
