from __future__ import annotations

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication


COLORS = {
    "bg": "#0b0e14",
    "panel": "#111827",
    "panel_alt": "#162033",
    "panel_soft": "#1a2740",
    "border": "#2a3952",
    "text": "#f5f7fb",
    "muted": "#94a3b8",
    "accent": "#7c8cff",
    "accent_deep": "#6277ff",
    "accent_alt": "#54d1ff",
    "danger": "#ff6f91",
    "warning": "#f7c66a",
}


APP_STYLESHEET = f"""
QWidget {{
    background: {COLORS["bg"]};
    color: {COLORS["text"]};
    font-family: "Inter", "Geist", "Manrope", "Aptos", "Segoe UI", sans-serif;
    font-size: 10pt;
}}
QMainWindow, QStackedWidget, QScrollArea, QScrollArea > QWidget > QWidget {{
    background: transparent;
}}
QFrame#Sidebar {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 rgba(17, 24, 39, 0.95),
        stop:1 rgba(12, 18, 30, 0.88));
    border: 1px solid rgba(124, 140, 255, 0.16);
    border-radius: 28px;
}}
QFrame#TopShell, QFrame#SectionCard, QFrame#HeroBanner, QFrame#PlayerDock, QFrame#MetricCard {{
    background: rgba(17, 24, 39, 0.84);
    border: 1px solid rgba(148, 163, 184, 0.16);
    border-radius: 28px;
}}
QFrame#HeroBanner {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 rgba(23, 31, 50, 0.96),
        stop:0.56 rgba(26, 39, 64, 0.94),
        stop:1 rgba(18, 52, 86, 0.92));
}}
QWidget#VoiceSettingsEditor {{
    background: transparent;
}}
QPushButton {{
    background: rgba(26, 39, 64, 0.9);
    border: 1px solid rgba(148, 163, 184, 0.18);
    border-radius: 18px;
    padding: 11px 16px;
    font-weight: 600;
}}
QPushButton:hover {{
    border-color: rgba(84, 209, 255, 0.52);
    background: rgba(27, 41, 68, 0.96);
}}
QPushButton:focus {{
    border: 2px solid {COLORS["accent_alt"]};
    background: rgba(28, 42, 70, 0.98);
}}
QPushButton:pressed {{
    background: rgba(13, 20, 33, 0.98);
}}
QPushButton[variant="primary"] {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {COLORS["accent_deep"]},
        stop:1 {COLORS["accent_alt"]});
    color: #f8fbff;
    border-color: rgba(124, 140, 255, 0.7);
    font-weight: 700;
}}
QPushButton[variant="primary"]:hover {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #7486ff,
        stop:1 #63d9ff);
    border-color: rgba(99, 217, 255, 0.82);
}}
QPushButton[variant="subtle"] {{
    background: rgba(15, 23, 42, 0.72);
    color: {COLORS["text"]};
    border-color: rgba(124, 140, 255, 0.16);
}}
QPushButton[variant="danger"] {{
    background: rgba(255, 111, 145, 0.12);
    color: {COLORS["danger"]};
    border-color: rgba(255, 111, 145, 0.28);
}}
QPushButton[nav="true"] {{
    text-align: left;
    padding: 13px 16px;
    border-radius: 20px;
}}
QPushButton[nav="true"]:checked {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 rgba(124, 140, 255, 0.26),
        stop:1 rgba(84, 209, 255, 0.12));
    border-color: rgba(124, 140, 255, 0.55);
}}
QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QSpinBox {{
    background: rgba(9, 15, 25, 0.94);
    border: 1px solid rgba(148, 163, 184, 0.16);
    border-radius: 16px;
    padding: 12px 13px;
    selection-background-color: {COLORS["accent_deep"]};
}}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus, QSpinBox:focus {{
    border: 2px solid {COLORS["accent_alt"]};
}}
QTableWidget, QListWidget {{
    background: transparent;
    alternate-background-color: rgba(255, 255, 255, 0.02);
    border: 1px solid rgba(148, 163, 184, 0.14);
    border-radius: 22px;
    gridline-color: rgba(255,255,255,0.04);
}}
QTableWidget:focus, QListWidget:focus {{
    border: 2px solid {COLORS["accent_alt"]};
}}
QListWidget::item {{
    padding: 14px 16px;
    margin: 6px 8px;
    border-radius: 16px;
}}
QListWidget::item:hover {{
    background: rgba(124, 140, 255, 0.08);
}}
QListWidget::item:selected, QTableWidget::item:selected {{
    background: rgba(124, 140, 255, 0.18);
    border: 1px solid rgba(84, 209, 255, 0.28);
}}
QHeaderView::section {{
    background: rgba(9, 15, 25, 0.92);
    border: none;
    border-bottom: 1px solid rgba(148, 163, 184, 0.14);
    padding: 10px;
    color: {COLORS["muted"]};
    font-weight: 600;
}}
QTableWidget::item {{
    padding: 8px;
}}
QTabWidget::pane {{
    border: none;
}}
QTabBar::tab {{
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(148, 163, 184, 0.14);
    padding: 11px 16px;
    border-radius: 18px;
    margin-right: 10px;
}}
QTabBar::tab:selected {{
    background: rgba(124, 140, 255, 0.16);
    border-color: rgba(124, 140, 255, 0.52);
}}
QTabBar::tab:focus {{
    border: 2px solid {COLORS["accent_alt"]};
}}
QScrollBar:vertical {{
    width: 14px;
    background: transparent;
}}
QScrollBar::handle:vertical {{
    background: rgba(148, 163, 184, 0.22);
    border-radius: 7px;
    min-height: 30px;
}}
QProgressBar {{
    border: 1px solid rgba(148, 163, 184, 0.16);
    border-radius: 12px;
    text-align: center;
    background: rgba(9, 15, 25, 0.92);
}}
QProgressBar::chunk {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {COLORS["accent_deep"]},
        stop:1 {COLORS["accent_alt"]});
    border-radius: 11px;
}}
QCheckBox {{
    spacing: 10px;
}}
QCheckBox::indicator {{
    width: 18px;
    height: 18px;
}}
QCheckBox::indicator:unchecked {{
    border-radius: 6px;
    border: 1px solid rgba(148, 163, 184, 0.2);
    background: rgba(9, 15, 25, 0.92);
}}
QCheckBox::indicator:checked {{
    border-radius: 6px;
    border: 1px solid {COLORS["accent_deep"]};
    background: {COLORS["accent_deep"]};
}}
QSlider::groove:horizontal {{
    height: 6px;
    background: rgba(148, 163, 184, 0.16);
    border-radius: 3px;
}}
QSlider::handle:horizontal {{
    width: 18px;
    margin: -6px 0;
    border-radius: 9px;
    background: {COLORS["accent_alt"]};
}}
QLabel[role="muted"] {{
    color: {COLORS["muted"]};
}}
QLabel[role="title"] {{
    font-size: 19pt;
    font-weight: 600;
}}
QLabel[role="section-title"] {{
    font-size: 13.5pt;
    font-weight: 600;
}}
QLabel[role="metric-title"] {{
    color: {COLORS["muted"]};
    font-size: 8.6pt;
    font-weight: 600;
    text-transform: uppercase;
}}
QLabel[role="metric-value"] {{
    font-size: 20pt;
    font-weight: 700;
}}
"""


def apply_theme(app: QApplication) -> None:
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(COLORS["bg"]))
    palette.setColor(QPalette.WindowText, QColor(COLORS["text"]))
    palette.setColor(QPalette.Base, QColor("#091119"))
    palette.setColor(QPalette.AlternateBase, QColor(COLORS["panel_alt"]))
    palette.setColor(QPalette.ToolTipBase, QColor(COLORS["panel"]))
    palette.setColor(QPalette.ToolTipText, QColor(COLORS["text"]))
    palette.setColor(QPalette.Text, QColor(COLORS["text"]))
    palette.setColor(QPalette.Button, QColor(COLORS["panel"]))
    palette.setColor(QPalette.ButtonText, QColor(COLORS["text"]))
    palette.setColor(QPalette.Highlight, QColor(COLORS["accent_deep"]))
    palette.setColor(QPalette.HighlightedText, QColor("#f7fffc"))
    app.setPalette(palette)
    app.setStyleSheet(APP_STYLESHEET)
