"""Módulo de IA: identificación de hardware desde una imagen.

Motor: Google Gemini 2.0 Flash (visión) vía google-generativeai.
Devuelve marca, modelo, categoría y un término de búsqueda optimizado
para los scrapers de e-commerce.

Diseño:
- Carga perezosa: el modelo se crea en el primer uso, no al importar.
  Así FastAPI arranca aunque Gemini tarde o la key falte.
- Reintentos con backoff exponencial ante fallos transitorios.
- Respuesta normalizada y validada antes de devolverla.
"""
import io
import json
import logging
import os
import time
from typing import Dict

import google.generativeai as genai
from dotenv import load_dotenv
import PIL.Image

load_dotenv()

logger = logging.getLogger(__name__)

NOMBRE_MODELO = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
MAX_INTENTOS = 3

CATEGORIAS_VALIDAS = {
    "monitor", "mouse", "teclado", "laptop",
    "audifonos", "webcam", "otro",
}

# Sinónimos comunes que Gemini puede devolver -> categoría canónica.
SINONIMOS_CATEGORIA = {
    "portatil": "laptop", "portátil": "laptop", "notebook": "laptop",
    "computadora": "laptop", "pc": "laptop", "ultrabook": "laptop",
    "pantalla": "monitor", "display": "monitor", "tv": "monitor",
    "tecles": "teclado", "keyboard": "teclado",
    "raton": "mouse", "ratón": "mouse",
    "auriculares": "audifonos", "auriculares": "audifonos",
    "headset": "audifonos", "cascos": "audifonos",
    "camara": "webcam", "cámara": "webcam", "cam": "webcam",
}

PROMPT_IDENTIFICACION = (
    "Actúa como un experto en hardware informático. Analiza la imagen y "
    "identifica el componente que se ve. Responde SOLO en JSON con esta "
    "estructura exacta:\n"
    "{\n"
    '  "categoria": "monitor | mouse | teclado | laptop | audifonos | webcam | otro",\n'
    '  "marca": "marca exacta del fabricante o null",\n'
    '  "modelo": "modelo o referencia exacta o null",\n'
    '  "termino_busqueda": "frase concisa para buscar precios en tiendas peruanas"\n'
    "}\n"
    "Reglas:\n"
    "- termino_busqueda debe ser marca + modelo (+ categoría si faltan los anteriores), "
    "sin palabras de relleno como 'comprar', 'precio', 'online'.\n"
    "- Si NO es un componente informático, usa categoria='otro' y el resto null.\n"
    "- Si no reconoces marca/modelo, pon null y usa la categoría como termino_busqueda.\n\n"
    "Ejemplos de salida correcta:\n"
    'Ejemplo 1 (mouse Logitech G502): {"categoria":"mouse","marca":"Logitech","modelo":"G502","termino_busqueda":"Logitech G502 mouse"}\n'
    'Ejemplo 2 (monitor Samsung sin modelo visible): {"categoria":"monitor","marca":"Samsung","modelo":null,"termino_busqueda":"Samsung monitor"}\n'
    'Ejemplo 3 (teclado genérico sin marca legible): {"categoria":"teclado","marca":null,"modelo":null,"termino_busqueda":"teclado"}\n'
    'Ejemplo 4 (foto de un zapato, no es hardware): {"categoria":"otro","marca":null,"modelo":null,"termino_busqueda":null}'
)

# Instancia única del modelo, creada bajo demanda.
_model = None


def _get_model():
    """Crea (una sola vez) el modelo de Gemini configurado para devolver JSON."""
    global _model
    if _model is None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("No se encontró GEMINI_API_KEY en el archivo .env")
        genai.configure(api_key=api_key)
        _model = genai.GenerativeModel(
            model_name=NOMBRE_MODELO,
            generation_config={"response_mime_type": "application/json"},
        )
        logger.info("Modelo Gemini '%s' inicializado.", NOMBRE_MODELO)
    return _model


def _con_reintentos(fn):
    """Ejecuta fn con reintentos y backoff exponencial (1s, 2s, 4s)."""
    ultimo_error = None
    for intento in range(1, MAX_INTENTOS + 1):
        try:
            return fn()
        except Exception as e:
            ultimo_error = e
            if intento == MAX_INTENTOS:
                break
            espera = 2 ** (intento - 1)
            logger.warning("Gemini falló (intento %d/%d): %s. Reintentando en %ds...",
                           intento, MAX_INTENTOS, e, espera)
            time.sleep(espera)
    raise ultimo_error


def _normalizar(info: Dict) -> Dict:
    """Garantiza que el dict tenga todas las claves esperadas y categoría válida."""
    for k in ("categoria", "marca", "modelo", "termino_busqueda"):
        info.setdefault(k, None)
    # Normaliza categoría: minúsculas, sinónimos y validación.
    cat = (info.get("categoria") or "").strip().lower()
    # Si Gemini devuelve una frase (ej. "portátil para juegos"), extrae la 1ª palabra clave.
    for palabra in cat.split():
        if palabra in SINONIMOS_CATEGORIA:
            cat = SINONIMOS_CATEGORIA[palabra]
            break
        if palabra in CATEGORIAS_VALIDAS:
            cat = palabra
            break
    if cat not in CATEGORIAS_VALIDAS:
        cat = "otro"
    info["categoria"] = cat
    # Limpia nulos string ("null" textual) a None real.
    for k in ("marca", "modelo", "termino_busqueda"):
        val = info.get(k)
        if isinstance(val, str):
            val = val.strip()
            if val.lower() in ("null", "none", ""):
                val = None
        info[k] = val
    # Si no hay término de búsqueda, deriva uno básico.
    if not info["termino_busqueda"]:
        info["termino_busqueda"] = (
            f"{info['marca'] or ''} {info['modelo'] or ''}".strip()
            or info["categoria"]
        )
    return info


def _identificar(img: PIL.Image.Image) -> Dict:
    """Llama a Gemini, parsea el JSON y normaliza la respuesta."""
    model = _get_model()

    def call():
        return model.generate_content([PROMPT_IDENTIFICACION, img]).text

    crudo = _con_reintentos(call)
    try:
        info = json.loads(crudo)
    except (json.JSONDecodeError, TypeError) as e:
        raise ValueError(f"La IA devolvió un JSON inválido: {e}") from e

    if not isinstance(info, dict):
        raise ValueError("La IA devolvió un JSON que no es un objeto.")

    return _normalizar(info)


def identificar_hardware(ruta_imagen: str) -> Dict:
    """Identifica desde una ruta en disco (uso por CLI / pruebas)."""
    try:
        return _identificar(PIL.Image.open(ruta_imagen))
    except Exception as e:
        return {"error": str(e)}


def identificar_desde_bytes(datos: bytes) -> Dict:
    """Identifica desde bytes de imagen (uso por el endpoint de FastAPI)."""
    try:
        return _identificar(PIL.Image.open(io.BytesIO(datos)))
    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    nombre_foto_prueba = "prueba.jpg"
    if os.path.exists(nombre_foto_prueba):
        resultado = identificar_hardware(nombre_foto_prueba)
        print(json.dumps(resultado, indent=2, ensure_ascii=False))
    else:
        print(f"⚠️ Sube una imagen llamada '{nombre_foto_prueba}'")
