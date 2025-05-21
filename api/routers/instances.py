#!/usr/bin/env python
# Router for instance management endpoints

from fastapi import APIRouter, Depends, HTTPException, status, Request
from typing import List, Optional
from pydantic import BaseModel
from fastapi.templating import Jinja2Templates

from api.dependencies import get_orchestrator
from spotty_cloud.core.orchestrator.manager import OrchestratorManager

# Templates for HTML rendering
templates = Jinja2Templates(directory="api/templates")


# Define models
class InstanceCreate(BaseModel):
    instance_type: str
    workload_type: Optional[str] = None


class InstanceResponse(BaseModel):
    instance_id: str
    instance_type: str
    status: str
    start_time: Optional[float] = None
    workloads: List[str] = []


# Router
router = APIRouter(
    prefix="/api/instances",
    tags=["instances"],
    responses={404: {"description": "Instance not found"}},
)


@router.get("/", response_model=dict)
async def get_instances(orchestrator: OrchestratorManager = Depends(get_orchestrator)):
    """Get all active instances"""
    return orchestrator.get_instance_status()


@router.get("/{instance_id}", response_model=dict)
async def get_instance(
    instance_id: str, orchestrator: OrchestratorManager = Depends(get_orchestrator)
):
    """Get a specific instance by ID"""
    instance = orchestrator.get_instance_status(instance_id)
    if not instance or instance.get("status") == "not_found":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Instance {instance_id} not found",
        )
    return instance


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=dict)
async def request_instance(
    instance: InstanceCreate,
    orchestrator: OrchestratorManager = Depends(get_orchestrator),
):
    """Request a new instance"""
    # This is a simulated endpoint that would interface with your instance_manager
    request_id = orchestrator.instance_manager.request_instance(
        instance_type=instance.instance_type, workload_type=instance.workload_type
    )

    if not request_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to request instance",
        )

    return {"request_id": request_id, "status": "pending"}


@router.delete("/{instance_id}", status_code=status.HTTP_200_OK)
async def terminate_instance(
    instance_id: str, orchestrator: OrchestratorManager = Depends(get_orchestrator)
):
    """Terminate a specific instance"""
    success = orchestrator.trigger_instance_failure(instance_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Instance {instance_id} not found or could not be terminated",
        )
    return {"success": True, "message": f"Instance {instance_id} termination initiated"}


# Web interface router
web_router = APIRouter(
    prefix="/instances",
    tags=["web", "instances"],
    responses={404: {"description": "Not found"}},
)


@web_router.get("/")
async def get_instances_page(
    request: Request, orchestrator: OrchestratorManager = Depends(get_orchestrator)
):
    """Instances management page"""
    # Get all active instances
    instances = orchestrator.get_instance_status()

    # Get available instance types for the selection dropdown
    instance_types = (
        orchestrator.get_available_instance_types()
        if hasattr(orchestrator, "get_available_instance_types")
        else []
    )

    # Render instances page
    return templates.TemplateResponse(
        "instances.html",
        {
            "request": request,
            "title": "SpottyCloud Instances",
            "instances": instances,
            "instance_types": instance_types,
        },
    )
