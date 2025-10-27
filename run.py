import subprocess
import time
import sys
import requests
from pathlib import Path

def check_api_status():
    """Check if API is responding"""
    try:
        response = requests.get("http://localhost:8000", timeout=5)
        return response.status_code == 200
    except:
        return False

def start_server():
    """Start the FastAPI server"""
    print("="*70)
    print("  🌞 SOLAR + BATTERY OPTIMIZATION SYSTEM")
    print("="*70)
    print()
    print("🚀 Starting API server on port 8000...")
    print("   Please wait 10-30 seconds for initialization...")
    print()
    
    # Debug logging
    import sys
    sys.stdout.flush()  # Ensure prints are shown immediately
    
    # Start the server in a subprocess
    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "api_server:app", "--host", "0.0.0.0", "--port", "8000"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # Capture initial output
    try:
        stdout, stderr = process.communicate(timeout=1)
        if stdout:
            print("\nServer Output:", stdout)
        if stderr:
            print("\nServer Error:", stderr)
    except subprocess.TimeoutExpired:
        pass  # This is expected as the server keeps running
    
    # Wait for server to start
    max_attempts = 30
    for i in range(max_attempts):
        if check_api_status():
            print()
            print("="*70)
            print("  ✅ SYSTEM READY!")
            print("="*70)
            print()
            print("📍 Access Points:")
            print("   • API Server:  http://localhost:8000")
            print("   • API Docs:    http://localhost:8000/docs")
            print("   • Dashboard:   Open dashboard.html in your browser")
            print()
            print("⚠️  Press Ctrl+C to stop the server")
            print("="*70)
            print()
            
            # Keep running
            try:
                process.wait()
            except KeyboardInterrupt:
                print("\n\n🛑 Shutting down server...")
                process.terminate()
                process.wait()
                print("✓ Server stopped. Goodbye!")
            
            return
        
        print(".", end="", flush=True)
        time.sleep(1)
    
    print("\n\n❌ Server failed to start. Check for errors above.")
    process.terminate()

if __name__ == "__main__":
    start_server()