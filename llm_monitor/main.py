"""
主程序入口
包含定时任务调度、数据采集和通知逻辑
"""
import asyncio
from datetime import datetime
from loguru import logger
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from config.settings import settings, VENDOR_CONFIGS
from models.schema import init_db
from scrapers import get_all_scrapers
from services.price_tracker import PriceTracker
from services.news_monitor import NewsMonitor
from services.comparison import PriceComparator
from notifications.notifier import Notifier


class LLMMonitorApp:
    """LLM 监控应用主类"""
    
    def __init__(self):
        # 初始化数据库
        self.SessionLocal, self.engine = init_db(settings.DATABASE_URL)
        self.db = self.SessionLocal()
        
        # 初始化服务
        self.price_tracker = PriceTracker(self.db)
        self.news_monitor = NewsMonitor(self.db)
        self.price_comparator = PriceComparator(self.db)
        self.notifier = Notifier(self.db)
        
        # 初始化调度器
        self.scheduler = AsyncIOScheduler()
        
        # 爬虫实例缓存
        self.scrapers = {}
    
    async def initialize(self):
        """初始化应用"""
        logger.info("Initializing LLM Monitor...")
        
        # 初始化厂商记录
        for vendor_name, config in VENDOR_CONFIGS.items():
            if config.get("enabled", True):
                self.price_tracker.get_or_create_vendor(vendor_name)
        
        logger.info("Initialization complete")
    
    async def scrape_all_prices(self):
        """抓取所有厂商的价格信息"""
        logger.info("Starting price scraping...")
        
        scrapers = get_all_scrapers()
        
        for vendor_name, scraper in scrapers.items():
            try:
                logger.info(f"Scraping prices for {vendor_name}...")
                
                # 获取价格数据
                prices = await scraper.scrape_prices()
                
                if not prices:
                    logger.warning(f"No prices found for {vendor_name}")
                    continue
                
                # 获取或创建厂商
                vendor = self.price_tracker.get_or_create_vendor(vendor_name)
                if not vendor:
                    continue
                
                # 更新每个模型的价格
                for price_data in prices:
                    model = self.price_tracker.get_or_create_model(
                        vendor, 
                        price_data["model_name"]
                    )
                    
                    has_changed, current_price, change_info = self.price_tracker.update_price(
                        model, 
                        price_data
                    )
                    
                    # 如果价格变化超过阈值，发送通知
                    if has_changed and current_price:
                        # 检查是否超过阈值
                        if self.price_tracker.check_price_threshold(
                            change_info, 
                            settings.PRICE_CHANGE_THRESHOLD
                        ):
                            await self.notifier.send_price_alert(
                                vendor_name=vendor.name,
                                model_name=model.model_name,
                                old_input_price=current_price.input_price - (
                                    current_price.input_price * change_info["input_change_percent"] / 100
                                    if change_info["input_change_percent"] else 0
                                ),
                                new_input_price=current_price.input_price,
                                old_output_price=current_price.output_price - (
                                    current_price.output_price * change_info["output_change_percent"] / 100
                                    if change_info["output_change_percent"] else 0
                                ),
                                new_output_price=current_price.output_price,
                                change_percent=max(
                                    abs(change_info["input_change_percent"]),
                                    abs(change_info["output_change_percent"])
                                ),
                                change_type=change_info["change_type"]
                            )
                
                logger.info(f"Completed price scraping for {vendor_name}")
                
            except Exception as e:
                logger.error(f"Error scraping prices for {vendor_name}: {e}")
            finally:
                await scraper.close()
        
        logger.info("Price scraping completed")
    
    async def scrape_all_news(self):
        """抓取所有厂商的新闻动态"""
        logger.info("Starting news scraping...")
        
        scrapers = get_all_scrapers()
        
        for vendor_name, scraper in scrapers.items():
            try:
                logger.info(f"Scraping news for {vendor_name}...")
                
                # 获取新闻数据
                news_list = await scraper.scrape_news()
                
                if not news_list:
                    logger.debug(f"No news found for {vendor_name}")
                    continue
                
                # 获取或创建厂商
                vendor = self.news_monitor.get_or_create_vendor(vendor_name)
                if not vendor:
                    continue
                
                # 添加每条新闻
                for news_data in news_list:
                    news = self.news_monitor.add_news(vendor, news_data)
                    
                    # 如果是新新闻且未通知，发送提醒
                    if news and not news.is_notified:
                        await self.notifier.send_news_alert(
                            vendor_name=vendor.name,
                            news_title=news.title,
                            news_type=news.news_type,
                            news_url=news.url
                        )
                        self.news_monitor.mark_as_notified(news.id)
                
                logger.info(f"Completed news scraping for {vendor_name}")
                
            except Exception as e:
                logger.error(f"Error scraping news for {vendor_name}: {e}")
            finally:
                await scraper.close()
        
        logger.info("News scraping completed")
    
    async def process_unnotified_news(self):
        """处理未通知的新闻"""
        unnotified = self.news_monitor.get_unnotified_news()
        
        for news in unnotified:
            await self.notifier.send_news_alert(
                vendor_name=news["vendor_name"],
                news_title=news["title"],
                news_type=news["news_type"],
                news_url=news["url"]
            )
            self.news_monitor.mark_as_notified(news["id"])
    
    def setup_scheduler(self):
        """设置定时任务"""
        # 价格检查任务
        self.scheduler.add_job(
            self.scrape_all_prices,
            trigger=IntervalTrigger(seconds=settings.PRICE_CHECK_INTERVAL),
            id="price_check",
            name="Check Prices",
            replace_existing=True
        )
        
        # 新闻检查任务
        self.scheduler.add_job(
            self.scrape_all_news,
            trigger=IntervalTrigger(seconds=settings.NEWS_CHECK_INTERVAL),
            id="news_check",
            name="Check News",
            replace_existing=True
        )
        
        # 未通知新闻处理任务（每 5 分钟）
        self.scheduler.add_job(
            self.process_unnotified_news,
            trigger=IntervalTrigger(minutes=5),
            id="process_unnotified",
            name="Process Unnotified News",
            replace_existing=True
        )
        
        logger.info(f"Scheduled jobs: price_check ({settings.PRICE_CHECK_INTERVAL}s), "
                   f"news_check ({settings.NEWS_CHECK_INTERVAL}s)")
    
    async def run_once(self):
        """运行一次完整的数据采集"""
        await self.initialize()
        await self.scrape_all_prices()
        await self.scrape_all_news()
    
    async def run(self):
        """启动应用（带定时任务）"""
        await self.initialize()
        
        # 立即执行一次
        await self.scrape_all_prices()
        await self.scrape_all_news()
        
        # 启动调度器
        self.setup_scheduler()
        self.scheduler.start()
        
        logger.info("LLM Monitor is running...")
        
        # 保持运行
        try:
            while True:
                await asyncio.sleep(60)
        except KeyboardInterrupt:
            logger.info("Shutting down...")
            self.scheduler.shutdown()
            await self.notifier.close()
    
    def get_price_comparison(self, scenario: str = "chat"):
        """获取价格对比（同步方法，用于 CLI）"""
        return self.price_comparator.compare_by_scenario(scenario)
    
    def get_recent_news(self, limit: int = 10):
        """获取最近新闻（同步方法，用于 CLI）"""
        return self.news_monitor.get_recent_news(limit=limit)


