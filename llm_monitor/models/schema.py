"""
数据模型定义
"""
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, Boolean, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
from typing import Optional, Dict, Any

Base = declarative_base()


class Vendor(Base):
    """厂商信息表"""
    __tablename__ = "vendors"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False)  # 厂商标识，如 openai
    display_name = Column(String(100), nullable=False)  # 显示名称，如 OpenAI
    pricing_url = Column(String(500))  # 定价页面 URL
    api_base = Column(String(500))  # API 基础 URL
    enabled = Column(Boolean, default=True)  # 是否启用
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关联
    models = relationship("Model", back_populates="vendor")
    price_history = relationship("PriceHistory", back_populates="vendor")
    news = relationship("VendorNews", back_populates="vendor")


class Model(Base):
    """模型信息表"""
    __tablename__ = "models"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    vendor_id = Column(Integer, ForeignKey("vendors.id"), nullable=False)
    model_name = Column(String(200), nullable=False)  # 模型名称，如 gpt-4
    display_name = Column(String(200))  # 显示名称
    context_window = Column(Integer)  # 上下文窗口大小（tokens）
    description = Column(Text)  # 模型描述
    capabilities = Column(JSON)  # 能力标签，如 ["chat", "code", "vision"]
    is_latest = Column(Boolean, default=False)  # 是否最新版本
    release_date = Column(DateTime)  # 发布日期
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关联
    vendor = relationship("Vendor", back_populates="models")
    prices = relationship("CurrentPrice", back_populates="model")


class CurrentPrice(Base):
    """当前价格表"""
    __tablename__ = "current_prices"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    model_id = Column(Integer, ForeignKey("models.id"), nullable=False)
    input_price = Column(Float)  # 输入价格（每 1K tokens，美元）
    output_price = Column(Float)  # 输出价格（每 1K tokens，美元）
    currency = Column(String(10), default="USD")  # 货币单位
    unit = Column(String(50), default="1K tokens")  # 计价单位
    
    # 折扣信息
    discount_rate = Column(Float)  # 折扣率
    free_quota = Column(Float)  # 免费额度
    package_info = Column(JSON)  # 套餐信息
    
    # 场景定价（不同场景可能有不同价格）
    chat_price = Column(JSON)  # 聊天场景
    code_price = Column(JSON)  # 代码场景
    long_text_price = Column(JSON)  # 长文本场景
    multimodal_price = Column(JSON)  # 多模态场景
    
    effective_date = Column(DateTime, default=datetime.utcnow)  # 生效日期
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关联
    model = relationship("Model", back_populates="prices")


class PriceHistory(Base):
    """价格历史表"""
    __tablename__ = "price_history"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    vendor_id = Column(Integer, ForeignKey("vendors.id"), nullable=False)
    model_name = Column(String(200), nullable=False)
    input_price = Column(Float)  # 输入价格
    output_price = Column(Float)  # 输出价格
    currency = Column(String(10))
    change_type = Column(String(50))  # 变化类型：increase/decrease/new
    change_percent = Column(Float)  # 变化百分比
    snapshot_date = Column(DateTime, default=datetime.utcnow)  # 快照日期
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 关联
    vendor = relationship("Vendor", back_populates="price_history")


class VendorNews(Base):
    """厂商动态新闻表"""
    __tablename__ = "vendor_news"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    vendor_id = Column(Integer, ForeignKey("vendors.id"), nullable=False)
    title = Column(String(500), nullable=False)  # 新闻标题
    content = Column(Text)  # 新闻内容
    news_type = Column(String(50))  # 新闻类型：new_version/upgrade/context_window/agent/policy
    url = Column(String(500))  # 新闻链接
    published_date = Column(DateTime)  # 发布日期
    is_notified = Column(Boolean, default=False)  # 是否已通知
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 关联
    vendor = relationship("Vendor", back_populates="news")


class NotificationLog(Base):
    """通知日志表"""
    __tablename__ = "notification_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    notification_type = Column(String(50), nullable=False)  # 通知类型：price_change/new_model/news
    target_id = Column(Integer)  # 目标 ID（价格 ID、新闻 ID 等）
    channel = Column(String(50))  # 通知渠道：email/webhook/dingtalk/wechat
    status = Column(String(20), default="pending")  # 状态：pending/sent/failed
    message = Column(Text)  # 通知内容
    error_message = Column(Text)  # 错误信息
    sent_at = Column(DateTime)  # 发送时间
    created_at = Column(DateTime, default=datetime.utcnow)


# 数据库会话工厂
def init_db(database_url: str = "sqlite:///./llm_monitor.db"):
    """初始化数据库"""
    engine = create_engine(database_url, echo=False)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal, engine
