"""
Главное окно «Смотрюн3000» — frameless always-on-top панель.

Перемещение — за шапку (startSystemMove). Ресайз — за любой край/угол,
через нативный WM_NCHITTEST (ОС сама тянет границы, как у обычного окна).
Размер иконок фиксированный. Порядок строк меняется кнопками ▲/▼.
Активация окна не трогает флаг topmost и не использует minimize/alt-tab —
поэтому без мигания экрана.
"""

import json
import math
import ctypes
import ctypes.wintypes

from PySide6.QtCore import Qt, QPoint, QSize, Signal, QTimer
from PySide6.QtGui import (
    QPixmap, QImage, QKeySequence, QShortcut, QIcon, QPainter, QColor,
)
from PySide6.QtWidgets import (
    QWidget, QFrame, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QAbstractItemView, QMessageBox, QApplication,
    QSystemTrayIcon, QMenu, QStackedWidget, QSizePolicy,
)

from paths import SETTINGS_FILE, ensure_config_dir
from window_row import WindowRow
from dialogs import RenameDialog, HotkeyDialog, IconDialog, SettingsDialog
from feedback_overlay import FeedbackOverlay
from window_capture import WindowCaptureManager
import themes

ICON_DEFAULT, ICON_MIN, ICON_MAX = 48, 16, 256
ICON_STEP = 8

# Мини-окно: сетка живых превью окон
MINI_INTERVAL = 100      # период обновления сетки, мс

DEFAULT_SETTINGS = {
    'show_icons': True,
    'theme': 'black',
    'view_mode': 'full',   # 'full' | 'light' | 'mini'
    'icon_size': ICON_DEFAULT,
}
RESIZE_MARGIN = 7        # ширина прозрачной рамки-зоны ресайза

# WM_NCHITTEST коды
WM_NCHITTEST = 0x0084
HTLEFT, HTRIGHT, HTTOP, HTTOPLEFT, HTTOPRIGHT = 10, 11, 12, 13, 14
HTBOTTOM, HTBOTTOMLEFT, HTBOTTOMRIGHT = 15, 16, 17


class WindowListWidget(QListWidget):
    """Список окон: Ctrl+колесо меняет размер иконок; высота строк
    пересчитывается под ширину (длинное имя переносится вниз)."""

    ctrl_wheel = Signal(int)  # +1 больше / -1 меньше

    def wheelEvent(self, event):
        if event.modifiers() & Qt.ControlModifier:
            self.ctrl_wheel.emit(1 if event.angleDelta().y() > 0 else -1)
            event.accept()
        else:
            super().wheelEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.relayout_items()

    def relayout_items(self):
        w = self.viewport().width()
        if w <= 0:
            return
        for i in range(self.count()):
            item = self.item(i)
            widget = self.itemWidget(item)
            if widget is None:
                continue
            h = widget.heightForWidth(w) if widget.hasHeightForWidth() \
                else widget.sizeHint().height()
            if h > 0 and item.sizeHint().height() != h:
                item.setSizeHint(QSize(w, h))


