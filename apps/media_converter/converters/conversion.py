#-----------------------------------------------
# Convertidor de Imagenes
#-----------------------------------------------

from PIL import Image, ImageFile
import os
import shutil

# Pillow sometimes fails on truncated images; enable loading anyway
ImageFile.LOAD_TRUNCATED_IMAGES = True


def _prepare_dest(ruta_destino: str) -> str:
    """Asegura que la carpeta de destino exista dentro del repositorio.

    - Si `ruta_destino` es relativa, se interpreta respecto a la raíz del repo.
    - Crea el directorio padre si no existe.
    - Devuelve la ruta absoluta final a usar para guardar.
    """
    if ruta_destino is None:
        raise ValueError("ruta_destino no puede ser None")

    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

    if not os.path.isabs(ruta_destino):
        ruta_abs = os.path.join(repo_root, ruta_destino)
    else:
        ruta_abs = ruta_destino

    parent = os.path.dirname(ruta_abs)
    if parent == '':
        parent = os.path.join(repo_root, 'destino')
        ruta_abs = os.path.join(parent, os.path.basename(ruta_abs))

    os.makedirs(parent, exist_ok=True)
    return ruta_abs


def _find_ffmpeg() -> str | None:
    """Intentar localizar el ejecutable ffmpeg."""
    env_path = os.environ.get('FFMPEG_PATH')
    if env_path:
        env_path = os.path.abspath(env_path)
        if os.path.isfile(env_path):
            return env_path
        if os.path.isdir(env_path):
            for candidate in ('ffmpeg.exe', 'ffmpeg'):
                maybe = os.path.join(env_path, candidate)
                if os.path.isfile(maybe):
                    return maybe

    for name in ('ffmpeg', 'ffmpeg.exe'):
        p = shutil.which(name)
        if p:
            return p

    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    candidates = [
        os.path.join(repo_root, 'ffmpeg', 'ffmpeg'),
        os.path.join(repo_root, 'ffmpeg', 'ffmpeg.exe'),
        os.path.join(repo_root, 'ffmpeg', 'bin', 'ffmpeg'),
        os.path.join(repo_root, 'ffmpeg', 'bin', 'ffmpeg.exe'),
        os.path.join(repo_root, 'bin', 'ffmpeg'),
        os.path.join(repo_root, 'bin', 'ffmpeg.exe'),
        os.path.join(repo_root, 'ffmpeg.exe'),
        os.path.join(repo_root, 'ffmpeg'),
    ]

    user_profile = os.environ.get('USERPROFILE', '')
    local_app_data = os.environ.get('LOCALAPPDATA', '')
    program_files = os.environ.get('ProgramFiles', r'C:\Program Files')
    program_files_x86 = os.environ.get('ProgramFiles(x86)', r'C:\Program Files (x86)')
    windows_candidates = [
        r'C:\ffmpeg\bin\ffmpeg.exe',
        r'C:\ffmpeg\ffmpeg.exe',
        os.path.join(program_files, 'ffmpeg', 'bin', 'ffmpeg.exe'),
        os.path.join(program_files_x86, 'ffmpeg', 'bin', 'ffmpeg.exe'),
        os.path.join(program_files, 'ImageMagick-7.1.1-Q16-HDRI', 'ffmpeg.exe'),
        os.path.join(local_app_data, 'Microsoft', 'WinGet', 'Links', 'ffmpeg.exe'),
        os.path.join(user_profile, 'scoop', 'shims', 'ffmpeg.exe'),
        os.path.join(user_profile, 'scoop', 'apps', 'ffmpeg', 'current', 'bin', 'ffmpeg.exe'),
        os.path.join(os.environ.get('ProgramData', r'C:\ProgramData'), 'chocolatey', 'bin', 'ffmpeg.exe'),
    ]
    candidates.extend(windows_candidates)

    for c in candidates:
        if os.path.isfile(c):
            return c

    try:
        import imageio_ffmpeg
        p = imageio_ffmpeg.get_ffmpeg_exe()
        if p and os.path.isfile(p):
            return p
    except Exception:
        pass

    return None


