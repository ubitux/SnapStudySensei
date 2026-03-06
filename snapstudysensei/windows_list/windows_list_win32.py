import ctypes
from ctypes import wintypes

_USER32 = ctypes.windll.user32


class WindowsList:
    def __call__(self) -> dict[int, tuple[str, bool]]:
        self.windows = {}
        WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        cb_worker = WNDENUMPROC(self._enum_windows_cb)
        _USER32.EnumWindows(cb_worker, None)
        return self.windows

    def _enum_windows_cb(self, hwnd: wintypes.HWND, _: wintypes.LPARAM):
        """Callback for EnumWindows.

        See https://learn.microsoft.com/en-us/previous-versions/windows/desktop/legacy/ms633498(v=vs.85)
        """
        length = _USER32.GetWindowTextLengthW(hwnd) + 1
        buffer = ctypes.create_unicode_buffer(length)
        _USER32.GetWindowTextW(hwnd, buffer, length)
        if _USER32.IsWindowVisible(hwnd) and len(buffer.value) > 0:
            self.windows[hwnd] = (buffer.value, True)
        return True
