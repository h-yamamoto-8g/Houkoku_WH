"""Auto-generated style UI setup for the settings window.

NOTE: In production this would be generated from settingswindow.ui via pyside6-uic.
For initial development, we create the UI programmatically following the
design spec wireframe (section 3.2).

Three tabs: 報告書管理 / 部署別権限 / パス設定
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)


class Ui_SettingsWindow:
    """Sets up the settings dialog UI matching design spec 3.2."""

    def setupUi(self, dialog: QDialog) -> None:
        dialog.setObjectName("SettingsWindow")
        dialog.setWindowTitle("設定")
        dialog.resize(750, 600)
        dialog.setMinimumSize(600, 450)

        root_layout = QVBoxLayout(dialog)
        root_layout.setContentsMargins(16, 12, 16, 12)

        # --- Header ---
        header_layout = QHBoxLayout()
        lbl = QLabel("設定")
        lbl.setStyleSheet("font-size: 16px; font-weight: bold;")
        header_layout.addWidget(lbl)
        header_layout.addStretch()
        self.btn_close = QPushButton("戻る")
        self.btn_close.setFixedWidth(80)
        header_layout.addWidget(self.btn_close)
        root_layout.addLayout(header_layout)

        # --- Tab Widget ---
        self.tabs = QTabWidget()
        root_layout.addWidget(self.tabs)

        # ===== Tab 1: Report Management =====
        tab_reports = QWidget()
        tab_reports_layout = QVBoxLayout(tab_reports)

        self.tbl_reports = QTableWidget()
        self.tbl_reports.setColumnCount(3)
        self.tbl_reports.setHorizontalHeaderLabels(["報告書ID", "報告書名", "検索条件"])
        self.tbl_reports.horizontalHeader().setStretchLastSection(True)
        self.tbl_reports.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        self.tbl_reports.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tbl_reports.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        tab_reports_layout.addWidget(self.tbl_reports)

        btn_row = QHBoxLayout()
        self.btn_add_report = QPushButton("追加")
        self.btn_edit_report = QPushButton("編集")
        self.btn_delete_report = QPushButton("削除")
        btn_row.addWidget(self.btn_add_report)
        btn_row.addWidget(self.btn_edit_report)
        btn_row.addWidget(self.btn_delete_report)
        btn_row.addStretch()
        tab_reports_layout.addLayout(btn_row)

        self.tabs.addTab(tab_reports, "報告書管理")

        # ===== Tab 2: Department Permissions =====
        tab_perms = QWidget()
        tab_perms_layout = QVBoxLayout(tab_perms)

        selector_layout = QHBoxLayout()
        selector_layout.addWidget(QLabel("部署:"))
        self.cmb_dept = QComboBox()
        self.cmb_dept.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        selector_layout.addWidget(self.cmb_dept)
        selector_layout.addWidget(QLabel("報告書:"))
        self.cmb_perm_report = QComboBox()
        self.cmb_perm_report.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        selector_layout.addWidget(self.cmb_perm_report)
        tab_perms_layout.addLayout(selector_layout)

        tab_perms_layout.addWidget(QLabel("許可サンプル:"))
        self.sample_scroll = QScrollArea()
        self.sample_scroll.setWidgetResizable(True)
        self.sample_widget = QWidget()
        self.sample_list_layout = QVBoxLayout(self.sample_widget)
        self.sample_list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.sample_scroll.setWidget(self.sample_widget)
        tab_perms_layout.addWidget(self.sample_scroll)

        self.sample_checkboxes: list[QCheckBox] = []

        perm_btn_row = QHBoxLayout()
        perm_btn_row.addStretch()
        self.btn_save_perms = QPushButton("保存")
        self.btn_save_perms.setFixedWidth(100)
        perm_btn_row.addWidget(self.btn_save_perms)
        tab_perms_layout.addLayout(perm_btn_row)

        self.tabs.addTab(tab_perms, "部署別権限")

        # ===== Tab 3: Path Settings =====
        tab_paths = QWidget()
        tab_paths_layout = QVBoxLayout(tab_paths)

        form = QFormLayout()

        # 課内データパス
        self.txt_internal_path = QLineEdit()
        self.txt_internal_path.setReadOnly(True)
        self.btn_browse_internal = QPushButton("参照...")
        internal_row = QHBoxLayout()
        internal_row.addWidget(self.txt_internal_path)
        internal_row.addWidget(self.btn_browse_internal)
        form.addRow("課内データパス:", internal_row)

        # 課外データパス
        self.txt_external_path = QLineEdit()
        self.txt_external_path.setReadOnly(True)
        self.btn_browse_external = QPushButton("参照...")
        external_row = QHBoxLayout()
        external_row.addWidget(self.txt_external_path)
        external_row.addWidget(self.btn_browse_external)
        form.addRow("課外データパス:", external_row)

        # 元データCSV (derived, read-only info)
        self.lbl_source_csv = QLabel()
        self.lbl_source_csv.setStyleSheet("color: gray; font-size: 11px;")
        form.addRow("元データCSV:", self.lbl_source_csv)

        tab_paths_layout.addLayout(form)
        tab_paths_layout.addStretch()

        self.tabs.addTab(tab_paths, "パス設定")
