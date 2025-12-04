"""FastAPI routes for Spin K8s Deployment Tool."""

import uuid
import tempfile
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile

from src.models.api_models import (
    BuildResponse,
    DeployRequest,
    DeployResponse,
    PushRequest,
    ScaffoldRequest,
    ScaffoldResponse,
    TaskStatusResponse,
)
from src.services.task_manager import TaskManager, TaskStatus
from src.services.file_handler import FileHandler
from src.services.validation import ValidationService
from src.services.build import BuildService
from src.services.push import PushService
from src.services.scaffold import ScaffoldService
from src.services.deploy import DeployService
from src.services.manifest import ManifestService
from src.models.manifest import (
    SpinAppManifest,
    ResourceLimits,
    validate_autoscaling_config,
    Toleration,
)

router = APIRouter()

# Global service instances
task_manager = TaskManager()
file_handler = FileHandler()
validation_service = ValidationService()
build_service = BuildService()
push_service = PushService()
scaffold_service = ScaffoldService()
deploy_service = DeployService()
manifest_service = ManifestService()


def run_build_task(
    task_id: str,
    file_content: bytes,
    filename: str,
    app_name: str | None,
) -> None:
    """Background task to run the build process.
    
    This function:
    1. Updates task status to RUNNING
    2. Handles file (zip or single .py)
    3. Validates Python code with MyPy
    4. Executes the build
    5. Updates task status to COMPLETED or FAILED
    
    Requirements: 6.1, 6.2, 6.3, 6.4, 6.5
    """
    # Update status to RUNNING
    task_manager.update_status(task_id, TaskStatus.RUNNING)
    
    try:
        # Create temporary work directory
        work_dir = file_handler.create_temp_work_dir()
        
        # Handle file based on type
        if filename.endswith(".zip"):
            result = file_handler.handle_zip(file_content, work_dir)
        elif filename.endswith(".py"):
            result = file_handler.handle_single_py(file_content, filename, work_dir)
        else:
            task_manager.update_status(
                task_id,
                TaskStatus.FAILED,
                error=f"Unsupported file type: {filename}. Only .py and .zip files are supported."
            )
            return
        
        if not result.success:
            task_manager.update_status(
                task_id,
                TaskStatus.FAILED,
                error=result.error
            )
            return
        
        app_dir = result.app_dir

        # Find Python files to validate
        py_files = list(app_dir.glob("*.py"))
        
        # Validate Python code with MyPy
        if py_files:
            # Validate the main Python file or all Python files
            validation_result = validation_service.validate_python(str(app_dir))
            
            if not validation_result.success:
                task_manager.update_status(
                    task_id,
                    TaskStatus.FAILED,
                    error=f"MyPy validation failed:\n{validation_result.output}"
                )
                return
        
        # Execute the full build pipeline
        build_result = build_service.full_build(app_dir)
        
        if build_result.success:
            task_manager.update_status(
                task_id,
                TaskStatus.COMPLETED,
                result={
                    "wasm_path": build_result.wasm_path,
                    "app_dir": str(app_dir),
                }
            )
        else:
            task_manager.update_status(
                task_id,
                TaskStatus.FAILED,
                error=build_result.error
            )
            
    except Exception as e:
        task_manager.update_status(
            task_id,
            TaskStatus.FAILED,
            error=f"Build task failed with unexpected error: {str(e)}"
        )


@router.post("/build", response_model=BuildResponse, status_code=202)
async def build(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    app_name: str | None = Form(None),
) -> BuildResponse:
    """Build a Spin application from uploaded file.
    
    Accepts a .py file or .zip archive and starts a background build task.
    
    Requirements: 6.1 - Start operation as background task and return task ID immediately
    """
    # Create task and get task ID
    task_id = task_manager.create_task()
    
    # Read file content
    file_content = await file.read()
    filename = file.filename or "app.py"
    
    # Add background task
    background_tasks.add_task(
        run_build_task,
        task_id,
        file_content,
        filename,
        app_name,
    )
    
    return BuildResponse(
        task_id=task_id,
        status="pending",
        message="Build task created",
    )


