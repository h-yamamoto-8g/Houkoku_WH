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
        self._refresh_dept_combo()
        self._refresh_perm_report_combo()
        self._refresh_path_display()

    def _connect_signals(self) -> None:
        self._ui.btn_close.clicked.connect(self._on_close)

        # Tab 1: Reports
        self._ui.btn_add_report.clicked.connect(self._on_add_report)
        self._ui.btn_edit_report.clicked.connect(self._on_edit_report)
        self._ui.btn_delete_report.clicked.connect(self._on_delete_report)

        # Tab 2: Departments & Permissions
        self._ui.btn_add_dept.clicked.connect(self._on_add_dept)
        self._ui.btn_edit_dept.clicked.connect(self._on_edit_dept)
        self._ui.btn_delete_dept.clicked.connect(self._on_delete_dept)
        self._ui.cmb_dept.currentIndexChanged.connect(self._on_perm_selection_changed)
        self._ui.cmb_perm_report.currentIndexChanged.connect(self._on_perm_selection_changed)
        self._ui.btn_save_perms.clicked.connect(self._on_save_perms)

        # Tab 3: Paths
        self._ui.btn_browse_internal.clicked.connect(self._on_browse_internal)
        self._ui.btn_browse_external.clicked.connect(self._on_browse_external)

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

    # ---------- Tab 2: Department Permissions ----------

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
        self._refresh_dept_combo()
        # 追加した部署を選択状態にする
        self._ui.cmb_dept.setCurrentIndex(self._ui.cmb_dept.count() - 1)

    def _on_edit_dept(self) -> None:
        idx = self._ui.cmb_dept.currentIndex()
        if idx < 0:
            QMessageBox.warning(self, "警告", "編集する部署を選択してください。")
            return

        d = self._config.departments[idx]
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
        self._refresh_dept_combo()
        self._ui.cmb_dept.setCurrentIndex(idx)

    def _on_delete_dept(self) -> None:
        idx = self._ui.cmb_dept.currentIndex()
        if idx < 0:
            QMessageBox.warning(self, "警告", "削除する部署を選択してください。")
            return

        d = self._config.departments[idx]
        ans = QMessageBox.question(
            self, "確認", f"部署「{d.dept_name}」を削除しますか？"
        )
        if ans == QMessageBox.StandardButton.Yes:
            self._config.departments.pop(idx)
            self._refresh_dept_combo()

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

    # ---------- Tab 3: Path Settings ----------

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
