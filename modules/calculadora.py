# modules/calculadora.py
"""
Calculadora de Créditos con integración a API SBS
Interfaz moderna e intuitiva para cálculo de préstamos
"""
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from datetime import datetime, timedelta
from modules.amortizacion import (
    calcular_cuota_francesa, 
    calcular_cuota_alemana,
    generar_tabla_francesa, 
    generar_tabla_alemana,
    calcular_totales
)
from modules.utilities import formatear_moneda, validar_datos_credito
from modules.interes import calcular_tcea_completa

# Importar API de tasas
try:
    from modules.api_tasas import (
        APITasas,
        cargar_datos_api,
        CATEGORIAS_CREDITO
    )
    API_DISPONIBLE = True
except ImportError:
    API_DISPONIBLE = False
    # Definir CATEGORIAS_CREDITO local si no está disponible
    CATEGORIAS_CREDITO = {
        "Consumo": {
            "descripcion": "Créditos para personas naturales",
            "opciones": {"Libre Disponibilidad (más de 360 días)": "Préstamos no Revolventes"}
        },
        "Hipotecarios": {
            "descripcion": "Créditos para vivienda",
            "opciones": {"Préstamos para Vivienda": "Préstamos hipotecarios"}
        }
    }


def generar_pdf_calculadora(monto, tea_porcentaje, plazo, sistema, cuota_base, 
                            totales, costos_adicionales, costo_total_credito, 
                            tcea, banco, categoria, producto, tabla):
    """
    Genera un PDF profesional con el resumen de la simulación de crédito.
    """
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import inch, cm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    from io import BytesIO
    
    pdf_buffer = BytesIO()
    doc = SimpleDocTemplate(
        pdf_buffer,
        pagesize=A4,
        rightMargin=1.5*cm,
        leftMargin=1.5*cm,
        topMargin=1.5*cm,
        bottomMargin=1.5*cm
    )
    
    elements = []
    styles = getSampleStyleSheet()
    
    # Estilos personalizados
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#667EEA'),
        spaceAfter=10,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    subtitle_style = ParagraphStyle(
        'Subtitle',
        parent=styles['Normal'],
        fontSize=12,
        textColor=colors.HexColor('#666666'),
        alignment=TA_CENTER,
        spaceAfter=20
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#333333'),
        spaceBefore=15,
        spaceAfter=10,
        fontName='Helvetica-Bold'
    )
    
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#333333'),
        spaceAfter=6
    )
    
    highlight_style = ParagraphStyle(
        'Highlight',
        parent=styles['Normal'],
        fontSize=28,
        textColor=colors.HexColor('#667EEA'),
        alignment=TA_CENTER,
        fontName='Helvetica-Bold',
        spaceBefore=10,
        spaceAfter=10
    )
    
    # ===== TÍTULO =====
    elements.append(Paragraph("SIMULACIÓN DE CRÉDITO", title_style))
    elements.append(Paragraph("OptiCred - Sistema Inteligente de Créditos", subtitle_style))
    elements.append(Spacer(1, 0.3*inch))
    
    # ===== CUOTA DESTACADA =====
    if sistema == "Francés":
        cuota_texto = f"S/ {cuota_base:,.2f}"
        cuota_subtexto = f"Cuota mensual fija durante {plazo} meses"
    else:
        cuota_texto = f"S/ {cuota_base:,.2f}"
        cuota_ultima = tabla.iloc[-1]['cuota']
        cuota_subtexto = f"Primera cuota (decrece hasta S/ {cuota_ultima:,.2f})"
    
    elements.append(Paragraph("Tu cuota mensual:", normal_style))
    elements.append(Paragraph(cuota_texto, highlight_style))
    elements.append(Paragraph(cuota_subtexto, subtitle_style))
    
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#E0E0E0')))
    elements.append(Spacer(1, 0.2*inch))
    
    # ===== DATOS DEL PRÉSTAMO =====
    elements.append(Paragraph("📋 Datos del Préstamo", heading_style))
    
    datos_prestamo = [
        ['Concepto', 'Valor'],
        ['Monto solicitado', f"S/ {monto:,.2f}"],
        ['Plazo', f"{plazo} meses"],
        ['TEA', f"{tea_porcentaje:.2f}%"],
        ['TCEA', f"{tcea:.2f}%" if tcea else "N/A"],
        ['Sistema de amortización', sistema],
        ['Tipo de crédito', f"{categoria} - {producto}"],
    ]
    
    if banco:
        datos_prestamo.append(['Banco', banco])
    
    tabla_datos = Table(datos_prestamo, colWidths=[7*cm, 10*cm])
    tabla_datos.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#667EEA')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('TOPPADDING', (0, 0), (-1, 0), 10),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F8F9FA')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E0E0E0')),
        ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
        ('TOPPADDING', (0, 1), (-1, -1), 8),
    ]))
    elements.append(tabla_datos)
    elements.append(Spacer(1, 0.3*inch))
    
    # ===== RESUMEN FINANCIERO =====
    elements.append(Paragraph("💰 Resumen Financiero", heading_style))
    
    resumen_financiero = [
        ['Concepto', 'Monto'],
        ['Capital (monto solicitado)', f"S/ {monto:,.2f}"],
        ['Total intereses', f"S/ {totales['total_intereses']:,.2f}"],
        ['Costos adicionales', f"S/ {costos_adicionales:,.2f}"],
        ['COSTO TOTAL DEL CRÉDITO', f"S/ {costo_total_credito:,.2f}"],
    ]
    
    tabla_resumen = Table(resumen_financiero, colWidths=[10*cm, 7*cm])
    tabla_resumen.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#48BB78')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BACKGROUND', (0, 1), (-1, -2), colors.HexColor('#F0FFF4')),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#C6F6D5')),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#9AE6B4')),
    ]))
    elements.append(tabla_resumen)
    elements.append(Spacer(1, 0.3*inch))
    
    # ===== TABLA DE AMORTIZACIÓN (primeras 12 filas) =====
    elements.append(Paragraph("📅 Tabla de Amortización (primeros 12 meses)", heading_style))
    
    # Preparar datos de la tabla
    filas_mostrar = min(12, len(tabla))
    tabla_amort_data = [['Mes', 'Saldo Inicial', 'Interés', 'Amortización', 'Cuota', 'Saldo Final']]
    
    for i in range(filas_mostrar):
        fila = tabla.iloc[i]
        tabla_amort_data.append([
            str(int(fila['mes'])),
            f"S/ {fila['saldo_inicial']:,.2f}",
            f"S/ {fila['interes']:,.2f}",
            f"S/ {fila['amortizacion']:,.2f}",
            f"S/ {fila['cuota']:,.2f}",
            f"S/ {fila['saldo_final']:,.2f}"
        ])
    
    # Agregar fila de totales si hay más filas
    if len(tabla) > 12:
        tabla_amort_data.append([
            '...',
            f'(+{len(tabla) - 12} filas)',
            '',
            '',
            '',
            ''
        ])
    
    tabla_amort = Table(tabla_amort_data, colWidths=[1.2*cm, 2.8*cm, 2.5*cm, 2.8*cm, 2.5*cm, 2.8*cm])
    tabla_amort.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4A5568')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E0')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F7FAFC')]),
    ]))
    elements.append(tabla_amort)
    elements.append(Spacer(1, 0.3*inch))
    
    # ===== NOTAS =====
    nota_style = ParagraphStyle(
        'Nota',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.HexColor('#666666'),
        spaceAfter=5
    )
    
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#E0E0E0')))
    elements.append(Spacer(1, 0.1*inch))
    
    elements.append(Paragraph(
        "<b>Nota importante:</b> Esta simulación es referencial. Los montos finales pueden variar "
        "según las condiciones específicas de cada entidad financiera. Se recomienda verificar "
        "las tasas, comisiones y condiciones directamente con el banco antes de contratar.",
        nota_style
    ))
    
    elements.append(Paragraph(
        f"<i>Documento generado por OptiCred el {datetime.now().strftime('%d/%m/%Y a las %H:%M')}</i>",
        nota_style
    ))
    
    # Construir PDF
    doc.build(elements)
    pdf_buffer.seek(0)
    
    return pdf_buffer


