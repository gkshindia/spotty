#!/usr/bin/env python
# Router for workload management endpoints

import os
import shutil
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    Body,
    Request,
    File,
    UploadFile,
    Form,
)
from typing import Dict, List, Any, Optional
from pydantic import BaseModel

# Import yaml with error handling
try:
    import yaml
except ImportError:
    # Add PyYAML to requirements.txt if needed
    import json

    yaml = None
    print("WARNING: PyYAML not installed, using JSON as fallback for templates")
from fastapi.templating import Jinja2Templates

from api.dependencies import get_orchestrator
from spotty_cloud.core.orchestrator.manager import OrchestratorManager

# Templates for HTML rendering
templates = Jinja2Templates(directory="api/templates")


# Define models
class WorkloadCreate(BaseModel):
    type: str
    template_id: Optional[str] = None
    resources: dict = {"cpu": 1, "memory": 1, "gpu": 0}
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
    workload_id: str, orchestrator: OrchestratorManager = Depends(get_orchestrator)
):
    """Get a specific workload by ID"""
    status = orchestrator.get_workload_status(workload_id)
    if status.get("status") == "not_found":
        raise HTTPException(status_code=404, detail=f"Workload {workload_id} not found")
    return status


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=Dict[str, Any])
async def create_workload(
    workload: WorkloadCreate,
    orchestrator: OrchestratorManager = Depends(get_orchestrator),
):
    """Create a new workload"""
    # Convert pydantic model to dict
    workload_config = workload.dict()

    # Check if this is a template-based workload
    if "template_id" in workload_config:
        template_id = workload_config["template_id"]
        # Load the template
        try:
            template_data = await get_workload_template_detail(template_id)

            # Merge template with provided configuration
            # Template provides defaults, user input overwrites them
            if "resources" in template_data:
                for key, value in template_data["resources"].items():
                    if (
                        key not in workload_config["resources"]
                        or not workload_config["resources"][key]
                    ):
                        workload_config["resources"][key] = value

            if "timeout" in template_data and not workload_config.get("timeout"):
                workload_config["timeout"] = template_data["timeout"]

            # Add template parameters to workload params if not already set
            if "parameters" in template_data and "params" in workload_config:
                for param in template_data["parameters"]:
                    if (
                        param["name"] not in workload_config["params"]
                        and "default" in param
                    ):
                        workload_config["params"][param["name"]] = param["default"]

        except Exception as e:
            # Just log the error and continue with user-provided config
            print(f"Error applying template {template_id}: {e}")

    # Submit the workload to the orchestrator
    workload_id = orchestrator.submit_workload(workload_config)

    return {"workload_id": workload_id, "status": "submitted"}


@router.get("/templates", response_model=Dict[str, Any])
async def get_workload_templates():
    """Get available workload templates from the templates directory"""
    # Dictionary to store template info
    templates = {}

    try:
        # Path to templates directory - trying multiple possible locations
        project_root = os.path.abspath(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        )
        possible_template_dirs = [
            # Standard location
            os.path.join(project_root, "spotty_cloud", "workloads", "templates"),
            # Config templates location
            os.path.join(project_root, "spotty_cloud", "config", "templates"),
            # Local templates
            os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates"),
            # Direct path for Docker environments
            "/app/spotty_cloud/workloads/templates",
        ]

        # Log all possible template directories for debugging
        print(f"Project root is: {project_root}")
        print(f"All possible template directories: {possible_template_dirs}")

        template_found = False
        for templates_dir in possible_template_dirs:
            print(f"Looking for templates in: {templates_dir}")

            # List YAML files in templates directory
            if os.path.exists(templates_dir):
                print(f"Found templates directory: {templates_dir}")
                print(f"Directory contents: {os.listdir(templates_dir)}")

                for filename in os.listdir(templates_dir):
                    if filename.endswith((".yaml", ".yml")):
                        template_path = os.path.join(templates_dir, filename)
                        try:
                            if yaml is None:
                                with open(template_path, "r") as file:
                                    # Fallback to JSON if YAML not available
                                    import json

                                    template_data = json.load(file)
                            else:
                                with open(template_path, "r") as file:
                                    template_data = yaml.safe_load(file)

                            template_name = os.path.splitext(filename)[0]
                            print(f"Loaded template: {template_name}")

                            # Extract key information
                            templates[template_name] = {
                                "name": template_data.get("name", template_name),
                                "description": template_data.get("description", ""),
                                "type": template_data.get("type", "default"),
                                "resources": template_data.get(
                                    "resources", {"cpu": 1, "memory": 1, "gpu": 0}
                                ),
                                "timeout": template_data.get("timeout", 3600),
                            }
                            template_found = True
                        except Exception as e:
                            print(f"Error loading template {filename}: {e}")

        # If no templates found, provide some defaults
        if not templates:
            print("No templates found in any directory, using defaults")
            templates = {
                "ml_training": {
                    "name": "ML Training",
                    "description": "Machine learning model training workload",
                    "type": "gpu",
                    "resources": {"cpu": 4, "memory": 16, "gpu": 1},
                    "timeout": 7200,
                },
                "video_encoding": {
                    "name": "Video Encoding",
                    "description": "Video transcoding workload",
                    "type": "cpu",
                    "resources": {"cpu": 8, "memory": 16, "gpu": 0},
                    "timeout": 3600,
                },
                "edge_computing": {
                    "name": "Edge Computing",
                    "description": "Edge device simulation workload",
                    "type": "cpu",
                    "resources": {"cpu": 2, "memory": 4, "gpu": 0},
                    "timeout": 3600,
                },
            }
    except Exception as e:
        print(f"Error retrieving templates: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error retrieving templates: {str(e)}"
        )

    return templates


