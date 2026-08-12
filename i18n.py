"""
Простая локализация: словарь строк по языкам + функция t(key).

Язык переключается set_language(); строки берутся через t() в момент отрисовки,
поэтому при смене языка достаточно пересобрать/переоткрыть виджеты.
"""

LANGUAGES = {'ru': 'Русский', 'en': 'English'}
DEFAULT_LANG = 'ru'

_current = DEFAULT_LANG

_STR = {
    'ru': {
        # общее
        'common.save': 'Сохранить',
        'common.cancel': 'Отмена',
        'common.close': 'Закрыть',
        'error.title': 'Ошибка',

        # трей / шапка
        'tray.show_hide': 'Показать / Скрыть',
        'tray.settings': 'Настройки',
        'tray.quit': 'Выход',
        'tray.balloon': 'Свёрнуто в трей. Клик по иконке или хоткей — вернуть.',
        'titlebar.min_tooltip': 'Свернуть в трей',

        # мини-режим
        'mini.switch': 'Переключиться',
        'mini.rename': 'Переименовать…',
        'mini.hotkey': 'Горячая клавиша…',
        'mini.icon': 'Иконка…',
        'mini.tooltip_suffix': '  ·  ПКМ — меню',
        'mini.unavailable': 'WGC\nнедоступен',

        # переименование
        'rename.title': 'Переименовать окно',
        'rename.original': 'Оригинальное название:\n{title}',
        'rename.placeholder': 'Своё имя для окна…',
        'rename.delete': 'Удалить имя',

        # хоткей
        'hotkey.title': 'Горячая клавиша',
        'hotkey.window': 'Окно: {title}',
        'hotkey.current': 'Текущая: [{cur}]',
        'hotkey.not_set': 'не назначена',
        'hotkey.choose': 'Выберите цифру (0 = 10-й слот):',
        'hotkey.remove': 'Убрать хоткей',

        # иконка
        'icon.title': 'Иконка окна',
        'icon.none': 'Иконка не задана',
        'icon.choose': 'Выбрать файл…',
        'icon.remove': 'Удалить иконку',
        'icon.filter': 'Изображения (*.png *.ico *.jpg *.jpeg *.gif *.bmp);;Все файлы (*.*)',
        'icon.caption': 'Выберите иконку',

        # настройки
        'settings.title': 'Настройки',
        'settings.cat.general': 'Общие',
        'settings.cat.appearance': 'Вид',
        'settings.cat.info': 'Инфо',
        'settings.group.hotkeys': 'Горячие клавиши',
        'settings.enable_hotkeys': 'Включить горячие клавиши',
        'settings.use_shift': 'Использовать Shift+цифра (вместо простых цифр)',
        'settings.feedback': 'Показывать обратную связь (круг с цифрой)',
        'settings.tray_hotkey': 'Хоткей сворачивания в трей:',
        'settings.tray_hint': ('С Ctrl работают только спец-клавиши (буквы — нет, '
                               'ограничение Windows).\nПримеры: <ctrl>+<f9>, '
                               '<ctrl>+<shift>+<f10>, <alt>+<f8>'),
        'settings.group.appearance': 'Оформление',
        'settings.theme': 'Тема:',
        'settings.mode': 'Режим:',
        'settings.language': 'Язык:',
        'settings.mode_hint': ('«Мини-окно» показывает живые превью всех окон сеткой '
                               '(Windows.Graphics.Capture); масштаб — как у иконок '
                               '(Ctrl+колесо / Ctrl+↑↓).'),
        'settings.group.controls': 'Управление',
        'settings.invalid.title': 'Неверный хоткей',
        'settings.invalid.msg': ('Комбинация «{combo}» не распознана.\nОставлено прежнее '
                                 'значение. Пример формата: <ctrl>+<f9>'),
        'settings.info': (
            "<b>Переключение на окно</b><br>"
            "• Клик по имени или по иконке — переключиться на окно<br>"
            "• Цифры 1..9 и 0 — переключение на окно с соответствующим бейджем<br>"
            "• Режим Shift+цифра включается в разделе «Общие»<br>"
            "• Хоткеи работают, даже когда панель свёрнута<br><br>"
            "<b>Трей</b><br>"
            "• Хоткей сворачивания в трей (по умолчанию Ctrl+F9) — прячет/возвращает панель<br>"
            "• Клик по иконке в трее — показать/скрыть; правый клик — меню<br><br>"
            "<b>Список</b><br>"
            "• ▲ / ▼ — порядок; 🎨 — иконка, ⌨ — хоткей, ✎ — переименовать<br>"
            "• В «Мини-окне» — ПКМ по превью для тех же действий<br><br>"
            "<b>Клавиши</b><br>"
            "• F2 — настройки, F3 — обновить список (когда панель активна)<br>"
            "• Ctrl+↑ / Ctrl+↓ — размер иконок (глобально), либо Ctrl+колесо<br><br>"
            "<b>Окно</b><br>"
            "• Тянуть за шапку — переместить; за любой край — изменить размер"
        ),

        # темы / режимы
        'theme.black': 'Чёрная',
        'theme.white': 'Белая',
        'theme.orange': 'Оранжевая',
        'mode.full': 'Полный (иконки)',
        'mode.light': 'Лайт (только имена)',
        'mode.mini': 'Мини-окно (превью окон)',

        # приложение
        'app.already_running': ('Widgun уже запущен (возможно, свёрнут в трей).\n'
                                'Верни его хоткеем сворачивания или кликом по иконке в трее.'),
    },
    'en': {
        'common.save': 'Save',
        'common.cancel': 'Cancel',
        'common.close': 'Close',
        'error.title': 'Error',

        'tray.show_hide': 'Show / Hide',
        'tray.settings': 'Settings',
        'tray.quit': 'Quit',
        'tray.balloon': 'Minimized to tray. Click the icon or use the hotkey to restore.',
        'titlebar.min_tooltip': 'Minimize to tray',

        'mini.switch': 'Switch to',
        'mini.rename': 'Rename…',
        'mini.hotkey': 'Hotkey…',
        'mini.icon': 'Icon…',
        'mini.tooltip_suffix': '  ·  right-click for menu',
        'mini.unavailable': 'WGC\nunavailable',

        'rename.title': 'Rename window',
        'rename.original': 'Original title:\n{title}',
        'rename.placeholder': 'Custom name for the window…',
        'rename.delete': 'Delete name',

        'hotkey.title': 'Hotkey',
        'hotkey.window': 'Window: {title}',
        'hotkey.current': 'Current: [{cur}]',
        'hotkey.not_set': 'not set',
        'hotkey.choose': 'Choose a digit (0 = 10th slot):',
        'hotkey.remove': 'Remove hotkey',

        'icon.title': 'Window icon',
        'icon.none': 'No icon set',
        'icon.choose': 'Choose file…',
        'icon.remove': 'Remove icon',
        'icon.filter': 'Images (*.png *.ico *.jpg *.jpeg *.gif *.bmp);;All files (*.*)',
        'icon.caption': 'Choose an icon',

        'settings.title': 'Settings',
        'settings.cat.general': 'General',
        'settings.cat.appearance': 'Appearance',
        'settings.cat.info': 'Info',
        'settings.group.hotkeys': 'Hotkeys',
        'settings.enable_hotkeys': 'Enable hotkeys',
        'settings.use_shift': 'Use Shift+digit (instead of plain digits)',
        'settings.feedback': 'Show feedback (circle with number)',
        'settings.tray_hotkey': 'Minimize-to-tray hotkey:',
        'settings.tray_hint': ('With Ctrl only special keys work (letters do not — a '
                               'Windows limitation).\nExamples: <ctrl>+<f9>, '
                               '<ctrl>+<shift>+<f10>, <alt>+<f8>'),
        'settings.group.appearance': 'Appearance',
        'settings.theme': 'Theme:',
        'settings.mode': 'Mode:',
        'settings.language': 'Language:',
        'settings.mode_hint': ('"Mini window" shows live previews of all windows in a grid '
                               '(Windows.Graphics.Capture); scale it like icons '
                               '(Ctrl+wheel / Ctrl+↑↓).'),
        'settings.group.controls': 'Controls',
        'settings.invalid.title': 'Invalid hotkey',
        'settings.invalid.msg': ('The combo "{combo}" was not recognized.\nThe previous '
                                 'value was kept. Example format: <ctrl>+<f9>'),
        'settings.info': (
            "<b>Switch to a window</b><br>"
            "• Click a name or icon to switch<br>"
            "• Digits 1..9 and 0 switch to the window with that badge<br>"
            "• Shift+digit mode is toggled in the General tab<br>"
            "• Hotkeys work even when the panel is hidden<br><br>"
            "<b>Tray</b><br>"
            "• Minimize-to-tray hotkey (default Ctrl+F9) hides/restores the panel<br>"
            "• Click the tray icon to show/hide; right-click for a menu<br><br>"
            "<b>List</b><br>"
            "• ▲ / ▼ — order; 🎨 — icon, ⌨ — hotkey, ✎ — rename<br>"
            "• In Mini window — right-click a preview for the same actions<br><br>"
            "<b>Keys</b><br>"
            "• F2 — settings, F3 — refresh list (when the panel is focused)<br>"
            "• Ctrl+↑ / Ctrl+↓ — icon size (global), or Ctrl+wheel<br><br>"
            "<b>Window</b><br>"
            "• Drag the title bar to move; drag any edge to resize"
        ),

        'theme.black': 'Black',
        'theme.white': 'White',
        'theme.orange': 'Orange',
        'mode.full': 'Full (icons)',
        'mode.light': 'Light (names only)',
        'mode.mini': 'Mini window (previews)',

        'app.already_running': ('Widgun is already running (possibly minimized to tray).\n'
                                'Restore it with the tray hotkey or by clicking the tray icon.'),
    },
}


def set_language(code):
    global _current
    _current = code if code in LANGUAGES else DEFAULT_LANG


def get_language():
    return _current


def t(key, **kwargs):
    s = _STR.get(_current, {}).get(key)
    if s is None:
        s = _STR[DEFAULT_LANG].get(key, key)
    return s.format(**kwargs) if kwargs else s
