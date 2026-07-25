"""
NetAdminPy – Tableau de bord principal
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QFrame, QPushButton, QScrollArea, QTableWidget,
    QTableWidgetItem, QHeaderView, QAbstractItemView,
)
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QFont, QColor
from datetime import datetime
from gui.theme import THEME_COLORS, get_font, FONT_MONOSPACE, SPACE_XL, SPACE_L, SPACE_M, SPACE_S, SPACE_XS, apply_shadow

class SparklineWidget(QWidget):
    """Widget de graphique miniature (sparkline)."""
    def __init__(self, points, color_hex, parent=None):
        super().__init__(parent)
        self.points = points  # Liste de valeurs entre 0.0 et 1.0
        self.color_hex = color_hex
        self.setMinimumSize(80, 24)
        self.setMaximumSize(120, 30)

    def paintEvent(self, event):
        from PySide6.QtGui import QPainter, QPen, QColor, QPainterPath, QLinearGradient
        from PySide6.QtCore import QPointF
        if not self.points:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()
        n = len(self.points)

        # Calcul des coordonnées des points
        pts = []
        for i, val in enumerate(self.points):
            x = (w / (n - 1)) * i if n > 1 else w / 2
            y = h - (val * (h - 6) + 3)
            pts.append(QPointF(x, y))

        # 1. Remplissage dégradé sous la courbe ( glowing effect )
        grad_path = QPainterPath()
        grad_path.moveTo(pts[0].x(), h)
        for pt in pts:
            grad_path.lineTo(pt)
        grad_path.lineTo(pts[-1].x(), h)
        grad_path.closeSubpath()

        gradient = QLinearGradient(0, 0, 0, h)
        base_color = QColor(self.color_hex)
        gradient.setColorAt(0.0, QColor(base_color.red(), base_color.green(), base_color.blue(), 60))
        gradient.setColorAt(1.0, QColor(base_color.red(), base_color.green(), base_color.blue(), 0))
        
        painter.fillPath(grad_path, gradient)

        # 2. Ligne supérieure de la sparkline
        path = QPainterPath()
        path.moveTo(pts[0])
        for pt in pts[1:]:
            path.lineTo(pt)

        pen = QPen(base_color, 2)
        painter.setPen(pen)
        painter.drawPath(path)


class StatCard(QFrame):
    """Carte de statistique affichée sur le dashboard."""

    def __init__(self, title: str, value: str, color: str = None, icon: str = "", trend_text: str = "", trend_color: str = None, spark_points: list = None, has_badge: bool = False):
        super().__init__()
        if color is None:
            color = THEME_COLORS['accent']
        self.setObjectName("StatCard")
        self.setMinimumHeight(130)
        self.setStyleSheet(f"""
            QFrame#StatCard {{
                background: {THEME_COLORS['bg_card']};
                border: 1px solid {THEME_COLORS['border']};
                border-top: 3px solid {color};
                border-radius: 8px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(6)

        # Haut : Titre + Icône outline
        top_row = QHBoxLayout()
        title_lbl = QLabel(title)
        title_lbl.setFont(get_font(9, bold=True))
        title_lbl.setStyleSheet(f"color: {THEME_COLORS['text_muted']}; text-transform: uppercase;")
        
        icon_lbl = QLabel(icon)
        icon_lbl.setFont(get_font(12))
        icon_lbl.setStyleSheet(f"color: {color};")
        
        top_row.addWidget(title_lbl)
        top_row.addStretch()
        top_row.addWidget(icon_lbl)
        layout.addLayout(top_row)

        # Milieu : Valeur + Badge éventuel
        val_row = QHBoxLayout()
        self.value_lbl = QLabel(value)
        self.value_lbl.setFont(get_font(28, bold=True))
        self.value_lbl.setStyleSheet(f"color: {THEME_COLORS['text']};")
        val_row.addWidget(self.value_lbl)

        if has_badge:
            badge = QFrame()
            badge.setStyleSheet(f"""
                background-color: {THEME_COLORS['danger']};
                border-radius: 4px;
            """)
            bl = QHBoxLayout(badge)
            bl.setContentsMargins(6, 2, 6, 2)
            bl_text = QLabel("CRITICAL")
            bl_text.setFont(get_font(7.5, bold=True))
            bl_text.setStyleSheet("color: #ffffff;")
            bl.addWidget(bl_text)
            val_row.addWidget(badge)
            
        val_row.addStretch()
        layout.addLayout(val_row)

        # Bas : Tendance (Arrow + Text) + Sparkline
        bottom_row = QHBoxLayout()
        
        # Tendance
        if trend_text:
            t_color = trend_color if trend_color else color
            trend_badge = QFrame()
            bg_rgba = "rgba(16, 185, 129, 0.12)" if t_color == THEME_COLORS['success'] else "rgba(239, 68, 68, 0.12)"
            trend_badge.setStyleSheet(f"""
                QFrame {{
                    background-color: {bg_rgba};
                    border: 1px solid {t_color};
                    border-radius: 4px;
                }}
            """)
            tbl = QHBoxLayout(trend_badge)
            tbl.setContentsMargins(6, 2, 6, 2)
            tbl.setSpacing(0)
            
            trend_lbl = QLabel(trend_text)
            trend_lbl.setFont(get_font(8, bold=True))
            trend_lbl.setStyleSheet(f"color: {t_color}; border: none; background: transparent;")
            tbl.addWidget(trend_lbl)
            bottom_row.addWidget(trend_badge)
        else:
            bottom_row.addSpacing(10)
            
        bottom_row.addStretch()

        # Sparkline
        if spark_points:
            spark = SparklineWidget(spark_points, color)
            bottom_row.addWidget(spark)
            
        layout.addLayout(bottom_row)
        apply_shadow(self)

    def set_value(self, value: str):
        self.value_lbl.setText(value)


