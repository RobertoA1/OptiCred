# modules/simulaciones.py
"""
Módulo para realizar simulaciones de pagos extraordinarios y análisis de estrategias.
"""
import pandas as pd
import numpy as np
from modules.interes import tea_a_tem
from modules.amortizacion import calcular_cuota_francesa, calcular_totales

def calcular_nuevo_cronograma_frances(principal, tea, plazo_restante, cuota_objetivo=None):
    """
    Genera un nuevo cronograma (tabla) dado un principal y un plazo o cuota objetivo.
    Si se da cuota_objetivo, calculamos cuánto tarda en pagarse (Reducción Plazo).
    Si no, calculamos nueva cuota para el plazo_restante (Reducción Cuota).
    """
    tem = tea_a_tem(tea)
    tabla = []
    saldo = principal
    
    if cuota_objetivo:
        migracion_maxima = 360
        cuota = cuota_objetivo
        mes_relativo = 1
        
        while saldo > 0.01 and mes_relativo <= migracion_maxima:
            interes = saldo * tem
            amortizacion = cuota - interes
            
            if amortizacion > saldo:
                amortizacion = saldo
                cuota = amortizacion + interes
            
            saldo_final = saldo - amortizacion
            
            tabla.append({
                'saldo_inicial': round(saldo, 2),
                'interes': round(interes, 2),
                'amortizacion': round(amortizacion, 2),
                'cuota': round(cuota, 2),
                'saldo_final': round(max(0, saldo_final), 2)
            })
            saldo = saldo_final
            mes_relativo += 1
            
    else:
        cuota = calcular_cuota_francesa(principal, tea, plazo_restante)
        for mes_relativo in range(1, int(plazo_restante) + 1):
            interes = saldo * tem
            amortizacion = cuota - interes
            saldo_final = saldo - amortizacion
            
            tabla.append({
                'saldo_inicial': round(saldo, 2),
                'interes': round(interes, 2),
                'amortizacion': round(amortizacion, 2),
                'cuota': round(cuota, 2),
                'saldo_final': round(max(0, saldo_final), 2)
            })
            saldo = saldo_final

    return pd.DataFrame(tabla)

def simular_pago_extraordinario(tabla_original, mes_pago, monto_extra, tea, tipo_reduccion="Cuota"):
    """
    Simula un pago extraordinario único en un mes específico.
    
    Args:
        tabla_original: DataFrame del cronograma original
        mes_pago: Número de mes donde se hace el pago extra (después de pagar la cuota normal)
        monto_extra: Monto del pago extra
        tea: Tasa Efectiva Anual
        tipo_reduccion: "Cuota" o "Plazo"
        
    Returns:
        dict: {
            'tabla_nueva': DataFrame,
            'resumen': dict de ahorros
        }
    """
    # 1. Copiar parte histórica (antes del prepago)
    # Asumimos que el pago extra se hace DESPUES de la cuota del 'mes_pago'
    # Por tanto, el saldo se reduce en ese momento.
    
    # Validar que mes_pago estÃ© dentro del rango
    if mes_pago >= len(tabla_original):
        return None
        
    parte_anterior = tabla_original[tabla_original['mes'] <= mes_pago].copy()
    
    # Obtener el saldo final del mes de pago antes del extra
    saldo_pre_extra = parte_anterior.iloc[-1]['saldo_final']
    
    # Aplicar pago extra
    saldo_post_extra = max(0, saldo_pre_extra - monto_extra)
    
    # Modificar saldo final del mes de pago en la tabla visualmente (opcional, o mostrarlo como evento)
    # Para consistencia, el mes_pago mantiene su cuota normal, pero su saldo final baja drásticamente.
    parte_anterior.iloc[-1, parte_anterior.columns.get_loc('saldo_final')] = saldo_post_extra
    
    if saldo_post_extra <= 0:
        # Se pagó todo
        tabla_nueva = parte_anterior
    else:
        # 2. Recalcular el futuro
        plazo_original_restante = len(tabla_original) - mes_pago
        cuota_original = tabla_original.iloc[0]['cuota'] # Asumiendo francés fijo
        
        if tipo_reduccion == "Plazo":
            # Mantener cuota, reducir plazo
            df_futuro = calcular_nuevo_cronograma_frances(saldo_post_extra, tea, plazo_original_restante, cuota_objetivo=cuota_original)
        else:
            # Mantener plazo, reducir cuota
            df_futuro = calcular_nuevo_cronograma_frances(saldo_post_extra, tea, plazo_original_restante)
            
        # Ajustar numeración de meses
        df_futuro['mes'] = range(mes_pago + 1, mes_pago + 1 + len(df_futuro))
        
        # Unir tablas
        tabla_nueva = pd.concat([parte_anterior, df_futuro], ignore_index=True)
        
    # Calcular métricas
    totales_original = calcular_totales(tabla_original)
    totales_nuevo = calcular_totales(tabla_nueva)
    
    # Al costo total nuevo hay que sumarle el pago extra que salió del bolsillo
    costo_financiero_nuevo = totales_nuevo['total_pagado'] + monto_extra
    
    ahorro_intereses = totales_original['total_intereses'] - totales_nuevo['total_intereses']
    tiempo_ahorrado = len(tabla_original) - len(tabla_nueva)
    
    return {
        'tabla_actualizada': tabla_nueva,
        'resumen': {
            'interes_original': totales_original['total_intereses'],
            'interes_nuevo': totales_nuevo['total_intereses'],
            'ahorro_intereses': ahorro_intereses,
            'total_pagado_original': totales_original['total_pagado'],
            'total_pagado_nuevo_real': costo_financiero_nuevo, # Cuotas + Extra
            'meses_ahorrados': tiempo_ahorrado,
            'nuevo_plazo': len(tabla_nueva)
        }
    }

