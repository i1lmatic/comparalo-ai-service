"""Scraper de Amazon. Solo URL + selectores; lo demás lo hereda de BaseScraper.

NOTA: los selectores de e-commerce cambian seguido. Si una tienda deja de
devolver precios, casi siempre es aquí donde hay que actualizar.
"""
from urllib.parse import quote_plus
from typing import Optional

from playwright.async_api import Page
from scrapers.base import BaseScraper


class AmazonScraper(BaseScraper):
    tienda = "Amazon"

    def construir_url(self, query: str) -> str:
        return f"https://www.amazon.com/s?k={quote_plus(query)}"

    async def extraer(self, page: Page) -> Optional[dict]:
        # Primer resultado orgánico (no patrocinado, idealmente).
        tarjeta = "div[data-component-type='s-search-result']"
        await page.wait_for_selector(tarjeta, timeout=self.timeout)
        primero = page.locator(tarjeta).first

        entero = await self.texto_de(page, ".a-price-whole")
        fraccion = await self.texto_de(page, ".a-price-fraction")
        if entero is None:
            return None
        precio = self.parsear_precio(f"{entero}.{fraccion or '0'}")

        titulo = None
        try:
            titulo = (await primero.locator("h2 span").first.inner_text()).strip()
        except Exception:
            pass

        url = page.url
        try:
            href = await primero.locator("a.a-link-normal").first.get_attribute("href")
            if href:
                url = f"https://www.amazon.com{href}" if href.startswith("/") else href
        except Exception:
            pass

        return {"precio": precio, "titulo": titulo, "url": url}
