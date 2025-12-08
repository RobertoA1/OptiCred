# modules/amortizacion.py
"""
Módulo para generar tablas de amortización (Sistema Francés y Alemán).
"""
import pandas as pd
from modules.interes import tea_a_tem

# ==================== SISTEMA FRANCÉS ====================

def calcular_cuota_francesa(monto, tea, plazo):
    """
    Calcula la cuota mensual fija del sistema francés.
    
    Args:
        monto: Monto del préstamo
        tea: Tasa Efectiva Anual (en decimal)
        plazo: Plazo en meses
    
    Returns:
        cuota: Cuota mensual
    """
    tem = tea_a_tem(tea)
    
    if tem == 0:
        return monto / plazo
    
    cuota = monto * (tem * (1 + tem)**plazo) / ((1 + tem)**plazo - 1)
    return cuota

def generar_tabla_francesa(monto, tea, plazo):
    """
    Genera la tabla de amortización completa sistema francés.
    
    Returns:
        DataFrame con columnas: mes, saldo_inicial, interes, amortizacion, cuota, saldo_final
    """
    tem = tea_a_tem(tea)
    cuota = calcular_cuota_francesa(monto, tea, plazo)
    
    tabla = []
    saldo = monto
    
    for mes in range(1, plazo + 1):
        interes = saldo * tem
        amortizacion = cuota - interes
        saldo_final = saldo - amortizacion
        
        tabla.append({
            'mes': mes,
            'saldo_inicial': round(saldo, 2),
            'interes': round(interes, 2),
            'amortizacion': round(amortizacion, 2),
            'cuota': round(cuota, 2),
            'saldo_final': round(max(0, saldo_final), 2)
        })
        
        saldo = saldo_final
    
    return pd.DataFrame(tabla)

# ==================== SISTEMA ALEMÁN ====================

def calcular_amortizacion_alemana(monto, plazo):
    """
    Calcula la amortización constante del sistema alemán.
    
    Args:
        monto: Monto del préstamo
        plazo: Plazo en meses
    
    Returns:
        amortizacion_fija: Monto constante de amortización por mes
    """
    return monto / plazo

def calcular_cuota_alemana(saldo_actual, amortizacion_fija, tem):
    """
    Calcula la cuota variable del sistema alemán para un mes específico.
    
    Args:
        saldo_actual: Saldo pendiente actual
        amortizacion_fija: Amortización constante mensual
        tem: Tasa Efectiva Mensual (en decimal)
    
    Returns:
        cuota: Cuota del mes (amortización + interés)
    """
    interes = saldo_actual * tem
    cuota = amortizacion_fija + interes
    return cuota

def generar_tabla_alemana(monto, tea, plazo):
    """
    Genera la tabla de amortización completa sistema alemán.
    
    En el sistema alemán:
    - La amortización es CONSTANTE cada mes
    - Los intereses DECRECEN (porque el saldo disminuye)
    - La cuota DECRECE cada mes
    
    Returns:
        DataFrame con columnas: mes, saldo_inicial, interes, amortizacion, cuota, saldo_final
    """
    tem = tea_a_tem(tea)
    amortizacion_fija = calcular_amortizacion_alemana(monto, plazo)
    
    tabla = []
    saldo = monto
    
    for mes in range(1, plazo + 1):
        interes = saldo * tem
        amortizacion = amortizacion_fija
        cuota = amortizacion + interes
        saldo_final = saldo - amortizacion
        
        tabla.append({
            'mes': mes,
            'saldo_inicial': round(saldo, 2),
            'interes': round(interes, 2),
            'amortizacion': round(amortizacion, 2),
            'cuota': round(cuota, 2),
            'saldo_final': round(max(0, saldo_final), 2)
        })
        
        saldo = saldo_final
    
    return pd.DataFrame(tabla)

# ==================== FUNCIONES COMUNES ====================

def calcular_totales(tabla_df):
    """
    Calcula los totales de una tabla de amortización.
    Funciona tanto para sistema francés como alemán.
    """
    return {
        'total_intereses': tabla_df['interes'].sum(),
        'total_amortizacion': tabla_df['amortizacion'].sum(),
        'total_pagado': tabla_df['cuota'].sum()
    }

def comparar_sistemas(monto, tea, plazo):
    """
    Compara ambos sistemas de amortización.
    
    Returns:
        dict con tablas y totales de ambos sistemas
    """
    tabla_francesa = generar_tabla_francesa(monto, tea, plazo)
    tabla_alemana = generar_tabla_alemana(monto, tea, plazo)
    
    totales_francesa = calcular_totales(tabla_francesa)
    totales_alemana = calcular_totales(tabla_alemana)
    
    return {
        'francesa': {
            'tabla': tabla_francesa,
            'totales': totales_francesa
        },
        'alemana': {
            'tabla': tabla_alemana,
            'totales': totales_alemana
        },
        'diferencia_intereses': totales_francesa['total_intereses'] - totales_alemana['total_intereses'],
        'ahorro_sistema_aleman': totales_francesa['total_intereses'] - totales_alemana['total_intereses']
    }