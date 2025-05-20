#!/usr/bin/env python
# Router for workload management endpoints

from fastapi import APIRouter, Depends, HTTPException, status, Body, Request
from typing import Dict, List, Any, Optional
from pydantic import BaseModel
from fastapi.templating import Jinja2Templates

from api.dependencies import get_orchestrator
from spotty_cloud.core.orchestrator.manager import OrchestratorManager

# Templates for HTML rendering
templates = Jinja2Templates(directory="api/templates")

# Define models
class WorkloadCreate(BaseModel):
    type: str
    resources: dict = {
        "cpu": 1,
        "memory": 1,
        "gpu": 0
    }
    timeout: int = 3600
    params: Optional[Dict[str, Any]] = None

class WorkloadStatus(BaseModel):
    id: str
    type: str
    status: str
    instance_id: Optional[str] = None
    create_time: Optional[float] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    duration: Optional[float] = None
    retries: int = 0
    result: Optional[Any] = None

# Router - API endpoints
router = APIRouter(
    prefix="/api/workloads",
    tags=["workloads"],
    responses={404: {"description": "Workload not found"}},
)

@router.get("/", response_model=Dict[str, Any])
async def get_workloads(orchestrator: OrchestratorManager = Depends(get_orchestrator)):
    """Get all workloads"""
    workloads = {}
    for workload_id in orchestrator.workload_dispatcher.workloads:
        workloads[workload_id] = orchestrator.get_workload_status(workload_id)
    return workloads

@router.get("/{workload_id}", response_model=Dict[str, Any])
async def get_workload(
    workload_id: str, 
    orchestrator: OrchestratorManager = Depends(get_orchestrator)
):
    """Get a specific workload by ID"""
    status = orchestrator.get_workload_status(workload_id)
    if status.get('status') == 'not_found':
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workload {workload_id} not found"
        )
    return status

@router.post("/", status_code=status.HTTP_201_CREATED, response_model=Dict[str, Any])
async def create_workload(
    workload: WorkloadCreate,
    orchestrator: OrchestratorManager = Depends(get_orchestrator)
):
    """Create a new workload"""
    # Convert pydantic model to dict
    workload_config = workload.dict()
    
    # Submit the workload to the orchestrator
    workload_id = orchestrator.submit_workload(workload_config)
    
    return {
        "workload_id": workload_id,
        "status": "submitted"
    }

@router.get("/templates", response_model=Dict[str, Any])
async def get_workload_templates():
    """Get available workload templates"""
    # This could be fetched from your template system
    templates = {
        'cpu_workload': {
            'name': 'CPU Workload',
            'description': 'Standard compute-intensive workload',
            'type': 'cpu',
            'resources': {
                'cpu': 2,
                'memory': 2,
                'gpu': 0
            },
            'timeout': 3600
        },
        'gpu_workload': {
            'name': 'GPU Workload',
            'description': 'Graphics-intensive processing task',
            'type': 'gpu',
            'resources': {
                'cpu': 2,
                'memory': 4,
                'gpu': 1
            },
            'timeout': 7200
        },
        'video_encoding': {
            'name': 'Video Encoding',
            'description': 'Convert videos to multiple formats',
            'type': 'video',
            'resources': {
                'cpu': 2,
                'memory': 2,
                'gpu': 1
            },
            'timeout': 3600
        }
    }
    return templates

# Create a separate router for the web interface
web_router = APIRouter(
    prefix="/workloads",
    tags=["web", "workloads"],
    responses={404: {"description": "Not found"}},
)

@web_router.get("/")
async def get_workloads_page(
    request: Request,
    orchestrator: OrchestratorManager = Depends(get_orchestrator)
):
    """Workloads management page"""
    # Get all workloads
    workloads = {}
    for workload_id in orchestrator.workload_dispatcher.workloads:
        workloads[workload_id] = orchestrator.get_workload_status(workload_id)
    
    # Render workloads page
    return templates.TemplateResponse(
        "workloads.html",
        {
            "request": request,
            "title": "SpottyCloud Workloads",
            "workloads": workloads
        }
    )
