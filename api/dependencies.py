#!/usr/bin/env python
# Shared dependencies for FastAPI routes

from fastapi import HTTPException, status
from typing import Optional

from spotty_cloud.core.orchestrator.manager import OrchestratorManager

# Global orchestrator instance that will be set in main.py
orchestrator: Optional[OrchestratorManager] = None


def get_orchestrator():
    """
    Dependency to get the orchestrator instance
    """
    if orchestrator is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Orchestrator not initialized",
        )
    return orchestrator
