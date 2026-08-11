"""
Темы оформления: чёрная, белая, оранжевая.

Один шаблон QSS + три палитры. Подстановка через string.Template ($-плейсхолдеры),
чтобы не конфликтовать с фигурными скобками QSS.
"""

from string import Template

THEMES = {
    'black': 'Чёрная',
    'white': 'Белая',
    'orange': 'Оранжевая',
}

# Режимы отображения панели
VIEW_MODES = {
    'full': 'Полный (иконки)',
    'light': 'Лайт (только имена)',
    'mini': 'Мини-окно (центр экрана)',
}

PALETTES = {
    'black': {
        'panel_bg': '#1e1f22', 'border': '#35373c', 'titlebar_bg': '#232428',
        'title_text': '#ffffff', 'text': '#e6e7ea', 'text_muted': '#9aa0a6',
        'accent': '#4f6bed', 'accent_hover': '#5f7bf5', 'accent_text': '#ffffff',
        'surface': '#2b2d31', 'surface_hover': '#34363c',
        'badge_bg': '#3a4a6b', 'badge_text': '#dfe7ff',
        'rowbtn_bg': '#3a3d44', 'rowbtn_hover': '#4a4e57',
        'input_bg': '#1e1f22', 'footer_bg': '#232428', 'mode_text': '#8fb7ff',
        'status_ok': '#43b581', 'danger': '#f04747', 'danger_hover': '#f45a5a',
        'warn': '#faa61a', 'warn_text': '#1e1f22',
        'scroll': '#3a3d44', 'scroll_hover': '#4a4e57',
        'drag_handle': '#6b6f76', 'list_bg': '#1e1f22',
    },
    'white': {
        'panel_bg': '#f7f8fa', 'border': '#d6d9df', 'titlebar_bg': '#eceef2',
        'title_text': '#1e1f22', 'text': '#24262b', 'text_muted': '#6b7280',
        'accent': '#3b6bf0', 'accent_hover': '#4f7cf5', 'accent_text': '#ffffff',
        'surface': '#ffffff', 'surface_hover': '#eef1f6',
        'badge_bg': '#dbe4ff', 'badge_text': '#2743a0',
        'rowbtn_bg': '#e7eaf0', 'rowbtn_hover': '#d8dce4',
        'input_bg': '#ffffff', 'footer_bg': '#eceef2', 'mode_text': '#3b6bf0',
        'status_ok': '#2f9e63', 'danger': '#e23b3b', 'danger_hover': '#ef4d4d',
        'warn': '#e08600', 'warn_text': '#ffffff',
        'scroll': '#cdd2da', 'scroll_hover': '#b9bfc9',
        'drag_handle': '#9aa1ac', 'list_bg': '#f7f8fa',
    },
    'orange': {
        'panel_bg': '#241a12', 'border': '#4a3524', 'titlebar_bg': '#2e2117',
        'title_text': '#ffe9d6', 'text': '#f2e4d8', 'text_muted': '#b79a83',
        'accent': '#f0862a', 'accent_hover': '#ff9a44', 'accent_text': '#241a12',
        'surface': '#33241a', 'surface_hover': '#40301f',
        'badge_bg': '#6b3f1a', 'badge_text': '#ffd9b0',
        'rowbtn_bg': '#45311f', 'rowbtn_hover': '#56402a',
        'input_bg': '#241a12', 'footer_bg': '#2e2117', 'mode_text': '#ffb779',
        'status_ok': '#8bbf5a', 'danger': '#e2593b', 'danger_hover': '#f06b4d',
        'warn': '#f0a82a', 'warn_text': '#241a12',
        'scroll': '#45311f', 'scroll_hover': '#56402a',
        'drag_handle': '#a3805f', 'list_bg': '#241a12',
    },
}

