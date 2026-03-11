from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from lab_aid_extract.core.models import ExtractRequest, ExtractResult
from lab_aid_extract.core.errors import PathResolveError, ExcelLaunchError, ExportFailedError
from lab_aid_extract.services.path_service import PathService
from lab_aid_extract.services.result_service import ResultWriter
from lab_aid_extract.services.excel_service import ExcelService
from lab_aid_extract.services.extractor_service import LabAidExtractorService

"""
役割:
- CLI入口。パス解決、サービス組み立て、result.json 出力、exit code 統一

手順:
1) 引数parse
2) tool_dir決定
3) xlsm/out_dir/result.json を解決
4) ExtractRequest を作り service 実行
5) result.json を出して exit code を返す
"""


def main() -> int:
    parser = argparse.ArgumentParser()

    parser.add_argument("--xlsm-path", default="lab_aid_extractor.xlsm")
    parser.add_argument("--domain-code", required=True)
    parser.add_argument("--year", type=int, default=date.today().year)

    parser.add_argument("--out-dir", default=None)
    parser.add_argument("--result-json", default="result.json")

    parser.add_argument("--visible", action="store_true", default=True)
    parser.add_argument("--keep-open", action="store_true")

    # 手動ログイン促進の文言（必要なら変更できる）
    # parser.add_argument("--prompt-title", default="Lab-Aid Extract")
    # parser.add_argument("--prompt-message", default="Excel上でログインを完了したら「OK」を押してください。")

    args = parser.parse_args()

    path_service = PathService()
    tool_dir = path_service.get_tool_dir()

    result_json_path = path_service.resolve_result_json_path(tool_dir, args.result_json)
    writer = ResultWriter(result_json_path)

    try:
        xlsm_path = path_service.resolve_xlsm_path(tool_dir, args.xlsm_path)
        out_dir = path_service.resolve_out_dir(tool_dir, args.out_dir)

        req = ExtractRequest(
            xlsm_path=xlsm_path,
            domain_code=args.domain_code,
            year=args.year,
            out_dir=out_dir,
            visible=bool(args.visible),
            keep_open=bool(args.keep_open),
            # prompt_title=str(args.prompt_title),
            # prompt_message=str(args.prompt_message),
            result_json_path=result_json_path,
        )

        excel = ExcelService(visible=req.visible)
        extractor = LabAidExtractorService(excel=excel)

        csv_path, debug = extractor.run(req)

        writer.write(
            ExtractResult(
                ok=True,
                message="success",
                csv_path=str(csv_path),
                details={"debug": debug},
            )
        )
        return 0

    except PathResolveError as e:
        writer.write(ExtractResult(ok=False, message=str(e), details={"kind": "path_resolve"}))
        return 12
    except ExcelLaunchError as e:
        writer.write(ExtractResult(ok=False, message=str(e), details={"kind": "excel"}))
        return 10
    except ExportFailedError as e:
        writer.write(ExtractResult(ok=False, message=str(e), details={"kind": "export_failed"}))
        return 30
    except Exception as e:
        writer.write(ExtractResult(ok=False, message=f"unexpected_error: {e}", details={"kind": "unexpected"}))
        return 99


if __name__ == "__main__":
    raise SystemExit(main())
