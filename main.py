import sys
import traceback
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton,
    QVBoxLayout, QHBoxLayout, QMessageBox
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon, QPixmap
import os


def global_exception_handler(exc_type, exc_value, exc_traceback):
    err_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    print(err_msg)
    if QApplication.instance():
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Critical)
        msg.setWindowTitle("Error Fatal")
        msg.setText("Ocurrió un error inesperado.")
        msg.setDetailedText(err_msg)
        msg.exec()


sys.excepthook = global_exception_handler


def get_asset(filename):
    base = os.path.dirname(__file__)
    return os.path.join(base, "assets", "hub", filename)


class ImageToolsLauncher(QWidget):
    """Mini-launcher que muestra las 3 herramientas de imagen con IA."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Image Tools — Media Hub")
        self.setFixedSize(600, 300)
        icon_path = get_asset("Media-Hub.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        self._init_ui()

    def _init_ui(self):
        self.setStyleSheet("background:#1E1E2E; color:#E4E0DC;")
        root = QVBoxLayout(self)
        root.setContentsMargins(30, 24, 30, 24)
        root.setSpacing(20)

        title = QLabel("Image Tools")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size:22pt; font-weight:700; color:#E4E0DC;")
        root.addWidget(title)

        row = QHBoxLayout()
        row.setSpacing(20)

        tools = [
            ("backgrounderaser.webp", "Background Eraser", self.open_bg_remover),
            ("quality.webp",          "Quality Enhancer",  self.open_quality_enhancer),
            ("bulkwatermark.webp",    "Bulk Watermark",    self.open_watermark),
        ]

        for icon_file, label_text, handler in tools:
            col = QVBoxLayout()
            col.setSpacing(8)

            btn = QPushButton()
            icon_path = get_asset(icon_file)
            if os.path.exists(icon_path):
                btn.setIcon(QIcon(QPixmap(icon_path)))
            btn.setIconSize(QSize(100, 100))
            btn.setFixedSize(130, 130)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(
                "QPushButton{background:#2B2B3B;border-radius:16px;border:1px solid #3A3A52;}"
                "QPushButton:hover{background:#35354A;}"
            )
            btn.clicked.connect(handler)

            lbl = QLabel(label_text)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet("color:#9898B8; font-weight:600;")

            col.addWidget(btn, alignment=Qt.AlignmentFlag.AlignCenter)
            col.addWidget(lbl)
            row.addLayout(col)

        root.addLayout(row)

    def open_bg_remover(self):
        from apps.media_converter.ui.bg_remover import BackgroundRemoverUI
        self._open(BackgroundRemoverUI)

    def open_quality_enhancer(self):
        from apps.media_converter.ui.quality_enhancer import QualityEnhancerUI
        self._open(QualityEnhancerUI)

    def open_watermark(self):
        from apps.media_converter.ui.watermark_tool import WatermarkToolUI
        self._open(WatermarkToolUI)

    def _open(self, WindowClass):
        self.sub = WindowClass()
        self.sub.show()
        self.hide()


def main():
    app = QApplication(sys.argv)
    window = ImageToolsLauncher()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
