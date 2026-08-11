"""
Фоновое автообновление списка окон.

Работает в отдельном QThread: периодически дёргает window_logic.update_windows_cache(),
который сам эмитит сигнал windows_updated в GUI-поток. Здесь никаких обращений к
виджетам — только вызов логики.
"""

from PySide6.QtCore import QThread


class AutoRefresher(QThread):
    def __init__(self, window_logic, interval=3, parent=None):
        super().__init__(parent)
        self.window_logic = window_logic
        self.interval = interval  # секунды
        self._running = True

    def run(self):
        while self._running:
            try:
                self.window_logic.update_windows_cache()
            except Exception as e:
                print(f"Ошибка автообновления: {e}")
            # Прерываемое ожидание: спим маленькими шагами, чтобы быстро останавливаться
            for _ in range(int(self.interval * 10)):
                if not self._running:
                    break
                self.msleep(100)

    def stop(self):
        self._running = False
        self.wait(2000)
