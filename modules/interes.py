"""
Módulo para cálculos de tasas de interés y conversiones.
"""

def tea_a_tem(tea):
    tem = (1 + tea) ** (1/12) - 1
    return tem

def tem_a_tea(tem):
    tea = (1 + tem) ** 12 - 1
    return tea

def tna_a_tea(tna, capitalizacion=12):
    tea = (1 + tna/capitalizacion) ** capitalizacion - 1
    return tea

def calcular_tcea(monto, cuota_mensual, plazo, costos_iniciales=0):
    import numpy_financial as npf
    
    flujos = [-monto + costos_iniciales] + [cuota_mensual] * plazo
    
    # Calcular TIR mensual
    try:
        tir_mensual = npf.irr(flujos)
        tcea = (1 + tir_mensual) ** 12 - 1
        return tcea * 100
    except:
        return None

def calcular_tcea_completa(
    monto, 
    tea, 
    plazo, 
    comision_desembolso=0,
    comision_mensual=0,
    seguro_desgravamen=0,
    portes_mensuales=0
):
    """
    Calcula la Tasa de Costo Efectivo Anual (TCEA) completa considerando TODOS los costos.
    
    La TCEA es la tasa que iguala el valor presente de todos los flujos de efectivo
    (desembolso neto y pagos totales) según la SBS.
    
    Args:
        monto: Monto del préstamo (S/)
        tea: Tasa Efectiva Anual del crédito (en decimal, ej: 0.20 para 20%)
        plazo: Plazo en meses
        comision_desembolso: Comisión inicial como % del monto (en decimal, ej: 0.01 para 1%)
        comision_mensual: Comisión fija mensual (S/)
        seguro_desgravamen: Seguro mensual como % sobre saldo (en decimal, ej: 0.0005 para 0.05%)
        portes_mensuales: Portes y gastos mensuales fijos (S/)
    
    Returns:
        tcea: TCEA en porcentaje (%)
        
    Ejemplo:
        >>> calcular_tcea_completa(10000, 0.20, 12, 0.01, 5, 0.0005, 3)
        22.45  # TCEA = 22.45%
    """
    import numpy_financial as npf
    from modules.amortizacion import generar_tabla_francesa
    
    # Calcular comisión inicial
    monto_comision_desembolso = monto * comision_desembolso
    
    # Monto neto recibido por el cliente (negativo porque es un egreso para el banco)
    desembolso_neto = monto - monto_comision_desembolso
    
    # Generar tabla de amortización para obtener saldos mes a mes
    tabla = generar_tabla_francesa(monto, tea, plazo)
    
    # Construir flujos de caja mensuales
    flujos = [-desembolso_neto]  # Mes 0: cliente recibe el dinero (egreso para banco)
    
    for i in range(len(tabla)):
        # Cuota base del mes
        cuota_base = tabla.loc[i, 'cuota']
        
        # Saldo inicial del mes (para calcular seguro de desgravamen)
        saldo_inicial = tabla.loc[i, 'saldo_inicial']
        
        # Calcular seguro de desgravamen sobre el saldo
        seguro_mes = saldo_inicial * seguro_desgravamen
        
        # Cuota total del mes = cuota base + comisión mensual + seguro + portes
        cuota_total_mes = cuota_base + comision_mensual + seguro_mes + portes_mensuales
        
        flujos.append(cuota_total_mes)
    
    # Calcular TIR mensual
    try:
        tir_mensual = npf.irr(flujos)
        
        # Convertir TIR mensual a TCEA (anualizar)
        tcea = (1 + tir_mensual) ** 12 - 1
        
        return tcea * 100  # Retornar en porcentaje
    
    except Exception as e:
        # En caso de error (convergencia, flujos inválidos, etc.)
        return None

def calcular_cae(monto, plazo, costo_total):
    """
    Calcula el Costo Anual Equivalente (CAE).
    
    El CAE representa el costo total del crédito expresado como una tasa anual.
    
    Args:
        monto: Monto del préstamo
        plazo: Plazo en meses
        costo_total: Costo total del crédito (todo lo que pagará el cliente)
    
    Returns:
        cae: CAE en porcentaje
    """
    # Costo financiero total
    costo_financiero = costo_total - monto
    
    # CAE = (Costo Financiero / Monto) * (12 / Plazo) * 100
    cae = (costo_financiero / monto) * (12 / plazo) * 100
    
    return cae

def calcular_tcea_simplificada(monto, cuota_base, plazo, comisiones_totales, seguros_totales):
    """
    Método alternativo simplificado para calcular TCEA cuando no se tiene
    el detalle mes a mes.
    
    Args:
        monto: Monto del préstamo
        cuota_base: Cuota mensual base (sin costos adicionales)
        plazo: Plazo en meses
        comisiones_totales: Suma de todas las comisiones durante el crédito
        seguros_totales: Suma de todos los seguros durante el crédito
    
    Returns:
        tcea_aproximada: TCEA aproximada en porcentaje
    """
    import numpy_financial as npf
    
    # Cuota promedio con costos
    costos_mensuales = (comisiones_totales + seguros_totales) / plazo
    cuota_total_promedio = cuota_base + costos_mensuales
    
    # Flujos simplificados
    flujos = [-monto] + [cuota_total_promedio] * plazo
    
    try:
        tir_mensual = npf.irr(flujos)
        tcea = (1 + tir_mensual) ** 12 - 1
        return tcea * 100
    except:
        return None

def comparar_tea_vs_tcea(monto, tea, plazo, comision_desembolso, comision_mensual, seguro_desgravamen, portes):
    """
    Compara la TEA (tasa del crédito) con la TCEA (costo real total).
    
    Returns:
        dict con TEA, TCEA y la diferencia
    """
    tcea = calcular_tcea_completa(
        monto, tea, plazo, 
        comision_desembolso, comision_mensual, 
        seguro_desgravamen, portes
    )
    
    tea_porcentaje = tea * 100
    
    if tcea:
        diferencia = tcea - tea_porcentaje
        return {
            'tea': tea_porcentaje,
            'tcea': tcea,
            'diferencia': diferencia,
            'diferencia_relativa': (diferencia / tea_porcentaje) * 100
        }
    else:
        return None

def validar_tcea(tcea, tea):
    """
    Valida que la TCEA sea coherente (siempre debe ser >= TEA).
    
    Returns:
        tuple: (es_valida, mensaje)
    """
    tea_porcentaje = tea * 100
    
    if tcea is None:
        return False, "No se pudo calcular la TCEA"
    
    if tcea < tea_porcentaje:
        return False, f"Error: TCEA ({tcea:.2f}%) no puede ser menor que TEA ({tea_porcentaje:.2f}%)"
    
    if tcea > tea_porcentaje * 3:
        return False, f"Advertencia: TCEA ({tcea:.2f}%) parece muy alta respecto a TEA ({tea_porcentaje:.2f}%)"
    
    return True, f"TCEA válida: {tcea:.2f}% (TEA: {tea_porcentaje:.2f}%)"