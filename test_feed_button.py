"""
Quick test script for the feed-from-historical endpoint
This simulates what the dashboard button does
"""

import requests
import json

API_URL = "http://localhost:8000"

def test_feed_endpoint():
    """Test feeding hours from historical dataset"""
    
    print("=" * 60)
    print("Testing Feed from Historical Dataset")
    print("=" * 60)
    
    # Test with 24 hours
    num_hours = 24
    
    print(f"\n📥 Requesting to feed {num_hours} hours from dataset...")
    
    try:
        response = requests.post(
            f"{API_URL}/measurement/feed-from-historical",
            params={"num_hours": num_hours},
            timeout=30
        )
        
        result = response.json()
        
        if response.status_code == 200:
            if result.get("status") == "success":
                print(f"\n✅ SUCCESS!")
                print(f"   • Rows added: {result['rows_added']}")
                print(f"   • New window end: {result['new_window_end']}")
                
                if result.get('details'):
                    print(f"\n📋 Added timestamps:")
                    for timestamp in result['details']:
                        print(f"   • {timestamp}")
                
                print(f"\n🎉 Window successfully advanced by {num_hours} hours!")
                
            elif result.get("status") == "no_more_data":
                print(f"\n⚠️  No more data available")
                print(f"   Message: {result.get('message')}")
                print(f"   Current end: {result.get('current_end')}")
                
        else:
            print(f"\n❌ Error {response.status_code}")
            print(f"   Detail: {result.get('detail', 'Unknown error')}")
            
    except requests.exceptions.ConnectionError:
        print("\n❌ Connection Error!")
        print("   Is the API server running?")
        print("   Run: python -m uvicorn api_server:app --host 0.0.0.0 --port 8000")
        
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")

if __name__ == "__main__":
    test_feed_endpoint()
