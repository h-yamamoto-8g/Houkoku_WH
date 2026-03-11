"""
cli

役割:
- lab_aid_etl のコマンド入口（merge/normalize/extract/build）
- result.json を成功/失敗に関わらず必ず出力し、exit code を返す

手順:
1) argparse でコマンドを解析
2) 個別コマンド or build（merge→normalize→extract）を実行
3) 例外は EtlError の error_code を優先し result.json に記録
"""

from __future__ import annotations

import argparse
import os
import time
from typing import Any, Dict, Optional

from lab_aid_etl.errors import EtlError, InputError
from lab_aid_etl.result_writer import write_result_json
from lab_aid_etl.master_loader import load_master_data
from lab_aid_etl.merge_service import merge_yearly_csvs
from lab_aid_etl.normalize_service import normalize_full_csv
from lab_aid_etl.extract_service import extract_profile_csv
from lab_aid_etl.profile_loader import load_profile, resolve_profile_path

def _parser() -> argparse.ArgumentParser:
    """役割: CLI仕様を定義する（サブコマンド分割で責務を保つ）"""
    p = argparse.ArgumentParser(prog="lab_aid_etl")
    sub = p.add_subparsers(dest="command", required=True)

    # merge
    m = sub.add_parser("merge", help="yearly csvs -> full.csv")
    m.add_argument("--in", dest="yearly_dir", required=True)
    m.add_argument("--out", dest="out_csv", required=True)
    m.add_argument("--encoding", default="utf-8")
    m.add_argument("--delimiter", default=",")

    # normalize
    n = sub.add_parser("normalize", help="full.csv -> full_normalized.csv")
    n.add_argument("--in", dest="in_csv", required=True)
    n.add_argument("--out", dest="out_csv", required=True)
    n.add_argument("--master", dest="master_dir", required=True)
    n.add_argument("--unknown-policy", default="unknown", choices=["unknown", "empty"])
    n.add_argument("--encoding", default="utf-8")
    n.add_argument("--delimiter", default=",")

    # extract
    e = sub.add_parser("extract", help="full_normalized.csv -> profile csv")
    e.add_argument("--in", dest="in_csv", required=True)
    e.add_argument("--out", dest="out_csv", required=True)
    e.add_argument("--profile", required=True)
    e.add_argument("--profile-dir", default=None)
    e.add_argument("--encoding", default="utf-8")
    e.add_argument("--delimiter", default=",")

    # build
    b = sub.add_parser("build", help="merge -> normalize -> extract by profile")
    b.add_argument("--profile", required=True)
    b.add_argument("--profile-dir", default=None)
    b.add_argument("--force-merge", action="store_true")
    return p


def _safe_result_path(profile_name: str, profile_dir: Optional[str]) -> str:
    """
    役割:
    - profileが読めない場合でも result.json の出力先を決める

    手順:
    1) profile が読めれば profile.paths.result_json を使う
    2) ダメならカレントに <profile>_result.json
    """
    try:
        prof = load_profile(profile_name, profile_dir)
        return str(prof["paths"]["result_json"])
    except Exception:
        return f"{profile_name}_result.json"


def _run_merge(args: argparse.Namespace) -> Dict[str, Any]:
    """役割: mergeサブコマンドの実行（result用の統計を返す）"""
    merge_yearly_csvs(
        yearly_dir=args.yearly_dir,
        out_csv=args.out_csv,
        encoding=args.encoding,
        delimiter=args.delimiter,
        strict_header=True,
    )
    return {"outputs": {"full_csv": args.out_csv}}


def _run_normalize(args: argparse.Namespace) -> Dict[str, Any]:
    """役割: normalizeサブコマンドの実行（unknown件数などを返す）"""
    master = load_master_data(args.master_dir)
    stats = normalize_full_csv(
        in_csv=args.in_csv,
        out_csv=args.out_csv,
        master=master,
        encoding=args.encoding,
        delimiter=args.delimiter,
        unknown_policy=args.unknown_policy,
    )
    return {
        "outputs": {"full_normalized_csv": args.out_csv},
        "rows": {"input_rows": stats["input_rows"]},
        "unknown_counts": stats["unknown_counts"],
    }


def _run_extract(args: argparse.Namespace) -> Dict[str, Any]:
    """役割: extractサブコマンドの実行（入出力行数を返す）"""
    prof = load_profile(args.profile, args.profile_dir)
    ex = prof["extract"]
    counts = extract_profile_csv(
        in_csv=args.in_csv,
        out_csv=args.out_csv,
        columns_allowlist=ex["columns_allowlist"],
        domain_filter=ex["domain_filter"],
        encoding=args.encoding,
        delimiter=args.delimiter,
    )
    return {
        "outputs": {"output_csv": args.out_csv},
        "rows": {"input_rows": counts["input_rows"], "output_rows": counts["output_rows"]},
    }


