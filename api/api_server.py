"""
API Server para OptiCred - FastAPI
Servidor que expone endpoints para scraping de tasas SBS
"""

import asyncio
import sys
import platform

# Configurar event loop para Windows ANTES de importar el scraper (Playwright)
if platform.system() == 'Windows' and sys.version_info >= (3, 8):
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from datetime import datetime
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import pandas as pd
from datetime import datetime
import logging
from typing import Optional, Dict, Any
import uvicorn
from modules.scraper.extractores.sbs.tabla_moneda_nacional import Tabla_Moneda_Nacional
from modules.scraper.solicitadores.sbs.pagina_tasas_nacionales import Pagina_Tasas_Nacionales
from modules.sbs_scraper import SBSScraper
from modules.scraper.tipos_credito.slice_tipo_credito import Slice_Tipo_Credito
from modules.scraper.bancos.columna_banco import Columna_Banco
from modules.scraper.tipos_credito.indice_tipo_credito import Corporativo, Grandes_Empresas, Medianas_Empresas, Pequenas_Empresas, Micro_Empresas, Consumo, Hipotecarios

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Inicializar FastAPI
app = FastAPI(
    title="OptiCred API",
    description="API para extracción de tasas activas de la SBS",
    version="1.0.0"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Instancia global del scraper
scraper = SBSScraper(Pagina_Tasas_Nacionales, Tabla_Moneda_Nacional)

def parse_slice_tipo_credito(tipo_credito: str) -> Optional[Slice_Tipo_Credito]:
    try:
        return Slice_Tipo_Credito[tipo_credito.upper()]
    except KeyError:
        return None

def parse_columna_banco(banco: str) -> Optional[Columna_Banco]:
    try:
        return Columna_Banco[banco.upper()]
    except KeyError:
        return None

def parse_credito(tipo_credito: str, credito: str) -> Optional[Corporativo | Grandes_Empresas | Medianas_Empresas | Pequenas_Empresas | Micro_Empresas | Consumo | Hipotecarios ]:
    opciones = [Corporativo, Grandes_Empresas, Medianas_Empresas, Pequenas_Empresas, Micro_Empresas, Consumo, Hipotecarios]

    try:
        for opcion in opciones:
            if opcion.__name__.upper() == tipo_credito.upper():
                return opcion[credito.upper()]
    except KeyError:
        return None

@app.get("/")
async def root():
    """Endpoint principal"""
    return {
        "message": "OptiCred API - Tasas SBS",
        "version": "1.0.0",
        "endpoints": {
            "/tasas/activas": "Obtener todas las tasas activas",
            "/tasas/tipo/{tipo_credito}": "Filtrar por tipo de crédito",
            "/tasas/entidad/{entidad}": "Filtrar por entidad bancaria",
            "/tasas/resumen": "Resumen estadístico",
            "/health": "Verificar estado del servidor"
        }
    }

@app.get("/health")
async def health_check():
    """Verificar estado del servidor"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "cache_size": len(cache)
    }

@app.get("/tasas/activas")
async def get_tasas_activas():
    """
    Obtener todas las tasas activas de la SBS
    """
    try:     
        logger.info("Obteniendo tasas activas de SBS...")
        tasas = await scraper.get_tasas_activas()
        
        if tasas.empty:
            raise HTTPException(status_code=404, detail="No se pudieron obtener las tasas")
        
        # Almacenar en cache
        # set_cache(cache_key, tasas)
        
        return tasas.to_json(orient='split')
        
    except Exception as e:
        logger.error(f"Error al obtener tasas activas: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

@app.get("/tasas/tipo/{tipo_credito}")
async def get_tasas_por_tipo(tipo_credito: str):
    """
    Obtener tasas filtradas por tipo de crédito
    """
    try:
        tipo_credito = tipo_credito.upper()

        enum_tipo_credito = parse_slice_tipo_credito(tipo_credito)
        if enum_tipo_credito is None:
            raise HTTPException(status_code=400, detail="Tipo de crédito no válido")
        
        tasas = await scraper.get_tasas(enum_tipo_credito)
        return tasas.to_json(orient='split')
        
    except Exception as e:
        logger.error(f"Error al obtener tasas por tipo: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

@app.get('/bancos/')
async def get_bancos():
    try: 
        bancos = await scraper.get_bancos()
        return bancos.to_json(orient='split')
    except Exception as e:
        logger.error(f"Error al obtener bancos: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

@app.get('/tea/{banco}/{tipo_credito}/{credito}')
async def get_tea(banco: str, tipo_credito: str, credito: str):
    try:
        enum_banco = parse_columna_banco(banco)
        enum_credito = parse_credito(tipo_credito, credito)

        if enum_banco is None:
            raise HTTPException(status_code=400, detail="Banco no válido")

        if enum_credito is None:
            raise HTTPException(status_code=400, detail="Tipo de crédito o crédito no válido")

        tea = await scraper.get_tea(enum_banco, enum_credito)
        return tea
    except Exception as e:
        logger.error(f"Error al obtener tea: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

@app.get('/tasas/promedio/{tipo_credito}/{credito}')
async def get_promedio(tipo_credito: str, credito: str):
    try:
        enum_credito = parse_credito(tipo_credito, credito)

        if enum_credito is None:
            raise HTTPException(status_code=400, detail="Tipo de crédito o crédito no válido")

        tea = await scraper.get_promedio(enum_credito)
        return tea 
    except Exception as e:
        logger.error(f"Error al obtener promedio: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

@app.get('/tasas/{fecha}')
async def obtener_tasa_actualizada(fecha: str):
    try:
        fecha = fecha.strip()
        formato = "%d-%m-%Y"
        tasa = await scraper.obtener_tasa_actualizada(datetime.strptime(fecha, formato).date())
        return tasa.to_json(orient='split')
    except Exception as e:
        logger.error(f"Error al obtener tasa actualizada: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

if __name__ == "__main__":
    logger.info("Iniciando servidor API OptiCred...")
    uvicorn.run(
        "api_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