class ImageFormats:
    formatos_imagen = ['png', 'jpg', 'jpeg', 'webp', 'bmp', 'tiff', 'gif', 'ico']

    @staticmethod
    def _open_image(ruta_origen):
        return Image.open(ruta_origen)

    @staticmethod
    def _save_image(img: Image.Image, ruta_destino: str, formato: str, quality: int = 85):
        ruta_destino = _prepare_dest(ruta_destino)
        formato_lower = formato.lower()

        if formato_lower in ('jpg', 'jpeg'):
            if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
                fondo = Image.new('RGB', img.size, (255, 255, 255))
                fondo.paste(img.convert('RGBA'), mask=img.convert('RGBA').split()[-1])
                fondo.save(ruta_destino, 'JPEG', quality=quality)
            else:
                img.convert('RGB').save(ruta_destino, 'JPEG', quality=quality)
        elif formato_lower == 'png':
            if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
                img.save(ruta_destino, 'PNG', optimize=True)
            else:
                img.convert('RGB').save(ruta_destino, 'PNG', optimize=True)
        elif formato_lower == 'webp':
            img.save(ruta_destino, 'WEBP', quality=quality, method=6)
        elif formato_lower == 'ico':
            if img.mode != 'RGBA':
                img = img.convert('RGBA')
            # Ensure it fits max standard ico size, but PIL handles standard resizing or saves as is.
            img.save(ruta_destino, format='ICO')
        else:
            try:
                img.save(ruta_destino, formato.upper())
            except Exception:
                img.save(ruta_destino)

        return f"✅ Convertido: {os.path.basename(ruta_destino)}"

    @staticmethod
    def convertir(ruta_origen, ruta_destino, formato_destino=None):
        try:
            if formato_destino is None:
                formato_destino = os.path.splitext(ruta_destino)[1].lstrip('.').lower()
            img = ImageFormats._open_image(ruta_origen)
            return ImageFormats._save_image(img, ruta_destino, formato_destino)
        except Exception as e:
            return f"⚠️ Error con {os.path.basename(ruta_origen)}: {e}"

    @staticmethod
    def convertir_jpg_a_png(ruta_origen, ruta_destino):
        try:
            img = ImageFormats._open_image(ruta_origen)
            return ImageFormats._save_image(img, ruta_destino, 'png')
        except Exception as e:
            return f"⚠️ Error con {os.path.basename(ruta_origen)}: {e}"

    @staticmethod
    def convertir_jpg_a_webp(ruta_origen, ruta_destino):
        try:
            img = ImageFormats._open_image(ruta_origen)
            return ImageFormats._save_image(img, ruta_destino, 'webp')
        except Exception as e:
            return f"⚠️ Error con {os.path.basename(ruta_origen)}: {e}"

    @staticmethod
    def convertir_png_a_jpg(ruta_origen, ruta_destino):
        try:
            img = ImageFormats._open_image(ruta_origen)
            return ImageFormats._save_image(img, ruta_destino, 'jpg')
        except Exception as e:
            return f"⚠️ Error con {os.path.basename(ruta_origen)}: {e}"

    @staticmethod
    def convertir_png_a_webp(ruta_origen, ruta_destino):
        try:
            img = ImageFormats._open_image(ruta_origen)
            return ImageFormats._save_image(img, ruta_destino, 'webp')
        except Exception as e:
            return f"⚠️ Error con {os.path.basename(ruta_origen)}: {e}"

    @staticmethod
    def convertir_webp_a_jpg(ruta_origen, ruta_destino):
        try:
            img = ImageFormats._open_image(ruta_origen)
            return ImageFormats._save_image(img, ruta_destino, 'jpg')
        except Exception as e:
            return f"⚠️ Error con {os.path.basename(ruta_origen)}: {e}"

    @staticmethod
    def convertir_webp_a_png(ruta_origen, ruta_destino):
        try:
            img = ImageFormats._open_image(ruta_origen)
            return ImageFormats._save_image(img, ruta_destino, 'png')
        except Exception as e:
            return f"⚠️ Error con {os.path.basename(ruta_origen)}: {e}"


