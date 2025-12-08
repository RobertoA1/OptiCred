# modulos/utilidades.py
"""
Funciones auxiliares y de validación.
"""

def formatear_moneda(valor):
    """Formatea un número como moneda peruana."""
    return f"S/ {valor:,.2f}"

def validar_datos_credito(monto, tea, plazo):
    """
    Valida los inputs de un crédito.
    
    Returns:
        tuple: (es_valido, lista_errores)
    """
    errores = []
    
    if monto <= 0:
        errores.append("❌ El monto debe ser mayor a 0")
    elif monto > 1_000_000:
        errores.append("⚠️ El monto parece muy alto (máx: S/ 1,000,000)")
    
    if tea <= 0:
        errores.append("❌ La TEA debe ser mayor a 0%")
    elif tea > 1.0:  # 100%
        errores.append("⚠️ La TEA parece muy alta (>100%)")
    
    if plazo <= 0:
        errores.append("❌ El plazo debe ser mayor a 0 meses")
    elif plazo > 360:
        errores.append("⚠️ El plazo parece muy largo (máx: 360 meses)")
    
    return len(errores) == 0, errores

def calcular_porcentaje_interes(tabla_df):
    """Calcula qué porcentaje del total pagado corresponde a intereses."""
    total_pagado = tabla_df['cuota'].sum()
    total_intereses = tabla_df['interes'].sum()
    return (total_intereses / total_pagado) * 100 if total_pagado > 0 else 0