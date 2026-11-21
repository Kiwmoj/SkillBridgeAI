from collections.abc import Callable

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget


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
    def __init__(self, title: str) -> None:
        super().__init__()
        self.setObjectName("card")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(6)
        heading = QLabel(title)
        heading.setObjectName("cardTitle")
        layout.addWidget(heading)
        self.body = QVBoxLayout()
        layout.addLayout(self.body)
