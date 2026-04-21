# Playwright Recorder & Player

基于 Playwright 的 Web 操作录制与回放系统，支持生产环境使用。

## 功能特性

- **事件捕获**: click, input, keydown, scroll, change, navigation
- **稳定选择器生成**: data-testid → id → aria-label → role → tag.class → nth-child
- **智能优化**: 
  - scroll 事件合并（记录最终坐标）
  - input 高频节流（100ms 采样）
  - 密码/敏感输入自动脱敏
- **回放引擎**:
  - 智能同步机制（waitForSelector + networkidle）
  - 重试机制（最大 2 次，指数退避）
  - iframe 支持（保留 framePath）
  - 可选每步截图
- **工程化**: ESM 模块化、JSDoc 类型注释、严格模式

## 快速开始

### 安装依赖

```bash
npm install
```

### 安装 Playwright 浏览器

```bash
npx playwright install chromium
```

### 录制操作

```bash
# 基本用法
node src/index.js record https://example.com

# 指定输出文件
node src/index.js record https://example.com my-recording.json

# 无头模式
node src/index.js record https://example.com --headless
```

**退出录制**: 在终端按 `Enter` 键结束录制，生成 `recording.json`

### 回放操作

```bash
# 基本用法
node src/index.js play recording.json

# 开启截图
node src/index.js play recording.json --screenshots

# 无头模式
node src/index.js play recording.json --headless
```

## CLI 命令

| 命令 | 说明 |
|------|------|
| `record <url> [output]` | 录制指定 URL 的页面操作 |
| `play <file>` | 回放录制的 JSON 文件 |

### 选项

| 选项 | 说明 |
|------|------|
| `--help, -h` | 显示帮助信息 |
| `--headless` | 无头模式运行 |
| `--screenshots` | 回放时每步截图（保存到 ./screenshots） |
| `--no-verbose` | 关闭详细日志 |

## 录制数据格式

```json
[
  {
    "type": "click",
    "selector": "[data-testid=\"submit-btn\"]",
    "x": 150,
    "y": 300,
    "timestamp": 1704067200000
  },
  {
    "type": "input",
    "selector": "#username",
    "value": "user@example.com",
    "timestamp": 1704067201000
  },
  {
    "type": "keydown",
    "selector": "#password",
    "value": "Enter",
    "timestamp": 1704067202000
  },
  {
    "type": "scroll",
    "selector": ":root",
    "x": 0,
    "y": 500,
    "timestamp": 1704067203000
  }
]
```

### 事件类型

| 类型 | 说明 | 属性 |
|------|------|------|
| `click` | 点击事件 | selector, x, y, framePath |
| `input` | 输入事件 | selector, value, framePath |
| `change` | 变更事件 | selector, value, framePath |
| `keydown` | 按键事件 | selector, value (键名), framePath |
| `scroll` | 滚动事件 | selector, x, y, framePath |
| `navigation` | 导航事件 | selector, value (URL) |

## 典型测试场景

### 场景 1: 表单提交

```bash
# 1. 录制表单填写和提交
node src/index.js record https://httpbin.org/forms/post

# 执行操作:
# - 点击 custname 输入框
# - 输入客户姓名
# - 选择 size 下拉框
# - 勾选 topping 复选框
# - 点击 Submit 按钮
# - 按 Enter 结束录制

# 2. 回放
node src/index.js play recording.json --screenshots
```

**注意事项**:
- 密码字段会自动脱敏为 `***`
- 邮箱地址会脱敏处理
- 确保表单元素有稳定的选择器（id/name/data-testid）

### 场景 2: 动态列表滚动

```bash
# 1. 录制滚动操作
node src/index.js record https://demo.playwright.dev/todomvc

# 执行操作:
# - 添加多个 todo 项
# - 向下滚动列表
# - 删除某一项
# - 按 Enter 结束

# 2. 回放
node src/index.js play recording.json
```

**优化机制**:
- scroll 事件自动合并，只记录最终位置
- 避免高频滚动导致回放卡顿
- 滚动后等待网络空闲

### 场景 3: iframe 内点击

```bash
# 1. 录制含 iframe 的页面
node src/index.js record https://www.w3schools.com/tags/tryit.asp?filename=tryhtml_button_test

# 执行操作:
# - 在 iframe 内点击按钮
# - 切换下拉框选项
# - 按 Enter 结束

# 2. 回放（自动识别 iframe）
node src/index.js play recording.json
```

**iframe 支持**:
- 自动检测并记录 framePath
- 回放时穿透到目标 frame
- 跨域 iframe 有限制（无法访问内容）

## 项目结构

```
/workspace
├── package.json           # 依赖配置
├── src/
│   ├── index.js          # CLI 入口
│   ├── recorder.js       # 录制模块（注入脚本）
│   ├── player.js         # 回放模块（执行引擎）
│   ├── selector.js       # 选择器生成算法
│   └── utils.js          # 工具函数
└── screenshots/          # 截图输出目录（可选）
```

## API 参考

### Recorder

```javascript
import { generateInjectionScript, extractRecordedEvents } from './recorder.js';

// 生成注入脚本
const script = generateInjectionScript({
  inputThrottleMs: 100,
  scrollDebounceMs: 200,
  sanitizeSensitive: true
});

// 注入到页面
await page.evaluate(script);

// 提取事件
const events = await extractRecordedEvents(page);
```

### Player

```javascript
import { Player } from './player.js';

const player = new Player(page, {
  timeout: 5000,
  networkIdleTimeout: 3000,
  maxRetries: 2,
  screenshots: true,
  verbose: true
});

const result = await player.play(events);
console.log(result.success ? 'SUCCESS' : 'FAILED');
```

## 已知限制

1. **Shadow DOM**: 部分 Shadow DOM 场景可能无法正确生成选择器
2. **跨域 iframe**: 无法访问跨域 iframe 内部内容
3. **Canvas/SVG**: Canvas 点击坐标可能因分辨率变化失效
4. **动态内容**: 完全动态生成的 ID/class 可能导致选择器失效
5. **拖拽事件**: 暂未支持 drag/drop 复杂手势

## 最佳实践

### 提高录制稳定性

1. **添加 data-testid**: 为关键元素添加稳定标识
   ```html
   <button data-testid="submit-btn">Submit</button>
   ```

2. **避免动态类名**: 不要依赖框架生成的随机类名

3. **使用语义化 HTML**: 优先使用 button/a 等语义标签

### 调试技巧

1. **开启详细日志**: 默认开启，查看每步执行详情
2. **截图对比**: 使用 `--screenshots` 定位失败步骤
3. **慢速回放**: 修改 player.js 中的 delay 参数

## 许可证

MIT
