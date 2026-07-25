"""Authorization primitives for permission-based access control."""

from __future__ import annotations

from functools import wraps
from typing import Callable, Optional, Union

from models.auth_models import PermissionName, Session


class AuthorizationError(Exception):
    """Raised when an authenticated user lacks a required permission."""


class AuthorizationService:
    """Central service for evaluating permissions against an active session."""

    def can(self, session: Optional[Session], permission_name: Union[PermissionName, str]) -> bool:
        if session is None:
            return False
        if session.role_name == "Administrator":
            return True
        permission_value = permission_name.value if isinstance(permission_name, PermissionName) else permission_name
        return permission_value in set(session.permissions)

    def enforce(self, session: Optional[Session], permission_name: Union[PermissionName, str]) -> None:
        if not self.can(session, permission_name):
            raise AuthorizationError(f"Missing permission: {permission_name}")


def require_permission(permission_name: Union[PermissionName, str]):
    """Decorator that ensures the active session has the required permission."""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            from services.auth_service import get_current_session

            session = get_current_session()
            service = AuthorizationService()
            if not service.can(session, permission_name):
                raise AuthorizationError(f"Missing permission: {permission_name}")
            return func(*args, **kwargs)

        return wrapper

    return decorator
