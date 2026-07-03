"""ComparaLO - API REST.

Flujo: Imagen -> Identificación IA (Gemini) -> Scraping concurrente -> JSON.

Levantar en desarrollo:
    python run.py
(o sin recarga en caliente):
    uvicorn main:app --port 8000
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, UploadFile, HTTPException

from ai_module import identificar_desde_bytes
from core.browser import gestor_navegador
from core.models import ProductoIdentificado, RespuestaIdentificacion
from scraping_service import buscar_precios, mejor_precio


def es_imagen_valida(datos: bytes) -> bool:
    """Valida por *magic bytes*, no por el content-type que manda el cliente.

    Soporta JPEG, PNG y WEBP. Es más fiable porque apps móviles a veces
    envían 'application/octet-stream' aunque el archivo sí sea una imagen.
    """
    if datos[:3] == b"\xff\xd8\xff":                      # JPEG
        return True
    if datos[:8] == b"\x89PNG\r\n\x1a\n":                 # PNG
        return True
    if datos[:4] == b"RIFF" and datos[8:12] == b"WEBP":   # WEBP
        return True
    return False


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Arranca el navegador UNA vez al iniciar la app...
    try:
        await gestor_navegador.iniciar()
    except Exception as e:
        logging.error("FALLO al iniciar el navegador: %s", e)
        raise
    yield
    # ...y lo cierra limpiamente al apagarla.
    await gestor_navegador.cerrar()


app = FastAPI(title="ComparaLO API", version="1.0.0", lifespan=lifespan)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/identify", response_model=RespuestaIdentificacion)
async def identify(file: UploadFile = File(...)):
    datos_imagen = await file.read()
    if not es_imagen_valida(datos_imagen):
        raise HTTPException(
            status_code=415,
            detail="El archivo no es una imagen válida. Usa JPEG, PNG o WEBP.",
        )

    # 1) IA identifica el producto.
    info = identificar_desde_bytes(datos_imagen)
    if "error" in info:
        raise HTTPException(status_code=502, detail=f"Error de IA: {info['error']}")
    if info.get("categoria") == "otro":
        raise HTTPException(
            status_code=422,
            detail="La imagen no parece un componente informático.",
        )

    producto = ProductoIdentificado(
        marca=info.get("marca"),
        modelo=info.get("modelo"),
        categoria=info.get("categoria"),
        termino_busqueda=info.get("termino_busqueda"),
    )
    termino = producto.nombre_busqueda
    if not termino:
        raise HTTPException(status_code=422, detail="La IA no pudo identificar el producto.")

    # 2) Scraping concurrente en todas las tiendas.
    resultados = await buscar_precios(termino)

    # 3) Respuesta JSON.
    return RespuestaIdentificacion(
        producto=producto,
        termino_busqueda=termino,
        resultados=resultados,
        mejor_precio=mejor_precio(resultados),
    )
