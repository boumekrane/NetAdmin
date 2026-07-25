"""
NetAdminPy – Gestionnaire de base de données SQLite
"""

import sqlite3
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DATABASE_PATH

logger = logging.getLogger("NetAdminPy.Database")


class DatabaseManager:
    """Gestionnaire central de la base de données SQLite."""

    def __init__(self, db_path: str = DATABASE_PATH):
        self.db_path = db_path
        self._init_database()

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=DELETE")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _init_database(self):
        """Crée les tables si elles n'existent pas."""
        with self.get_connection() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS devices (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    hostname    TEXT,
                    ip          TEXT UNIQUE NOT NULL,
                    mac         TEXT,
                    vendor      TEXT,
                    device_type TEXT DEFAULT 'Unknown',
                    os_info     TEXT,
                    status      TEXT DEFAULT 'Unknown',
                    last_seen   TEXT,
                    first_seen  TEXT,
                    comments    TEXT,
                    created_at  TEXT DEFAULT (datetime('now'))
                );

                CREATE TABLE IF NOT EXISTS ports (
                    id        INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_id INTEGER NOT NULL,
                    port      INTEGER NOT NULL,
                    state     TEXT NOT NULL,
                    service   TEXT,
                    scanned_at TEXT DEFAULT (datetime('now')),
                    FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE,
                    UNIQUE(device_id, port)
                );

                CREATE TABLE IF NOT EXISTS monitoring_history (
                    id            INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_id     INTEGER NOT NULL,
                    timestamp     TEXT DEFAULT (datetime('now')),
                    status        TEXT NOT NULL,
                    response_time REAL,
                    FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS alerts (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_id  INTEGER,
                    type       TEXT NOT NULL,
                    message    TEXT NOT NULL,
                    severity   TEXT DEFAULT 'INFO',
                    timestamp  TEXT DEFAULT (datetime('now')),
                    acknowledged INTEGER DEFAULT 0,
                    FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE SET NULL
                );

                CREATE TABLE IF NOT EXISTS backups (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_id   INTEGER NOT NULL,
                    filename    TEXT NOT NULL,
                    filepath    TEXT NOT NULL,
                    size_bytes  INTEGER,
                    created_at  TEXT DEFAULT (datetime('now')),
                    FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS scan_sessions (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    ip_range   TEXT NOT NULL,
                    started_at TEXT DEFAULT (datetime('now')),
                    finished_at TEXT,
                    hosts_found INTEGER DEFAULT 0,
                    status     TEXT DEFAULT 'running'
                );

                CREATE INDEX IF NOT EXISTS idx_devices_ip ON devices(ip);
                CREATE INDEX IF NOT EXISTS idx_devices_status ON devices(status);
                CREATE INDEX IF NOT EXISTS idx_monitoring_device ON monitoring_history(device_id);
                CREATE INDEX IF NOT EXISTS idx_monitoring_ts ON monitoring_history(timestamp);
                CREATE INDEX IF NOT EXISTS idx_alerts_device ON alerts(device_id);
                CREATE INDEX IF NOT EXISTS idx_alerts_ack ON alerts(acknowledged);
            """)
        logger.info("Base de données initialisée : %s", self.db_path)

    # ──────────────────────────────────────────
    # DEVICES
    # ──────────────────────────────────────────

    def upsert_device(self, ip: str, **kwargs) -> int:
        """Insère ou met à jour un équipement. Retourne l'ID."""
        now = datetime.now().isoformat()
        kwargs["last_seen"] = now
        with self.get_connection() as conn:
            cur = conn.execute("SELECT id, first_seen FROM devices WHERE ip = ?", (ip,))
            row = cur.fetchone()
            if row:
                device_id = row["id"]
                fields = ", ".join(f"{k} = ?" for k in kwargs)
                values = list(kwargs.values()) + [ip]
                conn.execute(f"UPDATE devices SET {fields} WHERE ip = ?", values)
            else:
                kwargs["ip"] = ip
                kwargs["first_seen"] = now
                cols = ", ".join(kwargs.keys())
                placeholders = ", ".join("?" * len(kwargs))
                cur = conn.execute(
                    f"INSERT INTO devices ({cols}) VALUES ({placeholders})",
                    list(kwargs.values()),
                )
                device_id = cur.lastrowid
        return device_id

    def get_all_devices(self) -> List[Dict]:
        with self.get_connection() as conn:
            cur = conn.execute("SELECT * FROM devices ORDER BY ip")
            return [dict(r) for r in cur.fetchall()]

    def get_device_by_id(self, device_id: int) -> Optional[Dict]:
        with self.get_connection() as conn:
            cur = conn.execute("SELECT * FROM devices WHERE id = ?", (device_id,))
            row = cur.fetchone()
            return dict(row) if row else None

    def get_device_by_ip(self, ip: str) -> Optional[Dict]:
        with self.get_connection() as conn:
            cur = conn.execute("SELECT * FROM devices WHERE ip = ?", (ip,))
            row = cur.fetchone()
            return dict(row) if row else None

    def update_device_status(self, device_id: int, status: str):
        now = datetime.now().isoformat()
        with self.get_connection() as conn:
            conn.execute(
                "UPDATE devices SET status = ?, last_seen = ? WHERE id = ?",
                (status, now, device_id),
            )

    def update_device_field(self, device_id: int, field: str, value: Any):
        with self.get_connection() as conn:
            conn.execute(f"UPDATE devices SET {field} = ? WHERE id = ?", (value, device_id))

    def delete_device(self, device_id: int):
        with self.get_connection() as conn:
            conn.execute("DELETE FROM devices WHERE id = ?", (device_id,))

    def get_device_stats(self) -> Dict:
        with self.get_connection() as conn:
            total = conn.execute("SELECT COUNT(*) FROM devices").fetchone()[0]
            online = conn.execute("SELECT COUNT(*) FROM devices WHERE status='Online'").fetchone()[0]
            offline = conn.execute("SELECT COUNT(*) FROM devices WHERE status='Offline'").fetchone()[0]
            by_type = {}
            for row in conn.execute("SELECT device_type, COUNT(*) as cnt FROM devices GROUP BY device_type"):
                by_type[row["device_type"]] = row["cnt"]
        return {"total": total, "online": online, "offline": offline, "by_type": by_type}

    # ──────────────────────────────────────────
    # PORTS
    # ──────────────────────────────────────────

    def upsert_port(self, device_id: int, port: int, state: str, service: str = ""):
        now = datetime.now().isoformat()
        with self.get_connection() as conn:
            conn.execute(
                """INSERT INTO ports (device_id, port, state, service, scanned_at)
                   VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT(device_id, port) DO UPDATE SET
                       state=excluded.state,
                       service=excluded.service,
                       scanned_at=excluded.scanned_at""",
                (device_id, port, state, service, now),
            )

    def get_ports_for_device(self, device_id: int) -> List[Dict]:
        with self.get_connection() as conn:
            cur = conn.execute(
                "SELECT * FROM ports WHERE device_id = ? ORDER BY port", (device_id,)
            )
            return [dict(r) for r in cur.fetchall()]

    def get_open_ports_count(self) -> int:
        with self.get_connection() as conn:
            return conn.execute("SELECT COUNT(*) FROM ports WHERE state='open'").fetchone()[0]

    # ──────────────────────────────────────────
    # MONITORING
    # ──────────────────────────────────────────

    def add_monitoring_record(self, device_id: int, status: str, response_time: Optional[float] = None):
        now = datetime.now().isoformat()
        with self.get_connection() as conn:
            conn.execute(
                "INSERT INTO monitoring_history (device_id, timestamp, status, response_time) VALUES (?, ?, ?, ?)",
                (device_id, now, status, response_time),
            )

    def get_monitoring_history(self, device_id: int, limit: int = 100) -> List[Dict]:
        with self.get_connection() as conn:
            cur = conn.execute(
                """SELECT * FROM monitoring_history WHERE device_id = ?
                   ORDER BY timestamp DESC LIMIT ?""",
                (device_id, limit),
            )
            return [dict(r) for r in cur.fetchall()]

    def get_recent_monitoring(self, hours: int = 24) -> List[Dict]:
        with self.get_connection() as conn:
            cur = conn.execute(
                """SELECT mh.*, d.ip, d.hostname FROM monitoring_history mh
                   JOIN devices d ON d.id = mh.device_id
                   WHERE mh.timestamp >= datetime('now', ?)
                   ORDER BY mh.timestamp DESC""",
                (f"-{hours} hours",),
            )
            return [dict(r) for r in cur.fetchall()]

    # ──────────────────────────────────────────
    # ALERTS
    # ──────────────────────────────────────────

    def add_alert(self, message: str, alert_type: str = "SYSTEM",
                  severity: str = "INFO", device_id: Optional[int] = None):
        with self.get_connection() as conn:
            conn.execute(
                "INSERT INTO alerts (device_id, type, message, severity) VALUES (?, ?, ?, ?)",
                (device_id, alert_type, message, severity),
            )

    def get_alerts(self, unread_only: bool = False, limit: int = 200) -> List[Dict]:
        with self.get_connection() as conn:
            where = "WHERE acknowledged=0" if unread_only else ""
            cur = conn.execute(
                f"""SELECT a.*, d.ip, d.hostname FROM alerts a
                    LEFT JOIN devices d ON d.id = a.device_id
                    {where} ORDER BY a.timestamp DESC LIMIT ?""",
                (limit,),
            )
            return [dict(r) for r in cur.fetchall()]

    def acknowledge_alert(self, alert_id: int):
        with self.get_connection() as conn:
            conn.execute("UPDATE alerts SET acknowledged=1 WHERE id=?", (alert_id,))

    def acknowledge_all_alerts(self):
        with self.get_connection() as conn:
            conn.execute("UPDATE alerts SET acknowledged=1")

    def get_unread_alert_count(self) -> int:
        with self.get_connection() as conn:
            return conn.execute("SELECT COUNT(*) FROM alerts WHERE acknowledged=0").fetchone()[0]

    # ──────────────────────────────────────────
    # BACKUPS
    # ──────────────────────────────────────────

    def add_backup(self, device_id: int, filename: str, filepath: str, size_bytes: int = 0):
        with self.get_connection() as conn:
            conn.execute(
                "INSERT INTO backups (device_id, filename, filepath, size_bytes) VALUES (?, ?, ?, ?)",
                (device_id, filename, filepath, size_bytes),
            )

    def get_backups(self, device_id: Optional[int] = None) -> List[Dict]:
        with self.get_connection() as conn:
            if device_id:
                cur = conn.execute(
                    """SELECT b.*, d.ip, d.hostname FROM backups b
                       JOIN devices d ON d.id = b.device_id
                       WHERE b.device_id = ? ORDER BY b.created_at DESC""",
                    (device_id,),
                )
            else:
                cur = conn.execute(
                    """SELECT b.*, d.ip, d.hostname FROM backups b
                       JOIN devices d ON d.id = b.device_id
                       ORDER BY b.created_at DESC"""
                )
            return [dict(r) for r in cur.fetchall()]

    # ──────────────────────────────────────────
    # SCAN SESSIONS
    # ──────────────────────────────────────────

    def start_scan_session(self, ip_range: str) -> int:
        with self.get_connection() as conn:
            cur = conn.execute(
                "INSERT INTO scan_sessions (ip_range) VALUES (?)", (ip_range,)
            )
            return cur.lastrowid

    def finish_scan_session(self, session_id: int, hosts_found: int):
        now = datetime.now().isoformat()
        with self.get_connection() as conn:
            conn.execute(
                "UPDATE scan_sessions SET finished_at=?, hosts_found=?, status='completed' WHERE id=?",
                (now, hosts_found, session_id),
            )

    def get_last_scan(self) -> Optional[Dict]:
        with self.get_connection() as conn:
            cur = conn.execute(
                "SELECT * FROM scan_sessions ORDER BY started_at DESC LIMIT 1"
            )
            row = cur.fetchone()
            return dict(row) if row else None