"""Orquestador: lanza todas las tiendas en paralelo con asyncio.gather.

Responsabilidades:
- Ejecutar los scrapers en paralelo (con semáforo de concurrencia).
- Normalizar la moneda: convierte USD a PEN con tipo de cambio configurable.
- Filtrar resultados irrelevantes por similitud (fuzzy) entre el término de
  búsqueda y el título del producto encontrado.
- Ordenar: primero los 'ok' (más barato arriba), luego el resto.
"""
import asyncio
import os
import re
from typing import List, Optional

from core.browser import gestor_navegador
from core.models import ResultadoTienda
from scrapers.registry import SCRAPERS_ACTIVOS

# Cuántas tiendas consultar simultáneamente. Subir gasta más RAM/CPU;
# bajar reduce el riesgo de parecer un bot agresivo.
MAX_CONCURRENTES = 4

# Tipo de cambio USD -> PEN. Configurable por .env para mantenerlo fresco.
TIPO_CAMBIO_USD_PEN = float(os.getenv("TIPO_CAMBIO_USD_PEN", "3.75"))

# Umbral mínimo de relevancia (0-100). Por debajo, el resultado se descarta.
UMBRAL_RELEVANCIA = 35

# Palabras muy comunes que no aportan a la comparación de títulos.
_STOPWORDS = {
    "de", "la", "el", "en", "con", "para", "y", "the", "of", "for", "and",
    "gamer", "original", "nuevo", "new", "envio", "gratis", "envío",
}


def _tokenizar(texto: str) -> List[str]:
    """Tokeniza en palabras alfanuméricas en minúsculas, sin stopwords."""
    if not texto:
        return []
    tokens = re.findall(r"[a-z0-9]+", texto.lower())
    return [t for t in tokens if t not in _STOPWORDS and len(t) > 1]


def _relevancia(termino: str, titulo: Optional[str]) -> int:
    """Score 0-100 tipo F1 entre los tokens del término y los del título."""
    if not titulo:
        return 0
    t_term = set(_tokenizar(termino))
    t_tit = set(_tokenizar(titulo))
    if not t_term or not t_tit:
        return 0
    comunes = t_term & t_tit
    if not comunes:
        return 0
    precision = len(comunes) / len(t_tit)
    recall = len(comunes) / len(t_term)
    f1 = 2 * precision * recall / (precision + recall)
    return int(f1 * 100)


def _normalizar_moneda(r: ResultadoTienda) -> ResultadoTienda:
    """Convierte precios en USD a PEN para que todo sea comparable."""
    if r.estado == "ok" and r.precio is not None and r.moneda == "USD":
        r.precio = round(r.precio * TIPO_CAMBIO_USD_PEN, 2)
        r.moneda = "PEN"
    return r


def _filtrar_relevancia(r: ResultadoTienda, termino: str) -> ResultadoTienda:
    """Calcula relevancia y descarta resultados poco pertinentes."""
    if r.estado != "ok":
        return r
    score = _relevancia(termino, r.titulo)
    r.relevancia = score
    if score < UMBRAL_RELEVANCIA:
        r.estado = "sin_resultados"
        r.detalle = f"no relevante (score {score})"
    return r


async def buscar_precios(query: str, scrapers=None) -> List[ResultadoTienda]:
    """Consulta todas las tiendas en paralelo y devuelve sus resultados.

    Resiliente: si una tienda falla, las demás continúan (return_exceptions).
    """
    scrapers = scrapers or SCRAPERS_ACTIVOS
    semaforo = asyncio.Semaphore(MAX_CONCURRENTES)
    browser = gestor_navegador.browser

    tareas = [s.scrape(browser, query, semaforo) for s in scrapers]
    crudos = await asyncio.gather(*tareas, return_exceptions=True)

    resultados: List[ResultadoTienda] = []
    for scraper, res in zip(scrapers, crudos):
        if isinstance(res, ResultadoTienda):
            resultados.append(res)
        else:  # excepción que se escapó del scrape() (no debería pasar)
            resultados.append(
                ResultadoTienda(tienda=scraper.tienda, estado="error", detalle=str(res))
            )

    # Post-procesamiento: moneda y relevancia.
    resultados = [
        _filtrar_relevancia(_normalizar_moneda(r), query) for r in resultados
    ]

    # Orden: primero los 'ok' (más barato arriba), luego el resto.
    resultados.sort(key=lambda r: (r.estado != "ok", r.precio if r.precio else float("inf")))
    return resultados


def mejor_precio(resultados: List[ResultadoTienda]) -> Optional[ResultadoTienda]:
    ok = [r for r in resultados if r.estado == "ok" and r.precio is not None]
    return min(ok, key=lambda r: r.precio) if ok else None
