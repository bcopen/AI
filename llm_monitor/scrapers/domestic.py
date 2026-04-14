"""
国内厂商爬虫集合（字节豆包、阿里通义、智谱、Kimi、DeepSeek、百度文心）
"""
import re
from typing import List, Dict, Any
from loguru import logger

from scrapers.base import BaseScraper, PriceData, NewsData


class DoubaoScraper(BaseScraper):
    """字节豆包爬虫"""
    
    def __init__(self):
        super().__init__("doubao")
        self.pricing_url = "https://www.volcengine.com/product/doubao"
    
    async def scrape_prices(self) -> List[Dict[str, Any]]:
        """抓取字节豆包价格信息"""
        # 豆包模型价格（参考官方定价）
        model_prices = {
            "doubao-pro-4k": {"input": 0.0003, "output": 0.0006, "context_window": 4096},
            "doubao-pro-32k": {"input": 0.0008, "output": 0.0010, "context_window": 32768},
            "doubao-pro-128k": {"input": 0.005, "output": 0.009, "context_window": 131072},
            "doubao-lite-4k": {"input": 0.0001, "output": 0.0003, "context_window": 4096},
            "doubao-lite-32k": {"input": 0.0003, "output": 0.0006, "context_window": 32768},
            "doubao-lite-128k": {"input": 0.002, "output": 0.005, "context_window": 131072},
        }
        
        prices = []
        for model_name, price_info in model_prices.items():
            price_data = PriceData(
                model_name=model_name,
                input_price=price_info["input"],
                output_price=price_info["output"],
                context_window=price_info.get("context_window"),
                capabilities=["chat", "code"],
                currency="CNY",
                unit="1K tokens"
            )
            prices.append(price_data.to_dict())
        
        return prices
    
    async def scrape_news(self) -> List[Dict[str, Any]]:
        """抓取字节豆包新闻动态"""
        # 实际实现需要解析火山引擎官网新闻
        return []


class AliyunScraper(BaseScraper):
    """阿里通义千问爬虫"""
    
    def __init__(self):
        super().__init__("aliyun")
        self.pricing_url = "https://help.aliyun.com/price/tongyi"
    
    async def scrape_prices(self) -> List[Dict[str, Any]]:
        """抓取阿里通义价格信息"""
        model_prices = {
            "qwen-turbo": {"input": 0.002, "output": 0.006, "context_window": 32768},
            "qwen-plus": {"input": 0.004, "output": 0.012, "context_window": 32768},
            "qwen-max": {"input": 0.04, "output": 0.12, "context_window": 32768},
            "qwen-max-longcontext": {"input": 0.04, "output": 0.12, "context_window": 200000},
            "qwen-vl-plus": {"input": 0.015, "output": 0.045, "context_window": 8000},
            "qwen-audio-turbo": {"input": 0.01, "output": 0.03, "context_window": 8000},
        }
        
        prices = []
        for model_name, price_info in model_prices.items():
            capabilities = ["chat"]
            if "vl" in model_name or "audio" in model_name:
                capabilities.append("multimodal")
            
            price_data = PriceData(
                model_name=model_name,
                input_price=price_info["input"],
                output_price=price_info["output"],
                context_window=price_info.get("context_window"),
                capabilities=capabilities,
                currency="CNY",
                unit="1K tokens"
            )
            prices.append(price_data.to_dict())
        
        return prices
    
    async def scrape_news(self) -> List[Dict[str, Any]]:
        """抓取阿里通义新闻动态"""
        return []


class ZhipuScraper(BaseScraper):
    """智谱 AI 爬虫"""
    
    def __init__(self):
        super().__init__("zhipu")
        self.pricing_url = "https://open.bigmodel.cn/pricing"
    
    async def scrape_prices(self) -> List[Dict[str, Any]]:
        """抓取智谱 AI 价格信息"""
        model_prices = {
            "glm-4": {"input": 0.1, "output": 0.1, "context_window": 128000},
            "glm-4-air": {"input": 0.01, "output": 0.01, "context_window": 128000},
            "glm-4-airx": {"input": 0.02, "output": 0.02, "context_window": 8000},
            "glm-4-flash": {"input": 0.001, "output": 0.001, "context_window": 128000},
            "glm-3-turbo": {"input": 0.005, "output": 0.005, "context_window": 128000},
            "cogview-3": {"input": 0.12, "output": 0, "context_window": None},  # 按图片计价
        }
        
        prices = []
        for model_name, price_info in model_prices.items():
            capabilities = ["chat", "code"] if "cogview" not in model_name else ["image_generation"]
            
            price_data = PriceData(
                model_name=model_name,
                input_price=price_info["input"],
                output_price=price_info["output"],
                context_window=price_info.get("context_window"),
                capabilities=capabilities,
                currency="CNY",
                unit="1K tokens"
            )
            prices.append(price_data.to_dict())
        
        return prices
    
    async def scrape_news(self) -> List[Dict[str, Any]]:
        """抓取智谱 AI 新闻动态"""
        return []


