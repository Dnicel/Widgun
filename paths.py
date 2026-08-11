"""
Пути к данным приложения.

Все конфиги и иконки хранятся в подпапке `configs/` рядом с точкой запуска:
- собрано PyInstaller (.exe) → папка, где лежит .exe (а НЕ временная _MEIPASS,
  из-за которой данные не переживали перезапуск);
- обычный запуск скрипта → папка пакета.

Папка `configs/` создаётся автоматически при старте, если её нет.
"""

import sys
from pathlib import Path

if getattr(sys, 'frozen', False):
    # PyInstaller: рядом с исполняемым файлом (папка запуска)
    APP_DIR = Path(sys.executable).resolve().parent
else:
    APP_DIR = Path(__file__).resolve().parent

CONFIG_DIR = APP_DIR / "configs"
ICONS_DIR = CONFIG_DIR / "icons"

# Файлы данных (имена и форматы сохранены для совместимости)
WINDOW_NAMES_FILE = CONFIG_DIR / "window_names.json"
WINDOW_ICONS_FILE = CONFIG_DIR / "window_icons.json"
WINDOW_ORDER_FILE = CONFIG_DIR / "window_order.json"
HOTKEY_ASSIGNMENTS_FILE = CONFIG_DIR / "hotkey_assignments.json"
HOTKEY_SETTINGS_FILE = CONFIG_DIR / "hotkey_settings.json"
SETTINGS_FILE = CONFIG_DIR / "settings.json"


def ensure_config_dir() -> Path:
    """Создать папку configs, если её нет."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    return CONFIG_DIR


def ensure_icons_dir() -> Path:
    """Создать папку иконок (configs/icons), если её нет."""
    ICONS_DIR.mkdir(parents=True, exist_ok=True)
    return ICONS_DIR


# Гарантируем наличие папки configs сразу — чтобы сохранение работало
# уже на самом первом запуске.
ensure_config_dir()
