from PyQt6.QtWidgets import QApplication

# Professional "slate + blue" dark theme. Depth comes from subtle surfaces, a selected-nav indicator,
# and real drop shadows on cards (see components/widgets.py) rather than heavy gradients.
PRIMARY = "#3b82f6"

STYLESHEET = """
        QWidget {
            background: #0f172a;
            color: #e2e8f0;
            font-family: "Segoe UI";
            font-size: 10pt;
        }
        QMainWindow, QDialog {
            background: #0f172a;
        }

        /* Sidebar */
        #sidebar {
            background: #111c34;
            min-width: 248px;
            max-width: 248px;
            border-right: 1px solid #1e293b;
        }
        #brand {
            color: #f1f5f9;
            font-size: 17pt;
            font-weight: 800;
            letter-spacing: 0.5px;
            padding: 24px 20px 4px 20px;
        }
        #brandTag {
            color: #64748b;
            font-size: 8.5pt;
            font-weight: 600;
            letter-spacing: 2px;
            padding: 0 20px 14px 20px;
        }
        #nav {
            background: transparent;
            border: none;
            padding: 8px 12px;
            outline: 0;
        }
        #nav::item {
            padding: 11px 14px;
            margin: 2px 0;
            border-radius: 9px;
            border-left: 3px solid transparent;
            color: #94a3b8;
        }
        #nav::item:hover {
            background: #182542;
            color: #e2e8f0;
        }
        #nav::item:selected {
            background: #16233f;
            border-left: 3px solid #3b82f6;
            color: #ffffff;
        }

        /* Page surface */
        #pageScroll {
            background: #0f172a;
            border: none;
        }
        QLabel {
            background: transparent;
        }
        #pageTitle {
            font-size: 18pt;
            font-weight: 800;
            color: #f8fafc;
        }
        #pageSubtitle {
            color: #94a3b8;
            font-size: 10pt;
        }

        /* Cards (raised surfaces; shadow added in code) */
        #card {
            background: #1e293b;
            border: 1px solid #334155;
            border-radius: 14px;
        }
        #cardTitle {
            color: #94a3b8;
            font-size: 9.5pt;
            font-weight: 700;
            letter-spacing: 0.3px;
        }
        #cardValue {
            color: #f8fafc;
            font-size: 26pt;
            font-weight: 800;
        }
        #authCard {
            background: #1e293b;
            border: 1px solid #334155;
            border-radius: 16px;
        }

        /* Inputs */
        QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QSpinBox {
            background: #0f1a30;
            border: 1px solid #334155;
            border-radius: 9px;
            padding: 9px 11px;
            selection-background-color: #3b82f6;
        }
        QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus {
            border: 1px solid #3b82f6;
        }
        QTextEdit[readOnly="true"], QPlainTextEdit[readOnly="true"] {
            background: #16233f;
            color: #cbd5e1;
        }

        QListWidget {
            background: #0f1a30;
            border: 1px solid #334155;
            border-radius: 11px;
            padding: 6px;
            outline: 0;
        }
        QListWidget::item {
            padding: 9px;
            border-radius: 7px;
        }
        QListWidget::item:hover {
            background: #182542;
        }
        QListWidget::item:selected {
            background: #3b82f6;
            color: #ffffff;
        }

        /* Buttons (flat, professional) */
        QPushButton {
            background: #3b82f6;
            color: #ffffff;
            border: none;
            border-radius: 9px;
            padding: 10px 18px;
            font-weight: 600;
        }
        QPushButton:hover {
            background: #60a5fa;
        }
        QPushButton:pressed {
            background: #2563eb;
        }
        QPushButton:disabled {
            background: #273449;
            color: #64748b;
        }
        QCheckBox {
            spacing: 8px;
            color: #cbd5e1;
        }
        QCheckBox::indicator {
            width: 18px;
            height: 18px;
            border-radius: 5px;
            border: 1px solid #475569;
            background: #0f1a30;
        }
        QCheckBox::indicator:checked {
            background: #3b82f6;
            border: 1px solid #3b82f6;
        }

        /* Progress + status */
        QProgressBar {
            background: #0f1a30;
            border: none;
            border-radius: 2px;
            max-height: 4px;
        }
        QProgressBar::chunk {
            background: #3b82f6;
            border-radius: 2px;
        }
        QStatusBar {
            background: #111c34;
            color: #94a3b8;
            border-top: 1px solid #1e293b;
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
            background: #334155;
            border-radius: 5px;
            min-height: 30px;
        }
        QScrollBar::handle:vertical:hover {
            background: #475569;
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
            background: #334155;
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
