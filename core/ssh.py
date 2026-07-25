"""
NetAdminPy – Module SSH / Sauvegarde Cisco
Utilise paramiko (SSH natif) ou netmiko (multi-vendor CLI).
"""

import os
import logging
import re
from datetime import datetime
from typing import Optional, Tuple

logger = logging.getLogger("NetAdminPy.SSH")


def _try_import_netmiko():
    try:
        from netmiko import ConnectHandler
        return ConnectHandler
    except ImportError:
        return None


def _try_import_paramiko():
    try:
        import paramiko
        return paramiko
    except ImportError:
        return None


class SSHClient:
    """Client SSH générique (paramiko)."""

    def __init__(self, host: str, username: str, password: str,
                 port: int = 22, timeout: int = 10):
        self.host = host
        self.username = username
        self.password = password
        self.port = port
        self.timeout = timeout
        self._client = None

    def connect(self) -> Tuple[bool, str]:
        paramiko = _try_import_paramiko()
        if paramiko is None:
            return False, "paramiko non installé. Exécutez : pip install paramiko"

        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(
                self.host,
                username=self.username,
                password=self.password,
                port=self.port,
                timeout=self.timeout,
                look_for_keys=False,
                allow_agent=False,
            )
            self._client = client
            logger.info("SSH connecté à %s", self.host)
            return True, "Connexion réussie"
        except Exception as e:
            logger.error("SSH échec %s : %s", self.host, e)
            return False, str(e)

    def execute(self, command: str) -> Tuple[str, str]:
        if not self._client:
            return "", "Non connecté"
        try:
            _, stdout, stderr = self._client.exec_command(command, timeout=30)
            out = stdout.read().decode(errors="replace")
            err = stderr.read().decode(errors="replace")
            return out, err
        except Exception as e:
            return "", str(e)

    def disconnect(self):
        if self._client:
            self._client.close()
            self._client = None


class CiscoBackup:
    """Sauvegarde des configurations Cisco via SSH/Netmiko."""

    CISCO_COMMANDS = {
        "ios": "show running-config",
        "ios-xe": "show running-config",
        "ios-xr": "show running-config",
        "nxos": "show running-config",
        "asa": "show running-config",
    }

    def __init__(self, backup_dir: str):
        self.backup_dir = backup_dir

    def backup_device(
        self,
        host: str,
        username: str,
        password: str,
        device_type: str = "cisco_ios",
        port: int = 22,
        timeout: int = 30,
    ) -> Tuple[bool, str, str]:
        """
        Sauvegarde la config running d'un équipement Cisco.
        Retourne (succès, chemin_fichier, message).
        """
        ConnectHandler = _try_import_netmiko()

        if ConnectHandler:
            return self._backup_netmiko(
                host, username, password, device_type, port, timeout
            )
        else:
            logger.warning("netmiko non disponible, tentative via paramiko")
            return self._backup_paramiko(host, username, password, port, timeout)

    def _backup_netmiko(self, host, username, password, device_type, port, timeout):
        try:
            from netmiko import ConnectHandler

            conn = ConnectHandler(
                device_type=device_type,
                host=host,
                username=username,
                password=password,
                port=port,
                timeout=timeout,
                session_timeout=timeout,
            )
            output = conn.send_command("show running-config", read_timeout=30)
            conn.disconnect()

            filepath = self._save_config(host, output)
            return True, filepath, f"Sauvegarde réussie ({len(output)} caractères)"
        except Exception as e:
            logger.error("Backup Netmiko %s : %s", host, e)
            return False, "", str(e)

    def _backup_paramiko(self, host, username, password, port, timeout):
        client = SSHClient(host, username, password, port, timeout)
        ok, msg = client.connect()
        if not ok:
            return False, "", msg
        try:
            output, err = client.execute("show running-config")
            if err and not output:
                return False, "", f"Erreur SSH : {err}"
            filepath = self._save_config(host, output)
            return True, filepath, f"Sauvegarde réussie ({len(output)} caractères)"
        finally:
            client.disconnect()

    def _save_config(self, host: str, content: str) -> str:
        """Enregistre la configuration dans backups/<host>/YYYY-MM-DD.txt"""
        safe_host = re.sub(r"[^\w.\-]", "_", host)
        host_dir = os.path.join(self.backup_dir, safe_host)
        os.makedirs(host_dir, exist_ok=True)

        date_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"{date_str}.txt"
        filepath = os.path.join(host_dir, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(f"! Sauvegarde NetAdminPy\n")
            f.write(f"! Équipement : {host}\n")
            f.write(f"! Date       : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"!\n")
            f.write(content)

        logger.info("Config sauvegardée : %s", filepath)
        return filepath