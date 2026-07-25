"""SQLite-backed repository for authentication entities."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta
from typing import List, Optional

from database.db_manager import DatabaseManager
from models.auth_models import AuditLog, Permission, Role, Session, User


class AuthRepository:
    """Repository for users, roles, permissions, sessions and audit logs."""

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.initialize_schema()
        self.seed_defaults()

    def initialize_schema(self) -> None:
        """Create the authentication schema if it does not exist."""
        with self.db_manager.get_connection() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS roles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    description TEXT,
                    created_at TEXT DEFAULT (datetime('now'))
                );

                CREATE TABLE IF NOT EXISTS permissions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    description TEXT,
                    created_at TEXT DEFAULT (datetime('now'))
                );

                CREATE TABLE IF NOT EXISTS role_permissions (
                    role_id INTEGER NOT NULL,
                    permission_id INTEGER NOT NULL,
                    PRIMARY KEY (role_id, permission_id),
                    FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE,
                    FOREIGN KEY (permission_id) REFERENCES permissions(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL UNIQUE,
                    email TEXT,
                    password_hash TEXT NOT NULL,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    role_id INTEGER,
                    failed_login_count INTEGER NOT NULL DEFAULT 0,
                    locked_until TEXT,
                    last_login_at TEXT,
                    created_at TEXT DEFAULT (datetime('now')),
                    updated_at TEXT DEFAULT (datetime('now')),
                    FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE SET NULL
                );

                CREATE TABLE IF NOT EXISTS user_sessions (
                    session_id TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    created_at TEXT DEFAULT (datetime('now')),
                    expires_at TEXT NOT NULL,
                    last_seen TEXT,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    remember_me INTEGER NOT NULL DEFAULT 0,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS audit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    username TEXT,
                    action TEXT NOT NULL,
                    target_resource TEXT NOT NULL,
                    timestamp TEXT DEFAULT (datetime('now')),
                    result TEXT NOT NULL,
                    ip_address TEXT,
                    details TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
                );

                CREATE INDEX IF NOT EXISTS idx_users_role_id ON users(role_id);
                CREATE INDEX IF NOT EXISTS idx_user_sessions_user ON user_sessions(user_id);
                CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp ON audit_logs(timestamp);
                """
            )

    def seed_defaults(self) -> None:
        """Seed default roles and permissions if the database is empty."""
        with self.db_manager.get_connection() as conn:
            permission_names = [
                ("SCAN_NETWORK", "Scan network devices"),
                ("VIEW_INVENTORY", "View inventory"),
                ("EDIT_DEVICE", "Edit device records"),
                ("DELETE_DEVICE", "Delete device records"),
                ("BACKUP_CONFIGURATION", "Create configuration backups"),
                ("RESTORE_CONFIGURATION", "Restore configurations"),
                ("EXPORT_REPORT", "Export reports"),
                ("VIEW_REPORT", "View reports"),
                ("RUN_AI_ANALYSIS", "Run AI analysis"),
                ("MANAGE_USERS", "Manage users"),
                ("VIEW_AUDIT", "View audit logs"),
                ("SYSTEM_CONFIGURATION", "Manage system settings"),
            ]
            for name, description in permission_names:
                conn.execute(
                    "INSERT OR IGNORE INTO permissions (name, description) VALUES (?, ?)",
                    (name, description),
                )

            role_permissions = {
                "Administrator": permission_names,
                "Network Operator": [
                    ("SCAN_NETWORK", "Scan network devices"),
                    ("VIEW_INVENTORY", "View inventory"),
                    ("EDIT_DEVICE", "Edit device records"),
                    ("BACKUP_CONFIGURATION", "Create configuration backups"),
                    ("VIEW_REPORT", "View reports"),
                    ("EXPORT_REPORT", "Export reports"),
                ],
                "Security Analyst": [
                    ("VIEW_INVENTORY", "View inventory"),
                    ("VIEW_REPORT", "View reports"),
                    ("EXPORT_REPORT", "Export reports"),
                    ("RUN_AI_ANALYSIS", "Run AI analysis"),
                    ("VIEW_AUDIT", "View audit logs"),
                ],
                "Viewer": [
                    ("VIEW_INVENTORY", "View inventory"),
                    ("VIEW_REPORT", "View reports"),
                ],
            }

            for role_name, permission_list in role_permissions.items():
                conn.execute(
                    "INSERT OR IGNORE INTO roles (name, description) VALUES (?, ?)",
                    (role_name, f"Built-in {role_name} role"),
                )
                role_row = conn.execute(
                    "SELECT id FROM roles WHERE name = ?", (role_name,)
                ).fetchone()
                role_id = role_row[0]
                for permission_name, _ in permission_list:
                    permission_row = conn.execute(
                        "SELECT id FROM permissions WHERE name = ?", (permission_name,)
                    ).fetchone()
                    if permission_row is None:
                        continue
                    permission_id = permission_row[0]
                    conn.execute(
                        "INSERT OR IGNORE INTO role_permissions (role_id, permission_id) VALUES (?, ?)",
                        (role_id, permission_id),
                    )

    def get_user_by_username(self, username: str) -> Optional[User]:
        with self.db_manager.get_connection() as conn:
            row = conn.execute(
                """
                SELECT u.*, r.name as role_name
                FROM users u
                LEFT JOIN roles r ON r.id = u.role_id
                WHERE u.username = ?
                """,
                (username,),
            ).fetchone()
            if row is None:
                return None
            return self._row_to_user(row)

    def get_user_by_id(self, user_id: int) -> Optional[User]:
        with self.db_manager.get_connection() as conn:
            row = conn.execute(
                """
                SELECT u.*, r.name as role_name
                FROM users u
                LEFT JOIN roles r ON r.id = u.role_id
                WHERE u.id = ?
                """,
                (user_id,),
            ).fetchone()
            if row is None:
                return None
            return self._row_to_user(row)

    def create_user(self, user: User, password_hash: str) -> User:
        with self.db_manager.get_connection() as conn:
            cur = conn.execute(
                """
                INSERT INTO users (
                    username, email, password_hash, is_active, role_id,
                    failed_login_count, locked_until, last_login_at, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user.username,
                    user.email,
                    password_hash,
                    int(user.is_active),
                    user.role_id,
                    user.failed_login_count,
                    user.locked_until.isoformat() if user.locked_until else None,
                    user.last_login_at.isoformat() if user.last_login_at else None,
                    user.created_at.isoformat() if user.created_at else datetime.now().isoformat(),
                    user.updated_at.isoformat() if user.updated_at else datetime.now().isoformat(),
                ),
            )
            user.id = cur.lastrowid
            return user

    def update_user(self, user: User) -> None:
        with self.db_manager.get_connection() as conn:
            conn.execute(
                """
                UPDATE users
                SET username = ?, email = ?, password_hash = ?, is_active = ?, role_id = ?,
                    failed_login_count = ?, locked_until = ?, last_login_at = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    user.username,
                    user.email,
                    user.password_hash,
                    int(user.is_active),
                    user.role_id,
                    user.failed_login_count,
                    user.locked_until.isoformat() if user.locked_until else None,
                    user.last_login_at.isoformat() if user.last_login_at else None,
                    datetime.now().isoformat(),
                    user.id,
                ),
            )

    def set_password_hash(self, user_id: int, password_hash: str) -> None:
        with self.db_manager.get_connection() as conn:
            conn.execute(
                "UPDATE users SET password_hash = ?, updated_at = ? WHERE id = ?",
                (password_hash, datetime.now().isoformat(), user_id),
            )

    def get_role_by_name(self, role_name: str) -> Optional[Role]:
        with self.db_manager.get_connection() as conn:
            row = conn.execute(
                "SELECT id, name, description FROM roles WHERE name = ?",
                (role_name,),
            ).fetchone()
            if row is None:
                return None
            return Role(id=row[0], name=row[1], description=row[2])

    def get_permissions_for_role(self, role_name: str) -> List[str]:
        with self.db_manager.get_connection() as conn:
            rows = conn.execute(
                """
                SELECT p.name
                FROM role_permissions rp
                JOIN roles r ON r.id = rp.role_id
                JOIN permissions p ON p.id = rp.permission_id
                WHERE r.name = ?
                ORDER BY p.name
                """,
                (role_name,),
            ).fetchall()
            return [row[0] for row in rows]

    def create_session(self, session: Session) -> None:
        with self.db_manager.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO user_sessions (session_id, user_id, expires_at, last_seen, is_active, remember_me)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    session.session_id,
                    session.user_id,
                    session.expires_at.isoformat() if session.expires_at else None,
                    session.login_time.isoformat() if session.login_time else None,
                    1,
                    int(session.remember_me),
                ),
            )

    def invalidate_session(self, session_id: str) -> None:
        with self.db_manager.get_connection() as conn:
            conn.execute(
                "UPDATE user_sessions SET is_active = 0 WHERE session_id = ?",
                (session_id,),
            )

    def get_session(self, session_id: str) -> Optional[Session]:
        with self.db_manager.get_connection() as conn:
            row = conn.execute(
                "SELECT us.*, u.username, r.name as role_name FROM user_sessions us JOIN users u ON u.id=us.user_id LEFT JOIN roles r ON r.id=u.role_id WHERE us.session_id = ?",
                (session_id,),
            ).fetchone()
            if row is None:
                return None
            permissions = self.get_permissions_for_role(row["role_name"])
            return Session(
                session_id=row["session_id"],
                user_id=row["user_id"],
                username=row["username"],
                role_name=row["role_name"],
                permissions=permissions,
                login_time=datetime.fromisoformat(row["created_at"]),
                expires_at=datetime.fromisoformat(row["expires_at"]),
                remember_me=bool(row["remember_me"]),
            )

    def log_audit(self, audit_log: AuditLog) -> None:
        with self.db_manager.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO audit_logs (
                    user_id, username, action, target_resource, timestamp, result, ip_address, details
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    audit_log.user_id,
                    audit_log.username,
                    audit_log.action,
                    audit_log.target_resource,
                    audit_log.timestamp.isoformat() if audit_log.timestamp else datetime.now().isoformat(),
                    audit_log.result,
                    audit_log.ip_address,
                    audit_log.details,
                ),
            )

    def get_recent_audit(self, limit: int = 100) -> List[AuditLog]:
        with self.db_manager.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM audit_logs ORDER BY timestamp DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [self._row_to_audit_log(row) for row in rows]

    def _row_to_user(self, row: sqlite3.Row) -> User:
        locked_until = None
        if row["locked_until"]:
            locked_until = datetime.fromisoformat(row["locked_until"])
        last_login_at = None
        if row["last_login_at"]:
            last_login_at = datetime.fromisoformat(row["last_login_at"])
        return User(
            id=row["id"],
            username=row["username"],
            email=row["email"],
            password_hash=row["password_hash"],
            is_active=bool(row["is_active"]),
            role_id=row["role_id"],
            role_name=row["role_name"],
            failed_login_count=row["failed_login_count"],
            locked_until=locked_until,
            last_login_at=last_login_at,
        )

    def _row_to_audit_log(self, row: sqlite3.Row) -> AuditLog:
        timestamp = None
        if row["timestamp"]:
            timestamp = datetime.fromisoformat(row["timestamp"])
        return AuditLog(
            id=row["id"],
            user_id=row["user_id"],
            username=row["username"],
            action=row["action"],
            target_resource=row["target_resource"],
            timestamp=timestamp,
            result=row["result"],
            ip_address=row["ip_address"],
            details=row["details"],
        )
