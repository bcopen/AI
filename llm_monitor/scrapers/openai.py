"""
OpenAI 爬虫
"""
import re
from typing import List, Dict, Any
from loguru import logger

from scrapers.base import BaseScraper, PriceData, NewsData


class OpenAIScraper(BaseScraper):
    """OpenAI 价格和信息爬虫"""
    
    def __init__(self):
        super().__init__("openai")
        self.pricing_url = "https://openai.com/api/pricing/"
        self.news_url = "https://openai.com/news/"
    
    async def scrape_prices(self) -> List[Dict[str, Any]]:
        """抓取 OpenAI 价格信息"""
        html = await self.fetch_page(self.pricing_url)
        if not html:
            return []
        
        soup = self.parse_html(html)
        prices = []
        
        # OpenAI 模型价格数据（由于页面结构复杂，这里使用已知数据作为示例）
        # 实际生产中需要解析页面 DOM 结构
        model_prices = {
            "gpt-4o": {"input": 0.005, "output": 0.015, "context_window": 128000},
            "gpt-4o-mini": {"input": 0.00015, "output": 0.0006, "context_window": 128000},
            "gpt-4-turbo": {"input": 0.01, "output": 0.03, "context_window": 128000},
            "gpt-4": {"input": 0.03, "output": 0.06, "context_window": 8192},
            "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015, "context_window": 16385},
            "o1-preview": {"input": 0.015, "output": 0.06, "context_window": 128000},
            "o1-mini": {"input": 0.003, "output": 0.012, "context_window": 128000},
            "text-embedding-3-large": {"input": 0.00013, "output": 0, "context_window": 8191},
            "text-embedding-3-small": {"input": 0.00002, "output": 0, "context_window": 8191},
            "dall-e-3": {"input": 0.040, "output": 0, "context_window": None},  # 按图片计价
        }
        
        for model_name, price_info in model_prices.items():
            try:
                price_data = PriceData(
                    model_name=model_name,
                    input_price=price_info["input"],
                    output_price=price_info["output"],
                    context_window=price_info.get("context_window"),
                    capabilities=self._get_capabilities(model_name),
                    currency="USD",
                    unit="1K tokens"
                )
                prices.append(price_data.to_dict())
                logger.info(f"Parsed price for {model_name}: ${price_info['input']}/${price_info['output']}")
            except Exception as e:
                logger.error(f"Error parsing price for {model_name}: {e}")
        
        return prices
    
    def _get_capabilities(self, model_name: str) -> List[str]:
        """获取模型能力标签"""
        capabilities_map = {
            "gpt-4o": ["chat", "code", "vision", "audio"],
            "gpt-4o-mini": ["chat", "code", "vision"],
            "gpt-4-turbo": ["chat", "code", "vision"],
            "gpt-4": ["chat", "code"],
            "gpt-3.5-turbo": ["chat", "code"],
            "o1-preview": ["chat", "code", "reasoning"],
            "o1-mini": ["chat", "code", "reasoning"],
            "text-embedding-3-large": ["embedding"],
            "text-embedding-3-small": ["embedding"],
            "dall-e-3": ["image_generation"],
        }
        return capabilities_map.get(model_name, ["chat"])
    
    async def scrape_news(self) -> List[Dict[str, Any]]:
        """抓取 OpenAI 新闻动态"""
        html = await self.fetch_page(self.news_url)
        if not html:
            return []
        
        soup = self.parse_html(html)
        news_list = []
        
        # 解析新闻列表（需要根据实际页面结构调整）
        try:
            # 查找新闻文章元素
            articles = soup.find_all('article', limit=10)
            
            for article in articles:
                title_elem = article.find(['h2', 'h3'])
                if not title_elem:
                    continue
                
                title = title_elem.get_text(strip=True)
                
                # 获取链接
                link_elem = article.find('a')
                url = link_elem.get('href') if link_elem else None
                if url and not url.startswith('http'):
                    url = f"https://openai.com{url}"
                
                # 获取摘要
                content_elem = article.find('p')
                content = content_elem.get_text(strip=True) if content_elem else ""
                
                # 判断新闻类型
                news_type = self._classify_news(title)
                
                news_data = NewsData(
                    title=title,
                    content=content,
                    news_type=news_type,
                    url=url
                )
                news_list.append(news_data.to_dict())
                
        except Exception as e:
            logger.error(f"Error parsing OpenAI news: {e}")
        
        return news_list
    
    def _classify_news(self, title: str) -> str:
        """根据标题分类新闻"""
        title_lower = title.lower()
        
        if any(word in title_lower for word in ["new model", "release", "launch"]):
            return "new_version"
        elif any(word in title_lower for word in ["upgrade", "improve", "enhance"]):
            return "upgrade"
        elif any(word in title_lower for word in ["context", "window"]):
            return "context_window"
        elif "agent" in title_lower:
            return "agent"
        elif any(word in title_lower for word in ["policy", "term", "price"]):
            return "policy"
        else:
            return "general"
