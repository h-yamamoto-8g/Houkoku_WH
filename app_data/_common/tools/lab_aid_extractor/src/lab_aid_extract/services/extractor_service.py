from __future__ import annotations

import calendar
import datetime
from pathlib import Path
from typing import Dict, Any, Tuple

from lab_aid_extract.core.models import ExtractRequest
from lab_aid_extract.core.errors import ExportFailedError
from lab_aid_extract.services.win_event_wait_service import LoginWindowCloseWaiter
from lab_aid_extract.services.excel_service import ExcelService, ExcelSession

"""
役割:
- “xlsmを開く→ログインフォーム表示→ユーザー手動ログイン→設定入力→実行マクロ→CSV確認” を統合する

手順:
1) Excel起動＆xlsmを開く
2) Excelを最前面へ（ベストエフォート）
3) ログインフォーム表示マクロ実行（フォーム表示は必須）
4) ユーザーに「ログイン完了したらOK」を促す（MessageBoxで停止）
5) 設定セルへ値を反映（M5修正済み）
6) CSV出力マクロ実行
7) CSV存在確認
8) keep_openでなければExcelを閉じる
"""


class LabAidExtractorService:
    def __init__(self, excel: ExcelService):
        self._excel = excel

    def run(self, req: ExtractRequest) -> Tuple[Path, Dict[str, Any]]:
        session = self._excel.open_workbook(req.xlsm_path)
        debug: Dict[str, Any] = {}

        try:
            # 2) 最前面化（ユーザー操作を優先）
            self._excel.bring_to_front_best_effort(session)

            # 3) ログインフォーム表示（マクロ）
            self._excel.activate_sheet(session, "shtSearch")
            macro_login = self._excel.run_sheet_macro(session, "shtSearch", "ログインボタン_Click")
            debug["macro_login"] = macro_login

            # 4) 手動ログイン（待機機能は廃止し、ユーザーOKで続行）
            self._excel.bring_to_front_best_effort(session)
            # self._excel.show_user_prompt(req.prompt_title, req.prompt_message)

            # 5) 設定反映（ログイン後に確実にアクティブ化）
            session.workbook.Activate()
            self._excel.activate_sheet(session, "shtSearch")
            debug.update(self._apply_settings(session, req))

            # 6) CSV出力
            session.workbook.Activate()
            self._excel.activate_sheet(session, "shtSearch")
            macro_export = self._excel.run_sheet_macro(session, "shtSearch", "実行ボタン_Click")
            debug["macro_export"] = macro_export

            # 7) CSV確認
            csv_path = self._expected_csv_path(req)
            if not csv_path.exists():
                raise ExportFailedError(f"CSVが生成されていません: {csv_path}")

            return csv_path, debug

        finally:
            if not req.keep_open:
                try:
                    self._excel.close(session)
                except Exception:
                    pass

    def _apply_settings(self, session: ExcelSession, req: ExtractRequest) -> Dict[str, Any]:
        """
        役割:
        - 現行手順の「設定入力」をセル書き込みで再現する（ファイル名セルはM5）

        手順:
        1) out_dir を作成
        2) ファイル名 stem を作成（lab_data_<domain>_<year>）
        3) 日付範囲（FROM=1/1, TO=最新月末）を設定
        4) セルへ書き込み
        5) calculate() で反映を促す
        6) get_cell_text() で読み戻し（デバッグ用）
        """
        sheet = "shtSearch"
        out_dir = req.out_dir
        out_dir.mkdir(parents=True, exist_ok=True)

        file_stem = f"lab_data_{req.domain_code}_{req.year}"

        today = datetime.date.today()
        latest_month = today.month if today.year == req.year else 12
        last_day = calendar.monthrange(req.year, latest_month)[1]

        # 保存先
        self._excel.set_cell_value(session, sheet, "E3", str(out_dir))
        # ファイル名（拡張子なし）※M5が正しい
        self._excel.set_cell_value(session, sheet, "M5", file_stem)
        # domain_code
        self._excel.set_cell_value(session, sheet, "D7", req.domain_code)

        # FROM yyyy/1/1
        self._excel.set_cell_value(session, sheet, "D11", req.year)
        self._excel.set_cell_value(session, sheet, "E11", 1)
        self._excel.set_cell_value(session, sheet, "F11", 1)

        # TO yyyy/latest_month/last_day
        self._excel.set_cell_value(session, sheet, "D12", req.year)
        self._excel.set_cell_value(session, sheet, "E12", latest_month)
        self._excel.set_cell_value(session, sheet, "F12", last_day)

        # 入力確定・状態更新（失敗しても続行）
        self._excel.calculate(session)

        return {
            "E3_text": self._excel.get_cell_text(session, sheet, "E3"),
            "M5_text": self._excel.get_cell_text(session, sheet, "M5"),
            "D7_text": self._excel.get_cell_text(session, sheet, "D7"),
            "D11_text": self._excel.get_cell_text(session, sheet, "D11"),
            "E11_text": self._excel.get_cell_text(session, sheet, "E11"),
            "F11_text": self._excel.get_cell_text(session, sheet, "F11"),
            "D12_text": self._excel.get_cell_text(session, sheet, "D12"),
            "E12_text": self._excel.get_cell_text(session, sheet, "E12"),
            "F12_text": self._excel.get_cell_text(session, sheet, "F12"),
            "out_dir": str(out_dir),
            "file_stem": file_stem,
        }

    def _expected_csv_path(self, req: ExtractRequest) -> Path:
        return req.out_dir / f"lab_data_{req.domain_code}_{req.year}.csv"
