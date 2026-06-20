"""Orquestador: lanza todas las tiendas en paralelo con asyncio.gather."""
import asyncio
from typing import List, Optional

from core.browser import gestor_navegador
from core.models import ResultadoTienda
from scrapers.registry import SCRAPERS_ACTIVOS

# Cuántas tiendas consultar simultáneamente. Subir gasta más RAM/CPU;
# bajar reduce el riesgo de parecer un bot agresivo.
MAX_CONCURRENTES = 4


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

    # Orden: primero los 'ok' (más barato arriba), luego el resto.
    resultados.sort(key=lambda r: (r.estado != "ok", r.precio if r.precio else float("inf")))
    return resultados


def mejor_precio(resultados: List[ResultadoTienda]) -> Optional[ResultadoTienda]:
    ok = [r for r in resultados if r.estado == "ok" and r.precio is not None]
    return min(ok, key=lambda r: r.precio) if ok else None