def mostrar_calculadora_creditos():
    """
    Muestra la interfaz de la calculadora de créditos con datos reales de SBS
    """
    
    # ========== HEADER CON ESTILO ==========
    st.markdown("""
    <style>
    .calculator-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 16px;
        margin-bottom: 2rem;
        color: white;
        text-align: center;
    }
    .calculator-header h1 {
        margin: 0;
        font-size: 2.5rem;
        font-weight: 700;
    }
    .calculator-header p {
        margin: 0.5rem 0 0 0;
        opacity: 0.9;
        font-size: 1.1rem;
    }
    .metric-card {
        background: linear-gradient(145deg, #ffffff 0%, #f8f9fa 100%);
        border-radius: 12px;
        padding: 1.5rem;
        box-shadow: 0 4px 15px rgba(0,0,0,0.08);
        border-left: 4px solid #667eea;
        margin-bottom: 1rem;
    }
    .metric-card-success {
        border-left-color: #48bb78;
    }
    .metric-card-warning {
        border-left-color: #ed8936;
    }
    .metric-card-danger {
        border-left-color: #f56565;
    }
    .bank-chip {
        display: inline-block;
        background: #667eea;
        color: white;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.85rem;
        margin-right: 0.5rem;
        margin-bottom: 0.5rem;
    }
    .rate-indicator {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.75rem 1rem;
        border-radius: 8px;
        margin: 0.5rem 0;
    }
    .rate-good {
        background: #c6f6d5;
        color: #22543d;
    }
    .rate-average {
        background: #feebc8;
        color: #744210;
    }
    .rate-high {
        background: #fed7d7;
        color: #742a2a;
    }
    .info-box {
        background: linear-gradient(135deg, #e0e7ff 0%, #c7d2fe 100%);
        border-radius: 12px;
        padding: 1rem 1.5rem;
        margin: 1rem 0;
        border-left: 4px solid #667eea;
    }
    .timeline-item {
        display: flex;
        align-items: flex-start;
        margin-bottom: 1rem;
        padding-left: 2rem;
        position: relative;
    }
    .timeline-item::before {
        content: '';
        position: absolute;
        left: 0;
        top: 0.5rem;
        width: 12px;
        height: 12px;
        border-radius: 50%;
        background: #667eea;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div class="calculator-header">
        <h1>🧮 Calculadora de Créditos</h1>
        <p>Simula tu préstamo con tasas reales del mercado peruano</p>
    </div>
    """, unsafe_allow_html=True)
    
    # ========== CARGAR DATOS DE LA API ==========
    api_conectada = False
    api_tasas = None
    
    if API_DISPONIBLE:
        with st.spinner("🔄 Conectando con tasas actualizadas de la SBS..."):
            df_tasas, df_bancos, api_conectada = cargar_datos_api()
            
            if api_conectada:
                api_tasas = APITasas()
                api_tasas._tasas_activas = df_tasas
                api_tasas._bancos = df_bancos
                api_tasas._cache_cargado = True
                api_tasas._construir_indice_categorias()
    
    # Estado de conexión elegante
    if api_conectada:
        st.success("✅ **Conectado a la SBS** — Tasas actualizadas en tiempo real")
    else:
        st.warning("⚠️ **Modo offline** — Usando tasas de referencia")
    
    st.divider()
    
    # ========== SECCIÓN 1: CONFIGURACIÓN DEL PRÉSTAMO ==========
    st.subheader("📝 Configura tu Préstamo")
    
    # Fila 1: Tipo de crédito y sistema
    col_tipo1, col_tipo2 = st.columns(2)
    
    with col_tipo1:
        categoria_credito = st.selectbox(
            "🏢 **Tipo de Cliente**",
            list(CATEGORIAS_CREDITO.keys()),
            index=5 if "Consumo" in CATEGORIAS_CREDITO else 0,
            help="Selecciona según tu perfil"
        )
        
        # Mostrar descripción
        if categoria_credito in CATEGORIAS_CREDITO:
            st.caption(f"ℹ️ {CATEGORIAS_CREDITO[categoria_credito]['descripcion']}")
    
    with col_tipo2:
        opciones_producto = list(CATEGORIAS_CREDITO[categoria_credito]["opciones"].keys())
        tipo_producto = st.selectbox(
            "💳 **Producto Crediticio**",
            opciones_producto,
            help="Tipo específico de préstamo"
        )
    
    # Fila 2: Sistema de amortización
    col_sistema, col_info_sistema = st.columns([1, 2])
    
    with col_sistema:
        sistema = st.radio(
            "📐 **Sistema de Amortización**",
            ["Francés", "Alemán"],
            horizontal=True,
            help="Francés: cuota fija | Alemán: cuota decreciente"
        )
    
    with col_info_sistema:
        if sistema == "Francés":
            st.markdown("""
            <div class="info-box">
                <strong>📊 Sistema Francés</strong><br>
                <small>Cuota mensual <b>constante</b> durante todo el plazo. 
                Ideal para presupuestos fijos.</small>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="info-box">
                <strong>📉 Sistema Alemán</strong><br>
                <small>Cuota <b>decreciente</b> mes a mes. 
                Pagas menos intereses en total.</small>
            </div>
            """, unsafe_allow_html=True)
    
    st.divider()
    
    # ========== SECCIÓN 2: DATOS DEL PRÉSTAMO ==========
    st.subheader("💰 Datos del Préstamo")
    
    # Obtener información del mercado si está conectado
    promedio_mercado = 15.0
    mejor_banco = "N/A"
    mejor_tasa = 15.0
    bancos_disponibles = []
    tasas_mercado = {}
    
    if api_conectada and api_tasas:
        promedio_mercado = api_tasas.get_promedio(tipo_producto, categoria_credito)
        mejor_banco, mejor_tasa = api_tasas.get_mejor_tasa(tipo_producto, categoria_credito)
        bancos_disponibles = api_tasas.get_bancos(tipo_producto, categoria_credito)
        tasas_mercado = api_tasas.get_tasas_por_tipo(tipo_producto, categoria_credito)
    
    # Mostrar información del mercado
    if api_conectada and tasas_mercado:
        st.markdown("#### 📊 Tasas del Mercado Actual")
        
        col_m1, col_m2, col_m3 = st.columns(3)
        
        with col_m1:
            st.metric(
                "🏆 Mejor Tasa",
                f"{mejor_tasa:.2f}%",
                mejor_banco,
                delta_color="off"
            )
        
        with col_m2:
            st.metric(
                "📈 Promedio Mercado",
                f"{promedio_mercado:.2f}%"
            )
        
        with col_m3:
            peor_banco, peor_tasa = api_tasas.get_peor_tasa(tipo_producto, categoria_credito)
            st.metric(
                "📉 Tasa más Alta",
                f"{peor_tasa:.2f}%",
                peor_banco,
                delta_color="off"
            )
        
        # Mostrar bancos disponibles como chips
        with st.expander(f"🏦 Ver {len(bancos_disponibles)} bancos disponibles"):
            # Crear tabla de tasas ordenada
            tasas_ordenadas = sorted(tasas_mercado.items(), key=lambda x: x[1])
            
            col_bancos1, col_bancos2 = st.columns(2)
            
            mitad = len(tasas_ordenadas) // 2
            
            with col_bancos1:
                for banco, tasa in tasas_ordenadas[:mitad + 1]:
                    indicador = "🥇" if banco == mejor_banco else "🏦"
                    st.write(f"{indicador} **{banco}**: {tasa:.2f}%")
            
            with col_bancos2:
                for banco, tasa in tasas_ordenadas[mitad + 1:]:
                    st.write(f"🏦 **{banco}**: {tasa:.2f}%")
        
        st.divider()
    
    # Inputs principales
    col1, col2, col3 = st.columns(3)
    
    with col1:
        monto = st.number_input(
            "💵 **Monto del Préstamo (S/)**",
            min_value=1000.0,
            max_value=10000000.0,
            value=50000.0,
            step=1000.0,
            help="Monto total a solicitar",
            format="%.2f"
        )
        
        # Slider visual adicional
        monto = st.slider(
            "Ajustar monto",
            min_value=1000.0,
            max_value=500000.0,
            value=float(monto),
            step=1000.0,
            format="S/ %.0f",
            label_visibility="collapsed"
        )
    
    with col2:
        plazo = st.number_input(
            "📅 **Plazo (meses)**",
            min_value=1,
            max_value=360,
            value=36,
            step=1,
            help="Número de cuotas"
        )
        
        # Opciones rápidas de plazo
        st.markdown("**Plazos comunes:**")
        col_p1, col_p2, col_p3, col_p4 = st.columns(4)
        with col_p1:
            if st.button("12m", use_container_width=True, key="p12"):
                plazo = 12
        with col_p2:
            if st.button("24m", use_container_width=True, key="p24"):
                plazo = 24
        with col_p3:
            if st.button("36m", use_container_width=True, key="p36"):
                plazo = 36
        with col_p4:
            if st.button("48m", use_container_width=True, key="p48"):
                plazo = 48
    
    with col3:
        # Selector de banco o tasa manual
        modo_tasa = st.radio(
            "📊 **Obtener tasa desde:**",
            ["Banco específico", "Ingresar manualmente"],
            horizontal=True
        )
        
        if modo_tasa == "Banco específico" and bancos_disponibles:
            banco_seleccionado = st.selectbox(
                "🏦 **Selecciona un Banco**",
                bancos_disponibles,
                help="La tasa se cargará automáticamente"
            )
            
            if api_conectada and api_tasas:
                tea_porcentaje = api_tasas.get_tea(banco_seleccionado, tipo_producto, categoria_credito)
                if tea_porcentaje <= 0:
                    tea_porcentaje = promedio_mercado
            else:
                tea_porcentaje = promedio_mercado
            
            st.info(f"📊 TEA de {banco_seleccionado}: **{tea_porcentaje:.2f}%**")
        else:
            banco_seleccionado = None
            tea_porcentaje = st.slider(
                "📈 **TEA (%)**",
                min_value=1.0,
                max_value=100.0,
                value=float(promedio_mercado),
                step=0.1,
                help="Tasa Efectiva Anual"
            )
    
    # Indicador de tasa vs mercado
    if api_conectada:
        diferencia = tea_porcentaje - promedio_mercado
        if diferencia < -2:
            st.markdown(f"""
            <div class="rate-indicator rate-good">
                ✅ <strong>Excelente tasa</strong> — {abs(diferencia):.2f}% por debajo del promedio del mercado
            </div>
            """, unsafe_allow_html=True)
        elif diferencia > 2:
            st.markdown(f"""
            <div class="rate-indicator rate-high">
                ⚠️ <strong>Tasa elevada</strong> — {diferencia:.2f}% por encima del promedio del mercado
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="rate-indicator rate-average">
                📊 <strong>Tasa promedio</strong> — Dentro del rango normal del mercado
            </div>
            """, unsafe_allow_html=True)
    
    st.divider()
    
    # ========== SECCIÓN 3: COSTOS ADICIONALES (EXPANDIBLE) ==========
    with st.expander("💼 **Costos Adicionales** (opcional)", expanded=False):
        st.markdown("*Incluye estos costos para calcular la TCEA real*")
        
        col_cost1, col_cost2 = st.columns(2)
        
        with col_cost1:
            comision_desembolso = st.number_input(
                "Comisión de desembolso (%)",
                min_value=0.0,
                max_value=10.0,
                value=0.0,
                step=0.1,
                help="Porcentaje cobrado al desembolsar"
            )
            
            seguro_desgravamen = st.number_input(
                "Seguro desgravamen (% mensual)",
                min_value=0.0,
                max_value=1.0,
                value=0.05,
                step=0.01,
                help="Seguro sobre saldo deudor"
            )
        
        with col_cost2:
            comision_mensual = st.number_input(
                "Comisión mensual (S/)",
                min_value=0.0,
                value=0.0,
                step=5.0,
                help="Comisión fija mensual"
            )
            
            portes = st.number_input(
                "Portes y otros (S/)",
                min_value=0.0,
                value=0.0,
                step=1.0,
                help="Gastos de envío, mantenimiento, etc."
            )
    
    st.divider()
    
    # ========== BOTÓN DE CÁLCULO ==========
    calcular = st.button(
        "🔍 **CALCULAR MI CRÉDITO**",
        type="primary",
        use_container_width=True
    )
    
    if calcular:
        tea = tea_porcentaje / 100
        
        # Validar datos
        es_valido, errores = validar_datos_credito(monto, tea, plazo)
        
        if not es_valido:
            st.error("**❌ Errores en los datos:**")
            for error in errores:
                st.write(f"• {error}")
        else:
            with st.spinner("🧮 Calculando tu crédito..."):
                
                # ===== CÁLCULOS SEGÚN SISTEMA =====
                if sistema == "Francés":
                    cuota_base = calcular_cuota_francesa(monto, tea, plazo)
                    tabla = generar_tabla_francesa(monto, tea, plazo)
                else:
                    tabla = generar_tabla_alemana(monto, tea, plazo)
                    cuota_base = tabla.loc[0, 'cuota']
                    cuota_final = tabla.loc[plazo - 1, 'cuota']
                
                totales = calcular_totales(tabla)
                
                # Calcular costos adicionales
                costo_desembolso = monto * (comision_desembolso / 100)
                costo_mensual_extra = comision_mensual + portes
                saldo_promedio = monto / 2
                seguro_total = saldo_promedio * (seguro_desgravamen / 100) * plazo
                
                # Costos totales adicionales
                costos_adicionales = costo_desembolso + (costo_mensual_extra * plazo) + seguro_total
                costo_total_credito = totales['total_pagado'] + costos_adicionales
                
                # Calcular TCEA
                try:
                    tcea = calcular_tcea_completa(
                        monto, tea, plazo,
                        comision_desembolso / 100,
                        comision_mensual,
                        seguro_desgravamen / 100,
                        portes
                    )
                except:
                    tcea = None
                
                # Calcular fechas de pago
                fecha_inicio = datetime.now()
                fecha_fin = fecha_inicio + timedelta(days=plazo * 30)
                
                st.divider()
                
                # ========== RESULTADOS PRINCIPALES ==========
                st.markdown("## 📊 Resultado de tu Simulación")
                
                # Tarjeta principal de cuota
                if sistema == "Francés":
                    st.markdown(f"""
                    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                                padding: 2rem; border-radius: 16px; text-align: center; color: white; margin: 1rem 0;">
                        <p style="margin: 0; font-size: 1rem; opacity: 0.9;">Tu cuota mensual será de</p>
                        <h1 style="margin: 0.5rem 0; font-size: 3.5rem; font-weight: 700;">{formatear_moneda(cuota_base)}</h1>
                        <p style="margin: 0; font-size: 1rem; opacity: 0.9;">durante {plazo} meses</p>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                                padding: 2rem; border-radius: 16px; text-align: center; color: white; margin: 1rem 0;">
                        <p style="margin: 0; font-size: 1rem; opacity: 0.9;">Tu primera cuota será de</p>
                        <h1 style="margin: 0.5rem 0; font-size: 3rem; font-weight: 700;">{formatear_moneda(cuota_base)}</h1>
                        <p style="margin: 0; font-size: 1rem; opacity: 0.9;">↓ Disminuye hasta {formatear_moneda(cuota_final)} en el mes {plazo}</p>
                    </div>
                    """, unsafe_allow_html=True)
                
                # Métricas detalladas
                st.markdown("### 📈 Desglose Completo")
                
                col_m1, col_m2, col_m3, col_m4 = st.columns(4)
                
                with col_m1:
                    st.metric(
                        "💵 Monto Solicitado",
                        formatear_moneda(monto)
                    )
                
                with col_m2:
                    st.metric(
                        "📊 Total Intereses",
                        formatear_moneda(totales['total_intereses']),
                        f"{(totales['total_intereses']/monto)*100:.1f}% del monto"
                    )
                
                with col_m3:
                    st.metric(
                        "💼 Costos Adicionales",
                        formatear_moneda(costos_adicionales)
                    )
                
                with col_m4:
                    st.metric(
                        "💰 Costo Total",
                        formatear_moneda(costo_total_credito),
                        f"+{formatear_moneda(costo_total_credito - monto)} sobre el monto"
                    )
                
                # Segunda fila de métricas
                col_t1, col_t2, col_t3, col_t4 = st.columns(4)
                
                with col_t1:
                    st.metric("📅 TEA", f"{tea_porcentaje:.2f}%")
                
                with col_t2:
                    if tcea:
                        st.metric("📊 TCEA", f"{tcea:.2f}%", help="Tasa de Costo Efectivo Anual")
                    else:
                        st.metric("📊 TCEA", "N/A")
                
                with col_t3:
                    st.metric("📆 Fecha Inicio", fecha_inicio.strftime("%d/%m/%Y"))
                
                with col_t4:
                    st.metric("🏁 Fecha Fin", fecha_fin.strftime("%d/%m/%Y"))
                
                # Información del banco si se seleccionó
                if banco_seleccionado:
                    st.info(f"🏦 Simulación basada en tasas de **{banco_seleccionado}** para {categoria_credito} - {tipo_producto}")
                
                st.divider()
                
                # ========== TABS DE INFORMACIÓN DETALLADA ==========
                tab1, tab2, tab3, tab4 = st.tabs([
                    "📋 Tabla de Amortización", 
                    "📊 Gráficos Interactivos", 
                    "📅 Cronograma de Pagos",
                    "💾 Descargar"
                ])
                
                with tab1:
                    st.markdown("### 📋 Tabla de Amortización Completa")
                    
                    # Formatear tabla para mostrar
                    tabla_mostrar = tabla.copy()
                    tabla_mostrar['saldo_inicial'] = tabla_mostrar['saldo_inicial'].apply(formatear_moneda)
                    tabla_mostrar['interes'] = tabla_mostrar['interes'].apply(formatear_moneda)
                    tabla_mostrar['amortizacion'] = tabla_mostrar['amortizacion'].apply(formatear_moneda)
                    tabla_mostrar['cuota'] = tabla_mostrar['cuota'].apply(formatear_moneda)
                    tabla_mostrar['saldo_final'] = tabla_mostrar['saldo_final'].apply(formatear_moneda)
                    
                    # Renombrar columnas para mejor presentación
                    tabla_mostrar.columns = ['Mes', 'Saldo Inicial', 'Interés', 'Amortización', 'Cuota', 'Saldo Final']
                    
                    st.dataframe(
                        tabla_mostrar,
                        use_container_width=True,
                        height=400
                    )
                    
                    # Resumen al final
                    col_sum1, col_sum2, col_sum3 = st.columns(3)
                    with col_sum1:
                        st.metric("Total Intereses", formatear_moneda(totales['total_intereses']))
                    with col_sum2:
                        # El capital amortizado es simplemente el monto original
                        st.metric("Capital Amortizado", formatear_moneda(monto))
                    with col_sum3:
                        st.metric("Total Pagado", formatear_moneda(totales['total_pagado']))
                
                with tab2:
                    st.markdown("### 📊 Visualización de tu Crédito")
                    
                    # Gráfico 1: Evolución del saldo
                    fig_saldo = go.Figure()
                    
                    fig_saldo.add_trace(go.Scatter(
                        x=tabla['mes'],
                        y=tabla['saldo_final'],
                        mode='lines',
                        name='Saldo Deudor',
                        line=dict(color='#667eea', width=4),
                        fill='tozeroy',
                        fillcolor='rgba(102, 126, 234, 0.2)',
                        hovertemplate='Mes %{x}<br>Saldo: S/ %{y:,.2f}<extra></extra>'
                    ))
                    
                    fig_saldo.update_layout(
                        title='📉 Evolución de tu Deuda',
                        xaxis_title='Mes',
                        yaxis_title='Saldo (S/)',
                        hovermode='x unified',
                        height=400,
                        template='plotly_white'
                    )
                    
                    st.plotly_chart(fig_saldo, use_container_width=True)
                    
                    # Gráfico 2: Composición de cuotas
                    fig_composicion = go.Figure()
                    
                    fig_composicion.add_trace(go.Bar(
                        x=tabla['mes'],
                        y=tabla['interes'],
                        name='Interés',
                        marker_color='#f56565',
                        hovertemplate='Mes %{x}<br>Interés: S/ %{y:,.2f}<extra></extra>'
                    ))
                    
                    fig_composicion.add_trace(go.Bar(
                        x=tabla['mes'],
                        y=tabla['amortizacion'],
                        name='Amortización',
                        marker_color='#48bb78',
                        hovertemplate='Mes %{x}<br>Amortización: S/ %{y:,.2f}<extra></extra>'
                    ))
                    
                    fig_composicion.update_layout(
                        title='📊 Composición de Cuotas: Interés vs Capital',
                        xaxis_title='Mes',
                        yaxis_title='Monto (S/)',
                        barmode='stack',
                        hovermode='x unified',
                        height=400,
                        template='plotly_white',
                        legend=dict(orientation='h', yanchor='bottom', y=1.02)
                    )
                    
                    st.plotly_chart(fig_composicion, use_container_width=True)
                    
                    # Gráfico 3: Distribución del pago total (Pie)
                    col_pie1, col_pie2 = st.columns(2)
                    
                    with col_pie1:
                        fig_pie = go.Figure(data=[go.Pie(
                            labels=['Capital', 'Intereses', 'Costos Adicionales'],
                            values=[monto, totales['total_intereses'], costos_adicionales],
                            hole=0.4,
                            marker_colors=['#48bb78', '#f56565', '#ed8936'],
                            textinfo='label+percent',
                            hovertemplate='%{label}<br>S/ %{value:,.2f}<br>%{percent}<extra></extra>'
                        )])
                        
                        fig_pie.update_layout(
                            title='💰 Distribución del Pago Total',
                            height=350,
                            showlegend=True
                        )
                        
                        st.plotly_chart(fig_pie, use_container_width=True)
                    
                    with col_pie2:
                        # Gráfico de cuota (si es alemán, mostrar evolución)
                        if sistema == "Alemán":
                            fig_cuota = go.Figure()
                            
                            fig_cuota.add_trace(go.Scatter(
                                x=tabla['mes'],
                                y=tabla['cuota'],
                                mode='lines+markers',
                                name='Cuota',
                                line=dict(color='#667eea', width=3),
                                marker=dict(size=4)
                            ))
                            
                            fig_cuota.update_layout(
                                title='📉 Evolución de Cuota (Sistema Alemán)',
                                xaxis_title='Mes',
                                yaxis_title='Cuota (S/)',
                                height=350
                            )
                            
                            st.plotly_chart(fig_cuota, use_container_width=True)
                        else:
                            # Para sistema francés, mostrar acumulados
                            tabla['interes_acum'] = tabla['interes'].cumsum()
                            tabla['amort_acum'] = tabla['amortizacion'].cumsum()
                            
                            fig_acum = go.Figure()
                            
                            fig_acum.add_trace(go.Scatter(
                                x=tabla['mes'],
                                y=tabla['amort_acum'],
                                name='Capital Pagado',
                                fill='tozeroy',
                                fillcolor='rgba(72, 187, 120, 0.3)',
                                line=dict(color='#48bb78')
                            ))
                            
                            fig_acum.add_trace(go.Scatter(
                                x=tabla['mes'],
                                y=tabla['interes_acum'],
                                name='Intereses Pagados',
                                fill='tozeroy',
                                fillcolor='rgba(245, 101, 101, 0.3)',
                                line=dict(color='#f56565')
                            ))
                            
                            fig_acum.update_layout(
                                title='📈 Pagos Acumulados',
                                xaxis_title='Mes',
                                yaxis_title='Monto Acumulado (S/)',
                                height=350
                            )
                            
                            st.plotly_chart(fig_acum, use_container_width=True)
                
                with tab3:
                    st.markdown("### 📅 Cronograma de Pagos")
                    
                    # Crear cronograma con fechas
                    cronograma = tabla.copy()
                    fechas = [fecha_inicio + timedelta(days=30 * i) for i in range(1, plazo + 1)]
                    cronograma['fecha_pago'] = fechas[:len(cronograma)]
                    cronograma['fecha_pago'] = cronograma['fecha_pago'].apply(lambda x: x.strftime("%d/%m/%Y"))
                    
                    # Mostrar primeros y últimos pagos
                    st.markdown("#### 📆 Primeras cuotas")
                    
                    for i in range(min(6, len(cronograma))):
                        fila = cronograma.iloc[i]
                        col_fecha, col_cuota, col_detalle = st.columns([1, 1, 2])
                        
                        with col_fecha:
                            st.write(f"📅 **{fila['fecha_pago']}**")
                        with col_cuota:
                            st.write(f"💰 {formatear_moneda(fila['cuota'])}")
                        with col_detalle:
                            st.caption(f"Capital: {formatear_moneda(fila['amortizacion'])} | Interés: {formatear_moneda(fila['interes'])}")
                        
                        st.divider()
                    
                    if plazo > 6:
                        st.markdown("#### 📆 Últimas cuotas")
                        
                        for i in range(max(0, len(cronograma) - 3), len(cronograma)):
                            fila = cronograma.iloc[i]
                            col_fecha, col_cuota, col_detalle = st.columns([1, 1, 2])
                            
                            with col_fecha:
                                st.write(f"📅 **{fila['fecha_pago']}**")
                            with col_cuota:
                                st.write(f"💰 {formatear_moneda(fila['cuota'])}")
                            with col_detalle:
                                st.caption(f"Capital: {formatear_moneda(fila['amortizacion'])} | Interés: {formatear_moneda(fila['interes'])}")
                            
                            st.divider()
                
                with tab4:
                    st.markdown("### 💾 Descargar tu Simulación")
                    
                    col_dl1, col_dl2, col_dl3 = st.columns(3)
                    
                    with col_dl1:
                        # CSV
                        csv = tabla.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            label="📥 Descargar CSV",
                            data=csv,
                            file_name=f"amortizacion_{int(monto)}_{plazo}m_{sistema.lower()}.csv",
                            mime="text/csv",
                            use_container_width=True
                        )
                        st.caption("Ideal para abrir en Excel")
                    
                    with col_dl2:
                        # Excel
                        try:
                            from io import BytesIO
                            
                            excel_buffer = BytesIO()
                            with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                                tabla.to_excel(writer, sheet_name='Amortización', index=False)
                                
                                # Hoja de resumen
                                resumen_df = pd.DataFrame({
                                    'Concepto': ['Monto', 'TEA', 'Plazo', 'Sistema', 'Cuota', 'Total Intereses', 'Costo Total'],
                                    'Valor': [monto, f"{tea_porcentaje}%", f"{plazo} meses", sistema, 
                                             cuota_base, totales['total_intereses'], costo_total_credito]
                                })
                                resumen_df.to_excel(writer, sheet_name='Resumen', index=False)
                            
                            excel_buffer.seek(0)
                            
                            st.download_button(
                                label="📊 Descargar Excel",
                                data=excel_buffer,
                                file_name=f"simulacion_credito_{int(monto)}.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                use_container_width=True
                            )
                            st.caption("Incluye resumen y tabla completa")
                        except Exception as e:
                            st.error(f"Error al generar Excel: {e}")
                    
                    with col_dl3:
                        # PDF
                        try:
                            pdf_buffer = generar_pdf_calculadora(
                                monto=monto,
                                tea_porcentaje=tea_porcentaje,
                                plazo=plazo,
                                sistema=sistema,
                                cuota_base=cuota_base,
                                totales=totales,
                                costos_adicionales=costos_adicionales,
                                costo_total_credito=costo_total_credito,
                                tcea=tcea,
                                banco=banco_seleccionado,
                                categoria=categoria_credito,
                                producto=tipo_producto,
                                tabla=tabla
                            )
                            
                            st.download_button(
                                label="📄 Descargar PDF",
                                data=pdf_buffer,
                                file_name=f"simulacion_credito_{int(monto)}.pdf",
                                mime="application/pdf",
                                use_container_width=True
                            )
                            st.caption("Documento profesional")
                        except Exception as e:
                            st.error(f"Error al generar PDF: {e}")
                    
                    # Resumen para copiar
                    st.markdown("---")
                    st.markdown("#### 📋 Resumen para copiar")
                    
                    resumen_texto = f"""
═══════════════════════════════════════
    SIMULACIÓN DE CRÉDITO - OPTICRED
═══════════════════════════════════════

📌 DATOS DEL PRÉSTAMO
• Monto solicitado: {formatear_moneda(monto)}
• Plazo: {plazo} meses
• TEA: {tea_porcentaje:.2f}%
• Sistema: {sistema}
{"• Banco: " + banco_seleccionado if banco_seleccionado else ""}

💰 RESULTADOS
• Cuota mensual: {formatear_moneda(cuota_base)}
• Total intereses: {formatear_moneda(totales['total_intereses'])}
• Costos adicionales: {formatear_moneda(costos_adicionales)}
• COSTO TOTAL: {formatear_moneda(costo_total_credito)}
{"• TCEA: " + f"{tcea:.2f}%" if tcea else ""}

📅 FECHAS
• Inicio: {fecha_inicio.strftime("%d/%m/%Y")}
• Fin: {fecha_fin.strftime("%d/%m/%Y")}

═══════════════════════════════════════
Generado con OptiCred | {datetime.now().strftime("%d/%m/%Y %H:%M")}
                    """
                    
                    st.code(resumen_texto, language=None)
                
                st.divider()
                
                # ========== CONSEJOS FINALES ==========
                st.markdown("### 💡 Consejos para tu Crédito")
                
                col_consejo1, col_consejo2 = st.columns(2)
                
                with col_consejo1:
                    st.markdown("""
                    **✅ Antes de solicitar:**
                    - Compara tasas en al menos 3 bancos
                    - Verifica la TCEA, no solo la TEA
                    - Pregunta por seguros incluidos
                    - Revisa comisiones ocultas
                    """)
                
                with col_consejo2:
                    st.markdown("""
                    **📊 Tu capacidad de pago:**
                    - La cuota no debería superar el 30% de tus ingresos
                    - Ten un fondo de emergencia antes de endeudarte
                    - Considera adelantar pagos si es posible
                    """)
                
                # Alerta si la cuota es muy alta
                ingreso_recomendado = cuota_base / 0.3
                st.info(f"💼 **Ingreso mensual recomendado:** {formatear_moneda(ingreso_recomendado)} (para que la cuota sea máx. 30% de tus ingresos)")
    
    else:
        # Estado inicial - mostrar información útil
        st.markdown("---")
        st.markdown("### 💡 ¿Cómo funciona?")
        
        col_info1, col_info2, col_info3 = st.columns(3)
        
        with col_info1:
            st.markdown("""
            **1️⃣ Configura**
            
            Selecciona el tipo de crédito y sistema de amortización que deseas.
            """)
        
        with col_info2:
            st.markdown("""
            **2️⃣ Ingresa datos**
            
            Monto, plazo y tasa (o selecciona un banco para usar su tasa real).
            """)
        
        with col_info3:
            st.markdown("""
            **3️⃣ Obtén resultados**
            
            Cuota mensual, tabla de amortización, gráficos y más.
            """)
        
        st.markdown("---")
        st.info("👆 Completa los datos arriba y presiona **CALCULAR MI CRÉDITO** para comenzar")