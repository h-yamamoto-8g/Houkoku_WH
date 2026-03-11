"""
merge_service

役割:
- yearly CSV を縦連結して full.csv を生成する

手順:
1) yearly_dir 配下のCSVを昇順に列挙
2) 1本目のヘッダを基準ヘッダとして保持
3) 2本目以降はヘッダ一致を検証（strict）
4) 出力CSVにヘッダを1回だけ書き、データ行を追記
"""

from __future__ import annotations

import csv
import os
from typing import List

from .errors import CsvError, InputError


def merge_yearly_csvs(
    yearly_dir: str,
    out_csv: str,
    encoding: str,
    delimiter: str,
    strict_header: bool = True,
) -> None:
    """役割: 年別CSVを縦連結して out_csv を作る"""
    if not os.path.isdir(yearly_dir):
        raise InputError(f"yearly_dir not found: {yearly_dir}")

    files = sorted([f for f in os.listdir(yearly_dir) if f.lower().endswith(".csv")])
    if not files:
        raise InputError(f"No CSV files in: {yearly_dir}")

    os.makedirs(os.path.dirname(out_csv) or ".", exist_ok=True)

    expected_header: List[str] | None = None

    with open(out_csv, "w", encoding=encoding, newline="") as wf:
        writer = csv.writer(wf, delimiter=delimiter)

        for fname in files:
            path = os.path.join(yearly_dir, fname)
            with open(path, "r", encoding=encoding, newline="") as rf:
                reader = csv.reader(rf, delimiter=delimiter)
                header = next(reader, None)
                if header is None:
                    continue

                if expected_header is None:
                    expected_header = header
                    writer.writerow(expected_header)
                else:
                    if strict_header and header != expected_header:
                        raise CsvError(
                            f"Header mismatch in {fname}. expected={expected_header} actual={header}"
                        )

                for row in reader:
                    writer.writerow(row)

    if expected_header is None:
        raise CsvError("No header written (all files empty?)")