async def main():
    """主函数"""
    logger.add("llm_monitor.log", rotation="1 day", retention="7 days")
    
    app = LLMMonitorApp()
    
    # 命令行参数处理（简化版）
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "run":
            # 持续运行模式
            await app.run()
        elif command == "once":
            # 运行一次
            await app.run_once()
        elif command == "prices":
            # 只抓取价格
            await app.initialize()
            await app.scrape_all_prices()
        elif command == "news":
            # 只抓取新闻
            await app.initialize()
            await app.scrape_all_news()
        elif command == "compare":
            # 价格对比
            await app.initialize()
            scenario = sys.argv[2] if len(sys.argv) > 2 else "chat"
            results = app.get_price_comparison(scenario)
            
            print(f"\n{'='*60}")
            print(f"{scenario.upper()} 场景价格对比")
            print(f"{'='*60}\n")
            
            for i, item in enumerate(results[:10], 1):
                print(f"{i}. {item['vendor_display_name']} - {item['model_name']}")
                print(f"   输入：${item['input_price']}/1K, 输出：${item['output_price']}/1K")
                print(f"   总价：${item['cost_usd']:.6f} (1K 输入 + 500 输出)")
                print()
        elif command == "news-list":
            # 新闻列表
            await app.initialize()
            news_list = app.get_recent_news()
            
            print(f"\n{'='*60}")
            print("最近动态")
            print(f"{'='*60}\n")
            
            for news in news_list:
                print(f"[{news['vendor_display_name']}] {news['title']}")
                print(f"类型：{news['news_type']}")
                if news['url']:
                    print(f"链接：{news['url']}")
                print()
        else:
            print("Usage: python main.py [run|once|prices|news|compare|news-list]")
    else:
        # 默认运行一次
        print("No command specified, running once...")
        await app.run_once()
        
        # 显示摘要
        print("\n" + "="*60)
        print("数据采集完成！")
        print("="*60)
        
        prices = app.price_tracker.get_current_prices()
        print(f"\n共收集 {len(prices)} 条价格记录")
        
        news = app.news_monitor.get_recent_news(limit=5)
        print(f"最近 {len(news)} 条动态\n")


if __name__ == "__main__":
    asyncio.run(main())
