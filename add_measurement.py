import requests
import json

# Add one measurement via API
url = "http://localhost:8000/measurement/add"

data = {
    "timestamp": "2016-05-03 00:00:00",  # Correct format: YYYY-MM-DD HH:MM:SS
    "power_W": 0,  # Your actual power value
    "trigger_optimization": False
}

print("Adding measurement...")
print(f"Timestamp: {data['timestamp']}")
print(f"Power: {data['power_W']} W")

try:
    response = requests.post(url, json=data)
    
    if response.status_code == 200:
        result = response.json()
        print("\n✅ SUCCESS!")
        print(json.dumps(result, indent=2))
    else:
        print(f"\n❌ ERROR: {response.status_code}")
        print(response.text)
        
except Exception as e:
    print(f"\n❌ FAILED: {e}")
    print("\n⚠ Is the API server running?")
    print("   Check: http://localhost:8000")
