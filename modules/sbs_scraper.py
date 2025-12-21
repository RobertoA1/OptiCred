"""
SBS Scraper Module
Módulo robusto para extracción, limpieza y disponibilización de tasas activas de la SBS
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import lxml
from datetime import datetime, timedelta
import time
import logging
from typing import Dict, List, Optional, Tuple
import re
from playwright.sync_api import ViewportSize, sync_playwright
from playwright_stealth import Stealth

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

#def handle_console(msg):
#    print(f"[browser console] {msg.type}: {msg.text}")

class SBSScraper:
    """
    Clase principal para scraping de tasas activas de la SBS
    """
    
    def __init__(self):
        self.base_url = "https://www.sbs.gob.pe/app/pp/EstadisticasSAEEPortal/Paginas/TIActivaTipoCreditoEmpresa.aspx?tip=B"

        self.user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36'

        self.last_update = None
        self.cache_duration = timedelta(hours=1)  # Cache por 1 hora
        
    def _make_request(self, url: str, retries: int = 3) -> Optional[BeautifulSoup]:
        """
        Realiza solicitud HTTP con Playwright y retorna BeautifulSoup
        """
        for attempt in range(retries):
            try:
                logger.info(f"Intentando conexión a SBS con Playwright (intento {attempt + 1}/{retries})")
                
                with Stealth().use_sync(sync_playwright()) as p:
                    browser = p.chromium.launch(headless=True)
                    ctx = browser.new_context(user_agent=self.user_agent)
                    page = ctx.new_page()

                    page.goto(url, timeout=10000)

                    page.wait_for_load_state('networkidle')

                    page.evaluate("""
                    var date_input = $find('ctl00_cphContent_rdpDate');
                    date_input.set_selectedDate(new Date(2025, 11, 12));
                    """)

                    page.click('#ctl00_cphContent_btnConsultar')
                    
                    page.wait_for_timeout(5000)
                    
                    html_content = page.content()
                    
                    ctx.close()
                    browser.close()
                
                soup = BeautifulSoup(html_content, 'lxml')
                return soup
                
            except Exception as e:
                logger.error(f"Error en solicitud con Playwright (intento {attempt + 1}): {e}")
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)  # Backoff exponencial
                continue
                
        logger.error("No se pudo conectar a SBS después de todos los reintentos")
        return None
    
    def _extract_table_data(self, soup: BeautifulSoup) -> pd.DataFrame:
        """
        Extrae datos de la tabla principal de tasas
        """ 
        # div
        div = soup.find(id='ctl00_cphContent_rpgActualMn')
        tabla_moneda_nacional = div.table
        filas = tabla_moneda_nacional.tbody.contents

        # datosd
        # datos = filas[0].contents

        # encabezado vertical
        serie_encabezado_vertical = pd.Series()
        trsEncabezadoVertical = filas[2:-2]
        for tr in trsEncabezadoVertical:
            try:
                td = tr.find('td')
                nombre = td.text.strip()
                serie_encabezado_vertical = pd.concat([serie_encabezado_vertical, pd.Series([nombre])])
            except Exception as e:
                logger.error(f"Error al extraer encabezado vertical: {e}")
                continue
        
        # encabezado horizontal
        filas = tabla_moneda_nacional.find(id='ctl00_cphContent_rpgActualMn_ctl00_DataZone_DT').thead.tr.contents

        serie_encabezado_horizontal = pd.Series()
        thsEncabezadoHorizontal = filas[1:-1]
        for th in thsEncabezadoHorizontal:
            nombre = th.text.strip()
            serie_encabezado_horizontal = pd.concat([serie_encabezado_horizontal, pd.Series([nombre])])

#index=serie_encabezado_vertical, columns=serie_encabezado_horizontal
        tabla = pd.DataFrame(index=serie_encabezado_vertical, columns=serie_encabezado_horizontal)

        # datos

        filas = tabla_moneda_nacional.find(id='ctl00_cphContent_rpgActualMn_ctl00_DataZone_DT').tbody.contents
        filas = filas[1:-1]
        for i in range(0, len(trsEncabezadoVertical)):
            tr = filas[i]
            tds = tr.contents
            for j in range(1, len(thsEncabezadoHorizontal) + 1):
                td = tds[j]
                valor = td.text.strip()
                try:
                    float(valor)
                except:
                    valor = -1
                
                tabla.iloc[i, j - 1] = float(valor)

        print(tabla)

        logger.info(f"Se extrajeron {len(tabla)} filas de datos")
        return tabla
    
    def _is_valid_row(self, row_data: Dict[str, str]) -> bool:
        """
        Valida que una fila contenga datos relevantes
        """
        # Verificar que tenga campos clave
        required_fields = ['ENTIDAD', 'TASA']
        
        for field in required_fields:
            found = False
            for key in row_data.keys():
                if field.upper() in key.upper():
                    if row_data[key] and row_data[key].strip():
                        found = True
                        break
            if not found:
                return False
                
        return True
    
    def _clean_and_normalize_data(self, raw_data: List[Dict[str, str]]) -> pd.DataFrame:
        """
        Limpia y normaliza los datos extraídos
        """
        if not raw_data:
            return pd.DataFrame()
            
        # Convertir a DataFrame
        df = pd.DataFrame(raw_data)
        
        # Normalizar nombres de columnas
        df.columns = [self._normalize_column_name(col) for col in df.columns]
        
        # Limpiar datos
        df = self._clean_dataframe(df)
        
        # Estandarizar tipos de crédito
        df = self._standardize_credit_types(df)
        
        # Limpiar tasas
        df = self._clean_rates(df)
        
        # Añadir metadatos
        df['fecha_extraccion'] = datetime.now()
        df['fuente'] = 'SBS'
        
        return df
    
    def _normalize_column_name(self, col_name: str) -> str:
        """
        Normaliza nombres de columnas a un formato estándar
        """
        col_name = col_name.strip().lower()
        
        # Mapeos comunes
        mappings = {
            'entidad': 'entidad_bancaria',
            'banco': 'entidad_bancaria',
            'institución': 'entidad_bancaria',
            'tipo de crédito': 'tipo_credito',
            'tipo crédito': 'tipo_credito',
            'crédito': 'tipo_credito',
            'tasa': 'tea',
            'tea': 'tea',
            'tasa efectiva anual': 'tea',
            'moneda': 'moneda',
            'nacional/extranjera': 'moneda'
        }
        
        for key, value in mappings.items():
            if key in col_name:
                return value
                
        return col_name.replace(' ', '_')
    
    def _clean_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Limpia el DataFrame eliminando filas vacías y valores nulos
        """
        # Eliminar filas completamente vacías
        df = df.dropna(how='all')
        
        # Limpiar espacios en blanco
        for col in df.columns:
            if df[col].dtype == 'object':
                df[col] = df[col].astype(str).str.strip()
                df[col] = df[col].replace('', None)
                df[col] = df[col].replace('nan', None)
        
        return df
    
    def _standardize_credit_types(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Estandariza los tipos de crédito
        """
        if 'tipo_credito' not in df.columns:
            return df
            
        # Mapeo de tipos de crédito estándar
        credit_type_mapping = {
            'consumo': 'Consumo',
            'consumo ordinario': 'Consumo',
            'consumo rápido': 'Consumo',
            'hipotecario': 'Hipotecario',
            'hipotecario vivienda': 'Hipotecario',
            'vehicular': 'Vehicular',
            'vehículo': 'Vehicular',
            'microempresa': 'Microempresa',
            'microcrédito': 'Microempresa',
            'empresa': 'Empresarial',
            'empresarial': 'Empresarial',
            'comercial': 'Comercial',
            'agropecuario': 'Agropecuario'
        }
        
        # Aplicar normalización
        df['tipo_credito'] = df['tipo_credito'].str.lower()
        for key, value in credit_type_mapping.items():
            df.loc[df['tipo_credito'].str.contains(key, na=False), 'tipo_credito'] = value
            
        return df
    
    def _clean_rates(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Limpia y formatea las tasas de interés
        """
        rate_columns = ['tea', 'tasa', 'tasa_efectiva_anual']
        
        for col in rate_columns:
            if col in df.columns:
                # Extraer valores numéricos
                df[col] = df[col].astype(str).str.extract(r'(\d+\.?\d*)')
                df[col] = pd.to_numeric(df[col], errors='coerce')
                
        return df
    
    def get_tasas_activas(self, force_refresh: bool = False) -> pd.DataFrame:
        """
        Obtiene las tasas activas de la SBS
        
        Args:
            force_refresh: Si es True, ignora el cache y fuerza nueva descarga
            
        Returns:
            DataFrame con las tasas activas limpias y normalizadas
        """
        # Verificar cache
        if not force_refresh and self.last_update and \
           datetime.now() - self.last_update < self.cache_duration:
            logger.info("Usando datos cacheados")
            return getattr(self, '_cached_data', pd.DataFrame())
        
        logger.info("Iniciando extracción de tasas SBS")
        
        # Obtener página
        soup = self._make_request(self.base_url)
        if not soup:
            logger.error("No se pudo obtener la página de SBS")
            return pd.DataFrame()
        
        # Extraer datos
        raw_data = self._extract_table_data(soup)
        if not raw_data:
            logger.warning("No se extrajeron datos de la tabla")
            return pd.DataFrame()
        
        # Limpiar y normalizar
        df = self._clean_and_normalize_data(raw_data)
        
        # Actualizar cache
        self.last_update = datetime.now()
        self._cached_data = df
        
        logger.info(f"Extracción completada: {len(df)} registros obtenidos")
        return df
    
    def get_tasas_por_tipo(self, tipo_credito: str) -> pd.DataFrame:
        """
        Filtra tasas por tipo de crédito específico
        
        Args:
            tipo_credito: Tipo de crédito a filtrar
            
        Returns:
            DataFrame con tasas del tipo especificado
        """
        df = self.get_tasas_activas()
        
        if 'tipo_credito' in df.columns:
            filtered = df[df['tipo_credito'].str.contains(tipo_credito, case=False, na=False)]
            return filtered
            
        return pd.DataFrame()
    
    def get_tasas_por_entidad(self, entidad: str) -> pd.DataFrame:
        """
        Filtra tasas por entidad bancaria específica
        
        Args:
            entidad: Nombre de la entidad bancaria
            
        Returns:
            DataFrame con tasas de la entidad especificada
        """
        df = self.get_tasas_activas()
        
        if 'entidad_bancaria' in df.columns:
            filtered = df[df['entidad_bancaria'].str.contains(entidad, case=False, na=False)]
            return filtered
            
        return pd.DataFrame()
    
    def export_to_excel(self, df: pd.DataFrame, filename: str = None) -> str:
        """
        Exporta el DataFrame a Excel
        
        Args:
            df: DataFrame a exportar
            filename: Nombre del archivo (opcional)
            
        Returns:
            Ruta del archivo generado
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"tasas_sbs_{timestamp}.xlsx"
        
        filepath = f"exports/{filename}"
        
        # Crear directorio si no existe
        import os
        os.makedirs('exports', exist_ok=True)
        
        # Exportar
        df.to_excel(filepath, index=False, engine='openpyxl')
        logger.info(f"Datos exportados a {filepath}")
        
        return filepath
    
    def get_resumen_estadistico(self) -> Dict[str, any]:
        """
        Genera un resumen estadístico de las tasas actuales
        
        Returns:
            Diccionario con estadísticas descriptivas
        """
        df = self.get_tasas_activas()
        
        if df.empty or 'tea' not in df.columns:
            return {}
            
        resumen = {
            'total_registros': len(df),
            'fecha_actualizacion': self.last_update,
            'entidades_unicas': df['entidad_bancaria'].nunique() if 'entidad_bancaria' in df.columns else 0,
            'tipos_credito': df['tipo_credito'].unique().tolist() if 'tipo_credito' in df.columns else [],
            'estadisticas_tea': df['tea'].describe().to_dict() if 'tea' in df.columns else {}
        }
        
        return resumen

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

if __name__ == "__main__":
    # Prueba del módulo
    print("Probando scraper SBS...")
    scraper = SBSScraper()
    
    # Obtener todas las tasas
    tasas = scraper.get_tasas_activas()
    print(f"Se obtuvieron {len(tasas)} registros")
    
    if not tasas.empty:
        print("\nPrimeros 5 registros:")
        print(tasas.head())
        
        print("\nResumen estadístico:")
        resumen = scraper.get_resumen_estadistico()
        for key, value in resumen.items():
            print(f"{key}: {value}")
    else:
        print("No se obtuvieron datos")
