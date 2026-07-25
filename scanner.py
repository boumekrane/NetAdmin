"""
NetAdminPy – Scanner réseau (découverte + ports)
"""

import socket
import ipaddress
import logging
import subprocess
import platform
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Optional, Callable
from datetime import datetime

logger = logging.getLogger("NetAdminPy.Scanner")

# Table OUI (MAC vendor) partielle – enrichie via socket
COMMON_VENDORS = {
    "00:50:56": "VMware",
    "00:0c:29": "VMware",
    "00:1a:11": "Google",
    "b8:27:eb": "Raspberry Pi",
    "dc:a6:32": "Raspberry Pi",
    "00:1b:21": "Intel",
    "00:23:ae": "Cisco",
    "00:1e:13": "Cisco",
    "fc:fb:fb": "Cisco",
    "00:90:0b": "Apple",
    "ac:bc:32": "Apple",
    "3c:22:fb": "Apple",
    "00:26:b9": "Dell",
    "f0:1f:af": "Dell",
    "00:50:ba": "D-Link",
    "00:1c:f0": "D-Link",
    "00:08:9f": "TP-Link",
    "50:c7:bf": "TP-Link",
    "00:18:f3": "ASUSTek",
    "04:92:26": "ASUSTek",
    "00:0d:0b": "HP",
    "00:17:a4": "HP",
    "00:21:5a": "HP",
}


def get_vendor_from_mac(mac: str) -> str:
    if not mac:
        return "Unknown"
    prefix = mac[:8].lower()
    for oui, vendor in COMMON_VENDORS.items():
        if prefix == oui.lower():
            return vendor
    return "Unknown"


def ping_host(ip: str, timeout: float = 1.0, count: int = 1) -> Optional[float]:
    """
    Ping une IP. Retourne le temps de réponse en ms, ou None si offline.
    Compatible Linux/Windows/macOS.
    """
    system = platform.system().lower()
    if system == "windows":
        cmd = ["ping", "-n", str(count), "-w", str(int(timeout * 1000)), ip]
    else:
        cmd = ["ping", "-c", str(count), "-W", str(int(timeout)), ip]

    try:
        start = time.time()
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout + 2,
        )
        elapsed = (time.time() - start) * 1000  # ms
        if result.returncode == 0:
            return round(elapsed, 2)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return None


def get_mac_from_arp(ip: str) -> Optional[str]:
    """Récupère l'adresse MAC via la table ARP."""
    system = platform.system().lower()
    try:
        if system == "windows":
            out = subprocess.check_output(["arp", "-a", ip], timeout=3,
                                           stderr=subprocess.DEVNULL).decode()
            match = re.search(r"([\da-fA-F]{2}[:-]){5}[\da-fA-F]{2}", out)
        else:
            out = subprocess.check_output(["arp", "-n", ip], timeout=3,
                                           stderr=subprocess.DEVNULL).decode()
            match = re.search(r"([\da-fA-F]{2}[:-]){5}[\da-fA-F]{2}", out)
        if match:
            return match.group(0).replace("-", ":").upper()
    except Exception:
        pass
    return None


def resolve_hostname(ip: str) -> str:
    try:
        return socket.gethostbyaddr(ip)[0]
    except socket.herror:
        return ""


