"""
NetAdminPy – Configuration globale
"""

import os
import configparser

# Chemins de base
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.path.join(BASE_DIR, "database", "database.db")
LOGS_DIR = os.path.join(BASE_DIR, "logs")
BACKUPS_DIR = os.path.join(BASE_DIR, "backups")
REPORTS_DIR = os.path.join(BASE_DIR, "reports", "output")

# Créer les répertoires si nécessaires
for d in [LOGS_DIR, BACKUPS_DIR, REPORTS_DIR, os.path.join(BASE_DIR, "database")]:
    os.makedirs(d, exist_ok=True)

# Fichier de configuration
CONFIG_FILE = os.path.join(BASE_DIR, "netadminpy.ini")

# Valeurs par défaut
DEFAULTS = {
    "network": {
        "ip_range": "192.168.1.0/24",
        "ping_timeout": "1",
        "ping_count": "2",
        "scan_threads": "50",
    },
    "monitoring": {
        "interval_seconds": "60",
        "retry_count": "2",
        "retry_delay": "5",
    },
    "ports": {
        "default_ports": "21,22,23,25,53,80,110,143,443,445,3306,3389,5432,8080,8443",
        "tcp_timeout": "1",
    },
    "ssh": {
        "default_username": "admin",
        "default_timeout": "10",
    },
    "alerts": {
        "enable_log_alerts": "true",
        "enable_popup_alerts": "true",
    },
}


def load_config() -> configparser.ConfigParser:
    config = configparser.ConfigParser()
    # Charger les defaults
    for section, values in DEFAULTS.items():
        config[section] = values
    # Lire le fichier s'il existe
    if os.path.exists(CONFIG_FILE):
        config.read(CONFIG_FILE)
    return config


def save_config(config: configparser.ConfigParser):
    with open(CONFIG_FILE, "w") as f:
        config.write(f)


# Instance globale
APP_CONFIG = load_config()

# Informations de l'application
APP_NAME = "NetAdminPy"
APP_VERSION = "1.0.0"
APP_AUTHOR = "EMSI – Projet de fin d'études"

# Couleurs thème
COLORS = {
    "primary": "#0b0f19",
    "secondary": "#0f172a",
    "accent": "#1e293b",
    "highlight": "#38bdf8",
    "success": "#10b981",
    "warning": "#f59e0b",
    "danger": "#ef4444",
    "text": "#ffffff",
    "text_muted": "#64748b",
    "online": "#10b981",
    "offline": "#ef4444",
    "unknown": "#f59e0b",
}