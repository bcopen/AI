"""
配置文件
"""
from pydantic_settings import BaseSettings
from typing import List, Optional
from datetime import timedelta


class Settings(BaseSettings):
    """应用配置"""
    
    # 应用配置
    APP_NAME: str = "LLM Monitor"
    DEBUG: bool = True
    
    # 数据库配置
    DATABASE_URL: str = "sqlite:///./llm_monitor.db"
    
    # 爬虫配置
    REQUEST_TIMEOUT: int = 30
    USER_AGENT: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    REQUEST_DELAY: float = 1.0  # 请求间隔（秒）
    
    # 监控厂商列表
    MONITORED_VENDORS: List[str] = [
        "openai",
        "anthropic",
        "google",
        "doubao",
        "aliyun",
        "zhipu",
        "kimi",
        "deepseek",
        "baidu"
    ]
    
    # 定时任务配置
    PRICE_CHECK_INTERVAL: int = 3600  # 价格检查间隔（秒），默认 1 小时
    NEWS_CHECK_INTERVAL: int = 1800   # 新闻检查间隔（秒），默认 30 分钟
    
    # 通知配置
    ENABLE_EMAIL_NOTIFY: bool = False
    SMTP_SERVER: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    EMAIL_RECIPIENTS: List[str] = []
    
    ENABLE_WEBHOOK: bool = False
    WEBHOOK_URL: str = ""
    
    ENABLE_DINGTALK: bool = False
    DINGTALK_WEBHOOK: str = ""
    
    ENABLE_WECHAT: bool = False
    WECHAT_CORP_ID: str = ""
    WECHAT_AGENT_ID: str = ""
    WECHAT_SECRET: str = ""
    
    # 价格变动阈值（百分比），超过此阈值才发送通知
    PRICE_CHANGE_THRESHOLD: float = 5.0
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# 厂商定价页面 URL 配置
VENDOR_CONFIGS = {
    "openai": {
        "name": "OpenAI",
        "pricing_url": "https://openai.com/api/pricing/",
        "api_base": "https://api.openai.com/v1",
        "enabled": True
    },
    "anthropic": {
        "name": "Anthropic",
        "pricing_url": "https://www.anthropic.com/pricing",
        "api_base": "https://api.anthropic.com/v1",
        "enabled": True
    },
    "google": {
        "name": "Google",
        "pricing_url": "https://cloud.google.com/vertex-ai/pricing",
        "api_base": "https://us-central1-aiplatform.googleapis.com/v1",
        "enabled": True
    },
    "doubao": {
        "name": "字节豆包",
        "pricing_url": "https://www.volcengine.com/product/doubao",
        "api_base": "https://ark.cn-beijing.volces.com/api/v3",
        "enabled": True
    },
    "aliyun": {
        "name": "阿里通义",
        "pricing_url": "https://help.aliyun.com/price/tongyi",
        "api_base": "https://dashscope.aliyuncs.com/api/v1",
        "enabled": True
    },
    "zhipu": {
        "name": "智谱",
        "pricing_url": "https://open.bigmodel.cn/pricing",
        "api_base": "https://open.bigmodel.cn/api/paas/v4",
        "enabled": True
    },
    "kimi": {
        "name": "Kimi",
        "pricing_url": "https://platform.moonshot.cn/pricing",
        "api_base": "https://api.moonshot.cn/v1",
        "enabled": True
    },
    "deepseek": {
        "name": "DeepSeek",
        "pricing_url": "https://platform.deepseek.com/pricing",
        "api_base": "https://api.deepseek.com/v1",
        "enabled": True
    },
    "baidu": {
        "name": "百度文心",
        "pricing_url": "https://cloud.baidu.com/price/wenxinworkshop",
        "api_base": "https://aip.baidubce.com/rpc/2.0/ai_custom/v1",
        "enabled": True
    }
}

settings = Settings()
