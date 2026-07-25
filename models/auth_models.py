"""Authentication and authorization domain models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional


class PermissionName(str, Enum):
    """Canonical permission names used across the application."""

    SCAN_NETWORK = "SCAN_NETWORK"
    VIEW_INVENTORY = "VIEW_INVENTORY"
    EDIT_DEVICE = "EDIT_DEVICE"
    DELETE_DEVICE = "DELETE_DEVICE"
    BACKUP_CONFIGURATION = "BACKUP_CONFIGURATION"
    RESTORE_CONFIGURATION = "RESTORE_CONFIGURATION"
    EXPORT_REPORT = "EXPORT_REPORT"
    VIEW_REPORT = "VIEW_REPORT"
    RUN_AI_ANALYSIS = "RUN_AI_ANALYSIS"
    MANAGE_USERS = "MANAGE_USERS"
    VIEW_AUDIT = "VIEW_AUDIT"
    SYSTEM_CONFIGURATION = "SYSTEM_CONFIGURATION"


@dataclass(slots=True)
class Permission:
    """Represents a single permission definition."""

    id: Optional[int] = None
    name: str = ""
    description: str = ""


@dataclass(slots=True)
class Role:
    """Represents a business role that aggregates permissions."""

    id: Optional[int] = None
    name: str = ""
    description: str = ""
    permissions: List[Permission] = field(default_factory=list)


@dataclass(slots=True)
class User:
    """Represents an application user account."""

    id: Optional[int] = None
    username: str = ""
    email: Optional[str] = None
    password_hash: Optional[str] = None
    is_active: bool = True
    role_id: Optional[int] = None
    role_name: Optional[str] = None
    failed_login_count: int = 0
    locked_until: Optional[datetime] = None
    last_login_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass(slots=True)
class Session:
    """Represents an authenticated user session."""

    session_id: str = ""
    user_id: int = 0
    username: str = ""
    role_name: str = ""
    permissions: List[str] = field(default_factory=list)
    login_time: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    remember_me: bool = False


@dataclass(slots=True)
class AuditLog:
    """Represents an immutable audit record."""

    id: Optional[int] = None
    user_id: Optional[int] = None
    username: Optional[str] = None
    action: str = ""
    target_resource: str = ""
    timestamp: Optional[datetime] = None
    result: str = ""
    ip_address: Optional[str] = None
    details: Optional[str] = None
