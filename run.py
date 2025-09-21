#!/usr/bin/env python3
"""
DecentralFund DAO - Main Application Launcher
Unified script to start all services for the decentralized mutual fund
"""

import os
import sys
import time
import signal
import argparse
import subprocess
import multiprocessing
from pathlib import Path
from typing import List, Dict, Optional
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DecentralFundLauncher:
    """Main launcher for DecentralFund DAO services"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.processes: List[subprocess.Popen] = []
        self.services = {
            'database': self._setup_database,
            'backend': self._start_backend,
            'frontend': self._start_frontend,
            'worker': self._start_worker,
            'redis': self._start_redis,
            'contracts': self._deploy_contracts
        }
        
    def _check_dependencies(self) -> bool:
        """Check if all required dependencies are available"""
        logger.info("🔍 Checking dependencies...")
        
        dependencies = {
            'python': sys.executable,
            'pip': 'pip',
            'streamlit': 'streamlit',
            'uvicorn': 'uvicorn',
            'celery': 'celery',
            'redis-server': 'redis-server'
        }
        
        missing = []
        for name, command in dependencies.items():
            try:
                if name == 'python':
                    # Python is already available
                    continue
                    
                result = subprocess.run(
                    [command, '--version'],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode != 0:
                    missing.append(name)
                else:
                    logger.info(f"✅ {name}: Available")
            except (subprocess.TimeoutExpired, FileNotFoundError):
                missing.append(name)
                logger.warning(f"❌ {name}: Not found")
        
        if missing:
            logger.error(f"Missing dependencies: {', '.join(missing)}")
            logger.info("Please install missing dependencies and try again")
            return False
        
        logger.info("✅ All dependencies satisfied")
        return True
    
    def _setup_environment(self) -> bool:
        """Setup environment variables and configuration"""
        logger.info("⚙️ Setting up environment...")
        
        env_file = self.project_root / '.env'
        if not env_file.exists():
            logger.warning("⚠️ .env file not found, using defaults")
            
            # Create basic .env from template
            env_template = self.project_root / '.env.example'
            if env_template.exists():
                import shutil
                shutil.copy(env_template, env_file)
                logger.info("📝 Created .env from template")
            else:
                self._create_default_env(env_file)
        
        # Load environment variables
        try:
            from dotenv import load_dotenv
            load_dotenv(env_file)
            logger.info("✅ Environment variables loaded")
            return True
        except ImportError:
            logger.warning("python-dotenv not installed, skipping .env loading")
            return True
        except Exception as e:
            logger.error(f"Error loading environment: {str(e)}")
            return False
    
    def _create_default_env(self, env_file: Path):
        """Create default .env file"""
        default_config = """
