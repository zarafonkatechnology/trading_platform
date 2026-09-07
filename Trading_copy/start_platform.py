#!/usr/bin/env python
"""
Complete platform starter
"""

import subprocess
import sys
import time
import webbrowser
import os
from pathlib import Path

def check_services():
    """Check if all services are available"""
    print("🔍 Checking services...")
    
    # Check Python
    print(f"✅ Python: {sys.version}")
    
    # Check project structure
    required_dirs = ['src/core', 'src/api', 'src/mt4_gateway', 'src/services']
    for d in required_dirs:
        if os.path.exists(d):
            print(f"✅ {d}")
        else:
            print(f"⚠️ {d} not found")
    
    # Check MT4 file
    mt4_file = "C:/Users/sifer/AppData/Roaming/MetaQuotes/Terminal/Common/Files/dashboard_data.json"
    if os.path.exists(mt4_file):
        print("✅ MT4 data file found")
    else:
        print("⚠️ MT4 data file not found")

def start_all():
    """Start all services"""
    print("=" * 60)
    print("🚀 Starting Complete Trading Platform")
    print("=" * 60)
    
    # Check services first
    check_services()
    
    print("\n" + "=" * 60)
    print("📊 Starting services...")
    
    processes = []
    
    # Start FastAPI server
    print("📡 Starting API Server...")
    api_process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "src.api.main:app", 
         "--host", "0.0.0.0", "--port", "8000", "--reload"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    processes.append(("API", api_process, 8000))
    time.sleep(2)
    
    # Open browsers
    print("🌐 Opening browser...")
    webbrowser.open("http://localhost:8000/docs")
    webbrowser.open("http://localhost:8000")
    
    print("\n" + "=" * 60)
    print("✅ All services running!")
    print(f"📡 API:       http://localhost:8000")
    print(f"📖 API Docs:  http://localhost:8000/docs")
    print("=" * 60)
    print("\nPress Ctrl+C to stop all services\n")
    
    try:
        # Keep running
        for name, process, port in processes:
            process.wait()
    except KeyboardInterrupt:
        print("\n🛑 Stopping all services...")
        for name, process, port in processes:
            try:
                process.terminate()
                print(f"✅ Stopped {name}")
            except:
                pass
        print("✅ All services stopped!")

if __name__ == "__main__":
    start_all()