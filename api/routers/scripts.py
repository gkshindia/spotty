#!/usr/bin/env python
# Router for script execution endpoints

from fastapi import APIRouter, Depends, HTTPException, status, Body, Request
from typing import Dict, List, Any, Optional
from pydantic import BaseModel
import uuid
import time
from fastapi.templating import Jinja2Templates

from api.dependencies import get_orchestrator
from spotty_cloud.core.orchestrator.manager import OrchestratorManager

# Templates for HTML rendering
templates = Jinja2Templates(directory="api/templates")

# Define models
class ScriptExecute(BaseModel):
    script_name: str
    instance_id: Optional[str] = None
    parameters: Dict[str, Any] = {}

class ScriptResponse(BaseModel):
    execution_id: str
    script_name: str
    instance_id: Optional[str] = None
    status: str
    start_time: float
    
# Router
router = APIRouter(
    prefix="/api/scripts",
    tags=["scripts"],
    responses={404: {"description": "Not found"}},
)

# Web interface router
web_router = APIRouter(
    prefix="/scripts",
    tags=["web", "scripts"],
    responses={404: {"description": "Not found"}},
)

# In-memory storage for script executions (in a production app, this would be a database)
script_executions = {}

@router.get("/", response_model=Dict[str, Any])
async def get_available_scripts():
    """Get all available scripts"""
    # This could be fetched from your spotty.yaml or a specific script registry
    scripts = {
        'encode': {
            'description': 'Run video encoding batch job',
            'parameters': {}
        },
        'encode-gpu': {
            'description': 'Run video encoding with GPU acceleration',
            'parameters': {}
        },
        'encode-sample': {
            'description': 'Encode a single sample video',
            'parameters': {
                'input': {'type': 'string', 'default': '/data/input/sample.mp4'},
                'output': {'type': 'string', 'default': '/data/output/'}
            }
        }
    }
    return scripts

@router.post("/execute", status_code=status.HTTP_202_ACCEPTED)
async def execute_script(
    script: ScriptExecute,
    orchestrator: OrchestratorManager = Depends(get_orchestrator)
):
    """Execute a script on a specific instance or let the orchestrator choose an instance"""
    
    # Generate execution ID
    execution_id = f"exec-{uuid.uuid4().hex[:8]}"
    
    # Create execution record
    execution = {
        "execution_id": execution_id,
        "script_name": script.script_name,
        "instance_id": script.instance_id,
        "parameters": script.parameters,
        "status": "pending",
        "start_time": time.time(),
        "end_time": None,
        "result": None
    }
    
    # Store execution
    script_executions[execution_id] = execution
    
    # In a real implementation, you would interface with your workload dispatcher
    # or create a dedicated script executor that integrates with your orchestrator
    
    # For demo purposes, simulate async execution
    # In a real implementation, you would use background tasks or a queue
    def execute_in_background():
        import asyncio
        import random
        
        async def simulate_execution():
            await asyncio.sleep(5)  # Simulate script running
            script_executions[execution_id]["status"] = "completed"
            script_executions[execution_id]["end_time"] = time.time()
            script_executions[execution_id]["result"] = {
                "exit_code": 0,
                "output": "Script executed successfully"
            }
        
        asyncio.create_task(simulate_execution())
    
    # Start execution in background
    execute_in_background()
    
    return {
        "execution_id": execution_id,
        "status": "accepted",
        "message": f"Script {script.script_name} execution started"
    }

@router.get("/executions/{execution_id}", response_model=Dict[str, Any])
async def get_execution_status(execution_id: str):
    """Get the status of a script execution"""
    if execution_id not in script_executions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Execution {execution_id} not found"
        )
    
    return script_executions[execution_id]

@router.get("/executions", response_model=List[Dict[str, Any]])
async def get_all_executions():
    """Get all script executions"""
    return list(script_executions.values())

@web_router.get("/")
async def get_scripts_page(
    request: Request,
    orchestrator: OrchestratorManager = Depends(get_orchestrator)
):
    """Scripts management page"""
    # Get all available scripts
    scripts = []
    
    # In a real implementation, this would fetch scripts from a database or storage
    if hasattr(orchestrator, 'script_manager'):
        scripts = orchestrator.script_manager.get_all_scripts()
    
    # Render scripts page
    return templates.TemplateResponse(
        "scripts.html",
        {
            "request": request,
            "title": "SpottyCloud Scripts",
            "scripts": scripts
        }
    )
