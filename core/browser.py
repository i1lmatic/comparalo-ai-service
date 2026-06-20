"""Gestor de un único navegador Playwright compartido por toda la app.

En lugar de lanzar un Chromium por tienda (caro y lento), lanzamos UNO solo
al arrancar FastAPI y cada scraper crea su propio *contexto* aislado
(cookies/UA separados). Se inicia y se cierra con el lifespan de la app.
"""
from playwright.async_api import async_playwright, Browser

# Flags que reducen la huella de automatización y el consumo de recursos.
ARGS_NAVEGADOR = [
    "--disable-blink-features=AutomationControlled",
    "--no-sandbox",
    "--disable-dev-shm-usage",
    "--disable-gpu",
]


class GestorNavegador:
    def __init__(self) -> None:
        self._playwright = None
        self._browser: Browser | None = None

    async def iniciar(self) -> None:
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=True,
            args=ARGS_NAVEGADOR,
        )

    async def cerrar(self) -> None:
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()

    @property
    def browser(self) -> Browser:
        if self._browser is None:
            raise RuntimeError("El navegador no está iniciado. Llama a iniciar() primero.")
        return self._browser


# Instancia global que comparte la app.
gestor_navegador = GestorNavegador()
