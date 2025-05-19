#!/usr/bin/env python
# Main entry point for SpottyCloud distributed computing system

import argparse
import os
import sys
import logging
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from core.orchestrator.manager import OrchestratorManager
from utils.monitoring.system_monitor import SystemMonitor
from dashboard.backend.server import start_dashboard_server
from config.loader import ConfigLoader

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("spotty_cloud.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("spotty_cloud")

def parse_args():
    """
    Parse command line arguments
    """
    parser = argparse.ArgumentParser(description="SpottyCloud - Distributed Computing on AWS Spot Instances")
    parser.add_argument("--config", type=str, default="config/default.yaml", 
                        help="Path to configuration file")
    parser.add_argument("--dashboard-only", action="store_true", 
                        help="Start only the dashboard without the orchestrator")
    parser.add_argument("--port", type=int, default=8080,
                        help="Port for the dashboard server")
    parser.add_argument("--log-level", type=str, choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                        default="INFO", help="Logging level")
    return parser.parse_args()

def main():
    """
    Main entry point for the application
    """
    # Parse command line arguments
    args = parse_args()
    
    # Set log level
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    # Load configuration
    config_path = os.path.join(os.path.dirname(__file__), args.config)
    logger.info(f"Loading configuration from {config_path}")
    config = ConfigLoader.load(config_path)
    
    # Start dashboard server in a separate thread
    logger.info(f"Starting dashboard server on port {args.port}")
    dashboard_thread = start_dashboard_server(port=args.port, config=config)
    
    # If dashboard-only mode, just wait for the dashboard thread
    if args.dashboard_only:
        logger.info("Running in dashboard-only mode")
        dashboard_thread.join()
        return
    
    try:
        # Start system monitoring
        logger.info("Starting system monitoring")
        system_monitor = SystemMonitor(config)
        system_monitor.start()
        
        # Initialize and start orchestrator
        logger.info("Initializing orchestrator")
        orchestrator = OrchestratorManager(config)
        logger.info("Starting orchestrator")
        orchestrator.start()
        
        # Wait for orchestrator to complete
        orchestrator.wait()
        
    except KeyboardInterrupt:
        logger.info("Received shutdown signal, stopping services...")
    except Exception as e:
        logger.error(f"Error in main process: {str(e)}", exc_info=True)
    finally:
        # Clean shutdown of all components
        logger.info("Shutting down components...")
        if 'orchestrator' in locals():
            orchestrator.stop()
        if 'system_monitor' in locals():
            system_monitor.stop()
        logger.info("Shutdown complete")

if __name__ == "__main__":
    main()
