#!/usr/bin/env python3
"""
DecentralFund DAO - Startup Script
Launches both backend and frontend services
"""

import subprocess
import sys
import time
import os
from pathlib import Path

def check_dependencies():
    """Check if required dependencies are installed"""
    try:
        import fastapi
        import streamlit
        import sqlalchemy
        import web3
        print("✅ All dependencies are installed")
        return True
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("Please run: pip install -r requirements.txt")
        return False

def create_directories():
    """Create necessary directories"""
    directories = [
        "data",
        "logs",
        "artifacts"
    ]
    
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print(f"✅ Created directory: {directory}")

def start_backend():
    """Start the FastAPI backend"""
    print("🚀 Starting DecentralFund DAO Backend...")
    
    backend_cmd = [
        sys.executable, "-m", "uvicorn", 
        "backend.app:app", 
        "--reload", 
        "--host", "0.0.0.0", 
        "--port", "8000",
        "--log-level", "info"
    ]
    
    return subprocess.Popen(backend_cmd, cwd=os.getcwd())

def start_frontend():
    """Start the Streamlit frontend"""
    print("🎨 Starting DecentralFund DAO Frontend...")
    
    frontend_cmd = [
        sys.executable, "-m", "streamlit", 
        "run", "frontend/main.py",
        "--server.port", "8501",
        "--server.address", "0.0.0.0"
    ]
    
    return subprocess.Popen(frontend_cmd, cwd=os.getcwd())

def main():
    """Main startup function"""
    print("🏛️ DecentralFund DAO - World's First Decentralized Mutual Fund")
    print("=" * 60)
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    # Create directories
    create_directories()
    
    # Start services
    try:
        backend_process = start_backend()
        time.sleep(3)  # Wait for backend to start
        
        frontend_process = start_frontend()
        
        print("\n" + "=" * 60)
        print("🎉 DecentralFund DAO is now running!")
        print("=" * 60)
        print("📊 Frontend: http://localhost:8501")
        print("🔧 Backend API: http://localhost:8000")
        print("📚 API Docs: http://localhost:8000/docs")
        print("=" * 60)
        print("Press Ctrl+C to stop all services")
        print("=" * 60)
        
        # Wait for processes
        try:
            backend_process.wait()
        except KeyboardInterrupt:
            print("\n🛑 Shutting down services...")
            backend_process.terminate()
            frontend_process.terminate()
            
            # Wait for graceful shutdown
            backend_process.wait()
            frontend_process.wait()
            
            print("✅ All services stopped")
            
    except Exception as e:
        print(f"❌ Error starting services: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
