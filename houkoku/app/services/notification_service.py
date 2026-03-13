"""Notification JSON creation for Power Automate triggers.

Creates timestamped notification files in each department's
notifications/ folder to trigger email flows.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import app.config as _cfg
from app.core import file_utils
from app.core.config_store import Department, ReportDefinition


def create_notification(
    report: ReportDefinition,
    job_numbers: list[str],
    dept: Department,
    message: str,
    sent_by: str = "",
    report_link: str = "",
) -> dict:
    """Build a notification JSON payload.

    Args:
        report: Report definition.
        job_numbers: Selected JOB numbers.
        dept: Target department.
        message: User-entered notification message.
        sent_by: Sender name.
        report_link: Link to Excel Online template.

    Returns:
        Notification dict matching design spec 2.4.
    """
    return {
        "report_id": report.report_id,
        "report_name": report.report_name,
        "job_numbers": job_numbers,
        "sent_at": datetime.now().isoformat(timespec="seconds"),
        "sent_by": sent_by,
        "dept_id": dept.dept_id,
        "dept_name": dept.dept_name,
        "message": message,
        "report_link": report_link,
    }


def write_notification(
    dept: Department,
    notification: dict,
) -> Path:
    """Write notification JSON to department's notifications/ folder.

    Uses timestamped filename: notification_{YYYYMMDD_HHMMSS}.json

    Args:
        dept: Target department.
        notification: Notification payload dict.

    Returns:
        Path to written notification file.

    Raises:
        FileNotFoundError: If REPORTS_PATH is not configured.
    """
    reports_dir = _cfg.REPORTS_PATH
    if reports_dir is None:
        raise FileNotFoundError("出力先フォルダが設定されていません。")

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    notif_dir = reports_dir / dept.folder_name / "notifications"
    notif_dir.mkdir(parents=True, exist_ok=True)

    path = notif_dir / f"notification_{ts}.json"
    content = json.dumps(notification, ensure_ascii=False, indent=2)
    file_utils.safe_write_with_retry(path, content)

    return path


def send_all(
    report: ReportDefinition,
    job_numbers: list[str],
    departments: list[Department],
    message: str,
    sent_by: str = "",
) -> list[Path]:
    """Send notifications to all specified departments.

    Args:
        report: Report definition.
        job_numbers: Selected JOB numbers.
        departments: List of departments to notify.
        message: Notification message text.
        sent_by: Sender name.

    Returns:
        List of paths to written notification files.
    """
    paths: list[Path] = []

    for dept in departments:
        notif = create_notification(
            report=report,
            job_numbers=job_numbers,
            dept=dept,
            message=message,
            sent_by=sent_by,
        )
        path = write_notification(dept, notif)
        paths.append(path)

    return paths
