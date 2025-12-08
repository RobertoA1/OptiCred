# modules/comparador.py
"""
Función para mostrar el comparador de créditos con integración a API SBS
"""
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from modules.amortizacion import (
    calcular_cuota_francesa, 
    calcular_cuota_alemana,
    calcular_totales, 
    generar_tabla_francesa,
    generar_tabla_alemana
)
from modules.utilities import formatear_moneda
from modules.interes import calcular_tcea_completa

# Importar API de tasas (cuando el Integrante 1 la tenga lista)
try:
    from modules.api_tasas import APITasas
    API_DISPONIBLE = True
except ImportError:
    API_DISPONIBLE = False

def mostrar_comparador_creditos():
    """
    Muestra la interfaz del comparador de créditos con datos reales de SBS
    """
    st.title("📊 Comparador de Créditos")
    st.write("Compara múltiples opciones de financiamiento y elige la mejor")
    
    st.divider()
    
    # ========== PASO 1: SELECCIONAR SISTEMA DE AMORTIZACIÓN ==========
    st.subheader("🔧 Configuración General")
    
    col_config1, col_config2 = st.columns(2)
    
    with col_config1:
        sistema_amortizacion = st.selectbox(
            "📐 Sistema de Amortización",
            ["Francés (Cuota Fija)", "Alemán (Amortización Fija)"],
            help="Francés: cuota mensual constante | Alemán: cuota mensual decreciente"
        )
    
    with col_config2:
        # Inicializar API si está disponible
        if API_DISPONIBLE:
            api_tasas = APITasas()
            tipo_credito = st.selectbox(
                "🏦 Tipo de Crédito",
                ["Consumo", "Hipotecario", "Vehicular", "Microempresa", "Pequeña Empresa"],
                help="Selecciona el tipo de crédito para cargar las tasas reales de bancos"
            )
            
            try:
                bancos_disponibles = api_tasas.get_bancos(tipo_credito)
            except:
                bancos_disponibles = ["BCP", "Interbank", "BBVA", "Scotiabank", "Banco Pichincha"]
        else:
            tipo_credito = st.selectbox(
                "🏦 Tipo de Crédito",
                ["Consumo", "Hipotecario", "Vehicular", "Microempresa", "Pequeña Empresa"]
            )
            bancos_disponibles = ["BCP", "Interbank", "BBVA", "Scotiabank", "Banco Pichincha"]
    
    # Mostrar información del sistema seleccionado
    if sistema_amortizacion == "Francés (Cuota Fija)":
        st.info("ℹ️ **Sistema Francés:** La cuota mensual es constante. Al inicio pagas más intereses y menos capital. Al final es al revés.")
        sistema = "frances"
    else:
        st.info("ℹ️ **Sistema Alemán:** La amortización del capital es constante. La cuota mensual disminuye mes a mes porque los intereses bajan.")
        sistema = "aleman"
    
    st.divider()
    
    # ========== PASO 2: NÚMERO DE CRÉDITOS A COMPARAR ==========
    num_creditos = st.slider(
        "¿Cuántos créditos quieres comparar?", 
        2, 5, 2,
        help="Selecciona entre 2 y 5 opciones de crédito para comparar"
    )
    
    st.divider()
    
    # ========== PASO 3: FORMULARIOS DE CADA CRÉDITO ==========
    st.subheader("💳 Datos de los Créditos")
    
    # Almacenar datos de cada crédito
    creditos = []
    
    # Crear columnas según el número de créditos
    cols = st.columns(num_creditos)
    
    for i, col in enumerate(cols):
        with col:
            st.markdown(f"### Crédito {chr(65 + i)}")  # A, B, C, D, E
            
            # Selector de banco
            banco = st.selectbox(
                "Banco",
                bancos_disponibles,
                key=f"banco_{i}",
                help="Selecciona la entidad financiera"
            )
            
            # Obtener TEA sugerida según banco (si API disponible)
            if API_DISPONIBLE:
                try:
                    tea_sugerida = api_tasas.get_tea(banco, tipo_credito)
                except:
                    tea_sugerida = 20.0 + (i * 2)
            else:
                tea_sugerida = 20.0 + (i * 2)
            
            st.markdown("**Datos Principales:**")
            
            # Campos principales
            monto = st.number_input(
                "Monto (S/)",
                min_value=0.0,
                value=10000.0,
                step=1000.0,
                key=f"monto_{i}",
                help="Monto total del préstamo solicitado"
            )
            
            plazo = st.number_input(
                "Plazo (meses)",
                min_value=1,
                max_value=360,
                value=12,
                step=1,
                key=f"plazo_{i}",
                help="Cantidad de meses para pagar el crédito"
            )
            
            tea = st.slider(
                "TEA %",
                min_value=0.0,
                max_value=100.0,
                value=tea_sugerida,
                step=0.1,
                key=f"tea_{i}",
                help=f"Tasa sugerida para {banco}: {tea_sugerida}%"
            )
            
            # Mostrar si la tasa está por encima o debajo del promedio
            if API_DISPONIBLE:
                try:
                    promedio = api_tasas.get_promedio(tipo_credito)
                    if tea < promedio:
                        st.success(f"✅ Tasa {(promedio - tea):.2f}% por debajo del promedio")
                    else:
                        st.warning(f"⚠️ Tasa {(tea - promedio):.2f}% por encima del promedio")
                except:
                    pass
            
            st.markdown("---")
            st.markdown("**💰 Costos Adicionales:**")
            
            # Comisiones y costos
            with st.expander("Ver costos detallados"):
                comision_desembolso = st.number_input(
                    "Comisión de desembolso (%)",
                    min_value=0.0,
                    max_value=10.0,
                    value=0.0,
                    step=0.1,
                    key=f"com_desemb_{i}",
                    help="Porcentaje del monto que cobra el banco al desembolsar"
                )
                
                comision_mensual = st.number_input(
                    "Comisión mensual (S/)",
                    min_value=0.0,
                    value=0.0,
                    step=5.0,
                    key=f"com_mens_{i}",
                    help="Comisión fija que se paga cada mes"
                )
                
                seguro_desgravamen = st.number_input(
                    "Seguro de desgravamen (% mensual)",
                    min_value=0.0,
                    max_value=1.0,
                    value=0.0,
                    step=0.01,
                    key=f"seguro_{i}",
                    help="Porcentaje sobre saldo que se paga mensualmente"
                )
                
                portes = st.number_input(
                    "Portes y gastos (S/)",
                    min_value=0.0,
                    value=0.0,
                    step=5.0,
                    key=f"portes_{i}",
                    help="Otros gastos mensuales (envío de estados de cuenta, etc.)"
                )
            
            creditos.append({
                'banco': banco,
                'monto': monto,
                'tea': tea / 100,
                'plazo': plazo,
                'comision_desembolso': comision_desembolso / 100,
                'comision_mensual': comision_mensual,
                'seguro_desgravamen': seguro_desgravamen / 100,
                'portes': portes
            })
    
    st.divider()
    
    # ========== BOTÓN DE COMPARACIÓN ==========
    if st.button("🔍 Comparar Créditos", type="primary", use_container_width=True):
        
        with st.spinner("Calculando y comparando créditos..."):
            # Calcular datos para cada crédito
            resultados = []
            
            for i, credito in enumerate(creditos):
                
                # ===== CALCULAR SEGÚN SISTEMA DE AMORTIZACIÓN =====
                if sistema == "frances":
                    cuota_base = calcular_cuota_francesa(credito['monto'], credito['tea'], credito['plazo'])
                    tabla = generar_tabla_francesa(credito['monto'], credito['tea'], credito['plazo'])
                else:  # aleman
                    # Para el alemán, la primera cuota es la más alta
                    tabla = generar_tabla_alemana(credito['monto'], credito['tea'], credito['plazo'])
                    cuota_base = tabla.loc[0, 'cuota']  # Primera cuota (la más alta)
                
                totales = calcular_totales(tabla)
                
                # Calcular costos adicionales
                monto_comision_desembolso = credito['monto'] * credito['comision_desembolso']
                
                # Costos mensuales adicionales
                costo_mensual_adicional = credito['comision_mensual'] + credito['portes']
                
                # Calcular seguro de desgravamen sobre saldo promedio (simplificado)
                saldo_promedio = credito['monto'] / 2
                seguro_total = saldo_promedio * credito['seguro_desgravamen'] * credito['plazo']
                
                # Cuota total (aproximada para el primer mes)
                if sistema == "frances":
                    cuota_total_inicial = cuota_base + costo_mensual_adicional + (seguro_total / credito['plazo'])
                else:  # aleman
                    # En alemán, mostrar rango de cuotas
                    cuota_primera = tabla.loc[0, 'cuota']
                    cuota_ultima = tabla.loc[credito['plazo']-1, 'cuota']
                    cuota_total_inicial = cuota_primera + costo_mensual_adicional + (seguro_total / credito['plazo'])
                    cuota_total_final = cuota_ultima + costo_mensual_adicional + (seguro_total / credito['plazo'])
                
                # Costo total del crédito
                costo_total = (
                    totales['total_pagado'] + 
                    monto_comision_desembolso + 
                    (costo_mensual_adicional * credito['plazo']) + 
                    seguro_total
                )
                
                # Calcular TCEA
                try:
                    tcea = calcular_tcea_completa(
                        credito['monto'],
                        credito['tea'],
                        credito['plazo'],
                        credito['comision_desembolso'],
                        credito['comision_mensual'],
                        credito['seguro_desgravamen'],
                        credito['portes']
                    )
                except Exception as e:
                    tcea = None
                
                # Agregar resultados
                resultado = {
                    'Crédito': credito['banco'],
                    'Sistema': sistema_amortizacion,
                    'TEA (%)': credito['tea'] * 100,
                    'TCEA (%)': tcea if tcea else "N/A",
                    'Total Intereses': totales['total_intereses'],
                    'Costos Adicionales': monto_comision_desembolso + (costo_mensual_adicional * credito['plazo']) + seguro_total,
                    'Costo Total': costo_total
                }
                
                # Agregar cuotas según sistema
                if sistema == "frances":
                    resultado['Cuota Mensual'] = cuota_total_inicial
                else:  # aleman
                    resultado['Primera Cuota'] = cuota_total_inicial
                    resultado['Última Cuota'] = cuota_total_final
                
                resultados.append(resultado)
            
            df_resultados = pd.DataFrame(resultados)
            
            # ========== TABLA COMPARATIVA ==========
            st.subheader("📋 Tabla Comparativa Detallada")
            
            # Formatear para mostrar
            df_mostrar = df_resultados.copy()
            df_mostrar['TEA (%)'] = df_mostrar['TEA (%)'].apply(lambda x: f"{x:.2f}%")
            if df_mostrar['TCEA (%)'].iloc[0] != "N/A":
                df_mostrar['TCEA (%)'] = df_mostrar['TCEA (%)'].apply(lambda x: f"{x:.2f}%" if isinstance(x, (int, float)) else x)
            
            if sistema == "frances":
                df_mostrar['Cuota Mensual'] = df_mostrar['Cuota Mensual'].apply(formatear_moneda)
            else:
                df_mostrar['Primera Cuota'] = df_mostrar['Primera Cuota'].apply(formatear_moneda)
                df_mostrar['Última Cuota'] = df_mostrar['Última Cuota'].apply(formatear_moneda)
            
            df_mostrar['Total Intereses'] = df_mostrar['Total Intereses'].apply(formatear_moneda)
            df_mostrar['Costos Adicionales'] = df_mostrar['Costos Adicionales'].apply(formatear_moneda)
            df_mostrar['Costo Total'] = df_mostrar['Costo Total'].apply(formatear_moneda)
            
            st.dataframe(df_mostrar, use_container_width=True)
            
            st.divider()
            
            # ========== MÉTRICAS DESTACADAS ==========
            st.subheader("🎯 Métricas Clave")
            
            if sistema == "frances":
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    idx_mejor_cuota = df_resultados['Cuota Mensual'].idxmin()
                    st.metric(
                        "Menor Cuota",
                        formatear_moneda(df_resultados.loc[idx_mejor_cuota, 'Cuota Mensual']),
                        df_resultados.loc[idx_mejor_cuota, 'Crédito']
                    )
            else:  # aleman
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    idx_mejor_cuota = df_resultados['Primera Cuota'].idxmin()
                    st.metric(
                        "Menor Primera Cuota",
                        formatear_moneda(df_resultados.loc[idx_mejor_cuota, 'Primera Cuota']),
                        df_resultados.loc[idx_mejor_cuota, 'Crédito']
                    )
            
            with col2:
                idx_mejor_costo = df_resultados['Costo Total'].idxmin()
                st.metric(
                    "Menor Costo Total",
                    formatear_moneda(df_resultados.loc[idx_mejor_costo, 'Costo Total']),
                    df_resultados.loc[idx_mejor_costo, 'Crédito']
                )
            
            with col3:
                idx_menos_interes = df_resultados['Total Intereses'].idxmin()
                st.metric(
                    "Menos Intereses",
                    formatear_moneda(df_resultados.loc[idx_menos_interes, 'Total Intereses']),
                    df_resultados.loc[idx_menos_interes, 'Crédito']
                )
            
            with col4:
                if df_resultados['TCEA (%)'].iloc[0] != "N/A":
                    idx_mejor_tcea = df_resultados['TCEA (%)'].idxmin()
                    st.metric(
                        "Menor TCEA",
                        f"{df_resultados.loc[idx_mejor_tcea, 'TCEA (%)']:.2f}%",
                        df_resultados.loc[idx_mejor_tcea, 'Crédito']
                    )
            
            st.divider()
            
            # ========== GRÁFICOS COMPARATIVOS ==========
            st.subheader("📊 Comparación Visual")
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Gráfico de cuotas
                fig1 = go.Figure()
                
                if sistema == "frances":
                    fig1.add_trace(go.Bar(
                        x=df_resultados['Crédito'],
                        y=df_resultados['Cuota Mensual'],
                        marker_color='#667eea',
                        text=df_resultados['Cuota Mensual'].apply(lambda x: f"S/ {x:,.2f}"),
                        textposition='auto',
                        name='Cuota'
                    ))
                    titulo_cuota = 'Cuota Mensual por Crédito'
                else:
                    fig1.add_trace(go.Bar(
                        x=df_resultados['Crédito'],
                        y=df_resultados['Primera Cuota'],
                        marker_color='#667eea',
                        text=df_resultados['Primera Cuota'].apply(lambda x: f"S/ {x:,.2f}"),
                        textposition='auto',
                        name='Primera Cuota'
                    ))
                    fig1.add_trace(go.Bar(
                        x=df_resultados['Crédito'],
                        y=df_resultados['Última Cuota'],
                        marker_color='#95a5f6',
                        text=df_resultados['Última Cuota'].apply(lambda x: f"S/ {x:,.2f}"),
                        textposition='auto',
                        name='Última Cuota'
                    ))
                    titulo_cuota = 'Primera vs Última Cuota por Crédito'
                
                fig1.update_layout(
                    title=titulo_cuota,
                    xaxis_title='Crédito',
                    yaxis_title='Cuota (S/)',
                    showlegend=(sistema == "aleman")
                )
                st.plotly_chart(fig1, use_container_width=True)
            
            with col2:
                # Gráfico de costo total
                fig2 = go.Figure()
                fig2.add_trace(go.Bar(
                    x=df_resultados['Crédito'],
                    y=df_resultados['Costo Total'],
                    marker_color='#f5576c',
                    text=df_resultados['Costo Total'].apply(lambda x: f"S/ {x:,.2f}"),
                    textposition='auto',
                    name='Costo Total'
                ))
                fig2.update_layout(
                    title='Costo Total del Crédito',
                    xaxis_title='Crédito',
                    yaxis_title='Costo Total (S/)',
                    showlegend=False
                )
                st.plotly_chart(fig2, use_container_width=True)
            
            # Gráfico de barras apiladas - Desglose de costos
            fig3 = go.Figure()
            fig3.add_trace(go.Bar(
                name='Intereses',
                x=df_resultados['Crédito'],
                y=df_resultados['Total Intereses'],
                marker_color='#FF6B6B'
            ))
            fig3.add_trace(go.Bar(
                name='Costos Adicionales',
                x=df_resultados['Crédito'],
                y=df_resultados['Costos Adicionales'],
                marker_color='#FFA500'
            ))
            fig3.update_layout(
                title='Desglose de Costos por Crédito',
                xaxis_title='Crédito',
                yaxis_title='Monto (S/)',
                barmode='stack'
            )
            st.plotly_chart(fig3, use_container_width=True)
            
            st.divider()
            
            # ========== RECOMENDACIÓN FINAL ==========
            st.subheader("🎯 Recomendación Final")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if sistema == "frances":
                    st.success(f"""
                    **💰 Mejor para pago mensual:**
                    
                    {df_resultados.loc[idx_mejor_cuota, 'Crédito']}
                    
                    Cuota: {formatear_moneda(df_resultados.loc[idx_mejor_cuota, 'Cuota Mensual'])}
                    """)
                else:
                    st.success(f"""
                    **💰 Menor cuota inicial:**
                    
                    {df_resultados.loc[idx_mejor_cuota, 'Crédito']}
                    
                    Primera cuota: {formatear_moneda(df_resultados.loc[idx_mejor_cuota, 'Primera Cuota'])}
                    """)
            
            with col2:
                st.success(f"""
                **💵 Mejor costo total:**
                
                {df_resultados.loc[idx_mejor_costo, 'Crédito']}
                
                Total: {formatear_moneda(df_resultados.loc[idx_mejor_costo, 'Costo Total'])}
                """)
            
            with col3:
                st.success(f"""
                **📉 Menos intereses:**
                
                {df_resultados.loc[idx_menos_interes, 'Crédito']}
                
                Intereses: {formatear_moneda(df_resultados.loc[idx_menos_interes, 'Total Intereses'])}
                """)
            
            # ========== EXPORTACIÓN ==========
            st.divider()
            st.subheader("💾 Exportar Resultados")
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Exportar a CSV
                csv = df_resultados.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Descargar como CSV",
                    data=csv,
                    file_name=f"comparacion_creditos_{tipo_credito.lower()}_{sistema}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            
            with col2:
                st.info("📊 Exportación a Excel y PDF próximamente")