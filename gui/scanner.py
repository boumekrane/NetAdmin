"""
NetAdminPy – Interface du scanner réseau
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QSpinBox, QTableWidget, QTableWidgetItem,
    QProgressBar, QGroupBox, QComboBox, QTextEdit, QSplitter,
    QHeaderView, QFrame, QMessageBox, QAbstractItemView,
)
from PySide6.QtCore import Qt, Signal, QThread, QObject
from PySide6.QtGui import QFont, QColor

from core.scanner import NetworkScanner, PortScanner
from gui.theme import THEME_COLORS, get_font, FONT_MONOSPACE, SPACE_XL, SPACE_L, SPACE_M, SPACE_S, SPACE_XS, apply_shadow


class StatusBadge(QWidget):
    """Badge de statut avec pastille colorée."""
    def __init__(self, text, dot_color, text_color="#ffffff", parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(0)
        layout.setAlignment(Qt.AlignCenter)

        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: {THEME_COLORS['bg_card']};
                border: 1px solid {THEME_COLORS['border']};
                border-radius: 4px;
            }}
        """)
        fl = QHBoxLayout(frame)
        fl.setContentsMargins(8, 2, 8, 2)
        fl.setSpacing(6)

        dot = QLabel("●")
        dot.setStyleSheet(f"color: {dot_color}; font-size: 10px;")
        lbl = QLabel(text)
        lbl.setFont(get_font(9))
        lbl.setStyleSheet(f"color: {text_color};")

        fl.addWidget(dot)
        fl.addWidget(lbl)
        layout.addWidget(frame)