class KimiScraper(BaseScraper):
    """Kimi 爬虫"""
    
    def __init__(self):
        super().__init__("kimi")
        self.pricing_url = "https://platform.moonshot.cn/pricing"
    
    async def scrape_prices(self) -> List[Dict[str, Any]]:
        """抓取 Kimi 价格信息"""
        model_prices = {
            "moonshot-v1-8k": {"input": 0.012, "output": 0.012, "context_window": 8192},
            "moonshot-v1-32k": {"input": 0.024, "output": 0.024, "context_window": 32768},
            "moonshot-v1-128k": {"input": 0.06, "output": 0.06, "context_window": 131072},
        }
        
        prices = []
        for model_name, price_info in model_prices.items():
            price_data = PriceData(
                model_name=model_name,
                input_price=price_info["input"],
                output_price=price_info["output"],
                context_window=price_info.get("context_window"),
                capabilities=["chat", "code", "long_context"],
                currency="CNY",
                unit="1K tokens"
            )
            prices.append(price_data.to_dict())
        
        return prices
    
    async def scrape_news(self) -> List[Dict[str, Any]]:
        """抓取 Kimi 新闻动态"""
        return []


class DeepSeekScraper(BaseScraper):
    """DeepSeek 爬虫"""
    
    def __init__(self):
        super().__init__("deepseek")
        self.pricing_url = "https://platform.deepseek.com/pricing"
    
    async def scrape_prices(self) -> List[Dict[str, Any]]:
        """抓取 DeepSeek 价格信息"""
        model_prices = {
            "deepseek-chat": {"input": 0.001, "output": 0.002, "context_window": 128000},
            "deepseek-coder": {"input": 0.001, "output": 0.002, "context_window": 128000},
            "deepseek-v2-chat": {"input": 0.00013, "output": 0.00053, "context_window": 128000},
            "deepseek-v2-coder": {"input": 0.00013, "output": 0.00053, "context_window": 128000},
        }
        
        prices = []
        for model_name, price_info in model_prices.items():
            capabilities = ["chat", "code"] if "coder" in model_name else ["chat"]
            
            price_data = PriceData(
                model_name=model_name,
                input_price=price_info["input"],
                output_price=price_info["output"],
                context_window=price_info.get("context_window"),
                capabilities=capabilities,
                currency="CNY",
                unit="1K tokens"
            )
            prices.append(price_data.to_dict())
        
        return prices
    
    async def scrape_news(self) -> List[Dict[str, Any]]:
        """抓取 DeepSeek 新闻动态"""
        return []


class BaiduScraper(BaseScraper):
    """百度文心一言爬虫"""
    
    def __init__(self):
        super().__init__("baidu")
        self.pricing_url = "https://cloud.baidu.com/price/wenxinworkshop"
    
    async def scrape_prices(self) -> List[Dict[str, Any]]:
        """抓取百度文心价格信息"""
        model_prices = {
            "ernie-4.0": {"input": 0.12, "output": 0.12, "context_window": 8192},
            "ernie-3.5-128k": {"input": 0.008, "output": 0.008, "context_window": 131072},
            "ernie-3.5-8k": {"input": 0.0012, "output": 0.0012, "context_window": 8192},
            "ernie-lite-8k": {"input": 0.0003, "output": 0.0003, "context_window": 8192},
            "ernie-speed-128k": {"input": 0.004, "output": 0.004, "context_window": 131072},
            "ernie-speed-8k": {"input": 0.0005, "output": 0.0005, "context_window": 8192},
        }
        
        prices = []
        for model_name, price_info in model_prices.items():
            price_data = PriceData(
                model_name=model_name,
                input_price=price_info["input"],
                output_price=price_info["output"],
                context_window=price_info.get("context_window"),
                capabilities=["chat", "code"],
                currency="CNY",
                unit="1K tokens"
            )
            prices.append(price_data.to_dict())
        
        return prices
    
    async def scrape_news(self) -> List[Dict[str, Any]]:
        """抓取百度文心新闻动态"""
        return []
