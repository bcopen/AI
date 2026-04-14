"""
通知服务
支持邮件、Webhook、钉钉、企业微信等多种通知方式
"""
import smtplib
import httpx
import json
from typing import List, Dict, Any, Optional
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from loguru import logger
from sqlalchemy.orm import Session

from models.schema import NotificationLog
from config.settings import settings


class Notifier:
    """通知服务"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.http_client = httpx.AsyncClient(timeout=30)
    
    async def send_notification(
        self,
        notification_type: str,
        target_id: int,
        message: str,
        channel: Optional[str] = None
    ):
        """
        发送通知
        
        Args:
            notification_type: 通知类型 (price_change/new_model/news)
            target_id: 目标 ID
            message: 通知内容
            channel: 指定渠道，None 则使用所有启用的渠道
        """
        channels = []
        
        if channel:
            channels = [channel]
        else:
            if settings.ENABLE_EMAIL_NOTIFY:
                channels.append("email")
            if settings.ENABLE_WEBHOOK:
                channels.append("webhook")
            if settings.ENABLE_DINGTALK:
                channels.append("dingtalk")
            if settings.ENABLE_WECHAT:
                channels.append("wechat")
        
        for ch in channels:
            await self._send_via_channel(ch, notification_type, target_id, message)
    
    async def _send_via_channel(
        self,
        channel: str,
        notification_type: str,
        target_id: int,
        message: str
    ):
        """通过指定渠道发送通知"""
        log_entry = NotificationLog(
            notification_type=notification_type,
            target_id=target_id,
            channel=channel,
            status="pending",
            message=message
        )
        self.db.add(log_entry)
        self.db.commit()
        
        try:
            if channel == "email":
                success = await self._send_email(message, notification_type)
            elif channel == "webhook":
                success = await self._send_webhook(message, notification_type)
            elif channel == "dingtalk":
                success = await self._send_dingtalk(message, notification_type)
            elif channel == "wechat":
                success = await self._send_wechat(message, notification_type)
            else:
                logger.warning(f"Unknown channel: {channel}")
                success = False
            
            log_entry.status = "sent" if success else "failed"
            log_entry.sent_at = datetime.utcnow() if success else None
            self.db.commit()
            
            if success:
                logger.info(f"Notification sent via {channel}: {notification_type}")
            else:
                logger.error(f"Notification failed via {channel}: {notification_type}")
                
        except Exception as e:
            log_entry.status = "failed"
            log_entry.error_message = str(e)
            self.db.commit()
            logger.error(f"Notification error via {channel}: {e}")
    
    async def _send_email(self, message: str, subject: str) -> bool:
        """发送邮件通知"""
        if not settings.EMAIL_RECIPIENTS:
            return False
        
        try:
            msg = MIMEMultipart()
            msg["From"] = settings.SMTP_USER
            msg["To"] = ", ".join(settings.EMAIL_RECIPIENTS)
            msg["Subject"] = f"[LLM Monitor] {subject}"
            
            msg.attach(MIMEText(message, "plain", "utf-8"))
            
            server = smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT)
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)
            server.quit()
            
            return True
        except Exception as e:
            logger.error(f"Email sending failed: {e}")
            return False
    
    async def _send_webhook(self, message: str, notification_type: str) -> bool:
        """发送 Webhook 通知"""
        try:
            payload = {
                "type": notification_type,
                "message": message,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            response = await self.http_client.post(
                settings.WEBHOOK_URL,
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Webhook sending failed: {e}")
            return False
    
    async def _send_dingtalk(self, message: str, notification_type: str) -> bool:
        """发送钉钉通知"""
        try:
            payload = {
                "msgtype": "text",
                "text": {
                    "content": f"[LLM Monitor] {notification_type}\n{message}"
                }
            }
            
            response = await self.http_client.post(
                settings.DINGTALK_WEBHOOK,
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            return response.status_code == 200
        except Exception as e:
            logger.error(f"DingTalk sending failed: {e}")
            return False
    
    async def _send_wechat(self, message: str, notification_type: str) -> bool:
        """发送企业微信通知"""
        try:
            # 获取 access token（实际使用中需要缓存）
            token_url = f"https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid={settings.WECHAT_CORP_ID}&corpsecret={settings.WECHAT_SECRET}"
            token_response = await self.http_client.get(token_url)
            token_data = token_response.json()
            access_token = token_data.get("access_token")
            
            if not access_token:
                logger.error("Failed to get WeChat access token")
                return False
            
            payload = {
                "touser": "@all",
                "msgtype": "text",
                "agentid": int(settings.WECHAT_AGENT_ID),
                "text": {
                    "content": f"[LLM Monitor] {notification_type}\n{message}"
                }
            }
            
            send_url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={access_token}"
            response = await self.http_client.post(send_url, json=payload)
            
            return response.status_code == 200
        except Exception as e:
            logger.error(f"WeChat sending failed: {e}")
            return False
    
    async def send_price_change_alert(
        self,
        vendor_name: str,
        model_name: str,
        old_input: float,
        new_input: float,
        old_output: float,
        new_output: float,
        change_percent: float
    ):
        """发送价格变动提醒"""
        direction = "下降 📉" if change_percent < 0 else "上升 📈"
        message = (
            f"💰 价格变动提醒\n"
            f"厂商：{vendor_name}\n"
            f"模型：{model_name}\n"
            f"输入价格：${old_input:.6f} → ${new_input:.6f}\n"
            f"输出价格：${old_output:.6f} → ${new_output:.6f}\n"
            f"变化幅度：{abs(change_percent):.2f}% {direction}"
        )
        
        await self.send_notification(
            notification_type="price_change",
            target_id=0,  # TODO: 使用实际的价格记录 ID
            message=message
        )
    
    async def send_price_alert(
        self,
        vendor_name: str,
        model_name: str,
        old_input_price: float,
        new_input_price: float,
        old_output_price: float,
        new_output_price: float,
        change_percent: float,
        change_type: str
    ):
        """发送价格告警（支持变化类型）"""
        type_emoji = {
            "increase": "📈",
            "decrease": "📉",
            "new": "🆕"
        }
        type_text = {
            "increase": "涨价",
            "decrease": "降价",
            "new": "新模型"
        }
        
        emoji = type_emoji.get(change_type, "⚠️")
        text = type_text.get(change_type, "价格变动")
        
        message = (
            f"{emoji} {text}提醒\n"
            f"厂商：{vendor_name}\n"
            f"模型：{model_name}\n"
            f"输入价格：${old_input_price:.6f} → ${new_input_price:.6f}\n"
            f"输出价格：${old_output_price:.6f} → ${new_output_price:.6f}\n"
            f"变化幅度：{change_percent:.2f}%"
        )

        await self.send_notification(
            notification_type="price_change",
            target_id=0,
            message=message
        )
    
    async def send_new_model_alert(
        self,
        vendor_name: str,
        model_name: str,
        capabilities: List[str],
        context_window: Optional[int]
    ):
        """发送新模型上线提醒"""
        message = (
            f"🎉 新模型上线\n"
            f"厂商：{vendor_name}\n"
            f"模型：{model_name}\n"
            f"能力：{', '.join(capabilities)}\n"
            f"上下文窗口：{context_window or '未知'}"
        )
        
        await self.send_notification(
            notification_type="new_model",
            target_id=0,
            message=message
        )
    
    async def send_news_alert(
        self,
        vendor_name: str,
        news_title: str,
        news_type: str,
        news_url: Optional[str]
    ):
        """发送新闻动态提醒"""
        type_map = {
            "new_version": "新版本发布",
            "upgrade": "能力升级",
            "context_window": "上下文窗口更新",
            "agent": "Agent 更新",
            "policy": "政策调整",
            "general": "动态"
        }
        
        message = (
            f"📰 {type_map.get(news_type, '动态')}\n"
            f"厂商：{vendor_name}\n"
            f"标题：{news_title}\n"
        )
        
        if news_url:
            message += f"链接：{news_url}"
        
        await self.send_notification(
            notification_type="news",
            target_id=0,
            message=message
        )
    
    async def close(self):
        """关闭资源"""
        await self.http_client.aclose()
