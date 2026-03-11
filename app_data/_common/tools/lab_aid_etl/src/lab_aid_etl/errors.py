"""
errors

役割:
- ETL全体で共通利用する「終了コード付き例外」を定義する

手順:
1) EtlError を基底として error_code を持たせる
2) 代表的なカテゴリ（Input/Master/Csv）を派生で用意する
"""

from __future__ import annotations


class EtlError(Exception):
    """役割: error_code を持つ例外の基底クラス（exit code と result.json に反映する）"""
    error_code: int = 9


class InputError(EtlError):
    """役割: 引数・入出力パスなど、実行前に検知できる不備を表す"""
    error_code = 2


class MasterDataError(EtlError):
    """役割: master_data 側の不整合（重複所属・必須キー欠落・形式不正）を表す"""
    error_code = 3


class CsvError(EtlError):
    """役割: CSV の整合性不備（ヘッダ不一致・列数不一致など）を表す"""
    error_code = 4
