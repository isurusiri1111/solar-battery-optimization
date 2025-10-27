import requests
import json

# Batch add 24 hours of May 3rd data
url = "http://localhost:8000/measurement/batch"

# Data from your CSV (May 3, 2016) - only timestamp and Power(W)
measurements = [
    {"timestamp": "2016-05-03 00:00:00", "power_W": 0},
    {"timestamp": "2016-05-03 01:00:00", "power_W": 0},
    {"timestamp": "2016-05-03 02:00:00", "power_W": 0},
    {"timestamp": "2016-05-03 03:00:00", "power_W": 0},
    {"timestamp": "2016-05-03 04:00:00", "power_W": 0},
    {"timestamp": "2016-05-03 05:00:00", "power_W": 0},
    {"timestamp": "2016-05-03 06:00:00", "power_W": 828.18},
    {"timestamp": "2016-05-03 07:00:00", "power_W": 3206.67},
    {"timestamp": "2016-05-03 08:00:00", "power_W": 6438.83},
    {"timestamp": "2016-05-03 09:00:00", "power_W": 6675.75},
    {"timestamp": "2016-05-03 10:00:00", "power_W": 10234.83},
    {"timestamp": "2016-05-03 11:00:00", "power_W": 11003.33},
    {"timestamp": "2016-05-03 12:00:00", "power_W": 9288.42},
    {"timestamp": "2016-05-03 13:00:00", "power_W": 8986.91},
    {"timestamp": "2016-05-03 14:00:00", "power_W": 4043.17},
    {"timestamp": "2016-05-03 15:00:00", "power_W": 1913.83},
    {"timestamp": "2016-05-03 16:00:00", "power_W": 1091.17},
    {"timestamp": "2016-05-03 17:00:00", "power_W": 430.83},
    {"timestamp": "2016-05-03 18:00:00", "power_W": 117},
    {"timestamp": "2016-05-03 19:00:00", "power_W": 0},
    {"timestamp": "2016-05-03 20:00:00", "power_W": 0},
    {"timestamp": "2016-05-03 21:00:00", "power_W": 0},
    {"timestamp": "2016-05-03 22:00:00", "power_W": 0},
    {"timestamp": "2016-05-03 23:00:00", "power_W": 0},
]

data = {
    "measurements": measurements,
    "trigger_optimization": True  # Run optimization after batch import
}

print(f"Adding {len(measurements)} measurements...")
print(f"From: {measurements[0]['timestamp']}")
print(f"To:   {measurements[-1]['timestamp']}")

try:
    response = requests.post(url, json=data)
    
    if response.status_code == 200:
        result = response.json()
        print("\n✅ SUCCESS!")
        print(f"Status: {result['status']}")
        print(f"Total: {result['total']}")
        print(f"Successful: {result['successful']}")
        print("\nWindow will slide forward by 24 hours!")
    else:
        print(f"\n❌ ERROR: {response.status_code}")
        print(response.text)
        
except Exception as e:
    print(f"\n❌ FAILED: {e}")
    print("\n⚠ Is the API server running?")
    print("   Check: http://localhost:8000")
