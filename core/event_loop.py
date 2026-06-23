"""Factory de event loop para Windows.

uvicorn --reload usa SelectorEventLoop en Windows (no soporta subprocesos),
lo que rompe Playwright (que necesita lanzar Chromium como subproceso).
Este factory fuerza ProactorEventLoop, que sí soporta subprocesos.

Se usa vía:  uvicorn main:app --reload --loop core.event_loop:factory
o automáticamente a través de run.py
"""
import asyncio


def factory() -> asyncio.AbstractEventLoop:
    return asyncio.ProactorEventLoop()