@router.get("/tasks/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str) -> TaskStatusResponse:
    """Get the status of a background task."""
    task = task_manager.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")
    
    return TaskStatusResponse(
        task_id=task.task_id,
        status=task.status.value,
        result=task.result,
        error=task.error,
    )


def run_push_task(
    task_id: str,
    app_dir: str,
    registry_url: str,
    username: str,
    password: str,
    tag: str | None,
) -> None:
    """Background task to run the push process.
    
    This function:
    1. Updates task status to RUNNING
    2. Logs into the registry
    3. Pushes the application to the registry
    4. Updates task status to COMPLETED or FAILED
    
    Requirements: 6.1, 7.1, 7.2, 7.3, 7.4, 7.5, 7.6
    """
    # Update status to RUNNING
    task_manager.update_status(task_id, TaskStatus.RUNNING)
    
    try:
        app_path = Path(app_dir)
        
        # Verify app directory exists
        if not app_path.exists():
            task_manager.update_status(
                task_id,
                TaskStatus.FAILED,
                error=f"Application directory not found: {app_dir}"
            )
            return
        
        # Execute the full push pipeline (login + push)
        push_result = push_service.full_push(
            app_dir=app_path,
            registry_url=registry_url,
            username=username,
            password=password,
            tag=tag,
        )
        
        if push_result.success:
            task_manager.update_status(
                task_id,
                TaskStatus.COMPLETED,
                result={
                    "image_uri": push_result.image_uri,
                }
            )
        else:
            task_manager.update_status(
                task_id,
                TaskStatus.FAILED,
                error=push_result.error
            )
            
    except Exception as e:
        task_manager.update_status(
            task_id,
            TaskStatus.FAILED,
            error=f"Push task failed with unexpected error: {str(e)}"
        )


@router.post("/push", response_model=BuildResponse, status_code=202)
async def push(
    background_tasks: BackgroundTasks,
    request: PushRequest,
) -> BuildResponse:
    """Push a built Spin application to a container registry.
    
    Requirements: 6.1 - Start operation as background task and return task ID immediately
    Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6 - Registry login and push operations
    """
    # Create task and get task ID
    task_id = task_manager.create_task()
    
    # Add background task
    background_tasks.add_task(
        run_push_task,
        task_id,
        request.app_dir,
        request.registry_url,
        request.username,
        request.password,
        request.tag,
    )
    
    return BuildResponse(
        task_id=task_id,
        status="pending",
        message="Push task created",
    )


@router.post("/scaffold", response_model=ScaffoldResponse)
async def scaffold(request: ScaffoldRequest) -> ScaffoldResponse:
    """Generate SpinApp Kubernetes manifest using spin kube scaffold.
    
    Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6
    - 8.1: Execute spin kube scaffold --from {image}
    - 8.2: Pass --component {name} when specified
    - 8.3: Pass --replicas {count} when specified
    - 8.4: Pass --out {path} when specified
    - 8.5: Return generated YAML content or file path on success
    - 8.6: Return stderr output on failure
    """
    result = scaffold_service.scaffold(
        image_ref=request.image_ref,
        component=request.component,
        replicas=request.replicas,
        output_path=request.output_path,
    )
    
    return ScaffoldResponse(
        success=result.success,
        yaml_content=result.yaml_content,
        file_path=result.file_path,
        error=result.error,
    )


@router.post("/deploy", response_model=DeployResponse)
async def deploy(request: DeployRequest) -> DeployResponse:
    """Deploy a SpinApp to Kubernetes cluster.
    
    Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7, 13.1, 13.2, 13.3, 13.4, 13.5
    Requirements: 14.1, 14.2, 14.3, 14.4, 14.5
    - 10.1: Set namespace in SpinApp manifest metadata
    - 10.2: Include serviceAccountName in SpinApp manifest spec
    - 10.3: Return error if namespace does not exist
    - 10.4: Return deployed SpinApp name and namespace on success
    - 10.5: Apply SpinApp manifest to Kubernetes cluster
    - 10.6: Use custom application name if provided
    - 10.7: Generate unique name using Faker if not provided
    - 13.1: Default enableAutoscaling to true
    - 13.2: Allow explicit enableAutoscaling=false
    - 13.3: Omit replicas when enableAutoscaling is true
    - 13.4: Include replicas when enableAutoscaling is false
    - 13.5: Validate mutual exclusion of enableAutoscaling and replicas
    - 14.1: Add default Spot toleration when use_spot is true
    - 14.2: Add default Spot affinity when use_spot is true
    - 14.3: Omit Spot settings when use_spot is false
    - 14.4: Include custom tolerations in addition to default Spot toleration
    - 14.5: Include custom affinity rules
    """
    import tempfile
    import os
    
    # Validate autoscaling configuration (Requirement 13.5)
    is_valid, error_msg = validate_autoscaling_config(
        request.enable_autoscaling, 
        request.replicas
    )
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)
    
    # Create SpinApp manifest
    resources = ResourceLimits(
        cpu_limit=request.cpu_limit,
        memory_limit=request.memory_limit,
        cpu_request=request.cpu_request,
        memory_request=request.memory_request,
    )
    
    # Generate app name if not provided (Requirement 10.7)
    app_name = request.app_name or deploy_service.generate_app_name()
    
    # Parse custom tolerations (Requirement 14.4)
    custom_tolerations: list[Toleration] = []
    if request.custom_tolerations:
        for t in request.custom_tolerations:
            custom_tolerations.append(Toleration(
                key=t.get("key", ""),
                operator=t.get("operator", "Exists"),
                effect=t.get("effect", "NoSchedule"),
                value=t.get("value"),
            ))
    
    # Create manifest with autoscaling and Spot configuration
    # (Requirements 13.1, 13.2, 13.3, 13.4, 14.1, 14.2, 14.3, 14.4)
    manifest = SpinAppManifest(
        name=app_name,
        namespace=request.namespace,
        image=request.image_ref,
        service_account=request.service_account,
        resources=resources,
        replicas=request.replicas,
        enable_autoscaling=request.enable_autoscaling,
        use_spot=request.use_spot,
        tolerations=custom_tolerations,
    )
    
    # Generate YAML manifest
    yaml_content = manifest_service.to_yaml(manifest)
    
    # Write manifest to temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(yaml_content)
        manifest_path = f.name
    
    try:
        # Deploy using DeployService
        result = deploy_service.deploy(
            manifest_path=manifest_path,
            namespace=request.namespace,
            app_name=app_name,
            enable_autoscaling=request.enable_autoscaling,
            use_spot=request.use_spot,
        )
        
        if not result.success:
            # Return error response (Requirement 10.3)
            raise HTTPException(
                status_code=400 if "not found" in (result.error or "").lower() else 500,
                detail=result.error or "Deployment failed"
            )
        
        return DeployResponse(
            app_name=result.app_name or app_name,
            namespace=result.namespace or request.namespace,
            service_name=result.service_name,
            service_status=result.service_status,
            endpoint=result.endpoint,
            enable_autoscaling=result.enable_autoscaling,
            use_spot=result.use_spot,
            error=result.error,
        )
    finally:
        # Clean up temporary file
        if os.path.exists(manifest_path):
            os.unlink(manifest_path)


