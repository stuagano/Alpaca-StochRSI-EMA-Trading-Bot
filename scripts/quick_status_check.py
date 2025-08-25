#!/usr/bin/env python3
"""
Quick Status Check for All Microservices
"""

import requests
import json
from datetime import datetime

services = [
    ("Frontend", "http://localhost:9100"),
    ("API Gateway", "http://localhost:9000"), 
    ("Position Management", "http://localhost:9001"),
    ("Trading Execution", "http://localhost:9002"),
    ("Signal Processing", "http://localhost:9003"),
    ("Risk Management", "http://localhost:9004"),
    ("Market Data", "http://localhost:9005"),
    ("Historical Data", "http://localhost:9006"),
    ("Training Service", "http://localhost:9011")
]

def check_service(name, url):
    try:
        response = requests.get(f"{url}/health", timeout=3)
        if response.status_code == 200:
            return "🟢 ONLINE"
        else:
            return f"🔴 ERROR ({response.status_code})"
    except Exception as e:
        return f"🔴 OFFLINE"

print("🚀 MICROSERVICES QUICK STATUS CHECK")
print("=" * 50)
print(f"Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
print("=" * 50)

online_count = 0
for name, url in services:
    status = check_service(name, url)
    if "ONLINE" in status:
        online_count += 1
    print(f"{name:20} | {status}")

print("=" * 50)
print(f"Services Online: {online_count}/{len(services)} ({online_count/len(services)*100:.0f}%)")

if online_count == len(services):
    print("🎉 ALL MICROSERVICES OPERATIONAL!")
elif online_count >= len(services) * 0.8:
    print("✅ System mostly operational")
else:
    print("⚠️ Multiple services down - attention required")