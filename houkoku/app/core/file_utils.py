"""File I/O utilities for SharePoint-synced folders.

Provides retry logic for write operations (file locks)
and file sync wait (SharePoint propagation delay).
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Optional

MAX_RETRIES = 5
RETRY_DELAY_SEC = 1.0
SYNC_WAIT_SEC = 0.5
SYNC_MAX_RETRIES = 10


def safe_write_with_retry(
    path: Path,
    content: str,
    encoding: str = "utf-8",
    max_retries: int = MAX_RETRIES,
    delay: float = RETRY_DELAY_SEC,
) -> None:
    """Write content to file with retry on lock errors.

    Args:
        path: Target file path.
        content: Text content to write.
        encoding: File encoding (default utf-8).
        max_retries: Maximum retry attempts.
        delay: Seconds between retries.

    Raises:
        OSError: If all retries are exhausted.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    last_error: Optional[OSError] = None

    for attempt in range(max_retries):
        try:
            path.write_text(content, encoding=encoding)
            return
        except OSError as e:
            last_error = e
            if attempt < max_retries - 1:
                time.sleep(delay)

    raise OSError(f"ファイル書き込みに失敗しました ({max_retries}回リトライ後): {path}") from last_error


def safe_write_bytes_with_retry(
    path: Path,
    data: bytes,
    max_retries: int = MAX_RETRIES,
    delay: float = RETRY_DELAY_SEC,
) -> None:
    """Write bytes to file with retry on lock errors."""
    path.parent.mkdir(parents=True, exist_ok=True)
    last_error: Optional[OSError] = None

    for attempt in range(max_retries):
        try:
            path.write_bytes(data)
            return
        except OSError as e:
            last_error = e
            if attempt < max_retries - 1:
                time.sleep(delay)

    raise OSError(f"ファイル書き込みに失敗しました ({max_retries}回リトライ後): {path}") from last_error


def wait_for_file_sync(
    path: Path,
    max_retries: int = SYNC_MAX_RETRIES,
    delay: float = SYNC_WAIT_SEC,
) -> bool:
    """Wait for a file to appear (SharePoint sync propagation).

    Args:
        path: File path to check.
        max_retries: Maximum poll attempts.
        delay: Seconds between checks.

    Returns:
        True if file appeared, False if timeout.
    """
    for _ in range(max_retries):
        if path.exists():
            return True
        time.sleep(delay)
    return False
