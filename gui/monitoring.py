"""
NetAdminPy – Interface de monitoring
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QFrame,
    QGroupBox, QSpinBox, QAbstractItemView, QSplitter,
)
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QFont, QColor
from datetime import datetime
from gui.theme import THEME_COLORS, get_font, FONT_MONOSPACE, SPACE_XL, SPACE_L, SPACE_M, SPACE_S, SPACE_XS, apply_shadow


class MonitoringWidget(QWidget):
    """Panneau de supervision des équipements."""

    def __init__(self, db_manager, device_monitor=None, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.monitor = device_monitor
        self._build_ui()

        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self.refresh)
        self._refresh_timer.start(5_000)  # Rafraîchir toutes les 5s
        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACE_XL, SPACE_XL, SPACE_XL, SPACE_XL)
        layout.setSpacing(SPACE_L)

        # ── En-tête ──
        header = QHBoxLayout()
        title = QLabel("📡 Monitoring en temps réel")
        title.setFont(get_font(18, bold=True))
        title.setStyleSheet(f"color: {THEME_COLORS['text']};")
        header.addWidget(title)
        header.addStretch()

        self.status_lbl = QLabel("● Arrêté")
        self.status_lbl.setStyleSheet(f"color: {THEME_COLORS['danger']}; font-size: 13px; font-weight: bold;")
        header.addWidget(self.status_lbl)
        layout.addLayout(header)

        # ── Contrôles ──
        ctrl_box = QGroupBox("Paramètres de surveillance")
        apply_shadow(ctrl_box)
        ctrl_layout = QHBoxLayout(ctrl_box)
        ctrl_layout.setContentsMargins(SPACE_L, SPACE_L, SPACE_L, SPACE_L)
        ctrl_layout.setSpacing(SPACE_S)

        lbl_interval = QLabel("Intervalle (s) :")
        lbl_interval.setStyleSheet(f"color: {THEME_COLORS['text_muted']};")
        ctrl_layout.addWidget(lbl_interval)
        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(10, 3600)
        self.interval_spin.setValue(60)
        self.interval_spin.setSuffix(" s")
        ctrl_layout.addWidget(self.interval_spin)

        lbl_retry = QLabel("Tentatives :")
        lbl_retry.setStyleSheet(f"color: {THEME_COLORS['text_muted']};")
        ctrl_layout.addWidget(lbl_retry)
        self.retry_spin = QSpinBox()
        self.retry_spin.setRange(1, 5)
        self.retry_spin.setValue(2)
        ctrl_layout.addWidget(self.retry_spin)

        ctrl_layout.addStretch()

        self.btn_start = QPushButton("▶  Démarrer")
        self.btn_start.setObjectName("PrimaryBtn")
        self.btn_start.setCursor(Qt.PointingHandCursor)
        self.btn_start.clicked.connect(self._start_monitoring)

        self.btn_stop = QPushButton("⏹  Arrêter")
        self.btn_stop.setObjectName("DangerBtn")
        self.btn_stop.setCursor(Qt.PointingHandCursor)
        self.btn_stop.clicked.connect(self._stop_monitoring)
        self.btn_stop.setEnabled(False)

        ctrl_layout.addWidget(self.btn_start)
        ctrl_layout.addWidget(self.btn_stop)
        layout.addWidget(ctrl_box)

        # ── Splitter : état actuel + historique ──
        splitter = QSplitter(Qt.Vertical)

        # Table état actuel
        top_frame = QFrame()
        tl = QVBoxLayout(top_frame)
        tl.setContentsMargins(0, 0, 0, 0)

        top_label = QLabel("État des équipements")
        top_label.setFont(get_font(10, bold=True))
        top_label.setStyleSheet(f"color: {THEME_COLORS['accent']};")
        tl.addWidget(top_label)

        self.devices_table = QTableWidget()
        self.devices_table.setColumnCount(6)
        self.devices_table.setHorizontalHeaderLabels([
            "IP", "Hostname", "Statut", "RTT (ms)", "Dernière vue", "Alertes"
        ])
        self.devices_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.devices_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.devices_table.setAlternatingRowColors(True)
        self._style_table(self.devices_table)
        tl.addWidget(self.devices_table)
        splitter.addWidget(top_frame)

        # Table historique
        bottom_frame = QFrame()
        bl = QVBoxLayout(bottom_frame)
        bl.setContentsMargins(0, 0, 0, 0)

        bot_label = QLabel("Historique des 100 derniers événements")
        bot_label.setFont(get_font(10, bold=True))
        bot_label.setStyleSheet(f"color: {THEME_COLORS['warning']};")
        bl.addWidget(bot_label)

        self.history_table = QTableWidget()
        self.history_table.setColumnCount(5)
        self.history_table.setHorizontalHeaderLabels([
            "Horodatage", "IP", "Hostname", "Statut", "RTT (ms)"
        ])
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.history_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.history_table.setAlternatingRowColors(True)
        self._style_table(self.history_table)
        bl.addWidget(self.history_table)
        splitter.addWidget(bottom_frame)

        layout.addWidget(splitter)

    def _style_table(self, table):
        table.horizontalHeader().setFont(get_font(10, bold=True))

    def refresh(self):
        self._refresh_devices_table()
        self._refresh_history_table()
        if self.monitor:
            running = self.monitor.is_running()
            self.status_lbl.setText("● Actif" if running else "● Arrêté")
            self.status_lbl.setStyleSheet(
                f"color: {THEME_COLORS['success'] if running else THEME_COLORS['danger']}; font-size: 13px; font-weight: bold;"
            )

    def _refresh_devices_table(self):
        devices = self.db.get_all_devices()
        self.devices_table.setRowCount(len(devices))
        for row, d in enumerate(devices):
            status = d.get("status", "Unknown")
            color = QColor(THEME_COLORS['success']) if status == "Online" else (
                QColor(THEME_COLORS['danger']) if status == "Offline" else QColor(THEME_COLORS['warning'])
            )
            # Récupérer le dernier RTT depuis l'historique
            history = self.db.get_monitoring_history(d["id"], limit=1)
            rtt = str(round(history[0]["response_time"], 1)) + " ms" if history and history[0].get("response_time") else "—"

            vals = [
                d.get("ip", ""), d.get("hostname", "") or "—",
                status, rtt, (d.get("last_seen") or "")[:16],
                str(len([a for a in self.db.get_alerts() if a.get("device_id") == d["id"] and not a.get("acknowledged")])),
            ]
            for col, val in enumerate(vals):
                item = QTableWidgetItem(val)
                if col in (0, 2, 3, 4, 5):
                    item.setFont(get_font(9, monospace=True))
                else:
                    item.setFont(get_font(9))
                if col == 2:
                    item.setForeground(color)
                    item.setFont(get_font(10, bold=True, monospace=True))
                self.devices_table.setItem(row, col, item)

    def _refresh_history_table(self):
        records = self.db.get_recent_monitoring(hours=24)[:100]
        self.history_table.setRowCount(len(records))
        for row, r in enumerate(records):
            status = r.get("status", "")
            color = QColor(THEME_COLORS['success']) if status == "Online" else QColor(THEME_COLORS['danger'])
            rtt = r.get("response_time")
            rtt_str = f"{rtt:.1f} ms" if rtt is not None else "—"
            vals = [
                (r.get("timestamp") or "")[:19],
                r.get("ip", ""),
                r.get("hostname", "") or "—",
                status,
                rtt_str,
            ]
            for col, val in enumerate(vals):
                item = QTableWidgetItem(val)
                if col in (0, 1, 3, 4):
                    item.setFont(get_font(9, monospace=True))
                else:
                    item.setFont(get_font(9))
                if col == 3:
                    item.setForeground(color)
                    item.setFont(get_font(9, bold=True, monospace=True))
                self.history_table.setItem(row, col, item)

    def _start_monitoring(self):
        if self.monitor:
            self.monitor.interval = self.interval_spin.value()
            self.monitor.retry_count = self.retry_spin.value()
            self.monitor.start()
            self.btn_start.setEnabled(False)
            self.btn_stop.setEnabled(True)
            self.status_lbl.setText("● Actif")
            self.status_lbl.setStyleSheet(f"color: {THEME_COLORS['success']}; font-size: 13px; font-weight: bold;")

    def _stop_monitoring(self):
        if self.monitor:
            self.monitor.stop()
            self.btn_start.setEnabled(True)
            self.btn_stop.setEnabled(False)
            self.status_lbl.setText("● Arrêté")
            self.status_lbl.setStyleSheet(f"color: {THEME_COLORS['danger']}; font-size: 13px; font-weight: bold;")