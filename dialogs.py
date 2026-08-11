"""
Модальные диалоги: переименование, назначение хоткея, управление иконкой,
и полноценное окно настроек с категориями (боковое меню + разделы).
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QLineEdit,
    QPushButton, QButtonGroup, QFileDialog, QCheckBox,
    QGroupBox, QComboBox, QListWidget, QStackedWidget, QWidget, QMessageBox,
)

from themes import THEMES, VIEW_MODES


def _title_label(text):
    lbl = QLabel(text)
    lbl.setObjectName("DialogTitle")
    lbl.setWordWrap(True)
    return lbl


class RenameDialog(QDialog):
    def __init__(self, window_logic, window_key, original_title, parent=None):
        super().__init__(parent)
        self.window_logic = window_logic
        self.window_key = window_key
        self.setWindowTitle("Переименовать окно")
        self.setMinimumWidth(380)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        layout.addWidget(_title_label(f"Оригинальное название:\n{original_title[:120]}"))

        self.edit = QLineEdit(window_logic.custom_names.get(window_key, ""))
        self.edit.setPlaceholderText("Своё имя для окна…")
        self.edit.selectAll()
        self.edit.returnPressed.connect(self._save)
        layout.addWidget(self.edit)

        btns = QHBoxLayout()
        save_btn = QPushButton("Сохранить"); save_btn.setObjectName("Primary")
        save_btn.clicked.connect(self._save)
        del_btn = QPushButton("Удалить имя"); del_btn.setObjectName("Warn")
        del_btn.clicked.connect(self._delete)
        cancel_btn = QPushButton("Отмена")
        cancel_btn.clicked.connect(self.reject)
        btns.addWidget(save_btn); btns.addWidget(del_btn); btns.addStretch(1); btns.addWidget(cancel_btn)
        layout.addLayout(btns)

    def _save(self):
        self.window_logic.set_custom_name(self.window_key, self.edit.text().strip())
        self.accept()

    def _delete(self):
        self.window_logic.set_custom_name(self.window_key, "")
        self.accept()


class HotkeyDialog(QDialog):
    def __init__(self, window_logic, window_key, original_title, current_number, parent=None):
        super().__init__(parent)
        self.window_logic = window_logic
        self.window_key = window_key
        self.setWindowTitle("Горячая клавиша")
        self.setMinimumWidth(400)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        layout.addWidget(_title_label(f"Окно: {original_title[:70]}"))
        cur = current_number if current_number is not None else "не назначена"
        accent = QLabel(f"Текущая: [{cur}]"); accent.setObjectName("Accent")
        layout.addWidget(accent)
        layout.addWidget(QLabel("Выберите цифру (0 = 10-й слот):"))

        grid = QGridLayout()
        grid.setSpacing(6)
        self.group = QButtonGroup(self)
        self.group.setExclusive(True)
        for i, digit in enumerate(list(range(1, 10)) + [0]):
            btn = QPushButton(str(digit))
            btn.setObjectName("HotkeyChoice")
            btn.setCheckable(True)
            if current_number == digit:
                btn.setChecked(True)
            self.group.addButton(btn, digit)
            grid.addWidget(btn, i // 5, i % 5)
        layout.addLayout(grid)

        btns = QHBoxLayout()
        save_btn = QPushButton("Сохранить"); save_btn.setObjectName("Primary")
        save_btn.clicked.connect(self._save)
        remove_btn = QPushButton("Убрать хоткей"); remove_btn.setObjectName("Danger")
        remove_btn.clicked.connect(self._remove)
        cancel_btn = QPushButton("Отмена")
        cancel_btn.clicked.connect(self.reject)
        btns.addWidget(save_btn); btns.addWidget(remove_btn); btns.addStretch(1); btns.addWidget(cancel_btn)
        layout.addLayout(btns)

    def _save(self):
        digit = self.group.checkedId()
        if digit == -1:
            self.reject()
            return
        self.window_logic.assign_hotkey(self.window_key, digit)
        self.accept()

    def _remove(self):
        self.window_logic.remove_hotkey(self.window_key)
        self.accept()


class IconDialog(QDialog):
    FILE_FILTER = "Изображения (*.png *.ico *.jpg *.jpeg *.gif *.bmp);;Все файлы (*.*)"

    def __init__(self, window_logic, window_key, original_title, parent=None):
        super().__init__(parent)
        self.window_logic = window_logic
        self.window_key = window_key
        self.setWindowTitle("Иконка окна")
        self.setMinimumWidth(360)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        layout.addWidget(_title_label(f"Окно: {original_title[:70]}"))

        self.preview = QLabel("Иконка не задана")
        self.preview.setObjectName("Muted")
        self.preview.setAlignment(Qt.AlignCenter)
        self.preview.setMinimumHeight(120)
        layout.addWidget(self.preview)
        self._load_preview()

        btns = QHBoxLayout()
        choose_btn = QPushButton("Выбрать файл…"); choose_btn.setObjectName("Primary")
        choose_btn.clicked.connect(self._choose)
        remove_btn = QPushButton("Удалить иконку"); remove_btn.setObjectName("Danger")
        remove_btn.clicked.connect(self._remove)
        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(self.reject)
        btns.addWidget(choose_btn); btns.addWidget(remove_btn); btns.addStretch(1); btns.addWidget(close_btn)
        layout.addLayout(btns)

    def _load_preview(self):
        icon_path = self.window_logic.window_icons.get(self.window_key, '')
        abs_path = self.window_logic.resolve_icon_path(icon_path)
        if abs_path and abs_path.exists():
            pix = QPixmap(str(abs_path))
            if not pix.isNull():
                self.preview.setPixmap(
                    pix.scaled(96, 96, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                )
                return
        self.preview.setText("Иконка не задана")

    def _choose(self):
        filename, _ = QFileDialog.getOpenFileName(self, "Выберите иконку", "", self.FILE_FILTER)
        if filename:
            self.window_logic.set_window_icon(self.window_key, filename)
            self.accept()

    def _remove(self):
        self.window_logic.remove_window_icon(self.window_key)
        self.accept()


class SettingsDialog(QDialog):
    """Полноценное окно настроек с категориями (Общие / Вид / Инфо)."""

    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.hotkey_manager = main_window.hotkey_manager
        self._orig_mode = main_window.get_view_mode()
        self.setWindowTitle("Настройки")
        self.setMinimumSize(560, 440)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        body = QHBoxLayout()
        body.setSpacing(12)

        # Боковое меню категорий
        self.sidebar = QListWidget()
        self.sidebar.setObjectName("SettingsSidebar")
        self.sidebar.setFixedWidth(150)
        for name in ("Общие", "Вид", "Инфо"):
            self.sidebar.addItem(name)
        self.stack = QStackedWidget()

        self.stack.addWidget(self._build_general())
        self.stack.addWidget(self._build_appearance())
        self.stack.addWidget(self._build_info())

        self.sidebar.currentRowChanged.connect(self.stack.setCurrentIndex)
        self.sidebar.setCurrentRow(0)

        body.addWidget(self.sidebar)
        body.addWidget(self.stack, 1)
        root.addLayout(body)

        # Кнопки внизу
        btns = QHBoxLayout()
        save_btn = QPushButton("Сохранить"); save_btn.setObjectName("Primary")
        save_btn.clicked.connect(self._save)
        cancel_btn = QPushButton("Отмена")
        cancel_btn.clicked.connect(self.reject)
        btns.addStretch(1); btns.addWidget(save_btn); btns.addWidget(cancel_btn)
        root.addLayout(btns)

    # ---------- Категория: Общие (хоткеи) ----------
    def _build_general(self):
        s = self.hotkey_manager.settings
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        box = QGroupBox("Горячие клавиши")
        form = QVBoxLayout(box)
        form.setSpacing(10)

        self.enabled_cb = QCheckBox("Включить горячие клавиши")
        self.enabled_cb.setChecked(s.get('enabled', True))
        form.addWidget(self.enabled_cb)

        self.shift_cb = QCheckBox("Использовать Shift+цифра (вместо простых цифр)")
        self.shift_cb.setChecked(s.get('use_shift', False))
        form.addWidget(self.shift_cb)

        self.feedback_cb = QCheckBox("Показывать обратную связь (круг с цифрой)")
        self.feedback_cb.setChecked(s.get('feedback_enabled', True))
        form.addWidget(self.feedback_cb)

        tray_row = QHBoxLayout()
        tray_row.addWidget(QLabel("Хоткей сворачивания в трей:"))
        self.tray_edit = QLineEdit(s.get('tray_hotkey', '<ctrl>+<f9>'))
        self.tray_edit.setPlaceholderText("<ctrl>+<f9>")
        tray_row.addWidget(self.tray_edit, 1)
        form.addLayout(tray_row)

        hint = QLabel(
            "С Ctrl работают только спец-клавиши (буквы — нет, ограничение Windows).\n"
            "Примеры: <ctrl>+<f9>, <ctrl>+<shift>+<f10>, <alt>+<f8>")
        hint.setObjectName("Muted")
        hint.setWordWrap(True)
        form.addWidget(hint)

        layout.addWidget(box)
        layout.addStretch(1)
        return page

    # ---------- Категория: Вид (тема / режим / иконки) ----------
    def _build_appearance(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        box = QGroupBox("Оформление")
        form = QVBoxLayout(box)
        form.setSpacing(10)

        theme_row = QHBoxLayout()
        theme_row.addWidget(QLabel("Тема:"))
        self.theme_combo = QComboBox()
        self._theme_keys = list(THEMES.keys())
        for key in self._theme_keys:
            self.theme_combo.addItem(THEMES[key], key)
        current_theme = self.main_window.get_theme()
        if current_theme in self._theme_keys:
            self.theme_combo.setCurrentIndex(self._theme_keys.index(current_theme))
        # живой предпросмотр темы
        self.theme_combo.currentIndexChanged.connect(
            lambda i: self.main_window.apply_theme(self._theme_keys[i]))
        theme_row.addWidget(self.theme_combo, 1)
        form.addLayout(theme_row)

        mode_row = QHBoxLayout()
        mode_row.addWidget(QLabel("Режим:"))
        self.mode_combo = QComboBox()
        self._mode_keys = list(VIEW_MODES.keys())
        for key in self._mode_keys:
            self.mode_combo.addItem(VIEW_MODES[key], key)
        current_mode = self.main_window.get_view_mode()
        if current_mode in self._mode_keys:
            self.mode_combo.setCurrentIndex(self._mode_keys.index(current_mode))
        # живой предпросмотр режима (как у темы)
        self.mode_combo.currentIndexChanged.connect(
            lambda i: self.main_window.preview_view_mode(self._mode_keys[i]))
        mode_row.addWidget(self.mode_combo, 1)
        form.addLayout(mode_row)

        hint = QLabel("«Мини-окно» показывает живые превью всех окон сеткой "
                      "(Windows.Graphics.Capture); масштаб — как у иконок "
                      "(Ctrl+колесо / Ctrl+↑↓).")
        hint.setObjectName("Muted")
        hint.setWordWrap(True)
        form.addWidget(hint)

        layout.addWidget(box)
        layout.addStretch(1)
        return page

    # ---------- Категория: Инфо ----------
    def _build_info(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)

        box = QGroupBox("Управление")
        inner = QVBoxLayout(box)
        info = QLabel(
            "<b>Переключение на окно</b><br>"
            "• Клик по имени или по иконке — переключиться на окно<br>"
            "• Цифры 1..9 и 0 — переключение на окно с соответствующим бейджем<br>"
            "• Режим Shift+цифра включается в разделе «Общие»<br>"
            "• Хоткеи работают, даже когда панель свёрнута<br><br>"
            "<b>Трей</b><br>"
            "• Хоткей сворачивания в трей (по умолчанию Ctrl+F9) — прячет/возвращает панель<br>"
            "• Клик по иконке в трее — показать/скрыть; правый клик — меню<br><br>"
            "<b>Список</b><br>"
            "• Перетаскивание строки (за ☰) — изменить порядок<br>"
            "• 🎨 — иконка, ⌨ — хоткей, ✎ — переименовать<br><br>"
            "<b>Клавиши</b><br>"
            "• F2 — настройки, F3 — обновить список (когда панель активна)<br>"
            "• Ctrl+↑ / Ctrl+↓ — размер иконок (глобально), либо Ctrl+колесо над списком<br><br>"
            "<b>Окно</b><br>"
            "• Тянуть за шапку — переместить<br>"
            "• Тянуть за любой край/угол — изменить размер"
        )
        info.setObjectName("InfoText")
        info.setWordWrap(True)
        info.setTextFormat(Qt.RichText)
        inner.addWidget(info)
        inner.addStretch(1)

        layout.addWidget(box)
        layout.addStretch(1)
        return page

    # ---------- Сохранение ----------
    def _save(self):
        # Хоткей трея: валидируем, при ошибке оставляем прежний
        tray_hotkey = self.tray_edit.text().strip()
        if tray_hotkey and not self.hotkey_manager.is_valid_hotkey(tray_hotkey):
            QMessageBox.warning(
                self, "Неверный хоткей",
                f"Комбинация «{tray_hotkey}» не распознана.\n"
                "Оставлено прежнее значение. Пример формата: <ctrl>+<shift>+s")
            tray_hotkey = self.hotkey_manager.settings.get('tray_hotkey', '<ctrl>+<shift>+s')

        # Хоткеи
        self.hotkey_manager.apply_settings({
            'enabled': self.enabled_cb.isChecked(),
            'use_shift': self.shift_cb.isChecked(),
            'feedback_enabled': self.feedback_cb.isChecked(),
            'tray_hotkey': tray_hotkey,
        })
        # Вид
        self.main_window.set_theme(self._theme_keys[self.theme_combo.currentIndex()])
        self.main_window.set_view_mode(self._mode_keys[self.mode_combo.currentIndex()])
        self.accept()

    def reject(self):
        # откатываем живой предпросмотр темы и режима к сохранённым
        self.main_window.apply_theme(self.main_window.get_theme())
        self.main_window.preview_view_mode(self._orig_mode)
        super().reject()