class ImageRescalerLogic:
    @staticmethod
    def reescalar_imagen(ruta_origen, ruta_destino, modo="pixeles", ancho_target=None, alto_target=None, porcentaje=None, mantener_aspecto=True, no_agrandar=False):
        try:
            img = Image.open(ruta_origen)
            w, h = img.size

            if modo == "porcentaje":
                if porcentaje is None:
                    return "⚠️ Error: Porcentaje no especificado."
                factor = porcentaje / 100.0
                new_w = int(w * factor)
                new_h = int(h * factor)
            else: # pixeles
                if ancho_target is None or alto_target is None:
                    return "⚠️ Error: Ancho y alto deben especificarse en modo píxeles."
                new_w = int(ancho_target)
                new_h = int(alto_target)

                if mantener_aspecto:
                    # Si mantener aspecto está activo, recalculamos en base a la escala más restrictiva
                    # O podemos simplemente reescalar manteniendo el aspecto del ancho. 
                    # Generalmente se respeta el que se modificó, pero dejaremos que la UI mande 
                    # el ancho/alto con el aspecto ya mantenido o recalculamos acá si hace falta.
                    # Asumimos que la UI ya pasa los valores correctamente ajustados.
                    pass

            if no_agrandar:
                if new_w > w or new_h > h:
                    new_w = min(new_w, w)
                    new_h = min(new_h, h)

            if (new_w, new_h) == (w, h):
                # No resize needed, just save copy
                img_resized = img
            else:
                img_resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
                
            return ImageFormats._save_image(img_resized, ruta_destino, os.path.splitext(ruta_destino)[1].lstrip('.').lower())
        except Exception as e:
            return f"⚠️ Error reescalando {os.path.basename(ruta_origen)}: {e}"


class BackgroundRemoverLogic:
    @staticmethod
    def quitar_fondo(ruta_origen, ruta_destino, model_name="u2net", alpha_matting=False):
        try:
            import rembg
            with open(ruta_origen, "rb") as input_file:
                input_data = input_file.read()
                
            session = rembg.new_session(model_name)
            output_data = rembg.remove(
                input_data, 
                session=session, 
                post_process_mask=True,
                alpha_matting=alpha_matting
            )
            
            # Ensure the destination path is absolute and exists
            ruta_destino = _prepare_dest(ruta_destino)
            
            with open(ruta_destino, "wb") as output_file:
                output_file.write(output_data)
                
            return f"✅ Fondo eliminado: {os.path.basename(ruta_destino)}"
        except ImportError:
            return "⚠️ Error: La librería rembg no está instalada."
        except Exception as e:
            return f"⚠️ Error quitando fondo a {os.path.basename(ruta_origen)}: {e}"


