import sys
import os
import datetime
import subprocess
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, QFileDialog, QMessageBox, 
    QHBoxLayout, QComboBox, QCheckBox, QFrame
)
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt

from apps.media_converter.converters.conversion import ImageEnhancerLogic
from apps.media_converter.ui.ui_theme import (
    get_app_colors,
    get_button_style,
    get_drop_label_style,
    get_soft_button_style,
    get_remove_button_style,
    get_convert_button_style,
    apply_window_theme,
    make_card_container,
)

class ImageDropLabel(QLabel):
    def __init__(self, on_image_dropped, parent=None):
        super().__init__(parent)
        self.main_window = parent
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setText("Arrastra aquí una imagen")
        self.setStyleSheet(f"{get_drop_label_style()}min-height: 180px;")
        self.setAcceptDrops(True)
        self.image_path = None
        self.on_image_dropped = on_image_dropped
        self.allowed_extensions = ('.png', '.jpg', '.jpeg', '.bmp', '.webp', '.tiff')

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            valid = any(
                url.toLocalFile().lower().endswith(self.allowed_extensions)
                for url in event.mimeData().urls()
            )
            if valid:
                event.acceptProposedAction()
            else:
                event.ignore()
        else:
            event.ignore()

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            valid_files = [
                url.toLocalFile()
                for url in event.mimeData().urls()
                if url.toLocalFile().lower().endswith(self.allowed_extensions)
            ]
            invalid_count = len(event.mimeData().urls()) - len(valid_files)
            if valid_files:
                self.on_image_dropped(valid_files)
            if invalid_count > 0:
                QMessageBox.warning(self, "Formato no soportado", f"{invalid_count} archivo(s) no son imágenes válidas y fueron ignorados.")
        else:
            event.ignore()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if hasattr(self.main_window, 'open_batch_manager'):
                self.main_window.open_batch_manager()


class QualityEnhancerUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Mejorador de Calidad con IA (4x)")
        self.setGeometry(100, 100, 480, 560)
        apply_window_theme(self)
        self._colors = get_app_colors()
        
        self.image_path = None
        self.batch_files = []
        
        self.init_ui()

    def init_ui(self):
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(26, 24, 26, 24)
        card, card_layout = make_card_container()

        top_layout = QHBoxLayout()
        back_btn = QPushButton("← Volver al Hub")
        back_btn.setFixedWidth(130)
        back_btn.clicked.connect(self.go_back)
        back_btn.setStyleSheet(get_soft_button_style())
        top_layout.addWidget(back_btn)
        top_layout.addStretch()
        card_layout.addLayout(top_layout)

        self.label = QLabel("Selecciona o arrastra una imagen para mejorar su calidad")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet(f"color: {self._colors['text_main']}; font-size: 13pt; font-weight:600;")
        self.label.setWordWrap(True)
        card_layout.addWidget(self.label)

        self.info_label = QLabel("La imagen aumentará su resolución utilizando Inteligencia Artificial (Real-ESRGAN).")
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.info_label.setStyleSheet(f"color: {self._colors['text_muted']}; font-size: 10pt;")
        self.info_label.setWordWrap(True)
        card_layout.addWidget(self.info_label)

        # Settings Frame
        settings_frame = QFrame()
        settings_frame.setStyleSheet(f"background: {self._colors['card']}; border-radius: 8px; margin-top: 10px; margin-bottom: 10px;")
        settings_layout = QVBoxLayout(settings_frame)
        settings_layout.setContentsMargins(15, 15, 15, 15)
        
        # Model Selection
        model_layout = QHBoxLayout()
        model_label = QLabel("Tipo de Imagen:")
        model_label.setStyleSheet(f"color: {self._colors['text_muted']}; font-weight: bold;")
        self.combo_model = QComboBox()
        self.combo_model.addItems(["Foto Real (Estándar)", "Ilustración / Anime", "Retrato Detallado"])
        self.combo_model.setStyleSheet(f"background: {self._colors['bg']}; color: {self._colors['text_main']}; border: 1px solid {self._colors['border']}; border-radius: 4px; padding: 4px;")
        model_layout.addWidget(model_label)
        model_layout.addWidget(self.combo_model)
        settings_layout.addLayout(model_layout)
        
        # Scale and TTA Selection
        scale_layout = QHBoxLayout()
        scale_label = QLabel("Escala:")
        scale_label.setStyleSheet(f"color: {self._colors['text_muted']}; font-weight: bold;")
        self.combo_scale = QComboBox()
        self.combo_scale.addItems(["2x", "3x", "4x"])
        self.combo_scale.setCurrentText("4x")
        self.combo_scale.setStyleSheet(f"background: {self._colors['bg']}; color: {self._colors['text_main']}; border: 1px solid {self._colors['border']}; border-radius: 4px; padding: 4px;")
        scale_layout.addWidget(scale_label)
        scale_layout.addWidget(self.combo_scale)
        scale_layout.addStretch()
        
        self.check_tta = QCheckBox("Modo Ultra Detalle (TTA - Lento)")
        self.check_tta.setStyleSheet(f"color: {self._colors['text_main']}; font-weight: bold;")
        self.check_tta.setToolTip("Procesa la imagen 8 veces para eliminar ruido y bordes sierra. Ideal para resultados perfectos.")
        scale_layout.addWidget(self.check_tta)
        settings_layout.addLayout(scale_layout)
        
        card_layout.addWidget(settings_frame)

        self.image_label = ImageDropLabel(self.on_image_dropped, self)
        card_layout.addWidget(self.image_label)

        # Botones de Acción
        self.select_button = QPushButton("Seleccionar Imagen")
        self.select_button.clicked.connect(self.select_image)
        self.select_button.setStyleSheet(get_button_style())
        card_layout.addWidget(self.select_button)

        self.select_folder_button = QPushButton("Seleccionar Carpeta")
        self.select_folder_button.clicked.connect(self.select_folder)
        self.select_folder_button.setStyleSheet(get_button_style())
        card_layout.addWidget(self.select_folder_button)

        self.remove_button = QPushButton("Quitar todo")
        self.remove_button.clicked.connect(self.remove_image)
        self.remove_button.setEnabled(False)
        self.remove_button.setStyleSheet(get_remove_button_style())
        card_layout.addWidget(self.remove_button)

        self.convert_button = QPushButton("Mejorar Calidad")
        self.convert_button.clicked.connect(self.convert_image)
        self.convert_button.setEnabled(False)
        self.convert_button.setStyleSheet(get_convert_button_style())
        card_layout.addWidget(self.convert_button)

        self.layout.addWidget(card)
        self.setLayout(self.layout)

    def open_batch_manager(self):
        if self.batch_files:
            from core.ui.batch_dialog import BatchDialog
            from PyQt6.QtWidgets import QDialog
            dialog = BatchDialog(self.batch_files, self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self.batch_files = dialog.get_files()
                if len(self.batch_files) == 0:
                    self.remove_image()
                elif len(self.batch_files) == 1:
                    self.image_label.clear()
                    self.image_label.setText(os.path.basename(self.batch_files[0]))
                else:
                    self.image_label.clear()
                    self.image_label.setText(f"{len(self.batch_files)} imágenes seleccionadas")

    def go_back(self):
        from core.ui.hub_window import HubWindow
        self.hub_window = HubWindow()
        self.hub_window.show()
        self.close()

    def select_image(self):
        file_dialog = QFileDialog()
        file_paths, _ = file_dialog.getOpenFileNames(self, "Seleccionar Imágenes", "", "Imágenes (*.png *.jpg *.jpeg *.bmp *.webp *.tiff)")
        if file_paths:
            self.image_path = None
            for fp in file_paths:
                if fp not in self.batch_files:
                    self.batch_files.append(fp)
            self._refresh_label()

    def on_image_dropped(self, file_paths):
        self.image_path = None
        for fp in file_paths:
            if fp not in self.batch_files:
                self.batch_files.append(fp)
        self._refresh_label()

    def _refresh_label(self):
        if not self.batch_files:
            return
        if len(self.batch_files) == 1:
            fp = self.batch_files[0]
            pixmap = QPixmap(fp)
            self.image_label.setPixmap(pixmap.scaled(250, 250, Qt.AspectRatioMode.KeepAspectRatio))
        else:
            self.image_label.clear()
            self.image_label.setText(f"{len(self.batch_files)} imágenes seleccionadas")
        self.convert_button.setEnabled(True)
        self.remove_button.setEnabled(True)

    def select_folder(self):
        folder_path = QFileDialog.getExistingDirectory(self, "Seleccionar Carpeta de Imágenes")
        if not folder_path:
            return
        valid_exts = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff"}
        self.image_path = None
        for name in os.listdir(folder_path):
            file_path = os.path.join(folder_path, name)
            if os.path.isfile(file_path) and os.path.splitext(name)[1].lower() in valid_exts:
                if file_path not in self.batch_files:
                    self.batch_files.append(file_path)
        if not self.batch_files:
            QMessageBox.warning(self, "Sin archivos", "No se encontraron imágenes compatibles en la carpeta.")
            return
        self._refresh_label()

    def remove_image(self):
        self.image_path = None
        self.batch_files = []
        self.image_label.clear()
        self.image_label.setText("Arrastra aquí una imagen")
        self.convert_button.setEnabled(False)
        self.remove_button.setEnabled(False)

    def choose_output_folder(self):
        return QFileDialog.getExistingDirectory(self, "Seleccionar carpeta de salida")

    def convert_image(self):
        output_dir = self.choose_output_folder()
        if not output_dir:
            return

        model_map = {
            "Foto Real (Estándar)": "realesrgan-x4plus",
            "Ilustración / Anime": "realesrgan-x4plus-anime",
            "Retrato Detallado": "realesrnet-x4plus"
        }
        selected_model = model_map.get(self.combo_model.currentText(), "realesrgan-x4plus")
        scale = int(self.combo_scale.currentText().replace("x", ""))
        use_tta = self.check_tta.isChecked()

        if self.batch_files:
            if len(self.batch_files) > 5:
                folder_name = "Mejorado_Masivo_" + datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                output_dir = os.path.join(output_dir, folder_name)
                if not os.path.exists(output_dir):
                    os.makedirs(output_dir)
                    
            converted = 0
            failed = 0
            total = len(self.batch_files)
            was_cancelled = False
            
            from core.ui.advanced_progress import AdvancedProgressDialog
            progress = AdvancedProgressDialog("Mejorando calidad...", total, self)
            progress.show()
            QApplication.processEvents()

            try:
                for idx, file_path in enumerate(self.batch_files, start=1):
                    while progress.is_paused and not progress.is_cancelled:
                        import time
                        time.sleep(0.1)
                        QApplication.processEvents()
                        
                    if progress.is_cancelled:
                        was_cancelled = True
                        break
                        
                    nombre = os.path.splitext(os.path.basename(file_path))[0]
                    ext = os.path.splitext(file_path)[1]
                    ruta_destino = os.path.join(output_dir, f"{nombre}_{scale}x{ext}")
                    
                    resultado = ImageEnhancerLogic.mejorar_calidad(
                        ruta_origen=file_path,
                        ruta_destino=ruta_destino,
                        model_name=selected_model,
                        scale=scale,
                        use_tta=use_tta
                    )
                    
                    if str(resultado).startswith("✅"):
                        converted += 1
                    else:
                        failed += 1
                        
                    progress.setLabelText(f"Mejorando calidad... ({idx}/{total})")
                    progress.setValue(idx)
                    QApplication.processEvents()
            finally:
                progress.close()

            if was_cancelled:
                QMessageBox.warning(
                    self,
                    "Conversión Cancelada",
                    f"Proceso cancelado por el usuario.\nSe completaron {converted} imágenes de {total} antes de cancelar."
                )
            else:
                QMessageBox.information(
                    self,
                    "Proceso Masivo",
                    f"Procesados con éxito: {converted}\nFallidos: {failed}",
                )
            try:
                from core.ui.result_viewer import ResultViewerDialog
                viewer = ResultViewerDialog(output_dir, self)
                viewer.exec()
            except Exception:
                try:
                    os.startfile(output_dir)
                except AttributeError:
                    import subprocess
                    subprocess.Popen(["xdg-open", output_dir])
            return

        if not self.image_path:
            QMessageBox.warning(self, "Advertencia", "Por favor selecciona una imagen primero.")
            return

        nombre = os.path.splitext(os.path.basename(self.image_path))[0]
        ext = os.path.splitext(self.image_path)[1]
        ruta_destino = os.path.join(output_dir, f"{nombre}_{scale}x{ext}")

        from core.ui.advanced_progress import AdvancedProgressDialog
        progress = AdvancedProgressDialog("Mejorando calidad...", 1, self)
        progress.show()
        QApplication.processEvents()
        try:
            resultado = ImageEnhancerLogic.mejorar_calidad(
                ruta_origen=self.image_path,
                ruta_destino=ruta_destino,
                model_name=selected_model,
                scale=scale,
                use_tta=use_tta
            )
        finally:
            progress.close()

        if "Error" in resultado:
            QMessageBox.warning(self, "Error", resultado)
        else:
            QMessageBox.information(self, "Proceso Completado", resultado)
            try:
                os.startfile(output_dir)
            except AttributeError:
                subprocess.Popen(['xdg-open', output_dir])

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = QualityEnhancerUI()
    window.show()
    sys.exit(app.exec())