class NetworkScanner:
    """Découverte et scan d'un réseau."""

    def __init__(self, config=None):
        self.config = config
        self._stop_flag = False

    def stop(self):
        self._stop_flag = True

    def discover_network(
        self,
        ip_range: str,
        threads: int = 50,
        timeout: float = 1.0,
        progress_callback: Optional[Callable] = None,
        result_callback: Optional[Callable] = None,
    ) -> List[Dict]:
        """
        Découvre tous les hôtes actifs dans la plage IP.
        progress_callback(current, total, host_info)
        result_callback(host_info)  → appelé dès qu'un hôte est trouvé
        """
        self._stop_flag = False
        try:
            network = ipaddress.ip_network(ip_range, strict=False)
        except ValueError as e:
            logger.error("Plage IP invalide : %s – %s", ip_range, e)
            return []

        hosts = list(network.hosts())
        total = len(hosts)
        found = []
        processed = 0

        logger.info("Découverte réseau : %s (%d hôtes)", ip_range, total)

        def scan_one(ip_obj):
            ip = str(ip_obj)
            rtt = ping_host(ip, timeout=timeout)
            if rtt is not None:
                mac = get_mac_from_arp(ip) or ""
                hostname = resolve_hostname(ip)
                vendor = get_vendor_from_mac(mac)
                info = {
                    "ip": ip,
                    "hostname": hostname,
                    "mac": mac,
                    "vendor": vendor,
                    "response_time": rtt,
                    "status": "Online",
                    "last_seen": datetime.now().isoformat(),
                }
                return info
            return None

        with ThreadPoolExecutor(max_workers=threads) as executor:
            futures = {executor.submit(scan_one, ip): ip for ip in hosts}
            for future in as_completed(futures):
                if self._stop_flag:
                    executor.shutdown(wait=False, cancel_futures=True)
                    break
                processed += 1
                result = future.result()
                if result:
                    found.append(result)
                    if result_callback:
                        result_callback(result)
                if progress_callback:
                    progress_callback(processed, total, result)

        logger.info("Découverte terminée : %d hôtes trouvés sur %d", len(found), total)
        return found


# ──────────────────────────────────────────────────────────
# SCANNER DE PORTS
# ──────────────────────────────────────────────────────────

COMMON_SERVICES = {
    21: "FTP", 22: "SSH", 23: "Telnet", 25: "SMTP",
    53: "DNS", 80: "HTTP", 110: "POP3", 143: "IMAP",
    443: "HTTPS", 445: "SMB", 3306: "MySQL", 3389: "RDP",
    5432: "PostgreSQL", 5900: "VNC", 8080: "HTTP-Alt", 8443: "HTTPS-Alt",
    161: "SNMP", 162: "SNMP-Trap", 179: "BGP", 514: "Syslog",
    69: "TFTP", 67: "DHCP", 68: "DHCP",
}


def scan_port(ip: str, port: int, timeout: float = 1.0) -> Dict:
    """Teste si un port TCP est ouvert."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(timeout)
            result = s.connect_ex((ip, port))
            state = "open" if result == 0 else "closed"
    except (socket.timeout, OSError):
        state = "filtered"
    return {
        "port": port,
        "state": state,
        "service": COMMON_SERVICES.get(port, "Unknown"),
    }


class PortScanner:
    """Scanner de ports TCP multi-threadé."""

    DEFAULT_PORTS = [21, 22, 23, 25, 53, 80, 110, 143, 443, 445,
                     3306, 3389, 5432, 5900, 8080, 8443]

    def __init__(self, timeout: float = 1.0, threads: int = 100):
        self.timeout = timeout
        self.threads = threads
        self._stop_flag = False

    def stop(self):
        self._stop_flag = True

    def scan_host(
        self,
        ip: str,
        ports: Optional[List[int]] = None,
        progress_callback: Optional[Callable] = None,
    ) -> List[Dict]:
        """Scanne une liste de ports sur une IP."""
        self._stop_flag = False
        if ports is None:
            ports = self.DEFAULT_PORTS

        results = []
        total = len(ports)
        done = 0

        with ThreadPoolExecutor(max_workers=self.threads) as executor:
            futures = {executor.submit(scan_port, ip, p, self.timeout): p for p in ports}
            for future in as_completed(futures):
                if self._stop_flag:
                    executor.shutdown(wait=False, cancel_futures=True)
                    break
                done += 1
                result = future.result()
                results.append(result)
                if progress_callback:
                    progress_callback(done, total, result)

        results.sort(key=lambda x: x["port"])
        open_count = sum(1 for r in results if r["state"] == "open")
        logger.info("%s – %d/%d ports ouverts", ip, open_count, len(results))
        return results

    def scan_range(
        self,
        ip: str,
        start_port: int = 1,
        end_port: int = 1024,
        progress_callback: Optional[Callable] = None,
    ) -> List[Dict]:
        ports = list(range(start_port, end_port + 1))
        return self.scan_host(ip, ports, progress_callback)