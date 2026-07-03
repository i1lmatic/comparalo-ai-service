"""Gestor de un único navegador Playwright compartido por toda la app.

En lugar de lanzar un Chromium por tienda (caro y lento), lanzamos UNO solo
al arrancar FastAPI y cada scraper crea su propio *contexto* aislado
(cookies/UA separados). Se inicia y se cierra con el lifespan de la app.
"""
import logging

from playwright.async_api import async_playwright, Browser

logger = logging.getLogger(__name__)

# Flags que reducen la huella de automatización y el consumo de recursos.
# Optimizados para contenedores con RAM limitada (ej. Render free tier 512MB).
ARGS_NAVEGADOR = [
    "--disable-blink-features=AutomationControlled",
    "--no-sandbox",
    "--disable-dev-shm-usage",
    "--disable-gpu",
    "--disable-extensions",
    "--disable-background-networking",
    "--disable-background-timer-throttling",
    "--disable-renderer-backgrounding",
    "--disable-features=TranslateUI",
    "--disable-ipc-flooding-protection",
    "--memory-pressure-off",
]


class GestorNavegador:
    def __init__(self) -> None:
        self._playwright = None
        self._browser: Browser | None = None

    async def iniciar(self) -> None:
        logger.info("Iniciando navegador Playwright...")
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=True,
            args=ARGS_NAVEGADOR,
        )
        logger.info("Navegador Playwright iniciado correctamente.")

    async def cerrar(self) -> None:
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        logger.info("Navegador Playwright cerrado.")

    @property
    def browser(self) -> Browser:
        if self._browser is None:
            raise RuntimeError("El navegador no está iniciado. Llama a iniciar() primero.")
        return self._browser


# Instancia global que comparte la app.
gestor_navegador = GestorNavegador()