class MiniCell(QFrame):
    """Ячейка сетки: живое превью окна + подпись (ник), клик — активация."""

    clicked = Signal(str)  # key

    def __init__(self, key, label_text, parent=None):
        super().__init__(parent)
        self.key = key
        self.setObjectName("MiniCell")
        self.setCursor(Qt.PointingHandCursor)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(3, 3, 3, 3)
        lay.setSpacing(2)

        self.preview = QLabel()
        self.preview.setObjectName("MiniPreview")
        self.preview.setAlignment(Qt.AlignCenter)
        self.preview.setMinimumSize(1, 1)
        self.preview.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        lay.addWidget(self.preview, 1)

        self.name = QLabel(label_text)
        self.name.setObjectName("MiniName")
        self.name.setAlignment(Qt.AlignCenter)
        # Ignored по горизонтали — длинная подпись не растягивает колонку
        self.name.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        lay.addWidget(self.name)

    def set_min_side(self, side):
        self.preview.setMinimumSize(side, max(1, side * 9 // 16))

    def set_frame(self, pix):
        self.preview.setPixmap(pix)

    def show_placeholder(self, text):
        pm = self.preview.pixmap()
        if pm is None or pm.isNull():
            self.preview.setText(text)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.key)
        super().mousePressEvent(event)


class MiniGrid(QWidget):
    """Сетка живых превью окон. Ctrl+колесо — масштаб (как у иконок)."""

    ctrl_wheel = Signal(int)
    activate_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("MiniGrid")
        self._grid = QGridLayout(self)
        self._grid.setContentsMargins(6, 6, 6, 6)
        self._grid.setSpacing(6)
        self.cells = {}   # key -> (MiniCell, hwnd)

    def rebuild(self, windows):
        while self._grid.count():
            item = self._grid.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        self.cells.clear()

        n = len(windows)
        if n == 0:
            return
        columns = max(1, int(math.ceil(math.sqrt(n))))
        for idx, wd in enumerate(windows):
            hwnd = getattr(wd.get('window_object'), '_hWnd', None)
            name = wd.get('custom_name') or wd.get('formatted_title', '')
            if len(name) > 22:
                name = name[:21] + '…'
            num = wd.get('hotkey_number')
            label = f"[{num}] {name}" if num is not None else name
            cell = MiniCell(wd['key'], label)
            cell.setToolTip(wd.get('custom_name') or wd.get('formatted_title', ''))
            cell.clicked.connect(self.activate_requested)
            r, c = divmod(idx, columns)
            self._grid.addWidget(cell, r, c)
            self.cells[wd['key']] = (cell, hwnd)

    def wheelEvent(self, event):
        if event.modifiers() & Qt.ControlModifier:
            self.ctrl_wheel.emit(1 if event.angleDelta().y() > 0 else -1)
            event.accept()
        else:
            super().wheelEvent(event)


class TitleBar(QFrame):
    """Шапка окна: тянем за неё — системное перемещение окна."""

    def __init__(self, window, parent=None):
        super().__init__(parent)
        self.setObjectName("TitleBar")
        self._window = window
        self.setFixedHeight(40)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 8, 0)

        title = QLabel("👁️ Смотрюн3000")
        title.setObjectName("TitleLabel")
        layout.addWidget(title)
        layout.addStretch(1)

        settings_btn = QPushButton("⚙")
        settings_btn.setObjectName("SettingsButton")
        settings_btn.setCursor(Qt.PointingHandCursor)
        settings_btn.clicked.connect(window.open_settings)
        layout.addWidget(settings_btn)

        min_btn = QPushButton("—")
        min_btn.setObjectName("MinimizeButton")
        min_btn.setCursor(Qt.PointingHandCursor)
        min_btn.setToolTip("Свернуть в трей")
        min_btn.clicked.connect(window.hide_to_tray)
        layout.addWidget(min_btn)

        close_btn = QPushButton("✕")
        close_btn.setObjectName("CloseButton")
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.clicked.connect(window.close)
        layout.addWidget(close_btn)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            handle = self._window.windowHandle()
            if handle:
                handle.startSystemMove()
                event.accept()


