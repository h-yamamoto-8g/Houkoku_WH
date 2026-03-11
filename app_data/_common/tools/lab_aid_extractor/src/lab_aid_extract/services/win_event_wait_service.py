import ctypes
import ctypes.wintypes as wt
import time

class LoginWindowCloseWaiter:
    """
    役割:
    - Windowsのイベントフック（WinEventHook）で「指定タイトルのウィンドウが閉じた瞬間」を検知する

    手順:
    1) Excelプロセス（pid）に紐づくウィンドウイベントをフック
    2) 対象タイトル（部分一致）のウィンドウが DESTROY されたらフラグを立てる
    3) MessagePumpでイベントを受け取り、フラグが立ったら復帰
    """

    EVENT_OBJECT_DESTROY = 0x8001
    WINEVENT_OUTOFCONTEXT = 0x0000

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    ole32 = ctypes.WinDLL("ole32", use_last_error=True)

    WinEventProcType = ctypes.WINFUNCTYPE(
        None,
        wt.HANDLE, wt.DWORD, wt.HWND, wt.LONG, wt.LONG, wt.DWORD, wt.DWORD
    )

    def __init__(self):
        self._closed = False
        self._hook = None
        self._target_pid = None
        self._title_key = None
        self._proc = self.WinEventProcType(self._callback)

    def wait_closed(self, pid: int, title_key: str, timeout_sec: int = 0) -> None:
        """
        役割:
        - pid配下で title_key を含むウィンドウが閉じるまで待つ（イベント駆動）

        timeout_sec:
        - 0なら無期限
        """
        self._closed = False
        self._target_pid = int(pid)
        self._title_key = (title_key or "").strip()

        # COMメッセージ処理が必要なためCoInitializeしておく
        self.ole32.CoInitialize(None)

        self._hook = self.user32.SetWinEventHook(
            self.EVENT_OBJECT_DESTROY,
            self.EVENT_OBJECT_DESTROY,
            0,
            self._proc,
            0, 0,
            self.WINEVENT_OUTOFCONTEXT
        )
        if not self._hook:
            raise RuntimeError("SetWinEventHookに失敗しました")

        start = time.time()
        try:
            msg = wt.MSG()
            while True:
                if self._closed:
                    return
                if timeout_sec > 0 and (time.time() - start) > timeout_sec:
                    raise TimeoutError("ログインウィンドウ待機がタイムアウトしました")

                # メッセージを1件処理（無ければ少し待つ）
                has = self.user32.PeekMessageW(ctypes.byref(msg), 0, 0, 0, 1)
                if has:
                    self.user32.TranslateMessage(ctypes.byref(msg))
                    self.user32.DispatchMessageW(ctypes.byref(msg))
                else:
                    time.sleep(0.05)
        finally:
            if self._hook:
                self.user32.UnhookWinEvent(self._hook)
                self._hook = None
            self.ole32.CoUninitialize()

    def _callback(self, hWinEventHook, event, hwnd, idObject, idChild, dwEventThread, dwmsEventTime):
        # 役割:
        # - DESTROYイベントが来た時に、対象pid+タイトル一致なら closed=True にする
        try:
            pid = wt.DWORD()
            self.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            if int(pid.value) != self._target_pid:
                return

            # タイトル取得
            length = self.user32.GetWindowTextLengthW(hwnd)
            if length <= 0:
                return
            buf = ctypes.create_unicode_buffer(length + 1)
            self.user32.GetWindowTextW(hwnd, buf, length + 1)
            title = (buf.value or "").strip()

            # 部分一致（"ログイン" 等）
            if self._title_key and (self._title_key in title):
                self._closed = True
        except Exception:
            return
