from PyQt6.QtWidgets import QApplication

# Dark, high-contrast theme. Colours are centralised here so the whole app restyles from one place.
STYLESHEET = """
        QWidget {
            background: #0b1220;
            color: #e8eefc;
            font-family: "Segoe UI";
            font-size: 10pt;
        }
        QMainWindow, QDialog {
            background: #0b1220;
        }

        /* Sidebar */
        #sidebar {
            background: #0e1728;
            min-width: 236px;
            max-width: 236px;
            border-right: 1px solid #1d2b45;
        }
        #brand {
            color: #6ea8ff;
            font-size: 17pt;
            font-weight: 800;
            letter-spacing: 1px;
            padding: 22px 18px 10px 18px;
        }
        #nav {
            background: transparent;
            border: none;
            padding: 8px 10px;
            outline: 0;
        }
        #nav::item {
            padding: 11px 14px;
            margin: 2px 0;
            border-radius: 10px;
            color: #b8c6e4;
        }
        #nav::item:hover {
            background: #16233c;
            color: #e8eefc;
        }
        #nav::item:selected {
            background: qlineargradient(
                x1:0, y1:0, x2:1, y2:0,
                stop:0 #1f67d1, stop:1 #7757d9
            );
            color: #ffffff;
        }

        /* Page surface */
        #pageScroll, #pageScroll > QWidget > QWidget {
            background: #0b1220;
            border: none;
        }

        /* Headings rendered via rich-text labels inherit this colour */
        QLabel {
            background: transparent;
        }

        /* Cards */
        #card {
            background: #111c31;
            border: 1px solid #1f2d49;
            border-radius: 14px;
        }
        #cardTitle {
            color: #8fb7ff;
            font-size: 11pt;
            font-weight: 700;
        }
        #cardValue {
            color: #ffffff;
            font-size: 20pt;
            font-weight: 800;
        }

        /* Inputs */
        QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QSpinBox {
            background: #0f1a2e;
            border: 1px solid #263750;
            border-radius: 10px;
            padding: 9px 10px;
            selection-background-color: #1f67d1;
        }
        QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus {
            border: 1px solid #4b8bf0;
        }
        QTextEdit[readOnly="true"], QPlainTextEdit[readOnly="true"] {
            background: #0d1726;
            color: #d4ddf2;
        }

        QListWidget {
            background: #0f1a2e;
            border: 1px solid #263750;
            border-radius: 10px;
            padding: 6px;
            outline: 0;
        }
        QListWidget::item {
            padding: 8px;
            border-radius: 8px;
        }
        QListWidget::item:hover {
            background: #16233c;
        }
        QListWidget::item:selected {
            background: #1f67d1;
            color: #ffffff;
        }

        /* Buttons */
        QPushButton {
            background: #1f67d1;
            color: #ffffff;
            border: none;
            border-radius: 10px;
            padding: 10px 16px;
            font-weight: 700;
        }
        QPushButton:hover {
            background: #2f7bea;
        }
        QPushButton:pressed {
            background: #195bbd;
        }
        QPushButton:disabled {
            background: #24324c;
            color: #71809c;
        }
        QCheckBox {
            spacing: 8px;
        }
        QCheckBox::indicator {
            width: 18px;
            height: 18px;
            border-radius: 5px;
            border: 1px solid #3a4c6b;
            background: #0f1a2e;
        }
        QCheckBox::indicator:checked {
            background: #1f67d1;
            border: 1px solid #1f67d1;
        }

        /* Progress + status */
        QProgressBar {
            background: #0f1a2e;
            border: none;
            border-radius: 2px;
            max-height: 4px;
        }
        QProgressBar::chunk {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1f67d1, stop:1 #7757d9);
            border-radius: 2px;
        }
        QStatusBar {
            background: #0e1728;
            color: #9fb0d0;
            border-top: 1px solid #1d2b45;
        }
        QStatusBar::item {
            border: none;
        }

        /* Scrollbars */
        QScrollBar:vertical {
            background: transparent;
            width: 10px;
            margin: 2px;
        }
        QScrollBar::handle:vertical {
            background: #2a3a58;
            border-radius: 5px;
            min-height: 28px;
        }
        QScrollBar::handle:vertical:hover {
            background: #38507a;
        }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            height: 0;
        }
        QScrollBar:horizontal {
            background: transparent;
            height: 10px;
            margin: 2px;
        }
        QScrollBar::handle:horizontal {
            background: #2a3a58;
            border-radius: 5px;
            min-width: 28px;
        }
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
            width: 0;
        }
        """


def apply_theme(app: QApplication) -> None:
    app.setStyle("Fusion")
    app.setStyleSheet(STYLESHEET)
