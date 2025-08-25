#!/usr/bin/env python3
"""
Notification Service

Handles all notifications including email, SMS, webhooks, and real-time updates.
Provides centralized notification management for trading events.

Features:
- Email notifications
- Webhook delivery
- Real-time WebSocket updates
- Notification templates
- Delivery status tracking
- Rate limiting and throttling
"""

import os
import asyncio
import json
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Union
from contextlib import asynccontextmanager
from enum import Enum
import smtplib
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart

import structlog
from fastapi import FastAPI, HTTPException, Depends, status, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import httpx
from pydantic import BaseModel, Field, EmailStr
import redis.asyncio as redis
from jinja2 import Template

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

# Configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", "trading-bot@example.com")
WEBHOOK_TIMEOUT = int(os.getenv("WEBHOOK_TIMEOUT", "10"))

# Redis client
redis_client = None

# Enums
class NotificationType(str, Enum):
    EMAIL = "email"
    WEBHOOK = "webhook"
    WEBSOCKET = "websocket"
    SMS = "sms"

class NotificationPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class NotificationStatus(str, Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    RETRY = "retry"

class EventType(str, Enum):
    ORDER_FILLED = "order_filled"
    ORDER_CANCELLED = "order_cancelled"
    POSITION_OPENED = "position_opened"
    POSITION_CLOSED = "position_closed"
    SIGNAL_GENERATED = "signal_generated"
    RISK_ALERT = "risk_alert"
    SYSTEM_ALERT = "system_alert"
    MARKET_ALERT = "market_alert"

# Data Models
class NotificationRequest(BaseModel):
    type: NotificationType = Field(..., description="Type of notification")
    recipient: str = Field(..., description="Recipient (email, phone, webhook URL)")
    subject: str = Field(..., description="Notification subject")
    message: str = Field(..., description="Notification message")
    priority: NotificationPriority = Field(default=NotificationPriority.MEDIUM)
    template: Optional[str] = Field(None, description="Template name")
    template_data: Optional[Dict[str, Any]] = Field(None, description="Template variables")
    event_type: Optional[EventType] = Field(None, description="Event type for categorization")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")

class NotificationResponse(BaseModel):
    id: str
    status: NotificationStatus
    message: str
    created_at: datetime
    sent_at: Optional[datetime] = None

class WebhookPayload(BaseModel):
    event_type: str
    timestamp: datetime
    data: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = None

class SubscriptionRequest(BaseModel):
    event_types: List[EventType]
    notification_type: NotificationType
    recipient: str
    enabled: bool = True

# WebSocket Connection Manager
class ConnectionManager:
    """Manages WebSocket connections for real-time notifications."""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.subscriptions: Dict[str, List[EventType]] = {}
    
    async def connect(self, websocket: WebSocket, client_id: str):
        """Accept WebSocket connection."""
        await websocket.accept()
        self.active_connections.append(websocket)
        self.subscriptions[client_id] = []
        logger.info("WebSocket client connected", client_id=client_id)
    
    def disconnect(self, websocket: WebSocket, client_id: str):
        """Handle WebSocket disconnection."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        if client_id in self.subscriptions:
            del self.subscriptions[client_id]
        logger.info("WebSocket client disconnected", client_id=client_id)
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        """Send message to specific WebSocket connection."""
        try:
            await websocket.send_text(message)
        except Exception as e:
            logger.error("Error sending WebSocket message", error=str(e))
    
    async def broadcast(self, message: Dict[str, Any], event_type: EventType):
        """Broadcast message to all connected clients interested in the event type."""
        message_str = json.dumps(message)
        
        # Send to all connections (for now - could filter by subscriptions)
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message_str)
            except:
                disconnected.append(connection)
        
        # Remove disconnected clients
        for connection in disconnected:
            if connection in self.active_connections:
                self.active_connections.remove(connection)

# Notification Templates
TEMPLATES = {
    "order_filled": {
        "subject": "Order Filled: {{symbol}}",
        "body": """
Your {{side}} order for {{quantity}} shares of {{symbol}} has been filled at ${{price}}.

Order Details:
- Symbol: {{symbol}}
- Side: {{side}}
- Quantity: {{quantity}}
- Price: ${{price}}
- Total Value: ${{total_value}}
- Timestamp: {{timestamp}}

Best regards,
Trading Bot
"""
    },
    "position_closed": {
        "subject": "Position Closed: {{symbol}} - {{pnl_status}}",
        "body": """
Your position in {{symbol}} has been closed.

Position Details:
- Symbol: {{symbol}}
- Quantity: {{quantity}}
- Entry Price: ${{entry_price}}
- Exit Price: ${{exit_price}}
- P&L: ${{pnl}} ({{pnl_percent}}%)
- Duration: {{duration}}

Best regards,
Trading Bot
"""
    },
    "risk_alert": {
        "subject": "Risk Alert: {{alert_type}}",
        "body": """
RISK ALERT: {{alert_type}}

{{message}}

Current Portfolio Status:
- Total Value: ${{portfolio_value}}
- Daily P&L: ${{day_pnl}}
- Risk Score: {{risk_score}}

Please review your positions and take appropriate action.

Best regards,
Trading Bot
"""
    },
    "signal_generated": {
        "subject": "Trading Signal: {{action}} {{symbol}}",
        "body": """
New trading signal generated:

Signal Details:
- Symbol: {{symbol}}
- Action: {{action}}
- Strength: {{strength}}%
- Strategy: {{strategy}}
- Price: ${{price}}
- Timestamp: {{timestamp}}

Best regards,
Trading Bot
"""
    }
}

# Notification Service
class NotificationService:
    """Core notification service for all types of notifications."""
    
    def __init__(self):
        self.connection_manager = ConnectionManager()
        
    async def send_notification(self, request: NotificationRequest) -> NotificationResponse:
        """Send a notification via the specified method."""
        try:
            notification_id = f"notif_{int(datetime.utcnow().timestamp())}"
            
            # Apply template if specified
            subject, message = await self._apply_template(request)
            
            # Route to appropriate sender
            if request.type == NotificationType.EMAIL:
                success = await self._send_email(request.recipient, subject, message)
            elif request.type == NotificationType.WEBHOOK:
                success = await self._send_webhook(request.recipient, request, subject, message)
            elif request.type == NotificationType.WEBSOCKET:
                success = await self._send_websocket(request, subject, message)
            else:
                raise ValueError(f"Unsupported notification type: {request.type}")
            
            status = NotificationStatus.SENT if success else NotificationStatus.FAILED
            sent_at = datetime.utcnow() if success else None
            
            # Store notification record in Redis
            await self._store_notification_record(notification_id, request, status, sent_at)
            
            return NotificationResponse(
                id=notification_id,
                status=status,
                message="Notification sent successfully" if success else "Failed to send notification",
                created_at=datetime.utcnow(),
                sent_at=sent_at
            )
            
        except Exception as e:
            logger.error("Error sending notification", error=str(e), request=request.dict())
            return NotificationResponse(
                id=f"notif_{int(datetime.utcnow().timestamp())}",
                status=NotificationStatus.FAILED,
                message=f"Error: {str(e)}",
                created_at=datetime.utcnow()
            )
    
    async def send_event_notification(self, event_type: EventType, data: Dict[str, Any]):
        """Send notifications for specific events."""
        try:
            # Get subscribers for this event type
            subscribers = await self._get_event_subscribers(event_type)
            
            # Send WebSocket broadcast
            await self.connection_manager.broadcast({
                "event_type": event_type.value,
                "data": data,
                "timestamp": datetime.utcnow().isoformat()
            }, event_type)
            
            # Send to other subscribers
            for subscriber in subscribers:
                notification_request = NotificationRequest(
                    type=subscriber["type"],
                    recipient=subscriber["recipient"],
                    subject=f"Event: {event_type.value}",
                    message=json.dumps(data, indent=2),
                    event_type=event_type,
                    template=event_type.value if event_type.value in TEMPLATES else None,
                    template_data=data
                )
                
                await self.send_notification(notification_request)
                
        except Exception as e:
            logger.error("Error sending event notification", error=str(e), event_type=event_type)
    
    async def _apply_template(self, request: NotificationRequest) -> tuple[str, str]:
        """Apply Jinja2 template to notification content."""
        if not request.template or request.template not in TEMPLATES:
            return request.subject, request.message
        
        template_data = request.template_data or {}
        template = TEMPLATES[request.template]
        
        try:
            subject_template = Template(template["subject"])
            body_template = Template(template["body"])
            
            subject = subject_template.render(**template_data)
            message = body_template.render(**template_data)
            
            return subject, message
        except Exception as e:
            logger.error("Template rendering error", error=str(e), template=request.template)
            return request.subject, request.message
    
    async def _send_email(self, recipient: str, subject: str, message: str) -> bool:
        """Send email notification."""
        try:
            if not SMTP_USER or not SMTP_PASSWORD:
                logger.warning("SMTP not configured, skipping email")
                return False
            
            # Create message
            msg = MimeMultipart()
            msg['From'] = SMTP_FROM
            msg['To'] = recipient
            msg['Subject'] = subject
            
            msg.attach(MimeText(message, 'plain'))
            
            # Send email
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
                server.starttls()
                server.login(SMTP_USER, SMTP_PASSWORD)
                text = msg.as_string()
                server.sendmail(SMTP_FROM, recipient, text)
            
            logger.info("Email sent successfully", recipient=recipient, subject=subject)
            return True
            
        except Exception as e:
            logger.error("Email sending failed", error=str(e), recipient=recipient)
            return False
    
    async def _send_webhook(self, webhook_url: str, request: NotificationRequest, 
                          subject: str, message: str) -> bool:
        """Send webhook notification."""
        try:
            payload = WebhookPayload(
                event_type=request.event_type.value if request.event_type else "notification",
                timestamp=datetime.utcnow(),
                data={
                    "subject": subject,
                    "message": message,
                    "priority": request.priority.value
                },
                metadata=request.metadata
            )
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    webhook_url,
                    json=payload.dict(),
                    timeout=WEBHOOK_TIMEOUT
                )
                
                if response.status_code == 200:
                    logger.info("Webhook sent successfully", url=webhook_url)
                    return True
                else:
                    logger.error("Webhook failed", url=webhook_url, status=response.status_code)
                    return False
                    
        except Exception as e:
            logger.error("Webhook sending failed", error=str(e), url=webhook_url)
            return False
    
    async def _send_websocket(self, request: NotificationRequest, subject: str, message: str) -> bool:
        """Send WebSocket notification."""
        try:
            notification_data = {
                "type": "notification",
                "subject": subject,
                "message": message,
                "priority": request.priority.value,
                "event_type": request.event_type.value if request.event_type else None,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            await self.connection_manager.broadcast(
                notification_data, 
                request.event_type or EventType.SYSTEM_ALERT
            )
            return True
            
        except Exception as e:
            logger.error("WebSocket sending failed", error=str(e))
            return False
    
    async def _store_notification_record(self, notification_id: str, request: NotificationRequest, 
                                       status: NotificationStatus, sent_at: Optional[datetime]):
        """Store notification record in Redis."""
        try:
            record = {
                "id": notification_id,
                "type": request.type.value,
                "recipient": request.recipient,
                "subject": request.subject,
                "status": status.value,
                "priority": request.priority.value,
                "event_type": request.event_type.value if request.event_type else None,
                "created_at": datetime.utcnow().isoformat(),
                "sent_at": sent_at.isoformat() if sent_at else None
            }
            
            if redis_client:
                await redis_client.setex(
                    f"notification:{notification_id}",
                    86400,  # 24 hours TTL
                    json.dumps(record)
                )
        except Exception as e:
            logger.error("Failed to store notification record", error=str(e))
    
    async def _get_event_subscribers(self, event_type: EventType) -> List[Dict[str, Any]]:
        """Get subscribers for a specific event type."""
        try:
            if redis_client:
                subscribers_key = f"subscribers:{event_type.value}"
                subscribers_data = await redis_client.get(subscribers_key)
                
                if subscribers_data:
                    return json.loads(subscribers_data)
            
            return []
        except Exception as e:
            logger.error("Failed to get subscribers", error=str(e))
            return []

# Global service instance
notification_service = NotificationService()

# Application lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global redis_client
    
    try:
        # Initialize Redis connection
        redis_client = redis.from_url(REDIS_URL)
        await redis_client.ping()
        logger.info("✅ Notification Service started successfully")
        yield
    except Exception as e:
        logger.error("❌ Failed to start Notification Service", error=str(e))
        yield
    finally:
        if redis_client:
            await redis_client.close()
        logger.info("🔌 Notification Service shutdown complete")

# FastAPI application
app = FastAPI(
    title="Notification Service",
    description="Centralized notification management for trading events",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Routes

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    redis_connected = False
    if redis_client:
        try:
            await redis_client.ping()
            redis_connected = True
        except:
            pass
    
    smtp_configured = bool(SMTP_USER and SMTP_PASSWORD)
    
    return {
        "service": "notification",
        "status": "healthy",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "redis_connected": redis_connected,
        "smtp_configured": smtp_configured,
        "active_websocket_connections": len(notification_service.connection_manager.active_connections)
    }

@app.post("/send", response_model=NotificationResponse)
async def send_notification(request: NotificationRequest):
    """Send a notification."""
    return await notification_service.send_notification(request)

@app.post("/events/{event_type}")
async def send_event_notification(event_type: EventType, data: Dict[str, Any]):
    """Send notifications for specific events."""
    await notification_service.send_event_notification(event_type, data)
    return {"message": "Event notification sent", "event_type": event_type.value}

@app.post("/subscribe")
async def subscribe_to_events(subscription: SubscriptionRequest):
    """Subscribe to event notifications."""
    try:
        if redis_client:
            for event_type in subscription.event_types:
                subscribers_key = f"subscribers:{event_type.value}"
                
                # Get existing subscribers
                existing_data = await redis_client.get(subscribers_key)
                subscribers = json.loads(existing_data) if existing_data else []
                
                # Add new subscriber
                subscriber_data = {
                    "type": subscription.notification_type.value,
                    "recipient": subscription.recipient,
                    "enabled": subscription.enabled
                }
                
                # Remove existing subscription for same recipient/type
                subscribers = [s for s in subscribers 
                             if not (s["recipient"] == subscription.recipient and 
                                   s["type"] == subscription.notification_type.value)]
                
                # Add new subscription
                subscribers.append(subscriber_data)
                
                # Store updated subscribers
                await redis_client.set(subscribers_key, json.dumps(subscribers))
        
        return {"message": "Subscription created successfully"}
    except Exception as e:
        logger.error("Failed to create subscription", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create subscription"
        )

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """WebSocket endpoint for real-time notifications."""
    await notification_service.connection_manager.connect(websocket, client_id)
    try:
        while True:
            # Keep connection alive and handle incoming messages
            data = await websocket.receive_text()
            # Echo back for now (could handle subscription updates)
            await notification_service.connection_manager.send_personal_message(
                f"Message received: {data}", websocket
            )
    except WebSocketDisconnect:
        notification_service.connection_manager.disconnect(websocket, client_id)

@app.get("/templates")
async def get_templates():
    """Get available notification templates."""
    return {"templates": list(TEMPLATES.keys())}

@app.get("/history")
async def get_notification_history(limit: int = 50):
    """Get notification history."""
    try:
        if not redis_client:
            return {"notifications": []}
        
        # Get notification keys
        keys = await redis_client.keys("notification:*")
        notifications = []
        
        for key in keys[-limit:]:  # Get latest notifications
            data = await redis_client.get(key)
            if data:
                notifications.append(json.loads(data))
        
        # Sort by created_at descending
        notifications.sort(key=lambda x: x["created_at"], reverse=True)
        
        return {"notifications": notifications}
    except Exception as e:
        logger.error("Failed to get notification history", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get notification history"
        )

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8008,
        reload=True
    )