def simular_pagos_recurrentes(monto_prestamo, tea, plazo_total, monto_extra_mensual, desde_mes):
    """
    Simula pagos extras recurrentes desde un mes específico hasta el final.
    Siempre reduce PLAZO (es lo natural al pagar más constante).
    """
    tem = tea_a_tem(tea)
    cuota_base = calcular_cuota_francesa(monto_prestamo, tea, plazo_total)
    
    tabla = []
    saldo = monto_prestamo
    
    max_iter = 360
    mes = 1
    
    while saldo > 0.01 and mes <= max_iter:
        interes = saldo * tem
        
        # Cuota normal
        pago_mes = cuota_base
        
        # Si estamos en período de pago extra
        extra = 0
        if mes >= desde_mes:
            extra = monto_extra_mensual
            
        # El pago total (cuota + extra)
        pago_total = pago_mes + extra
        
        # Amortización
        amortizacion = pago_total - interes
        
        # Ajuste final
        if amortizacion > saldo:
            amortizacion = saldo
            pago_total = amortizacion + interes
            # Recalculamos distribución para visualización
            # Si el pago total baja, asumimos que se reduce primero el extra, luego la cuota
            # Pero matemáticamente 'cuota' es lo que cuenta
        
        saldo_final = saldo - amortizacion
        
        tabla.append({
            'mes': mes,
            'saldo_inicial': round(saldo, 2),
            'interes': round(interes, 2),
            'amortizacion': round(amortizacion, 2),
            'cuota_base': round(pago_mes, 2), # La exigible
            'pago_extra': round(extra if pago_total > pago_mes else max(0, pago_total - pago_mes), 2),
            'total_pagado': round(pago_total, 2),
            'saldo_final': round(max(0, saldo_final), 2)
        })
        
        saldo = saldo_final
        mes += 1
        
    return pd.DataFrame(tabla)

def comparar_estrategias_prepago(monto_prestamo, tea, plazo, presupuesto_anual_extra):
    """
    Compara 3 estrategias dado un presupuesto ANUAL de prepago:
    1. Mensual: presupuesto / 12 cada mes.
    2. Semestral: presupuesto / 2 cada 6 meses.
    3. Anual: presupuesto entero en el mes 12 de cada año.
    """
    estrategias = []
    
    # Caso Base (Sin prepago)
    base_df = calcular_nuevo_cronograma_frances(monto_prestamo, tea, plazo) # Reusing logic to generate pure french
    base_df['mes'] = base_df.index + 1
    base_totales = calcular_totales(base_df)
    estrategias.append({
        'nombre': 'Sin Prepago',
        'interes_total': base_totales['total_intereses'],
        'plazo': len(base_df),
        'ahorro': 0
    })
    
    # Estrategia 1: Mensual
    monto_mensual = presupuesto_anual_extra / 12
    # Simulamos recorriendo mes a mes
    # Reutilizamos logica de simular_pagos_recurrentes
    df_mensual = simular_pagos_recurrentes(monto_prestamo, tea, plazo, monto_mensual, 1)
    totales_mensual = df_mensual['interes'].sum()
    estrategias.append({
        'nombre': 'Pago Mensual',
        'interes_total': totales_mensual,
        'plazo': len(df_mensual),
        'ahorro': base_totales['total_intereses'] - totales_mensual
    })

    # Estrategia 2: Anual (Mes 12, 24, 36...)
    # Custom simulation loop needed for periodic
    df_anual = _simular_pagos_periodicos(monto_prestamo, tea, plazo, presupuesto_anual_extra, 12)
    totales_anual = df_anual['interes'].sum()
    estrategias.append({
        'nombre': 'Pago Anual',
        'interes_total': totales_anual,
        'plazo': len(df_anual),
        'ahorro': base_totales['total_intereses'] - totales_anual
    })

    return pd.DataFrame(estrategias)

def _simular_pagos_periodicos(monto, tea, plazo, monto_extra, periodo_meses):
    """Helper para pagos cada N meses"""
    tem = tea_a_tem(tea)
    cuota_base = calcular_cuota_francesa(monto, tea, plazo)
    
    tabla = []
    saldo = monto
    mes = 1
    
    while saldo > 0.01 and mes <= 360:
        interes = saldo * tem
        pago_mes = cuota_base
        
        extra = 0
        if mes % periodo_meses == 0:
            extra = monto_extra
            
        pago_total = pago_mes + extra
        amortizacion = pago_total - interes
        
        if amortizacion > saldo:
            amortizacion = saldo
        
        saldo_final = saldo - amortizacion
        
        tabla.append({
            'mes': mes,
            'interes': interes,
            'amortizacion': amortizacion,
            'cuota': pago_total,
            'saldo_final': saldo_final
        })
        
        saldo = saldo_final
        mes += 1
        
    return pd.DataFrame(tabla)
