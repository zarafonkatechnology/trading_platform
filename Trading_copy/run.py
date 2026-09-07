#!/usr/bin/env python
"""
Unified launcher for the complete trading platform
"""

import os
import sys
import asyncio
import subprocess
import webbrowser
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

def check_dependencies():
    """Check if all dependencies are installed"""
    try:
        import fastapi
        import uvicorn
        import sqlalchemy
        return True
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("Run: pip install -r requirements.txt")
        return False

def start_dashboard():
    """Start the forex dashboard"""
    dashboard_path = Path(__file__).parent.parent / "forex_dashboard.py"
    if dashboard_path.exists():
        print("📊 Starting Dashboard...")
        return subprocess.Popen(
            [sys.executable, str(dashboard_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
    print("⚠️ Dashboard not found at:", dashboard_path)
    return None

def start_api():
    """Start the FastAPI server"""
    print("🔌 Starting API Server...")
    return subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "src.api.main:app", 
         "--host", "0.0.0.0", "--port", "8000", "--reload"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

def main():
    """Main entry point"""
    print("🚀 Starting Trading Platform...")
    print("=" * 50)
    
    # Check dependencies
    if not check_dependencies():
        return
    
    # Start services
    services = []
    
    # Start Dashboard
    dashboard = start_dashboard()
    if dashboard:
        services.append(("Dashboard", dashboard))
    
    # Start API
    api = start_api()
    services.append(("API", api))
    
    # Wait for services to start
    print("⏳ Waiting for services to start...")
    time.sleep(3)
    
    # Open browser
    print("🌐 Opening browser...")
    webbrowser.open("http://localhost:5002")
    webbrowser.open("http://localhost:8000/docs")
    
    print("""
    ✅ Trading Platform is running!
    
    📊 Dashboard:  http://localhost:5002
    📡 API:        http://localhost:8000
    📖 API Docs:   http://localhost:8000/docs
    
    Press Ctrl+C to stop
    """)
    
    try:
        # Wait for processes
        for name, process in services:
            process.wait()
    except KeyboardInterrupt:
        print("\n🛑 Stopping services...")
        for name, process in services:
            try:
                process.terminate()
                print(f"✅ Stopped {name}")
            except:
                pass
        print("✅ All services stopped!")

if __name__ == "__main__":
    main()