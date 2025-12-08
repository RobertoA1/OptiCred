# modulos/calculadora.py
"""
Función para mostrar la calculadora de créditos
"""
import streamlit as st
import plotly.graph_objects as go
from modules.amortizacion import (
    calcular_cuota_francesa, 
    generar_tabla_francesa, 
    calcular_totales
)
from modules.utilities import formatear_moneda, validar_datos_credito

def mostrar_calculadora_creditos():
    """
    Muestra la interfaz de la calculadora de créditos
    """
    st.title("💰 Calculadora de Créditos")
    st.write("Calcula tu cuota mensual y genera la tabla de amortización completa")
    
    st.divider()
    
    # ========== FORMULARIO DE ENTRADA ==========
    col1, col2, col3 = st.columns(3)
    
    with col1:
        monto = st.number_input(
            "Monto del Préstamo (S/)",
            min_value=0.0,
            value=10000.0,
            step=1000.0,
            help="Ingresa el monto total que deseas solicitar"
        )
    
    with col2:
        tea_porcentaje = st.slider(
            "Tasa Efectiva Anual (TEA) %",
            min_value=0.0,
            max_value=100.0,
            value=20.0,
            step=0.5,
            help="Tasa de interés anual efectiva"
        )
    
    with col3:
        plazo = st.number_input(
            "Plazo (meses)",
            min_value=1,
            max_value=360,
            value=12,
            step=1,
            help="Número de meses para pagar el crédito"
        )
    
    st.write("")
    
    # Botón de cálculo
    if st.button("🔍 Calcular Amortización", type="primary"):
        
        tea = tea_porcentaje / 100  # Convertir a decimal
        
        # Validar datos
        es_valido, errores = validar_datos_credito(monto, tea, plazo)
        
        if not es_valido:
            st.error("**Errores en los datos ingresados:**")
            for error in errores:
                st.write(error)
        else:
            # Calcular cuota
            cuota = calcular_cuota_francesa(monto, tea, plazo)
            
            # Generar tabla de amortización
            tabla = generar_tabla_francesa(monto, tea, plazo)
            totales = calcular_totales(tabla)
            
            st.divider()
            
            # Mostrar métricas principales
            st.subheader("📈 Resumen del Crédito")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Cuota Mensual", formatear_moneda(cuota))
            with col2:
                st.metric("Total Intereses", formatear_moneda(totales['total_intereses']))
            with col3:
                st.metric("Total a Pagar", formatear_moneda(totales['total_pagado']))
            with col4:
                porcentaje_interes = (totales['total_intereses'] / totales['total_pagado']) * 100
                st.metric("% Interés", f"{porcentaje_interes:.1f}%")
            
            st.divider()
            
            # Tabs para organizar información
            tab1, tab2, tab3 = st.tabs(["📋 Tabla de Amortización", "📊 Gráficos", "💾 Descargar"])
            
            with tab1:
                st.subheader("Tabla de Amortización Completa")
                # Formatear la tabla para mostrar
                tabla_mostrar = tabla.copy()
                tabla_mostrar['saldo_inicial'] = tabla_mostrar['saldo_inicial'].apply(formatear_moneda)
                tabla_mostrar['interes'] = tabla_mostrar['interes'].apply(formatear_moneda)
                tabla_mostrar['amortizacion'] = tabla_mostrar['amortizacion'].apply(formatear_moneda)
                tabla_mostrar['cuota'] = tabla_mostrar['cuota'].apply(formatear_moneda)
                tabla_mostrar['saldo_final'] = tabla_mostrar['saldo_final'].apply(formatear_moneda)
                
                st.dataframe(tabla_mostrar, use_container_width=True, height=400)
            
            with tab2:
                st.subheader("Visualización de la Amortización")
                
                # Gráfico 1: Evolución del saldo
                fig1 = go.Figure()
                fig1.add_trace(go.Scatter(
                    x=tabla['mes'],
                    y=tabla['saldo_final'],
                    mode='lines+markers',
                    name='Saldo',
                    line=dict(color='#FF6B6B', width=3),
                    fill='tozeroy'
                ))
                fig1.update_layout(
                    title='Evolución del Saldo de la Deuda',
                    xaxis_title='Mes',
                    yaxis_title='Saldo (S/)',
                    hovermode='x unified'
                )
                st.plotly_chart(fig1, use_container_width=True)
                
                # Gráfico 2: Composición de pagos
                fig2 = go.Figure()
                fig2.add_trace(go.Bar(
                    x=tabla['mes'],
                    y=tabla['interes'],
                    name='Interés',
                    marker_color='#FF6B6B'
                ))
                fig2.add_trace(go.Bar(
                    x=tabla['mes'],
                    y=tabla['amortizacion'],
                    name='Amortización',
                    marker_color='#4ECDC4'
                ))
                fig2.update_layout(
                    title='Composición de la Cuota: Interés vs Amortización',
                    xaxis_title='Mes',
                    yaxis_title='Monto (S/)',
                    barmode='stack',
                    hovermode='x unified'
                )
                st.plotly_chart(fig2, use_container_width=True)
            
            with tab3:
                st.subheader("Descargar Tabla de Amortización")
                
                # Convertir a CSV
                csv = tabla.to_csv(index=False).encode('utf-8')
                
                st.download_button(
                    label="📥 Descargar como CSV",
                    data=csv,
                    file_name=f"amortizacion_{monto}_{plazo}meses.csv",
                    mime="text/csv",
                    use_container_width=True
                )
                
                st.info("💡 Tip: Puedes abrir el archivo CSV en Excel para realizar análisis adicionales")
    
    else:
        st.info("👆 Completa los datos del crédito y haz clic en **Calcular Amortización**")