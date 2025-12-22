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

from modules.scraper.bancos import columna_banco
from modules.scraper.tipos_credito.slice_tipo_credito import Slice_Tipo_Credito
from modules.scraper.tipos_credito.indice_tipo_credito import Corporativo, Grandes_Empresas, Medianas_Empresas, Pequenas_Empresas, Micro_Empresas, Consumo, Hipotecarios
from modules.scraper.bancos.columna_banco import Columna_Banco


# Configurar event loop para Windows
if platform.system() == 'Windows':
    if sys.version_info >= (3, 8):
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

#def handle_console(msg):
#    print(f"[browser console] {msg.type}: {msg.text}")

class SBSScraper:
    """
    Clase principal para scraping de tasas activas de la SBS
    """
    
    def __init__(self, interpretador_html, extractor_moneda_nacional):
        self.interpretador_html = interpretador_html
        self.extractor_moneda_nacional = extractor_moneda_nacional

        self.last_update = None
        self.cache_duration = timedelta(hours=1)  # Cache por 1 hora
        
    async def _obtener_bs4_de_sbs(self, retries: int = 3, fecha: Optional[date] = None) -> Optional[BeautifulSoup]:
        """
        Realiza solicitud HTTP con Playwright y retorna BeautifulSoup
        """
        for attempt in range(retries):
            try:
                soup = BeautifulSoup(await self.interpretador_html().solicitar(fecha), 'lxml')
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
        tabla = self.extractor_moneda_nacional(soup).obtener()

        logger.info(f"Se extrajeron {len(tabla)} filas de datos")
        return tabla
    
    async def get_tasas_activas(self, fecha: Optional[date] = None) -> pd.DataFrame:
        soup = await self._obtener_bs4_de_sbs(fecha=fecha)
        if not soup:
            logger.error("No se pudo obtener la página de SBS")
            return pd.DataFrame()
        
        raw_data = self._extraer_tabla_nacional(soup)
        if raw_data.empty:
            logger.warning("No se extrajeron datos de la tabla")
            return pd.DataFrame()
        
        logger.info(f"Extracción completada: {len(raw_data)} registros obtenidos")
        return raw_data

    async def get_tasas(self, slice_tipo_credito: Slice_Tipo_Credito) -> pd.DataFrame:
        tabla = await self.get_tasas_activas()
        return tabla[slice_tipo_credito.value]

    async def get_bancos(self) -> pd.Series:
        tabla = await self.get_tasas_activas()
        return pd.Series(tabla.columns)

    async def get_tea(self, banco: Columna_Banco, credito: Corporativo | Grandes_Empresas | Medianas_Empresas | Pequenas_Empresas | Micro_Empresas | Consumo | Hipotecarios) -> float:
        tabla = await self.get_tasas_activas()
        return tabla.iloc[credito.value, banco.value]

    async def get_promedio(self, tipo_credito: Corporativo | Grandes_Empresas | Medianas_Empresas | Pequenas_Empresas | Micro_Empresas | Consumo | Hipotecarios) -> float:
        tabla = await self.get_tasas_activas()
        return tabla.iloc[tipo_credito.value, Columna_Banco.PROMEDIO.value]

    async def obtener_tasa_actualizada(self, fecha: date):
        return await self.get_tasas_activas(fecha=fecha)

# Funciones de conveniencia para uso directo
def obtener_tasas_sbs() -> pd.DataFrame:
    """
    Función simplificada para obtener tasas de la SBS
    """
    scraper = SBSScraper()
    return scraper.get_tasas_activas()

def obtener_tasas_consumo() -> pd.DataFrame:
    """
    Obtiene tasas para créditos de consumo
    """
    scraper = SBSScraper()
    return scraper.get_tasas_por_tipo('Consumo')

def obtener_tasas_hipotecario() -> pd.DataFrame:
    """
    Obtiene tasas para créditos hipotecarios
    """
    scraper = SBSScraper()
    return scraper.get_tasas_por_tipo('Hipotecario')