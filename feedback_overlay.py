"""
Кратковременный оверлей обратной связи по хоткею: круг с цифрой по центру панели.
Полупрозрачное frameless-окно, не перехватывает мышь, само закрывается через ~0.8с.
"""

from PySide6.QtCore import Qt, QTimer, QRectF
from PySide6.QtGui import QPainter, QColor, QPen, QFont
from PySide6.QtWidgets import QWidget


class FeedbackOverlay(QWidget):
    SIZE = 84

    def __init__(self, number, center_point):
        super().__init__(None)
        self.number = str(number)
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
            | Qt.WindowTransparentForInput
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setFixedSize(self.SIZE, self.SIZE)
        self.move(int(center_point.x() - self.SIZE / 2),
                  int(center_point.y() - self.SIZE / 2))

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = QRectF(6, 6, self.SIZE - 12, self.SIZE - 12)
        painter.setBrush(QColor(79, 107, 237, 220))   # индиго-акцент
        painter.setPen(QPen(QColor(255, 255, 255, 230), 3))
        painter.drawEllipse(rect)

        painter.setPen(QColor(255, 255, 255))
        font = QFont("Segoe UI", 26, QFont.Bold)
        painter.setFont(font)
        painter.drawText(self.rect(), Qt.AlignCenter, self.number)

    def show_briefly(self, ms=800):
        self.show()
        QTimer.singleShot(ms, self.close)
