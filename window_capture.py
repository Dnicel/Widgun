"""
Живой захват окон через Windows.Graphics.Capture (пакет windows-capture).

По одной сессии на HWND; кадры приходят в фоновом потоке, храним последний
(уменьшенный) кадр как BGRA-байты, потокобезопасно. Захватывает реальное
содержимое окна, даже если оно перекрыто другими.
"""

import threading

try:
    from windows_capture import WindowsCapture
    AVAILABLE = True
    _IMPORT_ERROR = None
except Exception as e:  # пакет не установлен / не Windows / нет WGC
    WindowsCapture = None
    AVAILABLE = False
    _IMPORT_ERROR = e

# Троттлинг захвата (мс) и предел стороны кадра (px) — ради CPU/памяти
CAPTURE_INTERVAL_MS = 100
MAX_SIDE = 384


class _Session:
    __slots__ = ('control', 'frame', 'lock')

    def __init__(self):
        self.control = None
        self.frame = None      # (bytes_bgra, width, height) или None
        self.lock = threading.Lock()


class WindowCaptureManager:
    """Управляет набором WGC-сессий по HWND."""

    def __init__(self):
        self._sessions = {}    # hwnd:int -> _Session
        self._guard = threading.Lock()

    def available(self):
        return AVAILABLE

    def import_error(self):
        return _IMPORT_ERROR

    def set_targets(self, hwnds):
        """Синхронизировать активные сессии с нужным набором HWND."""
        wanted = {int(h) for h in hwnds if h}
        with self._guard:
            for hwnd in list(self._sessions):
                if hwnd not in wanted:
                    self._stop(hwnd)
            for hwnd in wanted:
                if hwnd not in self._sessions:
                    self._start(hwnd)

    def _start(self, hwnd):
        if not AVAILABLE:
            return
        sess = _Session()
        try:
            cap = WindowsCapture(
                cursor_capture=False,
                draw_border=False,
                minimum_update_interval=CAPTURE_INTERVAL_MS,
                window_hwnd=hwnd,
            )

            @cap.event
            def on_frame_arrived(frame, capture_control):
                try:
                    buf = frame.frame_buffer      # (h, w, 4) BGRA
                    h, w = buf.shape[0], buf.shape[1]
                    step = max(1, max(w, h) // MAX_SIDE)
                    if step > 1:
                        buf = buf[::step, ::step]
                    buf = buf[:, :, :4].copy()    # непрерывный BGRA
                    with sess.lock:
                        sess.frame = (buf.tobytes(), buf.shape[1], buf.shape[0])
                except Exception:
                    pass

            @cap.event
            def on_closed():
                pass

            sess.control = cap.start_free_threaded()
            self._sessions[hwnd] = sess
        except Exception as e:
            print(f"WGC: не удалось запустить захват hwnd={hwnd}: {e}")

    def _stop(self, hwnd):
        sess = self._sessions.pop(hwnd, None)
        if sess and sess.control:
            try:
                sess.control.stop()
            except Exception:
                pass

    def latest(self, hwnd):
        sess = self._sessions.get(int(hwnd))
        if not sess:
            return None
        with sess.lock:
            return sess.frame

    def stop_all(self):
        with self._guard:
            for hwnd in list(self._sessions):
                self._stop(hwnd)