class ImageEnhancerLogic:
    @staticmethod
    def _download_model_if_needed():
        import requests
        import zipfile
        
        # 1. Buscar primero en la carpeta local del proyecto
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
        local_exe = os.path.join(repo_root, 'apps', 'models', 'realesrgan', 'realesrgan-ncnn-vulkan.exe')
        if os.path.isfile(local_exe):
            return local_exe
        
        # 2. Si no existe localmente, descargar a ProgramData para evitar errores de espacios en rutas (bug de _wfopen en realesrgan)
        appdata_dir = os.environ.get('ProgramData')
        if not appdata_dir:
            appdata_dir = os.environ.get('APPDATA') or os.path.expanduser('~')
        models_dir = os.path.join(appdata_dir, "MediaHub", "models", "realesrgan")
        os.makedirs(models_dir, exist_ok=True)
        exe_path = os.path.join(models_dir, "realesrgan-ncnn-vulkan.exe")
        
        if not os.path.exists(exe_path):
            zip_path = os.path.join(models_dir, "realesrgan.zip")
            url = "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesrgan-ncnn-vulkan-20220424-windows.zip"
            response = requests.get(url, stream=True)
            if response.status_code == 200:
                with open(zip_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                        
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(models_dir)
                    
                os.remove(zip_path)
            else:
                raise Exception("No se pudo descargar el modelo de Super Resolución (Real-ESRGAN).")
        return exe_path

    @staticmethod
    def mejorar_calidad(ruta_origen, ruta_destino, model_name="realesrgan-x4plus", scale=4, use_tta=False):
        import subprocess
        import tempfile
        import shutil
        import uuid
        try:
            exe_path = ImageEnhancerLogic._download_model_if_needed()
            
            # Ensure the destination path is absolute and exists
            ruta_destino = _prepare_dest(ruta_destino)
            
            # Use temp files to avoid Unicode issues with the executable
            temp_dir = tempfile.gettempdir()
            unique_id = str(uuid.uuid4())
            ext_origen = os.path.splitext(ruta_origen)[1].lower()
            if not ext_origen:
                ext_origen = ".png"
            
            input_tmp = os.path.join(temp_dir, f"input_{unique_id}{ext_origen}")
            output_tmp = os.path.join(temp_dir, f"output_{unique_id}.png")
            
            shutil.copy2(ruta_origen, input_tmp)
            
            # Run Real-ESRGAN
            cmd = [
                exe_path,
                "-i", input_tmp,
                "-o", output_tmp,
                "-s", str(scale),
                "-n", model_name,
                "-t", "400"
            ]
            
            if use_tta:
                cmd.append("-x")
            
            # Hide console window on Windows
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            try:
                subprocess.run(cmd, check=True, startupinfo=startupinfo, capture_output=True, text=True)
            except subprocess.CalledProcessError as e:
                raise Exception(f"El motor de IA falló: {e.stderr.strip() if e.stderr else str(e)}")
            
            if os.path.exists(output_tmp):
                shutil.copy2(output_tmp, ruta_destino)
            else:
                raise Exception("El programa no generó la imagen de salida.")
                
            # Cleanup
            try:
                os.remove(input_tmp)
                os.remove(output_tmp)
            except:
                pass
            
            return f"✅ Calidad mejorada con IA (Real-ESRGAN): {os.path.basename(ruta_destino)}"
        except Exception as e:
            return f"⚠️ Error mejorando la calidad de {os.path.basename(ruta_origen)}: {e}"


class AudioFormats:
    formatos_audio = ['mp3', 'wav', 'flac', 'ogg', 'm4a', 'mpeg', 'aac', 'wma', 'alac', 'aiff']

    @staticmethod
    def _run_ffmpeg(ruta_origen, ruta_destino, extra_args=None):
        import subprocess
        if extra_args is None:
            extra_args = []
        ruta_destino = _prepare_dest(ruta_destino)
        ffmpeg_path = _find_ffmpeg()
        if not ffmpeg_path:
            return False, '❌ ffmpeg no está disponible. Añádelo a PATH o define la variable de entorno FFMPEG_PATH apuntando al ejecutable.'
        cmd = [ffmpeg_path, '-y', '-i', ruta_origen] + extra_args + [ruta_destino]
        try:
            repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
            subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, cwd=repo_root)
            return True, f"✅ Convertido: {os.path.basename(ruta_origen)} -> {os.path.basename(ruta_destino)}"
        except subprocess.CalledProcessError as e:
            stderr = e.stderr.decode(errors='replace') if isinstance(e.stderr, (bytes, bytearray)) else str(e.stderr)
            return False, f"⚠️ Error en ffmpeg: {stderr}"

    @staticmethod
    def _default_audio_args(formato_destino: str):
        fmt = (formato_destino or '').lower()
        if fmt == 'mp3':
            return ['-vn', '-c:a', 'libmp3lame', '-b:a', '192k']
        if fmt == 'wav':
            return ['-vn', '-c:a', 'pcm_s16le', '-ar', '44100', '-ac', '2']
        if fmt == 'flac':
            return ['-vn', '-c:a', 'flac']
        if fmt == 'ogg':
            return ['-vn', '-c:a', 'libvorbis', '-q:a', '5']
        if fmt in ('m4a', 'aac'):
            return ['-vn', '-c:a', 'aac', '-b:a', '192k']
        return ['-vn', '-c:a', 'aac', '-b:a', '192k']

    @staticmethod
    def convertir(ruta_origen, ruta_destino, formato_destino=None):
        try:
            if formato_destino is None:
                formato_destino = os.path.splitext(ruta_destino)[1].lstrip('.').lower()
            extra_args = AudioFormats._default_audio_args(formato_destino)
            ok, msg = AudioFormats._run_ffmpeg(ruta_origen, ruta_destino, extra_args=extra_args)
            return msg
        except Exception as e:
            return f"⚠️ Error con {os.path.basename(ruta_origen)}: {e}"


