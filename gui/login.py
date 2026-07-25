"""Authentication dialog for NetAdminPy."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from services.auth_service import AuthService, AuthenticationError
from models.auth_models import Session


class LoginWindow(QDialog):
    """Professional login dialog that authenticates through the auth service."""

    def __init__(self, auth_service: AuthService):
        super().__init__()
        self.auth_service = auth_service
        self.session: Optional[Session] = None
        self._build_ui()

    def _build_ui(self) -> None:
        self.setWindowTitle("NetAdminPy Authentication")
        self.setModal(True)
        self.resize(420, 280)
        self.setMinimumWidth(380)

        container = QWidget(self)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        title = QLabel("Secure Sign In")
        title.setStyleSheet("font-size: 20px; font-weight: 600;")
        layout.addWidget(title)

        subtitle = QLabel("Access the NetAdminPy control plane")
        subtitle.setStyleSheet("color: #64748b;")
        layout.addWidget(subtitle)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignLeft)
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Username")
        self.username_input.setMinimumHeight(36)
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Password")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setMinimumHeight(36)
        self.remember_me = QCheckBox("Remember me")
        form.addRow("Username", self.username_input)
        form.addRow("Password", self.password_input)
        form.addRow("", self.remember_me)
        layout.addLayout(form)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #ef4444; min-height: 18px;")
        layout.addWidget(self.status_label)

        actions = QHBoxLayout()
        actions.addStretch()
        self.login_button = QPushButton("Sign In")
        self.login_button.setDefault(True)
        self.login_button.clicked.connect(self._handle_login)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        actions.addWidget(self.cancel_button)
        actions.addWidget(self.login_button)
        layout.addLayout(actions)

        self.setLayout(layout)

    def _handle_login(self) -> None:
        username = self.username_input.text().strip()
        password = self.password_input.text()
        self.status_label.setText("")
        try:
            self.session = self.auth_service.login(
                username=username,
                password=password,
                remember_me=self.remember_me.isChecked(),
                ip_address="local",
            )
        except AuthenticationError as exc:
            self.status_label.setText(str(exc))
            QMessageBox.warning(self, "Authentication Failed", str(exc))
            return
        self.accept()
