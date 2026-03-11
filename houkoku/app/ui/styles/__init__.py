"""QSS stylesheet definitions.

White-based theme with light rounded corners.
Yu Gothic (Windows) / Hiragino Sans (macOS).
"""

import platform

_FONT_FAMILY = (
    "'Yu Gothic UI', 'Yu Gothic', 'Meiryo'"
    if platform.system() == "Windows"
    else "'Hiragino Sans', 'Hiragino Kaku Gothic ProN', sans-serif"
)

APP_STYLESHEET = f"""
QWidget {{
    font-family: {_FONT_FAMILY};
    font-size: 13px;
    color: #333333;
    background-color: #f5f7fa;
}}

QMainWindow {{
    background-color: #f5f7fa;
}}

QGroupBox {{
    background-color: #ffffff;
    border: 1px solid #e0e0e0;
    border-radius: 6px;
    margin-top: 12px;
    padding: 16px 12px 12px 12px;
    font-weight: bold;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    color: #555555;
}}

QComboBox {{
    background-color: #ffffff;
    border: 1px solid #cccccc;
    border-radius: 4px;
    padding: 6px 10px;
    min-height: 24px;
}}

QComboBox:hover {{
    border-color: #999999;
}}

QComboBox::drop-down {{
    border: none;
    width: 24px;
}}

QLineEdit, QTextEdit, QPlainTextEdit {{
    background-color: #ffffff;
    border: 1px solid #cccccc;
    border-radius: 4px;
    padding: 6px 10px;
}}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
    border-color: #4a90d9;
}}

QPushButton {{
    background-color: #ffffff;
    border: 1px solid #cccccc;
    border-radius: 4px;
    padding: 8px 20px;
    min-height: 24px;
    color: #333333;
}}

QPushButton:hover {{
    background-color: #e8e8e8;
    border-color: #999999;
}}

QPushButton:pressed {{
    background-color: #d0d0d0;
}}

QPushButton#btn_export {{
    background-color: #4a90d9;
    color: #ffffff;
    border: none;
    font-weight: bold;
}}

QPushButton#btn_export:hover {{
    background-color: #3a7bc8;
}}

QPushButton#btn_send {{
    background-color: #5cb85c;
    color: #ffffff;
    border: none;
    font-weight: bold;
}}

QPushButton#btn_send:hover {{
    background-color: #4cae4c;
}}

QTableView, QTableWidget {{
    background-color: #ffffff;
    border: 1px solid #e0e0e0;
    border-radius: 4px;
    gridline-color: #eeeeee;
    selection-background-color: #e3f2fd;
    selection-color: #333333;
}}

QHeaderView::section {{
    background-color: #f0f0f0;
    border: none;
    border-bottom: 1px solid #cccccc;
    border-right: 1px solid #e0e0e0;
    padding: 6px 8px;
    font-weight: bold;
    color: #555555;
}}

QCheckBox {{
    spacing: 8px;
}}

QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border: 1px solid #cccccc;
    border-radius: 3px;
    background-color: #ffffff;
}}

QCheckBox::indicator:checked {{
    background-color: #4a90d9;
    border-color: #4a90d9;
}}

QTabWidget::pane {{
    background-color: #ffffff;
    border: 1px solid #e0e0e0;
    border-radius: 4px;
}}

QTabBar::tab {{
    background-color: #f0f0f0;
    border: 1px solid #e0e0e0;
    border-bottom: none;
    padding: 8px 20px;
    margin-right: 2px;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
}}

QTabBar::tab:selected {{
    background-color: #ffffff;
    border-bottom: 2px solid #4a90d9;
}}

QLabel#lbl_status {{
    color: #888888;
    font-size: 11px;
}}

QScrollBar:vertical {{
    background-color: #f5f7fa;
    width: 10px;
    border: none;
}}

QScrollBar::handle:vertical {{
    background-color: #cccccc;
    border-radius: 5px;
    min-height: 30px;
}}

QScrollBar::handle:vertical:hover {{
    background-color: #aaaaaa;
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
"""
