"""SpinApp manifest data models with validation.

This module provides dataclasses for SpinApp Kubernetes manifests,
including resource limits validation.

Requirements: 9.1, 9.2, 9.3, 9.4, 12.1
"""

from dataclasses import dataclass, field
from typing import Optional
import re


# Kubernetes resource format regex pattern
# Valid formats: 100m (millicores), 128Mi (mebibytes), 1Gi (gibibytes), etc.
RESOURCE_FORMAT_PATTERN = re.compile(
    r'^[0-9]+(\.[0-9]+)?(m|Ki|Mi|Gi|Ti|Pi|Ei|k|M|G|T|P|E)?$'
)


class ResourceValidationError(ValueError):
    """Raised when a resource value has invalid format."""
    pass


def validate_resource_format(value: str, field_name: str) -> str:
    """Validate that a resource value conforms to Kubernetes resource format.
    
    Valid formats include:
    - Integer values: 100, 200
    - Millicores: 100m, 500m
    - Binary units: 128Ki, 256Mi, 1Gi, 2Ti, 1Pi, 1Ei
    - Decimal units: 1k, 1M, 1G, 1T, 1P, 1E
    
    Args:
        value: The resource value to validate
        field_name: Name of the field for error messages
        
    Returns:
        The validated value
        
    Raises:
        ResourceValidationError: If the value doesn't match valid format
    """
    if not RESOURCE_FORMAT_PATTERN.match(value):
        raise ResourceValidationError(
            f"Invalid resource format for {field_name}: '{value}'. "
            f"Expected format like '100m', '128Mi', '1Gi', etc."
        )
    return value


@dataclass
class ResourceLimits:
    """Kubernetes resource limits and requests.
    
    Represents CPU and memory limits/requests for a SpinApp deployment.
    All values must conform to Kubernetes resource format.
    
    Requirements: 9.1, 9.2, 9.3, 9.4
    """
    cpu_limit: Optional[str] = None
    memory_limit: Optional[str] = None
    cpu_request: Optional[str] = None
    memory_request: Optional[str] = None
    
    def __post_init__(self):
        """Validate resource formats after initialization."""
        if self.cpu_limit is not None:
            validate_resource_format(self.cpu_limit, "cpu_limit")
        if self.memory_limit is not None:
            validate_resource_format(self.memory_limit, "memory_limit")
        if self.cpu_request is not None:
            validate_resource_format(self.cpu_request, "cpu_request")
        if self.memory_request is not None:
            validate_resource_format(self.memory_request, "memory_request")
    
    def has_limits(self) -> bool:
        """Check if any limits are set."""
        return self.cpu_limit is not None or self.memory_limit is not None
    
    def has_requests(self) -> bool:
        """Check if any requests are set."""
        return self.cpu_request is not None or self.memory_request is not None
    
    def has_any(self) -> bool:
        """Check if any resource values are set."""
        return self.has_limits() or self.has_requests()


@dataclass
class SpinAppManifest:
    """SpinApp Kubernetes custom resource manifest.
    
    Represents a SpinApp CRD for deploying Spin applications to Kubernetes.
    
    Requirements: 9.1, 9.2, 9.3, 9.4, 12.1
    """
    name: str
    image: str
    namespace: str = "default"
    replicas: int = 1
    service_account: Optional[str] = None
    resources: ResourceLimits = field(default_factory=ResourceLimits)
    api_version: str = "core.spinoperator.dev/v1alpha1"
    kind: str = "SpinApp"
    
    def __post_init__(self):
        """Validate manifest fields after initialization."""
        if not self.name:
            raise ValueError("SpinApp name cannot be empty")
        if not self.image:
            raise ValueError("SpinApp image cannot be empty")
        if self.replicas < 1:
            raise ValueError("Replicas must be at least 1")
