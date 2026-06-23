"""Punto de entrada para desarrollo con recarga en caliente.

Uso:
    python run.py

Nota: no uses `uvicorn main:app --reload` directamente en Windows porque
uvicorn fuerza SelectorEventLoop (incompatible con Playwright). Este script
pasa el loop factory correcto (--loop core.event_loop:factory).
"""
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        reload=True,
        loop="core.event_loop:factory",
        host="127.0.0.1",
        port=8000,
    )
