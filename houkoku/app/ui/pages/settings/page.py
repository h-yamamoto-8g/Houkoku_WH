"""Settings page wrapper.

Wraps Ui_SettingsWindow and manages the three tabs:
  - Report Management
  - Department Permissions
  - Path Settings
"""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QLineEdit,
    QMessageBox,
    QTableWidgetItem,
    QVBoxLayout,
)

import app.config as _cfg
from app.core.config_store import (
    AppConfig,
    ColumnSetting,
    DEFAULT_COLUMN_SETTINGS,
    Department,
    ReportDefinition,
    save_config,
    validate_config,
)
from app.services.report_service import ReportService
from app.ui.generated.ui_settingswindow import Ui_SettingsWindow


class _ReportDialog(QDialog):
    """Single dialog for adding/editing a report definition."""

    def __init__(
        self,
        parent=None,
        *,
        title: str = "報告書",
        report_name: str = "",
        protocols: str = "",
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(400)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.txt_name = QLineEdit(report_name)
        form.addRow("報告書名:", self.txt_name)

        self.txt_protocols = QLineEdit(protocols)
        form.addRow("検索条件（プロトコル名、カンマ区切り）:", self.txt_protocols)

        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_values(self) -> tuple[str, list[str]]:
        """Return (report_name, protocol_list)."""
        name = self.txt_name.text().strip()
        protocols = [
            p.strip() for p in self.txt_protocols.text().split(",") if p.strip()
        ]
        return name, protocols


class _DeptDialog(QDialog):
    """Single dialog for adding/editing a department."""

    def __init__(
        self,
        parent=None,
        *,
        title: str = "部署",
        dept_name: str = "",
        folder_name: str = "",
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(400)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.txt_name = QLineEdit(dept_name)
        form.addRow("部署名:", self.txt_name)

        self.txt_folder = QLineEdit(folder_name)
        form.addRow("フォルダ名:", self.txt_folder)

        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_values(self) -> tuple[str, str]:
        """Return (dept_name, folder_name)."""
        return self.txt_name.text().strip(), self.txt_folder.text().strip()


class _ColumnDialog(QDialog):
    """Dialog for editing a column's display name and visibility."""

    def __init__(
        self,
        parent=None,
        *,
        title: str = "列設定",
        column_key: str = "",
        display_name: str = "",
        visible: bool = True,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(400)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.lbl_key = QLineEdit(column_key)
        self.lbl_key.setReadOnly(True)
        self.lbl_key.setStyleSheet("background: #f0f0f0;")
        form.addRow("列キー:", self.lbl_key)

        self.txt_display_name = QLineEdit(display_name)
        form.addRow("表示名:", self.txt_display_name)

        self.chk_visible = QCheckBox("表示する")
        self.chk_visible.setChecked(visible)
        form.addRow("表示:", self.chk_visible)

        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_values(self) -> tuple[str, bool]:
        """Return (display_name, visible)."""
        return self.txt_display_name.text().strip(), self.chk_visible.isChecked()


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
            column_settings=[
                ColumnSetting(c.column_key, c.display_name, c.visible)
                for c in config.column_settings
            ],
        )
        # Ensure column_settings has defaults if empty
        if not self._config.column_settings:
            self._config.column_settings = [
                ColumnSetting(c.column_key, c.display_name, c.visible)
                for c in DEFAULT_COLUMN_SETTINGS
            ]
        self._report_svc = report_svc
        self._dirty = False
        self._cached_samples: list[dict] | None = None  # lazily loaded from valid_samples.json

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
        self._on_perm_selection_changed()
        self._refresh_column_table()

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

        # Tab 3: Department Permissions
        self._ui.cmb_dept.currentIndexChanged.connect(self._on_perm_selection_changed)
        self._ui.cmb_perm_report.currentIndexChanged.connect(self._on_perm_selection_changed)
        self._ui.btn_select_all.clicked.connect(lambda: self._set_all_samples(True))
        self._ui.btn_deselect_all.clicked.connect(lambda: self._set_all_samples(False))
        self._ui.btn_save_perms.clicked.connect(self._on_save_perms)

        # Tab 4: Paths
        self._ui.btn_browse_internal.clicked.connect(self._on_browse_internal)
        self._ui.btn_browse_external.clicked.connect(self._on_browse_external)

        # Tab 5: Column Settings
        self._ui.btn_col_edit.clicked.connect(self._on_edit_column)
        self._ui.btn_col_up.clicked.connect(self._on_col_up)
        self._ui.btn_col_down.clicked.connect(self._on_col_down)
        self._ui.btn_col_reset.clicked.connect(self._on_col_reset)

    # ---------- Tab 1: Report Management ----------

    def _refresh_report_table(self) -> None:
        tbl = self._ui.tbl_reports
        tbl.setRowCount(len(self._config.report_definitions))

        for i, r in enumerate(self._config.report_definitions):
            tbl.setItem(i, 0, QTableWidgetItem(r.report_id))
            tbl.setItem(i, 1, QTableWidgetItem(r.report_name))
            protocols = ", ".join(r.search_filters.get("protocol_name", []))
            tbl.setItem(i, 2, QTableWidgetItem(protocols))

    def _on_add_report(self) -> None:
        dlg = _ReportDialog(self, title="報告書追加")
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        report_name, protocols = dlg.get_values()
        if not report_name:
            QMessageBox.warning(self, "警告", "報告書名を入力してください。")
            return

        report_id = uuid.uuid4().hex[:8]

        new_report = ReportDefinition(
            report_id=report_id,
            report_name=report_name,
            search_filters={"protocol_name": protocols},
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

        dlg = _ReportDialog(
            self,
            title="報告書編集",
            report_name=r.report_name,
            protocols=", ".join(r.search_filters.get("protocol_name", [])),
        )
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        report_name, protocols = dlg.get_values()
        if not report_name:
            QMessageBox.warning(self, "警告", "報告書名を入力してください。")
            return

        r.report_name = report_name
        r.search_filters = {"protocol_name": protocols}
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

    def _refresh_dept_combo(self) -> None:
        self._ui.cmb_dept.blockSignals(True)
        self._ui.cmb_dept.clear()
        for d in self._config.departments:
            self._ui.cmb_dept.addItem(d.dept_name, d.dept_id)
        self._ui.cmb_dept.blockSignals(False)

    def _on_add_dept(self) -> None:
        dlg = _DeptDialog(self, title="部署追加")
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        dept_name, folder_name = dlg.get_values()
        if not dept_name:
            QMessageBox.warning(self, "警告", "部署名を入力してください。")
            return

        dept_id = uuid.uuid4().hex[:8]
        new_dept = Department(
            dept_id=dept_id,
            dept_name=dept_name,
            folder_name=folder_name,
        )
        self._config.departments.append(new_dept)
        self._refresh_dept_table()
        self._refresh_dept_combo()

    def _on_edit_dept(self) -> None:
        row = self._ui.tbl_depts.currentRow()
        if row < 0:
            QMessageBox.warning(self, "警告", "編集する部署を選択してください。")
            return

        d = self._config.departments[row]
        dlg = _DeptDialog(
            self,
            title="部署編集",
            dept_name=d.dept_name,
            folder_name=d.folder_name,
        )
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        dept_name, folder_name = dlg.get_values()
        if not dept_name:
            QMessageBox.warning(self, "警告", "部署名を入力してください。")
            return

        d.dept_name = dept_name
        d.folder_name = folder_name
        self._refresh_dept_table()
        self._refresh_dept_combo()

    def _on_delete_dept(self) -> None:
        row = self._ui.tbl_depts.currentRow()
        if row < 0:
            QMessageBox.warning(self, "警告", "削除する部署を選択してください。")
            return

        d = self._config.departments[row]
        ans = QMessageBox.question(
            self, "確認", f"部署「{d.dept_name}」を削除しますか？"
        )
        if ans == QMessageBox.StandardButton.Yes:
            self._config.departments.pop(row)
            self._refresh_dept_table()
            self._refresh_dept_combo()

    # ---------- Tab 3: Department Permissions ----------

    def _refresh_perm_report_combo(self) -> None:
        self._ui.cmb_perm_report.blockSignals(True)
        self._ui.cmb_perm_report.clear()
        for r in self._config.report_definitions:
            self._ui.cmb_perm_report.addItem(r.report_name, r.report_id)
        self._ui.cmb_perm_report.blockSignals(False)

    def _load_valid_samples(self) -> list[dict]:
        """Load and cache active WH samples from valid_samples.json."""
        if self._cached_samples is not None:
            return self._cached_samples

        self._cached_samples = []
        if _cfg.INTERNAL_PATH is None:
            return self._cached_samples

        json_path = _cfg.INTERNAL_PATH / "_common" / "master_data" / "source" / "valid_samples.json"
        if not json_path.exists():
            return self._cached_samples

        import json

        try:
            data = json.loads(json_path.read_text(encoding="utf-8"))
            items = data.get("items", [])
            self._cached_samples = sorted(
                [it for it in items if it.get("domain_code") == "WH" and it.get("is_active")],
                key=lambda it: it.get("sort_order", 0),
            )
        except Exception:
            pass

        return self._cached_samples

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

        samples = self._load_valid_samples()
        allowed = dept.allowed_samples.get(report.report_id, [])

        for item in samples:
            set_code = item.get("set_code", "")
            display = item.get("display_name", set_code)
            cb = QCheckBox(f"{display}  ({set_code})")
            cb.setProperty("sample_code", set_code)
            cb.setChecked(set_code in allowed)
            self._ui.sample_checkboxes.append(cb)
            self._ui.sample_list_layout.addWidget(cb)

    def _set_all_samples(self, checked: bool) -> None:
        for cb in self._ui.sample_checkboxes:
            cb.setChecked(checked)

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

    # ---------- Tab 5: Column Settings ----------

    def _refresh_column_table(self) -> None:
        tbl = self._ui.tbl_columns
        tbl.blockSignals(True)
        tbl.setRowCount(len(self._config.column_settings))

        for i, col in enumerate(self._config.column_settings):
            # Checkbox for visibility
            cb = QCheckBox()
            cb.setChecked(col.visible)
            cb.setStyleSheet("margin-left: 16px;")
            cb.stateChanged.connect(lambda state, row=i: self._on_col_visible_changed(row, state))
            tbl.setCellWidget(i, 0, cb)

            # Column key (read-only)
            key_item = QTableWidgetItem(col.column_key)
            tbl.setItem(i, 1, key_item)

            # Display name (read-only in table, edit via dialog)
            tbl.setItem(i, 2, QTableWidgetItem(col.display_name))

        tbl.blockSignals(False)

    def _on_col_visible_changed(self, row: int, state: int) -> None:
        if 0 <= row < len(self._config.column_settings):
            self._config.column_settings[row].visible = state == Qt.CheckState.Checked.value

    def _on_edit_column(self) -> None:
        row = self._ui.tbl_columns.currentRow()
        if row < 0:
            QMessageBox.warning(self, "警告", "編集する列を選択してください。")
            return

        col = self._config.column_settings[row]
        dlg = _ColumnDialog(
            self,
            title="列設定の編集",
            column_key=col.column_key,
            display_name=col.display_name,
            visible=col.visible,
        )
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        display_name, visible = dlg.get_values()
        if not display_name:
            QMessageBox.warning(self, "警告", "表示名を入力してください。")
            return

        col.display_name = display_name
        col.visible = visible
        self._refresh_column_table()

    def _on_col_up(self) -> None:
        row = self._ui.tbl_columns.currentRow()
        if row <= 0:
            return
        cs = self._config.column_settings
        cs[row - 1], cs[row] = cs[row], cs[row - 1]
        self._refresh_column_table()
        self._ui.tbl_columns.setCurrentCell(row - 1, 1)

    def _on_col_down(self) -> None:
        row = self._ui.tbl_columns.currentRow()
        cs = self._config.column_settings
        if row < 0 or row >= len(cs) - 1:
            return
        cs[row], cs[row + 1] = cs[row + 1], cs[row]
        self._refresh_column_table()
        self._ui.tbl_columns.setCurrentCell(row + 1, 1)

    def _on_col_reset(self) -> None:
        ans = QMessageBox.question(
            self, "確認", "列設定を初期値に戻しますか？"
        )
        if ans == QMessageBox.StandardButton.Yes:
            self._config.column_settings = [
                ColumnSetting(c.column_key, c.display_name, c.visible)
                for c in DEFAULT_COLUMN_SETTINGS
            ]
            self._refresh_column_table()

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

    def _save_and_accept(self) -> None:
        """Validate, save config to disk, and accept the dialog."""
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

    def _on_close(self) -> None:
        self._save_and_accept()

    def closeEvent(self, event) -> None:  # noqa: N802
        """Handle window close (×ボタン / Escキー) — save before closing."""
        self._save_and_accept()
        event.accept()
