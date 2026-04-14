"""
基础爬虫类
"""
import httpx
from bs4 import BeautifulSoup
from typing import Optional, Dict, Any, List
from datetime import datetime
from loguru import logger
from abc import ABC, abstractmethod

from config.settings import settings


class BaseScraper(ABC):
    """基础爬虫类，所有厂商爬虫的基类"""
    
    def __init__(self, vendor_name: str):
        self.vendor_name = vendor_name
        self.session = httpx.AsyncClient(
            timeout=settings.REQUEST_TIMEOUT,
            headers={
                "User-Agent": settings.USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            }
        )
    
    async def fetch_page(self, url: str) -> Optional[str]:
        """获取页面内容"""
        try:
            response = await self.session.get(url)
            response.raise_for_status()
            return response.text
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch {url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching {url}: {e}")
            return None
    
    def parse_html(self, html: str) -> BeautifulSoup:
        """解析 HTML"""
        return BeautifulSoup(html, 'lxml')
    
    @abstractmethod
    async def scrape_prices(self) -> List[Dict[str, Any]]:
        """抓取价格信息，子类必须实现"""
        pass
    
    @abstractmethod
    async def scrape_news(self) -> List[Dict[str, Any]]:
        """抓取新闻动态，子类必须实现"""
        pass
    
    async def close(self):
        """关闭会话"""
        await self.session.aclose()


class PriceData:
    """价格数据类"""
    
    def __init__(
        self,
        model_name: str,
        input_price: float,
        output_price: float,
        currency: str = "USD",
        unit: str = "1K tokens",
        context_window: Optional[int] = None,
        capabilities: Optional[List[str]] = None,
        **kwargs
    ):
        self.model_name = model_name
        self.input_price = input_price
        self.output_price = output_price
        self.currency = currency
        self.unit = unit
        self.context_window = context_window
        self.capabilities = capabilities or []
        self.extra_data = kwargs
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "model_name": self.model_name,
            "input_price": self.input_price,
            "output_price": self.output_price,
            "currency": self.currency,
            "unit": self.unit,
            "context_window": self.context_window,
            "capabilities": self.capabilities,
            **self.extra_data
        }


class NewsData:
    """新闻数据类"""
    
    def __init__(
        self,
        title: str,
        content: str,
        news_type: str,
        url: Optional[str] = None,
        published_date: Optional[datetime] = None,
        **kwargs
    ):
        self.title = title
        self.content = content
        self.news_type = news_type
        self.url = url
        self.published_date = published_date or datetime.utcnow()
        self.extra_data = kwargs
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "title": self.title,
            "content": self.content,
            "news_type": self.news_type,
            "url": self.url,
            "published_date": self.published_date.isoformat(),
            **self.extra_data
        }
