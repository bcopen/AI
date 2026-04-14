# LLM Monitor - 大模型价格监控系统

监控全球主流大模型厂商的 Token 价格变化和最新动态。

## 功能特性

### ✅ 已实现功能

1. **Token 价格监控**
   - 支持 9 家厂商：OpenAI、Anthropic、Google、字节豆包、阿里通义、智谱、Kimi、DeepSeek、百度文心
   - 实时抓取官方 API 定价页
   - 记录输入/输出单价、折扣、套餐、免费额度
   - 价格变化百分比计算
   - 阈值告警（默认 5%）

2. **模型动态监控**
   - 新版本发布
   - 能力升级
   - 上下文窗口变化
   - Agent 全家桶更新
   - 政策调整

3. **价格对比工具**
   - 按场景自动比价：聊天、代码、长文本、多模态
   - 历史价格曲线（Chart.js 可视化）

4. **推送提醒**
   - 降价/涨价/新模型上线自动通知
   - 支持多渠道：邮件、Webhook、钉钉、企业微信

5. **Web 界面**
   - 价格列表展示
   - 价格对比排名
   - 历史曲线图表
   - 新闻动态
   - 导出报表

6. **数据导出**
   - CSV 格式（适用于 Excel、Numbers）
   - Excel 格式（多工作表，按厂商分类）

## 快速开始

### 安装依赖

```bash
cd llm_monitor
pip install -r requirements.txt
```

### 配置环境变量

创建 `.env` 文件：

```bash
# 通知配置
ENABLE_EMAIL_NOTIFY=false
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your@email.com
SMTP_PASSWORD=your_password
EMAIL_RECIPIENTS=["recipient@example.com"]

ENABLE_WEBHOOK=false
WEBHOOK_URL=https://your-webhook-url.com

ENABLE_DINGTALK=false
DINGTALK_WEBHOOK=https://oapi.dingtalk.com/robot/send?access_token=xxx

ENABLE_WECHAT=false
WECHAT_CORP_ID=your_corp_id
WECHAT_AGENT_ID=1000001
WECHAT_SECRET=your_secret

# 价格变动阈值（百分比）
PRICE_CHANGE_THRESHOLD=5.0

# 检查间隔（秒）
PRICE_CHECK_INTERVAL=3600
NEWS_CHECK_INTERVAL=1800
```

### 运行

#### 命令行模式

```bash
# 运行一次完整采集
python main.py once

# 持续运行（带定时任务）
python main.py run

# 只抓取价格
python main.py prices

# 只抓取新闻
python main.py news

# 价格对比
python main.py compare chat
python main.py compare code
python main.py compare long_text
python main.py compare multimodal

# 查看最近新闻
python main.py news-list
```

#### Web 界面

```bash
# 启动 Web 服务
python web/app.py

# 访问 http://localhost:8000/web
# API 文档：http://localhost:8000/docs
```

### 导出报表

通过 Web 界面或 API 导出：

```bash
# CSV
curl http://localhost:8000/api/export/csv -o prices.csv

# Excel
curl http://localhost:8000/api/export/excel -o prices.xlsx
```

## API 接口

| 接口 | 说明 |
|------|------|
| `GET /api/prices` | 获取当前价格列表 |
| `GET /api/prices?vendor=openai` | 按厂商筛选价格 |
| `GET /api/prices/history/{vendor}/{model}` | 获取价格历史 |
| `GET /api/compare/{scenario}` | 按场景对比价格 |
| `GET /api/news` | 获取新闻动态 |
| `GET /api/vendors` | 获取厂商列表 |
| `GET /api/stats` | 获取统计数据 |
| `GET /api/export/csv` | 导出 CSV |
| `GET /api/export/excel` | 导出 Excel |
| `GET /web` | Web 界面 |

## 项目结构

```
llm_monitor/
├── config/              # 配置文件
│   └── settings.py
├── models/              # 数据模型
│   └── schema.py
├── scrapers/            # 爬虫模块
│   ├── base.py
│   ├── openai.py
│   ├── international.py
│   └── domestic.py
├── services/            # 业务服务
│   ├── price_tracker.py
│   ├── news_monitor.py
│   └── comparison.py
├── notifications/       # 通知服务
│   └── notifier.py
├── web/                 # Web 界面
│   └── app.py
├── main.py              # 主程序入口
├── requirements.txt     # 依赖列表
└── README.md
```

## 扩展更多厂商

1. 在 `scrapers/` 目录下创建新的爬虫类
2. 继承 `BaseScraper` 并实现 `scrape_prices()` 和 `scrape_news()`
3. 在 `config/settings.py` 中添加厂商配置
4. 在 `scrapers/__init__.py` 中注册爬虫

## License

MIT License
