# modulos/comparador.py
"""
Función para mostrar el comparador de créditos
"""
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from modules.amortizacion import calcular_cuota_francesa, calcular_totales, generar_tabla_francesa
from modules.utilities import formatear_moneda

def mostrar_comparador_creditos():
    """
    Muestra la interfaz del comparador de créditos
    """
    st.title("📊 Comparador de Créditos")
    st.write("Compara múltiples opciones de financiamiento y elige la mejor")
    
    st.divider()
    
    # Número de créditos a comparar
    num_creditos = st.slider("¿Cuántos créditos quieres comparar?", 2, 5, 2)
    
    st.divider()
    
    # Almacenar datos de cada crédito
    creditos = []
    
    # Crear columnas según el número de créditos
    cols = st.columns(num_creditos)
    
    for i, col in enumerate(cols):
        with col:
            st.subheader(f"Crédito {chr(65 + i)}")  # A, B, C, D, E
            
            nombre = st.text_input(
                "Nombre del Crédito",
                value=f"Banco {chr(65 + i)}",
                key=f"nombre_{i}"
            )
            
            monto = st.number_input(
                "Monto (S/)",
                min_value=0.0,
                value=10000.0,
                step=1000.0,
                key=f"monto_{i}"
            )
            
            tea = st.slider(
                "TEA %",
                min_value=0.0,
                max_value=100.0,
                value=20.0 + (i * 2),  # Variar un poco por defecto
                step=0.5,
                key=f"tea_{i}"
            )
            
            plazo = st.number_input(
                "Plazo (meses)",
                min_value=1,
                max_value=360,
                value=12,
                key=f"plazo_{i}"
            )
            
            comision = st.number_input(
                "Comisión inicial (S/)",
                min_value=0.0,
                value=0.0,
                step=50.0,
                key=f"comision_{i}"
            )
            
            creditos.append({
                'nombre': nombre,
                'monto': monto,
                'tea': tea / 100,
                'plazo': plazo,
                'comision': comision
            })
    
    st.divider()
    
    if st.button("🔍 Comparar Créditos", type="primary", use_container_width=False):
        
        # Calcular datos para cada crédito
        resultados = []
        
        for credito in creditos:
            cuota = calcular_cuota_francesa(credito['monto'], credito['tea'], credito['plazo'])
            tabla = generar_tabla_francesa(credito['monto'], credito['tea'], credito['plazo'])
            totales = calcular_totales(tabla)
            
            resultados.append({
                'Crédito': credito['nombre'],
                'Cuota Mensual': cuota,
                'Total Intereses': totales['total_intereses'],
                'Total Pagado': totales['total_pagado'],
                'Comisión': credito['comision'],
                'Costo Total': totales['total_pagado'] + credito['comision']
            })
        
        df_resultados = pd.DataFrame(resultados)
        
        # ========== TABLA COMPARATIVA ==========
        st.subheader("📋 Tabla Comparativa")
        
        # Formatear para mostrar
        df_mostrar = df_resultados.copy()
        df_mostrar['Cuota Mensual'] = df_mostrar['Cuota Mensual'].apply(formatear_moneda)
        df_mostrar['Total Intereses'] = df_mostrar['Total Intereses'].apply(formatear_moneda)
        df_mostrar['Total Pagado'] = df_mostrar['Total Pagado'].apply(formatear_moneda)
        df_mostrar['Comisión'] = df_mostrar['Comisión'].apply(formatear_moneda)
        df_mostrar['Costo Total'] = df_mostrar['Costo Total'].apply(formatear_moneda)
        
        st.dataframe(df_mostrar, use_container_width=True)
        
        st.divider()
        
        # ========== GRÁFICOS COMPARATIVOS ==========
        st.subheader("📊 Comparación Visual")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Gráfico de barras - Cuota mensual
            fig1 = go.Figure()
            fig1.add_trace(go.Bar(
                x=df_resultados['Crédito'],
                y=df_resultados['Cuota Mensual'],
                marker_color='#667eea',
                text=df_resultados['Cuota Mensual'].apply(lambda x: f"S/ {x:,.2f}"),
                textposition='auto'
            ))
            fig1.update_layout(
                title='Cuota Mensual por Crédito',
                xaxis_title='Crédito',
                yaxis_title='Cuota (S/)',
                showlegend=False
            )
            st.plotly_chart(fig1, use_container_width=True)
        
        with col2:
            # Gráfico de barras - Costo total
            fig2 = go.Figure()
            fig2.add_trace(go.Bar(
                x=df_resultados['Crédito'],
                y=df_resultados['Costo Total'],
                marker_color='#f5576c',
                text=df_resultados['Costo Total'].apply(lambda x: f"S/ {x:,.2f}"),
                textposition='auto'
            ))
            fig2.update_layout(
                title='Costo Total por Crédito',
                xaxis_title='Crédito',
                yaxis_title='Costo Total (S/)',
                showlegend=False
            )
            st.plotly_chart(fig2, use_container_width=True)
        
        # Gráfico de pastel - Distribución de intereses
        fig3 = go.Figure()
        fig3.add_trace(go.Pie(
            labels=df_resultados['Crédito'],
            values=df_resultados['Total Intereses'],
            hole=0.3
        ))
        fig3.update_layout(title='Distribución de Intereses Totales')
        st.plotly_chart(fig3, use_container_width=True)
        
        st.divider()
        
        # ========== RECOMENDACIÓN ==========
        st.subheader("🎯 Recomendación")
        
        # Encontrar el mejor crédito
        idx_mejor_cuota = df_resultados['Cuota Mensual'].idxmin()
        idx_mejor_costo = df_resultados['Costo Total'].idxmin()
        idx_menos_interes = df_resultados['Total Intereses'].idxmin()
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.success(f"**Menor Cuota Mensual:**\n\n{df_resultados.loc[idx_mejor_cuota, 'Crédito']}\n\n{formatear_moneda(df_resultados.loc[idx_mejor_cuota, 'Cuota Mensual'])}")
        
        with col2:
            st.success(f"**Menor Costo Total:**\n\n{df_resultados.loc[idx_mejor_costo, 'Crédito']}\n\n{formatear_moneda(df_resultados.loc[idx_mejor_costo, 'Costo Total'])}")
        
        with col3:
            st.success(f"**Menos Intereses:**\n\n{df_resultados.loc[idx_menos_interes, 'Crédito']}\n\n{formatear_moneda(df_resultados.loc[idx_menos_interes, 'Total Intereses'])}")