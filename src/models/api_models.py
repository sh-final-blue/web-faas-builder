"""Pydantic models for API requests and responses."""

from pydantic import BaseModel


class BuildRequest(BaseModel):
    """Request model for build endpoint."""
    app_name: str | None = None


class BuildResponse(BaseModel):
    """Response model for build and push operations."""
    task_id: str
    status: str
    message: str


class PushRequest(BaseModel):
    """Request model for push endpoint."""
    registry_url: str
    username: str
    password: str
    tag: str | None = None
    app_dir: str


class ScaffoldRequest(BaseModel):
    """Request model for scaffold endpoint."""
    image_ref: str
    component: str | None = None
    replicas: int = 1
    output_path: str | None = None


class ScaffoldResponse(BaseModel):
    """Response model for scaffold endpoint."""
    success: bool
    yaml_content: str | None = None
    file_path: str | None = None
    error: str | None = None


class DeployRequest(BaseModel):
    """Request model for deploy endpoint.
    
    Requirements: 10.1, 10.2, 10.5, 10.6, 10.7
    """
    app_name: str | None = None
    namespace: str
    service_account: str | None = None
    cpu_limit: str | None = None
    memory_limit: str | None = None
    cpu_request: str | None = None
    memory_request: str | None = None
    image_ref: str
    enable_autoscaling: bool = True
    replicas: int | None = None
    use_spot: bool = True
    custom_tolerations: list[dict] | None = None
    custom_affinity: dict | None = None


class DeployResponse(BaseModel):
    """Response model for deploy endpoint.
    
    Requirements: 10.4, 10.5, 11.1, 11.2
    """
    app_name: str
    namespace: str
    service_name: str | None = None
    service_status: str = "pending"
    endpoint: str | None = None
    enable_autoscaling: bool = True
    use_spot: bool = True
    error: str | None = None


class TaskStatusResponse(BaseModel):
    """Response model for task status endpoint."""
    task_id: str
    status: str
    result: dict | None = None
    error: str | None = None
