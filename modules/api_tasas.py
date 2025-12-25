# modules/api_tasas.py
"""
Módulo de integración entre la API de tasas SBS y el comparador de créditos.
Soporta el formato "Categoría - Tipo" del selector en cascada.

SOLUCIONADO: Manejo de filas con nombres repetidos usando índice numérico.
"""
import asyncio
from typing import Optional, List, Dict, Tuple
import pandas as pd
import streamlit as st
import logging
import re

logger = logging.getLogger(__name__)

# =============================================================================
# IMPORTAR CLIENTE API
# =============================================================================

try:
    from api.api_client import OptiCredAPIClient
    API_CLIENT_DISPONIBLE = True
except ImportError:
    try:
        from modules.api_client import OptiCredAPIClient
        API_CLIENT_DISPONIBLE = True
    except ImportError:
        API_CLIENT_DISPONIBLE = False
        logger.warning("OptiCredAPIClient no disponible")


# =============================================================================
# MAPEO DE CATEGORÍAS - NOMBRES EXACTOS DE LA TABLA SBS
# =============================================================================

CATEGORIAS_CREDITO = {
    "Corporativos": {
        "descripcion": "Créditos para grandes corporaciones con ventas anuales > S/ 200 millones",
        "opciones": {
            "Descuentos": "Descuentos",
            "Préstamos hasta 30 días": "Préstamos hasta 30 días",
            "Préstamos de 31 a 90 días": "Préstamos de 31 a 90 días",
            "Préstamos de 91 a 180 días": "Préstamos de 91 a 180 días",
            "Préstamos de 181 a 360 días": "Préstamos de 181 a 360 días",
            "Préstamos a más de 360 días": "Préstamos a más de 360 días",
        }
    },
    "Grandes Empresas": {
        "descripcion": "Créditos para empresas con ventas anuales > S/ 20 millones",
        "opciones": {
            "Descuentos": "Descuentos",
            "Préstamos hasta 30 días": "Préstamos hasta 30 días",
            "Préstamos de 31 a 90 días": "Préstamos de 31 a 90 días",
            "Préstamos de 91 a 180 días": "Préstamos de 91 a 180 días",
            "Préstamos de 181 a 360 días": "Préstamos de 181 a 360 días",
            "Préstamos a más de 360 días": "Préstamos a más de 360 días",
        }
    },
    "Medianas Empresas": {
        "descripcion": "Créditos para empresas con ventas anuales entre S/ 1.7 y S/ 20 millones",
        "opciones": {
            "Descuentos": "Descuentos",
            "Préstamos hasta 30 días": "Préstamos hasta 30 días",
            "Préstamos de 31 a 90 días": "Préstamos de 31 a 90 días",
            "Préstamos de 91 a 180 días": "Préstamos de 91 a 180 días",
            "Préstamos de 181 a 360 días": "Préstamos de 181 a 360 días",
            "Préstamos a más de 360 días": "Préstamos a más de 360 días",
        }
    },
    "Pequeñas Empresas": {
        "descripcion": "Créditos para empresas con ventas anuales entre S/ 150 mil y S/ 1.7 millones",
        "opciones": {
            "Descuentos": "Descuentos",
            "Préstamos hasta 30 días": "Préstamos hasta 30 días",
            "Préstamos de 31 a 90 días": "Préstamos de 31 a 90 días",
            "Préstamos de 91 a 180 días": "Préstamos de 91 a 180 días",
            "Préstamos de 181 a 360 días": "Préstamos de 181 a 360 días",
            "Préstamos a más de 360 días": "Préstamos a más de 360 días",
        }
    },
    "Microempresas": {
        "descripcion": "Créditos para negocios con ventas anuales < S/ 150 mil",
        "opciones": {
            "Tarjetas de Crédito": "Tarjetas de Crédito",
            "Descuentos": "Descuentos",
            "Préstamos Revolventes": "Préstamos Revolventes",
            "Préstamos a cuota fija hasta 30 días": "Préstamos a cuota fija hasta 30 días",
            "Préstamos a cuota fija de 31 a 90 días": "Préstamos  a cuota fija de 31 a 90 días",
            "Préstamos a cuota fija de 91 a 180 días": "Préstamos  a cuota fija de 91 a 180 días",
            "Préstamos a cuota fija de 181 a 360 días": "Préstamos a cuota fija de 181 a 360 días",
            "Préstamos a cuota fija a más de 360 días": "Préstamos a cuota fija a más de 360 días",
        }
    },
    "Consumo": {
        "descripcion": "Créditos para personas naturales (uso personal)",
        "opciones": {
            "Tarjetas de Crédito": "Tarjetas de Crédito",
            "Préstamos Revolventes": "Préstamos Revolventes",
            "Préstamos para Automóviles": "Préstamos no  Revolventes para automóviles",
            "Libre Disponibilidad (hasta 360 días)": "Préstamos no  Revolventes para libre disponibilidad hasta 360 días",
            "Libre Disponibilidad (más de 360 días)": "Préstamos no  Revolventes para libre disponibilidad a más de 360 días",
            "Créditos Pignoraticios": "Créditos pignoraticios",
        }
    },
    "Hipotecarios": {
        "descripcion": "Créditos con garantía hipotecaria para vivienda",
        "opciones": {
            "Préstamos para Vivienda": "Préstamos hipotecarios para vivienda",
        }
    },
}

