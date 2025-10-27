"""
Automatic Continuous Feeder
Feeds 1 row (1 hour) from historical dataset at regular intervals
"""

import requests
import time
from datetime import datetime

API_URL = "http://localhost:8000"

def feed_one_hour():
    """Feed 1 hour from historical dataset"""
    try:
        response = requests.post(
            f"{API_URL}/measurement/feed-from-historical",
            params={"num_hours": 1},
            timeout=30
        )
        
        result = response.json()
        
        if response.status_code == 200:
            if result.get("status") == "success":
                timestamp = datetime.now().strftime("%H:%M:%S")
                print(f"[{timestamp}] ✅ Added 1 hour | Window end: {result['new_window_end']}")
                return True
            elif result.get("status") == "no_more_data":
                print(f"\n⚠️  No more data available in historical CSV")
                print(f"   {result.get('message')}")
                return False
        else:
            print(f"❌ Error: {result.get('detail')}")
            return True  # Continue trying
            
    except requests.exceptions.ConnectionError:
        print("❌ Connection Error! Is the API server running?")
        return True  # Continue trying
    except Exception as e:
        print(f"❌ Error: {e}")
        return True  # Continue trying

def main():
    """Main continuous feeding loop"""
    print("=" * 70)
    print("  CONTINUOUS AUTO-FEEDER")
    print("=" * 70)
    print("📥 Feeding 1 hour from historical dataset every 5 seconds")
    print("Press Ctrl+C to stop")
    print("=" * 70)
    print()
    
    interval = 5  # seconds between feeds
    count = 0
    
    try:
        while True:
            count += 1
            print(f"\n[Feed #{count}]", end=" ")
            
            should_continue = feed_one_hour()
            
            if not should_continue:
                print("\n🛑 Stopping - no more data available")
                break
            
            # Wait before next feed
            time.sleep(interval)
            
    except KeyboardInterrupt:
        print("\n\n🛑 Stopped by user")
        print(f"Total feeds: {count}")

if __name__ == "__main__":
    main()
