"""FastAPI routes for Spin K8s Deployment Tool."""

import uuid

from fastapi import APIRouter, File, Form, UploadFile

from src.models.api_models import (
    BuildResponse,
    DeployRequest,
    DeployResponse,
    PushRequest,
    ScaffoldRequest,
    ScaffoldResponse,
    TaskStatusResponse,
)

router = APIRouter()


@router.post("/build", response_model=BuildResponse, status_code=202)
async def build(
    file: UploadFile = File(...),
    app_name: str | None = Form(None),
) -> BuildResponse:
    """Build a Spin application from uploaded file.
    
    Accepts a .py file or .zip archive and starts a background build task.
    """
    task_id = str(uuid.uuid4())
    return BuildResponse(
        task_id=task_id,
        status="pending",
        message="Build task created",
    )


@router.get("/tasks/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str) -> TaskStatusResponse:
    """Get the status of a background task."""
    return TaskStatusResponse(
        task_id=task_id,
        status="pending",
        result=None,
        error=None,
    )


@router.post("/push", response_model=BuildResponse, status_code=202)
async def push(request: PushRequest) -> BuildResponse:
    """Push a built Spin application to a container registry."""
    task_id = str(uuid.uuid4())
    return BuildResponse(
        task_id=task_id,
        status="pending",
        message="Push task created",
    )



@router.post("/scaffold", response_model=ScaffoldResponse)
async def scaffold(request: ScaffoldRequest) -> ScaffoldResponse:
    """Generate SpinApp Kubernetes manifest using spin kube scaffold."""
    dummy_yaml = """apiVersion: core.spinoperator.dev/v1alpha1
kind: SpinApp
metadata:
  name: my-spin-app
  namespace: default
spec:
  image: {}
  replicas: {}
""".format(request.image_ref, request.replicas)
    
    return ScaffoldResponse(
        success=True,
        yaml_content=dummy_yaml,
        file_path=request.output_path,
        error=None,
    )


@router.post("/deploy", response_model=DeployResponse)
async def deploy(request: DeployRequest) -> DeployResponse:
    """Deploy a SpinApp to Kubernetes cluster."""
    app_name = request.app_name or f"spin-app-{uuid.uuid4().hex[:8]}"
    service_name = f"{app_name}-svc" if request.service_type else None
    endpoint = f"{service_name}.{request.namespace}.svc.cluster.local" if service_name else None
    
    return DeployResponse(
        app_name=app_name,
        namespace=request.namespace,
        service_name=service_name,
        endpoint=endpoint,
    )


@router.post("/build-and-push", response_model=BuildResponse, status_code=202)
async def build_and_push(
    file: UploadFile = File(...),
    registry_url: str = Form(...),
    username: str = Form(...),
    password: str = Form(...),
    tag: str | None = Form(None),
    app_name: str | None = Form(None),
) -> BuildResponse:
    """Build and push a Spin application in a single operation.
    
    Accepts a .py file or .zip archive, builds it, and pushes to the registry.
    """
    task_id = str(uuid.uuid4())
    return BuildResponse(
        task_id=task_id,
        status="pending",
        message="Build and push task created",
    )