def run_build_and_push_task(
    task_id: str,
    file_content: bytes,
    filename: str,
    registry_url: str,
    username: str,
    password: str,
    tag: str | None,
    app_name: str | None,
) -> None:
    """Background task to run the build and push process.
    
    This function chains build and push services in a single background task:
    1. Updates task status to RUNNING
    2. Handles file (zip or single .py)
    3. Validates Python code with MyPy
    4. Executes the build
    5. Pushes to registry
    6. Updates task status to COMPLETED or FAILED
    
    Requirements: 6.1, 6.7
    """
    # Update status to RUNNING
    task_manager.update_status(task_id, TaskStatus.RUNNING)
    
    try:
        # Create temporary work directory
        work_dir = file_handler.create_temp_work_dir()
        
        # Handle file based on type
        if filename.endswith(".zip"):
            result = file_handler.handle_zip(file_content, work_dir)
        elif filename.endswith(".py"):
            result = file_handler.handle_single_py(file_content, filename, work_dir)
        else:
            task_manager.update_status(
                task_id,
                TaskStatus.FAILED,
                error=f"Unsupported file type: {filename}. Only .py and .zip files are supported."
            )
            return
        
        if not result.success:
            task_manager.update_status(
                task_id,
                TaskStatus.FAILED,
                error=result.error
            )
            return
        
        app_dir = result.app_dir

        # Find Python files to validate
        py_files = list(app_dir.glob("*.py"))
        
        # Validate Python code with MyPy
        if py_files:
            validation_result = validation_service.validate_python(str(app_dir))
            
            if not validation_result.success:
                task_manager.update_status(
                    task_id,
                    TaskStatus.FAILED,
                    error=f"MyPy validation failed:\n{validation_result.output}"
                )
                return
        
        # Execute the full build pipeline
        build_result = build_service.full_build(app_dir)
        
        if not build_result.success:
            task_manager.update_status(
                task_id,
                TaskStatus.FAILED,
                error=f"Build failed: {build_result.error}"
            )
            return
        
        # Execute the full push pipeline (login + push)
        push_result = push_service.full_push(
            app_dir=app_dir,
            registry_url=registry_url,
            username=username,
            password=password,
            tag=tag,
        )
        
        if push_result.success:
            task_manager.update_status(
                task_id,
                TaskStatus.COMPLETED,
                result={
                    "wasm_path": build_result.wasm_path,
                    "image_uri": push_result.image_uri,
                }
            )
        else:
            task_manager.update_status(
                task_id,
                TaskStatus.FAILED,
                error=f"Push failed: {push_result.error}"
            )
            
    except Exception as e:
        task_manager.update_status(
            task_id,
            TaskStatus.FAILED,
            error=f"Build and push task failed with unexpected error: {str(e)}"
        )


@router.post("/build-and-push", response_model=BuildResponse, status_code=202)
async def build_and_push(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    registry_url: str = Form(...),
    username: str = Form(...),
    password: str = Form(...),
    tag: str | None = Form(None),
    app_name: str | None = Form(None),
) -> BuildResponse:
    """Build and push a Spin application in a single operation.
    
    Accepts a .py file or .zip archive, builds it, and pushes to the registry.
    
    Requirements: 6.1, 6.7 - Start combined operation as background task
    """
    # Create task and get task ID
    task_id = task_manager.create_task()
    
    # Read file content
    file_content = await file.read()
    filename = file.filename or "app.py"
    
    # Add background task
    background_tasks.add_task(
        run_build_and_push_task,
        task_id,
        file_content,
        filename,
        registry_url,
        username,
        password,
        tag,
        app_name,
    )
    
    return BuildResponse(
        task_id=task_id,
        status="pending",
        message="Build and push task created",
    )
