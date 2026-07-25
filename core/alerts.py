"""
NetAdminPy – Système d'alertes
"""

import logging
from typing import Callable, List, Optional
from datetime import datetime

logger = logging.getLogger("NetAdminPy.Alerts")


class AlertManager:
    """
    Gère les alertes de l'application.
    Peut notifier via callbacks (UI popup, son, etc.)
    """

    SEVERITY_LEVELS = {"DEBUG": 0, "INFO": 1, "WARNING": 2, "CRITICAL": 3}

    def __init__(self, db_manager, min_severity: str = "INFO"):
        self.db = db_manager
        self.min_severity = min_severity
        self._callbacks: List[Callable] = []

    def register_callback(self, fn: Callable):
        """Enregistre une fonction appelée à chaque alerte."""
        self._callbacks.append(fn)

    def fire(
        self,
        message: str,
        alert_type: str = "SYSTEM",
        severity: str = "INFO",
        device_id: Optional[int] = None,
    ):
        """Déclenche une alerte."""
        if self.SEVERITY_LEVELS.get(severity, 0) < self.SEVERITY_LEVELS.get(self.min_severity, 0):
            return

        # Persister en base
        self.db.add_alert(message, alert_type=alert_type, severity=severity, device_id=device_id)

        # Logger
        log_fn = {
            "DEBUG": logger.debug,
            "INFO": logger.info,
            "WARNING": logger.warning,
            "CRITICAL": logger.critical,
        }.get(severity, logger.info)
        log_fn("[%s] %s", alert_type, message)

        # Notifier les callbacks
        payload = {
            "message": message,
            "type": alert_type,
            "severity": severity,
            "device_id": device_id,
            "timestamp": datetime.now().isoformat(),
        }
        for cb in self._callbacks:
            try:
                cb(payload)
            except Exception as e:
                logger.error("Erreur callback alerte : %s", e)

    # Raccourcis
    def info(self, message: str, **kwargs):
        self.fire(message, severity="INFO", **kwargs)

    def warning(self, message: str, **kwargs):
        self.fire(message, severity="WARNING", **kwargs)

    def critical(self, message: str, **kwargs):
        self.fire(message, severity="CRITICAL", **kwargs)

    def device_offline(self, device: dict):
        ip = device.get("ip", "?")
        name = device.get("hostname") or ip
        self.fire(
            f"⚠️  {name} ({ip}) est HORS LIGNE",
            alert_type="DEVICE_DOWN",
            severity="CRITICAL",
            device_id=device.get("id"),
        )

    def device_online(self, device: dict, rtt: float):
        ip = device.get("ip", "?")
        name = device.get("hostname") or ip
        self.fire(
            f"✅  {name} ({ip}) est de nouveau EN LIGNE (RTT: {rtt:.1f}ms)",
            alert_type="DEVICE_UP",
            severity="INFO",
            device_id=device.get("id"),
        )

    def scan_complete(self, ip_range: str, count: int):
        self.fire(
            f"🔍  Scan terminé sur {ip_range} : {count} équipement(s) découvert(s)",
            alert_type="SCAN",
            severity="INFO",
        )

    def backup_created(self, host: str, path: str):
        self.fire(
            f"💾  Sauvegarde créée pour {host} → {path}",
            alert_type="BACKUP",
            severity="INFO",
        )