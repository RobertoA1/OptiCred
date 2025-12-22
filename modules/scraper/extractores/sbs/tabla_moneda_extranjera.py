from bs4 import BeautifulSoup
import pandas as pd
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Tabla_Moneda_Extranjera:
    def __init__(self, soup: BeautifulSoup):
        self.soup = soup

    def _extraer_encabezado_vertical(self) -> pd.Series:
        soup = self.soup

        div = soup.find(id='ctl00_cphContent_rpgActualMex')
        tabla_moneda_extranjera = div.table
        filas = tabla_moneda_extranjera.tbody.contents
        
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

        return serie_encabezado_vertical

    def _extraer_encabezado_horizontal(self) -> pd.Series:
        soup = self.soup

        div = soup.find(id='ctl00_cphContent_rpgActualMex')
        tabla_moneda_extranjera = div.table
        filas = tabla_moneda_extranjera.find(id='ctl00_cphContent_rpgActualMex_ctl00_DataZone_DT').thead.tr.contents

        serie_encabezado_horizontal = pd.Series()
        thsEncabezadoHorizontal = filas[1:-1]
        for th in thsEncabezadoHorizontal:
            nombre = th.text.strip()
            serie_encabezado_horizontal = pd.concat([serie_encabezado_horizontal, pd.Series([nombre])])

        return serie_encabezado_horizontal

    def _obtener_datos(self, df: pd.DataFrame) -> pd.DataFrame:
        soup = self.soup

        div = soup.find(id='ctl00_cphContent_rpgActualMex')
        tabla_moneda_nacional = div.table

        filas = tabla_moneda_nacional.find(id='ctl00_cphContent_rpgActualMex_ctl00_DataZone_DT').tbody.contents
        filas = filas[1:-1]
        for i in range(0, len(df.index)):
            tr = filas[i]
            tds = tr.contents
            for j in range(1, len(df.columns) + 1):
                td = tds[j]
                valor = td.text.strip()
                try:
                    float(valor)
                except:
                    valor = -1
                
                df.iloc[i, j - 1] = float(valor)

        return df

    def obtener(self) -> pd.DataFrame:
        serie_encabezado_vertical = self._extraer_encabezado_vertical()
        serie_encabezado_horizontal = self._extraer_encabezado_horizontal()

        resultado = pd.DataFrame(index=serie_encabezado_vertical, columns=serie_encabezado_horizontal)
        self._obtener_datos(resultado)

        return resultado