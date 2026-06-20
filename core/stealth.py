"""Utilidades de evasión anti-bot: User-Agents, esperas y contexto sigiloso."""
import asyncio
import random

# Pool de User-Agents reales y recientes. Se rota uno por contexto/tienda.
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
]

# Viewports comunes para que cada contexto no luzca idéntico.
VIEWPORTS = [
    {"width": 1920, "height": 1080},
    {"width": 1536, "height": 864},
    {"width": 1440, "height": 900},
    {"width": 1366, "height": 768},
]

# Script que se inyecta ANTES de cargar la página para ocultar señales
# típicas de automatización (navigator.webdriver, etc.).
STEALTH_JS = """
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
Object.defineProperty(navigator, 'languages', { get: () => ['es-PE', 'es'] });
Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
window.chrome = { runtime: {} };
"""


def kwargs_contexto() -> dict:
    """Devuelve kwargs aleatorizados para browser.new_context()."""
    return {
        "user_agent": random.choice(USER_AGENTS),
        "viewport": random.choice(VIEWPORTS),
        "locale": "es-PE",
        "timezone_id": "America/Lima",
        "extra_http_headers": {
            "Accept-Language": "es-PE,es;q=0.9,en;q=0.8",
        },
    }


async def espera_aleatoria(minimo: float = 0.4, maximo: float = 1.5) -> None:
    """Pausa aleatoria para imitar comportamiento humano y espaciar requests."""
    await asyncio.sleep(random.uniform(minimo, maximo))
