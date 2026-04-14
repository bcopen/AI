"""
价格跟踪服务
"""
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from loguru import logger
from sqlalchemy.orm import Session

from models.schema import Vendor, Model, CurrentPrice, PriceHistory
from config.settings import settings, VENDOR_CONFIGS


class PriceTracker:
    """价格跟踪服务"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
    
    def get_or_create_vendor(self, vendor_name: str) -> Optional[Vendor]:
        """获取或创建厂商记录"""
        vendor_config = VENDOR_CONFIGS.get(vendor_name)
        if not vendor_config:
            logger.warning(f"No config found for vendor: {vendor_name}")
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
            logger.info(f"Created vendor: {vendor_name}")
        
        return vendor
    
    def get_or_create_model(self, vendor: Vendor, model_name: str) -> Model:
        """获取或创建模型记录"""
        model = self.db.query(Model).filter(
            Model.vendor_id == vendor.id,
            Model.model_name == model_name
        ).first()
        
        if not model:
            model = Model(
                vendor_id=vendor.id,
                model_name=model_name,
                display_name=model_name.replace("-", " ").title()
            )
            self.db.add(model)
            self.db.commit()
            self.db.refresh(model)
        
        return model
    
    def update_price(self, model: Model, price_data: Dict[str, Any]) -> Tuple[bool, Optional[CurrentPrice], Dict[str, Any]]:
        """
        更新模型价格
        
        Returns:
            (是否有变化，当前价格记录，变化详情)
        """
        # 查找当前价格记录
        current_price = self.db.query(CurrentPrice).filter(
            CurrentPrice.model_id == model.id
        ).first()
        
        input_price = price_data.get("input_price", 0)
        output_price = price_data.get("output_price", 0)
        
        change_info = {
            "has_change": False,
            "input_change_percent": 0.0,
            "output_change_percent": 0.0,
            "change_type": "new" if not current_price else "update"
        }
        
        # 检查价格是否变化
        has_changed = False
        if current_price:
            if (abs(current_price.input_price - input_price) > 0.00001 or
                abs(current_price.output_price - output_price) > 0.00001):
                has_changed = True
                change_info["has_change"] = True
                
                # 计算变化百分比
                if current_price.input_price > 0:
                    change_info["input_change_percent"] = round(
                        ((input_price - current_price.input_price) / current_price.input_price) * 100, 2
                    )
                if current_price.output_price > 0:
                    change_info["output_change_percent"] = round(
                        ((output_price - current_price.output_price) / current_price.output_price) * 100, 2
                    )
                
                # 确定变化类型
                if change_info["input_change_percent"] > 0 or change_info["output_change_percent"] > 0:
                    change_info["change_type"] = "increase"
                else:
                    change_info["change_type"] = "decrease"
                
                # 记录历史
                self._record_price_history(
                    model.vendor_id,
                    model.model_name,
                    current_price.input_price,
                    current_price.output_price,
                    current_price.currency,
                    change_type=change_info["change_type"],
                    change_percent=max(
                        abs(change_info["input_change_percent"]),
                        abs(change_info["output_change_percent"])
                    )
                )
                # 更新当前价格
                current_price.input_price = input_price
                current_price.output_price = output_price
                current_price.currency = price_data.get("currency", "USD")
                current_price.unit = price_data.get("unit", "1K tokens")
                current_price.updated_at = datetime.utcnow()
        else:
            # 新价格记录
            has_changed = True
            change_info["has_change"] = True
            change_info["change_type"] = "new"
            current_price = CurrentPrice(
                model_id=model.id,
                input_price=input_price,
                output_price=output_price,
                currency=price_data.get("currency", "USD"),
                unit=price_data.get("unit", "1K tokens")
            )
            self.db.add(current_price)
            # 记录为新模型
            self._record_price_history(
                model.vendor_id,
                model.model_name,
                input_price,
                output_price,
                price_data.get("currency", "USD"),
                change_type="new",
                change_percent=0.0
            )
        
        # 更新模型信息
        if price_data.get("context_window"):
            model.context_window = price_data["context_window"]
        if price_data.get("capabilities"):
            model.capabilities = price_data["capabilities"]
        
        self.db.commit()
        
        if has_changed:
            logger.info(f"Price updated for {model.model_name}: ${input_price}/${output_price}, "
                       f"change: {change_info['input_change_percent']}%/{change_info['output_change_percent']}%")
        
        return has_changed, current_price, change_info
    
    def _record_price_history(
        self,
        vendor_id: int,
        model_name: str,
        input_price: float,
        output_price: float,
        currency: str,
        change_type: str = "update",
        change_percent: float = 0.0
    ):
        """记录价格历史"""
        history = PriceHistory(
            vendor_id=vendor_id,
            model_name=model_name,
            input_price=input_price,
            output_price=output_price,
            currency=currency,
            change_type=change_type,
            change_percent=change_percent,
            snapshot_date=datetime.utcnow()
        )
        self.db.add(history)
        self.db.commit()
    
    def get_current_prices(self, vendor_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取当前价格列表"""
        query = self.db.query(CurrentPrice).join(Model).join(Vendor)
        
        if vendor_name:
            query = query.filter(Vendor.name == vendor_name)
        
        results = []
        for price in query.all():
            results.append({
                "vendor_name": price.model.vendor.name,
                "vendor_display_name": price.model.vendor.display_name,
                "model_name": price.model.model_name,
                "input_price": price.input_price,
                "output_price": price.output_price,
                "currency": price.currency,
                "unit": price.unit,
                "context_window": price.model.context_window,
                "capabilities": price.model.capabilities,
                "updated_at": price.updated_at.isoformat() if price.updated_at else None
            })
        
        return results
    
    def get_price_history(
        self,
        vendor_name: str,
        model_name: str,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """获取价格历史记录"""
        from datetime import timedelta
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        vendor = self.db.query(Vendor).filter(Vendor.name == vendor_name).first()
        if not vendor:
            return []
        
        history = self.db.query(PriceHistory).filter(
            PriceHistory.vendor_id == vendor.id,
            PriceHistory.model_name == model_name,
            PriceHistory.snapshot_date >= cutoff_date
        ).order_by(PriceHistory.snapshot_date.desc()).all()
        
        return [
            {
                "input_price": h.input_price,
                "output_price": h.output_price,
                "currency": h.currency,
                "change_type": h.change_type,
                "change_percent": h.change_percent,
                "snapshot_date": h.snapshot_date.isoformat()
            }
            for h in history
        ]
    
    def check_price_threshold(
        self,
        change_info: Dict[str, Any],
        threshold: float = 5.0
    ) -> bool:
        """检查价格变化是否超过阈值"""
        if not change_info.get("has_change"):
            return False
        
        input_change = abs(change_info.get("input_change_percent", 0))
        output_change = abs(change_info.get("output_change_percent", 0))
        
        return input_change >= threshold or output_change >= threshold
    
    def export_to_csv(self, filename: str, vendor_name: Optional[str] = None):
        """导出价格数据到 CSV"""
        import csv
        
        prices = self.get_current_prices(vendor_name)
        
        if not prices:
            logger.warning("No prices to export")
            return False
        
        with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'vendor_name', 'vendor_display_name', 'model_name',
                'input_price', 'output_price', 'currency', 'unit',
                'context_window', 'capabilities', 'updated_at'
            ])
            writer.writeheader()
            writer.writerows(prices)
        
        logger.info(f"Exported {len(prices)} prices to {filename}")
        return True
    
    def export_to_excel(self, filename: str, vendor_name: Optional[str] = None):
        """导出价格数据到 Excel"""
        try:
            import pandas as pd
        except ImportError:
            logger.error("pandas is required for Excel export. Install with: pip install pandas openpyxl")
            return False
        
        prices = self.get_current_prices(vendor_name)
        
        if not prices:
            logger.warning("No prices to export")
            return False
        
        df = pd.DataFrame(prices)
        
        # 添加价格变化统计
        try:
            df['total_price'] = df['input_price'] + df['output_price']
            df['cost_example'] = df['input_price'] * 1 + df['output_price'] * 0.5  # 1K 输入 + 500 输出
        except Exception:
            pass
        
        # 按厂商分组创建多个 sheet
        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
            # 总表
            df.to_excel(writer, sheet_name='全部价格', index=False)
            
            # 按厂商分 sheet
            for vendor in df['vendor_name'].unique():
                vendor_df = df[df['vendor_name'] == vendor]
                sheet_name = vendor[:31]  # Excel sheet name limit
                vendor_df.to_excel(writer, sheet_name=sheet_name, index=False)
        
        logger.info(f"Exported {len(prices)} prices to Excel: {filename}")
        return True
