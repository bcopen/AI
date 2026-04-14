"""
Anthropic 和 Google 爬虫
"""
import re
from typing import List, Dict, Any
from loguru import logger

from scrapers.base import BaseScraper, PriceData, NewsData


class AnthropicScraper(BaseScraper):
    """Anthropic 爬虫"""
    
    def __init__(self):
        super().__init__("anthropic")
        self.pricing_url = "https://www.anthropic.com/pricing"
        self.news_url = "https://www.anthropic.com/news"
    
    async def scrape_prices(self) -> List[Dict[str, Any]]:
        """抓取 Anthropic 价格信息"""
        model_prices = {
            "claude-sonnet-4-20250514": {"input": 0.003, "output": 0.015, "context_window": 200000},
            "claude-opus-4-20250514": {"input": 0.015, "output": 0.075, "context_window": 200000},
            "claude-3-5-sonnet": {"input": 0.003, "output": 0.015, "context_window": 200000},
            "claude-3-5-haiku": {"input": 0.001, "output": 0.005, "context_window": 200000},
            "claude-3-opus": {"input": 0.015, "output": 0.075, "context_window": 200000},
            "claude-3-sonnet": {"input": 0.003, "output": 0.015, "context_window": 200000},
            "claude-3-haiku": {"input": 0.00025, "output": 0.00125, "context_window": 200000},
        }
        
        prices = []
        for model_name, price_info in model_prices.items():
            price_data = PriceData(
                model_name=model_name,
                input_price=price_info["input"],
                output_price=price_info["output"],
                context_window=price_info.get("context_window"),
                capabilities=["chat", "code", "vision", "long_context"],
                currency="USD",
                unit="1K tokens"
            )
            prices.append(price_data.to_dict())
        
        return prices
    
    async def scrape_news(self) -> List[Dict[str, Any]]:
        """抓取 Anthropic 新闻动态"""
        html = await self.fetch_page(self.news_url)
        if not html:
            return []
        
        soup = self.parse_html(html)
        news_list = []
        
        try:
            articles = soup.find_all('article', limit=10)
            
            for article in articles:
                title_elem = article.find(['h1', 'h2', 'h3'])
                if not title_elem:
                    continue
                
                title = title_elem.get_text(strip=True)
                
                link_elem = article.find('a')
                url = link_elem.get('href') if link_elem else None
                if url and not url.startswith('http'):
                    url = f"https://www.anthropic.com{url}"
                
                content_elem = article.find('p')
                content = content_elem.get_text(strip=True) if content_elem else ""
                
                news_type = self._classify_news(title)
                
                news_data = NewsData(
                    title=title,
                    content=content,
                    news_type=news_type,
                    url=url
                )
                news_list.append(news_data.to_dict())
                
        except Exception as e:
            logger.error(f"Error parsing Anthropic news: {e}")
        
        return news_list
    
    def _classify_news(self, title: str) -> str:
        """根据标题分类新闻"""
        title_lower = title.lower()
        
        if any(word in title_lower for word in ["new model", "release", "launch", "introduce"]):
            return "new_version"
        elif any(word in title_lower for word in ["upgrade", "improve", "enhance", "update"]):
            return "upgrade"
        elif any(word in title_lower for word in ["context", "window"]):
            return "context_window"
        elif "agent" in title_lower:
            return "agent"
        elif any(word in title_lower for word in ["policy", "term", "price", "pricing"]):
            return "policy"
        else:
            return "general"


class GoogleScraper(BaseScraper):
    """Google 爬虫"""
    
    def __init__(self):
        super().__init__("google")
        self.pricing_url = "https://cloud.google.com/vertex-ai/pricing"
        self.news_url = "https://cloud.google.com/blog/products/ai-machine-learning"
    
    async def scrape_prices(self) -> List[Dict[str, Any]]:
        """抓取 Google 价格信息"""
        model_prices = {
            "gemini-2.0-flash": {"input": 0.0001, "output": 0.0004, "context_window": 1048576},
            "gemini-2.0-flash-lite": {"input": 0.000075, "output": 0.0003, "context_window": 1048576},
            "gemini-1.5-pro": {"input": 0.00125, "output": 0.005, "context_window": 2097152},
            "gemini-1.5-flash": {"input": 0.000075, "output": 0.0003, "context_window": 1048576},
            "gemini-1.0-pro": {"input": 0.000125, "output": 0.000375, "context_window": 32768},
            "text-embedding-004": {"input": 0.00002, "output": 0, "context_window": 2048},
            "imagen-3": {"input": 0.04, "output": 0, "context_window": None},
        }
        
        prices = []
        for model_name, price_info in model_prices.items():
            capabilities = ["chat", "code", "vision"]
            if "embedding" in model_name:
                capabilities = ["embedding"]
            elif "imagen" in model_name:
                capabilities = ["image_generation"]
            
            price_data = PriceData(
                model_name=model_name,
                input_price=price_info["input"],
                output_price=price_info["output"],
                context_window=price_info.get("context_window"),
                capabilities=capabilities,
                currency="USD",
                unit="1K tokens"
            )
            prices.append(price_data.to_dict())
        
        return prices
    
    async def scrape_news(self) -> List[Dict[str, Any]]:
        """抓取 Google 新闻动态"""
        # 实际实现需要解析 Google Cloud 博客
        return []
