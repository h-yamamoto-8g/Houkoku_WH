"""
役割:
- アプリ内例外を分類し、result.json / exit code を安定させる

手順:
- 例外の種類ごとにクラスを分ける
"""


class LabAidExtractError(Exception):
    """アプリ内で扱う共通基底例外（期待する失敗）"""


class PathResolveError(LabAidExtractError):
    """パス解決（xlsm/app_data/out_dir など）の失敗"""


class ExcelLaunchError(LabAidExtractError):
    """Excel起動・ブック操作・セル操作・マクロ実行の失敗"""


class ExportFailedError(LabAidExtractError):
    """CSV出力後のファイル存在確認などが失敗"""
