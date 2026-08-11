"""
Глобальные горячие клавиши (pynput), матчинг по vk-кодам.

Простые цифры 0-9 или Shift+цифры переключают окна; Ctrl+стрелки меняют размер;
настраиваемый хоткей сворачивает в трей. Сравнение идёт по «физическим» клавишам
(vk), а не по символам — поэтому Shift+цифра работает независимо от раскладки
(в отличие от подхода через GlobalHotKeys, где «1» под Shift приходит как «!»).

О срабатывании сообщаем в GUI-поток сигналами Qt (queued connection).
"""

import json

from pynput import keyboard
from PySide6.QtCore import QObject, Signal

from paths import HOTKEY_SETTINGS_FILE, ensure_config_dir


# vk-коды цифр (верхний ряд и numpad)
_DIGIT_VK = {0x31: 1, 0x32: 2, 0x33: 3, 0x34: 4, 0x35: 5,
             0x36: 6, 0x37: 7, 0x38: 8, 0x39: 9, 0x30: 0}
_NUMPAD_VK = {0x61: 1, 0x62: 2, 0x63: 3, 0x64: 4, 0x65: 5,
              0x66: 6, 0x67: 7, 0x68: 8, 0x69: 9, 0x60: 0}


def _mod_set(names):
    s = set()
    for n in names:
        k = getattr(keyboard.Key, n, None)
        if k is not None:
            s.add(k)
    return s


_CTRL = _mod_set(['ctrl', 'ctrl_l', 'ctrl_r'])
_SHIFT = _mod_set(['shift', 'shift_l', 'shift_r'])
_ALT = _mod_set(['alt', 'alt_l', 'alt_r', 'alt_gr'])


def _key_vk(key):
    """vk клавиши (для Key берём из value, для KeyCode — напрямую)."""
    if isinstance(key, keyboard.Key):
        return getattr(key.value, 'vk', None)
    return getattr(key, 'vk', None)


def _parse_combo(combo):
    """'<ctrl>+<f9>' -> (frozenset({'ctrl'}), vk) либо None (напр. для букв)."""
    try:
        keys = keyboard.HotKey.parse(combo)
    except Exception:
        return None
    mods = set()
    main_vk = None
    for k in keys:
        if k in _CTRL:
            mods.add('ctrl')
        elif k in _SHIFT:
            mods.add('shift')
        elif k in _ALT:
            mods.add('alt')
        else:
            main_vk = _key_vk(k)
    if main_vk is None:
        return None
    return (frozenset(mods), main_vk)


class HotkeyManager(QObject):
    hotkey_activated = Signal(int)            # нажата цифра-хоткей (0-9)
    toggle_visibility_requested = Signal()    # хоткей трея
    icon_size_step_requested = Signal(int)    # +1 больше / -1 меньше

    def __init__(self, window_logic):
        super().__init__()
        self.window_logic = window_logic

        self.hotkey_listener = None
        self._mods = set()
        self._combos = []   # список (frozenset(mods), vk, action)

        self.default_settings = {
            'enabled': True,
            'feedback_enabled': True,
            'use_shift': False,
            # С Ctrl надёжны только спец-клавиши (не буквы) — дефолт с <f9>.
            'tray_hotkey': '<ctrl>+<f9>',
        }
        self.settings = self.default_settings.copy()
        self.load_settings()
        self.enabled = self.settings.get('enabled', True)
        if not HOTKEY_SETTINGS_FILE.exists():
            self.save_settings()

    # ========== ЖИЗНЕННЫЙ ЦИКЛ СЛУШАТЕЛЯ ==========

    def start(self):
        if self.enabled:
            self._start_listener()

    def _start_listener(self):
        if self.hotkey_listener is not None:
            return
        self._rebuild_combos()
        self._mods = set()
        self.hotkey_listener = keyboard.Listener(
            on_press=self._on_press, on_release=self._on_release)
        self.hotkey_listener.start()

    def _stop_listener(self):
        if self.hotkey_listener:
            try:
                self.hotkey_listener.stop()
            except Exception:
                pass
            self.hotkey_listener = None

    def stop(self):
        self._stop_listener()
        self.enabled = False

    def restart(self):
        self._stop_listener()
        if self.enabled:
            self._start_listener()

    # ========== МАТЧИНГ ==========

    def _rebuild_combos(self):
        """Пересобрать назначаемые комбо (трей, размер иконок)."""
        self._combos = []
        tray = _parse_combo(self.settings.get('tray_hotkey', '').strip())
        if tray:
            self._combos.append((tray[0], tray[1], self._on_toggle))
        up = _parse_combo('<ctrl>+<up>')
        down = _parse_combo('<ctrl>+<down>')
        self._combos.append((up[0], up[1], lambda: self.icon_size_step_requested.emit(1)))
        self._combos.append((down[0], down[1], lambda: self.icon_size_step_requested.emit(-1)))

    def _on_press(self, key):
        try:
            if key in _CTRL:
                self._mods.add('ctrl'); return
            if key in _SHIFT:
                self._mods.add('shift'); return
            if key in _ALT:
                self._mods.add('alt'); return

            vk = _key_vk(key)
            if vk is None:
                return
            mods = frozenset(self._mods)

            # 1) назначаемые комбо (трей / размер иконок)
            for cmods, cvk, action in self._combos:
                if vk == cvk and mods == cmods:
                    action()
                    return

            # 2) цифры-переключатели
            digit = _DIGIT_VK.get(vk)
            if digit is None:
                digit = _NUMPAD_VK.get(vk)
            if digit is not None:
                if self.settings.get('use_shift', False):
                    if mods == frozenset({'shift'}):
                        self.hotkey_activated.emit(digit)
                else:
                    if not mods:
                        self.hotkey_activated.emit(digit)
        except Exception as e:
            print(f"Ошибка обработки хоткея: {e}")

    def _on_release(self, key):
        if key in _CTRL:
            self._mods.discard('ctrl')
        elif key in _SHIFT:
            self._mods.discard('shift')
        elif key in _ALT:
            self._mods.discard('alt')

    def _on_toggle(self):
        self.toggle_visibility_requested.emit()

    @staticmethod
    def is_valid_hotkey(combo):
        """Комбо валидно, если парсится и заканчивается спец-клавишей (есть vk)."""
        return _parse_combo(combo) is not None

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
