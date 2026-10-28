"""Data source adapters package for external marine information providers."""

from app.adapters.base import BaseMarineDataAdapter
from app.adapters.incois import INCOISAdapter
from app.adapters.ocean_data import OceanDataAdapter
from app.adapters.open_meteo_marine import OpenMeteoMarineAdapter

__all__ = [
    "BaseMarineDataAdapter",
    "INCOISAdapter",
    "OceanDataAdapter",
    "OpenMeteoMarineAdapter",
]
