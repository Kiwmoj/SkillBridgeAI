from PyQt6.QtWidgets import QApplication

STYLESHEET = """
        QWidget {
            background: #0b1220;
            color: #edf4ff;
            font-family: "Segoe UI";
            font-size: 10pt;
        }
        #sidebar {
            background: #101a2d;
            min-width: 220px;
            max-width: 220px;
            border-right: 1px solid #26334b;
        }
        #brand {
            color: #63a4ff;
            font-size: 16pt;
            font-weight: bold;
            padding: 18px;
        }
        #nav {
            background: transparent;
            border: none;
            padding: 8px;
        }
        #nav::item {
            padding: 12px;
            border-radius: 8px;
        }
        #nav::item:selected {
            background: qlineargradient(
                x1:0, y1:0, x2:1, y2:0,
                stop:0 #1f67d1, stop:1 #7757d9
            );
        }
        QLineEdit, QTextEdit {
            background: #131d31;
            border: 1px solid #2b3b57;
            border-radius: 8px;
            padding: 8px;
        }
        QListWidget {
            background: #131d31;
            border: 1px solid #2b3b57;
            border-radius: 8px;
            padding: 6px;
        }
        QPushButton {
            background: #1f67d1;
            border: none;
            border-radius: 8px;
            padding: 9px 14px;
            font-weight: bold;
        }
        QPushButton:hover {
            background: #347fe8;
        }
        QProgressBar {
            background: #131d31;
            border: none;
            max-height: 4px;
        }
        #cardTitle {
            color: #82b4ff;
            font-size: 12pt;
            font-weight: bold;
        }
        """


def apply_theme(app: QApplication) -> None:
    app.setStyle("Fusion")
    app.setStyleSheet(STYLESHEET)
