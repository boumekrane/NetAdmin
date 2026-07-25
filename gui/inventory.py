"""
NetAdminPy – Interface inventaire
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QFrame,
    QDialog, QFormLayout, QLineEdit, QComboBox, QTextEdit,
    QAbstractItemView, QMessageBox, QDialogButtonBox,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor
from gui.theme import THEME_COLORS, get_font, FONT_MONOSPACE, SPACE_XL, SPACE_L, SPACE_M, SPACE_S, SPACE_XS


class DeviceDetailDialog(QDialog):
    """Dialogue de fiche complète d'un équipement."""

    saved = Signal()

    def __init__(self, device: dict, db_manager, parent=None):
        super().__init__(parent)
        self.device = device
        self.db = db_manager
        self.setWindowTitle(f"Fiche équipement – {device.get('ip')}")
        self.setMinimumWidth(500)
        self.setStyleSheet(f"""
            QLabel {{ color: {THEME_COLORS['text_muted']}; }}
            QPushButton#SaveBtn {{
                background: {THEME_COLORS['accent']}; color: {THEME_COLORS['bg_window']}; border: none;
                border-radius: 4px; padding: 8px 20px; font-weight: bold;
            }}
            QPushButton#SaveBtn:hover {{ background: {THEME_COLORS['accent_hover']}; }}
        """)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(SPACE_M)
        layout.setContentsMargins(SPACE_XL, SPACE_XL, SPACE_XL, SPACE_XL)

        title = QLabel(f"🖥️  {self.device.get('hostname') or self.device.get('ip')}")
        title.setFont(get_font(14, bold=True))
        title.setStyleSheet(f"color: {THEME_COLORS['accent']};")
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(10)

        def lbl(t):
            l = QLabel(t)
            l.setFont(get_font(10))
            l.setMinimumWidth(120)
            return l

        self.hostname_edit = QLineEdit(self.device.get("hostname", "") or "")
        self.ip_lbl = QLabel(f"<b>{self.device.get('ip', '')}</b>")
        self.ip_lbl.setStyleSheet(f"color: {THEME_COLORS['accent']}; font-family: {FONT_MONOSPACE}; font-size: 13px;")
        self.mac_lbl = QLabel(self.device.get("mac", "") or "—")
        self.mac_lbl.setStyleSheet(f"font-family: {FONT_MONOSPACE};")
        self.vendor_lbl = QLabel(self.device.get("vendor", "") or "—")
        self.os_edit = QLineEdit(self.device.get("os_info", "") or "")

        self.type_combo = QComboBox()
        self.type_combo.addItems(["Unknown", "Router", "Switch", "Server", "Workstation",
                                   "Printer", "Access Point", "Firewall", "Camera", "Other"])
        cur_type = self.device.get("device_type", "Unknown")
        idx = self.type_combo.findText(cur_type)
        if idx >= 0:
            self.type_combo.setCurrentIndex(idx)

        self.comments_edit = QTextEdit(self.device.get("comments", "") or "")
        self.comments_edit.setMaximumHeight(100)

        first = self.device.get("first_seen", "")[:16] if self.device.get("first_seen") else "—"
        last = self.device.get("last_seen", "")[:16] if self.device.get("last_seen") else "—"

        form.addRow(lbl("Adresse IP :"), self.ip_lbl)
        form.addRow(lbl("Hostname :"), self.hostname_edit)
        form.addRow(lbl("Adresse MAC :"), self.mac_lbl)
        form.addRow(lbl("Constructeur :"), self.vendor_lbl)
        form.addRow(lbl("Système :"), self.os_edit)
        form.addRow(lbl("Type :"), self.type_combo)
        form.addRow(lbl("Première vue :"), QLabel(first))
        form.addRow(lbl("Dernière vue :"), QLabel(last))
        form.addRow(lbl("Commentaires :"), self.comments_edit)
        layout.addLayout(form)

        # Ports ouverts
        ports = self.db.get_ports_for_device(self.device["id"])
        open_ports = [p for p in ports if p.get("state") == "open"]
        if open_ports:
            ports_lbl = QLabel("Ports ouverts : " + ", ".join(
                f"{p['port']}/{p.get('service', '?')}" for p in open_ports
            ))
            ports_lbl.setStyleSheet(f"color: {THEME_COLORS['success']}; font-family: {FONT_MONOSPACE}; font-size: 11px;")
            ports_lbl.setWordWrap(True)
            layout.addWidget(ports_lbl)

        # Boutons
        btns = QHBoxLayout()
        save_btn = QPushButton("💾  Enregistrer")
        save_btn.setObjectName("SaveBtn")
        save_btn.setCursor(Qt.PointingHandCursor)
        save_btn.clicked.connect(self._save)
        cancel_btn = QPushButton("Annuler")
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setStyleSheet(f"background: {THEME_COLORS['bg_card']}; color: {THEME_COLORS['text_muted']}; border: 1px solid {THEME_COLORS['border']}; border-radius: 4px; padding: 8px 16px;")
        btns.addStretch()
        btns.addWidget(cancel_btn)
        btns.addWidget(save_btn)
        layout.addLayout(btns)

    def _save(self):
        self.db.update_device_field(self.device["id"], "hostname", self.hostname_edit.text().strip())
        self.db.update_device_field(self.device["id"], "os_info", self.os_edit.text().strip())
        self.db.update_device_field(self.device["id"], "device_type", self.type_combo.currentText())
        self.db.update_device_field(self.device["id"], "comments", self.comments_edit.toPlainText().strip())
        self.saved.emit()
        self.accept()