class VideoFormats:
    formatos_video = ['mp4', 'mkv', 'avi', 'mov', 'webm', 'flv', 'wmv', 'm4v', '3gp', 'mpeg', 'mp3']

    @staticmethod
    def _run_ffmpeg(ruta_origen, ruta_destino, extra_args=None):
        import subprocess
        if extra_args is None:
            extra_args = []
        ruta_destino = _prepare_dest(ruta_destino)
        ffmpeg_path = _find_ffmpeg()
        if not ffmpeg_path:
            return False, '❌ ffmpeg no está disponible. Añádelo a PATH o define la variable de entorno FFMPEG_PATH apuntando al ejecutable.'
        cmd = [ffmpeg_path, '-y', '-i', ruta_origen] + extra_args + [ruta_destino]
        try:
            repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
            subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, cwd=repo_root)
            return True, f"✅ Convertido: {os.path.basename(ruta_origen)} -> {os.path.basename(ruta_destino)}"
        except subprocess.CalledProcessError as e:
            stderr = e.stderr.decode(errors='replace') if isinstance(e.stderr, (bytes, bytearray)) else str(e.stderr)
            return False, f"⚠️ Error en ffmpeg: {stderr}"

    _hw_encoder = None

    @classmethod
    def get_hw_encoder(cls):
        if cls._hw_encoder is not None:
            return cls._hw_encoder
            
        cls._hw_encoder = "libx264" # default fallback
        import subprocess, os
        try:
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            r = subprocess.run(['wmic', 'path', 'win32_VideoController', 'get', 'name'], capture_output=True, text=True, startupinfo=startupinfo)
            out = r.stdout.lower()
            if "nvidia" in out:
                cls._hw_encoder = "h264_nvenc"
            elif "amd" in out or "radeon" in out:
                cls._hw_encoder = "h264_amf"
        except:
            pass
        return cls._hw_encoder

    @staticmethod
    def _default_video_args(formato_destino: str):
        fmt = (formato_destino or '').lower()
        hw = VideoFormats.get_hw_encoder()
        
        if fmt in ('mp4', 'mov', 'm4v'):
            return ['-c:v', hw, '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart']
        if fmt == 'mkv':
            return ['-c:v', hw, '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k']
        if fmt == 'webm':
            return ['-c:v', 'libvpx-vp9', '-b:v', '0', '-crf', '32', '-c:a', 'libopus', '-b:a', '128k']
        if fmt == 'avi':
            return ['-c:v', 'mpeg4', '-q:v', '5', '-c:a', 'libmp3lame', '-b:a', '192k']
        if fmt == 'wmv':
            return ['-c:v', 'wmv2', '-c:a', 'wmav2']
        if fmt == 'flv':
            return ['-c:v', 'flv', '-c:a', 'libmp3lame', '-b:a', '128k']
        if fmt == '3gp':
            return ['-c:v', 'h263', '-c:a', 'aac', '-b:a', '96k']
        if fmt == 'mp3':
            # Extraer solo el audio en mp3 (descartar video)
            return ['-vn', '-c:a', 'libmp3lame', '-b:a', '192k']
        return ['-c:v', hw, '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k']

    @staticmethod
    def convertir(ruta_origen, ruta_destino, formato_destino=None):
        try:
            if formato_destino is None:
                formato_destino = os.path.splitext(ruta_destino)[1].lstrip('.').lower()
            extra_args = VideoFormats._default_video_args(formato_destino)
            ok, msg = VideoFormats._run_ffmpeg(ruta_origen, ruta_destino, extra_args=extra_args)
            return msg
        except Exception as e:
            return f"⚠️ Error con {os.path.basename(ruta_origen)}: {e}"

