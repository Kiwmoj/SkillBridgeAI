from collections.abc import Callable

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QBoxLayout,
    QGraphicsDropShadowEffect,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


def elevate(widget: QWidget, blur: int = 24, y_offset: int = 6, alpha: int = 150) -> None:
    """Attach a soft drop shadow so a surface reads as raised (a '3D' card/button)."""
    shadow = QGraphicsDropShadowEffect(widget)
    shadow.setBlurRadius(blur)
    shadow.setXOffset(0)
    shadow.setYOffset(y_offset)
    shadow.setColor(QColor(0, 0, 0, alpha))
    widget.setGraphicsEffect(shadow)


def text_label(value: str) -> QLabel:
    label = QLabel(value)
    label.setTextFormat(Qt.TextFormat.PlainText)
    label.setWordWrap(True)
    return label


def add_action(layout: QBoxLayout, label: str, action: Callable[..., object]) -> QPushButton:
    button = QPushButton(label)
    button.clicked.connect(action)
    layout.addWidget(button)
    return button


class Card(QWidget):
    def __init__(self, title: str, accent: str | None = None) -> None:
        super().__init__()
        self.setObjectName("card")
        elevate(self)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(6)
        heading = QLabel(title)
        heading.setObjectName("cardTitle")
        if accent:
            heading.setStyleSheet(f"color: {accent}; font-size: 11pt; font-weight: 700;")
        layout.addWidget(heading)
        self.body = QVBoxLayout()
        layout.addLayout(self.body)
