#!/usr/bin/env python3
"""
Simplified Notification Service
"""

from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(
    title="Notification Service",
    description="Alert and notification management",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mock alerts
MOCK_ALERTS = [
    {
        "id": "alert_001",
        "type": "trade_execution",
        "severity": "info",
        "title": "Order Filled",
        "message": "Buy order for 100 shares of AAPL filled at $175.50",
        "timestamp": (datetime.utcnow() - timedelta(hours=2)).isoformat(),
        "read": True
    },
    {
        "id": "alert_002",
        "type": "risk_warning",
        "severity": "warning",
        "title": "Risk Limit Approaching",
        "message": "Portfolio risk approaching daily limit (80% used)",
        "timestamp": (datetime.utcnow() - timedelta(hours=1)).isoformat(),
        "read": False
    },
    {
        "id": "alert_003",
        "type": "signal",
        "severity": "info",
        "title": "Buy Signal Generated",
        "message": "Strong buy signal detected for MSFT",
        "timestamp": (datetime.utcnow() - timedelta(minutes=30)).isoformat(),
        "read": False
    }
]

class NotificationRequest(BaseModel):
    type: str
    severity: str  # info, warning, error, critical
    title: str
    message: str

@app.get("/health")
async def health_check():
    return {
        "service": "notification",
        "status": "healthy",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "unread_alerts": sum(1 for a in MOCK_ALERTS if not a.get("read", False))
    }

@app.get("/alerts")
async def get_alerts(unread_only: bool = False):
    """Get all alerts or only unread ones."""
    alerts = MOCK_ALERTS
    if unread_only:
        alerts = [a for a in alerts if not a.get("read", False)]
    
    return {
        "alerts": alerts,
        "total": len(alerts),
        "unread": sum(1 for a in alerts if not a.get("read", False)),
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/alerts/{alert_id}")
async def get_alert(alert_id: str):
    """Get specific alert."""
    alert = next((a for a in MOCK_ALERTS if a["id"] == alert_id), None)
    if not alert:
        return {"error": "Alert not found"}
    return alert

@app.post("/alerts")
async def create_alert(notification: NotificationRequest):
    """Create a new alert."""
    new_alert = {
        "id": f"alert_{len(MOCK_ALERTS) + 1:03d}",
        "type": notification.type,
        "severity": notification.severity,
        "title": notification.title,
        "message": notification.message,
        "timestamp": datetime.utcnow().isoformat(),
        "read": False
    }
    
    MOCK_ALERTS.insert(0, new_alert)  # Add to beginning
    
    return {
        "message": "Alert created successfully",
        "alert": new_alert
    }

@app.put("/alerts/{alert_id}/read")
async def mark_alert_read(alert_id: str):
    """Mark an alert as read."""
    for alert in MOCK_ALERTS:
        if alert["id"] == alert_id:
            alert["read"] = True
            return {"message": "Alert marked as read", "alert": alert}
    
    return {"error": "Alert not found"}

@app.get("/alerts/summary")
async def get_alerts_summary():
    """Get alerts summary."""
    summary = {
        "total": len(MOCK_ALERTS),
        "unread": sum(1 for a in MOCK_ALERTS if not a.get("read", False)),
        "by_severity": {},
        "by_type": {}
    }
    
    for alert in MOCK_ALERTS:
        severity = alert.get("severity", "info")
        alert_type = alert.get("type", "other")
        
        summary["by_severity"][severity] = summary["by_severity"].get(severity, 0) + 1
        summary["by_type"][alert_type] = summary["by_type"].get(alert_type, 0) + 1
    
    return summary

@app.delete("/alerts/{alert_id}")
async def delete_alert(alert_id: str):
    """Delete an alert."""
    global MOCK_ALERTS
    MOCK_ALERTS = [a for a in MOCK_ALERTS if a["id"] != alert_id]
    return {"message": "Alert deleted successfully"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main_simple:app", host="127.0.0.1", port=9008, reload=True)