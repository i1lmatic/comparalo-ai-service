"""Modelos de datos (Pydantic) usados en toda la app."""
from typing import Literal, Optional, List
from pydantic import BaseModel


class ResultadoTienda(BaseModel):
    """Resultado del scraping de UNA tienda.

    El campo `estado` permite que el frontend distinga entre
    'no se encontró precio' y 'la tienda nos bloqueó / falló'.
    """
    tienda: str
    estado: Literal["ok", "sin_resultados", "timeout", "error"] = "ok"
    precio: Optional[float] = None
    moneda: str = "PEN"
    titulo: Optional[str] = None
    url: Optional[str] = None
    detalle: Optional[str] = None  # mensaje de error si estado != ok


class ProductoIdentificado(BaseModel):
    marca: Optional[str] = None
    modelo: Optional[str] = None
    categoria: Optional[str] = None

    @property
    def nombre_busqueda(self) -> str:
        return f"{self.marca or ''} {self.modelo or ''}".strip()


class RespuestaIdentificacion(BaseModel):
    """Lo que devuelve POST /identify."""
    producto: ProductoIdentificado
    termino_busqueda: str
    resultados: List[ResultadoTienda]
    mejor_precio: Optional[ResultadoTienda] = None
