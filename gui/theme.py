"""
NetAdminPy – Centralized Design System & Stylesheet (Frosted Glass Theme)
"""

from PySide6.QtGui import QFont, QColor
from PySide6.QtWidgets import QGraphicsDropShadowEffect

# ── Palette de Couleurs (Dark Slate & Neon Accents) ─────────
THEME_COLORS = {
    "bg_window": "transparent",    # Window background is transparent to show the factory image
    "bg_container": "#0f172a",     # Neutral dark slate for sidebar (solid)
    "bg_card": "rgba(30, 41, 59, 0.65)",  # Translucent slate-navy for cards
    "bg_input": "rgba(9, 13, 22, 0.75)",  # Darker translucent for input fields/tables
    "border": "rgba(255, 255, 255, 0.08)", # Very thin translucent light border
    "accent": "#38bdf8",           # Electric sky/cyber blue accent
    "accent_hover": "#0ea5e9",     # Cyber blue hover
    "accent_active": "#0284c7",    # Cyber blue pressed/active
    "accent_muted": "rgba(56, 189, 248, 0.12)", # Muted accent for selected states
    "text": "#ffffff",             # White text
    "text_muted": "#64748b",       # Muted text color (slate grey)
    "success": "#10b981",          # Cybersecurity green
    "warning": "#f59e0b",          # Alert amber/yellow
    "danger": "#ef4444",           # Critical red
}

# ── Typographies ───────────────────────────────────────────
FONT_FAMILY = '"Segoe UI", -apple-system, BlinkMacSystemFont, "Roboto", sans-serif'
FONT_MONOSPACE = '"Consolas", "Cascadia Code", "Courier New", monospace'

def get_font(size=10, bold=False, monospace=False) -> QFont:
    """Helper tool to create structured QFont settings."""
    family = FONT_MONOSPACE if monospace else "Segoe UI"
    font = QFont(family, size)
    font.setBold(bold)
    return font

# ── Espacements ────────────────────────────────────────────
# Constantes basées sur une grille de 8px
SPACE_XS = 4
SPACE_S = 8
SPACE_M = 12
SPACE_L = 16
SPACE_XL = 24

def apply_shadow(widget, color=None, offset=(0, 4), blur_radius=12):
    """Applies a professional native drop shadow effect to a QWidget."""
    if not widget:
        return
    if color is None:
        color = QColor(0, 0, 0, 100)
    effect = QGraphicsDropShadowEffect(widget)
    effect.setColor(color)
    effect.setOffset(offset[0], offset[1])
    effect.setBlurRadius(blur_radius)
    widget.setGraphicsEffect(effect)

