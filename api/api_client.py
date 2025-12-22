"""
API Client para OptiCred
Cliente para consumir los endpoints del API Server (asíncrono para Streamlit)
"""

import aiohttp
import asyncio
from narwhals.stable.v1 import Series
import pandas as pd
from typing import Optional, Union
import logging
import streamlit as st
import json

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OptiCredAPIClient:
    """Cliente asíncrono para interactuar con la API de OptiCred"""
    
    def __init__(self, base_url: Optional[str] = None):
        """
        Inicializar el cliente API
        
        Args:
            base_url: URL base del servidor API (si no se proporciona, usa secrets.toml)
        """
        if base_url is None:
            try:
                base_url = st.secrets["api"]["base_url"]
            except (KeyError, FileNotFoundError):
                base_url = "http://localhost:8000"
                logger.warning(f"No se encontró base_url en secrets.toml, usando default: {base_url}")
        
        self.base_url = base_url.rstrip('/')
        self.session = None
        
    async def _make_request(self, endpoint: str):
        """
        Realizar una petición HTTP asíncrona al endpoint especificado y devolver su JSON
        """
        if self.session is None:
            self.session = aiohttp.ClientSession()

        url = f"{self.base_url}{endpoint}"
        try:
            async with self.session.get(url) as response:
                response.raise_for_status()
                return await response.json()
        except aiohttp.ClientError as e:
            logger.error(f"Error en petición a {url}: {str(e)}")
            raise
    
    async def close_session(self):
        """Cerrar la sesión HTTP"""
        if self.session is not None:
            await self.session.close()
            self.session = None
    
    def _json_to_dataframe(self, json_data: Union[str, dict]) -> pd.DataFrame:
        try:
            return pd.read_json(json_data, orient='split', typ='frame')
        except Exception as e:
            logger.error(f"Error al convertir JSON a DataFrame: {str(e)}")
            raise

    def _json_to_series(self, json_data: Union[str, dict]) -> pd.Series:
        try:
            return pd.read_json(json_data, orient='split', typ='series')
        except Exception as e:
            logger.error(f"Error al convertir JSON a Series: {str(e)}")
            raise
        
    async def get_tasas_activas(self) -> pd.DataFrame:
        """
        Obtener todas las tasas activas de la SBS
        
        Returns:
            pd.DataFrame: DataFrame con todas las tasas activas
        """
        logger.info("Obteniendo tasas activas...")
        json_data = await self._make_request("/tasas/activas")
        return self._json_to_dataframe(json_data)
    
    async def get_tasas_por_tipo(self, tipo_credito: str) -> pd.DataFrame:
        """
        Obtener tasas filtradas por tipo de crédito
        
        Args:
            tipo_credito: Tipo de crédito a filtrar
            
        Returns:
            pd.DataFrame: DataFrame con tasas filtradas
        """
        logger.info(f"Obteniendo tasas por tipo: {tipo_credito}")
        endpoint = f"/tasas/tipo/{tipo_credito}"
        json_data = await self._make_request(endpoint)
        return self._json_to_dataframe(json_data)
    
    async def get_bancos(self) -> pd.DataFrame:
        """
        Obtener lista de bancos disponibles
        
        Returns:
            pd.DataFrame: DataFrame con bancos
        """
        logger.info("Obteniendo lista de bancos...")
        json_data = await self._make_request("/bancos/")
        return self._json_to_series(json_data)
    
    async def get_tea(self, banco: str, tipo_credito: str, credito: str) -> float:
        """
        Obtener TEA para un banco, tipo de crédito y crédito específicos
        
        Args:
            banco: Nombre del banco
            tipo_credito: Tipo de crédito
            credito: Crédito específico
            
        Returns:
            float: Valor TEA
        """
        logger.info(f"Obteniendo TEA para {banco}/{tipo_credito}/{credito}")
        endpoint = f"/tea/{banco}/{tipo_credito}/{credito}"
        tea_value = await self._make_request(endpoint)
        return float(tea_value)
    
    async def get_promedio(self, tipo_credito: str, credito: str) -> float:
        """
        Obtener promedio de tasas para un tipo de crédito y crédito específicos
        
        Args:
            tipo_credito: Tipo de crédito
            credito: Crédito específico
            
        Returns:
            float: Valor promedio
        """
        logger.info(f"Obteniendo promedio para {tipo_credito}/{credito}")
        endpoint = f"/tasas/promedio/{tipo_credito}/{credito}"
        promedio_value = await self._make_request(endpoint)
        return float(promedio_value)
    
    async def get_tasas_por_fecha(self, fecha: str) -> pd.DataFrame:
        """
        Obtener tasas actualizadas para una fecha específica
        
        Args:
            fecha: Fecha en formato DD-MM-YYYY
            
        Returns:
            pd.DataFrame: DataFrame con tasas de la fecha
        """
        logger.info(f"Obteniendo tasas para fecha: {fecha}")
        endpoint = f"/tasas/{fecha}"
        json_data = await self._make_request(endpoint)
        return self._json_to_dataframe(json_data)
    
    async def health_check(self) -> dict:
        """
        Verificar estado del servidor
        
        Returns:
            dict: Información de estado del servidor
        """
        logger.info("Verificando estado del servidor...")
        return await self._make_request("/health")
    
    async def get_root_info(self) -> dict:
        """
        Obtener información principal de la API
        
        Returns:
            dict: Información de endpoints y versión
        """
        logger.info("Obteniendo información de la API...")
        return await self._make_request("/")

