"""Scraper de Falabella Perú."""
from urllib.parse import quote_plus
from typing import Optional

from playwright.async_api import Page
from scrapers.base import BaseScraper


class FalabellaScraper(BaseScraper):
    tienda = "Falabella"

    def construir_url(self, query: str) -> str:
        return f"https://www.falabella.com.pe/falabella-pe/search?Ntt={quote_plus(query)}"

    async def extraer(self, page: Page) -> Optional[dict]:
        # Falabella renderiza con JS; esperamos a que aparezca cualquier precio.
        precio_txt = await self.texto_de(
            page,
            "[data-internet-price]",
            "span[class*='copy10']",          # clase típica de precio
            "li[class*='pod'] span[class*='price']",
            timeout=self.timeout,
        )
        if precio_txt is None:
            return None
        precio = self.parsear_precio(precio_txt)

        titulo = await self.texto_de(
            page, "b[class*='pod-subTitle']", "a[class*='pod-link'] b"
        )

        url = page.url
        try:
            href = await page.locator("a[class*='pod-link']").first.get_attribute("href")
            if href:
                url = href if href.startswith("http") else f"https://www.falabella.com.pe{href}"
        except Exception:
            pass

        return {"precio": precio, "titulo": titulo, "url": url, "moneda": "PEN"}
