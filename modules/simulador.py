# modules/simulador.py
"""
Función para mostrar el simulador de pagos extraordinarios
"""
import streamlit as st
import pandas as pd
import altair as alt
from modules.amortizacion import generar_tabla_francesa
from modules.simulaciones import (
    simular_pago_extraordinario, 
    simular_pagos_recurrentes, 
    comparar_estrategias_prepago
)

def mostrar_simulador_pagos():
    """
    Muestra la interfaz del simulador de pagos extraordinarios
    """
    st.title("🔄 Simulador de Pagos Extraordinarios")
    st.markdown("Descubre cuánto puedes ahorrar haciendo pagos adicionales a tu crédito.")
    
    with st.sidebar:
        st.header("1. Datos del Crédito")
        monto = st.number_input("Monto del Préstamo (S/)", min_value=1000.0, value=50000.0, step=1000.0)
        tea = st.number_input("Tasa Efectiva Anual (TEA %)", min_value=1.0, max_value=200.0, value=15.0, step=0.1)
        plazo = st.number_input("Plazo Original (meses)", min_value=6, max_value=360, value=24, step=6)
        
        st.info(f"Cuota aprox. original: S/ {generar_tabla_francesa(monto, tea/100, plazo).iloc[0]['cuota']:,.2f}")

    tab1, tab2, tab3 = st.tabs(["💰 Pago Único", "📅 Pagos Recurrentes", "📊 Comparar Estrategias"])
    
    with tab1:
        st.subheader("Simulación de Pago Único (Prepago)")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            mes_prepago = st.number_input("¿En qué mes harás el pago?", min_value=1, max_value=plazo-1, value=6)
        with col2:
            monto_prepago = st.number_input("Monto del pago extra (S/)", min_value=100.0, value=5000.0, step=100.0)
        with col3:
            tipo_reduccion = st.selectbox("Tipo de Reducción", ["Cuota", "Plazo"], help="Reducir Cuota: Pagas lo mismo más tiempo. Reducir Plazo: Pagas menos tiempo.")

        if st.button("Simular Pago Único", type="primary"):
            tabla_base = generar_tabla_francesa(monto, tea/100, plazo)
            
            resultado = simular_pago_extraordinario(tabla_base, mes_prepago, monto_prepago, tea/100, tipo_reduccion)
            
            if resultado:
                resumen = resultado['resumen']
                tabla_nueva = resultado['tabla_actualizada']
                
                st.divider()
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Ahorro Intereses", f"S/ {resumen['ahorro_intereses']:,.2f}", delta_color="normal")
                m2.metric("Meses Ahorrados", f"{resumen['meses_ahorrados']} meses")
                m3.metric("Total Intereses Nuevo", f"S/ {resumen['interes_nuevo']:,.2f}")
                m4.metric("Costo Financiero Total", f"S/ {resumen['total_pagado_nuevo_real']:,.2f}")
                
                st.subheader("Visualización del Impacto")
                
                chart_data = pd.DataFrame({
                    'Mes': range(1, len(tabla_base) + 1),
                    'Saldo Original': tabla_base['saldo_final'],
                })
                new_balance = tabla_nueva['saldo_final'].tolist()
                new_balance += [0] * (len(chart_data) - len(new_balance))
                chart_data['Nuevo Saldo'] = new_balance[:len(chart_data)] 
                
                chart_melted = chart_data.melt('Mes', var_name='Escenario', value_name='Saldo')
                
                c = alt.Chart(chart_melted).mark_line().encode(
                    x='Mes',
                    y='Saldo',
                    color='Escenario'
                ).interactive()
                
                st.altair_chart(c, use_container_width=True)
                
                with st.expander("Ver Nueva Tabla de Amortización"):
                    st.dataframe(tabla_nueva)
            else:
                st.error("Error en la simulación. Verifica el mes de pago.")

    with tab2:
        st.subheader("Simulación de Pagos Mensuales Adicionales")
        col1, col2 = st.columns(2)
        with col1:
            mes_inicio = st.number_input("Empezar desde el mes:", min_value=1, max_value=plazo-1, value=1)
        with col2:
            extra_mensual = st.number_input("Monto extra mensual (S/)", min_value=50.0, value=200.0, step=50.0)
            
        if st.button("Simular Recurrente"):
            df_recurr = simular_pagos_recurrentes(monto, tea/100, plazo, extra_mensual, mes_inicio)
            
            tabla_base = generar_tabla_francesa(monto, tea/100, plazo)
            interes_orig = tabla_base['interes'].sum()
            interes_new = df_recurr['interes'].sum()
            ahorro = interes_orig - interes_new
            meses_ahorrados = len(tabla_base) - len(df_recurr)
            
            st.divider()
            c1, c2, c3 = st.columns(3)
            c1.metric("Ahorro Intereses", f"S/ {ahorro:,.2f}")
            c2.metric("Plazo Original", f"{len(tabla_base)} meses")
            c3.metric("Nuevo Plazo", f"{len(df_recurr)} meses", f"-{meses_ahorrados} meses")
            
            st.altair_chart(
                alt.Chart(df_recurr).mark_bar().encode(
                    x='mes',
                    y='saldo_final',
                    tooltip=['mes', 'saldo_final', 'interes', 'amortizacion']
                ).interactive(),
                use_container_width=True
            )

    with tab3:
        st.subheader("Comparación de Estrategias")
        st.markdown("Si tienes un presupuesto anual extra (ej. gratificación, utilidades), ¿qué conviene más?")
        
        presupuesto = st.number_input("Presupuesto Anual Extra Disponible (S/)", min_value=1000.0, value=2400.0, step=100.0)
        
        if st.button("Comparar Estrategias"):
            resultados_est = comparar_estrategias_prepago(monto, tea/100, plazo, presupuesto)
            
            mejor = resultados_est.sort_values('interes_total').iloc[0]
            st.success(f"🏆 La mejor estrategia es: **{mejor['nombre']}** con un ahorro de S/ {mejor['ahorro']:,.2f}")
            
            c = alt.Chart(resultados_est).mark_bar().encode(
                x=alt.X('nombre', sort=None, title="Estrategia"),
                y=alt.Y('interes_total', title="Intereses Totales (S/)"),
                color='nombre',
                tooltip=['nombre', 'interes_total', 'ahorro', 'plazo']
            )
            st.altair_chart(c, use_container_width=True)
            
            st.dataframe(resultados_est.style.format({
                'interes_total': "{:,.2f}",
                'ahorro': "{:,.2f}"
            }))