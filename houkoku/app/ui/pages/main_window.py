"""Main window wrapper.

Wraps Ui_MainWindow, connects signals, and delegates to services.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QMainWindow,
    QMessageBox,
    QTableWidgetItem,
)

from app.core.config_store import AppConfig, ReportDefinition
from app.core.permission_store import DepartmentSummary
from app.services.report_service import ReportService
from app.services import notification_service
from app.ui.dialogs.loading_dialog import LoadingOverlay, WorkerThread
from app.ui.dialogs.send_confirm_dialog import SendConfirmDialog
from app.ui.generated.ui_mainwindow import Ui_MainWindow


# Preview columns to show (subset of the 51 CSV columns)
PREVIEW_COLUMNS = [
    "sample_code",
    "sample_name",
    "valid_sample_set_code",
    "sample_job_number",
    "request_protocol_name",
    "holder_name",
    "test_name",
    "test_reported_data",
    "test_unit_name",
]


class MainWindow(QMainWindow):
    """Application main window."""

    def __init__(self, services: dict) -> None:
        super().__init__()
        self._ui = Ui_MainWindow()
        self._ui.setupUi(self)

        self._report_svc: ReportService = services["report"]
        self._config: Optional[AppConfig] = None
        self._current_report: Optional[ReportDefinition] = None
        self._current_job: Optional[str] = None
        self._dept_summaries: list[DepartmentSummary] = []

        self._overlay = LoadingOverlay(self)
        self._worker: Optional[WorkerThread] = None

        self._connect_signals()

    def set_config(self, config: AppConfig) -> None:
        """Set config and populate report combo."""
        self._config = config
        self._report_svc.set_config(config)
        self._populate_reports()

    # ---------- Signal Connections ----------

    def _connect_signals(self) -> None:
        self._ui.cmb_report.currentIndexChanged.connect(self._on_report_changed)
        self._ui.cmb_job.currentIndexChanged.connect(self._on_job_changed)
        self._ui.btn_export.clicked.connect(self._on_export)
        self._ui.btn_send.clicked.connect(self._on_send)
        self._ui.btn_settings.clicked.connect(self._on_settings)

    # ---------- UI Population ----------

    def _populate_reports(self) -> None:
        self._ui.cmb_report.blockSignals(True)
        self._ui.cmb_report.clear()

        reports = self._report_svc.get_report_definitions()
        for r in reports:
            self._ui.cmb_report.addItem(r.report_name, r.report_id)

        self._ui.cmb_report.blockSignals(False)

        if reports:
            self._ui.cmb_report.setCurrentIndex(0)
            self._on_report_changed(0)

    def _on_report_changed(self, index: int) -> None:
        reports = self._report_svc.get_report_definitions()
        if index < 0 or index >= len(reports):
            return

        self._current_report = reports[index]

        # Update job numbers
        jobs = self._report_svc.get_job_numbers(self._current_report)
        self._ui.cmb_job.blockSignals(True)
        self._ui.cmb_job.clear()
        for j in jobs:
            self._ui.cmb_job.addItem(str(j))
        self._ui.cmb_job.blockSignals(False)

        if jobs:
            self._ui.cmb_job.setCurrentIndex(0)
            self._on_job_changed(0)
        else:
            self._clear_preview()

    def _on_job_changed(self, index: int) -> None:
        if index < 0 or self._current_report is None:
            return

        self._current_job = self._ui.cmb_job.currentText()
        if not self._current_job:
            return

        self._overlay.set_message("データ読み込み中...")
        self._overlay.show_overlay()

        report = self._current_report
        job = self._current_job

        def do_preview():
            return self._report_svc.preview_job(report, job)

        self._worker = WorkerThread(do_preview, self)
        self._worker.finished.connect(self._on_job_preview_done)
        self._worker.error.connect(self._on_worker_error)
        self._worker.start()

    def _on_job_preview_done(self, result: object) -> None:
        self._overlay.hide_overlay()
        if not isinstance(result, tuple):
            return
        df, summaries = result
        self._apply_preview(df)
        self._apply_department_list(summaries)

    # ---------- Preview ----------

    def _apply_preview(self, df: "pd.DataFrame") -> None:
        """Populate preview table from a pre-computed DataFrame."""
        # Show subset of columns that exist
        cols = [c for c in PREVIEW_COLUMNS if c in df.columns]
        display = df[cols] if cols else df

        unique_samples = df["valid_sample_set_code"].nunique() if not df.empty else 0
        self._ui.lbl_sample_count.setText(f"対象サンプル: {unique_samples}件 ({len(df)}行)")

        # Populate table
        self._ui.tbl_preview.setRowCount(min(len(display), 200))
        self._ui.tbl_preview.setColumnCount(len(display.columns))
        self._ui.tbl_preview.setHorizontalHeaderLabels(list(display.columns))

        for row_idx in range(min(len(display), 200)):
            for col_idx, col_name in enumerate(display.columns):
                val = display.iloc[row_idx, col_idx]
                self._ui.tbl_preview.setItem(
                    row_idx, col_idx, QTableWidgetItem(str(val) if val is not None else "")
                )

    def _apply_department_list(self, summaries: list["DepartmentSummary"]) -> None:
        """Populate department checkboxes from pre-computed summaries."""
        self._dept_summaries = summaries

        # Clear existing checkboxes
        for cb in self._ui.dept_checkboxes:
            self._ui.dept_list_layout.removeWidget(cb)
            cb.deleteLater()
        self._ui.dept_checkboxes.clear()

        # Create new checkboxes
        for s in self._dept_summaries:
            codes_str = ", ".join(s.sample_codes[:5])
            if len(s.sample_codes) > 5:
                codes_str += "..."

            label = f"{s.dept_name}  →  {s.sample_count}件"
            if codes_str:
                label += f" ({codes_str})"

            cb = QCheckBox(label)
            cb.setProperty("dept_id", s.dept_id)
            cb.setChecked(s.sample_count > 0)
            cb.setEnabled(s.sample_count > 0)
            self._ui.dept_checkboxes.append(cb)
            self._ui.dept_list_layout.addWidget(cb)

    def _clear_preview(self) -> None:
        self._ui.lbl_sample_count.setText("対象サンプル: -")
        self._ui.tbl_preview.setRowCount(0)
        self._ui.tbl_preview.setColumnCount(0)
        for cb in self._ui.dept_checkboxes:
            self._ui.dept_list_layout.removeWidget(cb)
            cb.deleteLater()
        self._ui.dept_checkboxes.clear()

    # ---------- Export ----------

    def _get_selected_dept_ids(self) -> list[str]:
        return [
            cb.property("dept_id")
            for cb in self._ui.dept_checkboxes
            if cb.isChecked()
        ]

    def _on_export(self) -> None:
        if self._current_report is None or self._current_job is None:
            QMessageBox.warning(self, "警告", "報告書とJOB番号を選択してください。")
            return

        selected = self._get_selected_dept_ids()
        if not selected:
            QMessageBox.warning(self, "警告", "出力先の部署を選択してください。")
            return

        self._overlay.set_message("CSV出力中...")
        self._overlay.show_overlay()

        report = self._current_report
        job = self._current_job

        def do_export():
            return self._report_svc.export_report(
                report=report,
                job_number=job,
                selected_dept_ids=selected,
            )

        self._worker = WorkerThread(do_export, self)
        self._worker.finished.connect(self._on_export_done)
        self._worker.error.connect(self._on_worker_error)
        self._worker.start()

    def _on_export_done(self, result: object) -> None:
        self._overlay.hide_overlay()
        exported = result if isinstance(result, dict) else {}
        count = len(exported)
        self._ui.lbl_status.setText(f"{count}部署にCSVを出力しました。")
        QMessageBox.information(
            self,
            "出力完了",
            f"SharePointに出力しました。\n{count}部署のCSVファイルを作成しました。\n"
            "Excel Onlineで確認してください。",
        )

    # ---------- Send ----------

    def _on_send(self) -> None:
        if self._current_report is None or self._current_job is None:
            QMessageBox.warning(self, "警告", "報告書とJOB番号を選択してください。")
            return

        selected_ids = self._get_selected_dept_ids()
        if not selected_ids:
            QMessageBox.warning(self, "警告", "送信先の部署を選択してください。")
            return

        # Filter summaries to selected departments
        selected_summaries = [
            s for s in self._dept_summaries if s.dept_id in selected_ids
        ]
        message = self._ui.txt_message.toPlainText()

        dlg = SendConfirmDialog(selected_summaries, message, self)
        if dlg.exec() != SendConfirmDialog.DialogCode.Accepted:
            return

        self._overlay.set_message("送信中...")
        self._overlay.show_overlay()

        report = self._current_report
        job = self._current_job
        departments = [
            d
            for d in self._report_svc.get_departments()
            if d.dept_id in selected_ids
        ]

        def do_send():
            return notification_service.send_all(
                report=report,
                job_number=job,
                departments=departments,
                message=message,
            )

        self._worker = WorkerThread(do_send, self)
        self._worker.finished.connect(self._on_send_done)
        self._worker.error.connect(self._on_worker_error)
        self._worker.start()

    def _on_send_done(self, result: object) -> None:
        self._overlay.hide_overlay()
        paths = result if isinstance(result, list) else []
        self._ui.lbl_status.setText(f"{len(paths)}部署に送信完了。")
        QMessageBox.information(
            self, "送信完了", f"{len(paths)}部署への通知が完了しました。"
        )

    # ---------- Error Handling ----------

    def _on_worker_error(self, msg: str) -> None:
        self._overlay.hide_overlay()
        self._ui.lbl_status.setText(f"エラー: {msg}")
        QMessageBox.critical(self, "エラー", msg)

    # ---------- Settings ----------

    def _on_settings(self) -> None:
        from app.ui.pages.settings.page import SettingsPage

        dlg = SettingsPage(self._config, self._report_svc, self)
        if dlg.exec() == SettingsPage.DialogCode.Accepted:
            new_config = dlg.get_config()
            if new_config:
                self.set_config(new_config)
                self._ui.lbl_status.setText("設定を保存しました。")

    # ---------- Resize ----------

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._overlay.setGeometry(self.rect())
