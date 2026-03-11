from __future__ import annotations

import csv
import os
from typing import Any, Dict, List

from .errors import InputError


def _eval_domain_filter(domain_filter: Dict[str, Any], row: Dict[str, str]) -> bool:
    """
    役割:
    - domain_filter を評価する（現運用：test.domain_code == WH）

    手順:
    1) entity/field/op/value を読む
    2) entity=test & field=domain_code の場合、row["test_domain_code"] を参照
    3) op を評価
    """
    entity = domain_filter.get("entity")
    field = domain_filter.get("field")
    op = domain_filter.get("op")
    value = domain_filter.get("value")

    if entity == "test" and field == "domain_code":
        left = row.get("test_domain_code", "")
    else:
        # 将来拡張用：必要なら row の任意列参照を許容
        left = row.get(field or "", "")

    if op == "eq":
        return left == value
    if op == "neq":
        return left != value

    raise ValueError(f"Unsupported domain_filter op: {op}")


def extract_profile_csv(
    in_csv: str,
    out_csv: str,
    columns_allowlist: List[str],
    domain_filter: Dict[str, Any],
    encoding: str,
    delimiter: str,
) -> Dict[str, int]:
    """
    役割:
    - 正規化済みCSVからプロファイル用CSVを作る
    - 入出力行数を返す（result.json用）

    手順:
    1) 入力存在チェック
    2) DictReaderで読み、filter→allowlistで書く
    """
    if not os.path.isfile(in_csv):
        raise InputError(f"Input CSV not found: {in_csv}")

    os.makedirs(os.path.dirname(out_csv) or ".", exist_ok=True)

    input_rows = 0
    output_rows = 0

    with open(in_csv, "r", encoding=encoding, newline="") as rf, open(out_csv, "w", encoding=encoding, newline="") as wf:
        reader = csv.DictReader(rf, delimiter=delimiter)
        writer = csv.DictWriter(wf, fieldnames=columns_allowlist, delimiter=delimiter)
        writer.writeheader()

        for row in reader:
            input_rows += 1

            if not _eval_domain_filter(domain_filter, row):
                continue

            out_row = {c: row.get(c, "") for c in columns_allowlist}
            writer.writerow(out_row)
            output_rows += 1

    return {"input_rows": input_rows, "output_rows": output_rows}