from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import win32com.client  # pywin32
import win32gui
import win32con
import win32api

from lab_aid_extract.core.errors import ExcelLaunchError

"""
役割:
- Excel COM Automation を抽象化し、xlsmを開く/前面化/セル書込み/マクロ実行 を提供する

手順:
1) DispatchEx で Excel を起動
2) Workbooks.Open で xlsm を開く
3) 必要に応じて前面化
4) セル入力やマクロ実行を行う
"""


@dataclass
class ExcelSession:
    app: Any
    workbook: Any


class ExcelService:
    def __init__(self, visible: bool):
        self._visible = visible

    def open_workbook(self, xlsm_path: Path) -> ExcelSession:
        """
        役割:
        - Excelを起動し、xlsmを開く

        手順:
        1) Excel.Application を DispatchEx で起動
        2) Visible, DisplayAlerts を設定
        3) Workbooks.Open で xlsm を開く
        """
        try:
            app = win32com.client.DispatchEx("Excel.Application")
            app.Visible = bool(self._visible)
            app.DisplayAlerts = False
            wb = app.Workbooks.Open(str(xlsm_path))
            return ExcelSession(app=app, workbook=wb)
        except Exception as e:
            raise ExcelLaunchError(f"Excel起動またはブックオープンに失敗: {e}") from e

    def get_hwnd(self, session: ExcelSession) -> int:
        """役割: Excelアプリのウィンドウハンドルを取得する"""
        try:
            return int(session.app.Hwnd)
        except Exception as e:
            raise ExcelLaunchError(f"Excel HWND取得に失敗: {e}") from e

    def bring_to_front_best_effort(self, session: ExcelSession) -> None:
        """
        役割:
        - Excelを最前面に出す（失敗しても致命にしない）

        手順:
        1) hwnd取得
        2) 最小化なら復帰
        3) 前面化を試行（Windows制約で失敗し得る）
        """
        try:
            hwnd = self.get_hwnd(session)
            if win32gui.IsIconic(hwnd):
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            try:
                win32gui.SetForegroundWindow(hwnd)
                win32gui.BringWindowToTop(hwnd)
            except Exception:
                pass
        except Exception:
            pass

    def show_user_prompt(self, title: str, message: str) -> None:
        """
        役割:
        - コンソールなしでもユーザーに操作を促す（手動ログインの合図）

        手順:
        - win32api.MessageBox でOK待ちダイアログを出す
        """
        # 0x00000000 = OK only
        # win32api.MessageBox(0, message, title, 0x00000000)
        return

    def activate_sheet(self, session: ExcelSession, sheet_key: str) -> None:
        """
        役割:
        - ActiveSheet依存のため対象シートをアクティブ化（表示名/CodeName両対応）

        手順:
        1) Worksheets(sheet_key)（表示名）で試す
        2) 失敗なら全シートを走査し Name/CodeName 一致で探す
        """
        wb = session.workbook
        try:
            ws = wb.Worksheets(sheet_key)
            ws.Activate()
            return
        except Exception:
            pass

        candidates = []
        try:
            for ws in wb.Worksheets:
                name = str(ws.Name)
                try:
                    code_name = str(ws.CodeName)
                except Exception:
                    code_name = None
                candidates.append({"name": name, "code_name": code_name})
                if name == sheet_key or (code_name is not None and code_name == sheet_key):
                    ws.Activate()
                    return
        except Exception as e:
            raise ExcelLaunchError(f"シート一覧取得に失敗: {e}") from e

        raise ExcelLaunchError(f"指定シートが見つかりません: '{sheet_key}'. 候補: {candidates}")

    def set_cell_value(self, session: ExcelSession, sheet_name: str, address: str, value: Any) -> None:
        """
        役割:
        - セルへ値を設定（結合セルはMergeAreaへ）

        手順:
        1) Range取得
        2) MergeCellsなら MergeArea.Value
        3) それ以外は Value
        """
        try:
            ws = session.workbook.Worksheets(sheet_name)
            rng = ws.Range(address)
            if bool(rng.MergeCells):
                rng.MergeArea.Value = value
            else:
                rng.Value = value
        except Exception as e:
            raise ExcelLaunchError(f"セル書き込みに失敗: {sheet_name}!{address} -> {e}") from e

    def get_cell_text(self, session: ExcelSession, sheet_name: str, address: str) -> str:
        """役割: デバッグ用にセルの Text を取得する"""
        ws = session.workbook.Worksheets(sheet_name)
        return str(ws.Range(address).Text)

    def calculate(self, session: ExcelSession) -> None:
        """役割: 入力後に計算/状態更新を促す（失敗しても致命にしない）"""
        try:
            session.app.Calculate()
        except Exception:
            pass

    def run_sheet_macro(self, session: ExcelSession, sheet_code_name: str, proc_name: str) -> str:
        """
        役割:
        - 開いているブック名から動的にマクロ参照文字列を生成し、確実に実行する

        手順:
        1) workbook.Name を取得（(1)付き等でも正しく参照するため）
        2) "'ブック名'!shtSearch.実行ボタン_Click" の形式で Application.Run
        3) 実行したマクロ文字列を返す（result.json に残すため）
        """
        wb_name = str(session.workbook.Name)
        macro = f"'{wb_name}'!{sheet_code_name}.{proc_name}"
        try:
            session.app.Run(macro)
            return macro
        except Exception as e:
            raise ExcelLaunchError(f"マクロ実行に失敗: {macro} -> {e}") from e

    def close(self, session: ExcelSession) -> None:
        """
        役割:
        - Excelを閉じる（Excel側が落ちていても落とさない）

        手順:
        - Close/Quit を例外握りつぶしで実行
        """
        try:
            try:
                session.workbook.Close(SaveChanges=False)
            except Exception:
                pass
        finally:
            try:
                session.app.Quit()
            except Exception:
                pass
