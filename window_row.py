"""
Виджет одной строки списка окон.

Слева: кнопки ▲/▼ (переместить строку вверх/вниз) · бейдж [n] · иконка(кликабельная)
Далее: имя(клик) · 🎨 · ⌨ · ✎.  В лайт-режиме иконка не показывается.
Клик и по имени, и по иконке активирует окно. Действия — через сигналы.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QSizePolicy
)


class ClickableLabel(QLabel):
    """Метка-«ссылка»: клик активирует окно. Умеет переносить текст по словам."""

    clicked = Signal()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class WindowRow(QWidget):
    activate_requested = Signal(str)                 # key
    rename_requested = Signal(str, str)              # key, original_title
    hotkey_requested = Signal(str, str, object)      # key, original_title, current_number
    icon_requested = Signal(str, str)                # key, original_title
    move_requested = Signal(str, int)                # key, delta (-1 вверх / +1 вниз)

    def __init__(self, window_data, pixmap=None, show_icons=True, light=False, parent=None):
        super().__init__(parent)
        self.setObjectName("WindowRow")
        self._icon_h = 0

        self.key = window_data.get('key', '')
        original_title = window_data.get('title', '')
        custom_name = window_data.get('custom_name', '')
        formatted = window_data.get('formatted_title', 'Unknown')
        hotkey_number = window_data.get('hotkey_number')
        display_name = custom_name if custom_name else formatted

        layout = QHBoxLayout(self)
        margin_v = 3 if light else 5
        layout.setContentsMargins(6, margin_v, 8, margin_v)
        layout.setSpacing(6)

        # Кнопки перемещения вверх/вниз
        move_col = QVBoxLayout()
        move_col.setSpacing(1)
        up_btn = self._make_move_button("▲")
        up_btn.clicked.connect(lambda: self.move_requested.emit(self.key, -1))
        down_btn = self._make_move_button("▼")
        down_btn.clicked.connect(lambda: self.move_requested.emit(self.key, 1))
        move_col.addWidget(up_btn)
        move_col.addWidget(down_btn)
        layout.addLayout(move_col)

        # Бейдж хоткея
        if hotkey_number is not None:
            badge = QLabel(str(hotkey_number))
            badge.setObjectName("HotkeyBadge")
            layout.addWidget(badge)

        # Иконка (кликабельная) — только в полном режиме
        if not light and show_icons and pixmap is not None and not pixmap.isNull():
            icon_btn = QPushButton()
            icon_btn.setObjectName("IconButton")
            icon_btn.setFlat(True)
            icon_btn.setCursor(Qt.PointingHandCursor)
            icon_btn.setIcon(QIcon(pixmap))
            icon_btn.setIconSize(pixmap.size())
            icon_btn.setFixedSize(pixmap.width() + 8, pixmap.height() + 8)
            icon_btn.clicked.connect(lambda: self.activate_requested.emit(self.key))
            layout.addWidget(icon_btn)
            self._icon_h = pixmap.height() + 8

        # Имя окна (клик = активация). Длинное имя переносится по словам вниз,
        # а не налезает на иконку/кнопки.
        self.name_lbl = ClickableLabel(display_name)
        self.name_lbl.setObjectName("WindowName")
        self.name_lbl.setWordWrap(True)
        self.name_lbl.setCursor(Qt.PointingHandCursor)
        self.name_lbl.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        sp = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        sp.setHeightForWidth(True)
        self.name_lbl.setSizePolicy(sp)
        self.name_lbl.clicked.connect(lambda: self.activate_requested.emit(self.key))
        layout.addWidget(self.name_lbl, 1)

        # Кнопки действий
        if show_icons:
            icon_action = self._make_button("🎨")
            icon_action.clicked.connect(
                lambda: self.icon_requested.emit(self.key, original_title)
            )
            layout.addWidget(icon_action)

        hotkey_btn = self._make_button("⌨")
        hotkey_btn.clicked.connect(
            lambda: self.hotkey_requested.emit(self.key, original_title, hotkey_number)
        )
        layout.addWidget(hotkey_btn)

        rename_btn = self._make_button("✎")
        rename_btn.clicked.connect(
            lambda: self.rename_requested.emit(self.key, original_title)
        )
        layout.addWidget(rename_btn)

        # Минимальная высота содержимого (иконка или ряд кнопок ▲/▼)
        self._min_content_height = max(self._icon_h, 31)

    # ---- Динамическая высота: имя переносится вниз, а не налезает ----

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        lay = self.layout()
        m = lay.contentsMargins()
        spacing = lay.spacing() if lay.spacing() > 0 else 6

        # ширина, занятая всем, кроме имени
        reserved = m.left() + m.right()
        for i in range(lay.count()):
            item = lay.itemAt(i)
            w = item.widget()
            sub = item.layout()
            if w is self.name_lbl:
                continue
            if w is not None:
                reserved += w.sizeHint().width()
            elif sub is not None:
                reserved += sub.sizeHint().width()
        reserved += spacing * max(0, lay.count() - 1)

        avail = max(24, width - reserved)
        name_h = self.name_lbl.heightForWidth(avail)
        if name_h <= 0:
            name_h = self.name_lbl.sizeHint().height()

        return max(self._min_content_height, name_h) + m.top() + m.bottom()

    def _make_button(self, text):
        btn = QPushButton(text)
        btn.setProperty("class", "RowButton")
        btn.setCursor(Qt.PointingHandCursor)
        return btn

    def _make_move_button(self, text):
        btn = QPushButton(text)
        btn.setObjectName("MoveButton")
        btn.setCursor(Qt.PointingHandCursor)
        btn.setFixedSize(20, 15)
        return btn