class MainWindow(QWidget):
    def __init__(self, window_logic, hotkey_manager):
        super().__init__()
        self.window_logic = window_logic
        self.hotkey_manager = hotkey_manager
        self.auto_refresher = None

        self.app_settings = self._load_settings()
        self.show_icons = bool(self.app_settings.get('show_icons', True))
        self.theme = self.app_settings.get('theme', 'black')
        self.view_mode = self._resolve_view_mode()
        self.icon_size = max(ICON_MIN, min(ICON_MAX,
                             int(self.app_settings.get('icon_size', ICON_DEFAULT))))

        self._pixmap_cache = {}
        self._list_signature = None
        self._grid_sig = None
        self._rebuilding = False

        self.tray = None

        # Живой захват окон (WGC) + таймер обновления сетки мини-режима
        self.capture = WindowCaptureManager()
        self._mini_timer = QTimer(self)
        self._mini_timer.setInterval(MINI_INTERVAL)
        self._mini_timer.timeout.connect(self._update_grid)

        self._setup_window()
        self._build_ui()
        self._setup_tray()
        self._wire_signals()
        self._install_shortcuts()
        self._apply_view_mode()

        # Материализуем settings.json на первом запуске
        if not SETTINGS_FILE.exists():
            self._save_settings()

    def _resolve_view_mode(self):
        """Определить режим, мигрируя со старого light_mode при необходимости."""
        mode = self.app_settings.get('view_mode')
        if mode in themes.VIEW_MODES:
            return mode
        # старый формат
        if self.app_settings.get('light_mode'):
            return 'light'
        return 'full'

    # ========== ОКНО ==========

    def _setup_window(self):
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowTitle("Смотрюн3000")
        self.setMinimumSize(300, 240)
        self.resize(380, 520)
        self.move(120, 120)

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(RESIZE_MARGIN, RESIZE_MARGIN, RESIZE_MARGIN, RESIZE_MARGIN)

        self.panel = QFrame()
        self.panel.setObjectName("Panel")
        outer.addWidget(self.panel)

        root = QVBoxLayout(self.panel)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(TitleBar(self))

        # Стек: страница со списком (полный/лайт) и страница мини-окна
        self.stack = QStackedWidget()

        self.list = WindowListWidget()
        self.list.setObjectName("WindowList")
        self.list.setSelectionMode(QAbstractItemView.NoSelection)
        self.list.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.list.setFocusPolicy(Qt.NoFocus)
        self.list.ctrl_wheel.connect(
            lambda direction: self._change_icon_size(direction * ICON_STEP))
        self.stack.addWidget(self.list)

        self.mini_grid = MiniGrid()
        self.mini_grid.ctrl_wheel.connect(
            lambda direction: self._change_icon_size(direction * ICON_STEP))
        self.mini_grid.activate_requested.connect(self._activate)
        self.stack.addWidget(self.mini_grid)

        root.addWidget(self.stack, 1)

        # Тонкий нижний кап для скруглённых углов (без статус-строки)
        footer = QFrame()
        footer.setObjectName("Footer")
        footer.setFixedHeight(10)
        root.addWidget(footer)

    def _wire_signals(self):
        self.window_logic.windows_updated.connect(self._on_windows_updated)
        self.window_logic.error_occurred.connect(self._on_error)
        self.hotkey_manager.hotkey_activated.connect(self._on_hotkey)
        self.hotkey_manager.toggle_visibility_requested.connect(self._toggle_tray)
        self.hotkey_manager.icon_size_step_requested.connect(
            lambda direction: self._change_icon_size(direction * ICON_STEP))

    def _install_shortcuts(self):
        # Локальные (когда панель активна). Глобальные размеры иконок и трей —
        # через pynput в hotkey_manager (работают из любого окна).
        self._add_shortcut("F2", self.open_settings)
        self._add_shortcut("F3", self.window_logic.refresh_windows)

    def _add_shortcut(self, sequence, handler):
        sc = QShortcut(QKeySequence(sequence), self, handler)
        # ApplicationShortcut — срабатывает даже при NoFocus у виджетов
        sc.setContext(Qt.ApplicationShortcut)
        return sc

    def set_auto_refresher(self, refresher):
        self.auto_refresher = refresher

    # ========== ТРЕЙ ==========

    def _make_app_icon(self):
        """Простая иконка-«глаз» для трея/таскбара (без внешних файлов)."""
        pix = QPixmap(64, 64)
        pix.fill(Qt.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor('#4f6bed'))
        p.drawEllipse(4, 4, 56, 56)
        p.setBrush(QColor('#ffffff'))
        p.drawEllipse(16, 22, 32, 20)
        p.setBrush(QColor('#1e1f22'))
        p.drawEllipse(26, 26, 12, 12)
        p.end()
        return QIcon(pix)

    def _setup_tray(self):
        icon = self._make_app_icon()
        self.setWindowIcon(icon)
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        self.tray = QSystemTrayIcon(icon, self)
        self.tray.setToolTip("Смотрюн3000")

        menu = QMenu()
        menu.addAction("Показать / Скрыть", self._toggle_tray)
        menu.addAction("Настройки", self.open_settings)
        menu.addSeparator()
        menu.addAction("Выход", self.close)
        self.tray.setContextMenu(menu)
        self._tray_menu = menu

        self.tray.activated.connect(self._on_tray_activated)
        self.tray.show()

    def _on_tray_activated(self, reason):
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            self._toggle_tray()

    def _toggle_tray(self):
        """Свернуть панель в трей или вернуть её на экран."""
        if self.isVisible():
            self.hide_to_tray()
        else:
            self._restore_from_tray()

    def hide_to_tray(self):
        """Убрать панель с экрана в трей (кнопка «—» или хоткей)."""
        if self.tray:
            self.hide()
            if self.tray.supportsMessages():
                self.tray.showMessage(
                    "Смотрюн3000",
                    "Свёрнуто в трей. Клик по иконке или хоткей — вернуть.",
                    QSystemTrayIcon.Information, 2500)
        else:
            self.showMinimized()

    def _restore_from_tray(self):
        self.show()
        self.raise_()
        self.activateWindow()

    # ========== НАТИВНЫЙ РЕСАЙЗ ЗА КРАЯ ==========

    def nativeEvent(self, eventType, message):
        if eventType in (b"windows_generic_MSG", "windows_generic_MSG"):
            try:
                msg = ctypes.wintypes.MSG.from_address(int(message))
            except Exception:
                return super().nativeEvent(eventType, message)

            if msg.message == WM_NCHITTEST:
                gx = ctypes.c_short(msg.lParam & 0xFFFF).value
                gy = ctypes.c_short((msg.lParam >> 16) & 0xFFFF).value
                pt = self.mapFromGlobal(QPoint(gx, gy))
                x, y, w, h = pt.x(), pt.y(), self.width(), self.height()
                b = RESIZE_MARGIN + 3
                left, right = x < b, x > w - b
                top, bottom = y < b, y > h - b
                if top and left:
                    return True, HTTOPLEFT
                if top and right:
                    return True, HTTOPRIGHT
                if bottom and left:
                    return True, HTBOTTOMLEFT
                if bottom and right:
                    return True, HTBOTTOMRIGHT
                if left:
                    return True, HTLEFT
                if right:
                    return True, HTRIGHT
                if top:
                    return True, HTTOP
                if bottom:
                    return True, HTBOTTOM
        return super().nativeEvent(eventType, message)

    # ========== ИКОНКИ ==========

    def _pixmap_for(self, icon_path):
        if self.view_mode != 'full' or not self.show_icons or not icon_path:
            return None
        abs_path = self.window_logic.resolve_icon_path(icon_path)
        if not abs_path or not abs_path.exists():
            return None
        cache_key = (str(abs_path), self.icon_size)
        if cache_key in self._pixmap_cache:
            return self._pixmap_cache[cache_key]
        pix = QPixmap(str(abs_path))
        if pix.isNull():
            return None
        pix = pix.scaled(self.icon_size, self.icon_size,
                         Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self._pixmap_cache[cache_key] = pix
        return pix

    def _change_icon_size(self, delta):
        self.set_icon_size(self.icon_size + delta)

    def _reset_icon_size(self):
        self.set_icon_size(ICON_DEFAULT)

    def set_icon_size(self, size):
        new_size = max(ICON_MIN, min(ICON_MAX, int(size)))
        if new_size == self.icon_size:
            return
        self.icon_size = new_size
        self.app_settings['icon_size'] = new_size
        self._save_settings()
        self._pixmap_cache.clear()
        if self.view_mode == 'mini':
            self._update_grid()
        else:
            self._force_rebuild()

    # ========== РЕЖИМ ОТОБРАЖЕНИЯ ==========

    def get_view_mode(self):
        return self.view_mode

    def preview_view_mode(self, mode):
        """Применить режим визуально, без сохранения (для предпросмотра)."""
        if mode not in themes.VIEW_MODES:
            return
        self.view_mode = mode
        self.app_settings['view_mode'] = mode
        self.app_settings.pop('light_mode', None)   # чистим старый ключ
        self._apply_view_mode()

    def set_view_mode(self, mode):
        """Применить и сохранить режим."""
        self.preview_view_mode(mode)
        self._save_settings()

    def _apply_view_mode(self):
        if self.view_mode == 'mini':
            self.stack.setCurrentWidget(self.mini_grid)
            self._rebuild_grid(self.window_logic.windows_cache)
        else:
            self.stack.setCurrentWidget(self.list)
            self._force_rebuild()
            self.capture.stop_all()
        self._update_mini_timer()

    # ========== МИНИ-РЕЖИМ (сетка живых превью) ==========

    def _grid_signature(self, windows):
        return tuple(
            (w['key'], getattr(w.get('window_object'), '_hWnd', None))
            for w in windows
        )

    def _rebuild_grid(self, windows):
        """Пересобрать сетку и синхронизировать WGC-сессии под текущие окна."""
        self._grid_sig = self._grid_signature(windows)
        self.mini_grid.rebuild(windows)
        hwnds = [hwnd for (_cell, hwnd) in self.mini_grid.cells.values() if hwnd]
        self.capture.set_targets(hwnds)
        self._update_grid()

    def _maybe_rebuild_grid(self, windows):
        if self._grid_signature(windows) != self._grid_sig:
            self._rebuild_grid(windows)

    def _update_mini_timer(self):
        active = (self.view_mode == 'mini' and self.isVisible())
        if active:
            if not self._mini_timer.isActive():
                self._mini_timer.start()
        else:
            if self._mini_timer.isActive():
                self._mini_timer.stop()
            self.capture.stop_all()

    def _update_grid(self):
        if self.view_mode != 'mini':
            return
        floor = self.icon_size
        for key, (cell, hwnd) in self.mini_grid.cells.items():
            cell.set_min_side(floor)
            frame = self.capture.latest(hwnd) if hwnd else None
            if frame is None:
                cell.show_placeholder("…" if self.capture.available() else "WGC\nнедоступен")
                continue
            data, w, h = frame
            img = QImage(data, w, h, w * 4, QImage.Format_ARGB32)
            # цель — фактический размер превью в ячейке, но не меньше icon_size
            tw = max(cell.preview.width(), floor)
            th = max(cell.preview.height(), floor * 9 // 16)
            pix = QPixmap.fromImage(img).scaled(
                tw, th, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            cell.set_frame(pix)

    def showEvent(self, event):
        super().showEvent(event)
        if self.view_mode == 'mini':
            self._rebuild_grid(self.window_logic.windows_cache)
        self._update_mini_timer()

    def hideEvent(self, event):
        super().hideEvent(event)
        self._update_mini_timer()

    # ========== ТЕМЫ ==========

    def get_theme(self):
        return self.theme

    def apply_theme(self, theme_name):
        """Применить тему визуально (без сохранения) — для предпросмотра."""
        app = QApplication.instance()
        if app:
            themes.apply_theme(app, theme_name)

    def set_theme(self, theme_name):
        """Применить и сохранить тему."""
        self.theme = theme_name
        self.app_settings['theme'] = theme_name
        self._save_settings()
        self.apply_theme(theme_name)

    # ========== СПИСОК ОКОН ==========

    def _signature(self, windows):
        return (self.view_mode, self.show_icons, self.icon_size) + tuple(
            (w['key'], w.get('custom_name', ''), w.get('formatted_title', ''),
             w.get('hotkey_number'), w.get('icon_path', ''))
            for w in windows
        )

    def _force_rebuild(self):
        self._list_signature = None
        self._on_windows_updated(self.window_logic.windows_cache)

    def _on_windows_updated(self, windows):
        # В мини-режиме обновляем сетку превью, а не список
        if self.view_mode == 'mini':
            self._maybe_rebuild_grid(windows)
            return

        signature = self._signature(windows)
        if signature == self._list_signature:
            return
        self._list_signature = signature

        self._rebuilding = True
        self.list.clear()
        for w in windows:
            pixmap = self._pixmap_for(w.get('icon_path', ''))
            row = WindowRow(w, pixmap, self.show_icons, self.view_mode == 'light')
            row.activate_requested.connect(self._activate)
            row.rename_requested.connect(self._open_rename)
            row.hotkey_requested.connect(self._open_hotkey)
            row.icon_requested.connect(self._open_icon)
            row.move_requested.connect(self._move_row)

            item = QListWidgetItem(self.list)
            item.setData(Qt.UserRole, w['key'])
            vw = self.list.viewport().width()
            if vw > 0 and row.hasHeightForWidth():
                item.setSizeHint(QSize(vw, row.heightForWidth(vw)))
            else:
                item.setSizeHint(QSize(0, row.sizeHint().height()))
            self.list.addItem(item)
            self.list.setItemWidget(item, row)
        self._rebuilding = False
        # Пересчитать высоты под фактическую ширину (перенос длинных имён)
        self.list.relayout_items()

    def _move_row(self, key, delta):
        keys = [self.list.item(i).data(Qt.UserRole) for i in range(self.list.count())]
        if key not in keys:
            return
        idx = keys.index(key)
        j = idx + delta
        if 0 <= j < len(keys):
            keys[idx], keys[j] = keys[j], keys[idx]
            self.window_logic.apply_order(keys)
            self._force_rebuild()

    # ========== ДЕЙСТВИЯ ==========

    def _activate(self, key):
        self.window_logic.activate_window_by_key(key)

    def _open_rename(self, key, title):
        RenameDialog(self.window_logic, key, title, self).exec()

    def _open_hotkey(self, key, title, current):
        HotkeyDialog(self.window_logic, key, title, current, self).exec()

    def _open_icon(self, key, title):
        IconDialog(self.window_logic, key, title, self).exec()

    def open_settings(self):
        SettingsDialog(self, self).exec()

    # ========== СИГНАЛЫ ЛОГИКИ ==========

    def _on_error(self, message):
        QMessageBox.critical(self, "Ошибка", message)

    def _on_hotkey(self, digit):
        window_data = self.window_logic.get_window_by_hotkey(digit)
        if not window_data:
            return
        if self.hotkey_manager.settings.get('feedback_enabled', True):
            overlay = FeedbackOverlay(digit, self.frameGeometry().center())
            overlay.show_briefly()
            self._overlay_ref = overlay
        self.window_logic.activate_window_by_key(window_data['key'])

    # ========== НАСТРОЙКИ ПРИЛОЖЕНИЯ ==========

    def _load_settings(self):
        try:
            if SETTINGS_FILE.exists():
                with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                merged = DEFAULT_SETTINGS.copy()
                merged.update(data)
                return merged
        except Exception as e:
            print(f"Ошибка загрузки settings.json: {e}")
        return DEFAULT_SETTINGS.copy()

    def _save_settings(self):
        try:
            ensure_config_dir()
            with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.app_settings, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Ошибка сохранения settings.json: {e}")

    # ========== ЗАКРЫТИЕ ==========

    def closeEvent(self, event):
        try:
            if self.auto_refresher:
                self.auto_refresher.stop()
            self.hotkey_manager.stop()
            self.capture.stop_all()
            self._mini_timer.stop()
            self._save_settings()
            if self.tray:
                self.tray.hide()
        except Exception as e:
            print(f"Ошибка при закрытии: {e}")
        event.accept()
        # Автовыход по закрытию окна отключён (из-за трея) — выходим явно
        QApplication.quit()
