from __future__ import annotations

import sys
from pathlib import Path
from lab_aid_extract.core.errors import PathResolveError

"""
役割:
- SharePoint配下で絶対パスが変動する前提のため、
  exe位置（またはソース位置）を基準に相対パス解決・app_data探索を行う

手順:
1) tool_dir（実行基準ディレクトリ）を決める
2) xlsm_path を tool_dir 基準で解決
3) app_data を親方向に探索し、規定 out_dir を作る
"""


class PathService:
    def get_tool_dir(self) -> Path:
        """
        役割:
        - 実行基準ディレクトリ（tool_dir）を返す

        手順:
        - 凍結（exe）: exeがあるディレクトリを tool_dir とする
        - 通常（python実行）: リポジトリ直下相当を tool_dir とする
        """
        if getattr(sys, "frozen", False):
            return Path(sys.executable).resolve().parent
        # src/lab_aid_extract/services/path_service.py の 4階層上 = プロジェクトルート想定
        return Path(__file__).resolve().parents[3]

    def resolve_xlsm_path(self, tool_dir: Path, xlsm_arg: str) -> Path:
        """
        役割:
        - --xlsm-path を tool_dir 基準で解決する（相対パス前提）

        手順:
        - 相対なら tool_dir / xlsm_arg
        - 絶対ならそのまま
        - 存在しなければ例外
        """
        p = Path(xlsm_arg)
        resolved = p if p.is_absolute() else (tool_dir / p)
        if not resolved.exists():
            raise PathResolveError(f"xlsm が見つかりません: {resolved}")
        return resolved

    def find_app_data_dir(self, tool_dir: Path) -> Path:
        """
        役割:
        - tool_dir から親方向へ app_data を探索する

        手順:
        - tool_dir → parents を順に見て app_data があれば採用
        """
        for base in [tool_dir, *tool_dir.parents]:
            c = base / "app_data"
            if c.exists() and c.is_dir():
                return c
        raise PathResolveError("app_data ディレクトリが見つかりません（配置が想定と異なります）")

    def default_out_dir(self, tool_dir: Path) -> Path:
        """
        役割:
        - out_dir省略時の出力先を返す
          app_data/_common/data/lab_aid/raw

        手順:
        - app_data を探索し、規定パスを組み立てる
        """
        app_data_dir = self.find_app_data_dir(tool_dir)
        return app_data_dir / "_common" / "data" / "lab_aid" / "raw"

    def resolve_out_dir(self, tool_dir: Path, out_dir_arg: str | None) -> Path:
        """
        役割:
        - --out-dir を解決する（省略時は規定）

        手順:
        - 指定あり: 相対なら tool_dir / 指定、絶対ならそのまま
        - 指定なし: default_out_dir
        """
        if out_dir_arg:
            p = Path(out_dir_arg)
            return p if p.is_absolute() else (tool_dir / p)
        return self.default_out_dir(tool_dir)

    def resolve_result_json_path(self, tool_dir: Path, result_json_arg: str) -> Path:
        """
        役割:
        - result.json の出力先を tool_dir 基準で解決する（混乱防止）

        手順:
        - 相対なら tool_dir / result_json_arg
        - 絶対ならそのまま
        """
        p = Path(result_json_arg)
        return p if p.is_absolute() else (tool_dir / p)
