#!/usr/bin/env python3
"""
Точка входа «Смотрюн3000» (Qt / PySide6).

Собирает компоненты, связывает их сигналами и запускает цикл событий Qt.
Бизнес-логика (window_logic / hotkey_manager / auto_refresh) framework-независима;
здесь только сборка UI и запуск.
"""

import sys
import traceback

from PySide6.QtWidgets import QApplication, QMessageBox

import themes
from window_logic import WindowLogic
from hotkey_manager import HotkeyManager
from auto_refresh import AutoRefresher
from main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Widgun")
    # Панель может «жить» в трее со скрытым окном — не выходим автоматически
    app.setQuitOnLastWindowClosed(False)

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
