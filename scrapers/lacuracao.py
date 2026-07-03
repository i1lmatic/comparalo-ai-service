"""Scraper de La Curacao."""
from urllib.parse import quote_plus
from typing import Optional

from playwright.async_api import Page
from scrapers.base import BaseScraper


class LaCuracaoScraper(BaseScraper):
    tienda = "La Curacao"

    def construir_url(self, query: str) -> str:
        # URL de búsqueda de La Curacao Perú (VTEX)
        return f"https://www.lacuracao.pe/{quote_plus(query)}?_q={quote_plus(query)}&map=ft"

    async def extraer(self, page: Page) -> Optional[dict]:
        # Esperamos al contenedor de productos (VTEX)
        primero = ".vtex-search-result-3-x-galleryItem, .vtex-product-summary-2-x-container"
        await page.wait_for_selector(primero, timeout=self.timeout)

        # Buscar el precio dentro de los selectores clásicos de VTEX
        precio_txt = await self.texto_de(
            page,
            ".vtex-productPrice-1-x-sellingPriceValue",
            ".vtex-product-summary-2-x-priceContainer .vtex-store-components-3-x-sellingPrice",
            timeout=self.timeout,
        )
        
        if precio_txt is None:
            return None
            
        precio = self.parsear_precio(precio_txt)

        # Buscar el título
        titulo = await self.texto_de(
            page, 
            ".vtex-product-summary-2-x-productNameContainer",
            ".vtex-product-summary-2-x-nameContainer"
        )

        # Buscar la URL (el href del primer enlace del producto)
        url = page.url
        try:
            href = await page.locator("a.vtex-product-summary-2-x-clearLink").first.get_attribute("href")
            if href:
                if href.startswith("/"):
                    url = f"https://www.lacuracao.pe{href}"
                else:
                    url = href
        except Exception:
            pass

        return {"precio": precio, "titulo": titulo, "url": url, "moneda": "PEN"}
