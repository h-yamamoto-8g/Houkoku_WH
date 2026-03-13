"""Settings page wrapper.

Wraps Ui_SettingsWindow and manages the three tabs:
  - Report Management
  - Department Permissions
  - Path Settings
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QScrollArea,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

import app.config as _cfg
from app.core.config_store import (
    AppConfig,
    Department,
    ReportDefinition,
    save_config,
    validate_config,
)
from app.services.report_service import ReportService
from app.ui.generated.ui_settingswindow import Ui_SettingsWindow


class SettingsPage(QDialog):
    """Settings dialog with three tabs."""

    def __init__(
        self,
        config: Optional[AppConfig],
        report_svc: ReportService,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._ui = Ui_SettingsWindow()
        self._ui.setupUi(self)

        self._config = AppConfig() if config is None else AppConfig(
            version=config.version,
            sharepoint_paths=dict(config.sharepoint_paths),
            report_definitions=list(config.report_definitions),
            departments=list(config.departments),
        )
        self._report_svc = report_svc
        self._dirty = False

        self._init_data()
        self._connect_signals()

    def get_config(self) -> Optional[AppConfig]:
        """Return updated config if changes were saved."""
        return self._config if self._dirty else None

    # ---------- Initialization ----------

    def _init_data(self) -> None:
        self._refresh_report_table()
        self._refresh_dept_table()
        self._refresh_dept_combo()
        self._refresh_perm_report_combo()
        self._refresh_path_display()

    def _connect_signals(self) -> None:
        self._ui.btn_close.clicked.connect(self._on_close)

        # Tab 1: Reports
        self._ui.btn_add_report.clicked.connect(self._on_add_report)
        self._ui.btn_edit_report.clicked.connect(self._on_edit_report)
        self._ui.btn_delete_report.clicked.connect(self._on_delete_report)

        # Tab 2: Department Management
        self._ui.btn_add_dept.clicked.connect(self._on_add_dept)
        self._ui.btn_edit_dept.clicked.connect(self._on_edit_dept)
        self._ui.btn_delete_dept.clicked.connect(self._on_delete_dept)

        # Tab 3: Permissions
        self._ui.cmb_dept.currentIndexChanged.connect(self._on_perm_selection_changed)
        self._ui.cmb_perm_report.currentIndexChanged.connect(self._on_perm_selection_changed)
        self._ui.btn_save_perms.clicked.connect(self._on_save_perms)

        # Tab 3: Paths
        self._ui.btn_browse_internal.clicked.connect(self._on_browse_internal)
        self._ui.btn_browse_external.clicked.connect(self._on_browse_external)

    # ---------- Helpers ----------

    def _get_available_protocols(self) -> list[str]:
        """Get unique request_protocol values from loaded CSV."""
        if not self._report_svc.is_loaded or self._report_svc._df is None:
            return []
        col = "request_protocol"
        if col not in self._report_svc._df.columns:
            return []
        return sorted(self._report_svc._df[col].dropna().unique().tolist())

    def _select_protocols_dialog(
        self, title: str, current: list[str]
    ) -> tuple[list[str], bool]:
        """Show a dialog with checkboxes for available protocols.

        Returns (selected_list, accepted).
        """
        available = self._get_available_protocols()
        if not available:
            # Fallback to text input if CSV not loaded
            text, ok = QInputDialog.getText(
                self, title, "検索条件（プロトコル名、カンマ区切り）:",
                text=", ".join(current),
            )
            if not ok:
                return [], False
            return [p.strip() for p in text.split(",") if p.strip()], True

        dlg = QDialog(self)
        dlg.setWindowTitle(title)
        dlg.setMinimumWidth(350)
        dlg.setMinimumHeight(400)
        layout = QVBoxLayout(dlg)
        layout.addWidget(QLabel("プロトコルを選択してください:"))

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        cb_layout = QVBoxLayout(container)

        checkboxes: list[QCheckBox] = []
        for proto in available:
            cb = QCheckBox(proto)
            cb.setChecked(proto in current)
            checkboxes.append(cb)
            cb_layout.addWidget(cb)
        cb_layout.addStretch()

        scroll.setWidget(container)
        layout.addWidget(scroll)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        layout.addWidget(buttons)

        if dlg.exec() != QDialog.DialogCode.Accepted:
            return [], False

        selected = [cb.text() for cb in checkboxes if cb.isChecked()]
        return selected, True

    # ---------- Tab 1: Report Management ----------

    def _refresh_report_table(self) -> None:
        tbl = self._ui.tbl_reports
        tbl.setColumnCount(4)
        tbl.setHorizontalHeaderLabels(["報告書ID", "報告書名", "検索条件", "Lab-Aidお気に入り名"])
        tbl.setRowCount(len(self._config.report_definitions))

        for i, r in enumerate(self._config.report_definitions):
            tbl.setItem(i, 0, QTableWidgetItem(r.report_id))
            tbl.setItem(i, 1, QTableWidgetItem(r.report_name))
            protocols = ", ".join(r.search_filters.get("protocol_name", []))
            tbl.setItem(i, 2, QTableWidgetItem(protocols))
            tbl.setItem(i, 3, QTableWidgetItem(r.labaid_favorite_name))

    def _show_report_dialog(
        self,
        title: str,
        report_id: str = "",
        report_name: str = "",
        protocols: list[str] | None = None,
        favorite_name: str = "",
        id_editable: bool = True,
    ) -> tuple[dict, bool]:
        """Show a single dialog for report add/edit. Returns (values, accepted)."""
        if protocols is None:
            protocols = []

        dlg = QDialog(self)
        dlg.setWindowTitle(title)
        dlg.setMinimumWidth(450)
        layout = QVBoxLayout(dlg)

        form = QFormLayout()

        txt_id = QLineEdit(report_id)
        txt_id.setReadOnly(not id_editable)
        if not id_editable:
            txt_id.setStyleSheet("background: #f0f0f0; color: #888;")
        form.addRow("報告書ID:", txt_id)

        txt_name = QLineEdit(report_name)
        form.addRow("報告書名:", txt_name)

        txt_favorite = QLineEdit(favorite_name)
        form.addRow("Lab-Aidお気に入り名:", txt_favorite)

        layout.addLayout(form)

        # Protocol selection
        layout.addWidget(QLabel("検索条件（プロトコル）:"))
        available = self._get_available_protocols()
        proto_checkboxes: list[QCheckBox] = []

        if available:
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setMaximumHeight(200)
            container = QWidget()
            cb_layout = QVBoxLayout(container)
            for proto in available:
                cb = QCheckBox(proto)
                cb.setChecked(proto in protocols)
                proto_checkboxes.append(cb)
                cb_layout.addWidget(cb)
            cb_layout.addStretch()
            scroll.setWidget(container)
            layout.addWidget(scroll)
        else:
            txt_protocols = QLineEdit(", ".join(protocols))
            txt_protocols.setPlaceholderText("プロトコル名をカンマ区切りで入力")
            layout.addWidget(txt_protocols)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        layout.addWidget(buttons)

        if dlg.exec() != QDialog.DialogCode.Accepted:
            return {}, False

        if available:
            selected_protocols = [cb.text() for cb in proto_checkboxes if cb.isChecked()]
        else:
            selected_protocols = [p.strip() for p in txt_protocols.text().split(",") if p.strip()]

        return {
            "report_id": txt_id.text().strip(),
            "report_name": txt_name.text().strip(),
            "protocols": selected_protocols,
            "favorite_name": txt_favorite.text().strip(),
        }, True

    def _on_add_report(self) -> None:
        values, ok = self._show_report_dialog("報告書追加")
        if not ok:
            return
        if not values["report_id"] or not values["report_name"]:
            QMessageBox.warning(self, "警告", "報告書IDと報告書名は必須です。")
            return

        new_report = ReportDefinition(
            report_id=values["report_id"],
            report_name=values["report_name"],
            search_filters={"protocol_name": values["protocols"]},
            labaid_favorite_name=values["favorite_name"],
        )
        self._config.report_definitions.append(new_report)
        self._refresh_report_table()
        self._refresh_perm_report_combo()

    def _on_edit_report(self) -> None:
        row = self._ui.tbl_reports.currentRow()
        if row < 0:
            QMessageBox.warning(self, "警告", "編集する報告書を選択してください。")
            return

        r = self._config.report_definitions[row]
        values, ok = self._show_report_dialog(
            "報告書編集",
            report_id=r.report_id,
            report_name=r.report_name,
            protocols=r.search_filters.get("protocol_name", []),
            favorite_name=r.labaid_favorite_name,
            id_editable=False,
        )
        if not ok:
            return

        r.report_name = values["report_name"]
        r.search_filters = {"protocol_name": values["protocols"]}
        r.labaid_favorite_name = values["favorite_name"]
        self._refresh_report_table()

    def _on_delete_report(self) -> None:
        row = self._ui.tbl_reports.currentRow()
        if row < 0:
            QMessageBox.warning(self, "警告", "削除する報告書を選択してください。")
            return

        r = self._config.report_definitions[row]
        ans = QMessageBox.question(
            self, "確認", f"報告書「{r.report_name}」を削除しますか？"
        )
        if ans == QMessageBox.StandardButton.Yes:
            self._config.report_definitions.pop(row)
            self._refresh_report_table()
            self._refresh_perm_report_combo()

    # ---------- Tab 2: Department Management ----------

    def _refresh_dept_table(self) -> None:
        tbl = self._ui.tbl_depts
        tbl.setRowCount(len(self._config.departments))
        for i, d in enumerate(self._config.departments):
            tbl.setItem(i, 0, QTableWidgetItem(d.dept_id))
            tbl.setItem(i, 1, QTableWidgetItem(d.dept_name))
            tbl.setItem(i, 2, QTableWidgetItem(d.folder_name))

    def _show_dept_dialog(
        self,
        title: str,
        dept_name: str = "",
        folder_name: str = "",
    ) -> tuple[dict, bool]:
        """Show a single dialog for department add/edit. Returns (values, accepted)."""
        dlg = QDialog(self)
        dlg.setWindowTitle(title)
        dlg.setMinimumWidth(400)
        layout = QVBoxLayout(dlg)

        form = QFormLayout()

        txt_name = QLineEdit(dept_name)
        form.addRow("部署名:", txt_name)

        txt_folder = QLineEdit(folder_name)
        txt_folder.setPlaceholderText("例: A → {報告書パス}/A に出力")
        form.addRow("格納先フォルダ名:", txt_folder)

        layout.addLayout(form)

        hint = QLabel("※ 格納先フォルダ名は報告書出力先のサブフォルダ名です")
        hint.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(hint)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        layout.addWidget(buttons)

        if dlg.exec() != QDialog.DialogCode.Accepted:
            return {}, False

        return {
            "dept_name": txt_name.text().strip(),
            "folder_name": txt_folder.text().strip(),
        }, True

    def _on_add_dept(self) -> None:
        values, ok = self._show_dept_dialog("部署追加")
        if not ok:
            return
        if not values["dept_name"] or not values["folder_name"]:
            QMessageBox.warning(self, "警告", "部署名と格納先フォルダ名は必須です。")
            return

        # Auto-generate dept_id
        existing_ids = {d.dept_id for d in self._config.departments}
        idx = len(self._config.departments) + 1
        while f"DEPT-{idx:03d}" in existing_ids:
            idx += 1
        dept_id = f"DEPT-{idx:03d}"

        new_dept = Department(
            dept_id=dept_id,
            dept_name=values["dept_name"],
            folder_name=values["folder_name"],
        )
        self._config.departments.append(new_dept)
        self._refresh_dept_table()
        self._refresh_dept_combo()

    def _on_edit_dept(self) -> None:
        row = self._ui.tbl_depts.currentRow()
        if row < 0:
            QMessageBox.warning(self, "警告", "編集する部署を選択してください。")
            return

        dept = self._config.departments[row]
        values, ok = self._show_dept_dialog(
            "部署編集",
            dept_name=dept.dept_name,
            folder_name=dept.folder_name,
        )
        if not ok:
            return

        dept.dept_name = values["dept_name"]
        dept.folder_name = values["folder_name"]
        self._refresh_dept_table()
        self._refresh_dept_combo()

    def _on_delete_dept(self) -> None:
        row = self._ui.tbl_depts.currentRow()
        if row < 0:
            QMessageBox.warning(self, "警告", "削除する部署を選択してください。")
            return

        dept = self._config.departments[row]
        ans = QMessageBox.question(
            self, "確認", f"部署「{dept.dept_name}」を削除しますか？\n"
            "この部署に設定された権限も削除されます。"
        )
        if ans == QMessageBox.StandardButton.Yes:
            self._config.departments.pop(row)
            self._refresh_dept_table()
            self._refresh_dept_combo()

    # ---------- Tab 3: Department Permissions ----------

    def _refresh_dept_combo(self) -> None:
        self._ui.cmb_dept.blockSignals(True)
        self._ui.cmb_dept.clear()
        for d in self._config.departments:
            self._ui.cmb_dept.addItem(d.dept_name, d.dept_id)
        self._ui.cmb_dept.blockSignals(False)

    def _refresh_perm_report_combo(self) -> None:
        self._ui.cmb_perm_report.blockSignals(True)
        self._ui.cmb_perm_report.clear()
        for r in self._config.report_definitions:
            self._ui.cmb_perm_report.addItem(r.report_name, r.report_id)
        self._ui.cmb_perm_report.blockSignals(False)

    def _on_perm_selection_changed(self, _index: int = 0) -> None:
        dept_idx = self._ui.cmb_dept.currentIndex()
        report_idx = self._ui.cmb_perm_report.currentIndex()

        # Clear existing checkboxes
        for cb in self._ui.sample_checkboxes:
            self._ui.sample_list_layout.removeWidget(cb)
            cb.deleteLater()
        self._ui.sample_checkboxes.clear()

        if dept_idx < 0 or report_idx < 0:
            return

        dept = self._config.departments[dept_idx]
        report = self._config.report_definitions[report_idx]

        # Get all unique sample codes from loaded data
        all_samples: list[str] = []
        if self._report_svc.is_loaded:
            df = self._report_svc.preview_report(report, "")
            # Get from full report filter (any job)
            import pandas as pd
            from app.core import loader
            full_df = loader.filter_by_report(
                self._report_svc._df, report.search_filters
            ) if self._report_svc._df is not None else pd.DataFrame()
            if not full_df.empty:
                all_samples = sorted(full_df["valid_sample_set_code"].dropna().unique().tolist())

        allowed = dept.allowed_samples.get(report.report_id, [])

        for sample_code in all_samples:
            cb = QCheckBox(sample_code)
            cb.setProperty("sample_code", sample_code)
            cb.setChecked(sample_code in allowed)
            self._ui.sample_checkboxes.append(cb)
            self._ui.sample_list_layout.addWidget(cb)

    def _on_save_perms(self) -> None:
        dept_idx = self._ui.cmb_dept.currentIndex()
        report_idx = self._ui.cmb_perm_report.currentIndex()

        if dept_idx < 0 or report_idx < 0:
            return

        dept = self._config.departments[dept_idx]
        report = self._config.report_definitions[report_idx]

        selected = [
            cb.property("sample_code")
            for cb in self._ui.sample_checkboxes
            if cb.isChecked()
        ]

        dept.allowed_samples[report.report_id] = selected
        QMessageBox.information(self, "保存", "権限設定を保存しました。")

    # ---------- Tab 4: Path Settings ----------

    def _refresh_path_display(self) -> None:
        if _cfg.INTERNAL_PATH is not None:
            self._ui.txt_internal_path.setText(str(_cfg.INTERNAL_PATH))
        else:
            self._ui.txt_internal_path.setText("")

        if _cfg.EXTERNAL_PATH is not None:
            self._ui.txt_external_path.setText(str(_cfg.EXTERNAL_PATH))
        else:
            self._ui.txt_external_path.setText("")

        if _cfg.SOURCE_CSV_PATH is not None:
            self._ui.lbl_source_csv.setText(str(_cfg.SOURCE_CSV_PATH))
        else:
            self._ui.lbl_source_csv.setText("(課内データパスを設定してください)")

    def _on_browse_internal(self) -> None:
        start_dir = str(Path.home())
        if _cfg.INTERNAL_PATH and _cfg.INTERNAL_PATH.exists():
            start_dir = str(_cfg.INTERNAL_PATH)

        folder = QFileDialog.getExistingDirectory(
            self, "課内データパスを選択", start_dir
        )
        if folder:
            path = Path(folder)
            _cfg.save_internal_path(path)
            _cfg.reload_paths(new_internal_path=path)
            self._refresh_path_display()

    def _on_browse_external(self) -> None:
        start_dir = str(Path.home())
        if _cfg.EXTERNAL_PATH and _cfg.EXTERNAL_PATH.exists():
            start_dir = str(_cfg.EXTERNAL_PATH)

        folder = QFileDialog.getExistingDirectory(
            self, "課外データパスを選択", start_dir
        )
        if folder:
            path = Path(folder)
            _cfg.save_external_path(path)
            _cfg.reload_paths(new_external_path=path)
            self._refresh_path_display()

    # ---------- Close ----------

    def _on_close(self) -> None:
        # Validate and save
        warnings = validate_config(self._config)
        if warnings:
            msg = "以下の警告があります:\n" + "\n".join(f"- {w}" for w in warnings)
            QMessageBox.warning(self, "設定の警告", msg)

        try:
            save_config(self._config)
            self._dirty = True
            self.accept()
        except FileNotFoundError as e:
            QMessageBox.critical(self, "エラー", str(e))
            self.reject()
