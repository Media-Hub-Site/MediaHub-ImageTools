"""
apps/media_converter/ui/image_tools_window.py
─────────────────────────────────────────────
Ventana unificada y moderna para MediaHub Image Tools.
Integra:
  1. Quitar Fondo (rembg con modelos u2net, isnet, silueta)
  2. Mejorar Calidad 4x (Real-ESRGAN con IA)
  3. Marca de Agua en Lote (Texto o Logo con opacidad y posición)
  4. Optimizador / Compresor Web (JPG, PNG, WebP con control de peso)
Incluye SplitPreview (Antes/Después interactivo).
"""

import os
import sys
import shutil
import tempfile
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QStackedWidget, QFileDialog, QMessageBox, QComboBox, QCheckBox,
    QSpinBox, QSlider, QProgressBar, QFrame, QScrollArea, QLineEdit
)
from PyQt6.QtGui import QIcon, QPixmap, QColor
from PyQt6.QtCore import Qt, QThread, pyqtSignal

from apps.media_converter.converters.conversion import (
    BackgroundRemoverLogic,
    ImageEnhancerLogic,
    WatermarkLogic,
    ImageFormats,
    _prepare_dest
)
from apps.media_converter.ui.split_preview import SplitPreviewWidget


def get_asset(filename):
    base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    p = os.path.join(base, "assets", "hub", filename)
    if os.path.isfile(p):
        return p
    return os.path.join(base, "assets", filename)


class ImageWorker(QThread):
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(str, str)  # (mensaje, ruta_salida)
    error = pyqtSignal(str)

    def __init__(self, task_type: str, params: dict, parent=None):
        super().__init__(parent)
        self.task_type = task_type
        self.params = params

    def run(self):
        try:
            self.progress.emit(15, "Procesando imagen con IA...")
            orig = self.params["orig"]
            dest = self.params["dest"]

            if self.task_type == "bg_remover":
                model = self.params.get("model", "u2net")
                alpha = self.params.get("alpha", False)
                res = BackgroundRemoverLogic.quitar_fondo(orig, dest, model, alpha)
                if "Error" in res:
                    self.error.emit(res)
                else:
                    self.progress.emit(100, "¡Listo!")
                    self.finished.emit(res, dest)

            elif self.task_type == "quality":
                model = self.params.get("model", "realesrgan-x4plus")
                scale = self.params.get("scale", 4)
                use_tta = self.params.get("tta", False)
                res = ImageEnhancerLogic.mejorar_calidad(orig, dest, model, scale, use_tta)
                if "Error" in res:
                    self.error.emit(res)
                else:
                    self.progress.emit(100, "¡Listo!")
                    self.finished.emit(res, dest)

            elif self.task_type == "watermark":
                wm_type = self.params.get("wm_type", "texto")
                text = self.params.get("text", "")
                logo = self.params.get("logo", None)
                pos = self.params.get("pos", "Centro")
                opac = self.params.get("opacity", 70)
                
                from PIL import Image, ImageDraw, ImageFont
                base_image = Image.open(orig).convert("RGBA")
                w, h = base_image.size
                
                if wm_type == "imagen" and logo and os.path.exists(logo):
                    wm = Image.open(logo).convert("RGBA")
                    if opac < 100:
                        alpha = wm.split()[3].point(lambda p: p * (opac / 100.0))
                        wm.putalpha(alpha)
                    wm_ratio = wm.width / wm.height
                    new_w = max(20, int(w * 0.18))
                    new_h = max(20, int(new_w / wm_ratio))
                    wm = wm.resize((new_w, new_h), Image.Resampling.LANCZOS)
                else:
                    font_size = max(18, int(w * 0.04))
                    try:
                        font = ImageFont.truetype("arial.ttf", font_size)
                    except Exception:
                        font = ImageFont.load_default()
                    dummy = Image.new("RGBA", (1, 1))
                    d_dummy = ImageDraw.Draw(dummy)
                    bbox = d_dummy.textbbox((0, 0), text, font=font)
                    tw = bbox[2] - bbox[0]
                    th = bbox[3] - bbox[1]
                    pad = max(6, int(font_size * 0.3))
                    wm = Image.new("RGBA", (tw + pad * 2, th + pad * 2), (0, 0, 0, 0))
                    d_wm = ImageDraw.Draw(wm)
                    alpha = int(255 * (opac / 100.0))
                    d_wm.text((pad, pad), text, fill=(255, 255, 255, alpha), font=font)
                    
                margin = int(w * 0.03)
                pos_lower = pos.lower()
                if "centro" in pos_lower or "center" in pos_lower:
                    x = (w - wm.width) // 2
                    y = (h - wm.height) // 2
                elif "arriba izquierda" in pos_lower or "top-left" in pos_lower:
                    x, y = margin, margin
                elif "arriba derecha" in pos_lower or "top-right" in pos_lower:
                    x = w - wm.width - margin
                    y = margin
                elif "abajo izquierda" in pos_lower or "bottom-left" in pos_lower:
                    x = margin
                    y = h - wm.height - margin
                else:
                    x = w - wm.width - margin
                    y = h - wm.height - margin
                    
                base_image.paste(wm, (x, y), wm)
                ext = os.path.splitext(dest)[1].lower()
                if ext in [".jpg", ".jpeg"]:
                    base_image = base_image.convert("RGB")
                    base_image.save(dest, quality=95)
                else:
                    base_image.save(dest)
                    
                self.progress.emit(100, "¡Listo!")
                self.finished.emit("✅ Marca de agua aplicada correctamente", dest)

            elif self.task_type == "compress":
                fmt = self.params.get("fmt", "webp")
                quality = self.params.get("quality", 80)
                from PIL import Image
                img = Image.open(orig)
                res = ImageFormats._save_image(img, dest, fmt, quality=quality)
                self.progress.emit(100, "¡Listo!")
                self.finished.emit(res, dest)

        except Exception as e:
            self.error.emit(str(e))


class ImageToolsWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Image Tools — Media Hub")
        self.resize(1020, 680)
        self.setMinimumSize(960, 600)

        icon_path = get_asset("Media-Hub.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.current_orig_path: str | None = None
        self.current_dest_path: str | None = None
        self.current_worker: ImageWorker | None = None

        self._init_ui()
        self._apply_styles()

    def _init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ── SIDEBAR ──────────────────────────────────────────────────────────
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(240)
        sb_layout = QVBoxLayout(sidebar)
        sb_layout.setContentsMargins(18, 24, 18, 24)
        sb_layout.setSpacing(10)

        app_title = QLabel("IMAGE TOOLS")
        app_title.setObjectName("sidebarTitle")
        app_sub = QLabel("Herramientas de Imagen IA")
        app_sub.setObjectName("sidebarSubtitle")
        sb_layout.addWidget(app_title)
        sb_layout.addWidget(app_sub)
        sb_layout.addSpacing(15)

        self.nav_buttons = []
        modules = [
            ("🪄  Quitar Fondo IA", 0),
            ("✨  Mejorar Calidad 4x", 1),
            ("🏷️  Marca de Agua", 2),
            ("⚡  Comprimir / Optimizar", 3),
        ]

        for text, idx in modules:
            btn = QPushButton(text)
            btn.setObjectName("navBtn")
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked, i=idx: self._switch_tab(i))
            sb_layout.addWidget(btn)
            self.nav_buttons.append(btn)

        sb_layout.addStretch()

        self.btn_open_folder = QPushButton("📁 Ver Carpeta Salida")
        self.btn_open_folder.setObjectName("navSecondaryBtn")
        self.btn_open_folder.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_open_folder.clicked.connect(self._open_output_dir)
        sb_layout.addWidget(self.btn_open_folder)

        main_layout.addWidget(sidebar)

        # ── CONTENIDO PRINCIPAL ──────────────────────────────────────────────
        content_frame = QFrame()
        content_frame.setObjectName("contentFrame")
        c_layout = QVBoxLayout(content_frame)
        c_layout.setContentsMargins(28, 24, 28, 24)
        c_layout.setSpacing(16)

        # Barra de carga de archivo
        file_box = QFrame()
        file_box.setObjectName("fileBox")
        fb_layout = QHBoxLayout(file_box)
        fb_layout.setContentsMargins(14, 10, 14, 10)

        self.file_label = QLabel("Arrastra o selecciona una imagen para comenzar")
        self.file_label.setObjectName("fileLabel")
        fb_layout.addWidget(self.file_label, stretch=1)

        self.btn_select_file = QPushButton("Seleccionar Imagen")
        self.btn_select_file.setObjectName("actionBtnPrimary")
        self.btn_select_file.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_select_file.clicked.connect(self._pick_file)
        fb_layout.addWidget(self.btn_select_file)

        c_layout.addWidget(file_box)

        # Preview Split
        self.split_preview = SplitPreviewWidget(self)
        c_layout.addWidget(self.split_preview, stretch=1)

        # Barra de Opciones Dinámica (Stacked por herramienta)
        self.options_stack = QStackedWidget()

        # Tab 0: Quitar Fondo
        tab_bg = QWidget()
        t0_layout = QHBoxLayout(tab_bg)
        t0_layout.setContentsMargins(0, 0, 0, 0)
        t0_layout.addWidget(QLabel("Modelo:"))
        self.combo_bg_model = QComboBox()
        self.combo_bg_model.addItems(["u2net (General / Preciso)", "isnet-general-use", "u2net_human_seg (Personas)", "silueta (Rápido)"])
        t0_layout.addWidget(self.combo_bg_model)
        self.chk_alpha = QCheckBox("Alpha Matting (Bordes suaves)")
        t0_layout.addWidget(self.chk_alpha)
        t0_layout.addStretch()
        self.options_stack.addWidget(tab_bg)

        # Tab 1: Calidad 4x
        tab_qual = QWidget()
        t1_layout = QHBoxLayout(tab_qual)
        t1_layout.setContentsMargins(0, 0, 0, 0)
        t1_layout.addWidget(QLabel("Modelo IA:"))
        self.combo_qual_model = QComboBox()
        self.combo_qual_model.addItems(["realesrgan-x4plus (Fotos)", "realesrgan-x4plus-anime (Ilustraciones/Anime)"])
        t1_layout.addWidget(self.combo_qual_model)
        t1_layout.addWidget(QLabel("Escala:"))
        self.spin_scale = QSpinBox()
        self.spin_scale.setRange(2, 4)
        self.spin_scale.setValue(4)
        t1_layout.addWidget(self.spin_scale)
        self.chk_tta = QCheckBox("Modo TTA (Máxima fidelidad)")
        t1_layout.addWidget(self.chk_tta)
        t1_layout.addStretch()
        self.options_stack.addWidget(tab_qual)

        # Tab 2: Marca de agua
        tab_wm = QWidget()
        t2_layout = QHBoxLayout(tab_wm)
        t2_layout.setContentsMargins(0, 0, 0, 0)
        t2_layout.addWidget(QLabel("Texto:"))
        self.txt_watermark = QLineEdit("Media Hub")
        self.txt_watermark.setFixedWidth(160)
        t2_layout.addWidget(self.txt_watermark)
        t2_layout.addWidget(QLabel("Posición:"))
        self.combo_wm_pos = QComboBox()
        self.combo_wm_pos.addItems(["Centro", "Abajo Derecha", "Abajo Izquierda", "Arriba Derecha", "Arriba Izquierda"])
        t2_layout.addWidget(self.combo_wm_pos)
        t2_layout.addWidget(QLabel("Opacidad:"))
        self.spin_wm_opac = QSpinBox()
        self.spin_wm_opac.setRange(10, 100)
        self.spin_wm_opac.setValue(70)
        t2_layout.addWidget(self.spin_wm_opac)
        t2_layout.addStretch()
        self.options_stack.addWidget(tab_wm)

        # Tab 3: Comprimir
        tab_comp = QWidget()
        t3_layout = QHBoxLayout(tab_comp)
        t3_layout.setContentsMargins(0, 0, 0, 0)
        t3_layout.addWidget(QLabel("Formato:"))
        self.combo_comp_fmt = QComboBox()
        self.combo_comp_fmt.addItems(["webp", "jpg", "png"])
        t3_layout.addWidget(self.combo_comp_fmt)
        t3_layout.addWidget(QLabel("Calidad:"))
        self.slider_quality = QSlider(Qt.Orientation.Horizontal)
        self.slider_quality.setRange(20, 100)
        self.slider_quality.setValue(80)
        self.lbl_qual_val = QLabel("80%")
        self.slider_quality.valueChanged.connect(lambda v: self.lbl_qual_val.setText(f"{v}%"))
        t3_layout.addWidget(self.slider_quality)
        t3_layout.addWidget(self.lbl_qual_val)
        t3_layout.addStretch()
        self.options_stack.addWidget(tab_comp)

        c_layout.addWidget(self.options_stack)

        # Barra inferior de acción y progreso
        bottom_box = QHBoxLayout()
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setTextVisible(False)
        bottom_box.addWidget(self.progress_bar, stretch=1)

        self.status_label = QLabel("")
        self.status_label.setObjectName("statusLabel")
        bottom_box.addWidget(self.status_label)

        self.btn_process = QPushButton("🚀 Procesar Imagen")
        self.btn_process.setObjectName("btnProcess")
        self.btn_process.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_process.clicked.connect(self._start_process)
        bottom_box.addWidget(self.btn_process)

        c_layout.addLayout(bottom_box)
        main_layout.addWidget(content_frame, stretch=1)

        # Activar primera pestaña
        self._switch_tab(0)

    def _switch_tab(self, index: int):
        for i, btn in enumerate(self.nav_buttons):
            btn.setChecked(i == index)
        self.options_stack.setCurrentIndex(index)

    def _pick_file(self):
        file, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar Imagen", "",
            "Imágenes (*.png *.jpg *.jpeg *.webp *.bmp *.tiff)"
        )
        if file:
            self.current_orig_path = file
            self.current_dest_path = None
            self.file_label.setText(f"📄 {os.path.basename(file)}")
            self.split_preview.set_images(file, None)
            self.status_label.setText("Imagen lista para procesar.")

    def _get_output_dir(self):
        home = os.environ.get("USERPROFILE") or os.path.expanduser("~")
        dest = os.path.join(home, "Downloads", "MediaHub_Images")
        os.makedirs(dest, exist_ok=True)
        return dest

    def _open_output_dir(self):
        d = self._get_output_dir()
        try:
            os.startfile(d)
        except Exception as e:
            QMessageBox.warning(self, "Aviso", f"No se pudo abrir la carpeta:\n{e}")

    def _start_process(self):
        if not self.current_orig_path or not os.path.isfile(self.current_orig_path):
            QMessageBox.warning(self, "Atención", "Por favor selecciona primero una imagen.")
            return

        idx = self.options_stack.currentIndex()
        out_dir = self._get_output_dir()
        base_name, _ = os.path.splitext(os.path.basename(self.current_orig_path))

        params = {"orig": self.current_orig_path}

        if idx == 0:
            task_type = "bg_remover"
            dest = os.path.join(out_dir, f"{base_name}_nobg.png")
            m_text = self.combo_bg_model.currentText().split()[0]
            params.update({"dest": dest, "model": m_text, "alpha": self.chk_alpha.isChecked()})

        elif idx == 1:
            task_type = "quality"
            dest = os.path.join(out_dir, f"{base_name}_4x.png")
            m_text = self.combo_qual_model.currentText().split()[0]
            params.update({"dest": dest, "model": m_text, "scale": self.spin_scale.value(), "tta": self.chk_tta.isChecked()})

        elif idx == 2:
            task_type = "watermark"
            dest = os.path.join(out_dir, f"{base_name}_watermark.png")
            params.update({
                "dest": dest, "wm_type": "texto",
                "text": self.txt_watermark.text().strip() or "Media Hub",
                "pos": self.combo_wm_pos.currentText(),
                "opacity": self.spin_wm_opac.value()
            })

        else:
            task_type = "compress"
            fmt = self.combo_comp_fmt.currentText().lower()
            dest = os.path.join(out_dir, f"{base_name}_optimized.{fmt}")
            params.update({"dest": dest, "fmt": fmt, "quality": self.slider_quality.value()})

        self.btn_process.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(15)
        self.status_label.setText("⏳ Procesando...")

        self.current_worker = ImageWorker(task_type, params, self)
        self.current_worker.progress.connect(self._on_worker_progress)
        self.current_worker.finished.connect(self._on_worker_finished)
        self.current_worker.error.connect(self._on_worker_error)
        self.current_worker.start()

    def _on_worker_progress(self, pct: int, msg: str):
        self.progress_bar.setValue(pct)
        self.status_label.setText(msg)

    def _on_worker_finished(self, msg: str, saved_path: str):
        self.btn_process.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.current_dest_path = saved_path
        self.status_label.setText("✅ ¡Procesamiento completado!")
        self.split_preview.set_images(self.current_orig_path, saved_path)

    def _on_worker_error(self, err: str):
        self.btn_process.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.status_label.setText("❌ Error en el procesamiento")
        QMessageBox.critical(self, "Error", err)

    def _apply_styles(self):
        self.setStyleSheet("""
            QMainWindow {
                background-color: #0F1117;
                color: #F3F4F6;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            }
            QFrame#sidebar {
                background-color: #161822;
                border-right: 1px solid #232736;
            }
            QLabel#sidebarTitle {
                color: #FFFFFF;
                font-size: 14pt;
                font-weight: 800;
                letter-spacing: -0.3px;
            }
            QLabel#sidebarSubtitle {
                color: #828B9E;
                font-size: 9pt;
            }
            QPushButton#navBtn {
                background-color: transparent;
                color: #9CA3AF;
                border: none;
                border-radius: 8px;
                padding: 10px 14px;
                font-size: 10pt;
                font-weight: 600;
                text-align: left;
            }
            QPushButton#navBtn:hover {
                background-color: #1F2332;
                color: #FFFFFF;
            }
            QPushButton#navBtn:checked {
                background-color: #2563EB;
                color: #FFFFFF;
            }
            QPushButton#navSecondaryBtn {
                background-color: #1E2230;
                color: #D1D5DB;
                border: 1px solid #2B3144;
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 9pt;
                font-weight: 600;
            }
            QPushButton#navSecondaryBtn:hover {
                background-color: #272C3E;
                color: #FFFFFF;
            }
            QFrame#contentFrame {
                background-color: #0F1117;
            }
            QFrame#fileBox {
                background-color: #161822;
                border: 1px solid #232736;
                border-radius: 12px;
            }
            QLabel#fileLabel {
                color: #9CA3AF;
                font-size: 9.5pt;
                font-weight: 500;
            }
            QPushButton#actionBtnPrimary {
                background-color: #1F2433;
                color: #FFFFFF;
                border: 1px solid #323A52;
                border-radius: 8px;
                padding: 8px 16px;
                font-size: 9.5pt;
                font-weight: 600;
            }
            QPushButton#actionBtnPrimary:hover {
                background-color: #2B334A;
            }
            QPushButton#btnProcess {
                background-color: #2563EB;
                color: #FFFFFF;
                border: none;
                border-radius: 10px;
                padding: 10px 24px;
                font-size: 10.5pt;
                font-weight: 700;
            }
            QPushButton#btnProcess:hover {
                background-color: #1D4ED8;
            }
            QPushButton#btnProcess:disabled {
                background-color: #1E2333;
                color: #6B7280;
            }
            QComboBox, QSpinBox, QLineEdit {
                background-color: #161822;
                color: #F3F4F6;
                border: 1px solid #2B3144;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 9pt;
            }
            QComboBox::drop-down {
                border: none;
                padding-right: 8px;
            }
            QComboBox QAbstractItemView {
                background-color: #1A1D28;
                color: #F3F4F6;
                selection-background-color: #2563EB;
                selection-color: #FFFFFF;
                border: 1px solid #2B3144;
                outline: none;
                padding: 4px;
            }
            QComboBox QAbstractItemView::item {
                min-height: 28px;
                color: #F3F4F6;
                padding: 4px 8px;
            }
            QComboBox QAbstractItemView::item:selected {
                background-color: #2563EB;
                color: #FFFFFF;
            }
            QCheckBox {
                color: #D1D5DB;
                font-size: 9pt;
                font-weight: 500;
            }
            QLabel#statusLabel {
                color: #9CA3AF;
                font-size: 9pt;
                font-weight: 500;
            }
            QProgressBar {
                background-color: #161822;
                border: 1px solid #232736;
                border-radius: 6px;
                min-height: 8px;
            }
            QProgressBar::chunk {
                background-color: #2563EB;
                border-radius: 6px;
            }
        """)