_TEMPLATE = Template("""
* { font-family: "Segoe UI", "Inter", sans-serif; color: $text; }

#Panel { background-color: $panel_bg; border: 1px solid $border; border-radius: 10px; }

#TitleBar {
    background-color: $titlebar_bg;
    border-top-left-radius: 10px; border-top-right-radius: 10px;
}
#TitleLabel { font-size: 12px; font-weight: 600; color: $title_text; }
#SettingsButton, #CloseButton, #ModeButton {
    background-color: transparent; border: none; border-radius: 6px;
    font-size: 14px; padding: 4px 8px; color: $text;
}
#SettingsButton:hover, #ModeButton:hover { background-color: $surface_hover; }
#CloseButton:hover { background-color: $danger; color: #ffffff; }

#WindowList {
    background-color: $list_bg; border: none; outline: 0; padding: 4px;
}
#WindowList::item { border: none; margin: 2px 0; padding: 0; }
#WindowList::item:selected { background: transparent; }

#WindowRow { background-color: $surface; border: 1px solid $border; border-radius: 8px; }
#WindowRow:hover { background-color: $surface_hover; }

#MiniGrid { background-color: $list_bg; }
#MiniCell {
    background-color: $surface;
    border: 1px solid $border;
    border-radius: 6px;
}
#MiniCell:hover { border: 1px solid $accent; }
#MiniPreview { background-color: $panel_bg; border-radius: 4px; color: $text_muted; }
#MiniName { color: $text; font-size: 11px; }

#DragHandle { color: $drag_handle; font-size: 13px; }

#HotkeyBadge {
    background-color: $badge_bg; color: $badge_text; font-weight: 700;
    font-size: 11px; border-radius: 5px; padding: 1px 6px;
}

#WindowName, #IconButton {
    font-size: 13px; color: $text; background: transparent; border: none; text-align: left;
}
#WindowName:hover { color: $accent; }
#IconButton { border-radius: 6px; }
#IconButton:hover { background-color: $surface_hover; }

.RowButton {
    background-color: $rowbtn_bg; border: none; border-radius: 6px;
    padding: 4px 7px; font-size: 13px; min-width: 14px; color: $text;
}
.RowButton:hover { background-color: $rowbtn_hover; }

#MoveButton {
    background-color: $rowbtn_bg; border: none; border-radius: 3px;
    color: $text_muted; font-size: 9px; padding: 0;
}
#MoveButton:hover { background-color: $accent; color: $accent_text; }

#Footer {
    background-color: $footer_bg;
    border-bottom-left-radius: 10px; border-bottom-right-radius: 10px;
}
#StatusLabel { color: $status_ok; font-size: 11px; }

QScrollBar:vertical { background: transparent; width: 10px; margin: 2px; }
QScrollBar::handle:vertical { background: $scroll; border-radius: 5px; min-height: 24px; }
QScrollBar::handle:vertical:hover { background: $scroll_hover; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; }

/* ===== Диалоги / настройки ===== */
QDialog { background-color: $titlebar_bg; }
QLabel { color: $text; }
QLabel#DialogTitle { font-size: 13px; font-weight: 600; }
QLabel#Muted { color: $text_muted; }
QLabel#Accent { color: $accent; font-weight: 600; }
QLabel#InfoText { color: $text; font-size: 12px; }

#SettingsSidebar {
    background-color: $panel_bg; border: 1px solid $border;
    border-radius: 8px; outline: 0; padding: 4px;
}
#SettingsSidebar::item { padding: 8px 12px; border-radius: 6px; color: $text; }
#SettingsSidebar::item:selected { background-color: $accent; color: $accent_text; }
#SettingsSidebar::item:hover:!selected { background-color: $surface_hover; }

QLineEdit, QSpinBox, QComboBox {
    background-color: $input_bg; border: 1px solid $border; border-radius: 6px;
    padding: 6px 8px; selection-background-color: $accent; color: $text;
}
QLineEdit:focus, QSpinBox:focus, QComboBox:focus { border: 1px solid $accent; }
QComboBox QAbstractItemView {
    background-color: $panel_bg; border: 1px solid $border;
    selection-background-color: $accent; selection-color: $accent_text;
}

QCheckBox, QRadioButton { spacing: 8px; padding: 3px; color: $text; }
QCheckBox::indicator, QRadioButton::indicator { width: 16px; height: 16px; }

QPushButton {
    background-color: $rowbtn_bg; border: none; border-radius: 6px;
    padding: 7px 14px; font-size: 12px; color: $text;
}
QPushButton:hover { background-color: $rowbtn_hover; }
QPushButton#Primary { background-color: $accent; color: $accent_text; }
QPushButton#Primary:hover { background-color: $accent_hover; }
QPushButton#Danger { background-color: $danger; color: #ffffff; }
QPushButton#Danger:hover { background-color: $danger_hover; }
QPushButton#Warn { background-color: $warn; color: $warn_text; }

QPushButton#HotkeyChoice { min-width: 30px; padding: 8px; font-weight: 700; }
QPushButton#HotkeyChoice:checked { background-color: $accent; color: $accent_text; }

QSlider::groove:horizontal { height: 6px; background: $input_bg; border-radius: 3px; }
QSlider::handle:horizontal {
    background: $accent; width: 16px; margin: -6px 0; border-radius: 8px;
}
QSlider::sub-page:horizontal { background: $accent; border-radius: 3px; }

QGroupBox {
    border: 1px solid $border; border-radius: 8px; margin-top: 10px; padding: 10px;
}
QGroupBox::title {
    subcontrol-origin: margin; left: 10px; padding: 0 4px; color: $text_muted;
}

QMenu {
    background-color: $panel_bg; border: 1px solid $border;
    border-radius: 6px; padding: 4px;
}
QMenu::item { padding: 6px 16px; border-radius: 4px; color: $text; }
QMenu::item:selected { background-color: $accent; color: $accent_text; }
QMenu::separator { height: 1px; background: $border; margin: 4px 8px; }

QMessageBox { background-color: $titlebar_bg; }
""")


def build_qss(theme_name):
    palette = PALETTES.get(theme_name, PALETTES['black'])
    return _TEMPLATE.substitute(palette)


def apply_theme(app, theme_name):
    app.setStyleSheet(build_qss(theme_name))
