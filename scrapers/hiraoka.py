"""Scraper de Hiraoka (tienda Magento)."""
from urllib.parse import quote_plus
from typing import Optional

from playwright.async_api import Page
from scrapers.base import BaseScraper


class HiraokaScraper(BaseScraper):
    tienda = "Hiraoka"

    def construir_url(self, query: str) -> str:
        return f"https://hiraoka.com.pe/catalogsearch/result/?q={quote_plus(query)}"

    async def extraer(self, page: Page) -> Optional[dict]:
        # Magento usa .price dentro de la tarjeta del producto.
        primero = "li.product-item, ol.products li"
        await page.wait_for_selector(primero, timeout=self.timeout)

        precio_txt = await self.texto_de(
            page,
            "li.product-item .price-wrapper .price",
            "span[data-price-type='finalPrice'] .price",
            ".price",
            timeout=self.timeout,
        )
        if precio_txt is None:
            return None
        precio = self.parsear_precio(precio_txt)

        titulo = await self.texto_de(page, "a.product-item-link")

        url = page.url
        try:
            href = await page.locator("a.product-item-link").first.get_attribute("href")
            if href:
                url = href
        except Exception:
            pass

        return {"precio": precio, "titulo": titulo, "url": url, "moneda": "PEN"}