def _run_build(args: argparse.Namespace) -> Dict[str, Any]:
    """
    役割:
    - build（merge→normalize→extract）を profile から自動実行する

    手順:
    1) profile読込（paths/io/extract）
    2) full.csv が無い or force-merge なら merge
    3) normalize（full → full_normalized）
    4) extract（full_normalized → profile出力）
    """
    prof = load_profile(args.profile, args.profile_dir)
    paths = prof["paths"]
    io = prof.get("io", {"encoding": "utf-8", "delimiter": ","})
    encoding = io.get("encoding", "utf-8")
    delimiter = io.get("delimiter", ",")

    yearly_dir = str(paths["yearly_dir"])
    full_csv = str(paths["full_csv"])
    master_dir = str(paths["master_data_dir"])
    full_norm = str(paths["full_normalized_csv"])
    out_csv = str(paths["output_csv"])

    steps: Dict[str, Any] = {}

    # merge（必要時のみ）
    s = time.time()
    merge_yearly_csvs(yearly_dir, full_csv, encoding, delimiter, strict_header=True)
    steps["merge"] = {"ran": True, "ms": int((time.time() - s) * 1000)}

    # normalize
    s = time.time()
    master = load_master_data(master_dir)
    norm_stats = normalize_full_csv(full_csv, full_norm, master, encoding, delimiter, unknown_policy=prof.get("unknown_policy", "unknown"))
    steps["normalize"] = {"ran": True, "ms": int((time.time() - s) * 1000)}

    # extract
    s = time.time()
    ex = prof["extract"]
    counts = extract_profile_csv(full_norm, out_csv, ex["columns_allowlist"], ex["domain_filter"], encoding, delimiter)
    steps["extract"] = {"ran": True, "ms": int((time.time() - s) * 1000)}

    return {
        "steps": steps,
        "outputs": {"full_csv": full_csv, "full_normalized_csv": full_norm, "output_csv": out_csv},
        "rows": {"input_rows": counts["input_rows"], "output_rows": counts["output_rows"]},
        "unknown_counts": norm_stats["unknown_counts"],
    }


def main(argv: list[str] | None = None) -> int:
    """
    役割:
    - 実行エントリ。必ず result.json を出し exit code を返す

    手順:
    1) 引数解析
    2) コマンド実行
    3) success/error を result.json に書く
    """
    args = _parser().parse_args(argv)
    t0 = time.time()

    # result.json の出力先（build/ extract は profile から、他は out_csv 隣に出す）
    if args.command in ("build",):
        result_path = _safe_result_path(args.profile, args.profile_dir)
    elif args.command in ("extract",):
        # extract単体実行でも profile の result_json を優先
        result_path = _safe_result_path(args.profile, args.profile_dir)
    else:
        out_csv = getattr(args, "out_csv", None)
        if not out_csv:
            result_path = "result.json"
        else:
            result_path = os.path.join(os.path.dirname(out_csv) or ".", "result.json")

    result: Dict[str, Any] = {"status": "error", "command": args.command}

    try:
        if args.command == "merge":
            payload = _run_merge(args)
        elif args.command == "normalize":
            payload = _run_normalize(args)
        elif args.command == "extract":
            payload = _run_extract(args)
        elif args.command == "build":
            payload = _run_build(args)
        else:
            raise InputError(f"Unknown command: {args.command}")

        result.update(payload)
        result["status"] = "success"
        result["execution_time_ms"] = int((time.time() - t0) * 1000)
        write_result_json(result_path, result)
        return 0

    except EtlError as e:
        result["status"] = "error"
        result["error_code"] = e.error_code
        result["message"] = type(e).__name__
        result["details"] = str(e)
        result["execution_time_ms"] = int((time.time() - t0) * 1000)
        write_result_json(result_path, result)
        return e.error_code
    
    except PermissionError as e:
        result["status"] = "error"
        result["error_code"] = 2
        result["message"] = type(e).__name__
        result["details"] = f"File is locked. Close the file and retry. ({e})"
        result["execution_time_ms"] = int((time.time() - t0) * 1000)
        write_result_json(result_path, result)
        return 2

    except Exception as e:
        result["status"] = "error"
        result["error_code"] = 9
        result["message"] = type(e).__name__
        result["details"] = str(e)
        result["execution_time_ms"] = int((time.time() - t0) * 1000)
        write_result_json(result_path, result)
        return 9

if __name__ == "__main__":
    import sys
    raise SystemExit(main(sys.argv[1:]))