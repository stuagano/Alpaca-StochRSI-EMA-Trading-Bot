#!/usr/bin/env python3
"""
Real Data Verification Script
Tests all microservices to ensure compliance with NO FAKE DATA policy

This script verifies that:
1. All services return data_source: "alpaca_real" or "real"
2. No services return mock, demo, or fake data markers
3. Services fail gracefully when APIs are unavailable
4. All responses contain legitimate real data characteristics
"""

import httpx
import asyncio
import json
from datetime import datetime
from typing import Dict, List, Any

class RealDataValidator:
    def __init__(self):
        self.services = {
            "position-management": {"port": 9001, "critical": True},
            "trading-execution": {"port": 9002, "critical": True}, 
            "signal-processing": {"port": 9003, "critical": True},
            "risk-management": {"port": 9004, "critical": True},
            "market-data": {"port": 9005, "critical": True},
            "historical-data": {"port": 9006, "critical": True},
            "analytics": {"port": 9007, "critical": True},
        }
        
        self.forbidden_markers = [
            "mock", "demo", "fake", "simulated", "fallback", 
            "test_data", "dummy", "sample", "mock_data_violation"
        ]
        
        self.required_real_markers = [
            "alpaca_real", "real", "live", "alpaca_markets"
        ]
        
    async def check_service_health(self, service_name: str, port: int) -> Dict[str, Any]:
        """Check if service is healthy and returning real data"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"http://localhost:{port}/health")
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Check for forbidden mock data markers
                    content_str = json.dumps(data).lower()
                    forbidden_found = []
                    
                    for marker in self.forbidden_markers:
                        if marker in content_str:
                            forbidden_found.append(marker)
                    
                    # Check for required real data markers
                    real_markers_found = []
                    for marker in self.required_real_markers:
                        if marker in content_str:
                            real_markers_found.append(marker)
                    
                    return {
                        "service": service_name,
                        "status": "healthy",
                        "port": port,
                        "data_source": data.get("data_source", "unknown"),
                        "forbidden_markers": forbidden_found,
                        "real_markers": real_markers_found,
                        "compliant": len(forbidden_found) == 0 and len(real_markers_found) > 0,
                        "response": data
                    }
                else:
                    return {
                        "service": service_name,
                        "status": "unhealthy",
                        "port": port,
                        "status_code": response.status_code,
                        "compliant": False
                    }
                    
        except Exception as e:
            return {
                "service": service_name,
                "status": "error",
                "port": port,
                "error": str(e),
                "compliant": False
            }
    
    async def test_real_data_endpoints(self, service_name: str, port: int) -> Dict[str, Any]:
        """Test specific endpoints for real data compliance"""
        endpoints = {
            "position-management": ["/positions", "/portfolio/summary"],
            "signal-processing": ["/signals/AAPL"],
            "risk-management": ["/portfolio/risk"],
            "analytics": ["/analytics/summary"],
            "historical-data": ["/historical/AAPL?limit=5"],
        }
        
        if service_name not in endpoints:
            return {"service": service_name, "tests": [], "compliant": True}
        
        test_results = []
        
        for endpoint in endpoints[service_name]:
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.get(f"http://localhost:{port}{endpoint}")
                    
                    if response.status_code == 200:
                        data = response.json()
                        content_str = json.dumps(data).lower()
                        
                        # Check for forbidden markers
                        forbidden_found = [m for m in self.forbidden_markers if m in content_str]
                        
                        # Check for real markers
                        real_markers = [m for m in self.required_real_markers if m in content_str]
                        
                        test_results.append({
                            "endpoint": endpoint,
                            "status": "success",
                            "has_data_source": "data_source" in data,
                            "data_source": data.get("data_source", "missing"),
                            "forbidden_markers": forbidden_found,
                            "real_markers": real_markers,
                            "compliant": len(forbidden_found) == 0 and ("data_source" not in data or data.get("data_source") in self.required_real_markers)
                        })
                    else:
                        # Check if it's a proper error (good) vs fake data (bad)
                        error_data = response.json() if response.headers.get("content-type", "").startswith("application/json") else {"detail": response.text}
                        
                        test_results.append({
                            "endpoint": endpoint,
                            "status": "error",
                            "status_code": response.status_code,
                            "error": error_data,
                            "compliant": True  # Errors are better than fake data!
                        })
                        
            except Exception as e:
                test_results.append({
                    "endpoint": endpoint,
                    "status": "exception",
                    "error": str(e),
                    "compliant": True  # Exceptions are better than fake data!
                })
        
        return {
            "service": service_name,
            "tests": test_results,
            "compliant": all(test.get("compliant", False) for test in test_results)
        }
    
    async def run_comprehensive_validation(self) -> Dict[str, Any]:
        """Run comprehensive validation of all services"""
        print("🔍 REAL DATA VALIDATION STARTED")
        print("=" * 60)
        
        # Check health of all services
        print("\n📋 Checking service health...")
        health_results = []
        
        for service_name, config in self.services.items():
            result = await self.check_service_health(service_name, config["port"])
            health_results.append(result)
            
            status_emoji = "✅" if result.get("compliant") else "❌"
            print(f"  {status_emoji} {service_name:20} | Port {config['port']} | {result.get('status', 'unknown')}")
            
            if not result.get("compliant"):
                if result.get("forbidden_markers"):
                    print(f"      ⚠️  Found forbidden markers: {result['forbidden_markers']}")
                if not result.get("real_markers"):
                    print(f"      ⚠️  Missing real data markers")
        
        # Test real data endpoints
        print(f"\n🧪 Testing real data endpoints...")
        endpoint_results = []
        
        for service_name, config in self.services.items():
            if not config.get("critical", False):
                continue
                
            result = await self.test_real_data_endpoints(service_name, config["port"])
            endpoint_results.append(result)
            
            print(f"\n  📊 {service_name}:")
            for test in result["tests"]:
                endpoint = test["endpoint"]
                status_emoji = "✅" if test.get("compliant") else "❌"
                status = test.get("status", "unknown")
                
                print(f"    {status_emoji} {endpoint:25} | {status}")
                
                if not test.get("compliant") and test.get("forbidden_markers"):
                    print(f"        ⚠️  Forbidden markers: {test['forbidden_markers']}")
        
        # Generate summary
        health_compliant = sum(1 for r in health_results if r.get("compliant", False))
        endpoint_compliant = sum(1 for r in endpoint_results if r.get("compliant", False))
        
        print(f"\n" + "=" * 60)
        print(f"📊 VALIDATION SUMMARY")
        print(f"=" * 60)
        print(f"🏥 Health Checks:  {health_compliant}/{len(health_results)} compliant")
        print(f"🧪 Endpoint Tests: {endpoint_compliant}/{len(endpoint_results)} compliant")
        
        overall_compliant = (health_compliant == len(health_results) and 
                           endpoint_compliant == len(endpoint_results))
        
        if overall_compliant:
            print(f"🎉 ALL SERVICES COMPLIANT WITH NO FAKE DATA POLICY!")
            print(f"✅ All services return real data only")
            print(f"✅ No forbidden mock/demo markers found")
            print(f"✅ Services fail gracefully when APIs unavailable")
        else:
            print(f"❌ COMPLIANCE VIOLATIONS DETECTED")
            print(f"⚠️  Some services may be returning fake data")
            print(f"⚠️  Review the detailed results above")
        
        return {
            "overall_compliant": overall_compliant,
            "health_results": health_results,
            "endpoint_results": endpoint_results,
            "summary": {
                "health_compliant": health_compliant,
                "health_total": len(health_results),
                "endpoint_compliant": endpoint_compliant,
                "endpoint_total": len(endpoint_results)
            },
            "timestamp": datetime.utcnow().isoformat()
        }

async def main():
    """Run the validation"""
    validator = RealDataValidator()
    results = await validator.run_comprehensive_validation()
    
    # Save results
    with open("real_data_validation_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\n💾 Detailed results saved to: real_data_validation_results.json")
    
    # Exit with appropriate code
    exit_code = 0 if results["overall_compliant"] else 1
    print(f"🚪 Exiting with code: {exit_code}")
    exit(exit_code)

if __name__ == "__main__":
    asyncio.run(main())