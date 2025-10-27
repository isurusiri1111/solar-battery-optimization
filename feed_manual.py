"""
Manual Feed Script - Feed 1 hour at a time when YOU press Enter
"""

import requests
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
                print(f"✅ [{timestamp}] Added 1 hour | Window end: {result['new_window_end']}")
                return True
            elif result.get("status") == "no_more_data":
                print(f"\n⚠️  No more data available in CSV")
                print(f"   {result.get('message')}")
                return False
        else:
            print(f"❌ Error: {result.get('detail')}")
            return True
            
    except requests.exceptions.ConnectionError:
        print("❌ Connection Error! Server not running?")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    """Manual feeding - press Enter to feed"""
    print("=" * 70)
    print("  MANUAL FEED - Press Enter to feed 1 hour")
    print("=" * 70)
    print("Commands:")
    print("  - Press ENTER → Feed 1 hour")
    print("  - Type 'q' and press ENTER → Quit")
    print("=" * 70)
    print()
    
    count = 0
    
    try:
        while True:
            user_input = input("\nPress Enter to feed next hour (or 'q' to quit): ").strip().lower()
            
            if user_input == 'q':
                print("\n👋 Goodbye!")
                break
            
            # Feed one hour
            count += 1
            print(f"\n[Feed #{count}]", end=" ")
            
            success = feed_one_hour()
            
            if not success:
                print("\n🛑 Cannot continue")
                break
                
    except KeyboardInterrupt:
        print("\n\n🛑 Stopped by user")
    
    print(f"\nTotal feeds: {count}")

if __name__ == "__main__":
    main()