class SubtitleGeneratorLogic:
    @staticmethod
    def _download_whisper_if_needed():
        import requests, zipfile, os
        appdata_dir = os.environ.get('ProgramData')
        if not appdata_dir:
            appdata_dir = os.environ.get('APPDATA') or os.path.expanduser('~')
        whisper_dir = os.path.join(appdata_dir, "MediaHub", "models", "whisper")
        os.makedirs(whisper_dir, exist_ok=True)
        exe_path = os.path.join(whisper_dir, "main.exe")
        
        if not os.path.exists(exe_path):
            zip_path = os.path.join(whisper_dir, "whisper-bin-x64.zip")
            url = "https://github.com/ggerganov/whisper.cpp/releases/download/v1.5.4/whisper-bin-x64.zip"
            response = requests.get(url, stream=True)
            if response.status_code == 200:
                with open(zip_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(whisper_dir)
                os.remove(zip_path)
            else:
                raise Exception("No se pudo descargar el motor Whisper.")
        return exe_path

    @staticmethod
    def _download_model_if_needed(model_size):
        import requests, os
        appdata_dir = os.environ.get('ProgramData')
        if not appdata_dir:
            appdata_dir = os.environ.get('APPDATA') or os.path.expanduser('~')
        models_dir = os.path.join(appdata_dir, "MediaHub", "models", "whisper")
        os.makedirs(models_dir, exist_ok=True)
        
        model_name = f"ggml-{model_size}.bin"
        model_path = os.path.join(models_dir, model_name)
        
        if not os.path.exists(model_path):
            url = f"https://huggingface.co/ggerganov/whisper.cpp/resolve/main/{model_name}"
            response = requests.get(url, stream=True)
            if response.status_code == 200:
                with open(model_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
            else:
                raise Exception(f"No se pudo descargar el modelo {model_size}.")
        return model_path

    @staticmethod
    def generar_subtitulos(ruta_origen, ruta_destino, model_size="tiny", language="auto"):
        import subprocess, tempfile, os, shutil, uuid
        try:
            exe_path = SubtitleGeneratorLogic._download_whisper_if_needed()
            model_path = SubtitleGeneratorLogic._download_model_if_needed(model_size)
            
            ruta_destino = _prepare_dest(ruta_destino)
            temp_dir = tempfile.gettempdir()
            unique_id = str(uuid.uuid4())
            wav_tmp = os.path.join(temp_dir, f"audio_{unique_id}.wav")
            
            # Extract 16kHz wav audio
            ffmpeg_path = _find_ffmpeg()
            if not ffmpeg_path:
                return "❌ ffmpeg no está disponible."
            
            cmd_ffmpeg = [ffmpeg_path, "-y", "-i", ruta_origen, "-vn", "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", wav_tmp]
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
            subprocess.run(cmd_ffmpeg, check=True, startupinfo=startupinfo, capture_output=True)
            
            # Run Whisper
            cmd_whisper = [
                exe_path,
                "-m", model_path,
                "-f", wav_tmp,
                "-l", language,
                "-osrt"
            ]
            
            res = subprocess.run(cmd_whisper, check=False, startupinfo=startupinfo, capture_output=True, text=True)
            if res.returncode != 0:
                raise Exception(f"Whisper falló: {res.stderr}")
            
            srt_tmp = wav_tmp + ".srt"
            if os.path.exists(srt_tmp):
                shutil.copy2(srt_tmp, ruta_destino)
                os.remove(srt_tmp)
            else:
                raise Exception("El programa no generó el archivo SRT.")
            
            if os.path.exists(wav_tmp):
                os.remove(wav_tmp)
                
            return f"✅ Subtítulos generados: {os.path.basename(ruta_destino)}"
        except Exception as e:
            return f"⚠️ Error generando subtítulos: {e}"

class WatermarkLogic:
    @staticmethod
    def aplicar_marca_agua(ruta_origen, ruta_destino, watermark_path, position="bottom-right", opacity=100):
        import os
        try:
            ruta_destino = _prepare_dest(ruta_destino)
            ext = os.path.splitext(ruta_origen)[1].lower()
            
            if ext in ['.mp4', '.mkv', '.avi', '.mov', '.webm', '.flv']:
                return WatermarkLogic._watermark_video(ruta_origen, ruta_destino, watermark_path, position, opacity)
            else:
                return WatermarkLogic._watermark_image(ruta_origen, ruta_destino, watermark_path, position, opacity)
        except Exception as e:
            return f"⚠️ Error aplicando marca de agua: {e}"

    @staticmethod
    def _watermark_image(ruta_origen, ruta_destino, watermark_path, position, opacity):
        from PIL import Image
        import os
        base_image = Image.open(ruta_origen).convert("RGBA")
        watermark = Image.open(watermark_path).convert("RGBA")
        
        if opacity < 100:
            alpha = watermark.split()[3]
            alpha = alpha.point(lambda p: p * (opacity / 100.0))
            watermark.putalpha(alpha)
            
        wm_ratio = watermark.width / watermark.height
        new_wm_width = int(base_image.width * 0.15)
        new_wm_height = int(new_wm_width / wm_ratio)
        watermark = watermark.resize((new_wm_width, new_wm_height), Image.Resampling.LANCZOS)
        
        margin = int(base_image.width * 0.03)
        x, y = 0, 0
        if position == "top-left":
            x, y = margin, margin
        elif position == "top-right":
            x, y = base_image.width - watermark.width - margin, margin
        elif position == "bottom-left":
            x, y = margin, base_image.height - watermark.height - margin
        elif position == "bottom-right":
            x, y = base_image.width - watermark.width - margin, base_image.height - watermark.height - margin
        elif position == "center":
            x, y = (base_image.width - watermark.width) // 2, (base_image.height - watermark.height) // 2
            
        base_image.paste(watermark, (x, y), watermark)
        
        formato = os.path.splitext(ruta_destino)[1].lstrip('.').lower()
        if formato in ['jpg', 'jpeg']:
            base_image = base_image.convert("RGB")
            base_image.save(ruta_destino, quality=95)
        else:
            base_image.save(ruta_destino)
            
        return f"✅ Marca de agua aplicada: {os.path.basename(ruta_destino)}"

    @staticmethod
    def _watermark_video(ruta_origen, ruta_destino, watermark_path, position, opacity):
        import subprocess, os
        ffmpeg_path = _find_ffmpeg()
        if not ffmpeg_path:
            return "❌ ffmpeg no está disponible."
            
        margin_expr = "main_w*0.03"
        if position == "top-left":
            overlay = f"overlay={margin_expr}:{margin_expr}"
        elif position == "top-right":
            overlay = f"overlay=main_w-overlay_w-{margin_expr}:{margin_expr}"
        elif position == "bottom-left":
            overlay = f"overlay={margin_expr}:main_h-overlay_h-{margin_expr}"
        elif position == "bottom-right":
            overlay = f"overlay=main_w-overlay_w-{margin_expr}:main_h-overlay_h-{margin_expr}"
        elif position == "center":
            overlay = "overlay=(main_w-overlay_w)/2:(main_h-overlay_h)/2"
            
        opc = opacity / 100.0
        
        filter_complex = f"[1:v]format=rgba,colorchannelmixer=aa={opc}[wm];[0:v][wm]{overlay}"
        
        cmd = [
            ffmpeg_path, "-y",
            "-i", ruta_origen,
            "-i", watermark_path,
            "-filter_complex", filter_complex,
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "copy",
            ruta_destino
        ]
        
        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
        try:
            subprocess.run(cmd, check=True, startupinfo=startupinfo, capture_output=True, text=True)
            return f"✅ Marca de agua aplicada: {os.path.basename(ruta_destino)}"
        except subprocess.CalledProcessError as e:
            return f"⚠️ Error en FFmpeg: {e.stderr}"
