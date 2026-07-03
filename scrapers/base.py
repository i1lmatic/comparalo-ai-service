"""Patrón Strategy para scrapers de tiendas.

Toda la lógica común (crear contexto sigiloso, navegar, bloquear recursos,
timeouts, captura de errores) vive AQUÍ. Cada tienda concreta solo implementa
`construir_url()` y `extraer()`.
"""
import re
from abc import ABC, abstractmethod
from typing import Optional

from playwright.async_api import Browser, Page, TimeoutError as PlaywrightTimeout

from core.models import ResultadoTienda
from core.stealth import kwargs_contexto, espera_aleatoria, STEALTH_JS

# Tipos de recurso que bloqueamos para acelerar la carga y gastar menos ancho de banda.
RECURSOS_BLOQUEADOS = {"image", "media", "font"}


class BaseScraper(ABC):
    tienda: str = "Desconocida"
    timeout: int = 25000  # ms para goto / wait_for_selector (nube es mas lenta)
    bloquear_recursos: bool = True

    # ---- Métodos que CADA tienda debe implementar -------------------------

    @abstractmethod
    def construir_url(self, query: str) -> str:
        """Devuelve la URL de búsqueda de la tienda para el término dado."""

    @abstractmethod
    async def extraer(self, page: Page) -> Optional[dict]:
        """Extrae el primer resultado de la página ya cargada.

        Debe devolver {'precio': float, 'titulo': str, 'url': str}
        o None si no encontró nada.
        """

    # ---- Lógica común (no se toca al añadir tiendas) ----------------------

    async def scrape(self, browser: Browser, query: str, semaforo) -> ResultadoTienda:
        """Orquesta el scraping de esta tienda de forma resiliente.

        Nunca lanza excepción: siempre devuelve un ResultadoTienda con su
        `estado`, para que un fallo no rompa el asyncio.gather del resto.
        """
        async with semaforo:  # limita cuántas tiendas corren a la vez
            context = await browser.new_context(**kwargs_contexto())
            await context.add_init_script(STEALTH_JS)
            page = await context.new_page()
            try:
                if self.bloquear_recursos:
                    await page.route("**/*", self._filtrar_recursos)

                await espera_aleatoria(0.3, 1.0)  # jitter antes de navegar
                url = self.construir_url(query)
                await page.goto(url, wait_until="domcontentloaded", timeout=self.timeout)
                await espera_aleatoria(0.5, 1.5)  # deja que renderice / parezca humano

                datos = await self.extraer(page)
                if not datos or datos.get("precio") is None:
                    return ResultadoTienda(tienda=self.tienda, estado="sin_resultados")

                return ResultadoTienda(tienda=self.tienda, estado="ok", **datos)

            except PlaywrightTimeout:
                return ResultadoTienda(
                    tienda=self.tienda, estado="timeout",
                    detalle="La tienda no respondió a tiempo (posible bloqueo).",
                )
            except Exception as e:
                return ResultadoTienda(tienda=self.tienda, estado="error", detalle=str(e))
            finally:
                await context.close()

    async def _filtrar_recursos(self, route) -> None:
        if route.request.resource_type in RECURSOS_BLOQUEADOS:
            await route.abort()
        else:
            await route.continue_()

    # ---- Helpers compartidos para las subclases ---------------------------

    @staticmethod
    def parsear_precio(texto: str) -> Optional[float]:
        """Convierte 'S/ 1,299.00' o '1.299,00' a float. Tolerante a basura."""
        if not texto:
            return None
        # Quita todo menos dígitos, puntos y comas.
        limpio = re.sub(r"[^\d.,]", "", texto)
        if not limpio:
            return None
        # Si hay ambos separadores, el último es el decimal.
        if "," in limpio and "." in limpio:
            if limpio.rfind(",") > limpio.rfind("."):
                limpio = limpio.replace(".", "").replace(",", ".")
            else:
                limpio = limpio.replace(",", "")
        else:
            limpio = limpio.replace(",", "")
        try:
            return float(limpio)
        except ValueError:
            return None

    @staticmethod
    async def texto_de(page: Page, *selectores: str, timeout: int = 5000) -> Optional[str]:
        """Devuelve el texto del primer selector que aparezca. Robusto ante cambios de DOM."""
        for sel in selectores:
            try:
                el = await page.wait_for_selector(sel, timeout=timeout, state="attached")
                if el:
                    texto = (await el.inner_text()).strip()
                    if texto:
                        return texto
            except PlaywrightTimeout:
                continue
        return None
