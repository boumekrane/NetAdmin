"""
NetAdminPy – Module de monitoring (surveillance continue)
"""

import logging
import threading
import time
from datetime import datetime
from typing import Dict, List, Optional, Callable

from core.scanner import ping_host

logger = logging.getLogger("NetAdminPy.Monitor")


class DeviceMonitor:
    """
    Surveille en permanence les équipements enregistrés.
    Toutes les `interval` secondes, il ping chaque device.
    """

    def __init__(
        self,
        db_manager,
        interval: int = 60,
        retry_count: int = 2,
        retry_delay: int = 5,
        timeout: float = 1.5,
        on_status_change: Optional[Callable] = None,
        on_alert: Optional[Callable] = None,
    ):
        self.db = db_manager
        self.interval = interval
        self.retry_count = retry_count
        self.retry_delay = retry_delay
        self.timeout = timeout
        self.on_status_change = on_status_change
        self.on_alert = on_alert

        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._device_states: Dict[int, str] = {}  # device_id → dernier status

    # ──────────────────────────────────────────
    # Contrôle
    # ──────────────────────────────────────────

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="MonitorThread")
        self._thread.start()
        logger.info("Monitoring démarré (intervalle : %ds)", self.interval)

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("Monitoring arrêté")

    def is_running(self) -> bool:
        return self._running

    # ──────────────────────────────────────────
    # Boucle principale
    # ──────────────────────────────────────────

    def _loop(self):
        while self._running:
            try:
                self._check_all_devices()
            except Exception as e:
                logger.error("Erreur monitoring : %s", e)
            # Attendre interval secondes (interruptible)
            for _ in range(self.interval * 10):
                if not self._running:
                    return
                time.sleep(0.1)

    def _check_all_devices(self):
        devices = self.db.get_all_devices()
        if not devices:
            return
        logger.debug("Vérification de %d équipements…", len(devices))

        for device in devices:
            if not self._running:
                return
            self._check_device(device)

    def _check_device(self, device: Dict):
        device_id = device["id"]
        ip = device["ip"]
        previous_status = self._device_states.get(device_id, device.get("status", "Unknown"))

        # Premier essai
        rtt = ping_host(ip, timeout=self.timeout)

        # Retry si échec
        if rtt is None:
            for attempt in range(self.retry_count):
                time.sleep(self.retry_delay)
                rtt = ping_host(ip, timeout=self.timeout)
                if rtt is not None:
                    break

        new_status = "Online" if rtt is not None else "Offline"

        # Enregistrer dans l'historique
        self.db.add_monitoring_record(device_id, new_status, rtt)
        self.db.update_device_status(device_id, new_status)
        self._device_states[device_id] = new_status

        # Détecter un changement d'état
        if previous_status != new_status:
            logger.info(
                "Changement d'état : %s (%s) → %s",
                device.get("hostname") or ip,
                ip,
                new_status,
            )
            self._handle_status_change(device, previous_status, new_status, rtt)

    def _handle_status_change(self, device: Dict, old_status: str, new_status: str, rtt):
        device_id = device["id"]
        ip = device["ip"]
        name = device.get("hostname") or ip

        if new_status == "Offline":
            severity = "CRITICAL"
            msg = f"⚠️  {name} ({ip}) est maintenant HORS LIGNE"
        else:
            severity = "INFO"
            msg = f"✅  {name} ({ip}) est de nouveau EN LIGNE (RTT: {rtt:.1f}ms)"

        self.db.add_alert(msg, alert_type="STATUS_CHANGE", severity=severity, device_id=device_id)

        if self.on_alert:
            self.on_alert({"message": msg, "severity": severity, "device": device})

        if self.on_status_change:
            self.on_status_change(device, old_status, new_status, rtt)

    # ──────────────────────────────────────────
    # Stats temps réel
    # ──────────────────────────────────────────

    def get_current_states(self) -> Dict[int, str]:
        return dict(self._device_states)

    def force_check(self, device: Dict) -> Dict:
        """Force un ping immédiat sur un équipement."""
        ip = device["ip"]
        rtt = ping_host(ip, timeout=self.timeout)
        status = "Online" if rtt is not None else "Offline"
        return {"ip": ip, "status": status, "response_time": rtt, "checked_at": datetime.now().isoformat()}