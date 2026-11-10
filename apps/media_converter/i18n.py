"""
apps/media_converter/i18n.py
────────────────────────────
Gestor de internacionalización ligero para MediaHub-ImageTools.
Detecta el idioma configurado vía:
1. Argumento CLI: --lang=es / --lang=en
2. Variable de entorno: MEDIAHUB_APP_LANG / MEDIAHUB_LANG / LANG
3. Archivo config_lang.json en el directorio de la aplicación
4. Idioma del sistema operativo por defecto
"""

import os
import sys
import json
import locale

_CURRENT_LANG = None

STRINGS = {
    "es": {
        "app_title": "Herramientas de Imagen — Media Hub",
        "header_title": "HERRAMIENTAS DE IMAGEN",
        "header_sub": "Herramientas de Imagen IA",
        "tab_bg": "Quitar Fondo IA",
        "tab_enhance": "Mejorar Calidad 4x",
        "tab_watermark": "Marca de Agua",
        "tab_compress": "Comprimir / Optimizar",
        "btn_open_folder": "Ver Carpeta Salida",
        "drag_drop_prompt": "Arrastra o selecciona una imagen para comenzar",
        "btn_select_image": "Seleccionar Imagen",
        "lbl_model": "Modelo:",
        "lbl_ai_model": "Modelo IA:",
        "lbl_scale": "Escala:",
        "chk_tta": "Modo TTA (Máxima fidelidad)",
        "lbl_type": "Tipo:",
        "lbl_text": "Texto:",
        "type_text": "Texto",
        "type_image": "Imagen / Logo",
        "btn_select_logo": "Cargar Logo PNG",
        "no_logo_selected": "Sin logo seleccionado",
        "lbl_position": "Posición:",
        "pos_center": "Centro",
        "pos_bottom_right": "Abajo Derecha",
        "pos_bottom_left": "Abajo Izquierda",
        "pos_top_right": "Arriba Derecha",
        "pos_top_left": "Arriba Izquierda",
        "lbl_opacity": "Opacidad:",
        "lbl_format": "Formato:",
        "lbl_quality": "Calidad:",
        "btn_process": "Procesar Imagen",
        "status_ready": "Imagen lista para procesar.",
        "status_processing": "Procesando...",
        "status_processing_ia": "Procesando imagen con IA...",
        "status_done": "Procesamiento completado",
        "status_error": "Error en el procesamiento",
        "msg_select_first": "Por favor selecciona una imagen primero.",
        "msg_select_logo_first": "Por favor selecciona un archivo de imagen o logo para la marca de agua.",
        "dialog_attention": "Atención",
        "dialog_error": "Error",
        "preview_original": "Original",
        "preview_result": "Resultado",
        "dialog_select_img_title": "Seleccionar Imagen",
        "dialog_select_logo_title": "Seleccionar Logo o Marca de Agua",
    },
    "en": {
        "app_title": "Image Tools — Media Hub",
        "header_title": "IMAGE TOOLS",
        "header_sub": "AI Image Tools",
        "tab_bg": "Remove Background AI",
        "tab_enhance": "Enhance Quality 4x",
        "tab_watermark": "Watermark",
        "tab_compress": "Compress / Optimize",
        "btn_open_folder": "Open Output Folder",
        "drag_drop_prompt": "Drag and drop or select an image to start",
        "btn_select_image": "Select Image",
        "lbl_model": "Model:",
        "lbl_ai_model": "AI Model:",
        "lbl_scale": "Scale:",
        "chk_tta": "TTA Mode (Maximum fidelity)",
        "lbl_type": "Type:",
        "lbl_text": "Text:",
        "type_text": "Text",
        "type_image": "Image / Logo",
        "btn_select_logo": "Load Logo PNG",
        "no_logo_selected": "No logo selected",
        "lbl_position": "Position:",
        "pos_center": "Center",
        "pos_bottom_right": "Bottom Right",
        "pos_bottom_left": "Bottom Left",
        "pos_top_right": "Top Right",
        "pos_top_left": "Top Left",
        "lbl_opacity": "Opacity:",
        "lbl_format": "Format:",
        "lbl_quality": "Quality:",
        "btn_process": "Process Image",
        "status_ready": "Image ready to process.",
        "status_processing": "Processing...",
        "status_processing_ia": "Processing image with AI...",
        "status_done": "Processing complete",
        "status_error": "Processing error",
        "msg_select_first": "Please select an image first.",
        "msg_select_logo_first": "Please select an image or logo file for the watermark.",
        "dialog_attention": "Attention",
        "dialog_error": "Error",
        "preview_original": "Original",
        "preview_result": "Result",
        "dialog_select_img_title": "Select Image",
        "dialog_select_logo_title": "Select Logo or Watermark Image",
    }
}


def get_current_language() -> str:
    global _CURRENT_LANG
    if _CURRENT_LANG:
        return _CURRENT_LANG

    # 1. Argumento CLI (--lang=xx)
    for arg in sys.argv[1:]:
        if arg.startswith("--lang="):
            val = arg.split("=", 1)[1].strip().lower()
            if val in ("es", "en"):
                _CURRENT_LANG = val
                return _CURRENT_LANG

    # 2. Variable de entorno
    for env_var in ("MEDIAHUB_APP_LANG", "MEDIAHUB_LANG", "LANG"):
        val = os.environ.get(env_var, "").lower()
        if val.startswith("es"):
            _CURRENT_LANG = "es"
            return "es"
        elif val.startswith("en"):
            _CURRENT_LANG = "en"
            return "en"

    # 3. Archivo config_lang.json en la misma carpeta del ejecutable o raíz
    base_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    cfg_candidates = [
        os.path.join(base_dir, "config_lang.json"),
        os.path.join(base_dir, "..", "config_lang.json"),
    ]
    for cfg in cfg_candidates:
        if os.path.isfile(cfg):
            try:
                with open(cfg, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    val = data.get("language")
                    if val in ("es", "en"):
                        _CURRENT_LANG = val
                        return _CURRENT_LANG
            except Exception:
                pass

    # 4. Fallback sistema
    try:
        lang, _ = locale.getdefaultlocale()
        if lang and lang.lower().startswith("es"):
            _CURRENT_LANG = "es"
            return "es"
    except Exception:
        pass

    _CURRENT_LANG = "es"
    return "es"


def t(key: str, **kwargs) -> str:
    lang = get_current_language()
    text = STRINGS.get(lang, STRINGS["es"]).get(key, STRINGS["es"].get(key, key))
    if kwargs:
        try:
            return text.format(**kwargs)
        except Exception:
            return text
    return text
