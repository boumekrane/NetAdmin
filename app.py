"""
NetAdminPy – Point d'entrée principal
Plateforme d'automatisation de l'administration réseau
EMSI – Projet de fin d'études 3IIR
"""

import sys
import os
import logging
from datetime import datetime

# ── Logging ──────────────────────────────────────────────
LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)-20s] %(levelname)-8s %(message)s",
    handlers=[
        logging.FileHandler(
            os.path.join(LOG_DIR, f"netadminpy_{datetime.now().strftime('%Y%m%d')}.log"),
            encoding="utf-8",
        ),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("NetAdminPy")

# ── Qt / PySide6 ──────────────────────────────────────────
try:
    from PySide6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QLabel, QPushButton, QStackedWidget, QFrame, QSizePolicy,
        QMessageBox, QSystemTrayIcon, QMenu, QLineEdit,
    )
    from PySide6.QtCore import Qt, QTimer, Signal
    from PySide6.QtGui import QFont, QIcon, QPixmap, QColor, QPalette
except ImportError:
    print("ERREUR : PySide6 n'est pas installé.")
    print("Exécutez : pip install PySide6")
    sys.exit(1)

from config import APP_NAME, APP_VERSION, COLORS, APP_CONFIG
from database.db_manager import DatabaseManager
from core.monitor import DeviceMonitor
from core.alerts import AlertManager
from gui.dashboard import DashboardWidget
from gui.scanner import ScannerWidget
from gui.monitoring import MonitoringWidget
from gui.inventory import InventoryWidget
from gui.reports import ReportsWidget
from gui.login import LoginWindow
from gui.theme import THEME_COLORS, GLOBAL_QSS, get_font, apply_shadow
from repositories.auth_repository import AuthRepository
from services.auth_service import AuthService, AuthenticationError
from authorization.permissions import PermissionName



# ════════════════════════════════════════════════════════════
# NAV BUTTON (barre latérale)
# ════════════════════════════════════════════════════════════

