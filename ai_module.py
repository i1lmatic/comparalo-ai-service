import os
import io
import google.generativeai as genai
from dotenv import load_dotenv
import PIL.Image

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("❌ ERROR: No se encontró la GEMINI_API_KEY en el archivo .env")

genai.configure(api_key=api_key)

def obtener_modelo_valido():
    """Busca el modelo Flash más reciente disponible en tu cuenta."""
    try:
        for m in genai.list_models():
            # Buscamos el modelo que sea 'flash' y permita generar contenido
            if 'generateContent' in m.supported_generation_methods:
                if 'flash' in m.name.lower():
                    print(f"✅ Usando modelo encontrado: {m.name}")
                    return m.name
        return "gemini-1.5-flash" # Fallback por si acaso
    except Exception as e:
        print(f"⚠️ Error al listar modelos: {e}")
        return "gemini-1.5-flash"

# Configuramos el modelo con el nombre que encontremos
NOMBRE_MODELO = obtener_modelo_valido()
model = genai.GenerativeModel(
    model_name=NOMBRE_MODELO,
    generation_config={"response_mime_type": "application/json"}
)

PROMPT_IDENTIFICACION = (
    "Actúa como un experto en hardware. Identifica marca, modelo y categoría. "
    "Responde solo en JSON: {'marca': '...', 'modelo': '...', 'categoria': '...'}"
)


def _identificar(img: PIL.Image.Image) -> str:
    response = model.generate_content([PROMPT_IDENTIFICACION, img])
    return response.text


def identificar_hardware(ruta_imagen: str) -> str:
    """Identifica desde una ruta en disco (uso por CLI / pruebas)."""
    try:
        return _identificar(PIL.Image.open(ruta_imagen))
    except Exception as e:
        return f'{{"error": "{str(e)}"}}'


def identificar_desde_bytes(datos: bytes) -> str:
    """Identifica desde bytes de imagen (uso por el endpoint de FastAPI)."""
    try:
        return _identificar(PIL.Image.open(io.BytesIO(datos)))
    except Exception as e:
        return f'{{"error": "{str(e)}"}}'

if __name__ == "__main__":
    nombre_foto_prueba = "prueba.jpg" 
    if os.path.exists(nombre_foto_prueba):
        print(identificar_hardware(nombre_foto_prueba))
    else:
        print(f"⚠️ Sube una imagen llamada '{nombre_foto_prueba}'")