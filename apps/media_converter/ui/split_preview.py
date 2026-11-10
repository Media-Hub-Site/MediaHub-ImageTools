"""
apps/media_converter/ui/split_preview.py
────────────────────────────────────────
Widget interactivo Split-Slider "Antes / Después" para comparar imágenes.
Permite deslizar una barra vertical con el ratón para ver la imagen original vs la procesada.
Soporta imágenes de ultra alta resolución (4K, 8K, 16K) sin desbordar memoria.
Soporta previsualización en vivo (live preview) mediante QPixmap directo.
"""

import os
from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QPixmap, QColor, QPen, QCursor, QImageReader
from PyQt6.QtCore import Qt, QRect, QPoint, QSize


def _load_preview_pixmap(path: str | None, max_dim: int = 2560) -> QPixmap | None:
    """Carga una imagen de forma segura y optimizada para previsualización."""
    if not path or not os.path.exists(path):
        return None
    try:
        reader = QImageReader(path)
        reader.setAutoTransform(True)
        # Permitir asignación de hasta 2048 MB para imágenes masivas de escalado 4x/8x
        reader.setAllocationLimit(2048)
        sz = reader.size()
        if sz.isValid() and (sz.width() > max_dim or sz.height() > max_dim):
            scaled_sz = sz.scaled(QSize(max_dim, max_dim), Qt.AspectRatioMode.KeepAspectRatio)
            reader.setScaledSize(scaled_sz)
        img = reader.read()
        if not img.isNull():
            return QPixmap.fromImage(img)
    except Exception as e:
        print(f"Error cargando preview con QImageReader: {e}")
    # Respaldo convencional
    try:
        px = QPixmap(path)
        if not px.isNull():
            return px
    except Exception:
        pass
    return None


class SplitPreviewWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(240)
        self.pixmap_before: QPixmap | None = None
        self.pixmap_after: QPixmap | None = None
        self.split_position = 0.5  # 0.0 to 1.0
        self.is_dragging = False
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.SizeHorCursor)

    def set_images(self, path_before: str | None, path_after: str | None):
        self.pixmap_before = _load_preview_pixmap(path_before)
        self.pixmap_after = _load_preview_pixmap(path_after)
        self.update()

    def set_after_pixmap(self, pixmap: QPixmap | None):
        """Asigna directamente un QPixmap generado en memoria (para vista previa en vivo)."""
        self.pixmap_after = pixmap
        self.update()

    def clear(self):
        self.pixmap_before = None
        self.pixmap_after = None
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_dragging = True
            self._update_split(event.pos().x())

    def mouseMoveEvent(self, event):
        if self.is_dragging:
            self._update_split(event.pos().x())

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_dragging = False

    def _update_split(self, mouse_x: int):
        w = max(self.width(), 1)
        self.split_position = max(0.05, min(0.95, mouse_x / w))
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        w, h = self.width(), self.height()

        # Fondo cuadriculado transparente (checkerboard)
        self._draw_checkerboard(painter, w, h)

        if not self.pixmap_before and not self.pixmap_after:
            painter.setPen(QColor("#71717A"))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Sin imagen cargada para comparar")
            return

        split_x = int(w * self.split_position)

        # 1. Si sólo tenemos la de antes
        if self.pixmap_before and not self.pixmap_after:
            scaled = self.pixmap_before.scaled(w, h, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            ox = (w - scaled.width()) // 2
            oy = (h - scaled.height()) // 2
            painter.drawPixmap(ox, oy, scaled)
            return

        # 2. Si sólo tenemos la de después
        if self.pixmap_after and not self.pixmap_before:
            scaled = self.pixmap_after.scaled(w, h, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            ox = (w - scaled.width()) // 2
            oy = (h - scaled.height()) // 2
            painter.drawPixmap(ox, oy, scaled)
            return

        # 3. Dibujar ambas con recorte según el split_x
        scaled_before = self.pixmap_before.scaled(w, h, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        scaled_after = self.pixmap_after.scaled(w, h, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)

        ox = (w - scaled_before.width()) // 2
        oy = (h - scaled_before.height()) // 2

        # Lado izquierdo (Antes)
        painter.save()
        painter.setClipRect(0, 0, split_x, h)
        painter.drawPixmap(ox, oy, scaled_before)
        # Etiqueta "Original"
        painter.setPen(QColor("#FFFFFF"))
        painter.fillRect(10, 10, 70, 24, QColor(0, 0, 0, 160))
        painter.drawText(QRect(10, 10, 70, 24), Qt.AlignmentFlag.AlignCenter, "Original")
        painter.restore()

        # Lado derecho (Después)
        painter.save()
        painter.setClipRect(split_x, 0, w - split_x, h)
        painter.drawPixmap(ox, oy, scaled_after)
        # Etiqueta "Resultado"
        painter.setPen(QColor("#FFFFFF"))
        painter.fillRect(w - 90, 10, 80, 24, QColor(37, 99, 235, 200))
        painter.drawText(QRect(w - 90, 10, 80, 24), Qt.AlignmentFlag.AlignCenter, "Resultado")
        painter.restore()

        # Línea divisoria central con manija
        pen = QPen(QColor("#FFFFFF"), 2)
        painter.setPen(pen)
        painter.drawLine(split_x, 0, split_x, h)

        # Manija circular
        cy = h // 2
        painter.setBrush(QColor("#FFFFFF"))
        painter.drawEllipse(QPoint(split_x, cy), 14, 14)
        painter.setPen(QPen(QColor("#18181B"), 2))
        painter.drawLine(split_x - 4, cy - 5, split_x - 4, cy + 5)
        painter.drawLine(split_x + 4, cy - 5, split_x + 4, cy + 5)

    def _draw_checkerboard(self, painter: QPainter, w: int, h: int):
        painter.fillRect(0, 0, w, h, QColor("#18181B"))
        sq = 16
        c1 = QColor("#222228")
        for x in range(0, w, sq):
            for y in range(0, h, sq):
                if ((x // sq) + (y // sq)) % 2 == 0:
                    painter.fillRect(x, y, sq, sq, c1)