# DecentralFund DAO Configuration
DATABASE_URL=sqlite:///./decentralfund.db
WEB3_PROVIDER_URL=http://localhost:8545
CHAIN_ID=1337
SECRET_KEY=dev-secret-key-change-in-production
REDIS_URL=redis://localhost:6379
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=INFO
"""
        env_file.write_text(default_config.strip())
        logger.info("📝 Created default .env file")
    
    def _setup_database(self) -> bool:
        """Initialize database"""
        logger.info("🗄️ Setting up database...")
        
        try:
            # Run database migrations
            migration_script = self.project_root / 'scripts' / 'migrate_db.py'
            if migration_script.exists():
                result = subprocess.run([
                    sys.executable, str(migration_script)
                ], cwd=self.project_root, capture_output=True, text=True)
                
                if result.returncode == 0:
                    logger.info("✅ Database initialized successfully")
                    return True
                else:
                    logger.error(f"Database setup failed: {result.stderr}")
                    return False
            else:
                logger.warning("Migration script not found, skipping database setup")
                return True
                
        except Exception as e:
            logger.error(f"Database setup error: {str(e)}")
            return False
    
    def _deploy_contracts(self) -> bool:
        """Deploy smart contracts to local blockchain"""
        logger.info("📝 Deploying smart contracts...")
        
        try:
            deploy_script = self.project_root / 'scripts' / 'deploy_contracts.py'
            if deploy_script.exists():
                result = subprocess.run([
                    sys.executable, str(deploy_script)
                ], cwd=self.project_root, capture_output=True, text=True)
                
                if result.returncode == 0:
                    logger.info("✅ Smart contracts deployed successfully")
                    return True
                else:
                    logger.warning(f"Contract deployment failed: {result.stderr}")
                    logger.info("Continuing without contracts (demo mode)")
                    return True
            else:
                logger.warning("Contract deployment script not found")
                return True
                
        except Exception as e:
            logger.warning(f"Contract deployment error: {str(e)}")
            return True  # Non-critical for demo
    
    def _start_redis(self) -> Optional[subprocess.Popen]:
        """Start Redis server"""
        logger.info("🔄 Starting Redis server...")
        
        try:
            # Check if Redis is already running
            result = subprocess.run(
                ['redis-cli', 'ping'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0 and 'PONG' in result.stdout:
                logger.info("✅ Redis already running")
                return None
            
            # Start Redis server
            process = subprocess.Popen(
                ['redis-server', '--daemonize', 'yes'],
                cwd=self.project_root
            )
            
            # Wait a moment for Redis to start
            time.sleep(2)
            
            # Verify Redis is running
            result = subprocess.run(
                ['redis-cli', 'ping'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                logger.info("✅ Redis server started successfully")
                return process
            else:
                logger.warning("⚠️ Redis server may not be running properly")
                return process
                
        except FileNotFoundError:
            logger.warning("Redis not found, background tasks will be disabled")
            return None
        except Exception as e:
            logger.warning(f"Redis startup error: {str(e)}")
            return None
    
    def _start_backend(self) -> subprocess.Popen:
        """Start FastAPI backend server"""
        logger.info("🚀 Starting backend API server...")
        
        backend_cmd = [
            sys.executable, '-m', 'uvicorn',
            'backend.app:app',
            '--reload',
            '--host', '0.0.0.0',
            '--port', '8000',
            '--log-level', 'info'
        ]
        
        process = subprocess.Popen(
            backend_cmd,
            cwd=self.project_root,
            env=dict(os.environ, PYTHONPATH=str(self.project_root))
        )
        
        logger.info("✅ Backend API server starting on http://localhost:8000")
        return process
    
    def _start_frontend(self) -> subprocess.Popen:
        """Start Streamlit frontend"""
        logger.info("🎨 Starting frontend dashboard...")
        
        frontend_cmd = [
            sys.executable, '-m', 'streamlit',
            'run',
            'frontend/main.py',
            '--server.port', '8501',
            '--server.address', '0.0.0.0',
            '--server.headless', 'true',
            '--browser.gatherUsageStats', 'false'
        ]
        
        process = subprocess.Popen(
            frontend_cmd,
            cwd=self.project_root,
            env=dict(os.environ, PYTHONPATH=str(self.project_root))
        )
        
        logger.info("✅ Frontend dashboard starting on http://localhost:8501")
        return process
    
    def _start_worker(self) -> Optional[subprocess.Popen]:
        """Start Celery background worker"""
        logger.info("👷 Starting background worker...")
        
        try:
            worker_cmd = [
                sys.executable, '-m', 'celery',
                '-A', 'backend.tasks',
                'worker',
                '--loglevel=info',
                '--concurrency=2'
            ]
            
            process = subprocess.Popen(
                worker_cmd,
                cwd=self.project_root,
                env=dict(os.environ, PYTHONPATH=str(self.project_root))
            )
            
            logger.info("✅ Background worker started")
            return process
            
        except Exception as e:
            logger.warning(f"Worker startup failed: {str(e)}")
            return None
    
    def _wait_for_services(self, timeout: int = 30):
        """Wait for services to be ready"""
        logger.info("⏳ Waiting for services to be ready...")
        
        services_to_check = [
            ('Backend API', 'http://localhost:8000/health'),
            ('Frontend', 'http://localhost:8501')
        ]
        
        import requests
        from urllib.parse import urlparse
        
        start_time = time.time()
        
        for service_name, url in services_to_check:
            while time.time() - start_time < timeout:
                try:
                    response = requests.get(url, timeout=2)
                    if response.status_code == 200:
                        logger.info(f"✅ {service_name} is ready")
                        break
                except requests.RequestException:
                    pass
                
                time.sleep(2)
            else:
                logger.warning(f"⚠️ {service_name} not responding after {timeout}s")
    
    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            logger.info(f"\n🛑 Received signal {signum}, shutting down gracefully...")
            self.stop_all()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    def start_all(self, services: List[str] = None) -> bool:
        """Start all or specified services"""
        self._setup_signal_handlers()
        
        if not self._check_dependencies():
            return False
        
        if not self._setup_environment():
            return False
        
        # Determine which services to start
        if services is None:
            services = ['database', 'redis', 'backend', 'frontend', 'worker']
        
        logger.info(f"🚀 Starting DecentralFund DAO services: {', '.join(services)}")
        
        # Start services in order
        for service_name in services:
            if service_name in self.services:
                try:
                    if service_name in ['database', 'contracts']:
                        # These are setup tasks, not persistent services
                        success = self.services[service_name]()
                        if not success:
                            logger.error(f"Failed to setup {service_name}")
                            return False
                    else:
                        # These are persistent services
                        process = self.services[service_name]()
                        if process:
                            self.processes.append(process)
                            
                except Exception as e:
                    logger.error(f"Failed to start {service_name}: {str(e)}")
                    return False
            else:
                logger.warning(f"Unknown service: {service_name}")
        
        # Wait for services to be ready
        if self.processes:
            self._wait_for_services()
            
            logger.info("🎉 DecentralFund DAO is ready!")
            logger.info("📊 Frontend Dashboard: http://localhost:8501")
            logger.info("🔧 Backend API: http://localhost:8000")
            logger.info("📖 API Docs: http://localhost:8000/docs")
            logger.info("Press Ctrl+C to stop all services")
            
            # Keep the main process running
            try:
                while True:
                    # Check if any process has died
                    for i, process in enumerate(self.processes):
                        if process.poll() is not None:
                            logger.warning(f"Process {i} has exited with code {process.returncode}")
                    
                    time.sleep(5)
            except KeyboardInterrupt:
                logger.info("Keyboard interrupt received")
        
        return True
    
    def stop_all(self):
        """Stop all running services"""
        logger.info("🛑 Stopping all services...")
        
        for i, process in enumerate(self.processes):
            try:
                logger.info(f"Stopping process {i}...")
                process.terminate()
                
                # Wait for graceful shutdown
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    logger.warning(f"Force killing process {i}")
                    process.kill()
                    
            except Exception as e:
                logger.error(f"Error stopping process {i}: {str(e)}")
        
        self.processes.clear()
        logger.info("✅ All services stopped")
    
    def status(self):
        """Check status of all services"""
        logger.info("📊 Service Status:")
        
        services_status = [
            ('Backend API', 'http://localhost:8000/health'),
            ('Frontend', 'http://localhost:8501'),
            ('Redis', 'redis://localhost:6379')
        ]
        
        import requests
        
        for service_name, endpoint in services_status:
            try:
                if endpoint.startswith('http'):
                    response = requests.get(endpoint, timeout=5)
                    status = "🟢 Running" if response.status_code == 200 else "🔴 Error"
                elif endpoint.startswith('redis'):
                    result = subprocess.run(['redis-cli', 'ping'], 
                                          capture_output=True, text=True, timeout=5)
                    status = "🟢 Running" if result.returncode == 0 else "🔴 Not Running"
                else:
                    status = "❓ Unknown"
                    
                logger.info(f"  {service_name}: {status}")
                
            except Exception as e:
                logger.info(f"  {service_name}: 🔴 Error - {str(e)}")

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="DecentralFund DAO Launcher")
    parser.add_argument('action', choices=['start', 'stop', 'status', 'demo'], 
                       help='Action to perform')
    parser.add_argument('--services', nargs='+', 
                       choices=['database', 'redis', 'backend', 'frontend', 'worker', 'contracts'],
                       help='Specific services to start')
    parser.add_argument('--dev', action='store_true', 
                       help='Start in development mode')
    
    args = parser.parse_args()
    
    launcher = DecentralFundLauncher()
    
    if args.action == 'start':
        services = args.services if args.services else None
        success = launcher.start_all(services)
        sys.exit(0 if success else 1)
        
    elif args.action == 'stop':
        launcher.stop_all()
        
    elif args.action == 'status':
        launcher.status()
        
    elif args.action == 'demo':
        logger.info("🎭 Starting DecentralFund DAO in demo mode...")
        
        # Setup demo data first
        demo_script = Path(__file__).parent / 'scripts' / 'seed_demo_data.py'
        if demo_script.exists():
            subprocess.run([sys.executable, str(demo_script)])
        
        # Start all services
        success = launcher.start_all()
        sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()