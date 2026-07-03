"""Scraper de Amazon. Solo URL + selectores; lo demás lo hereda de BaseScraper.

NOTA: los selectores de e-commerce cambian seguido. Si una tienda deja de
devolver precios, casi siempre es aquí donde hay que actualizar.
"""
from urllib.parse import quote_plus
from typing import Optional

from playwright.async_api import Page, TimeoutError as PlaywrightTimeout
from scrapers.base import BaseScraper


class AmazonScraper(BaseScraper):
    tienda = "Amazon"

    def construir_url(self, query: str) -> str:
        return f"https://www.amazon.com/s?k={quote_plus(query)}"

    async def extraer(self, page: Page) -> Optional[dict]:
        # Espera a que aparezca al menos un resultado de búsqueda.
        tarjeta = "div[data-component-type='s-search-result']"
        await page.wait_for_selector(tarjeta, timeout=self.timeout)

        # Itera los resultados y se queda con el PRIMERO que tenga precio.
        # El primer card a veces es patrocinado o no renderiza precio.
        total = await page.locator(tarjeta).count()
        for i in range(min(total, 8)):  # revisa hasta 8 cards
            card = page.locator(tarjeta).nth(i)

            # .a-offscreen trae el precio completo (ej. "$29.99") en un solo texto.
            precio_txt = None
            try:
                precio_txt = await card.locator(".a-offscreen").first.inner_text(timeout=3000)
            except PlaywrightTimeout:
                continue
            if not precio_txt:
                continue

            precio = self.parsear_precio(precio_txt)
            if precio is None:
                continue

            # Título del resultado actual.
            titulo = None
            try:
                titulo = (await card.locator("h2 span").first.inner_text(timeout=3000)).strip()
            except PlaywrightTimeout:
                pass

            # URL del producto.
            url = page.url
            try:
                href = await card.locator("a.a-link-normal").first.get_attribute("href", timeout=3000)
                if href:
                    url = f"https://www.amazon.com{href}" if href.startswith("/") else href
            except PlaywrightTimeout:
                pass

            return {"precio": precio, "titulo": titulo, "url": url, "moneda": "USD"}

        return None
