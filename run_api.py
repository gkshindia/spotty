#!/usr/bin/env python
# Start script for SpottyCloud FastAPI application

import argparse
import os
import sys
import uvicorn
from pathlib import Path

def parse_args():
    """
    Parse command line arguments for SpottyCloud FastAPI app
    """
    parser = argparse.ArgumentParser(description="SpottyCloud FastAPI Application")
    parser.add_argument("--host", type=str, default="0.0.0.0",
                        help="Host to bind the server to")
    parser.add_argument("--port", type=int, default=8000,
                        help="Port to bind the server to")
    parser.add_argument("--reload", action="store_true",
                        help="Enable auto-reload for development")
    parser.add_argument("--workers", type=int, default=1,
                        help="Number of worker processes")
    parser.add_argument("--env-file", type=str, default=None,
                        help="Path to .env file for environment variables")
    parser.add_argument("--log-level", type=str, default="info",
                        choices=["debug", "info", "warning", "error", "critical"],
                        help="Logging level")
    return parser.parse_args()

def main():
    """
    Main entry point for the application
    """
    args = parse_args()
    
    # Import dotenv at the top to ensure it's available
    from dotenv import load_dotenv
    
    # Set environment variables from .env file if provided via command line
    if args.env_file and os.path.exists(args.env_file):
        print(f"Loading environment variables from {args.env_file}")
        load_dotenv(args.env_file, override=True)
    # If no env file specified, try to load from default .env in project root
    elif os.path.exists(os.path.join(Path(__file__).parent, '.env')):
        default_env = os.path.join(Path(__file__).parent, '.env')
        print(f"Loading environment variables from default .env file: {default_env}")
        load_dotenv(default_env, override=True)
        
    # Verify AWS credentials are loaded
    aws_keys_present = all(os.environ.get(key) for key in [
        'AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 'AWS_DEFAULT_REGION'
    ])
    if aws_keys_present:
        print("AWS credentials loaded successfully")
        if os.environ.get('AWS_SESSION_TOKEN'):
            print("Using temporary credentials with session token")
    else:
        print("WARNING: AWS credentials not fully loaded - some features may not work")
    
    # Ensure spotty_cloud is in the Python path
    sys.path.insert(0, str(Path(__file__).parent))
    
    # Start the FastAPI application using uvicorn
    uvicorn.run(
        "api.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        workers=args.workers,
        log_level=args.log_level
    )

if __name__ == "__main__":
    main()
