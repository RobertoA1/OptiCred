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