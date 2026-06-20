"""Registro de tiendas activas.

Para añadir una tienda nueva: crea su archivo (hereda BaseScraper) e
inclúyela en esta lista. Nada más cambia en el resto de la app.
"""
from scrapers.amazon import AmazonScraper
from scrapers.falabella import FalabellaScraper
from scrapers.hiraoka import HiraokaScraper

SCRAPERS_ACTIVOS = [
    AmazonScraper(),
    FalabellaScraper(),
    HiraokaScraper(),
]
