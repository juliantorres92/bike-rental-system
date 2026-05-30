"""HTTP adapter package (driving side, FastAPI) for the rental domain (E-02).

This package is the ONLY place that imports FastAPI. The domain core never
depends on it. Reexports the app factory and composition root for clean imports:

    from bike_rental.adapters.api import create_app, InMemoryWorld
"""

from __future__ import annotations

from .app import create_app
from .composition import InMemoryWorld

__all__ = ["create_app", "InMemoryWorld"]
