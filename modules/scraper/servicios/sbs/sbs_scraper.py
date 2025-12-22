"""
SBS Scraper Module
Módulo robusto para extracción, limpieza y disponibilización de tasas activas de la SBS
"""

import asyncio
import sys
import platform
from bs4 import BeautifulSoup
import pandas as pd
from datetime import date, timedelta
import time
import logging
from typing import Optional

from modules.enum.sbs.slice_tipo_credito import Slice_Tipo_Credito
from modules.enum.sbs.indice_tipo_credito import Corporativo, Grandes_Empresas, Medianas_Empresas, Pequenas_Empresas, Micro_Empresas, Consumo, Hipotecarios
from modules.enum.sbs.columna_banco import Columna_Banco
from modules.enum.sbs.tipo_moneda import Tipo_Moneda

# Configurar event loop para Windows
if platform.system() == 'Windows':
    if sys.version_info >= (3, 8):
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SBSScraper:
    """
    Clase principal para scraping de tasas activas de la SBS
    """
    
    def __init__(self, interpretador_html, extractor_moneda_nacional, extractor_moneda_extranjera):
        self._interpretador_html = interpretador_html
        self._extractor_moneda_nacional = extractor_moneda_nacional
        self._extractor_moneda_extranjera = extractor_moneda_extranjera
        
    async def _obtener_bs4_de_sbs(self, retries: int = 3, fecha: Optional[date] = None) -> Optional[BeautifulSoup]:
        """
        Realiza solicitud HTTP con Playwright y retorna BeautifulSoup
        """
        for attempt in range(retries):
            try:
                soup = BeautifulSoup(await self._interpretador_html().solicitar(fecha), 'lxml')
                return soup
                
            except Exception as e:
                logger.error(f"Error en solicitud con Playwright (intento {attempt + 1}): {e}")
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)  # Backoff exponencial
                continue
                
        logger.error("No se pudo conectar a SBS después de todos los reintentos")
        return None
    
    def _extraer_tabla_nacional(self, soup: BeautifulSoup) -> pd.DataFrame:
        """
        Extrae datos de la tabla principal de tasas
        """
        tabla = self._extractor_moneda_nacional(soup).obtener()

        logger.info(f"Se extrajeron {len(tabla)} filas de datos")
        return tabla

    def _extraer_tabla_extranjera(self, soup: BeautifulSoup) -> pd.DataFrame:
        """
        Extrae datos de la tabla principal de tasas
        """
        tabla = self._extractor_moneda_extranjera(soup).obtener()

        logger.info(f"Se extrajeron {len(tabla)} filas de datos")
        return tabla
    
    def _obtener_extractor(self, moneda: Tipo_Moneda):
        return [self._extraer_tabla_nacional, self._extraer_tabla_extranjera][moneda.value]
    
    async def get_tasas_activas(self, fecha: Optional[date] = None, moneda: Tipo_Moneda = Tipo_Moneda.NACIONAL) -> pd.DataFrame:
        soup = await self._obtener_bs4_de_sbs(fecha=fecha)
        if not soup:
            logger.error("No se pudo obtener la página de SBS")
            return pd.DataFrame()

        extractor = self._obtener_extractor(moneda)

        raw_data = extractor(soup)
        if raw_data.empty:
            logger.warning("No se extrajeron datos de la tabla")
            return pd.DataFrame()
        
        logger.info(f"Extracción completada: {len(raw_data)} registros obtenidos")
        return raw_data

    async def get_tasas(self, slice_tipo_credito: Slice_Tipo_Credito, moneda: Tipo_Moneda = Tipo_Moneda.NACIONAL) -> pd.DataFrame:
        tabla = await self.get_tasas_activas(moneda=moneda)
        return tabla[slice_tipo_credito.value]

    async def get_bancos(self, moneda: Tipo_Moneda = Tipo_Moneda.NACIONAL) -> pd.Series:
        tabla = await self.get_tasas_activas(moneda=moneda)
        return pd.Series(tabla.columns)

    async def get_tea(self, banco: Columna_Banco, credito: Corporativo | Grandes_Empresas | Medianas_Empresas | Pequenas_Empresas | Micro_Empresas | Consumo | Hipotecarios, moneda: Tipo_Moneda = Tipo_Moneda.NACIONAL) -> float:
        tabla = await self.get_tasas_activas(moneda=moneda)
        return tabla.iloc[credito.value, banco.value]

    async def get_promedio(self, tipo_credito: Corporativo | Grandes_Empresas | Medianas_Empresas | Pequenas_Empresas | Micro_Empresas | Consumo | Hipotecarios, moneda: Tipo_Moneda = Tipo_Moneda.NACIONAL) -> float:
        tabla = await self.get_tasas_activas(moneda=moneda)
        return tabla.iloc[tipo_credito.value, Columna_Banco.PROMEDIO.value]

    async def obtener_tasa_actualizada(self, fecha: date, moneda: Tipo_Moneda = Tipo_Moneda.NACIONAL):
        return await self.get_tasas_activas(fecha=fecha, moneda=moneda)