# ── Feuille de Style Globale (QSS) ──────────────────────────
GLOBAL_QSS = f"""
* {{
    font-family: {FONT_FAMILY};
    font-size: 10pt;
}}

QMainWindow {{
    background-color: #0b0f19;
}}

QWidget#CentralWidget {{
    background: transparent;
}}

/* Sidebar - opaque, solid dark slate */
QFrame#Sidebar {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #0f172a, stop:1 #020617);
    border: none;
    border-right: 1px solid #1e293b;
}}

/* Panels / Cards - Frosted Glass effect */
QFrame#Panel {{
    background-color: {THEME_COLORS['bg_card']};
    border: 1px solid {THEME_COLORS['border']};
    border-radius: 8px;
}}

QFrame#StatusBadgeCard {{
    background-color: {THEME_COLORS['bg_input']};
    border: 1px solid {THEME_COLORS['border']};
    border-radius: 8px;
}}
QFrame#StatusBadgeCard:hover {{
    border-color: {THEME_COLORS['accent']};
    background-color: {THEME_COLORS['bg_card']};
}}

/* Scrollbars */
QScrollBar:vertical {{
    background: {THEME_COLORS['bg_input']};
    width: 10px;
    margin: 0px;
    border: none;
}}
QScrollBar::handle:vertical {{
    background: rgba(255, 255, 255, 0.15);
    border-radius: 5px;
    min-height: 20px;
}}
QScrollBar::handle:vertical:hover {{
    background: {THEME_COLORS['accent']};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: none;
}}

QScrollBar:horizontal {{
    background: {THEME_COLORS['bg_input']};
    height: 10px;
    margin: 0px;
    border: none;
}}
QScrollBar::handle:horizontal {{
    background: rgba(255, 255, 255, 0.15);
    border-radius: 5px;
    min-width: 20px;
}}
QScrollBar::handle:horizontal:hover {{
    background: {THEME_COLORS['accent']};
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0px;
}}
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
    background: none;
}}

/* Standard Buttons - Rounded 8px */
QPushButton {{
    background: {THEME_COLORS['bg_card']};
    color: {THEME_COLORS['text']};
    border: 1px solid {THEME_COLORS['border']};
    border-radius: 8px;
    padding: 6px 14px;
    font-weight: 500;
}}
QPushButton:hover {{
    background: rgba(255, 255, 255, 0.08);
    border-color: {THEME_COLORS['accent']};
}}
QPushButton:pressed {{
    background: {THEME_COLORS['bg_input']};
}}

QPushButton#PrimaryBtn {{
    background: {THEME_COLORS['accent']};
    color: #020617;
    border: none;
    border-radius: 8px;
    padding: 8px 18px;
    font-weight: bold;
}}
QPushButton#PrimaryBtn:hover {{
    background: {THEME_COLORS['accent_hover']};
}}
QPushButton#PrimaryBtn:pressed {{
    background: {THEME_COLORS['accent_active']};
}}
QPushButton#PrimaryBtn:disabled {{
    background: #334155;
    color: {THEME_COLORS['text_muted']};
}}

QPushButton#SecondaryBtn {{
    background: transparent;
    color: {THEME_COLORS['accent']};
    border: 1px solid {THEME_COLORS['accent']};
    border-radius: 8px;
    padding: 8px 18px;
    font-weight: bold;
}}
QPushButton#SecondaryBtn:hover {{
    background: rgba(56, 189, 248, 0.08);
}}
QPushButton#SecondaryBtn:pressed {{
    background: rgba(56, 189, 248, 0.18);
}}

QPushButton#DangerBtn {{
    background: {THEME_COLORS['danger']};
    color: {THEME_COLORS['text']};
    border: none;
    border-radius: 8px;
    padding: 8px 18px;
    font-weight: bold;
}}
QPushButton#DangerBtn:hover {{
    background: #e5123d;
}}
QPushButton#DangerBtn:pressed {{
    background: #b20f30;
}}

/* Form elements - Uniform height and rounded 8px */
QLineEdit, QSpinBox, QComboBox, QTextEdit {{
    background: {THEME_COLORS['bg_input']};
    color: {THEME_COLORS['text']};
    border: 1px solid {THEME_COLORS['border']};
    border-radius: 8px;
    padding: 6px 10px;
    min-height: 28px;
}}
QLineEdit:focus, QSpinBox:focus, QComboBox:focus, QTextEdit:focus {{
    border: 1px solid {THEME_COLORS['accent']};
}}
QComboBox::drop-down {{
    border: none;
    padding-right: 8px;
}}
QSpinBox::up-button, QSpinBox::down-button {{
    background: rgba(255, 255, 255, 0.05);
    border: none;
    width: 18px;
}}
QSpinBox::up-button:hover, QSpinBox::down-button:hover {{
    background: rgba(255, 255, 255, 0.15);
}}

/* Group Boxes - Card design config panel */
QGroupBox {{
    background-color: {THEME_COLORS['bg_card']};
    color: {THEME_COLORS['accent']};
    font-weight: bold;
    border: 1px solid {THEME_COLORS['border']};
    border-radius: 8px;
    margin-top: 16px;
    padding: 16px;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 14px;
    padding: 0 6px;
}}

/* Tooltips */
QToolTip {{
    background: #0f172a;
    color: {THEME_COLORS['text']};
    border: 1px solid {THEME_COLORS['accent']};
    border-radius: 8px;
    padding: 6px;
}}

/* Tabs (QTabWidget) - Frosted Glass pane */
QTabWidget::pane {{
    border: 1px solid {THEME_COLORS['border']};
    background: {THEME_COLORS['bg_card']};
    border-radius: 8px;
    top: -1px;
}}
QTabBar::tab {{
    background: rgba(15, 23, 42, 0.45);
    color: {THEME_COLORS['text_muted']};
    padding: 8px 18px;
    border: 1px solid {THEME_COLORS['border']};
    border-bottom: none;
    border-radius: 8px 8px 0 0;
    margin-right: 4px;
}}
QTabBar::tab:selected {{
    background: {THEME_COLORS['bg_card']};
    color: {THEME_COLORS['text']};
    font-weight: bold;
    border-bottom: 1px solid transparent;
}}
QTabBar::tab:hover {{
    background: rgba(255, 255, 255, 0.04);
    color: {THEME_COLORS['text']};
}}

/* Tables (QTableWidget) - Frosted Glass design */
QTableWidget {{
    background: {THEME_COLORS['bg_input']};
    gridline-color: {THEME_COLORS['border']};
    color: {THEME_COLORS['text']};
    border: 1px solid {THEME_COLORS['border']};
    border-radius: 8px;
}}
QTableWidget::item {{
    padding: 8px 12px;
    border-bottom: 1px solid {THEME_COLORS['border']};
}}
QTableWidget::item:hover {{
    background-color: rgba(255, 255, 255, 0.03);
}}
QTableWidget::item:selected {{
    background: {THEME_COLORS['accent_muted']};
    color: {THEME_COLORS['text']};
}}
QTableWidget::item:alternate {{
    background: rgba(15, 23, 42, 0.35);
}}
QHeaderView::section {{
    background-color: rgba(15, 23, 42, 0.85);
    color: {THEME_COLORS['text_muted']};
    padding: 10px;
    font-weight: bold;
    font-size: 8pt;
    text-transform: uppercase;
    border: none;
    border-right: 1px solid {THEME_COLORS['border']};
    border-bottom: 1px solid {THEME_COLORS['border']};
}}

/* Progress Bars - Thin & Rounded */
QProgressBar {{
    border: 1px solid {THEME_COLORS['border']};
    border-radius: 8px;
    background: {THEME_COLORS['bg_input']};
    color: {THEME_COLORS['text']};
    text-align: center;
    height: 12px;
    font-size: 7.5pt;
    font-weight: bold;
}}
QProgressBar::chunk {{
    background: {THEME_COLORS['accent']};
    border-radius: 7px;
}}

/* Dialogs / MessageBoxes */
QMessageBox, QDialog {{
    background-color: #0f172a;
}}
QMessageBox QLabel {{
    color: {THEME_COLORS['text']};
}}
"""