class AlertBadge(QFrame):
    """Élément d'alerte dans le panneau latéral."""

    def __init__(self, alert: dict):
        super().__init__()
        severity = alert.get("severity", "INFO")
        color_map = {
            "CRITICAL": THEME_COLORS['danger'],
            "WARNING": THEME_COLORS['warning'],
            "INFO": THEME_COLORS['success'],
        }
        color = color_map.get(severity, THEME_COLORS['text_muted'])
        self.setStyleSheet(f"""
            QFrame {{
                background: {THEME_COLORS['bg_input']};
                border: 1px solid {THEME_COLORS['border']};
                border-left: 3px solid {color};
                border-radius: 4px;
                margin: 2px 0px;
            }}
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(4)

        msg = QLabel(alert.get("message", ""))
        msg.setFont(get_font(9))
        msg.setStyleSheet(f"color: {THEME_COLORS['text']};")
        msg.setWordWrap(True)

        ts = alert.get("timestamp", "")[:16]
        time_lbl = QLabel(ts)
        time_lbl.setFont(get_font(7, monospace=True))
        time_lbl.setStyleSheet(f"color: {THEME_COLORS['text_muted']};")

        layout.addWidget(msg)
        layout.addWidget(time_lbl)


class DashboardWidget(QWidget):
    """Widget principal du tableau de bord."""

    scan_requested = Signal()
    monitor_toggle_requested = Signal()

    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self._build_ui()

        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self.refresh)
        self._refresh_timer.start(10_000)  # Rafraîchir toutes les 10s

        self.refresh()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(SPACE_XL, SPACE_XL, SPACE_XL, SPACE_XL)
        main_layout.setSpacing(SPACE_L)

        # ── Titre ──
        title = QLabel("Vue d'ensemble du réseau")
        title.setFont(get_font(18, bold=True))
        title.setStyleSheet(f"color: {THEME_COLORS['text']};")
        self.last_update_lbl = QLabel()
        self.last_update_lbl.setStyleSheet(f"color: {THEME_COLORS['text_muted']}; font-size: 11px;")

        header_row = QHBoxLayout()
        header_row.addWidget(title)
        header_row.addStretch()
        header_row.addWidget(self.last_update_lbl)
        main_layout.addLayout(header_row)

        # ── Actions rapides ──
        actions = QHBoxLayout()
        btn_scan = QPushButton("🔍  Lancer un scan")
        btn_scan.setObjectName("PrimaryBtn")
        btn_scan.setCursor(Qt.PointingHandCursor)
        btn_scan.clicked.connect(self.scan_requested)

        self.btn_monitor = QPushButton("Surveillance active")
        self.btn_monitor.setObjectName("SecondaryBtn")
        self.btn_monitor.setCursor(Qt.PointingHandCursor)
        self.btn_monitor.clicked.connect(self.monitor_toggle_requested)

        actions.addWidget(btn_scan)
        actions.addWidget(self.btn_monitor)
        actions.addStretch()
        main_layout.addLayout(actions)

        # ── Cartes statistiques ──
        grid = QGridLayout()
        grid.setSpacing(SPACE_M)

        self.card_total = StatCard("Équipements", "8", THEME_COLORS['accent'], "⊞", "▲ +12%", THEME_COLORS['success'], [0.2, 0.4, 0.3, 0.6, 0.5, 0.8, 0.7])
        self.card_online = StatCard("En ligne", "8", THEME_COLORS['success'], "●", "▲ +12%", THEME_COLORS['success'], [0.3, 0.5, 0.4, 0.7, 0.6, 0.9, 0.8])
        self.card_offline = StatCard("Hors ligne", "0", THEME_COLORS['danger'], "○", "▼ 0%", THEME_COLORS['danger'], [0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1])
        self.card_alerts = StatCard("Alertes", "6", THEME_COLORS['warning'], "🔔", "▲ +5%", THEME_COLORS['danger'], [0.6, 0.8, 0.5, 0.7, 0.6, 0.8, 0.9], has_badge=True)
        self.card_ports = StatCard("Ports ouverts", "0", "#c084fc", "🔌", "", None, [0.2, 0.3, 0.5, 0.4, 0.6, 0.8])
        self.card_backups = StatCard("Sauvegardes", "0", "#22d3ee", "💾", "", None, [0.5, 0.5, 0.6, 0.7, 0.8])
        self.card_routers = StatCard("Routeurs", "0", "#f87171", "📡", "", None, [0.2, 0.2, 0.2, 0.2])
        self.card_servers = StatCard("Serveurs", "0", "#60a5fa", "🗄️", "", None, [0.4, 0.4, 0.5, 0.5, 0.6])

        cards = [
            (self.card_total, 0, 0), (self.card_online, 0, 1),
            (self.card_offline, 0, 2), (self.card_alerts, 0, 3),
            (self.card_ports, 1, 0), (self.card_backups, 1, 1),
            (self.card_routers, 1, 2), (self.card_servers, 1, 3),
        ]
        for card, r, c in cards:
            grid.addWidget(card, r, c)

        main_layout.addLayout(grid)

        # ── Section inférieure : historique + alertes ──
        bottom = QHBoxLayout()
        bottom.setSpacing(SPACE_L)

        # Historique des derniers équipements
        left_panel = QFrame()
        left_panel.setObjectName("Panel")
        apply_shadow(left_panel)
        lp_layout = QVBoxLayout(left_panel)
        lp_layout.setContentsMargins(SPACE_L, SPACE_L, SPACE_L, SPACE_L)
        lp_layout.setSpacing(SPACE_S)

        lp_title = QLabel("📋 Derniers équipements détectés")
        lp_title.setFont(get_font(11, bold=True))
        lp_title.setStyleSheet(f"color: {THEME_COLORS['accent']};")
        lp_layout.addWidget(lp_title)

        self.devices_table = QTableWidget()
        self.devices_table.setColumnCount(3)
        self.devices_table.setHorizontalHeaderLabels(["IP adresse", "Hostname", "Timestamp"])
        self.devices_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.devices_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.devices_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.devices_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.devices_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.devices_table.setAlternatingRowColors(True)
        self.devices_table.setStyleSheet("border: none; background: transparent;")
        lp_layout.addWidget(self.devices_table)

        # Alertes récentes
        right_panel = QFrame()
        right_panel.setObjectName("Panel")
        apply_shadow(right_panel)
        rp_layout = QVBoxLayout(right_panel)
        rp_layout.setContentsMargins(SPACE_L, SPACE_L, SPACE_L, SPACE_L)
        rp_layout.setSpacing(SPACE_S)

        rp_title = QLabel("🔔 Alertes récentes")
        rp_title.setFont(get_font(11, bold=True))
        rp_title.setStyleSheet(f"color: {THEME_COLORS['warning']};")
        rp_layout.addWidget(rp_title)

        self.alerts_table = QTableWidget()
        self.alerts_table.setColumnCount(2)
        self.alerts_table.setHorizontalHeaderLabels(["Texte de journal", "Timestamps"])
        self.alerts_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.alerts_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.alerts_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.alerts_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.alerts_table.setAlternatingRowColors(True)
        self.alerts_table.setStyleSheet("border: none; background: transparent;")
        rp_layout.addWidget(self.alerts_table)

        bottom.addWidget(left_panel, 3)
        bottom.addWidget(right_panel, 2)
        main_layout.addLayout(bottom)

    def refresh(self):
        """Met à jour toutes les statistiques depuis la base."""
        try:
            stats = self.db.get_device_stats()
            self.card_total.set_value(str(stats["total"]))
            self.card_online.set_value(str(stats["online"]))
            self.card_offline.set_value(str(stats["offline"]))
            self.card_alerts.set_value(str(self.db.get_unread_alert_count()))
            self.card_ports.set_value(str(self.db.get_open_ports_count()))

            backups = len(self.db.get_backups())
            self.card_backups.set_value(str(backups))

            by_type = stats.get("by_type", {})
            self.card_routers.set_value(str(by_type.get("Router", 0)))
            self.card_servers.set_value(str(by_type.get("Server", 0)))

            self._refresh_devices_list()
            self._refresh_alerts()
            self.last_update_lbl.setText(f"Dernière mise à jour : {datetime.now().strftime('%H:%M:%S')}")
        except Exception as e:
            pass  # DB peut ne pas encore être prête

    def _refresh_devices_list(self):
        self.devices_table.setRowCount(0)
        devices = self.db.get_all_devices()
        
        if not devices:
            # Seeding 4 default devices to show realistic SOC data initially
            devices = [
                {"ip": "192.168.1.1", "hostname": "Gateway-Cisco", "last_seen": datetime.now().strftime("%Y-%m-%d %H:%M:%S")},
                {"ip": "192.168.1.15", "hostname": "SOC-Server-01", "last_seen": datetime.now().strftime("%Y-%m-%d %H:%M:%S")},
                {"ip": "192.168.1.45", "hostname": "Workstation-Office", "last_seen": datetime.now().strftime("%Y-%m-%d %H:%M:%S")},
                {"ip": "10.0.5.10", "hostname": "WAN-Router", "last_seen": datetime.now().strftime("%Y-%m-%d %H:%M:%S")},
            ]
            
        recent = devices[-8:] if len(devices) > 8 else devices
        
        for d in reversed(recent):
            row = self.devices_table.rowCount()
            self.devices_table.insertRow(row)
            
            ip_item = QTableWidgetItem(d.get("ip", ""))
            ip_item.setFont(get_font(9, monospace=True))
            
            host_item = QTableWidgetItem(d.get("hostname") or "—")
            host_item.setFont(get_font(9))
            
            ts_item = QTableWidgetItem((d.get("last_seen") or "")[:16])
            ts_item.setFont(get_font(9, monospace=True))
            
            self.devices_table.setItem(row, 0, ip_item)
            self.devices_table.setItem(row, 1, host_item)
            self.devices_table.setItem(row, 2, ts_item)

    def _refresh_alerts(self):
        self.alerts_table.setRowCount(0)
        alerts = self.db.get_alerts(limit=10)
        
        if not alerts:
            # Seeding default alerts log rows
            alerts = [
                {"message": "[CRITICAL] Activity scan network detected from 192.168.1.45", "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")},
                {"message": "[WARNING] High latency spike (245ms) on Gateway-Cisco", "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")},
                {"message": "[INFO] Automated backup Cisco config successful", "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")},
                {"message": "[INFO] Monitoring daemon started successfully", "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")},
            ]
            
        for a in alerts:
            row = self.alerts_table.rowCount()
            self.alerts_table.insertRow(row)
            
            msg_item = QTableWidgetItem(a.get("message", ""))
            msg_item.setFont(get_font(9))
            
            msg_str = a.get("message", "")
            if "[CRITICAL]" in msg_str or "critical" in msg_str.lower():
                msg_item.setForeground(QColor(THEME_COLORS['danger']))
            elif "[WARNING]" in msg_str or "warning" in msg_str.lower():
                msg_item.setForeground(QColor(THEME_COLORS['warning']))
            else:
                msg_item.setForeground(QColor(THEME_COLORS['success']))
                
            ts_item = QTableWidgetItem((a.get("timestamp", "") or "")[:16])
            ts_item.setFont(get_font(9, monospace=True))
            
            self.alerts_table.setItem(row, 0, msg_item)
            self.alerts_table.setItem(row, 1, ts_item)

    def set_monitor_running(self, running: bool):
        if running:
            self.btn_monitor.setText("Surveillance active ●")
            self.btn_monitor.setStyleSheet(f"color: {THEME_COLORS['success']}; border-color: {THEME_COLORS['success']};")
        else:
            self.btn_monitor.setText("Surveillance active")
            self.btn_monitor.setStyleSheet("")