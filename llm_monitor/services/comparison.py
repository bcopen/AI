"""
价格对比服务
"""
from typing import List, Dict, Any, Optional
from loguru import logger
from sqlalchemy.orm import Session

from models.schema import Vendor, Model, CurrentPrice


class PriceComparator:
    """价格对比服务"""
    
    # 场景到能力标签的映射
    SCENARIO_CAPABILITIES = {
        "chat": ["chat"],
        "code": ["chat", "code"],
        "long_text": ["chat", "long_context"],
        "multimodal": ["chat", "vision", "multimodal"],
        "embedding": ["embedding"],
        "image_generation": ["image_generation"]
    }
    
    def __init__(self, db_session: Session):
        self.db = db_session
    
    def compare_by_scenario(
        self,
        scenario: str,
        tokens_input: int = 1000,
        tokens_output: int = 500
    ) -> List[Dict[str, Any]]:
        """
        按场景对比价格
        
        Args:
            scenario: 场景类型 (chat/code/long_text/multimodal/embedding/image_generation)
            tokens_input: 输入 token 数量
            tokens_output: 输出 token 数量
            
        Returns:
            价格对比列表，按总价格排序
        """
        capabilities_needed = self.SCENARIO_CAPABILITIES.get(scenario, ["chat"])
        
        # 获取所有当前价格
        prices = self.db.query(CurrentPrice).join(Model).join(Vendor).filter(
            Vendor.enabled == True
        ).all()
        
        results = []
        for price in prices:
            model = price.model
            vendor = model.vendor
            
            # 检查模型是否支持该场景
            model_capabilities = model.capabilities or []
            if not any(cap in model_capabilities for cap in capabilities_needed):
                continue
            
            # 检查上下文窗口是否满足长文本场景
            if scenario == "long_text" and model.context_window:
                if model.context_window < tokens_input + tokens_output:
                    continue
            
            # 计算总价
            total_cost = (price.input_price * tokens_input / 1000 + 
                         price.output_price * tokens_output / 1000)
            
            # 转换为 USD（如果是 CNY）
            cost_usd = total_cost
            if price.currency == "CNY":
                cost_usd = total_cost / 7.2  #  approximate exchange rate
            
            results.append({
                "vendor_name": vendor.name,
                "vendor_display_name": vendor.display_name,
                "model_name": model.model_name,
                "input_price": price.input_price,
                "output_price": price.output_price,
                "currency": price.currency,
                "total_cost": total_cost,
                "cost_usd": cost_usd,
                "context_window": model.context_window,
                "capabilities": model_capabilities,
                "unit": price.unit
            })
        
        # 按价格排序
        results.sort(key=lambda x: x["cost_usd"])
        
        return results
    
    def get_cheapest_models(
        self,
        scenario: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """获取指定场景下最便宜的模型"""
        comparison = self.compare_by_scenario(scenario)
        return comparison[:limit]
    
    def compare_specific_models(
        self,
        model_names: List[str],
        tokens_input: int = 1000,
        tokens_output: int = 500
    ) -> List[Dict[str, Any]]:
        """
        对比指定模型的价格
        
        Args:
            model_names: 模型名称列表 (格式：vendor/model_name，如 "openai/gpt-4o")
            tokens_input: 输入 token 数量
            tokens_output: 输出 token 数量
        """
        results = []
        
        for full_name in model_names:
            parts = full_name.split("/")
            if len(parts) != 2:
                logger.warning(f"Invalid model name format: {full_name}")
                continue
            
            vendor_name, model_name = parts
            
            price = self.db.query(CurrentPrice).join(Model).join(Vendor).filter(
                Vendor.name == vendor_name,
                Model.model_name == model_name
            ).first()
            
            if not price:
                logger.warning(f"Price not found for {full_name}")
                continue
            
            total_cost = (price.input_price * tokens_input / 1000 + 
                         price.output_price * tokens_output / 1000)
            
            cost_usd = total_cost
            if price.currency == "CNY":
                cost_usd = total_cost / 7.2
            
            results.append({
                "vendor_name": vendor_name,
                "model_name": model_name,
                "input_price": price.input_price,
                "output_price": price.output_price,
                "currency": price.currency,
                "total_cost": total_cost,
                "cost_usd": cost_usd,
                "context_window": price.model.context_window,
                "capabilities": price.model.capabilities
            })
        
        results.sort(key=lambda x: x["cost_usd"])
        return results
    
    def get_vendor_ranking(self, scenario: str = "chat") -> List[Dict[str, Any]]:
        """
        获取厂商价格排名（按平均价格）
        
        Args:
            scenario: 场景类型
        """
        comparison = self.compare_by_scenario(scenario)
        
        vendor_stats = {}
        for item in comparison:
            vendor = item["vendor_name"]
            if vendor not in vendor_stats:
                vendor_stats[vendor] = {
                    "vendor_display_name": item["vendor_display_name"],
                    "models": [],
                    "total_cost": 0,
                    "count": 0
                }
            vendor_stats[vendor]["models"].append(item["model_name"])
            vendor_stats[vendor]["total_cost"] += item["cost_usd"]
            vendor_stats[vendor]["count"] += 1
        
        # 计算平均价格
        ranking = []
        for vendor, stats in vendor_stats.items():
            avg_cost = stats["total_cost"] / stats["count"] if stats["count"] > 0 else 0
            ranking.append({
                "vendor_name": vendor,
                "vendor_display_name": stats["vendor_display_name"],
                "avg_cost_usd": avg_cost,
                "model_count": stats["count"],
                "models": stats["models"]
            })
        
        ranking.sort(key=lambda x: x["avg_cost_usd"])
        return ranking
