from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict, Any

"""
役割:
- CLI入力と結果を型として固定し、層間の受け渡しを明確化する

手順:
- Request: 実行条件をまとめる
- Result : result.json に出す内容をまとめる
"""


@dataclass(frozen=True)
class ExtractRequest:
    """
    役割:
    - 実行条件DTO（services層に渡す）

    手順:
    1) app/main.py で引数 parse
    2) path_service で xlsm/out_dir を解決
    3) このDTOに詰めて extractor_service に渡す
    """
    xlsm_path: Path
    domain_code: str
    year: int
    out_dir: Path

    visible: bool = True
    keep_open: bool = False

    # ユーザーに表示する文言（手動ログイン促進）
    # prompt_title: str = "Lab-Aid Extract"
    # prompt_message: str = "Excel上でログインを完了したら「OK」を押してください。"

    # result.json出力先（mainで解決して渡す）
    result_json_path: Optional[Path] = None


@dataclass
class ExtractResult:
    """
    役割:
    - result.json 出力用 DTO（親アプリが機械的に読める）

    フィールド:
    - ok: 成否
    - message: 要約メッセージ
    - csv_path: 成功時のCSVパス
    - details: デバッグ/分類情報
    """
    ok: bool
    message: str
    csv_path: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
