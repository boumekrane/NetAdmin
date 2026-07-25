"""Authentication service with secure password hashing and RBAC helpers."""

from __future__ import annotations

import hashlib
import os
import secrets
import string
from contextvars import ContextVar
from datetime import datetime, timedelta
from typing import Optional, Tuple

from authorization.permissions import AuthorizationError, AuthorizationService, PermissionName
from repositories.auth_repository import AuthRepository
from models.auth_models import AuditLog, Session, User


class AuthenticationError(Exception):
    """Raised when authentication fails."""


class AccountLockedError(AuthenticationError):
    """Raised when the account is temporarily locked."""


_current_session: ContextVar[Optional[Session]] = ContextVar("current_session", default=None)


class AuthService:
    """Service for login, password management, session handling and audit logging."""

    def __init__(self, repository: AuthRepository, max_failed_attempts: int = 5, session_ttl_minutes: int = 60):
        self.repository = repository
        self.max_failed_attempts = max_failed_attempts
        self.session_ttl_minutes = session_ttl_minutes
        self.authorization_service = AuthorizationService()

    def initialize_defaults(self) -> None:
        """Ensure the repository has seeded defaults."""
        self.repository.seed_defaults()

    def bootstrap_admin_user(self) -> Optional[User]:
        """Create an initial administrator account if none exists."""
        if self.repository.get_user_by_username("admin") is not None:
            return None
        password = os.getenv("NETADMINPY_ADMIN_PASSWORD")
        if not password:
            password = self._generate_password()
        password_hash = self.hash_password(password)
        role = self.repository.get_role_by_name("Administrator")
        if role is None:
            raise AuthenticationError("Administrator role is missing.")
        user = User(username="admin", email="admin@netadminpy.local", password_hash=password_hash, is_active=True, role_id=role.id)
        self.repository.create_user(user, password_hash)
        if not os.getenv("NETADMINPY_ADMIN_PASSWORD"):
            print(f"Initial admin password: {password}")
        return user

    def login(self, username: str, password: str, remember_me: bool = False, ip_address: Optional[str] = None) -> Session:
        """Authenticate a user and create a new session."""
        username = self._normalize_username(username)
        if not username or not password:
            raise AuthenticationError("Username and password are required.")

        user = self.repository.get_user_by_username(username)
        if user is None or not user.is_active:
            self._audit_login_failure(username, ip_address, "Unknown or inactive account")
            raise AuthenticationError("Invalid username or password.")

        if self._is_locked(user):
            self._audit_login_failure(username, ip_address, "Account locked")
            raise AccountLockedError("Account is locked. Contact an administrator.")

        if not self.verify_password(password, user.password_hash or ""):
            user.failed_login_count += 1
            if user.failed_login_count >= self.max_failed_attempts:
                user.locked_until = datetime.now() + timedelta(minutes=15)
            self.repository.update_user(user)
            self._audit_login_failure(username, ip_address, "Invalid password")
            raise AuthenticationError("Invalid username or password.")

        user.failed_login_count = 0
        user.locked_until = None
        user.last_login_at = datetime.now()
        self.repository.update_user(user)

        role_name = user.role_name or "Viewer"
        permissions = self.repository.get_permissions_for_role(role_name)
        session = Session(
            session_id=self._new_session_id(),
            user_id=user.id or 0,
            username=user.username,
            role_name=role_name,
            permissions=permissions,
            login_time=datetime.now(),
            expires_at=datetime.now() + timedelta(minutes=self.session_ttl_minutes if not remember_me else self.session_ttl_minutes * 2),
            remember_me=remember_me,
        )
        self.repository.create_session(session)
        set_current_session(session)
        self._audit_event(user, "LOGIN_SUCCESS", "session", "success", ip_address, "Successful authentication")
        return session

    def logout(self, session: Optional[Session] = None, ip_address: Optional[str] = None) -> None:
        """Invalidate the given session."""
        active_session = session or get_current_session()
        if active_session is None:
            return
        self.repository.invalidate_session(active_session.session_id)
        self._audit_event_by_session(active_session, "LOGOUT", "session", "success", ip_address, "Session closed")
        clear_current_session()

    def change_password(self, session: Session, old_password: str, new_password: str, ip_address: Optional[str] = None) -> None:
        """Change the password for the authenticated user."""
        user = self.repository.get_user_by_id(session.user_id)
        if user is None:
            raise AuthenticationError("User not found.")
        if not self.verify_password(old_password, user.password_hash or ""):
            self._audit_event(user, "PASSWORD_CHANGE_FAILED", "user", "failure", ip_address, "Invalid current password")
            raise AuthenticationError("Current password is invalid.")
        self._validate_password_policy(new_password)
        self.repository.set_password_hash(user.id or 0, self.hash_password(new_password))
        self._audit_event(user, "PASSWORD_CHANGED", "user", "success", ip_address, "Password changed")

    def validate_session(self, session: Optional[Session], ip_address: Optional[str] = None) -> Optional[Session]:
        """Validate the current session and reject expired sessions."""
        if session is None:
            return None
        if session.expires_at and session.expires_at <= datetime.now():
            self.repository.invalidate_session(session.session_id)
            clear_current_session()
            self._audit_event_by_session(session, "SESSION_EXPIRED", "session", "failure", ip_address, "Session expired")
            raise AuthenticationError("Session expired. Please sign in again.")
        return session

    def activate_user(self, actor: Session, user_id: int, ip_address: Optional[str] = None) -> None:
        self._require_permission(actor, PermissionName.MANAGE_USERS)
        user = self.repository.get_user_by_id(user_id)
        if user is None:
            raise AuthenticationError("User not found.")
        user.is_active = True
        self.repository.update_user(user)
        self._audit_event(user, "USER_ACTIVATED", "user", "success", ip_address, "User activated")

    def deactivate_user(self, actor: Session, user_id: int, ip_address: Optional[str] = None) -> None:
        self._require_permission(actor, PermissionName.MANAGE_USERS)
        user = self.repository.get_user_by_id(user_id)
        if user is None:
            raise AuthenticationError("User not found.")
        user.is_active = False
        self.repository.update_user(user)
        self._audit_event(user, "USER_DEACTIVATED", "user", "success", ip_address, "User deactivated")

    def get_current_session(self) -> Optional[Session]:
        return get_current_session()

    def set_current_session(self, session: Optional[Session]) -> None:
        set_current_session(session)

    def enforce_permission(self, session: Optional[Session], permission_name: PermissionName | str) -> None:
        self.authorization_service.enforce(session, permission_name)

    def can(self, session: Optional[Session], permission_name: PermissionName | str) -> bool:
        return self.authorization_service.can(session, permission_name)

    def hash_password(self, password: str) -> str:
        salt = hashlib.sha256(secrets.token_bytes(16)).hexdigest().encode("utf-8")
        derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 200_000)
        return salt.decode("utf-8") + ":" + derived.hex()

    def verify_password(self, password: str, password_hash: str) -> bool:
        if not password_hash or ":" not in password_hash:
            return False
        salt, expected = password_hash.split(":", 1)
        derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 200_000)
        return derived.hex() == expected

    def _is_locked(self, user: User) -> bool:
        if user.locked_until is None:
            return False
        return user.locked_until > datetime.now()

    def _audit_login_failure(self, username: str, ip_address: Optional[str], reason: str) -> None:
        self.repository.log_audit(
            AuditLog(
                username=username,
                action="LOGIN_FAILED",
                target_resource="authentication",
                timestamp=datetime.now(),
                result="failure",
                ip_address=ip_address,
                details=reason,
            )
        )

    def _audit_event(self, user: User, action: str, target_resource: str, result: str, ip_address: Optional[str], details: str) -> None:
        self.repository.log_audit(
            AuditLog(
                user_id=user.id,
                username=user.username,
                action=action,
                target_resource=target_resource,
                timestamp=datetime.now(),
                result=result,
                ip_address=ip_address,
                details=details,
            )
        )

    def _audit_event_by_session(self, session: Session, action: str, target_resource: str, result: str, ip_address: Optional[str], details: str) -> None:
        self.repository.log_audit(
            AuditLog(
                user_id=session.user_id,
                username=session.username,
                action=action,
                target_resource=target_resource,
                timestamp=datetime.now(),
                result=result,
                ip_address=ip_address,
                details=details,
            )
        )

    def _require_permission(self, session: Session, permission: PermissionName) -> None:
        if not self.can(session, permission):
            raise AuthorizationError(f"Missing permission: {permission.value}")

    def _normalize_username(self, username: str) -> str:
        return username.strip().lower()

    def _new_session_id(self) -> str:
        return secrets.token_urlsafe(24)

    def _generate_password(self) -> str:
        alphabet = string.ascii_letters + string.digits
        return "".join(secrets.choice(alphabet) for _ in range(16))

    def _validate_password_policy(self, password: str) -> None:
        if len(password) < 12:
            raise AuthenticationError("Password must be at least 12 characters long.")
        if not any(char.isupper() for char in password):
            raise AuthenticationError("Password must include an uppercase character.")
        if not any(char.isdigit() for char in password):
            raise AuthenticationError("Password must include a digit.")


def get_current_session() -> Optional[Session]:
    return _current_session.get()


def set_current_session(session: Optional[Session]) -> None:
    _current_session.set(session)


def clear_current_session() -> None:
    _current_session.set(None)
