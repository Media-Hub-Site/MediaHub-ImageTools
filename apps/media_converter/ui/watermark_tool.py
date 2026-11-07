import sys
import os
import datetime
import subprocess
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, QFileDialog, QMessageBox, 
    QHBoxLayout, QComboBox, QFrame, QSpinBox
)
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt

from apps.media_converter.converters.conversion import WatermarkLogic
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

class MediaDropLabel(QLabel):
    def __init__(self, on_media_dropped, parent=None):
        super().__init__(parent)
        self.main_window = parent
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setText("Arrastra aquí tus Fotos o Videos")
        self.setStyleSheet(f"{get_drop_label_style()}min-height: 120px;")
        self.setAcceptDrops(True)
        self.on_media_dropped = on_media_dropped
        self.allowed_extensions = ('.mp4', '.mkv', '.avi', '.mov', '.webm', '.flv', '.png', '.jpg', '.jpeg', '.bmp', '.webp', '.tiff')

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
                self.on_media_dropped(valid_files)
            if invalid_count > 0:
                QMessageBox.warning(self, "Formato no soportado", f"{invalid_count} archivo(s) no son válidos y fueron ignorados.")
        else:
            event.ignore()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if hasattr(self.main_window, 'open_batch_manager'):
                self.main_window.open_batch_manager()


class WatermarkToolUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Marca de Agua Masiva")
        self.setGeometry(100, 100, 480, 600)
        apply_window_theme(self)
        self._colors = get_app_colors()
        
        self.batch_files = []
        self.watermark_path = None
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

        self.label = QLabel("Aplica tu Logo (Marca de Agua) a Fotos y Videos")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet(f"color: {{self._colors['text_main']}}; font-size: 13pt; font-weight:600;")
        self.label.setWordWrap(True)
        card_layout.addWidget(self.label)

        # Settings Frame
        settings_frame = QFrame()
        settings_frame.setStyleSheet(f"background: {{self._colors['card']}}; border-radius: 8px; margin-top: 10px; margin-bottom: 10px;")
        settings_layout = QVBoxLayout(settings_frame)
        settings_layout.setContentsMargins(15, 15, 15, 15)
        
        # Watermark Selection
        wm_layout = QHBoxLayout()
        wm_label = QLabel("Logo (.png):")
        wm_label.setStyleSheet(f"color: {{self._colors['text_muted']}}; font-weight: bold;")
        self.btn_wm = QPushButton("Examinar...")
        self.btn_wm.setStyleSheet(get_button_style())
        self.btn_wm.clicked.connect(self.select_watermark)
        self.lbl_wm_name = QLabel("Ninguno")
        self.lbl_wm_name.setStyleSheet(f"color: {{self._colors['text_main']}};")
        wm_layout.addWidget(wm_label)
        wm_layout.addWidget(self.btn_wm)
        wm_layout.addWidget(self.lbl_wm_name)
        wm_layout.addStretch()
        settings_layout.addLayout(wm_layout)
        
        # Position Selection
        pos_layout = QHBoxLayout()
        pos_label = QLabel("Posición:")
        pos_label.setStyleSheet(f"color: {{self._colors['text_muted']}}; font-weight: bold;")
        self.combo_pos = QComboBox()
        self.combo_pos.addItems(["Abajo Derecha", "Abajo Izquierda", "Arriba Derecha", "Arriba Izquierda", "Centro"])
        self.combo_pos.setStyleSheet(f"background: {{self._colors['bg']}}; color: {{self._colors['text_main']}}; border: 1px solid {{self._colors['border']}}; border-radius: 4px; padding: 4px;")
        pos_layout.addWidget(pos_label)
        pos_layout.addWidget(self.combo_pos)
        settings_layout.addLayout(pos_layout)
        
        # Opacity Selection
        opc_layout = QHBoxLayout()
        opc_label = QLabel("Opacidad (%):")
        opc_label.setStyleSheet(f"color: {{self._colors['text_muted']}}; font-weight: bold;")
        self.spin_opc = QSpinBox()
        self.spin_opc.setRange(10, 100)
        self.spin_opc.setValue(100)
        self.spin_opc.setStyleSheet(f"background: {{self._colors['bg']}}; color: {{self._colors['text_main']}}; border: 1px solid {{self._colors['border']}}; padding: 4px;")
        opc_layout.addWidget(opc_label)
        opc_layout.addWidget(self.spin_opc)
        opc_layout.addStretch()
        settings_layout.addLayout(opc_layout)
        
        card_layout.addWidget(settings_frame)

        self.media_label = MediaDropLabel(self.on_media_dropped, self)
        card_layout.addWidget(self.media_label)

        # Botones de Acción
        self.select_button = QPushButton("Seleccionar Archivos")
        self.select_button.clicked.connect(self.select_media)
        self.select_button.setStyleSheet(get_button_style())
        card_layout.addWidget(self.select_button)

        self.remove_button = QPushButton("Quitar todo")
        self.remove_button.clicked.connect(self.remove_media)
        self.remove_button.setEnabled(False)
        self.remove_button.setStyleSheet(get_remove_button_style())
        card_layout.addWidget(self.remove_button)

        self.convert_button = QPushButton("Aplicar Marca de Agua")
        self.convert_button.clicked.connect(self.apply_watermark)
        self.convert_button.setEnabled(False)
        self.convert_button.setStyleSheet(get_convert_button_style())
        card_layout.addWidget(self.convert_button)

        self.layout.addWidget(card)
        self.setLayout(self.layout)

    def select_watermark(self):
        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getOpenFileName(self, "Seleccionar Logo PNG", "", "Imágenes PNG (*.png)")
        if file_path:
            self.watermark_path = file_path
            self.lbl_wm_name.setText(os.path.basename(file_path))
            self._refresh_convert_btn()

    def open_batch_manager(self):
        if self.batch_files:
            from core.ui.batch_dialog import BatchDialog
            from PyQt6.QtWidgets import QDialog
            dialog = BatchDialog(self.batch_files, self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self.batch_files = dialog.get_files()
                if len(self.batch_files) == 0:
                    self.remove_media()
                elif len(self.batch_files) == 1:
                    self.media_label.clear()
                    self.media_label.setText(os.path.basename(self.batch_files[0]))
                else:
                    self.media_label.clear()
                    self.media_label.setText(f"{len(self.batch_files)} archivos seleccionados")
            self._refresh_convert_btn()

    def go_back(self):
        from core.ui.hub_window import HubWindow
        self.hub_window = HubWindow()
        self.hub_window.show()
        self.close()

    def select_media(self):
        file_dialog = QFileDialog()
        file_paths, _ = file_dialog.getOpenFileNames(self, "Seleccionar Multimedia", "", "Multimedia (*.mp4 *.mkv *.avi *.mov *.png *.jpg *.jpeg *.webp)")
        if file_paths:
            for fp in file_paths:
                if fp not in self.batch_files:
                    self.batch_files.append(fp)
            self._refresh_label()

    def on_media_dropped(self, file_paths):
        for fp in file_paths:
            if fp not in self.batch_files:
                self.batch_files.append(fp)
        self._refresh_label()

    def _refresh_label(self):
        if not self.batch_files:
            return
        if len(self.batch_files) == 1:
            self.media_label.clear()
            self.media_label.setText(os.path.basename(self.batch_files[0]))
        else:
            self.media_label.clear()
            self.media_label.setText(f"{len(self.batch_files)} archivos seleccionados")
        self.remove_button.setEnabled(True)
        self._refresh_convert_btn()

    def _refresh_convert_btn(self):
        self.convert_button.setEnabled(bool(self.batch_files and self.watermark_path))

    def remove_media(self):
        self.batch_files = []
        self.media_label.clear()
        self.media_label.setText("Arrastra aquí tus Fotos o Videos")
        self.convert_button.setEnabled(False)
        self.remove_button.setEnabled(False)

    def choose_output_folder(self):
        return QFileDialog.getExistingDirectory(self, "Seleccionar carpeta de salida")

    def apply_watermark(self):
        if not self.watermark_path:
            QMessageBox.warning(self, "Error", "Debes seleccionar un logo primero.")
            return
            
        respuesta = QMessageBox.question(
            self,
            "Confirmación",
            "Esta marca de agua se aplicará a los archivos multimedia seleccionados.\n(Se guardarán como copias en la carpeta que elijas).\n\n¿Deseas continuar?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if respuesta == QMessageBox.StandardButton.No:
            return
            
        output_dir = self.choose_output_folder()
        if not output_dir:
            return

        pos_map = {
            "Abajo Derecha": "bottom-right",
            "Abajo Izquierda": "bottom-left",
            "Arriba Derecha": "top-right",
            "Arriba Izquierda": "top-left",
            "Centro": "center"
        }
        selected_pos = pos_map.get(self.combo_pos.currentText(), "bottom-right")
        opacity = self.spin_opc.value()

        if self.batch_files:
            if len(self.batch_files) > 5:
                folder_name = "MarcaAgua_Masivo_" + datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                output_dir = os.path.join(output_dir, folder_name)
                if not os.path.exists(output_dir):
                    os.makedirs(output_dir)
                    
            converted = 0
            failed = 0
            total = len(self.batch_files)
            was_cancelled = False
            
            from core.ui.advanced_progress import AdvancedProgressDialog
            progress = AdvancedProgressDialog("Aplicando Marca de Agua...", total, self)
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
                        
                    nombre = os.path.basename(file_path)
                    ruta_destino = os.path.join(output_dir, nombre)
                    
                    resultado = WatermarkLogic.aplicar_marca_agua(
                        ruta_origen=file_path,
                        ruta_destino=ruta_destino,
                        watermark_path=self.watermark_path,
                        position=selected_pos,
                        opacity=opacity
                    )
                    
                    if str(resultado).startswith("✅"):
                        converted += 1
                    else:
                        failed += 1
                        
                    progress.setLabelText(f"Aplicando Logo... ({idx}/{total})")
                    progress.setValue(idx)
                    QApplication.processEvents()
            finally:
                progress.close()

            if was_cancelled:
                QMessageBox.warning(
                    self,
                    "Proceso Cancelado",
                    f"Proceso cancelado por el usuario.\nSe completaron {converted} de {total} archivos."
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
