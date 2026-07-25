"""
NetAdminPy – Interface rapports et sauvegardes
"""

import os
import threading
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QFrame,
    QGroupBox, QComboBox, QLineEdit, QTextEdit, QTabWidget,
    QFileDialog, QMessageBox, QAbstractItemView, QProgressBar,
)
from PySide6.QtCore import Qt, Signal, QThread, QObject
from PySide6.QtGui import QFont, QColor

from core.ssh import CiscoBackup
from gui.theme import THEME_COLORS, get_font, FONT_MONOSPACE, SPACE_XL, SPACE_L, SPACE_M, SPACE_S, SPACE_XS, apply_shadow


class BackupWorker(QObject):
    finished = Signal(bool, str, str)

    def __init__(self, host, username, password, device_type, backup_dir):
        super().__init__()
        self.host = host
        self.username = username
        self.password = password
        self.device_type = device_type
        self.backup_dir = backup_dir

    def run(self):
        cb = CiscoBackup(self.backup_dir)
        ok, path, msg = cb.backup_device(
            self.host, self.username, self.password, self.device_type
        )
        self.finished.emit(ok, path, msg)


class ReportsWidget(QWidget):
    """Panneau rapports + sauvegardes Cisco."""

    def __init__(self, db_manager, config=None, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.config = config

        from config import REPORTS_DIR, BACKUPS_DIR
        self.reports_dir = REPORTS_DIR
        self.backups_dir = BACKUPS_DIR

        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACE_XL, SPACE_XL, SPACE_XL, SPACE_XL)
        layout.setSpacing(SPACE_L)

        title = QLabel("📊 Rapports & Sauvegardes")
        title.setFont(get_font(18, bold=True))
        title.setStyleSheet(f"color: {THEME_COLORS['text']};")
        layout.addWidget(title)

        tabs = QTabWidget()
        tabs.addTab(self._build_reports_tab(), "📄 Rapports")
        tabs.addTab(self._build_backup_tab(), "💾 Sauvegardes Cisco")
        layout.addWidget(tabs)

    # ── Onglet Rapports ──────────────────────────────────

    def _build_reports_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(SPACE_L, SPACE_L, SPACE_L, SPACE_L)
        layout.setSpacing(SPACE_L)

        desc = QLabel("Générez des rapports d'infrastructure au format PDF ou Excel. "
                       "Ils incluent l'inventaire, les ports ouverts et les statistiques de disponibilité.")
        desc.setWordWrap(True)
        desc.setStyleSheet(f"color: {THEME_COLORS['text_muted']}; font-size: 12px;")
        layout.addWidget(desc)

        # Options
        opts = QGroupBox("Options")
        apply_shadow(opts)
        ol = QHBoxLayout(opts)
        ol.setContentsMargins(SPACE_L, SPACE_L, SPACE_L, SPACE_L)
        ol.setSpacing(SPACE_S)

        lbl_title = QLabel("Titre du rapport :")
        lbl_title.setStyleSheet(f"color: {THEME_COLORS['text_muted']};")
        ol.addWidget(lbl_title)
        self.report_title = QLineEdit("Rapport d'infrastructure réseau")
        ol.addWidget(self.report_title, 2)

        lbl_fmt = QLabel("Format :")
        lbl_fmt.setStyleSheet(f"color: {THEME_COLORS['text_muted']};")
        ol.addWidget(lbl_fmt)
        self.format_combo = QComboBox()
        self.format_combo.addItems(["PDF", "Excel (.xlsx)", "Les deux"])
        ol.addWidget(self.format_combo)
        layout.addWidget(opts)

        # Boutons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(SPACE_S)
        btn_gen = QPushButton("⚙️  Générer le rapport")
        btn_gen.setObjectName("PrimaryBtn")
        btn_gen.setCursor(Qt.PointingHandCursor)
        btn_gen.clicked.connect(self._generate_report)

        btn_open_dir = QPushButton("📁  Ouvrir le dossier")
        btn_open_dir.setObjectName("SecondaryBtn")
        btn_open_dir.setCursor(Qt.PointingHandCursor)
        btn_open_dir.clicked.connect(lambda: os.startfile(self.reports_dir) if os.name == "nt"
                                       else os.system(f'xdg-open "{self.reports_dir}"'))
        btn_row.addWidget(btn_gen)
        btn_row.addWidget(btn_open_dir)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setRange(0, 0)  # indéterminé
        layout.addWidget(self.progress_bar)

        self.report_log = QTextEdit()
        self.report_log.setReadOnly(True)
        self.report_log.setMaximumHeight(200)
        self.report_log.setFont(get_font(9, monospace=True))
        layout.addWidget(self.report_log)
        layout.addStretch()
        return tab

    def _generate_report(self):
        devices = self.db.get_all_devices()
        if not devices:
            QMessageBox.warning(self, "Aucun équipement", "Aucun équipement dans la base de données.\nLancez d'abord un scan réseau.")
            return

        # Enrichir avec les ports
        for d in devices:
            d["ports"] = self.db.get_ports_for_device(d["id"])

        self.progress_bar.setVisible(True)
        fmt = self.format_combo.currentText()
        title = self.report_title.text().strip() or "Rapport d'infrastructure réseau"
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.report_log.clear()

        def run():
            from reports.generator import generate_pdf_report, generate_excel_report
            errors = []

            if fmt in ("PDF", "Les deux"):
                pdf_path = os.path.join(self.reports_dir, f"rapport_{ts}.pdf")
                ok, result = generate_pdf_report(devices, pdf_path, title)
                if ok:
                    self._log(f"✅ PDF généré : {pdf_path}")
                else:
                    self._log(f"❌ Erreur PDF : {result}")
                    errors.append(result)

            if fmt in ("Excel (.xlsx)", "Les deux"):
                xlsx_path = os.path.join(self.reports_dir, f"rapport_{ts}.xlsx")
                ok, result = generate_excel_report(devices, xlsx_path)
                if ok:
                    self._log(f"✅ Excel généré : {xlsx_path}")
                else:
                    self._log(f"❌ Erreur Excel : {result}")
                    errors.append(result)

            self.progress_bar.setVisible(False)
            if not errors:
                self._log("🎉 Rapport(s) généré(s) avec succès.")

        threading.Thread(target=run, daemon=True).start()

    def _log(self, msg: str):
        from PySide6.QtCore import QMetaObject, Qt, Q_ARG
        self.report_log.append(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

    # ── Onglet Sauvegardes Cisco ──────────────────────────

    def _build_backup_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(SPACE_L, SPACE_L, SPACE_L, SPACE_L)
        layout.setSpacing(SPACE_L)

        desc = QLabel("Sauvegardez la configuration running des équipements Cisco via SSH (Netmiko/Paramiko).")
        desc.setStyleSheet(f"color: {THEME_COLORS['text_muted']}; font-size: 12px;")
        layout.addWidget(desc)

        # Formulaire connexion
        form_box = QGroupBox("Connexion SSH")
        apply_shadow(form_box)
        fl = QHBoxLayout(form_box)
        fl.setContentsMargins(SPACE_L, SPACE_L, SPACE_L, SPACE_L)
        fl.setSpacing(SPACE_S)

        lbl_host = QLabel("Hôte :")
        lbl_host.setStyleSheet(f"color: {THEME_COLORS['text_muted']};")
        fl.addWidget(lbl_host)
        self.ssh_host = QLineEdit()
        self.ssh_host.setPlaceholderText("192.168.1.1")
        fl.addWidget(self.ssh_host)

        lbl_user = QLabel("Utilisateur :")
        lbl_user.setStyleSheet(f"color: {THEME_COLORS['text_muted']};")
        fl.addWidget(lbl_user)
        self.ssh_user = QLineEdit("admin")
        fl.addWidget(self.ssh_user)

        lbl_pass = QLabel("Mot de passe :")
        lbl_pass.setStyleSheet(f"color: {THEME_COLORS['text_muted']};")
        fl.addWidget(lbl_pass)
        self.ssh_pass = QLineEdit()
        self.ssh_pass.setEchoMode(QLineEdit.Password)
        fl.addWidget(self.ssh_pass)

        lbl_type = QLabel("Type :")
        lbl_type.setStyleSheet(f"color: {THEME_COLORS['text_muted']};")
        fl.addWidget(lbl_type)
        self.device_type_combo = QComboBox()
        self.device_type_combo.addItems(["cisco_ios", "cisco_xe", "cisco_nxos", "cisco_asa", "juniper"])
        fl.addWidget(self.device_type_combo)

        btn_backup = QPushButton("💾  Sauvegarder")
        btn_backup.setObjectName("PrimaryBtn")
        btn_backup.setCursor(Qt.PointingHandCursor)
        btn_backup.clicked.connect(self._do_backup)
        fl.addWidget(btn_backup)
        layout.addWidget(form_box)

        self.backup_status = QLabel("Prêt.")
        self.backup_status.setStyleSheet(f"color: {THEME_COLORS['text_muted']}; font-size: 11px;")
        layout.addWidget(self.backup_status)

        # Table des sauvegardes
        backups_lbl = QLabel("Sauvegardes existantes")
        backups_lbl.setFont(get_font(11, bold=True))
        backups_lbl.setStyleSheet(f"color: {THEME_COLORS['accent']};")
        layout.addWidget(backups_lbl)

        btn_refresh = QPushButton("🔄  Actualiser")
        btn_refresh.setObjectName("SecondaryBtn")
        btn_refresh.setCursor(Qt.PointingHandCursor)
        btn_refresh.clicked.connect(self._refresh_backups_table)
        layout.addWidget(btn_refresh, alignment=Qt.AlignRight)

        self.backups_table = QTableWidget()
        self.backups_table.setColumnCount(5)
        self.backups_table.setHorizontalHeaderLabels(["Équipement", "IP", "Fichier", "Taille", "Date"])
        self.backups_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.backups_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.backups_table.setAlternatingRowColors(True)
        layout.addWidget(self.backups_table)
        self._refresh_backups_table()
        return tab

    def _do_backup(self):
        host = self.ssh_host.text().strip()
        user = self.ssh_user.text().strip()
        pwd = self.ssh_pass.text()
        dtype = self.device_type_combo.currentText()

        if not host or not user:
            QMessageBox.warning(self, "Champs manquants", "Veuillez renseigner l'hôte et l'utilisateur.")
            return

        self.backup_status.setText("⏳ Connexion SSH en cours…")

        def run():
            cb = CiscoBackup(self.backups_dir)
            ok, path, msg = cb.backup_device(host, user, pwd, dtype)
            if ok:
                size = os.path.getsize(path) if os.path.exists(path) else 0
                device = self.db.get_device_by_ip(host)
                if device:
                    self.db.add_backup(device["id"], os.path.basename(path), path, size)
                self.backup_status.setText(f"✅ {msg}")
                self._refresh_backups_table()
            else:
                self.backup_status.setText(f"❌ Erreur : {msg}")

        threading.Thread(target=run, daemon=True).start()

    def _refresh_backups_table(self):
        backups = self.db.get_backups()
        self.backups_table.setRowCount(len(backups))
        for row, b in enumerate(backups):
            size = b.get("size_bytes", 0)
            size_str = f"{size/1024:.1f} Ko" if size else "—"
            vals = [
                b.get("hostname", "") or "—",
                b.get("ip", "") or "—",
                b.get("filename", ""),
                size_str,
                (b.get("created_at") or "")[:16],
            ]
            for col, val in enumerate(vals):
                item = QTableWidgetItem(str(val))
                if col in (1, 2, 3, 4):
                    item.setFont(get_font(9, monospace=True))
                else:
                    item.setFont(get_font(9))
                self.backups_table.setItem(row, col, item)