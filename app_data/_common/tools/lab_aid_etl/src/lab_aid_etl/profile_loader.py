from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional

from lab_aid_etl.errors import InputError


def _find_common_dir(start_dir: str) -> str:
    """
    役割:
    - 実行場所がどこでも、実体の "_common" ディレクトリを見つける

    手順:
    1) start_dir から親ディレクトリへ順に遡る
    2) 各階層で "<dir>/_common" が存在すればそれを採用
    3) 見つからなければ InputError
    """
    cur = os.path.abspath(start_dir)
    while True:
        candidate = os.path.join(cur, "_common")
        if os.path.isdir(candidate):
            return candidate

        parent = os.path.dirname(cur)
        if parent == cur:
            break
        cur = parent

    raise InputError('"_common" directory not found from current directory and parents.')


def _resolve_common_relative(path_value: str, common_dir: str) -> str:
    """
    役割:
    - "_common/..." のような論理パスを、実体の _common ディレクトリ基点で絶対パスに変換する

    手順:
    1) 先頭が "_common" の場合だけ変換
    2) それ以外はそのまま返す（相対/絶対どちらも許容）
    """
    if not isinstance(path_value, str):
        return path_value

    norm = path_value.replace("\\", "/")
    if norm.startswith("_common/") or norm == "_common":
        tail = norm[len("_common/") :] if norm != "_common" else ""
        return os.path.abspath(os.path.join(common_dir, tail))

    return path_value


def resolve_profile_path(profile_name: str, profile_dir: Optional[str]) -> str:
    """
    役割:
    - profile JSON のファイルパスを確定する

    手順:
    1) profile_dir が指定されていればそこから探す（相対なら cwd 基点）
    2) 指定が無ければ、実体の _common/master_data/views を自動探索してそこから探す
    """
    if profile_dir:
        return os.path.join(profile_dir, f"{profile_name}.json")

    common_dir = _find_common_dir(os.getcwd())
    return os.path.join(common_dir, "master_data", "views", f"{profile_name}.json")


def load_profile(profile_name: str, profile_dir: Optional[str]) -> Dict[str, Any]:
    """
    役割:
    - profile を読み込み、paths を絶対パス化して返す

    手順:
    1) profile path を確定して JSON 読み込み
    2) 必須キー（paths/extract）を検証
    3) paths.* が "_common/..." の場合、実体 _common 基点で絶対パス化
    4) extract 設定の最低限検証（columns_allowlist / domain_filter）
    """
    profile_path = resolve_profile_path(profile_name, profile_dir)
    if not os.path.isfile(profile_path):
        raise InputError(f"profile not found: {profile_path}")

    with open(profile_path, "r", encoding="utf-8") as f:
        obj = json.load(f)

    if "paths" not in obj or "extract" not in obj:
        raise InputError("profile missing required keys: paths/extract")

    common_dir = _find_common_dir(os.getcwd())

    paths = obj.get("paths", {})
    if isinstance(paths, dict):
        resolved = {}
        for k, v in paths.items():
            resolved[k] = _resolve_common_relative(v, common_dir)
        obj["paths"] = resolved

    ex = obj["extract"]
    if "columns_allowlist" not in ex or not isinstance(ex["columns_allowlist"], list):
        raise InputError("profile.extract.columns_allowlist is required (list)")

    if "domain_filter" not in ex or not isinstance(ex["domain_filter"], dict):
        raise InputError("profile.extract.domain_filter is required (dict)")

    # field方式の検証（安定版仕様に戻す）
    df = ex["domain_filter"]
    if "field" not in df or not isinstance(df.get("field"), str) or not df.get("field"):
        raise InputError("domain_filter.field is required (non-empty string)")

    return obj