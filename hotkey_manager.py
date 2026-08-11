"""
Глобальные горячие клавиши (pynput).

Режимы: простые цифры 0-9 или Shift+цифры. Слушатель работает в отдельном
потоке даже когда окно приложения свёрнуто. О нажатии сообщаем в GUI-поток
через сигнал Qt hotkey_activated(int) — Qt сам ставит вызов в очередь главного
потока (queued connection), поэтому активация окна происходит безопасно.
"""

import json
import threading
import time

from pynput import keyboard
from PySide6.QtCore import QObject, Signal

from paths import HOTKEY_SETTINGS_FILE, ensure_config_dir


class HotkeyManager(QObject):
    # Нажата цифра-хоткей (0-9). Обрабатывается в GUI-потоке.
    hotkey_activated = Signal(int)
    # Нажат хоткей сворачивания/разворачивания в трей.
    toggle_visibility_requested = Signal()
    # Изменение размера иконок: +1 больше / -1 меньше.
    icon_size_step_requested = Signal(int)

    def __init__(self, window_logic):
        super().__init__()
        self.window_logic = window_logic

        self.hotkey_listener = None
        self.listener_thread = None
        self.stop_event = threading.Event()

        self.default_settings = {
            'enabled': True,
            'max_windows': 10,
            'feedback_enabled': True,
            'minimize_on_hotkey': False,
            'switch_delay': 0.5,
            'use_shift': False,
            # ВАЖНО: на Windows pynput НЕ ловит Ctrl+<буква> (буква под Ctrl
            # приходит как управляющий символ). Надёжны только спец-клавиши
            # (функциональные, стрелки и т.п.) — поэтому дефолт с <f9>.
            'tray_hotkey': '<ctrl>+<f9>',
        }
        self.settings = self.default_settings.copy()
        self.load_settings()
        self.enabled = self.settings.get('enabled', True)
        # Материализуем hotkey_settings.json на первом запуске
        if not HOTKEY_SETTINGS_FILE.exists():
            self.save_settings()

    # ========== ЖИЗНЕННЫЙ ЦИКЛ СЛУШАТЕЛЯ ==========

    def start(self):
        """Запустить слушатель, если включён."""
        if self.enabled:
            self._start_listener()

    def _start_listener(self):
        if self.enabled and (self.listener_thread is None or not self.listener_thread.is_alive()):
            self.stop_event.clear()
            self.listener_thread = threading.Thread(
                target=self._hotkey_listener_worker, daemon=True
            )
            self.listener_thread.start()

    def _stop_listener(self):
        self.stop_event.set()
        if self.hotkey_listener:
            try:
                self.hotkey_listener.stop()
            except Exception:
                pass
            self.hotkey_listener = None
        if self.listener_thread and self.listener_thread.is_alive():
            self.listener_thread.join(timeout=1.0)

    def stop(self):
        """Полная остановка (при выходе из приложения)."""
        self._stop_listener()
        self.enabled = False

    def restart(self):
        """Перезапуск слушателя с текущими настройками."""
        self._stop_listener()
        time.sleep(0.2)
        if self.enabled:
            self._start_listener()

    # ========== РАБОЧИЙ ПОТОК ==========

    def _hotkey_listener_worker(self):
        use_shift = self.settings.get('use_shift', False)

        # digit: 1..9 -> цифра, 0 -> десятый слот
        hotkeys = {}
        for digit in list(range(1, 10)) + [0]:
            combo = f'<shift>+{digit}' if use_shift else str(digit)
            hotkeys[combo] = (lambda d=digit: self._on_hotkey(d))

        # Хоткей сворачивания в трей — добавляем только если он валиден,
        # чтобы кривая комбинация не уронила весь набор хоткеев.
        tray_combo = self.settings.get('tray_hotkey', '').strip()
        if tray_combo and self.is_valid_hotkey(tray_combo):
            hotkeys[tray_combo] = (lambda: self._on_toggle())

        # Размер иконок — глобально, через спец-клавиши (стрелки надёжны с Ctrl)
        hotkeys['<ctrl>+<up>'] = (lambda: self.icon_size_step_requested.emit(1))
        hotkeys['<ctrl>+<down>'] = (lambda: self.icon_size_step_requested.emit(-1))

        try:
            self.hotkey_listener = keyboard.GlobalHotKeys(hotkeys)
            with self.hotkey_listener as h:
                h.join()
        except Exception as e:
            print(f"Ошибка GlobalHotKeys: {e}")

    def _on_hotkey(self, digit):
        """Вызывается из потока pynput — просто эмитим сигнал в GUI-поток."""
        self.hotkey_activated.emit(digit)

    def _on_toggle(self):
        """Хоткей трея — эмитим сигнал переключения видимости в GUI-поток."""
        self.toggle_visibility_requested.emit()

    @staticmethod
    def is_valid_hotkey(combo):
        """Проверить, что строка-комбо парсится pynput (например '<ctrl>+<shift>+s')."""
        try:
            keyboard.HotKey.parse(combo)
            return True
        except Exception:
            return False

    # ========== НАСТРОЙКИ ==========

    def load_settings(self):
        try:
            if HOTKEY_SETTINGS_FILE.exists():
                with open(HOTKEY_SETTINGS_FILE, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                for key, default_value in self.default_settings.items():
                    self.settings[key] = loaded.get(key, default_value)
            else:
                self.settings = self.default_settings.copy()
        except Exception as e:
            print(f"Ошибка загрузки настроек: {e}")
            self.settings = self.default_settings.copy()

    def save_settings(self):
        try:
            ensure_config_dir()
            with open(HOTKEY_SETTINGS_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=2)
        except Exception as e:
            print(f"Ошибка сохранения настроек: {e}")

    def apply_settings(self, new_settings):
        """Применить настройки из диалога, сохранить и перезапустить слушатель."""
        self.settings.update(new_settings)
        self.enabled = self.settings.get('enabled', True)
        self.save_settings()
        if self.enabled:
            self.restart()
        else:
            self._stop_listener()
