from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from lab_aid_extract.core.models import ExtractResult

"""
役割:
- result.json を統一フォーマットで出力する

手順:
1) ExtractResult を dict 化
2) UTF-8でJSON保存
"""


class ResultWriter:
    def __init__(self, path: Path):
        self._path = path

    def write(self, result: ExtractResult) -> None:
        payload = asdict(result)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
