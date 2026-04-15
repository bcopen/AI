# Web 自动化测试 Agent

一个功能完整的 Web 自动化测试平台，支持项目管理、测试用例管理、录制测试、测试报告和定时任务。

## 功能特性

### 1. 项目管理
- 创建、编辑、删除项目
- 每个项目包含名称、URL 和描述
- 项目列表展示所有已创建的项目

### 2. 测试用例管理
- **手动添加**：手动创建测试用例
- **AI 生成（自然语言）**：根据自然语言描述自动生成测试用例
- **AI 生成（MCP 元素定位）**：通过 Playwright 自动识别页面元素生成测试用例
- 测试用例列表支持编辑、删除、执行
- 支持批量执行选中的测试用例

### 3. 录制测试
- 输入起始 URL 开始录制
- 自动记录鼠标点击、输入等操作
- 停止录制后显示操作步骤
- 可将录制的操作保存为测试用例

### 4. 测试报告
- 测试执行完成后自动生成报告
- 报告命名：项目名称 + 日期
- 包含通过率、失败数、执行时间等统计信息
- 详细的测试结果查看

### 5. 定时任务设置
- 创建自动化测试任务
- 设置 Cron 表达式定义执行周期
- 定时执行测试并生成报告

## 技术栈

- **后端**: Node.js + Express
- **数据库**: SQLite3
- **浏览器自动化**: Playwright
- **定时任务**: node-cron
- **前端**: 原生 HTML/CSS/JavaScript

## 安装与运行

### 安装依赖
```bash
npm install
```

### 启动服务
```bash
npm start
```

服务将在 http://localhost:3000 启动

## API 接口

### 项目
- `GET /api/projects` - 获取所有项目
- `GET /api/projects/:id` - 获取单个项目
- `POST /api/projects` - 创建项目
- `PUT /api/projects/:id` - 更新项目
- `DELETE /api/projects/:id` - 删除项目

### 测试用例
- `GET /api/projects/:projectId/test-cases` - 获取项目的测试用例
- `POST /api/test-cases` - 创建测试用例
- `PUT /api/test-cases/:id` - 更新测试用例
- `DELETE /api/test-cases/:id` - 删除测试用例
- `POST /api/test-cases/generate-ai` - AI 生成测试用例（自然语言）
- `POST /api/test-cases/generate-mcp` - AI 生成测试用例（MCP 元素定位）
- `POST /api/test-cases/:id/execute` - 执行单个测试用例
- `POST /api/test-cases/batch-execute` - 批量执行测试用例

### 录制
- `POST /api/recording/start` - 开始录制
- `POST /api/recording/stop` - 停止录制
- `GET /api/recording/status` - 获取录制状态
- `POST /api/recording/generate-test-case` - 从录制生成测试用例

### 报告
- `GET /api/reports` - 获取所有报告
- `GET /api/reports/:id` - 获取报告详情
- `GET /api/projects/:projectId/reports` - 获取项目相关报告

### 定时任务
- `GET /api/scheduled-tasks` - 获取所有定时任务
- `POST /api/scheduled-tasks` - 创建定时任务
- `PUT /api/scheduled-tasks/:id` - 更新定时任务
- `DELETE /api/scheduled-tasks/:id` - 删除定时任务

## Cron 表达式示例

- `0 9 * * *` - 每天早上 9 点
- `0 */2 * * *` - 每 2 小时
- `0 9 * * 1-5` - 工作日每天 9 点
- `*/5 * * * *` - 每 5 分钟

## 注意事项

1. 首次运行需要安装 Playwright 浏览器：
   ```bash
   npx playwright install chromium
   ```

2. 如果磁盘空间不足，可以设置外部存储路径：
   ```bash
   PLAYWRIGHT_BROWSERS_PATH=/path/to/storage npx playwright install chromium
   ```

3. 数据库文件 `test_automation.db` 会自动创建在项目根目录

## 许可证

ISC