class RTTIndicator(QWidget):
    """Indicateur visuel de qualité RTT."""
    def __init__(self, rtt_val, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(0)
        layout.setAlignment(Qt.AlignCenter)

        try:
            val = float(rtt_val)
            if val < 100:
                color = THEME_COLORS['success']
            elif val <= 300:
                color = THEME_COLORS['warning']
            else:
                color = THEME_COLORS['danger']
            text = f"{rtt_val} ms"
        except ValueError:
            color = THEME_COLORS['text_muted']
            text = "—"

        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: {THEME_COLORS['bg_card']};
                border: 1px solid {THEME_COLORS['border']};
                border-radius: 4px;
            }}
        """)
        fl = QHBoxLayout(frame)
        fl.setContentsMargins(8, 2, 8, 2)
        fl.setSpacing(6)

        dot = QLabel("●")
        dot.setStyleSheet(f"color: {color}; font-size: 8px;")
        lbl = QLabel(text)
        lbl.setFont(get_font(9, monospace=True))
        lbl.setStyleSheet(f"color: {THEME_COLORS['text']};")

        fl.addWidget(dot)
        fl.addWidget(lbl)
        layout.addWidget(frame)


class ScanWorker(QObject):
    """Worker Qt pour le scan (thread séparé)."""
    progress = Signal(int, int, object)
    host_found = Signal(dict)
    finished = Signal(list)
    error = Signal(str)

    def __init__(self, ip_range, threads, timeout):
        super().__init__()
        self.ip_range = ip_range
        self.threads = threads
        self.timeout = timeout
        self.scanner = NetworkScanner()

    def run(self):
        try:
            results = self.scanner.discover_network(
                self.ip_range,
                threads=self.threads,
                timeout=self.timeout,
                progress_callback=lambda c, t, h: self.progress.emit(c, t, h),
                result_callback=lambda h: self.host_found.emit(h),
            )
            self.finished.emit(results)
        except Exception as e:
            self.error.emit(str(e))

    def stop(self):
        self.scanner.stop()


class PortScanWorker(QObject):
    progress = Signal(int, int, dict)
    finished = Signal(list)
    error = Signal(str)

    def __init__(self, ip, ports, timeout):
        super().__init__()
        self.ip = ip
        self.ports = ports
        self.timeout = timeout
        self.ps = PortScanner(timeout=timeout)

    def run(self):
        try:
            results = self.ps.scan_host(
                self.ip, self.ports,
                progress_callback=lambda c, t, r: self.progress.emit(c, t, r),
            )
            self.finished.emit(results)
        except Exception as e:
            self.error.emit(str(e))

    def stop(self):
        self.ps.stop()


class ScannerWidget(QWidget):
    """Panneau complet de scan réseau."""

    devices_updated = Signal()

    def __init__(self, db_manager, alert_manager=None, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.alerts = alert_manager
        self._scan_thread = None
        self._scan_worker = None
        self._port_thread = None
        self._port_worker = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACE_XL, SPACE_XL, SPACE_XL, SPACE_XL)
        layout.setSpacing(SPACE_L)

        title = QLabel("🔍 Scanner réseau")
        title.setFont(get_font(18, bold=True))
        title.setStyleSheet(f"color: {THEME_COLORS['text']};")
        layout.addWidget(title)

        # ── Contrôles découverte ──
        ctrl_box = QGroupBox("Découverte réseau")
        apply_shadow(ctrl_box)
        ctrl_layout = QHBoxLayout(ctrl_box)
        ctrl_layout.setContentsMargins(SPACE_L, SPACE_L, SPACE_L, SPACE_L)
        ctrl_layout.setSpacing(SPACE_S)

        self.ip_input = QLineEdit("192.168.1.0/24")
        self.ip_input.setPlaceholderText("Plage IP (ex: 192.168.1.0/24)")
        self.ip_input.setMinimumWidth(220)

        threads_lbl = QLabel("Threads :")
        threads_lbl.setStyleSheet(f"color: {THEME_COLORS['text_muted']};")
        self.threads_spin = QSpinBox()
        self.threads_spin.setRange(1, 200)
        self.threads_spin.setValue(50)

        timeout_lbl = QLabel("Timeout (s) :")
        timeout_lbl.setStyleSheet(f"color: {THEME_COLORS['text_muted']};")
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(1, 10)
        self.timeout_spin.setValue(1)

        self.btn_scan = QPushButton("▶  Démarrer le scan")
        self.btn_scan.setObjectName("PrimaryBtn")
        self.btn_scan.setCursor(Qt.PointingHandCursor)
        self.btn_scan.clicked.connect(self._start_network_scan)

        self.btn_stop = QPushButton("⏹  Arrêter")
        self.btn_stop.setObjectName("DangerBtn")
        self.btn_stop.setCursor(Qt.PointingHandCursor)
        self.btn_stop.clicked.connect(self._stop_scan)
        self.btn_stop.setEnabled(False)

        lbl_ip = QLabel("Plage IP :")
        lbl_ip.setStyleSheet(f"color: {THEME_COLORS['text_muted']};")
        ctrl_layout.addWidget(lbl_ip)
        ctrl_layout.addWidget(self.ip_input, 2)
        ctrl_layout.addWidget(threads_lbl)
        ctrl_layout.addWidget(self.threads_spin)
        ctrl_layout.addWidget(timeout_lbl)
        ctrl_layout.addWidget(self.timeout_spin)
        ctrl_layout.addWidget(self.btn_scan)
        ctrl_layout.addWidget(self.btn_stop)
        layout.addWidget(ctrl_box)

        # Barre de progression
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        self.status_lbl = QLabel("Prêt.")
        self.status_lbl.setStyleSheet(f"color: {THEME_COLORS['text_muted']}; font-size: 11px;")
        layout.addWidget(self.status_lbl)

        # ── Splitter : table résultats + détail ports ──
        splitter = QSplitter(Qt.Vertical)

        # Table des équipements découverts
        top_frame = QFrame()
        top_layout = QVBoxLayout(top_frame)
        top_layout.setContentsMargins(0, 0, 0, 0)

        results_lbl = QLabel("Équipements découverts")
        results_lbl.setFont(get_font(10, bold=True))
        results_lbl.setStyleSheet(f"color: {THEME_COLORS['accent']};")
        top_layout.addWidget(results_lbl)

        self.results_table = QTableWidget()
        self.results_table.setColumnCount(8)
        self.results_table.setHorizontalHeaderLabels([
            "", "IP", "Hostname", "MAC", "Constructeur", "Statut", "RTT (ms)", "Dernière vue"
        ])
        hh = self.results_table.horizontalHeader()
        hh.setSectionResizeMode(QHeaderView.Stretch)
        hh.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.results_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.results_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.results_table.setAlternatingRowColors(True)
        self.results_table.itemDoubleClicked.connect(self._on_device_double_click)
        self._style_table(self.results_table)
        top_layout.addWidget(self.results_table)
        splitter.addWidget(top_frame)

        # Scanner de ports
        port_frame = QFrame()
        port_layout = QVBoxLayout(port_frame)
        port_layout.setContentsMargins(0, 0, 0, 0)

        port_ctrl = QHBoxLayout()
        port_ctrl.setSpacing(SPACE_S)
        port_lbl = QLabel("Scanner de ports :")
        port_lbl.setFont(get_font(10, bold=True))
        port_lbl.setStyleSheet(f"color: {THEME_COLORS['accent']};")

        self.port_ip_input = QLineEdit()
        self.port_ip_input.setPlaceholderText("IP cible (ex: 192.168.1.1)")

        self.port_range_combo = QComboBox()
        self.port_range_combo.addItems([
            "Ports courants (21-3389)",
            "Top 20 ports",
            "1-1024 (standard)",
            "1-65535 (complet)",
        ])

        self.btn_port_scan = QPushButton("🔌  Scanner les ports")
        self.btn_port_scan.setObjectName("SecondaryBtn")
        self.btn_port_scan.setCursor(Qt.PointingHandCursor)
        self.btn_port_scan.clicked.connect(self._start_port_scan)

        self.port_progress = QProgressBar()
        self.port_progress.setTextVisible(True)
        self.port_progress.setVisible(False)

        port_ctrl.addWidget(port_lbl)
        port_ctrl.addWidget(self.port_ip_input, 2)
        port_ctrl.addWidget(self.port_range_combo)
        port_ctrl.addWidget(self.btn_port_scan)
        port_layout.addLayout(port_ctrl)
        port_layout.addWidget(self.port_progress)

        self.ports_table = QTableWidget()
        self.ports_table.setColumnCount(5)
        self.ports_table.setHorizontalHeaderLabels(["", "Port", "Service", "État", "Scanné le"])
        ph = self.ports_table.horizontalHeader()
        ph.setSectionResizeMode(QHeaderView.Stretch)
        ph.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.ports_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.ports_table.setAlternatingRowColors(True)
        self.ports_table.styleSheet = ""
        self._style_table(self.ports_table)
        port_layout.addWidget(self.ports_table)
        splitter.addWidget(port_frame)

        layout.addWidget(splitter)

    def _style_table(self, table):
        table.horizontalHeader().setFont(get_font(10, bold=True))

    # ── Actions ──────────────────────────────────────────

    def _start_network_scan(self):
        ip_range = self.ip_input.text().strip()
        if not ip_range:
            QMessageBox.warning(self, "Erreur", "Veuillez saisir une plage IP.")
            return

        self.results_table.setRowCount(0)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.btn_scan.setEnabled(False)
        self.btn_stop.setEnabled(True)

        session_id = self.db.start_scan_session(ip_range)
        self._session_id = session_id
        self._found_hosts = []

        self._scan_thread = QThread()
        self._scan_worker = ScanWorker(
            ip_range,
            self.threads_spin.value(),
            float(self.timeout_spin.value()),
        )
        self._scan_worker.moveToThread(self._scan_thread)
        self._scan_thread.started.connect(self._scan_worker.run)
        self._scan_worker.progress.connect(self._on_scan_progress)
        self._scan_worker.host_found.connect(self._on_host_found)
        self._scan_worker.finished.connect(self._on_scan_finished)
        self._scan_worker.error.connect(self._on_scan_error)
        self._scan_thread.start()

        self.status_lbl.setText(f"Scan en cours : {ip_range}…")

    def _stop_scan(self):
        if self._scan_worker:
            self._scan_worker.stop()
        self.btn_stop.setEnabled(False)
        self.status_lbl.setText("Scan arrêté par l'utilisateur.")

    def _on_scan_progress(self, current, total, host):
        if total > 0:
            pct = int(current / total * 100)
            self.progress_bar.setValue(pct)
            self.progress_bar.setFormat(f"Scan : {current}/{total} IP ({pct}%)")

    def _on_host_found(self, host_info):
        self._found_hosts.append(host_info)
        # Sauvegarder en base
        device_id = self.db.upsert_device(
            host_info["ip"],
            hostname=host_info.get("hostname", ""),
            mac=host_info.get("mac", ""),
            vendor=host_info.get("vendor", ""),
            status=host_info.get("status", "Online"),
        )
        # Ajouter dans la table
        row = self.results_table.rowCount()
        self.results_table.insertRow(row)

        # Checkbox dans la colonne 0
        cb_item = QTableWidgetItem()
        cb_item.setCheckState(Qt.Unchecked)
        cb_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsSelectable)
        self.results_table.setItem(row, 0, cb_item)

        values = [
            host_info.get("ip", ""),
            host_info.get("hostname", "") or "—",
            host_info.get("mac", "") or "—",
            host_info.get("vendor", "") or "—",
            host_info.get("status", ""),
            str(host_info.get("response_time", "")) or "—",
            (host_info.get("last_seen", "") or "")[:16],
        ]
        for col_idx, val in enumerate(values, start=1):
            if col_idx == 5:  # Statut
                dot_color = THEME_COLORS['success'] if val == "Online" else THEME_COLORS['danger']
                badge = StatusBadge(val, dot_color, THEME_COLORS['text'])
                self.results_table.setCellWidget(row, col_idx, badge)
                
                item = QTableWidgetItem(val)
                item.setFont(get_font(9))
                self.results_table.setItem(row, col_idx, item)
            elif col_idx == 6:  # RTT
                rtt_indicator = RTTIndicator(val)
                self.results_table.setCellWidget(row, col_idx, rtt_indicator)
                
                item = QTableWidgetItem(val)
                item.setFont(get_font(9, monospace=True))
                self.results_table.setItem(row, col_idx, item)
            else:
                item = QTableWidgetItem(val)
                if col_idx in (1, 3, 7): # IP, MAC, dates are monospace
                    item.setFont(get_font(9, monospace=True))
                else:
                    item.setFont(get_font(9))
                self.results_table.setItem(row, col_idx, item)

    def _on_scan_finished(self, results):
        self._scan_thread.quit()
        self.db.finish_scan_session(self._session_id, len(results))
        self.btn_scan.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.progress_bar.setValue(100)
        self.status_lbl.setText(f"Scan terminé : {len(results)} équipement(s) trouvé(s).")
        if self.alerts:
            self.alerts.scan_complete(self.ip_input.text().strip(), len(results))
        self.devices_updated.emit()

    def _on_scan_error(self, msg):
        self._scan_thread.quit()
        self.btn_scan.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.progress_bar.setVisible(False)
        self.status_lbl.setText(f"Erreur : {msg}")
        QMessageBox.critical(self, "Erreur de scan", msg)

    def _on_device_double_click(self, item):
        row = item.row()
        ip = self.results_table.item(row, 1).text()
        self.port_ip_input.setText(ip)

    def _start_port_scan(self):
        ip = self.port_ip_input.text().strip()
        if not ip:
            QMessageBox.warning(self, "Erreur", "Veuillez saisir une adresse IP.")
            return

        mode = self.port_range_combo.currentIndex()
        if mode == 0:
            ports = [21, 22, 23, 25, 53, 80, 110, 143, 443, 445, 3306, 3389, 5432, 5900, 8080, 8443]
        elif mode == 1:
            ports = [21, 22, 23, 25, 80, 110, 139, 143, 443, 445, 3306, 3389, 5900, 8080, 8443, 1433, 27017, 6379, 5432, 161]
        elif mode == 2:
            ports = list(range(1, 1025))
        else:
            ports = list(range(1, 65536))

        self.ports_table.setRowCount(0)
        self.port_progress.setVisible(True)
        self.port_progress.setValue(0)
        self.btn_port_scan.setEnabled(False)

        self._port_thread = QThread()
        self._port_worker = PortScanWorker(ip, ports, timeout=1.0)
        self._port_worker.moveToThread(self._port_thread)
        self._port_thread.started.connect(self._port_worker.run)
        self._port_worker.progress.connect(self._on_port_progress)
        self._port_worker.finished.connect(self._on_port_finished)
        self._port_worker.error.connect(lambda e: self.status_lbl.setText(f"Erreur ports : {e}"))
        self._port_thread.start()

    def _on_port_progress(self, current, total, result):
        if total > 0:
            self.port_progress.setValue(int(current / total * 100))

        # Afficher uniquement les ports ouverts en temps réel
        if result.get("state") == "open":
            from datetime import datetime
            row = self.ports_table.rowCount()
            self.ports_table.insertRow(row)

            # Checkbox
            cb_item = QTableWidgetItem()
            cb_item.setCheckState(Qt.Unchecked)
            cb_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            self.ports_table.setItem(row, 0, cb_item)

            vals = [str(result["port"]), result.get("service", ""), result["state"],
                    datetime.now().strftime("%H:%M:%S")]
            for col, val in enumerate(vals, start=1):
                if col == 3: # State
                    dot_color = THEME_COLORS['success']
                    badge = StatusBadge(val, dot_color, THEME_COLORS['text'])
                    self.ports_table.setCellWidget(row, col, badge)
                    
                    item = QTableWidgetItem(val)
                    item.setFont(get_font(9))
                    self.ports_table.setItem(row, col, item)
                else:
                    item = QTableWidgetItem(val)
                    if col in (1, 4): # Port, Time are monospace
                        item.setFont(get_font(9, monospace=True))
                    else:
                        item.setFont(get_font(9))
                    self.ports_table.setItem(row, col, item)

    def _on_port_finished(self, results):
        self._port_thread.quit()
        self.btn_port_scan.setEnabled(True)
        self.port_progress.setValue(100)
        ip = self.port_ip_input.text().strip()
        # Sauvegarder en base
        device = self.db.get_device_by_ip(ip)
        if device:
            for r in results:
                if r["state"] == "open":
                    self.db.upsert_port(device["id"], r["port"], r["state"], r.get("service", ""))
        open_count = sum(1 for r in results if r["state"] == "open")
        self.status_lbl.setText(f"Scan de ports terminé sur {ip} : {open_count} port(s) ouvert(s).")

    def start_scan_for_ip(self, ip_range: str):
        self.ip_input.setText(ip_range)
        self._start_network_scan()