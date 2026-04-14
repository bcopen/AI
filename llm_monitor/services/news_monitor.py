"""
新闻监控服务
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
from loguru import logger
from sqlalchemy.orm import Session

from models.schema import Vendor, VendorNews
from config.settings import VENDOR_CONFIGS


class NewsMonitor:
    """新闻监控服务"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
    
    def get_or_create_vendor(self, vendor_name: str) -> Optional[Vendor]:
        """获取或创建厂商记录"""
        vendor_config = VENDOR_CONFIGS.get(vendor_name)
        if not vendor_config:
            return None
        
        vendor = self.db.query(Vendor).filter(Vendor.name == vendor_name).first()
        
        if not vendor:
            vendor = Vendor(
                name=vendor_name,
                display_name=vendor_config["name"],
                pricing_url=vendor_config["pricing_url"],
                api_base=vendor_config["api_base"],
                enabled=vendor_config["enabled"]
            )
            self.db.add(vendor)
            self.db.commit()
            self.db.refresh(vendor)
        
        return vendor
    
    def add_news(self, vendor: Vendor, news_data: Dict[str, Any]) -> Optional[VendorNews]:
        """添加新闻记录"""
        # 检查是否已存在（通过标题判断）
        existing = self.db.query(VendorNews).filter(
            VendorNews.vendor_id == vendor.id,
            VendorNews.title == news_data["title"]
        ).first()
        
        if existing:
            logger.debug(f"News already exists: {news_data['title']}")
            return None
        
        news = VendorNews(
            vendor_id=vendor.id,
            title=news_data["title"],
            content=news_data.get("content", ""),
            news_type=news_data.get("news_type", "general"),
            url=news_data.get("url"),
            published_date=datetime.fromisoformat(news_data["published_date"]) if news_data.get("published_date") else datetime.utcnow(),
            is_notified=False
        )
        
        self.db.add(news)
        self.db.commit()
        self.db.refresh(news)
        
        logger.info(f"Added news for {vendor.name}: {news.title}")
        return news
    
    def get_unnotified_news(self, limit: int = 50) -> List[Dict[str, Any]]:
        """获取未通知的新闻"""
        news_list = self.db.query(VendorNews).filter(
            VendorNews.is_notified == False
        ).order_by(VendorNews.created_at.desc()).limit(limit).all()
        
        results = []
        for news in news_list:
            results.append({
                "id": news.id,
                "vendor_name": news.vendor.name,
                "vendor_display_name": news.vendor.display_name,
                "title": news.title,
                "content": news.content,
                "news_type": news.news_type,
                "url": news.url,
                "published_date": news.published_date.isoformat() if news.published_date else None,
                "created_at": news.created_at.isoformat()
            })
        
        return results
    
    def mark_as_notified(self, news_id: int):
        """标记新闻为已通知"""
        news = self.db.query(VendorNews).filter(VendorNews.id == news_id).first()
        if news:
            news.is_notified = True
            self.db.commit()
            logger.debug(f"Marked news {news_id} as notified")
    
    def get_recent_news(
        self,
        vendor_name: Optional[str] = None,
        news_type: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """获取最近的新闻"""
        query = self.db.query(VendorNews).join(Vendor)
        
        if vendor_name:
            query = query.filter(Vendor.name == vendor_name)
        
        if news_type:
            query = query.filter(VendorNews.news_type == news_type)
        
        news_list = query.order_by(VendorNews.created_at.desc()).limit(limit).all()
        
        return [
            {
                "id": news.id,
                "vendor_name": news.vendor.name,
                "vendor_display_name": news.vendor.display_name,
                "title": news.title,
                "content": news.content,
                "news_type": news.news_type,
                "url": news.url,
                "published_date": news.published_date.isoformat() if news.published_date else None,
                "created_at": news.created_at.isoformat()
            }
            for news in news_list
        ]
    
    def get_news_statistics(self, days: int = 7) -> Dict[str, Any]:
        """获取新闻统计信息"""
        from datetime import timedelta
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        total_news = self.db.query(VendorNews).filter(
            VendorNews.created_at >= cutoff_date
        ).count()
        
        news_by_type = self.db.query(
            VendorNews.news_type,
            self.db.query(VendorNews).filter(
                VendorNews.created_at >= cutoff_date
            ).group_by(VendorNews.news_type).count()
        ).all()
        
        news_by_vendor = self.db.query(
            Vendor.name,
            self.db.query(VendorNews).join(Vendor).filter(
                VendorNews.created_at >= cutoff_date
            ).group_by(Vendor.name).count()
        ).all()
        
        return {
            "total_news": total_news,
            "by_type": dict(news_by_type),
            "by_vendor": dict(news_by_vendor),
            "period_days": days
        }