@router.post("/templates/upload", status_code=status.HTTP_201_CREATED)
async def upload_workload_template(name: str = Form(...), file: UploadFile = File(...)):
    """Upload and save a new workload template YAML file"""
    # Validate file is YAML
    if not file.filename.endswith((".yaml", ".yml")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only YAML files are accepted",
        )

    # Path to templates directory
    templates_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "spotty_cloud",
        "workloads",
        "templates",
    )

    # Create directory if it doesn't exist
    os.makedirs(templates_dir, exist_ok=True)

    # Generate filename based on name parameter
    safe_name = name.lower().replace(" ", "_").replace("-", "_")
    if not safe_name.endswith((".yaml", ".yml")):
        file_path = os.path.join(templates_dir, f"{safe_name}.yaml")
    else:
        file_path = os.path.join(templates_dir, safe_name)

    # Validate YAML content
    content = await file.read()
    try:
        yaml_content = yaml.safe_load(content)
        if not isinstance(yaml_content, dict):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid YAML structure. Must be a dictionary/object.",
            )
    except yaml.YAMLError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid YAML format"
        )

    # Save the file
    with open(file_path, "wb") as f:
        # Reset file pointer to beginning
        await file.seek(0)
        shutil.copyfileobj(file.file, f)

    return {
        "filename": os.path.basename(file_path),
        "template_name": name,
        "status": "saved",
    }


@router.get("/templates/{template_id}", response_model=Dict[str, Any])
async def get_workload_template_detail(template_id: str):
    """Get details of a specific template by ID"""
    # Get project root for absolute paths
    project_root = os.path.abspath(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    )

    # Try multiple template directories
    possible_template_dirs = [
        # Standard location
        os.path.join(project_root, "spotty_cloud", "workloads", "templates"),
        # Config templates location
        os.path.join(project_root, "spotty_cloud", "config", "templates"),
        # Local templates
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates"),
    ]

    # Try to find the template in any of the directories
    template_path = None
    for templates_dir in possible_template_dirs:
        # Try both .yaml and .yml extensions
        yaml_path = os.path.join(templates_dir, f"{template_id}.yaml")
        yml_path = os.path.join(templates_dir, f"{template_id}.yml")

        if os.path.exists(yaml_path):
            template_path = yaml_path
            print(f"Found template at {template_path}")
            break
        elif os.path.exists(yml_path):
            template_path = yml_path
            print(f"Found template at {template_path}")
            break

            # If no template file found
            # If template file not found, check if it's one of our default templates
            templates = await get_workload_templates()
            if template_id in templates:
                # Return the default template info
                default_template = templates[template_id]
                # Add some mock parameters based on the template type
                if default_template["type"] == "gpu":
                    default_template["parameters"] = [
                        {"name": "model_type", "default": "resnet50"},
                        {"name": "epochs", "default": 10},
                        {"name": "batch_size", "default": 32},
                    ]
                elif default_template["type"] == "cpu":
                    default_template["parameters"] = [
                        {"name": "source", "default": "/data/input.mp4"},
                        {"name": "target_format", "default": "mp4"},
                        {"name": "resolution", "default": "1080p"},
                    ]
                return default_template
            else:
                raise HTTPException(
                    status_code=404, detail=f"Template {template_id} not found"
                )

    try:
        with open(template_path, "r") as file:
            template_data = yaml.safe_load(file)
            return template_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading template: {str(e)}")


# Create a separate router for the web interface
web_router = APIRouter(
    prefix="/workloads",
    tags=["web", "workloads"],
    responses={404: {"description": "Not found"}},
)


@web_router.get("/")
async def get_workloads_page(
    request: Request, orchestrator: OrchestratorManager = Depends(get_orchestrator)
):
    """Workloads management page"""
    # Get all workloads
    workloads = {}
    for workload_id in orchestrator.workload_dispatcher.workloads:
        workloads[workload_id] = orchestrator.get_workload_status(workload_id)

    # Render workloads page
    return templates.TemplateResponse(
        "workloads.html",
        {"request": request, "title": "SpottyCloud Workloads", "workloads": workloads},
    )
