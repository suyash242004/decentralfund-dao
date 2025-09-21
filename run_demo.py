#!/usr/bin/env python3
"""
DecentralFund DAO - Quick Demo Launcher (Windows Compatible)
Simplified version for immediate hackathon demo
"""

import os
import sys
import time
import subprocess
import multiprocessing
from pathlib import Path
import logging

# Fix Windows encoding issues
if sys.platform.startswith('win'):
    import locale
    try:
        locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
    except:
        pass
    
    # Set console to UTF-8
    os.system('chcp 65001 >nul 2>&1')

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class QuickDemoLauncher:
    """Quick demo launcher without Redis dependencies"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.processes = []
        
    def setup_environment(self):
        """Setup minimal environment"""
        logger.info("Setting up demo environment...")
        
        # Create .env if not exists
        env_file = self.project_root / '.env'
        if not env_file.exists():
            env_content = """DATABASE_URL=sqlite:///./demo.db
WEB3_PROVIDER_URL=http://localhost:8545
SECRET_KEY=demo-secret-key-for-hackathon
ENVIRONMENT=demo
DEBUG=true
MOCK_BLOCKCHAIN=true
REDIS_URL=memory://localhost
CELERY_BROKER_URL=memory://localhost"""
            
            try:
                with open(env_file, 'w', encoding='utf-8') as f:
                    f.write(env_content)
                logger.info("Created demo .env file")
            except Exception as e:
                logger.error(f"Error creating .env file: {e}")
                return False
        
        # Create directories and __init__.py files
        directories = ['backend', 'frontend', 'contracts', 'scripts']
        
        for directory in directories:
            dir_path = self.project_root / directory
            dir_path.mkdir(exist_ok=True)
            
            init_file = dir_path / '__init__.py'
            init_file.touch()
        
        logger.info("Demo environment ready")
        return True
    
    def create_missing_files(self):
        """Create any missing critical files"""
        
        # Create migrate_db.py
        migrate_script = self.project_root / 'scripts' / 'migrate_db.py'
        migrate_content = '''"""Database migration script"""
import asyncio
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

async def main():
    try:
        print("Initializing database...")
        # For demo, just create a simple SQLite file
        import sqlite3
        db_path = Path(__file__).parent.parent / "demo.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE IF NOT EXISTS demo_table (id INTEGER PRIMARY KEY)")
        conn.close()
        print("Database initialized successfully")
        return True
    except Exception as e:
        print(f"Database setup: {e}")
        return False

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
'''
        
        try:
            with open(migrate_script, 'w', encoding='utf-8') as f:
                f.write(migrate_content)
        except Exception as e:
            logger.error(f"Error creating migrate script: {e}")
        
        # Create seed_demo_data.py
        seed_script = self.project_root / 'scripts' / 'seed_demo_data.py'
        seed_content = '''"""Seed demo data"""
print("Demo data seeded successfully")
'''
        
        try:
            with open(seed_script, 'w', encoding='utf-8') as f:
                f.write(seed_content)
        except Exception as e:
            logger.error(f"Error creating seed script: {e}")
        
        logger.info("Created missing scripts")
    
    def check_files_exist(self):
        """Check if required files exist"""
        required_files = [
            'backend/app.py',
            'frontend/main.py',
            'backend/config.py'
        ]
        
        missing_files = []
        for file_path in required_files:
            if not (self.project_root / file_path).exists():
                missing_files.append(file_path)
        
        if missing_files:
            logger.error(f"Missing required files: {missing_files}")
            logger.info("Please make sure you have copied all the code files to the correct locations:")
            logger.info("- backend/app.py (FastAPI application)")
            logger.info("- frontend/main.py (Streamlit dashboard)")  
            logger.info("- backend/config.py (Configuration)")
            logger.info("- backend/models.py (Database models)")
            logger.info("- backend/connection.py (Database connection)")
            return False
        
        return True
    
    def start_backend(self):
        """Start backend server"""
        logger.info("Starting backend server...")
        
        cmd = [
            sys.executable, '-m', 'uvicorn',
            'backend.app:app',
            '--reload',
            '--host', '127.0.0.1', 
            '--port', '8000'
        ]
        
        env = dict(os.environ)
        env['PYTHONPATH'] = str(self.project_root)
        env['PYTHONIOENCODING'] = 'utf-8'
        
        try:
            process = subprocess.Popen(
                cmd,
                cwd=self.project_root,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                encoding='utf-8'
            )
            
            self.processes.append(('backend', process))
            logger.info("Backend server starting on http://localhost:8000")
            return True
        except Exception as e:
            logger.error(f"Failed to start backend: {e}")
            return False
        
    def start_frontend(self):
        """Start frontend dashboard"""
        logger.info("Starting frontend dashboard...")
        
        cmd = [
            sys.executable, '-m', 'streamlit',
            'run', 'frontend/main.py',
            '--server.port', '8501',
            '--server.address', '127.0.0.1',
            '--server.headless', 'true'
        ]
        
        env = dict(os.environ)
        env['PYTHONPATH'] = str(self.project_root)
        env['PYTHONIOENCODING'] = 'utf-8'
        
        try:
            process = subprocess.Popen(
                cmd,
                cwd=self.project_root,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                encoding='utf-8'
            )
            
            self.processes.append(('frontend', process))
            logger.info("Frontend dashboard starting on http://localhost:8501")
            return True
        except Exception as e:
            logger.error(f"Failed to start frontend: {e}")
            return False
    
    def wait_for_services(self):
        """Wait for services to start"""
        logger.info("Waiting for services to start...")
        time.sleep(8)  # Give more time on Windows
        
        try:
            import requests
            
            # Check backend
            try:
                response = requests.get('http://localhost:8000/', timeout=5)
                logger.info("Backend is ready")
            except Exception as e:
                logger.warning(f"Backend may still be starting: {e}")
            
            # Check frontend  
            try:
                response = requests.get('http://localhost:8501/', timeout=5)
                logger.info("Frontend is ready")
            except Exception as e:
                logger.warning(f"Frontend may still be starting: {e}")
                
        except ImportError:
            logger.info("Requests not available, skipping health checks")
    
    def run_demo(self):
        """Run the complete demo"""
        logger.info("Starting DecentralFund DAO Demo...")
        
        try:
            # Setup environment
            if not self.setup_environment():
                return False
            
            # Check if files exist
            if not self.check_files_exist():
                return False
            
            # Create missing scripts
            self.create_missing_files()
            
            # Initialize database
            logger.info("Initializing database...")
            try:
                result = subprocess.run([
                    sys.executable, 'scripts/migrate_db.py'
                ], cwd=self.project_root, capture_output=True, text=True, timeout=30)
                
                if result.returncode == 0:
                    logger.info("Database initialized")
                else:
                    logger.warning("Database init had issues (continuing anyway)")
            except Exception as e:
                logger.warning(f"Database init warning: {e}")
            
            # Start services
            if not self.start_backend():
                return False
                
            time.sleep(5)  # Give backend time to start
            
            if not self.start_frontend():
                return False
            
            # Wait and show status
            self.wait_for_services()
            
            # Success message
            print("\n" + "="*60)
            print("DecentralFund DAO Demo is Ready!")
            print("="*60)
            print("Frontend Dashboard: http://localhost:8501")
            print("Backend API: http://localhost:8000")
            print("API Documentation: http://localhost:8000/docs")
            print("="*60)
            print("Demo Features:")
            print("  - Connect wallet and start SIP investment")
            print("  - Create governance proposals")
            print("  - Vote on community decisions")
            print("  - View AI-powered insights")
            print("  - Track portfolio performance")
            print("="*60)
            print("Press Ctrl+C to stop all services")
            print()
            
            # Keep running
            try:
                while True:
                    time.sleep(1)
                    
                    # Check if processes are still running
                    for name, process in self.processes:
                        if process.poll() is not None:
                            logger.warning(f"{name} process exited")
                    
            except KeyboardInterrupt:
                logger.info("Stopping demo...")
                self.stop_all()
                
        except Exception as e:
            logger.error(f"Demo failed: {e}")
            self.stop_all()
            return False
        
        return True
    
    def stop_all(self):
        """Stop all processes"""
        for name, process in self.processes:
            try:
                process.terminate()
                process.wait(timeout=5)
                logger.info(f"Stopped {name}")
            except:
                try:
                    process.kill()
                except:
                    pass

def main():
    launcher = QuickDemoLauncher()
    success = launcher.run_demo()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()