# Lista de categorías principales (headers en la tabla SBS)
CATEGORIAS_PRINCIPALES = [
    'corporativos', 'grandes empresas', 'medianas empresas', 
    'pequeñas empresas', 'microempresas', 'consumo', 'hipotecarios'
]


def normalizar_texto(texto: str) -> str:
    """Normaliza espacios múltiples y quita espacios al inicio/final."""
    texto = re.sub(r'\s+', ' ', str(texto))
    return texto.strip().lower()


class APITasas:
    """
    Clase para obtener tasas de interés reales desde la API SBS.
    Soporta formato "Categoría - Tipo" del selector en cascada.
    
    IMPORTANTE: Maneja correctamente filas con nombres repetidos
    usando el índice numérico basado en la posición de la categoría.
    """
    
    def __init__(self):
        self._tasas_activas: Optional[pd.DataFrame] = None
        self._bancos: Optional[pd.Series] = None
        self._cache_cargado = False
        # Cache de índices de categorías para búsqueda rápida
        self._indices_categorias: Optional[Dict[str, int]] = None
    
    # =========================================================================
    # MÉTODOS DE CARGA DE DATOS
    # =========================================================================
    
    def _ejecutar_async(self, coro):
        """Ejecuta una corutina de forma síncrona (compatible con Streamlit)."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, coro)
                    return future.result(timeout=30)
            else:
                return loop.run_until_complete(coro)
        except RuntimeError:
            return asyncio.run(coro)
    
    def cargar_datos(self) -> bool:
        """Carga los datos de tasas y bancos desde la API."""
        if not API_CLIENT_DISPONIBLE:
            logger.error("Cliente API no disponible")
            return False
        
        async def _fetch():
            client = OptiCredAPIClient()
            try:
                tasas = await client.get_tasas_activas()
                bancos = await client.get_bancos()
                return tasas, bancos
            finally:
                await client.close_session()
        
        try:
            self._tasas_activas, self._bancos = self._ejecutar_async(_fetch())
            self._cache_cargado = True
            # Construir índice de categorías al cargar
            self._construir_indice_categorias()
            logger.info("✅ Datos cargados desde la API")
            return True
        except Exception as e:
            logger.error(f"❌ Error al cargar datos: {e}")
            return False
    
    def _asegurar_datos(self):
        """Asegura que los datos estén cargados."""
        if not self._cache_cargado:
            self.cargar_datos()
    
    def _construir_indice_categorias(self):
        """
        Construye un diccionario con el índice numérico donde inicia cada categoría.
        Esto permite buscar filas específicas dentro de una categoría.
        """
        if self._tasas_activas is None:
            return
        
        self._indices_categorias = {}
        df = self._tasas_activas
        
        for i, idx in enumerate(df.index):
            idx_norm = normalizar_texto(str(idx))
            if idx_norm in CATEGORIAS_PRINCIPALES:
                self._indices_categorias[idx_norm] = i
                logger.info(f"   📍 Categoría '{idx_norm}' encontrada en índice {i}")
        
        logger.info(f"✅ Índice de categorías construido: {self._indices_categorias}")
    
    # =========================================================================
    # MÉTODO CLAVE: RESOLVER FILA EN LA TABLA
    # =========================================================================
    
    def _resolver_fila_tabla(self, tipo_credito: str) -> Tuple[str, str]:
        """
        Resuelve el nombre de la fila en la tabla SBS y la categoría.
        
        Acepta:
        - Formato "Categoría - Tipo" (ej: "Consumo - Préstamos para Automóviles")
        - Nombre directo de la fila (ej: "Préstamos de 31 a 90 días")
        
        Returns:
            Tupla (nombre_fila, categoría) donde categoría puede ser None si no se especificó
        """
        logger.info(f"🔍 _resolver_fila_tabla: Recibido '{tipo_credito}'")
        
        # Si viene en formato "Categoría - Tipo específico"
        if " - " in tipo_credito:
            partes = tipo_credito.split(" - ", 1)
            categoria = partes[0].strip()
            tipo_especifico = partes[1].strip()
            
            logger.info(f"   Formato detectado: Categoría='{categoria}', Tipo='{tipo_especifico}'")
            
            # Buscar en CATEGORIAS_CREDITO
            if categoria in CATEGORIAS_CREDITO:
                opciones = CATEGORIAS_CREDITO[categoria]["opciones"]
                if tipo_especifico in opciones:
                    resultado = opciones[tipo_especifico]
                    logger.info(f"   ✅ Encontrado en mapeo: '{resultado}'")
                    return (resultado, categoria)
                else:
                    logger.warning(f"   ⚠️ Tipo específico '{tipo_especifico}' no encontrado en opciones")
            else:
                logger.warning(f"   ⚠️ Categoría '{categoria}' no encontrada")
            
            # Fallback: usar el tipo específico directamente con la categoría
            logger.info(f"   Fallback: usando tipo específico '{tipo_especifico}' con categoría '{categoria}'")
            return (tipo_especifico, categoria)
        
        # Si es un nombre directo, devolverlo sin categoría
        logger.info(f"   Formato directo: devolviendo '{tipo_credito}' sin categoría")
        return (tipo_credito, None)
    
    # =========================================================================
    # MÉTODO CLAVE: BUSCAR FILA POR ÍNDICE NUMÉRICO
    # =========================================================================
    
    def _buscar_fila_por_indice(self, df: pd.DataFrame, fila_buscar: str, categoria: str = None) -> Optional[pd.Series]:
        """
        Busca una fila en el DataFrame usando índice numérico.
        
        ESTRATEGIA:
        1. Si hay categoría, encontrar el índice donde inicia esa categoría
        2. Buscar la fila específica DESPUÉS del header de categoría
        3. Detenerse cuando se encuentra otra categoría
        
        Args:
            df: DataFrame donde buscar
            fila_buscar: Nombre de la fila a buscar (ej: "Descuentos")
            categoria: Categoría para contextualizar la búsqueda (ej: "Corporativos")
        
        Returns:
            Series con los datos de la fila, o None si no se encuentra
        """
        fila_buscar_norm = normalizar_texto(fila_buscar)
        categoria_norm = normalizar_texto(categoria) if categoria else None
        
        logger.info(f"🔍 _buscar_fila_por_indice:")
        logger.info(f"   Buscando: '{fila_buscar}' (norm: '{fila_buscar_norm}')")
        logger.info(f"   Categoría: '{categoria}' (norm: '{categoria_norm}')")
        
        # Asegurar que tenemos el índice de categorías
        if self._indices_categorias is None:
            self._construir_indice_categorias()
        
        # ESTRATEGIA CON CATEGORÍA
        if categoria_norm and self._indices_categorias:
            if categoria_norm in self._indices_categorias:
                inicio_categoria = self._indices_categorias[categoria_norm]
                
                # Encontrar el fin de esta categoría (inicio de la siguiente)
                fin_categoria = len(df.index)
                for cat, idx in sorted(self._indices_categorias.items(), key=lambda x: x[1]):
                    if idx > inicio_categoria:
                        fin_categoria = idx
                        break
                
                logger.info(f"   📍 Rango de búsqueda: [{inicio_categoria + 1}, {fin_categoria})")
                
                # Buscar DENTRO del rango de la categoría (saltando el header)
                for i in range(inicio_categoria + 1, fin_categoria):
                    idx = df.index[i]
                    idx_norm = normalizar_texto(str(idx))
                    
                    # Coincidencia exacta
                    if idx_norm == fila_buscar_norm:
                        logger.info(f"   ✅ Encontrado en índice {i}: '{idx}'")
                        return df.iloc[i]
                    
                    # Coincidencia parcial
                    if fila_buscar_norm in idx_norm or idx_norm in fila_buscar_norm:
                        logger.info(f"   ✅ Coincidencia parcial en índice {i}: '{idx}'")
                        return df.iloc[i]
                
                logger.warning(f"   ❌ No encontrado en el rango de '{categoria}'")
            else:
                logger.warning(f"   ⚠️ Categoría '{categoria_norm}' no está en el índice")
        
        # FALLBACK: Búsqueda sin contexto (puede dar resultados incorrectos con nombres repetidos)
        logger.info(f"   ⚠️ Fallback: búsqueda sin contexto de categoría")
        
        for i, idx in enumerate(df.index):
            idx_norm = normalizar_texto(str(idx))
            
            if idx_norm == fila_buscar_norm:
                logger.info(f"   ✅ Fallback - Encontrado en índice {i}: '{idx}'")
                return df.iloc[i]
        
        logger.warning(f"   ❌ No se encontró la fila '{fila_buscar}'")
        return None
    
    # =========================================================================
    # MÉTODOS PÚBLICOS - BANCOS
    # =========================================================================
    
    def get_bancos(self, tipo_credito: str = None, categoria: str = None) -> List[str]:
        """
        Obtiene la lista de bancos disponibles.
        Si se especifica tipo_credito y categoria, filtra los que tienen tasa válida (> 0).
        
        Args:
            tipo_credito: Tipo de crédito específico (ej: "Descuentos")
            categoria: Categoría del crédito (ej: "Corporativos", "Grandes Empresas")
        """
        self._asegurar_datos()
        
        if self._bancos is None:
            return self._bancos_default()
        
        # Convertir a lista
        try:
            if isinstance(self._bancos, pd.Series):
                bancos_lista = self._bancos.dropna().tolist()
            elif isinstance(self._bancos, pd.DataFrame):
                bancos_lista = self._bancos.iloc[:, 0].dropna().tolist()
            else:
                bancos_lista = list(self._bancos)
        except Exception:
            return self._bancos_default()
        
        # Filtrar por tipo de crédito si se especifica
        if tipo_credito and categoria and self._tasas_activas is not None:
            bancos_con_tasa = self._filtrar_bancos_con_tasa(tipo_credito, categoria)
            if bancos_con_tasa:
                return bancos_con_tasa
        
        return bancos_lista if bancos_lista else self._bancos_default()
    
    def _bancos_default(self) -> List[str]:
        """Lista de bancos por defecto."""
        return ["BBVA", "Crédito", "Interbank", "Scotiabank", "Pichincha", "BIF", "GNB", "Mibanco"]
    
    def _filtrar_bancos_con_tasa(self, tipo_credito: str, categoria: str) -> List[str]:
        """
        Filtra bancos que tienen tasa válida (> 0) para el tipo de crédito Y categoría.
        
        Args:
            tipo_credito: Nombre del producto (ej: "Descuentos")
            categoria: Categoría del crédito (ej: "Corporativos")
        """
        logger.info(f"🔍 _filtrar_bancos_con_tasa:")
        logger.info(f"   Tipo: '{tipo_credito}', Categoría: '{categoria}'")
        
        if self._tasas_activas is None or self._tasas_activas.empty:
            return []
        
        df = self._tasas_activas
        
        # Resolver el nombre de la fila en la tabla SBS
        fila_buscar, cat_resuelta = self._resolver_fila_tabla(f"{categoria} - {tipo_credito}")
        
        # Buscar usando el nuevo método con índice
        fila_encontrada = self._buscar_fila_por_indice(df, fila_buscar, categoria)
        
        if fila_encontrada is None:
            logger.warning(f"   ❌ No se encontró la fila")
            return []
        
        # Extraer bancos con tasas válidas
        bancos_validos = []
        
        for col in df.columns:
            col_str = str(col).strip()
            
            # Saltar columnas que no son bancos
            if col_str.lower() in ['', 'tipo', 'producto', 'promedio']:
                continue
            
            try:
                valor = float(fila_encontrada[col])
                if valor > 0:  # Excluir -1 y valores no válidos
                    bancos_validos.append(col_str)
                    logger.info(f"      ✅ {col_str}: {valor}%")
                else:
                    logger.info(f"      ❌ {col_str}: {valor} (excluido)")
            except (ValueError, TypeError, KeyError):
                continue
        
        logger.info(f"   📊 Total bancos válidos: {len(bancos_validos)}")
        return bancos_validos
    
    # =========================================================================
    # MÉTODOS PÚBLICOS - TASAS
    # =========================================================================
    
    def get_tea(self, banco: str, tipo_credito: str, categoria: str = None) -> float:
        """
        Obtiene la TEA de un banco para un tipo de crédito específico.
        
        Args:
            banco: Nombre del banco (ej: "BBVA", "Crédito")
            tipo_credito: Tipo de crédito (ej: "Descuentos")
            categoria: Categoría del crédito (ej: "Corporativos")
        
        Returns:
            TEA como porcentaje (ej: 12.5), o valor default si no existe
        """
        self._asegurar_datos()
        
        if self._tasas_activas is None or self._tasas_activas.empty:
            return self._tea_default(categoria or tipo_credito)
        
        df = self._tasas_activas
        
        # Resolver nombre de fila
        fila_buscar, cat_resuelta = self._resolver_fila_tabla(
            f"{categoria} - {tipo_credito}" if categoria else tipo_credito
        )
        
        # Usar categoría proporcionada o la resuelta
        cat_final = categoria or cat_resuelta
        
        # Buscar la fila con contexto de categoría
        fila_encontrada = self._buscar_fila_por_indice(df, fila_buscar, cat_final)
        
        if fila_encontrada is None:
            return self._tea_default(cat_final or tipo_credito)
        
        # Buscar el banco en las columnas
        for col in df.columns:
            if self._coincide_banco(banco, str(col)):
                try:
                    valor = float(fila_encontrada[col])
                    if valor > 0:
                        return valor
                except (ValueError, TypeError, KeyError):
                    continue
        
        return self._tea_default(cat_final or tipo_credito)
    
    def _coincide_banco(self, banco_buscado: str, columna: str) -> bool:
        """Verifica si el nombre del banco coincide con la columna."""
        banco_lower = banco_buscado.lower().strip()
        col_lower = columna.lower().strip()
        
        if banco_lower == col_lower:
            return True
        
        if banco_lower in col_lower or col_lower in banco_lower:
            return True
        
        alias = {
            "bcp": ["crédito", "credito", "banco de crédito"],
            "credito": ["bcp", "crédito", "banco de crédito"],
            "crédito": ["bcp", "credito", "banco de crédito"],
        }
        
        if banco_lower in alias:
            for a in alias[banco_lower]:
                if a in col_lower:
                    return True
        
        return False
    
    def _tea_default(self, tipo_o_categoria: str) -> float:
        """TEA por defecto cuando no hay datos."""
        categoria = tipo_o_categoria.split(" - ")[0] if " - " in tipo_o_categoria else tipo_o_categoria
        
        defaults = {
            "Consumo": 35.0,
            "Hipotecarios": 9.0,
            "Hipotecario": 9.0,
            "Corporativos": 6.0,
            "Grandes Empresas": 8.0,
            "Medianas Empresas": 12.0,
            "Pequeñas Empresas": 18.0,
            "Microempresas": 35.0,
        }
        
        return defaults.get(categoria, 15.0)
    
    def get_promedio(self, tipo_credito: str, categoria: str = None) -> float:
        """
        Obtiene el promedio de tasas del mercado para la fila seleccionada.
        
        Args:
            tipo_credito: Tipo de crédito (ej: "Descuentos")
            categoria: Categoría del crédito (ej: "Corporativos")
        
        Returns:
            Promedio de tasas como porcentaje
        """
        self._asegurar_datos()
        
        if self._tasas_activas is None or self._tasas_activas.empty:
            return self._tea_default(categoria or tipo_credito)
        
        df = self._tasas_activas
        
        # Resolver nombre de fila
        fila_buscar, cat_resuelta = self._resolver_fila_tabla(
            f"{categoria} - {tipo_credito}" if categoria else tipo_credito
        )
        cat_final = categoria or cat_resuelta
        
        # Buscar la fila
        fila_encontrada = self._buscar_fila_por_indice(df, fila_buscar, cat_final)
        
        if fila_encontrada is None:
            return self._tea_default(cat_final or tipo_credito)
        
        # Buscar columna "Promedio"
        for col in df.columns:
            col_str = str(col).strip().lower()
            if 'promedio' in col_str:
                try:
                    val = float(fila_encontrada[col])
                    if val > 0:
                        return val
                except (ValueError, TypeError, KeyError):
                    pass
        
        # Calcular promedio manualmente
        valores_validos = []
        for col in df.columns:
            col_str = str(col).strip().lower()
            
            if col_str in ['', 'tipo', 'producto', 'promedio']:
                continue
            
            try:
                val = float(fila_encontrada[col])
                if val > 0:
                    valores_validos.append(val)
            except (ValueError, TypeError, KeyError):
                continue
        
        if valores_validos:
            return sum(valores_validos) / len(valores_validos)
        
        return self._tea_default(cat_final or tipo_credito)
    
    def get_tasas_por_tipo(self, tipo_credito: str, categoria: str = None) -> Dict[str, float]:
        """
        Obtiene todas las tasas válidas (> 0) para un tipo de crédito.
        
        Args:
            tipo_credito: Tipo de crédito (ej: "Descuentos")
            categoria: Categoría del crédito (ej: "Corporativos")
        
        Returns:
            Diccionario {nombre_banco: tasa} solo con valores válidos
        """
        self._asegurar_datos()
        
        resultado = {}
        
        if self._tasas_activas is None or self._tasas_activas.empty:
            for banco in self._bancos_default():
                resultado[banco] = self._tea_default(categoria or tipo_credito)
            return resultado
        
        df = self._tasas_activas
        
        # Resolver nombre de fila
        fila_buscar, cat_resuelta = self._resolver_fila_tabla(
            f"{categoria} - {tipo_credito}" if categoria else tipo_credito
        )
        cat_final = categoria or cat_resuelta
        
        # Buscar la fila
        fila_encontrada = self._buscar_fila_por_indice(df, fila_buscar, cat_final)
        
        if fila_encontrada is None:
            return resultado
        
        # Extraer valores válidos
        for col in df.columns:
            col_str = str(col).strip()
            
            if col_str.lower() in ['', 'tipo', 'producto', 'promedio']:
                continue
            
            try:
                val = float(fila_encontrada[col])
                if val > 0:
                    resultado[col_str] = val
            except (ValueError, TypeError, KeyError):
                continue
        
        return resultado
    
    def get_mejor_tasa(self, tipo_credito: str, categoria: str = None) -> Tuple[str, float]:
        """
        Obtiene el banco con la mejor tasa (más baja) para el tipo de crédito.
        
        Args:
            tipo_credito: Tipo de crédito (ej: "Descuentos")
            categoria: Categoría del crédito (ej: "Corporativos")
        
        Returns:
            Tupla (nombre_banco, tasa) o ("N/A", default) si no hay datos
        """
        tasas = self.get_tasas_por_tipo(tipo_credito, categoria)
        
        if not tasas:
            return ("N/A", self._tea_default(categoria or tipo_credito))
        
        mejor_banco = min(tasas, key=tasas.get)
        return (mejor_banco, tasas[mejor_banco])
    
    def get_peor_tasa(self, tipo_credito: str, categoria: str = None) -> Tuple[str, float]:
        """
        Obtiene el banco con la peor tasa (más alta) para el tipo de crédito.
        
        Returns:
            Tupla (nombre_banco, tasa) o ("N/A", default) si no hay datos
        """
        tasas = self.get_tasas_por_tipo(tipo_credito, categoria)
        
        if not tasas:
            return ("N/A", self._tea_default(categoria or tipo_credito))
        
        peor_banco = max(tasas, key=tasas.get)
        return (peor_banco, tasas[peor_banco])
    
    def get_rango_tasas(self, tipo_credito: str, categoria: str = None) -> Tuple[float, float]:
        """Obtiene (tasa_minima, tasa_maxima) para un tipo de crédito."""
        tasas = self.get_tasas_por_tipo(tipo_credito, categoria)
        valores = list(tasas.values())
        
        if not valores:
            default = self._tea_default(categoria or tipo_credito)
            return (default * 0.8, default * 1.2)
        
        return (min(valores), max(valores))
    
    # =========================================================================
    # MÉTODOS DE ACCESO A DATAFRAMES
    # =========================================================================
    
    def get_dataframe_tasas(self) -> Optional[pd.DataFrame]:
        """Retorna el DataFrame completo de tasas activas."""
        self._asegurar_datos()
        return self._tasas_activas
    
    def get_dataframe_bancos(self) -> Optional[pd.Series]:
        """Retorna la Serie de bancos."""
        self._asegurar_datos()
        return self._bancos
    
    def esta_conectado(self) -> bool:
        """Verifica si hay conexión exitosa con la API."""
        return self._cache_cargado and self._tasas_activas is not None
    
    def get_indices_categorias(self) -> Dict[str, int]:
        """Retorna el diccionario de índices de categorías (útil para debug)."""
        self._asegurar_datos()
        return self._indices_categorias or {}


# =============================================================================
# FUNCIONES DE CONVENIENCIA PARA STREAMLIT (con cache)
# =============================================================================

@st.cache_data(ttl=300, show_spinner=False)
def cargar_datos_api() -> Tuple[Optional[pd.DataFrame], Optional[pd.Series], bool]:
    """Carga datos de la API con cache de 5 minutos."""
    if not API_CLIENT_DISPONIBLE:
        return None, None, False
    
    api = APITasas()
    if api.cargar_datos():
        return api.get_dataframe_tasas(), api.get_dataframe_bancos(), True
    
    return None, None, False


def obtener_bancos(tipo_credito: str = None, categoria: str = None) -> List[str]:
    """Obtiene bancos disponibles."""
    df_tasas, df_bancos, conectado = cargar_datos_api()
    
    if not conectado:
        return APITasas()._bancos_default()
    
    api = APITasas()
    api._tasas_activas = df_tasas
    api._bancos = df_bancos
    api._cache_cargado = True
    api._construir_indice_categorias()
    
    return api.get_bancos(tipo_credito, categoria)


def obtener_tea(banco: str, tipo_credito: str, categoria: str = None) -> float:
    """Obtiene TEA de un banco."""
    df_tasas, df_bancos, conectado = cargar_datos_api()
    
    if not conectado:
        return APITasas()._tea_default(categoria or tipo_credito)
    
    api = APITasas()
    api._tasas_activas = df_tasas
    api._bancos = df_bancos
    api._cache_cargado = True
    api._construir_indice_categorias()
    
    return api.get_tea(banco, tipo_credito, categoria)


def obtener_promedio(tipo_credito: str, categoria: str = None) -> float:
    """Obtiene promedio del mercado."""
    df_tasas, df_bancos, conectado = cargar_datos_api()
    
    if not conectado:
        return APITasas()._tea_default(categoria or tipo_credito)
    
    api = APITasas()
    api._tasas_activas = df_tasas
    api._bancos = df_bancos
    api._cache_cargado = True
    api._construir_indice_categorias()
    
    return api.get_promedio(tipo_credito, categoria)


# =============================================================================
# TEST
# =============================================================================

if __name__ == "__main__":
    print("=== Test de APITasas (con manejo de filas repetidas) ===\n")
    
    api = APITasas()
    
    # Test del resolver
    print("📋 Test de _resolver_fila_tabla:")
    tests = [
        "Consumo - Préstamos para Automóviles",
        "Corporativos - Descuentos",
        "Grandes Empresas - Descuentos",  # Mismo nombre, diferente categoría
        "Hipotecarios - Préstamos para Vivienda",
    ]
    
    for test in tests:
        resultado = api._resolver_fila_tabla(test)
        print(f"  '{test}' → fila='{resultado[0]}', cat='{resultado[1]}'")
    
    print("\n" + "="*60 + "\n")
    
    if api.cargar_datos():
        print("✅ Conexión exitosa con la API\n")
        
        # Mostrar índices de categorías
        print("📍 Índices de categorías encontradas:")
        for cat, idx in api.get_indices_categorias().items():
            print(f"   {cat}: índice {idx}")
        
        print("\n" + "="*60 + "\n")
        
        # Test con filas que tienen el mismo nombre
        print("🔍 TEST: Filas con nombres repetidos")
        print("-" * 50)
        
        # Descuentos en Corporativos
        print("\n1️⃣ Descuentos en CORPORATIVOS:")
        tasas_corp = api.get_tasas_por_tipo("Descuentos", "Corporativos")
        print(f"   Bancos: {len(tasas_corp)}")
        for banco, tasa in sorted(tasas_corp.items(), key=lambda x: x[1])[:3]:
            print(f"   {banco}: {tasa}%")
        
        # Descuentos en Grandes Empresas
        print("\n2️⃣ Descuentos en GRANDES EMPRESAS:")
        tasas_ge = api.get_tasas_por_tipo("Descuentos", "Grandes Empresas")
        print(f"   Bancos: {len(tasas_ge)}")
        for banco, tasa in sorted(tasas_ge.items(), key=lambda x: x[1])[:3]:
            print(f"   {banco}: {tasa}%")
        
        # Verificar que son diferentes
        print("\n✅ VERIFICACIÓN:")
        if tasas_corp and tasas_ge:
            # Comparar una tasa específica
            banco_test = list(tasas_corp.keys())[0] if tasas_corp else "BBVA"
            tasa_corp = tasas_corp.get(banco_test, 0)
            tasa_ge = tasas_ge.get(banco_test, 0)
            print(f"   {banco_test} en Corporativos: {tasa_corp}%")
            print(f"   {banco_test} en Grandes Empresas: {tasa_ge}%")
            
            if tasa_corp != tasa_ge:
                print("   ✅ Las tasas son DIFERENTES (correcto!)")
            else:
                print("   ⚠️ Las tasas son iguales (verificar datos)")
        
    else:
        print("❌ Error de conexión, usando valores por defecto")