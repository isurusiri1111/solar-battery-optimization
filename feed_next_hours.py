import requests
import json

# Feed next rows from historical dataset
url = "http://localhost:8000/measurement/feed-from-historical"

# You can change num_hours to feed more data at once (1-24)
num_hours = 24  # Feed 24 hours of data

print(f"Feeding next {num_hours} hours from historical dataset...")

try:
    response = requests.post(f"{url}?num_hours={num_hours}")
    
    if response.status_code == 200:
        result = response.json()
        print("\n✅ SUCCESS!")
        print(f"Status: {result['status']}")
        
        if result['status'] == 'success':
            print(f"Rows added: {result['rows_added']}/{result['total_attempted']}")
            print(f"New window end: {result['new_window_end']}")
            print("\n📊 Window has slid forward!")
            print("   - Predictions automatically updated")
            print("   - Ready for optimization")
        elif result['status'] == 'no_more_data':
            print(f"⚠ {result['message']}")
            print(f"Current end: {result['current_end']}")
    else:
        print(f"\n❌ ERROR: {response.status_code}")
        print(response.text)
        
except Exception as e:
    print(f"\n❌ FAILED: {e}")
    print("\n⚠ Is the API server running?")
    print("   Start it: python -m uvicorn api_server:app --host 0.0.0.0 --port 8000")
