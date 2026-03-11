"""
result_writer

役割:
- result.json を「成功/失敗に関わらず必ず」出力する

手順:
1) 出力先ディレクトリを作成
2) JSONを整形して保存（ensure_ascii=False）
"""

from __future__ import annotations

import json
import os
from typing import Any


def write_result_json(path: str, payload: dict[str, Any]) -> None:
    """役割: result.json を保存する（ディレクトリが無ければ作成）"""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
