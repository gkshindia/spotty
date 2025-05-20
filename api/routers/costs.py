#!/usr/bin/env python
# Router for cost tracking endpoints

from fastapi import APIRouter, Depends, Query, HTTPException, status, Request
from typing import Dict, Any, List, Optional
import time
from datetime import datetime, timedelta
from fastapi.templating import Jinja2Templates

from api.dependencies import get_orchestrator
from spotty_cloud.core.orchestrator.manager import OrchestratorManager

# Templates for HTML rendering
templates = Jinja2Templates(directory="api/templates")

# Router
router = APIRouter(
    prefix="/api/costs",
    tags=["costs"],
    responses={404: {"description": "Not found"}},
)

@router.get("/", response_model=Dict[str, Any])
async def get_costs(orchestrator: OrchestratorManager = Depends(get_orchestrator)):
    """Get current cost data"""
    if not hasattr(orchestrator, 'cost_tracker'):
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Cost tracking not implemented"
        )
    
    return orchestrator.cost_tracker.get_current_cost_data()

@router.get("/history", response_model=List[Dict[str, Any]])
async def get_cost_history(
    days: int = Query(7, description="Number of days of history to retrieve"),
    orchestrator: OrchestratorManager = Depends(get_orchestrator)
):
    """Get historical cost data"""
    if not hasattr(orchestrator, 'cost_tracker'):
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Cost tracking not implemented"
        )
    
    return orchestrator.cost_tracker.get_historical_data(days)

@router.get("/savings", response_model=Dict[str, Any])
async def get_cost_savings(
    days: int = Query(7, description="Number of days to calculate savings for"),
    orchestrator: OrchestratorManager = Depends(get_orchestrator)
):
    """Get detailed cost savings information comparing spot vs on-demand pricing"""
    if not hasattr(orchestrator, 'cost_tracker'):
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Cost tracking not implemented"
        )
    
    historical_data = orchestrator.cost_tracker.get_historical_data(days)
    summary = orchestrator.cost_tracker.get_summary()
    
    return {
        'summary': summary,
        'historical': historical_data,
        'projected_monthly_savings': round(summary.get('total_savings', 0) * 30, 2) if summary else 0
    }

@router.get("/estimate", response_model=Dict[str, Any])
async def estimate_cost(
    instance_type: str,
    hours: float = Query(1.0, description="Number of hours to estimate"),
    spot: bool = Query(True, description="Use spot pricing (vs on-demand)")
):
    """Estimate cost for running an instance type for specified hours"""
    # This would need implementation with your cost estimation logic
    # Providing a mock implementation here
    
    # Mock price mapping (you'd implement this with actual AWS pricing info)
    price_map = {
        't3.medium': {'spot': 0.0125, 'on_demand': 0.0416},
        't3.large': {'spot': 0.0250, 'on_demand': 0.0832},
        'c5.large': {'spot': 0.0320, 'on_demand': 0.0850},
        'c5.xlarge': {'spot': 0.0640, 'on_demand': 0.1700},
        'g4dn.xlarge': {'spot': 0.2900, 'on_demand': 0.5260},
        'p3.2xlarge': {'spot': 1.2000, 'on_demand': 3.0600}
    }
    
    if instance_type not in price_map:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Pricing information not available for instance type: {instance_type}"
        )
    
    price_type = 'spot' if spot else 'on_demand'
    hourly_rate = price_map[instance_type][price_type]
    estimated_cost = hourly_rate * hours
    
    return {
        'instance_type': instance_type,
        'pricing_model': price_type,
        'hourly_rate': hourly_rate,
        'hours': hours,
        'estimated_cost': estimated_cost,
        'currency': 'USD'
    }

# Web interface router
web_router = APIRouter(
    prefix="/costs",
    tags=["web", "costs"],
    responses={404: {"description": "Not found"}},
)

@web_router.get("/")
async def get_costs_page(
    request: Request,
    orchestrator: OrchestratorManager = Depends(get_orchestrator)
):
    """Costs management page"""
    # Get cost data if cost tracker is available
    cost_data = None
    if hasattr(orchestrator, 'cost_tracker'):
        cost_data = orchestrator.cost_tracker.get_summary()
    
    # Render costs page
    return templates.TemplateResponse(
        "costs.html",
        {
            "request": request,
            "title": "SpottyCloud Cost Management",
            "cost_data": cost_data
        }
    )
