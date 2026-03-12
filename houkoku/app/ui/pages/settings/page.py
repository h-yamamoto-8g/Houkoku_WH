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
    QFileDialog,
    QInputDialog,
    QMessageBox,
    QTableWidgetItem,
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
        self._refresh_dept_combo()
        self._refresh_perm_report_combo()
        self._refresh_path_display()

    def _connect_signals(self) -> None:
        self._ui.btn_close.clicked.connect(self._on_close)

        # Tab 1: Reports
        self._ui.btn_add_report.clicked.connect(self._on_add_report)
        self._ui.btn_edit_report.clicked.connect(self._on_edit_report)
        self._ui.btn_delete_report.clicked.connect(self._on_delete_report)

        # Tab 2: Permissions
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
        report_id, ok = QInputDialog.getText(self, "報告書追加", "報告書ID:")
        if not ok or not report_id:
            return

        report_name, ok = QInputDialog.getText(self, "報告書追加", "報告書名:")
        if not ok or not report_name:
            return

        protocols_str, ok = QInputDialog.getText(
            self, "報告書追加", "検索条件（プロトコル名、カンマ区切り）:"
        )
        if not ok:
            return

        protocols = [p.strip() for p in protocols_str.split(",") if p.strip()]

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

        report_name, ok = QInputDialog.getText(
            self, "報告書編集", "報告書名:", text=r.report_name
        )
        if not ok:
            return

        protocols_str, ok = QInputDialog.getText(
            self,
            "報告書編集",
            "検索条件（プロトコル名、カンマ区切り）:",
            text=", ".join(r.search_filters.get("protocol_name", [])),
        )
        if not ok:
            return

        protocols = [p.strip() for p in protocols_str.split(",") if p.strip()]
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