class InventoryWidget(QWidget):
    """Panneau inventaire complet."""

    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACE_XL, SPACE_XL, SPACE_XL, SPACE_XL)
        layout.setSpacing(SPACE_L)

        # En-tête
        header = QHBoxLayout()
        title = QLabel("📋 Inventaire des équipements")
        title.setFont(get_font(18, bold=True))
        title.setStyleSheet(f"color: {THEME_COLORS['text']};")
        header.addWidget(title)
        header.addStretch()

        # Filtres
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["Tous", "En ligne", "Hors ligne", "Router", "Server", "Switch", "Unknown"])
        self.filter_combo.currentIndexChanged.connect(self.refresh)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Rechercher IP, hostname…")
        self.search_input.setMaximumWidth(250)
        self.search_input.textChanged.connect(self.refresh)

        btn_refresh = QPushButton("🔄  Actualiser")
        btn_refresh.setObjectName("SecondaryBtn")
        btn_refresh.setCursor(Qt.PointingHandCursor)
        btn_refresh.clicked.connect(self.refresh)

        btn_delete = QPushButton("🗑️  Supprimer")
        btn_delete.setObjectName("DangerBtn")
        btn_delete.setCursor(Qt.PointingHandCursor)
        btn_delete.clicked.connect(self._delete_selected)

        header.addWidget(self.search_input)
        header.addWidget(self.filter_combo)
        header.addWidget(btn_refresh)
        header.addWidget(btn_delete)
        layout.addLayout(header)

        # Statistiques rapides
        self.stats_lbl = QLabel()
        self.stats_lbl.setStyleSheet(f"color: {THEME_COLORS['text_muted']}; font-size: 11px;")
        layout.addWidget(self.stats_lbl)

        # Table principale
        self.table = QTableWidget()
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels([
            "IP", "Hostname", "MAC", "Constructeur", "Type",
            "Statut", "OS", "Première vue", "Dernière vue"
        ])
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(QHeaderView.Interactive)
        hh.setDefaultSectionSize(130)
        hh.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.itemDoubleClicked.connect(self._open_device_detail)
        layout.addWidget(self.table)

        tip = QLabel("💡 Double-cliquez sur un équipement pour éditer sa fiche.")
        tip.setStyleSheet(f"color: {THEME_COLORS['text_muted']}; font-size: 10px; font-style: italic;")
        layout.addWidget(tip)

    def refresh(self):
        devices = self.db.get_all_devices()

        # Appliquer le filtre
        filt = self.filter_combo.currentText()
        search = self.search_input.text().strip().lower()

        filtered = []
        for d in devices:
            if filt == "En ligne" and d.get("status") != "Online":
                continue
            if filt == "Hors ligne" and d.get("status") != "Offline":
                continue
            if filt in ["Router", "Server", "Switch", "Unknown"] and d.get("device_type") != filt:
                continue
            if search:
                haystack = f"{d.get('ip','')} {d.get('hostname','')} {d.get('mac','')}".lower()
                if search not in haystack:
                    continue
            filtered.append(d)

        self.table.setRowCount(len(filtered))
        online = sum(1 for d in filtered if d.get("status") == "Online")
        self.stats_lbl.setText(f"{len(filtered)} équipement(s) affiché(s) • {online} en ligne • {len(filtered)-online} hors ligne")

        for row, d in enumerate(filtered):
            status = d.get("status", "Unknown")
            color = QColor(THEME_COLORS['success']) if status == "Online" else (
                QColor(THEME_COLORS['danger']) if status == "Offline" else QColor(THEME_COLORS['warning'])
            )
            vals = [
                d.get("ip", ""), d.get("hostname", "") or "—",
                d.get("mac", "") or "—", d.get("vendor", "") or "—",
                d.get("device_type", "Unknown"), status,
                d.get("os_info", "") or "—",
                (d.get("first_seen") or "")[:16],
                (d.get("last_seen") or "")[:16],
            ]
            for col, val in enumerate(vals):
                item = QTableWidgetItem(str(val))
                item.setData(Qt.UserRole, d["id"])
                if col in (0, 2, 7, 8):
                    item.setFont(get_font(9, monospace=True))
                else:
                    item.setFont(get_font(9))
                if col == 5:
                    item.setForeground(color)
                    item.setFont(get_font(9, bold=True))
                self.table.setItem(row, col, item)

    def _open_device_detail(self, item):
        device_id = item.data(Qt.UserRole)
        device = self.db.get_device_by_id(device_id)
        if device:
            dlg = DeviceDetailDialog(device, self.db, self)
            dlg.saved.connect(self.refresh)
            dlg.exec()

    def _delete_selected(self):
        rows = set(idx.row() for idx in self.table.selectedIndexes())
        if not rows:
            return
        ids = [self.table.item(r, 0).data(Qt.UserRole) for r in rows]
        reply = QMessageBox.question(
            self, "Confirmer la suppression",
            f"Supprimer {len(ids)} équipement(s) ?\nCette action est irréversible.",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            for device_id in ids:
                self.db.delete_device(device_id)
            self.refresh()