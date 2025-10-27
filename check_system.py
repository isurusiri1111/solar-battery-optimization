import requests
import json

print("="*70)
print("  SYSTEM DIAGNOSTIC")
print("="*70)

# Test 1: Server alive?
print("\n1. Testing API server connection...")
try:
    response = requests.get("http://localhost:8000", timeout=5)
    print("   ✅ Server is running!")
    print(f"   Response: {response.json()['status']}")
except Exception as e:
    print(f"   ❌ Server not responding: {e}")
    print("   → Start server: python -m uvicorn api_server:app --host 0.0.0.0 --port 8000")
    exit()

# Test 2: System status
print("\n2. Checking system status...")
try:
    response = requests.get("http://localhost:8000/status")
    status = response.json()
    
    if status['predictor']['initialized']:
        print("   ✅ System initialized")
        print(f"   Window: {status['predictor']['window_size']} hours")
        print(f"   Start: {status['predictor']['window_start']}")
        print(f"   End: {status['predictor']['window_end']}")
        print(f"   Next expected: {status['predictor']['next_expected']}")
    else:
        print("   ⚠ System not initialized")
        print("   → Go to Tab 1 and click 'Initialize'")
        
except Exception as e:
    print(f"   ❌ Failed: {e}")

# Test 3: Try adding measurement
print("\n3. Testing measurement add...")
try:
    data = {
        "timestamp": "2016-05-03 00:00:00",
        "power_W": 0,
        "trigger_optimization": False
    }
    
    response = requests.post("http://localhost:8000/measurement/add", json=data)
    
    if response.status_code == 200:
        result = response.json()
        print("   ✅ Measurement added successfully!")
        print(f"   Status: {result['status']}")
        if result['status'] == 'updated' and 'result' in result:
            print(f"   New window end: {result['result'].get('window_end', 'N/A')}")
    else:
        print(f"   ❌ Failed: {response.status_code}")
        print(f"   {response.text}")
        
except Exception as e:
    print(f"   ❌ Failed: {e}")

print("\n" + "="*70)
print("  DIAGNOSTIC COMPLETE")
print("="*70)
