"""
Логика работы с окнами: обнаружение, фильтрация, активация, персистентность.

Framework-независимое ядро приложения. От tkinter отвязано полностью — общение
с UI идёт через сигналы Qt (windows_updated / status_message / error_occurred),
поэтому логику можно дёргать как из GUI-потока, так и из фонового автообновления.
"""

import json
import os
import hashlib
import shutil
import traceback
from pathlib import Path

import pygetwindow as gw
from PySide6.QtCore import QObject, Signal

from paths import (
    CONFIG_DIR,
    ICONS_DIR,
    ensure_config_dir,
    ensure_icons_dir,
    WINDOW_NAMES_FILE,
    WINDOW_ICONS_FILE,
    WINDOW_ORDER_FILE,
    HOTKEY_ASSIGNMENTS_FILE,
)


class WindowLogic(QObject):
    # Список window_data после сканирования (для перестроения UI)
    windows_updated = Signal(list)
    # Текст статуса + уровень ('ok' | 'warn' | 'error')
    status_message = Signal(str, str)
    # Сообщение об ошибке (для показа диалога)
    error_occurred = Signal(str)

    def __init__(self):
        super().__init__()
        self.hotkey_manager = None

        # Хранилища данных
        self.custom_names = {}
        self.window_icons = {}
        self.window_order = []
        self.hotkey_assignments = {}  # window_key -> цифра (0-9, где 0 = 10-й слот)

        # Настройки фильтрации
        self.target_text = 'Haven'
        self.separator = '–'
        self.show_only_after_separator = True

        # Кэш окон
        self.windows_cache = []

        self.load_data()
        # Материализуем файлы конфигов на первом запуске (создаст configs/*.json)
        self.save_data()

    def set_hotkey_manager(self, hotkey_manager):
        self.hotkey_manager = hotkey_manager

    # ========== ПЕРСИСТЕНТНОСТЬ ==========

    def load_data(self):
        """Загрузка сохранённых данных."""
        try:
            if WINDOW_NAMES_FILE.exists():
                with open(WINDOW_NAMES_FILE, 'r', encoding='utf-8') as f:
                    self.custom_names = json.load(f)

            if WINDOW_ICONS_FILE.exists():
                with open(WINDOW_ICONS_FILE, 'r', encoding='utf-8') as f:
                    self.window_icons = json.load(f)

            if WINDOW_ORDER_FILE.exists():
                with open(WINDOW_ORDER_FILE, 'r', encoding='utf-8') as f:
                    self.window_order = json.load(f)

            if HOTKEY_ASSIGNMENTS_FILE.exists():
                with open(HOTKEY_ASSIGNMENTS_FILE, 'r', encoding='utf-8') as f:
                    self.hotkey_assignments = json.load(f)

        except Exception as e:
            print(f"Ошибка загрузки данных: {e}")
            self.custom_names = {}
            self.window_icons = {}
            self.window_order = []
            self.hotkey_assignments = {}

    def save_data(self):
        """Сохранение данных."""
        try:
            ensure_config_dir()
            with open(WINDOW_NAMES_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.custom_names, f, ensure_ascii=False, indent=2)
            with open(WINDOW_ICONS_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.window_icons, f, ensure_ascii=False, indent=2)
            with open(WINDOW_ORDER_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.window_order, f)
            with open(HOTKEY_ASSIGNMENTS_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.hotkey_assignments, f)
        except Exception as e:
            print(f"Ошибка сохранения данных: {e}")

    # ========== ИКОНКИ ==========

    def resolve_icon_path(self, icon_path):
        """Абсолютный путь к иконке (в JSON хранится относительно configs)."""
        if not icon_path:
            return None
        p = Path(icon_path)
        if not p.is_absolute():
            p = CONFIG_DIR / p
        return p

    # ========== СКАНИРОВАНИЕ ОКОН ==========

    def format_window_title(self, title):
        """Форматирование заголовка окна (возвращает None, если окно не подходит)."""
        if not title:
            return None
        if self.target_text and self.target_text.lower() not in title.lower():
            return None

        if self.show_only_after_separator:
            if self.separator in title:
                parts = title.split(self.separator, 1)
                if len(parts) > 1 and parts[1].strip():
                    return parts[1].strip()
                return None
            return None

        return title

    def get_window_key(self, title):
        """Уникальный ключ окна по заголовку."""
        return hashlib.md5(title.encode()).hexdigest()[:16]

    def _auto_assign_hotkey(self, window_key):
        """Назначить свободную цифру окну, если есть место (до 10 привязок)."""
        if window_key in self.hotkey_assignments:
            return self.hotkey_assignments[window_key]
        if len(self.hotkey_assignments) >= 10:
            return None
        used = set(self.hotkey_assignments.values())
        for num in range(1, 11):
            display_num = num if num != 10 else 0
            if display_num not in used:
                self.hotkey_assignments[window_key] = display_num
                return display_num
        return None

    def _scan(self):
        """Просканировать окна и собрать список window_data. Мутирует привязки/кэш."""
        all_windows = gw.getAllWindows()

        found = []
        for window in all_windows:
            if not window.title or not window.title.strip():
                continue
            formatted_title = self.format_window_title(window.title)
            if formatted_title is None:
                continue

            window_key = self.get_window_key(window.title)
            hotkey_number = self._auto_assign_hotkey(window_key)

            found.append({
                'key': window_key,
                'title': window.title,
                'formatted_title': formatted_title,
                'custom_name': self.custom_names.get(window_key, ''),
                'icon_path': self.window_icons.get(window_key, ''),
                'window_object': window,
                'original_title': window.title,
                'hotkey_number': hotkey_number,
            })

        # Применяем сохранённый порядок: сначала окна из window_order, затем новые
        order_index = {key: i for i, key in enumerate(self.window_order)}
        found.sort(key=lambda w: order_index.get(w['key'], len(order_index) + 1))

        self.windows_cache = found
        return found

    def refresh_windows(self):
        """Полное сканирование + сохранение привязок + обновление UI."""
        try:
            found = self._scan()
            self.save_data()
            self.windows_updated.emit(found)
        except Exception as e:
            print(f"Ошибка в refresh_windows: {e}")
            traceback.print_exc()
            self.status_message.emit(f"Ошибка: {e}", 'error')

    def update_windows_cache(self):
        """Фоновое обновление (из потока автообновления). Обновляет кэш и UI."""
        try:
            found = self._scan()
            self.save_data()
            self.windows_updated.emit(found)
            return True
        except Exception as e:
            print(f"Ошибка обновления кэша окон: {e}")
            return False

    def get_visible_windows(self):
        return self.windows_cache

    # ========== ХОТКЕИ ==========

    def assign_hotkey(self, window_key, hotkey_number):
        """Назначить цифру окну (0-9, где 0 = 10-й слот)."""
        try:
            if hotkey_number < 0 or hotkey_number > 9:
                return False
            # Снимаем эту цифру с других окон
            for key, num in list(self.hotkey_assignments.items()):
                if num == hotkey_number and key != window_key:
                    del self.hotkey_assignments[key]
            self.hotkey_assignments[window_key] = hotkey_number
            self.save_data()
            self.refresh_windows()
            return True
        except Exception as e:
            print(f"Ошибка назначения хоткея: {e}")
            return False

    def remove_hotkey(self, window_key):
        """Снять привязку хоткея с окна."""
        try:
            if window_key in self.hotkey_assignments:
                del self.hotkey_assignments[window_key]
                self.save_data()
                self.refresh_windows()
            return True
        except Exception as e:
            print(f"Ошибка удаления хоткея: {e}")
            return False

    def get_window_by_hotkey(self, hotkey_number):
        """Окно (window_data) по назначенной цифре, либо None."""
        for window_key, assigned in self.hotkey_assignments.items():
            if assigned == hotkey_number:
                for w in self.windows_cache:
                    if w['key'] == window_key:
                        return w
        return None

    # ========== ИМЕНА / ИКОНКИ ==========

    def set_custom_name(self, window_key, custom_name):
        if custom_name.strip():
            self.custom_names[window_key] = custom_name.strip()
        elif window_key in self.custom_names:
            del self.custom_names[window_key]
        self.save_data()
        self.refresh_windows()

    def set_window_icon(self, window_key, icon_path):
        """Скопировать выбранный файл в папку иконок и привязать к окну."""
        try:
            ensure_icons_dir()
            ext = os.path.splitext(icon_path)[1]
            icon_filename = f"icon_{window_key}{ext}"
            dst = ICONS_DIR / icon_filename
            shutil.copy2(icon_path, dst)
            # Храним относительный путь для переносимости
            self.window_icons[window_key] = str(Path("icons") / icon_filename)
            self.save_data()
            self.refresh_windows()
        except Exception as e:
            print(f"Ошибка установки иконки: {e}")
            self.error_occurred.emit(f"Не удалось установить иконку:\n{e}")

    def remove_window_icon(self, window_key):
        try:
            if window_key in self.window_icons:
                abs_path = self.resolve_icon_path(self.window_icons[window_key])
                if abs_path and abs_path.exists():
                    try:
                        abs_path.unlink()
                    except OSError:
                        pass
                del self.window_icons[window_key]
                self.save_data()
                self.refresh_windows()
        except Exception as e:
            print(f"Ошибка удаления иконки: {e}")
            self.error_occurred.emit(f"Не удалось удалить иконку:\n{e}")

    # ========== ПОРЯДОК ОКОН ==========

    def apply_order(self, ordered_keys):
        """Сохранить новый порядок и переставить кэш окон под него."""
        self.window_order = list(ordered_keys)
        index = {k: i for i, k in enumerate(ordered_keys)}
        self.windows_cache.sort(key=lambda w: index.get(w['key'], len(index)))
        self.save_data()

    # ========== АКТИВАЦИЯ ОКНА ==========

    def activate_window_by_key(self, window_key):
        """
        Активация окна по ключу.

        Основной путь — win32 c AttachThreadInput: обходит защиту Windows от
        «кражи фокуса», поэтому окно выходит вперёд без мигания (никаких
        minimize/restore и alt+tab, которые дёргали весь экран).
        """
        window_data = next((w for w in self.windows_cache if w['key'] == window_key), None)
        if not window_data:
            print(f"Окно с ключом {window_key} не найдено в кэше")
            return False

        window = window_data['window_object']
        hwnd = getattr(window, '_hWnd', None)

        if hwnd and self._activate_hwnd(hwnd):
            return True

        # Тихий фолбэк через pygetwindow (без дёрганых методов)
        try:
            if getattr(window, 'isMinimized', False):
                window.restore()
            window.activate()
            return True
        except Exception as e:
            print(f"Не удалось активировать окно: {e}")
            return False

    def _activate_hwnd(self, hwnd):
        """Плавный вывод окна на передний план через WinAPI."""
        try:
            import ctypes
            user32 = ctypes.windll.user32
            kernel32 = ctypes.windll.kernel32
            SW_RESTORE = 9

            if user32.IsIconic(hwnd):
                user32.ShowWindow(hwnd, SW_RESTORE)

            fg = user32.GetForegroundWindow()
            cur_thread = kernel32.GetCurrentThreadId()
            fg_thread = user32.GetWindowThreadProcessId(fg, 0)
            target_thread = user32.GetWindowThreadProcessId(hwnd, 0)

            attached = []
            if fg_thread and fg_thread != cur_thread:
                if user32.AttachThreadInput(cur_thread, fg_thread, True):
                    attached.append(fg_thread)
            if target_thread and target_thread not in (cur_thread, fg_thread):
                if user32.AttachThreadInput(cur_thread, target_thread, True):
                    attached.append(target_thread)

            user32.BringWindowToTop(hwnd)
            user32.SetForegroundWindow(hwnd)
            user32.SetActiveWindow(hwnd)

            for t in attached:
                user32.AttachThreadInput(cur_thread, t, False)
            return True
        except Exception as e:
            print(f"win32 активация не удалась: {e}")
            traceback.print_exc()
            return False
