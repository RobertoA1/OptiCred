# modules/api_tasas.py
"""
Módulo de integración entre la API de tasas SBS y el comparador de créditos.
Soporta el formato "Categoría - Tipo" del selector en cascada.
"""
import asyncio
from typing import Optional, List, Dict, Tuple
import pandas as pd
import streamlit as st
import logging

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
            "Préstamos a cuota fija de 31 a 90 días": "Préstamos a cuota fija de 31 a 90 días",
            "Préstamos a cuota fija de 91 a 180 días": "Préstamos a cuota fija de 91 a 180 días",
            "Préstamos a cuota fija de 181 a 360 días": "Préstamos a cuota fija de 181 a 360 días",
            "Préstamos a cuota fija a más de 360 días": "Préstamos a cuota fija a más de 360 días",
        }
    },
    "Consumo": {
        "descripcion": "Créditos para personas naturales (uso personal)",
        "opciones": {
            "Tarjetas de Crédito": "Tarjetas de Crédito",
            "Préstamos Revolventes": "Préstamos Revolventes",
            "Préstamos para Automóviles": "Préstamos no Revolventes para automóviles",
            "Libre Disponibilidad (hasta 360 días)": "Préstamos no Revolventes para libre disponibilidad hasta 360 días",
            "Libre Disponibilidad (más de 360 días)": "Préstamos no Revolventes para libre disponibilidad a más de 360 días",
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


class APITasas:
    """
    Clase para obtener tasas de interés reales desde la API SBS.
    Soporta formato "Categoría - Tipo" del selector en cascada.
    """
    
    def __init__(self):
        self._tasas_activas: Optional[pd.DataFrame] = None
        self._bancos: Optional[pd.Series] = None
        self._cache_cargado = False
    
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
            logger.info("✅ Datos cargados desde la API")
            return True
        except Exception as e:
            logger.error(f"❌ Error al cargar datos: {e}")
            return False
    
    def _asegurar_datos(self):
        """Asegura que los datos estén cargados."""
        if not self._cache_cargado:
            self.cargar_datos()
    
    # =========================================================================
    # MÉTODO CLAVE: RESOLVER FILA EN LA TABLA
    # =========================================================================
    
    def _resolver_fila_tabla(self, tipo_credito: str) -> str:
        """
        Resuelve el nombre de la fila en la tabla SBS.
        
        Acepta:
        - Formato "Categoría - Tipo" (ej: "Consumo - Préstamos para Automóviles")
        - Nombre directo de la fila (ej: "Préstamos de 31 a 90 días")
        
        Returns:
            Nombre exacto de la fila en la tabla SBS
        """
        # Si viene en formato "Categoría - Tipo específico"
        if " - " in tipo_credito:
            partes = tipo_credito.split(" - ", 1)
            categoria = partes[0].strip()
            tipo_especifico = partes[1].strip()
            
            # Buscar en CATEGORIAS_CREDITO
            if categoria in CATEGORIAS_CREDITO:
                opciones = CATEGORIAS_CREDITO[categoria]["opciones"]
                if tipo_especifico in opciones:
                    return opciones[tipo_especifico]
            
            # Fallback: usar el tipo específico directamente
            return tipo_especifico
        
        # Si es un nombre directo, devolverlo tal cual
        return tipo_credito
    
    # =========================================================================
    # MÉTODOS PÚBLICOS - BANCOS
    # =========================================================================
    
    def get_bancos(self, tipo_credito: str = None) -> List[str]:
        """
        Obtiene la lista de bancos disponibles.
        Si se especifica tipo_credito, filtra los que tienen tasa válida (≠ -1).
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
        if tipo_credito and self._tasas_activas is not None:
            bancos_con_tasa = self._filtrar_bancos_con_tasa(tipo_credito)
            if bancos_con_tasa:
                return bancos_con_tasa
        
        return bancos_lista if bancos_lista else self._bancos_default()
    
    def _bancos_default(self) -> List[str]:
        """Lista de bancos por defecto."""
        return ["BBVA", "Crédito", "Interbank", "Scotiabank", "Pichincha", "BIF", "GNB", "Mibanco"]
    
    def _filtrar_bancos_con_tasa(self, tipo_credito: str) -> List[str]:
        """Filtra bancos que tienen tasa válida (> 0) para el tipo de crédito."""
        if self._tasas_activas is None or self._tasas_activas.empty:
            return []
        
        # Resolver el nombre de la fila
        fila_buscar = self._resolver_fila_tabla(tipo_credito)
        bancos_validos = []
        
        df = self._tasas_activas
        
        # Buscar la fila en el DataFrame (puede estar en el índice o en la primera columna)
        fila_encontrada = None
        
        # Opción 1: Buscar en el índice
        for idx in df.index:
            idx_str = str(idx).strip()
            if idx_str == fila_buscar or fila_buscar in idx_str or idx_str in fila_buscar:
                fila_encontrada = df.loc[idx]
                break
        
        # Opción 2: Buscar en la primera columna si no se encontró
        if fila_encontrada is None and len(df.columns) > 0:
            primera_col = df.columns[0]
            for idx, row in df.iterrows():
                valor_col = str(row[primera_col]).strip()
                if valor_col == fila_buscar or fila_buscar in valor_col or valor_col in fila_buscar:
                    fila_encontrada = row
                    break
        
        if fila_encontrada is None:
            return []
        
        # Extraer bancos con tasas válidas
        for col in df.columns:
            col_str = str(col).strip()
            # Saltar columnas que no son bancos
            if col_str.lower() in ['', 'tipo', 'producto', 'promedio']:
                continue
            try:
                valor = float(fila_encontrada[col])
                if valor > 0:  # -1 = no disponible
                    bancos_validos.append(col_str)
            except (ValueError, TypeError, KeyError):
                continue
        
        return bancos_validos
    
    # =========================================================================
    # MÉTODOS PÚBLICOS - TASAS
    # =========================================================================
    
    def get_tea(self, banco: str, tipo_credito: str) -> float:
        """
        Obtiene la TEA de un banco para un tipo de crédito.
        
        Args:
            banco: Nombre del banco (ej: "BBVA", "Crédito")
            tipo_credito: Tipo de crédito (ej: "Consumo - Préstamos para Automóviles")
        
        Returns:
            TEA como porcentaje (ej: 12.5)
        """
        self._asegurar_datos()
        
        if self._tasas_activas is None or self._tasas_activas.empty:
            return self._tea_default(tipo_credito)
        
        fila_buscar = self._resolver_fila_tabla(tipo_credito)
        df = self._tasas_activas
        
        # Buscar la fila
        fila_encontrada = None
        
        for idx in df.index:
            idx_str = str(idx).strip()
            if idx_str == fila_buscar or fila_buscar in idx_str or idx_str in fila_buscar:
                fila_encontrada = df.loc[idx]
                break
        
        if fila_encontrada is None and len(df.columns) > 0:
            primera_col = df.columns[0]
            for idx, row in df.iterrows():
                valor_col = str(row[primera_col]).strip()
                if valor_col == fila_buscar or fila_buscar in valor_col or valor_col in fila_buscar:
                    fila_encontrada = row
                    break
        
        if fila_encontrada is None:
            return self._tea_default(tipo_credito)
        
        # Buscar el banco en las columnas
        for col in df.columns:
            if self._coincide_banco(banco, str(col)):
                try:
                    valor = float(fila_encontrada[col])
                    if valor > 0:
                        return valor
                except (ValueError, TypeError, KeyError):
                    continue
        
        return self._tea_default(tipo_credito)
    
    def _coincide_banco(self, banco_buscado: str, columna: str) -> bool:
        """Verifica si el nombre del banco coincide con la columna."""
        banco_lower = banco_buscado.lower().strip()
        col_lower = columna.lower().strip()
        
        # Coincidencia exacta
        if banco_lower == col_lower:
            return True
        
        # Coincidencia parcial
        if banco_lower in col_lower or col_lower in banco_lower:
            return True
        
        # Alias comunes
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
    
    def _tea_default(self, tipo_credito: str) -> float:
        """TEA por defecto cuando no hay datos."""
        # Extraer categoría si viene en formato "Categoría - Tipo"
        categoria = tipo_credito.split(" - ")[0] if " - " in tipo_credito else tipo_credito
        
        defaults = {
            "Consumo": 35.0,
            "Hipotecarios": 9.0,
            "Hipotecario": 9.0,
            "Corporativo": 6.0,
            "Grandes Empresas": 8.0,
            "Medianas Empresas": 12.0,
            "Pequeñas Empresas": 18.0,
            "Microempresas": 35.0,
        }
        
        return defaults.get(categoria, 15.0)
    
    def get_promedio(self, tipo_credito: str) -> float:
        """
        Obtiene el promedio de tasas del mercado.
        Usa la columna 'Promedio' de la tabla SBS directamente.
        """
        self._asegurar_datos()
        
        if self._tasas_activas is None or self._tasas_activas.empty:
            return self._tea_default(tipo_credito)
        
        fila_buscar = self._resolver_fila_tabla(tipo_credito)
        df = self._tasas_activas
        
        # Buscar la fila
        fila_encontrada = None
        
        for idx in df.index:
            idx_str = str(idx).strip()
            if idx_str == fila_buscar or fila_buscar in idx_str or idx_str in fila_buscar:
                fila_encontrada = df.loc[idx]
                break
        
        if fila_encontrada is None and len(df.columns) > 0:
            primera_col = df.columns[0]
            for idx, row in df.iterrows():
                valor_col = str(row[primera_col]).strip()
                if valor_col == fila_buscar or fila_buscar in valor_col or valor_col in fila_buscar:
                    fila_encontrada = row
                    break
        
        if fila_encontrada is None:
            return self._tea_default(tipo_credito)
        
        # PRIMERO: Buscar la columna "Promedio" (última columna generalmente)
        for col in df.columns:
            col_str = str(col).strip().lower()
            if 'promedio' in col_str:
                try:
                    val = float(fila_encontrada[col])
                    if val > 0:
                        return val
                except (ValueError, TypeError, KeyError):
                    pass
        
        # FALLBACK: Si no hay columna Promedio, calcular manualmente
        valores = []
        for col in df.columns:
            col_str = str(col).strip().lower()
            # Saltar columnas que no son bancos
            if col_str in ['', 'tipo', 'producto', 'promedio']:
                continue
            try:
                val = float(fila_encontrada[col])
                if val > 0:  # Excluir -1
                    valores.append(val)
            except (ValueError, TypeError, KeyError):
                continue
        
        if valores:
            return sum(valores) / len(valores)
        
        return self._tea_default(tipo_credito)
    
    def get_tasas_por_tipo(self, tipo_credito: str) -> Dict[str, float]:
        """Obtiene todas las tasas disponibles para un tipo de crédito."""
        self._asegurar_datos()
        
        resultado = {}
        
        if self._tasas_activas is None or self._tasas_activas.empty:
            for banco in self._bancos_default():
                resultado[banco] = self._tea_default(tipo_credito)
            return resultado
        
        fila_buscar = self._resolver_fila_tabla(tipo_credito)
        df = self._tasas_activas
        
        # Buscar la fila
        fila_encontrada = None
        
        for idx in df.index:
            idx_str = str(idx).strip()
            if idx_str == fila_buscar or fila_buscar in idx_str or idx_str in fila_buscar:
                fila_encontrada = df.loc[idx]
                break
        
        if fila_encontrada is None and len(df.columns) > 0:
            primera_col = df.columns[0]
            for idx, row in df.iterrows():
                valor_col = str(row[primera_col]).strip()
                if valor_col == fila_buscar or fila_buscar in valor_col or valor_col in fila_buscar:
                    fila_encontrada = row
                    break
        
        if fila_encontrada is None:
            return resultado
        
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
    
    def get_mejor_tasa(self, tipo_credito: str) -> Tuple[str, float]:
        """Obtiene el banco con la mejor tasa (más baja)."""
        tasas = self.get_tasas_por_tipo(tipo_credito)
        
        if not tasas:
            return ("N/A", self._tea_default(tipo_credito))
        
        mejor_banco = min(tasas, key=tasas.get)
        return (mejor_banco, tasas[mejor_banco])
    
    def get_peor_tasa(self, tipo_credito: str) -> Tuple[str, float]:
        """Obtiene el banco con la peor tasa (más alta)."""
        tasas = self.get_tasas_por_tipo(tipo_credito)
        
        if not tasas:
            return ("N/A", self._tea_default(tipo_credito))
        
        peor_banco = max(tasas, key=tasas.get)
        return (peor_banco, tasas[peor_banco])
    
    def get_rango_tasas(self, tipo_credito: str) -> Tuple[float, float]:
        """Obtiene (tasa_minima, tasa_maxima) para un tipo de crédito."""
        tasas = self.get_tasas_por_tipo(tipo_credito)
        valores = list(tasas.values())
        
        if not valores:
            default = self._tea_default(tipo_credito)
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


def obtener_bancos(tipo_credito: str = None) -> List[str]:
    """Obtiene bancos disponibles."""
    df_tasas, df_bancos, conectado = cargar_datos_api()
    
    if not conectado:
        return APITasas()._bancos_default()
    
    api = APITasas()
    api._tasas_activas = df_tasas
    api._bancos = df_bancos
    api._cache_cargado = True
    
    return api.get_bancos(tipo_credito)


def obtener_tea(banco: str, tipo_credito: str) -> float:
    """Obtiene TEA de un banco."""
    df_tasas, df_bancos, conectado = cargar_datos_api()
    
    if not conectado:
        return APITasas()._tea_default(tipo_credito)
    
    api = APITasas()
    api._tasas_activas = df_tasas
    api._bancos = df_bancos
    api._cache_cargado = True
    
    return api.get_tea(banco, tipo_credito)


def obtener_promedio(tipo_credito: str) -> float:
    """Obtiene promedio del mercado."""
    df_tasas, df_bancos, conectado = cargar_datos_api()
    
    if not conectado:
        return APITasas()._tea_default(tipo_credito)
    
    api = APITasas()
    api._tasas_activas = df_tasas
    api._bancos = df_bancos
    api._cache_cargado = True
    
    return api.get_promedio(tipo_credito)


# =============================================================================
# TEST
# =============================================================================

if __name__ == "__main__":
    print("=== Test de APITasas ===\n")
    
    api = APITasas()
    
    # Test del resolver
    print("📋 Test de _resolver_fila_tabla:")
    tests = [
        "Consumo - Préstamos para Automóviles",
        "Consumo - Libre Disponibilidad (más de 360 días)",
        "Corporativo - Préstamos de 31 a 90 días",
        "Hipotecarios - Préstamos para Vivienda",
        "Préstamos de 31 a 90 días",  # Directo
    ]
    
    for test in tests:
        resultado = api._resolver_fila_tabla(test)
        print(f"  '{test}' → '{resultado}'")
    
    print("\n" + "="*50 + "\n")
    
    if api.cargar_datos():
        print("✅ Conexión exitosa\n")
        
        tipo_test = "Consumo - Préstamos para Automóviles"
        
        print(f"📊 Tasas para '{tipo_test}':")
        tasas = api.get_tasas_por_tipo(tipo_test)
        for banco, tasa in sorted(tasas.items(), key=lambda x: x[1]):
            print(f"  {banco}: {tasa}%")
        
        print(f"\n📈 Promedio: {api.get_promedio(tipo_test):.2f}%")
        
        mejor_banco, mejor_tasa = api.get_mejor_tasa(tipo_test)
        print(f"🏆 Mejor: {mejor_banco} con {mejor_tasa}%")
    else:
        print("❌ Error de conexión, usando valores por defecto")