# Funciones de conveniencia para uso directo
async def get_tasas_activas(base_url: str = "http://localhost:8000") -> pd.DataFrame:
    """Función de conveniencia para obtener tasas activas"""
    client = OptiCredAPIClient(base_url)
    try:
        result = await client.get_tasas_activas()
        return result
    finally:
        await client.close_session()

async def get_tea(banco: str, tipo_credito: str, credito: str, base_url: str = "http://localhost:8000") -> float:
    """Función de conveniencia para obtener TEA"""
    client = OptiCredAPIClient(base_url)
    try:
        result = await client.get_tea(banco, tipo_credito, credito)
        return result
    finally:
        await client.close_session()

async def get_promedio(tipo_credito: str, credito: str, base_url: str = "http://localhost:8000") -> float:
    """Función de conveniencia para obtener promedio"""
    client = OptiCredAPIClient(base_url)
    try:
        json_data = await self._make_request("/tasas/activas")
        return self._json_to_dataframe(json_data)
    finally:
        await client.close_session()

async def get_bancos(base_url: str = "http://localhost:8000") -> pd.DataFrame:
    """Función de conveniencia para obtener bancos"""
    client = OptiCredAPIClient(base_url)
    try:
        result = await client.get_bancos()
        return result
    finally:
        await client.close_session()

# Ejemplo de uso asíncrono
async def main():
    """Ejemplo de uso del cliente asíncrono"""
    # Crear instancia del cliente
    client = OptiCredAPIClient()
    
    try:
        # Verificar estado del servidor
        print("=== Estado del servidor ===")
        health = await client.health_check()
        print(f"Estado: {health['status']}")
        print(f"Timestamp: {health['timestamp']}")
        
        # Obtener tasas activas
        print("\n=== Tasas activas ===")
        tasas = await client.get_tasas_activas()
        print(f"Shape: {tasas.shape}")
        print(tasas.head())
        
        # Obtener bancos
        print("\n=== Bancos disponibles ===")
        bancos = await client.get_bancos()
        print(bancos.head())
        
        # Ejemplo de obtener TEA (descomentar con datos reales)
        # print("\n=== TEA ejemplo ===")
        # tea = await client.get_tea("BANCO_DE_CREDITO", "CONSUMO", "CONSUMO_ORDINARIO")
        # print(f"TEA: {tea}")
        
    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        await client.close_session()

if __name__ == "__main__":
    asyncio.run(main())