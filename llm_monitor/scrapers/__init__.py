"""
爬虫工厂模块
"""
from typing import Dict, Type, Optional
from loguru import logger

from scrapers.base import BaseScraper
from scrapers.openai import OpenAIScraper
from scrapers.international import AnthropicScraper, GoogleScraper
from scrapers.domestic import (
    DoubaoScraper,
    AliyunScraper,
    ZhipuScraper,
    KimiScraper,
    DeepSeekScraper,
    BaiduScraper
)


class ScraperFactory:
    """爬虫工厂类，用于创建和管理各厂商爬虫"""
    
    # 厂商标识到爬虫类的映射
    SCRAPER_MAP: Dict[str, Type[BaseScraper]] = {
        "openai": OpenAIScraper,
        "anthropic": AnthropicScraper,
        "google": GoogleScraper,
        "doubao": DoubaoScraper,
        "aliyun": AliyunScraper,
        "zhipu": ZhipuScraper,
        "kimi": KimiScraper,
        "deepseek": DeepSeekScraper,
        "baidu": BaiduScraper,
    }
    
    @classmethod
    def get_scraper(cls, vendor_name: str) -> Optional[BaseScraper]:
        """
        获取指定厂商的爬虫实例
        
        Args:
            vendor_name: 厂商标识
            
        Returns:
            爬虫实例，如果厂商不存在则返回 None
        """
        scraper_class = cls.SCRAPER_MAP.get(vendor_name.lower())
        if not scraper_class:
            logger.warning(f"No scraper found for vendor: {vendor_name}")
            return None
        
        try:
            return scraper_class()
        except Exception as e:
            logger.error(f"Failed to create scraper for {vendor_name}: {e}")
            return None
    
    @classmethod
    def get_all_scrapers(cls) -> Dict[str, BaseScraper]:
        """
        获取所有厂商的爬虫实例
        
        Returns:
            厂商标识到爬虫实例的字典
        """
        scrapers = {}
        for vendor_name, scraper_class in cls.SCRAPER_MAP.items():
            try:
                scrapers[vendor_name] = scraper_class()
            except Exception as e:
                logger.error(f"Failed to create scraper for {vendor_name}: {e}")
        return scrapers
    
    @classmethod
    def get_available_vendors(cls) -> list:
        """
        获取所有可用的厂商标识列表
        
        Returns:
            厂商标识列表
        """
        return list(cls.SCRAPER_MAP.keys())
    
    @classmethod
    def register_scraper(cls, vendor_name: str, scraper_class: Type[BaseScraper]):
        """
        注册新的爬虫类
        
        Args:
            vendor_name: 厂商标识
            scraper_class: 爬虫类
        """
        cls.SCRAPER_MAP[vendor_name.lower()] = scraper_class
        logger.info(f"Registered scraper for vendor: {vendor_name}")


# 便捷函数
def get_scraper(vendor_name: str) -> Optional[BaseScraper]:
    """获取指定厂商的爬虫实例"""
    return ScraperFactory.get_scraper(vendor_name)


def get_all_scrapers() -> Dict[str, BaseScraper]:
    """获取所有厂商的爬虫实例"""
    return ScraperFactory.get_all_scrapers()
