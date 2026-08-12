#!/usr/bin/env python3
"""
Точка входа «Смотрюн3000» (Qt / PySide6).

Собирает компоненты, связывает их сигналами и запускает цикл событий Qt.
Бизнес-логика (window_logic / hotkey_manager / auto_refresh) framework-независима;
здесь только сборка UI и запуск.
"""

import json
import sys
import traceback

from PySide6.QtCore import QSharedMemory
from PySide6.QtWidgets import QApplication, QMessageBox

import themes
import i18n
from i18n import t
from paths import SETTINGS_FILE
from window_logic import WindowLogic
from hotkey_manager import HotkeyManager
from auto_refresh import AutoRefresher
from main_window import MainWindow

# Держим ссылку на весь срок жизни процесса (иначе сегмент освободится)
_single_instance = None


def _init_language():
    """Установить язык из settings.json ещё до создания окна."""
    try:
        if SETTINGS_FILE.exists():
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                i18n.set_language(json.load(f).get('language', i18n.DEFAULT_LANG))
    except Exception:
        pass


def _acquire_single_instance():
    """True, если это единственный экземпляр. Иначе False (уже запущен)."""
    global _single_instance
    _single_instance = QSharedMemory("Widgun_single_instance_v1")
    # На случай аварийного завершения — присоединяемся и чистим осиротевший сегмент
    if _single_instance.attach():
        _single_instance.detach()
    return _single_instance.create(1)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Widgun")
    # Панель может «жить» в трее со скрытым окном — не выходим автоматически
    app.setQuitOnLastWindowClosed(False)
    _init_language()

    # Один экземпляр: второй запуск не должен вешать второй хук клавиатуры
    if not _acquire_single_instance():
        QMessageBox.information(None, "Widgun", t('app.already_running'))
        sys.exit(0)

    try:
        # Логика
        window_logic = WindowLogic()
        hotkey_manager = HotkeyManager(window_logic)
        window_logic.set_hotkey_manager(hotkey_manager)

        # UI
        window = MainWindow(window_logic, hotkey_manager)

        # Тема (из сохранённых настроек окна)
        themes.apply_theme(app, window.get_theme())

        # Автообновление списка окон в фоне
        auto_refresher = AutoRefresher(window_logic, interval=3)
        window.set_auto_refresher(auto_refresher)

        # Старт
        window.show()
        hotkey_manager.start()
        auto_refresher.start()
        window_logic.refresh_windows()

        sys.exit(app.exec())

    except Exception as e:
        print(f"КРИТИЧЕСКАЯ ОШИБКА: {e}")
        traceback.print_exc()
        QMessageBox.critical(None, "Ошибка запуска",
                             f"Не удалось запустить приложение:\n{e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