class NavButton(QPushButton):
    def __init__(self, icon: str, label: str):
        super().__init__(f"{icon}  {label}")
        self.setCheckable(True)
        self.setMinimumHeight(48)
        self.setCursor(Qt.PointingHandCursor)
        self.setFont(get_font(11))
        self.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {THEME_COLORS['text_muted']};
                border: none;
                border-left: 3px solid transparent;
                border-radius: 0px;
                text-align: left;
                padding: 10px 18px;
            }}
            QPushButton:hover {{
                background: rgba(255, 255, 255, 0.04);
                color: {THEME_COLORS['text']};
                border-left: 3px solid rgba(255, 255, 255, 0.15);
            }}
            QPushButton:checked {{
                background: rgba(56, 189, 248, 0.08);
                color: {THEME_COLORS['accent']};
                border-left: 3px solid {THEME_COLORS['accent']};
                font-weight: bold;
            }}
        """)


# ════════════════════════════════════════════════════════════
# FENÊTRE PRINCIPALE
# ════════════════════════════════════════════════════════════

class MainWindow(QMainWindow):

    def __init__(self, auth_service: AuthService, session):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.resize(1300, 800)
        self.setMinimumSize(1024, 680)

        self.auth_service = auth_service
        self.session = session

        # ── Services ──────────────────────────────────────
        self.db = DatabaseManager()
        self.alert_mgr = AlertManager(self.db)
        self.monitor = DeviceMonitor(
            db_manager=self.db,
            interval=int(APP_CONFIG.get("monitoring", "interval_seconds", fallback=60)),
            retry_count=int(APP_CONFIG.get("monitoring", "retry_count", fallback=2)),
            on_alert=self._on_monitor_alert,
        )
        self.alert_mgr.register_callback(self._on_alert_fired)

        # ── UI ────────────────────────────────────────────
        self._build_ui()
        self._apply_permission_state()
        self._nav_buttons[0].setChecked(True)

        # Timer rafraîchissement badge alertes
        self._badge_timer = QTimer(self)
        self._badge_timer.timeout.connect(self._update_alert_badge)
        self._badge_timer.start(8_000)
        self._update_alert_badge()

        # Synchro indicateur monitoring au démarrage
        if self.monitor.is_running():
            self.monitor_text.setText("Monitoring actif")
            self.monitor_icon.setStyleSheet(f"color: {THEME_COLORS['success']};")
            self.monitor_card.setStyleSheet(f"border-color: {THEME_COLORS['success']};")
        else:
            self.monitor_text.setText("Monitoring arrêté")
            self.monitor_icon.setStyleSheet(f"color: {THEME_COLORS['danger']};")
            self.monitor_card.setStyleSheet(f"border-color: {THEME_COLORS['danger']};")

        logger.info("%s v%s démarré", APP_NAME, APP_VERSION)
        self.alert_mgr.info(f"{APP_NAME} v{APP_VERSION} démarré.")

    # ── Construction UI ──────────────────────────────────

    def _build_ui(self):
        central = QWidget()
        central.setObjectName("CentralWidget")
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Barre latérale ──
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(220)
        sb_layout = QVBoxLayout(sidebar)
        sb_layout.setContentsMargins(16, 16, 16, 16)
        sb_layout.setSpacing(8)

        # Logo
        logo_frame = QFrame()
        logo_frame.setFixedHeight(80)
        logo_layout = QVBoxLayout(logo_frame)
        logo_layout.setContentsMargins(8, 0, 8, 8)
        app_name_lbl = QLabel(APP_NAME)
        app_name_lbl.setFont(get_font(16, bold=True))
        app_name_lbl.setStyleSheet(f"color: {THEME_COLORS['accent']};")
        version_lbl = QLabel(f"v{APP_VERSION} ({APP_CONFIG.get('network', 'ip_range', fallback='Network Tool')})")
        version_lbl.setFont(get_font(8))
        version_lbl.setStyleSheet(f"color: #64748b;")
        logo_layout.addWidget(app_name_lbl)
        logo_layout.addWidget(version_lbl)
        sb_layout.addWidget(logo_frame)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet(f"color: {THEME_COLORS['border']};")
        sb_layout.addWidget(sep)
        sb_layout.addSpacing(8)

        # Navigation groupées par catégories
        categories = [
            ("DASHBOARD", [
                ("⊞", "Tableau de bord", self._show_dashboard)
            ]),
            ("NETWORK TOOLKIT", [
                ("⌕", "Scanner", self._show_scanner),
                ("⚡", "Monitoring", self._show_monitoring)
            ]),
            ("ALERTS & LOGS", [
                ("▤", "Inventaire", self._show_inventory)
            ]),
            ("FORMS & REPORTS", [
                ("🗎", "Rapports", self._show_reports)
            ])
        ]
        self._nav_buttons = []
        self._nav_group = []

        for cat_name, items in categories:
            cat_lbl = QLabel(cat_name)
            cat_lbl.setFont(get_font(8, bold=True))
            cat_lbl.setStyleSheet(f"color: #64748b; margin-top: 14px; margin-bottom: 4px; padding-left: 8px; text-transform: uppercase;")
            sb_layout.addWidget(cat_lbl)
            
            for icon, label, fn in items:
                btn = NavButton(icon, label)
                btn.clicked.connect(lambda checked, f=fn, b=btn: self._nav_click(f, b))
                sb_layout.addWidget(btn)
                self._nav_buttons.append(btn)

        sb_layout.addStretch()

        # Status Badge Cards (petite carte visuelle)
        self.alert_card = QFrame()
        self.alert_card.setObjectName("StatusBadgeCard")
        self.alert_card.setFixedHeight(44)
        ac_layout = QHBoxLayout(self.alert_card)
        ac_layout.setContentsMargins(12, 6, 12, 6)
        ac_layout.setSpacing(8)
        self.alert_icon = QLabel("🔔")
        self.alert_icon.setFont(get_font(10))
        self.alert_icon.setStyleSheet(f"color: {THEME_COLORS['text_muted']};")
        self.alert_text = QLabel("0 alertes")
        self.alert_text.setFont(get_font(9))
        self.alert_text.setStyleSheet(f"color: {THEME_COLORS['text_muted']};")
        ac_layout.addWidget(self.alert_icon)
        ac_layout.addWidget(self.alert_text, 1)
        sb_layout.addWidget(self.alert_card)

        self.monitor_card = QFrame()
        self.monitor_card.setObjectName("StatusBadgeCard")
        self.monitor_card.setFixedHeight(44)
        mc_layout = QHBoxLayout(self.monitor_card)
        mc_layout.setContentsMargins(12, 6, 12, 6)
        mc_layout.setSpacing(8)
        self.monitor_icon = QLabel("●")
        self.monitor_icon.setFont(get_font(11))
        self.monitor_icon.setStyleSheet(f"color: {THEME_COLORS['danger']};")
        self.monitor_text = QLabel("Monitoring arrêté")
        self.monitor_text.setFont(get_font(9))
        self.monitor_text.setStyleSheet(f"color: {THEME_COLORS['text_muted']};")
        mc_layout.addWidget(self.monitor_icon)
        mc_layout.addWidget(self.monitor_text, 1)
        sb_layout.addWidget(self.monitor_card)

        apply_shadow(self.alert_card)
        apply_shadow(self.monitor_card)
        
        root.addWidget(sidebar)

        # ── Zone principale de droite ──
        main_container = QWidget()
        main_layout = QVBoxLayout(main_container)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ── Barre supérieure (Header Bar) ──
        header_bar = QFrame()
        header_bar.setObjectName("HeaderBar")
        header_bar.setFixedHeight(50)
        header_bar.setStyleSheet(f"""
            QFrame#HeaderBar {{
                background-color: rgba(15, 23, 42, 0.45);
                border-bottom: 1px solid {THEME_COLORS['border']};
            }}
        """)
        hb_layout = QHBoxLayout(header_bar)
        hb_layout.setContentsMargins(16, 0, 16, 0)

        # Gauche: Logo de rouage et de fiole, suivi du texte 'NetAdminPy v1.0.0'
        left_lbl = QLabel("⚙⚗ NetAdminPy v1.0.0")
        left_lbl.setFont(get_font(10, bold=True))
        left_lbl.setStyleSheet(f"color: {THEME_COLORS['accent']};")
        hb_layout.addWidget(left_lbl)

        hb_layout.addStretch()

        # Centre: Barre de recherche sombre centrée avec loupe
        search_frame = QFrame()
        search_frame.setObjectName("SearchBarFrame")
        search_frame.setFixedWidth(280)
        search_frame.setStyleSheet(f"""
            QFrame#SearchBarFrame {{
                background-color: rgba(9, 13, 22, 0.6);
                border: 1px solid {THEME_COLORS['border']};
                border-radius: 14px;
            }}
        """)
        sf_layout = QHBoxLayout(search_frame)
        sf_layout.setContentsMargins(10, 2, 10, 2)
        sf_layout.setSpacing(6)

        search_icon = QLabel("⌕")
        search_icon.setFont(get_font(11))
        search_icon.setStyleSheet(f"color: {THEME_COLORS['text_muted']};")

        search_input = QLineEdit()
        search_input.setPlaceholderText("Recherche...")
        search_input.setStyleSheet("background: transparent; border: none; color: #ffffff; padding: 0;")

        sf_layout.addWidget(search_icon)
        sf_layout.addWidget(search_input)
        hb_layout.addWidget(search_frame)

        hb_layout.addStretch()

        # Droite: Cluster d'icônes d'action
        cluster_widget = QWidget()
        cluster_layout = QHBoxLayout(cluster_widget)
        cluster_layout.setContentsMargins(0, 0, 0, 0)
        cluster_layout.setSpacing(16)

        self.user_status_label = QLabel(f"{self.session.username} • {self.session.role_name}")
        self.user_status_label.setFont(get_font(9, bold=True))
        self.user_status_label.setStyleSheet(f"color: {THEME_COLORS['accent']};")
        cluster_layout.addWidget(self.user_status_label)

        self.logout_button = QPushButton("Logout")
        self.logout_button.clicked.connect(self._logout)
        self.logout_button.setStyleSheet("padding: 6px 12px;")
        cluster_layout.addWidget(self.logout_button)

        # Cloche avec badge rouge "6"
        notif_container = QWidget()
        notif_layout = QHBoxLayout(notif_container)
        notif_layout.setContentsMargins(0, 0, 0, 0)
        notif_layout.setSpacing(2)

        bell_icon = QLabel("🔔")
        bell_icon.setFont(get_font(11))

        badge_lbl = QLabel("6")
        badge_lbl.setFont(get_font(7.5, bold=True))
        badge_lbl.setAlignment(Qt.AlignCenter)
        badge_lbl.setStyleSheet(f"""
            background-color: {THEME_COLORS['danger']};
            color: #ffffff;
            border-radius: 7px;
            padding: 1px 4px;
            min-width: 14px;
            max-height: 14px;
        """)

        notif_layout.addWidget(bell_icon)
        notif_layout.addWidget(badge_lbl)
        cluster_layout.addWidget(notif_container)

        hb_layout.addWidget(cluster_widget)
        main_layout.addWidget(header_bar)

        # ── Zone de contenu ──
        self._stack = QStackedWidget()

        self._dashboard = DashboardWidget(self.db)
        self._dashboard.scan_requested.connect(self._show_scanner)
        self._dashboard.monitor_toggle_requested.connect(self._toggle_monitoring_from_dashboard)

        self._scanner = ScannerWidget(self.db, self.alert_mgr)
        self._scanner.devices_updated.connect(self._dashboard.refresh)

        self._monitoring = MonitoringWidget(self.db, self.monitor)
        self._inventory = InventoryWidget(self.db)
        self._reports = ReportsWidget(self.db)

        self._stack.addWidget(self._dashboard)
        self._stack.addWidget(self._scanner)
        self._stack.addWidget(self._monitoring)
        self._stack.addWidget(self._inventory)
        self._stack.addWidget(self._reports)

        main_layout.addWidget(self._stack)

        # Footer
        footer = QFrame()
        footer.setObjectName("FooterBar")
        footer.setFixedHeight(24)
        footer.setStyleSheet(f"""
            QFrame#FooterBar {{
                background-color: rgba(15, 23, 42, 0.45);
                border-top: 1px solid {THEME_COLORS['border']};
            }}
        """)
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(16, 0, 16, 0)
        copyright_lbl = QLabel("© 2023. IndusRocker Technologies. Tous droits réservés.")
        copyright_lbl.setFont(get_font(8))
        copyright_lbl.setStyleSheet(f"color: {THEME_COLORS['text_muted']};")
        footer_layout.addWidget(copyright_lbl)
        footer_layout.addStretch()
        main_layout.addWidget(footer)

        root.addWidget(main_container)

    # ── Navigation ───────────────────────────────────────

    def _nav_click(self, fn, clicked_btn):
        for btn in self._nav_buttons:
            btn.setChecked(False)
        clicked_btn.setChecked(True)
        fn()

    def _apply_permission_state(self):
        permission_map = {
            self._nav_buttons[0]: None,
            self._nav_buttons[1]: PermissionName.SCAN_NETWORK,
            self._nav_buttons[2]: PermissionName.SCAN_NETWORK,
            self._nav_buttons[3]: PermissionName.VIEW_INVENTORY,
            self._nav_buttons[4]: PermissionName.VIEW_REPORT,
        }
        for button, permission in permission_map.items():
            if permission is None:
                button.setEnabled(True)
                continue
            button.setEnabled(self.auth_service.can(self.session, permission))

    def _logout(self):
        self.auth_service.logout(self.session)
        self.close()

    def _show_dashboard(self):
        self._stack.setCurrentWidget(self._dashboard)
        self._dashboard.refresh()

    def _show_scanner(self):
        self._stack.setCurrentWidget(self._scanner)

    def _show_monitoring(self):
        self._stack.setCurrentWidget(self._monitoring)

    def _show_inventory(self):
        self._stack.setCurrentWidget(self._inventory)
        self._inventory.refresh()

    def _show_reports(self):
        self._stack.setCurrentWidget(self._reports)

    # ── Monitoring ───────────────────────────────────────

    def _toggle_monitoring_from_dashboard(self):
        if self.monitor.is_running():
            self.monitor.stop()
            self._dashboard.set_monitor_running(False)
            self.monitor_text.setText("Monitoring arrêté")
            self.monitor_icon.setStyleSheet(f"color: {THEME_COLORS['danger']};")
            self.monitor_card.setStyleSheet(f"border-color: {THEME_COLORS['danger']};")
        else:
            self.monitor.start()
            self._dashboard.set_monitor_running(True)
            self.monitor_text.setText("Monitoring actif")
            self.monitor_icon.setStyleSheet(f"color: {THEME_COLORS['success']};")
            self.monitor_card.setStyleSheet(f"border-color: {THEME_COLORS['success']};")

    # ── Alertes ──────────────────────────────────────────

    def _on_monitor_alert(self, payload: dict):
        self._update_alert_badge()
        self._dashboard.refresh()

    def _on_alert_fired(self, payload: dict):
        self._update_alert_badge()

    def _update_alert_badge(self):
        count = self.db.get_unread_alert_count()
        self.alert_text.setText(f"{count} alerte{'s' if count != 1 else ''}")
        if count > 0:
            self.alert_icon.setStyleSheet(f"color: {THEME_COLORS['warning']}; font-weight: bold;")
            self.alert_text.setStyleSheet(f"color: {THEME_COLORS['text']}; font-weight: bold;")
            self.alert_card.setStyleSheet(f"border-color: {THEME_COLORS['warning']};")
        else:
            self.alert_icon.setStyleSheet(f"color: {THEME_COLORS['text_muted']};")
            self.alert_text.setStyleSheet(f"color: {THEME_COLORS['text_muted']};")
            self.alert_card.setStyleSheet("")

    # ── Fermeture ────────────────────────────────────────

    def closeEvent(self, event):
        if self.monitor.is_running():
            self.monitor.stop()
        logger.info("Application fermée.")
        event.accept()

    def paintEvent(self, event):
        from PySide6.QtGui import QPainter
        painter = QPainter(self)
        bg_path = os.path.join(os.path.dirname(__file__), "industrial_bg.png")
        if os.path.exists(bg_path):
            pixmap = QPixmap(bg_path)
            painter.drawPixmap(self.rect(), pixmap)
        else:
            painter.fillRect(self.rect(), QColor("#0b0f19"))


# ════════════════════════════════════════════════════════════
# LANCEMENT
# ════════════════════════════════════════════════════════════

def main():
    pyqt_plugin_dir = None
    try:
        import PySide6
        from pathlib import Path
        base = Path(PySide6.__file__).resolve().parent
        candidates = [
            base / "plugins",
            base / "plugins" / "platforms",
            base.parent / "PySide6" / "plugins",
            base.parent / "PySide6" / "plugins" / "platforms",
        ]
        for candidate in candidates:
            if candidate.exists():
                pyqt_plugin_dir = str(candidate)
                break
    except Exception:
        pyqt_plugin_dir = None

    if pyqt_plugin_dir:
        os.environ.setdefault("QT_PLUGIN_PATH", pyqt_plugin_dir)
        os.environ.setdefault("QT_QPA_PLATFORM_PLUGIN_PATH", pyqt_plugin_dir)

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setStyleSheet(GLOBAL_QSS)

    # Palette sombre
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(THEME_COLORS['bg_window']))
    palette.setColor(QPalette.WindowText, QColor(THEME_COLORS['text']))
    palette.setColor(QPalette.Base, QColor(THEME_COLORS['bg_input']))
    palette.setColor(QPalette.AlternateBase, QColor(THEME_COLORS['bg_container']))
    palette.setColor(QPalette.Text, QColor(THEME_COLORS['text']))
    palette.setColor(QPalette.Button, QColor(THEME_COLORS['bg_card']))
    palette.setColor(QPalette.ButtonText, QColor(THEME_COLORS['text']))
    palette.setColor(QPalette.Highlight, QColor(THEME_COLORS['accent']))
    palette.setColor(QPalette.HighlightedText, QColor(THEME_COLORS['bg_window']))
    app.setPalette(palette)

    db = DatabaseManager()
    auth_repository = AuthRepository(db)
    auth_service = AuthService(auth_repository)
    auth_service.initialize_defaults()
    auth_service.bootstrap_admin_user()

    login_dialog = LoginWindow(auth_service)
    if login_dialog.exec() != 1 or login_dialog.session is None:
        sys.exit(0)

    try:
        auth_service.validate_session(login_dialog.session)
    except AuthenticationError:
        QMessageBox.critical(None, "Session Expired", "Your session has expired. Please sign in again.")
        sys.exit(0)

    window = MainWindow(auth_service, login_dialog.session)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()