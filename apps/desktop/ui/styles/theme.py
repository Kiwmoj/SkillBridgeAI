from PyQt6.QtWidgets import QApplication

# Dark, high-contrast, "elevated" theme. A solid base avoids gradient banding across nested widgets;
# depth comes from gradients on cards/buttons/sidebar plus real drop shadows (see components/widgets.py).
STYLESHEET = """
        QWidget {
            background: #0a111f;
            color: #e8eefc;
            font-family: "Segoe UI";
            font-size: 10pt;
        }
        QMainWindow, QDialog {
            background: #0a111f;
        }

        /* Sidebar */
        #sidebar {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #12203a, stop:1 #0c1526);
            min-width: 244px;
            max-width: 244px;
            border-right: 1px solid #1d2b45;
        }
        #brand {
            color: #7db1ff;
            font-size: 18pt;
            font-weight: 800;
            letter-spacing: 1px;
            padding: 24px 18px 12px 18px;
        }
        #nav {
            background: transparent;
            border: none;
            padding: 8px 10px;
            outline: 0;
        }
        #nav::item {
            padding: 12px 14px;
            margin: 3px 0;
            border-radius: 11px;
            color: #b8c6e4;
        }
        #nav::item:hover {
            background: #1a2a47;
            color: #ffffff;
        }
        #nav::item:selected {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2b74e3, stop:1 #7f5be0);
            color: #ffffff;
        }

        /* Page surface */
        #pageScroll {
            background: #0a111f;
            border: none;
        }

        QLabel {
            background: transparent;
        }
        #pageTitle {
            font-size: 19pt;
            font-weight: 800;
            color: #ffffff;
        }
        #pageSubtitle {
            color: #91a2c4;
        }

        /* Cards (raised surfaces; drop shadow added in code) */
        #card {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #17243d, stop:1 #111c31);
            border: 1px solid #243655;
            border-radius: 16px;
        }
        #cardTitle {
            color: #9cc0ff;
            font-size: 11pt;
            font-weight: 700;
        }
        #cardValue {
            color: #ffffff;
            font-size: 26pt;
            font-weight: 800;
        }

        /* Inputs (inset look + focus glow) */
        QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QSpinBox {
            background: #0c1526;
            border: 1px solid #263750;
            border-radius: 10px;
            padding: 9px 11px;
            selection-background-color: #2b74e3;
        }
        QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus {
            border: 1px solid #5a97f5;
        }
        QTextEdit[readOnly="true"], QPlainTextEdit[readOnly="true"] {
            background: #0b1322;
            color: #d4ddf2;
        }

        QListWidget {
            background: #0c1526;
            border: 1px solid #263750;
            border-radius: 12px;
            padding: 6px;
            outline: 0;
        }
        QListWidget::item {
            padding: 9px;
            border-radius: 8px;
        }
        QListWidget::item:hover {
            background: #16233c;
        }
        QListWidget::item:selected {
            background: #2b74e3;
            color: #ffffff;
        }

        /* Buttons (raised gradient; sinks on press) */
        QPushButton {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #3a86f0, stop:1 #2567cf);
            color: #ffffff;
            border: none;
            border-radius: 11px;
            padding: 10px 18px;
            font-weight: 700;
        }
        QPushButton:hover {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #4e97ff, stop:1 #2f74e3);
        }
        QPushButton:pressed {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #2256b4, stop:1 #1c4ea3);
            padding-top: 11px;
            padding-bottom: 9px;
        }
        QPushButton:disabled {
            background: #223049;
            color: #6c7b98;
        }
        QCheckBox {
            spacing: 8px;
        }
        QCheckBox::indicator {
            width: 18px;
            height: 18px;
            border-radius: 5px;
            border: 1px solid #3a4c6b;
            background: #0c1526;
        }
        QCheckBox::indicator:checked {
            background: #2b74e3;
            border: 1px solid #2b74e3;
        }

        /* Progress + status */
        QProgressBar {
            background: #0c1526;
            border: none;
            border-radius: 3px;
            max-height: 5px;
        }
        QProgressBar::chunk {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2b74e3, stop:1 #7f5be0);
            border-radius: 3px;
        }
        QStatusBar {
            background: #0c1526;
            color: #9fb0d0;
            border-top: 1px solid #1d2b45;
        }
        QStatusBar::item {
            border: none;
        }

        /* Scrollbars */
        QScrollBar:vertical {
            background: transparent;
            width: 11px;
            margin: 2px;
        }
        QScrollBar::handle:vertical {
            background: #2a3a58;
            border-radius: 5px;
            min-height: 30px;
        }
        QScrollBar::handle:vertical:hover {
            background: #3b537a;
        }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            height: 0;
        }
        QScrollBar:horizontal {
            background: transparent;
            height: 11px;
            margin: 2px;
        }
        QScrollBar::handle:horizontal {
            background: #2a3a58;
            border-radius: 5px;
            min-width: 30px;
        }
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
            width: 0;
        }
        """


def apply_theme(app: QApplication) -> None:
    app.setStyle("Fusion")
    app.setStyleSheet(STYLESHEET)
