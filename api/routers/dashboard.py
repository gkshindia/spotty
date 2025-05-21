#!/usr/bin/env python
# Router for dashboard endpoints

from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from typing import Dict, Any

from api.dependencies import get_orchestrator
from spotty_cloud.core.orchestrator.manager import OrchestratorManager

# Templates for HTML rendering
templates = Jinja2Templates(directory="api/templates")

# Web interface router
web_router = APIRouter(
    prefix="/dashboard",
    tags=["web", "dashboard"],
    responses={404: {"description": "Not found"}},
)

# API router for data endpoints
router = APIRouter(
    prefix="/api/dashboard",
    tags=["dashboard", "api"],
    responses={404: {"description": "Not found"}},
)


@web_router.get("/")
async def get_dashboard(
    request: Request, orchestrator: OrchestratorManager = Depends(get_orchestrator)
):
    """Main dashboard page"""
    system_status = orchestrator.get_system_status()
    active_instances = orchestrator.get_instance_status()

    # Get workloads
    workloads = {}
    for workload_id in orchestrator.workload_dispatcher.workloads:
        workloads[workload_id] = orchestrator.get_workload_status(workload_id)

    # Get cost data if available
    cost_data = None
    if hasattr(orchestrator, "cost_tracker"):
        cost_data = orchestrator.cost_tracker.get_summary()

    # Render dashboard
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "title": "SpottyCloud Dashboard",
            "system_status": system_status,
            "instances": active_instances,
            "workloads": workloads,
            "cost_data": cost_data,
        },
    )


@router.get("/system-status")
async def get_system_status_api(
    orchestrator: OrchestratorManager = Depends(get_orchestrator),
):
    """Get overall system status"""
    return orchestrator.get_system_status()


@router.get("/resources")
async def get_resources_api(
    orchestrator: OrchestratorManager = Depends(get_orchestrator),
):
    """Get resource utilization information"""
    # This could be extended to include more detailed resource tracking
    system_status = orchestrator.get_system_status()

    # Sample extended resource format that could be implemented
    resources = {
        "cpu_usage": {
            "value": 45.2,  # Sample value - would come from resource monitoring
            "unit": "%",
        },
        "memory_usage": {
            "value": 62.8,  # Sample value - would come from resource monitoring
            "unit": "%",
        },
        "gpu_usage": {
            "value": 80.1,  # Sample value - would come from resource monitoring
            "unit": "%",
        },
        "instance_count": {
            "value": len(orchestrator.active_instances),
            "unit": "instances",
        },
        "pending_instance_count": {
            "value": len(orchestrator.pending_instances),
            "unit": "instances",
        },
    }

    return resources
