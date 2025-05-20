#!/usr/bin/env python
# Main FastAPI application for SpottyCloud

import logging
import os
import sys
from pathlib import Path

# Add project root to path for imports
root_path = Path(__file__).parent.parent
sys.path.insert(0, str(root_path))

from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
import uvicorn

# Import SpottyCloud components
from spotty_cloud.config.config_manager import ConfigManager
from spotty_cloud.core.orchestrator.manager import OrchestratorManager
from spotty_cloud.utils.aws.credentials import AWSCredentialManager

# Use dependencies module for shared resources
import api.dependencies

# Import API routers
from api.routers import instances, workloads, dashboard, scripts, costs

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("spotty_cloud.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("spotty_cloud_api")

# Initialize FastAPI app
app = FastAPI(
    title="SpottyCloud API",
    description="API for managing distributed computing on AWS Spot Instances",
    version="0.1.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files
app.mount("/static", StaticFiles(directory="api/static"), name="static")

# Templates
templates = Jinja2Templates(directory="api/templates")

# Configuration
config_manager = ConfigManager()
config = {
    'system': config_manager.get_system_config(),
    'aws': config_manager.get_aws_config(),
    'workloads': config_manager.get_workload_config(),
    'resilience': config_manager.get_resilience_config(),
    'monitoring': config_manager.get_monitoring_config()
}

# Get the orchestrator reference from dependencies
from api.dependencies import get_orchestrator

# Include API routers
app.include_router(dashboard.router)
app.include_router(instances.router)
app.include_router(workloads.router)
app.include_router(scripts.router)
app.include_router(costs.router)

# Include web interface routers
app.include_router(dashboard.web_router)
app.include_router(instances.web_router)
app.include_router(workloads.web_router)
app.include_router(scripts.web_router)
app.include_router(costs.web_router)

# Root endpoint (main dashboard)
@app.get("/")
async def root(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "title": "SpottyCloud Dashboard"}
    )

# Health check endpoint
@app.get("/health")
async def health_check():
    if api.dependencies.orchestrator is not None:
        system_status = api.dependencies.orchestrator.get_system_status()
        return {
            "status": "ok",
            "orchestrator": system_status["health"],
            "version": "0.1.0"
        }
    return {
        "status": "starting",
        "orchestrator": "not_initialized",
        "version": "0.1.0"
    }

# Start Orchestrator
@app.on_event("startup")
async def startup_event():
    try:
        logger.info("Initializing SpottyCloud orchestrator...")
        aws_credentials = AWSCredentialManager(config.get('aws', {}))
        api.dependencies.orchestrator = OrchestratorManager(config)
        api.dependencies.orchestrator.start()
        logger.info("SpottyCloud orchestrator started successfully")
    except Exception as e:
        logger.error(f"Failed to start orchestrator: {str(e)}", exc_info=True)

# Shutdown Orchestrator
@app.on_event("shutdown")
async def shutdown_event():
    if api.dependencies.orchestrator is not None:
        logger.info("Shutting down SpottyCloud orchestrator...")
        api.dependencies.orchestrator.stop()
        logger.info("SpottyCloud orchestrator stopped")

# Run the application directly when script is executed
if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("api.main:app", host="0.0.0.0", port=port, reload=True)
