# aplicacion.py
"""
OptiCred - Sistema Inteligente de Optimización de Créditos
"""
import streamlit as st
import asyncio
from api.api_client import OptiCredAPIClient
from modules.calculadora import mostrar_calculadora_creditos
from modules.comparador import mostrar_comparador_creditos
from modules.simulador import mostrar_simulador_pagos
from modules.recomendador import mostrar_recomendador_inteligente

# Configuración de la página
st.set_page_config(
    page_title="OptiCred - Dashboard de Créditos",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============= SIDEBAR - NAVEGACIÓN =============
st.sidebar.title("Navegación")
st.sidebar.markdown("---")

opcion = st.sidebar.radio(
    "Selecciona una opción:",
    ["🏠 Inicio", 
     "💰 Calculadora de Créditos",
     "📊 Comparador de Créditos",
     "🔄 Simulador de Pagos Extras",
     "🎯 Recomendador Inteligente",
     "🧪 Prueba de Conexión"],
    index=0
)

st.sidebar.markdown("---")

# Sección del código QR (opcional)
st.sidebar.markdown("### 📱 Accede a nuestra aplicación")
st.sidebar.info("Escanea el código QR para acceder desde tu móvil")

# Si tienes un QR, descomenta esto:
# try:
#     from PIL import Image
#     qr_image = Image.open("recursos/CodigoQR.png")
#     st.sidebar.image(qr_image, use_container_width=True)
#     
#     with open("recursos/CodigoQR.png", "rb") as file:
#         st.sidebar.download_button(
#             label="⬇️ Descargar Código QR",
#             data=file,
#             file_name="OptiCred_QR.png",
#             mime="image/png",
#             use_container_width=True
#         )
# except:
#     st.sidebar.warning("QR no disponible")

# ============= CONTENIDO PRINCIPAL =============

if opcion == "🏠 Inicio":
    # Página de inicio
    st.title("💰 Dashboard de Créditos")
    st.subheader("Herramienta integral para análisis y optimización de créditos financieros")
    
    st.divider()
    
    st.header("Bienvenido al Dashboard de OptiCred")
    
    st.write("")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("💰 Calculadora de Créditos")
        
        st.markdown("**Herramienta especializada para:**")
        st.markdown("""
        - Calcular cuotas mensuales de tu crédito
        - Generar tablas de amortización completas
        - Visualizar el comportamiento de tu deuda
        - Conocer el total de intereses a pagar
        """)
        
        st.markdown("**Características:**")
        st.markdown("""
        - Sistema Francés (cuota fija)
        - Sistema Alemán (amortización constante)
        - Cálculo automático de TEA y TEM
        - Gráficos interactivos de evolución
        """)
    
    with col2:
        st.subheader("📊 Comparador de Créditos")
        
        st.markdown("**Herramienta completa para:**")
        st.markdown("""
        - Comparar hasta 5 créditos simultáneamente
        - Evaluar TEA, TCEA y costos totales
        - Identificar la mejor opción de financiamiento
        - Analizar diferentes plazos y montos
        """)
        
        st.markdown("**Tipos de análisis:**")
        st.markdown("""
        - Créditos de consumo
        - Créditos vehiculares
        - Créditos hipotecarios
        - Créditos empresariales
        """)
        
        st.markdown("**Métricas incluidas:**")
        st.markdown("""
        - TCEA (Tasa de Costo Efectivo Anual)
        - Costo total del financiamiento
        - Comparación gráfica entre opciones
        """)
    
    st.write("")
    
    col3, col4 = st.columns(2)
    
    with col3:
        st.subheader("🔄 Simulador de Pagos Extras")
        
        st.markdown("**Funcionalidades avanzadas:**")
        st.markdown("""
        - Simular pagos extraordinarios
        - Calcular ahorro en intereses
        - Reducir tiempo del préstamo
        - Optimizar el pago de tu deuda
        """)
        
        st.markdown("**Opciones de simulación:**")
        st.markdown("""
        - Pago único en mes específico
        - Pagos recurrentes adicionales
        - Reducción de plazo vs reducción de cuota
        - Comparación antes/después del pago
        """)
    
    with col4:
        st.subheader("🎯 Recomendador Inteligente")
        
        st.markdown("**Sistema automatizado que:**")
        st.markdown("""
        - Recomienda el mejor crédito según tus necesidades
        - Evalúa múltiples criterios financieros
        - Calcula tu capacidad de pago
        - Optimiza tu decisión de financiamiento
        """)
        
        st.markdown("**Criterios de evaluación:**")
        st.markdown("""
        - Menor TCEA
        - Menor costo total
        - Menor tiempo de pago
        - Menor interés total
        - Ajuste a capacidad de pago
        """)
    
    st.divider()
    
    # Conceptos Clave
    st.header("📚 Conceptos Clave")
    
    col5, col6 = st.columns(2)
    
    with col5:
        with st.expander("¿Qué son los Créditos Financieros?"):
            st.markdown("""
            Los créditos son préstamos de dinero que deben devolverse con intereses.
            
            **Elementos principales:**
            - Monto del préstamo
            - Plazo de pago
            - Tasa de interés
            - Cuotas mensuales
            - Comisiones y seguros
            """)
        
        with st.expander("Sistema de Amortización Francés"):
            st.markdown("""
            **Características:**
            - Cuota constante todos los meses
            - Al inicio pagas más intereses
            - Al final pagas más capital
            - Presupuesto fijo mensual
            """)
    
    with col6:
        with st.expander("Sistema de Amortización Alemán"):
            st.markdown("""
            **Características:**
            - Amortización constante de capital
            - Cuota decreciente en el tiempo
            - Menos intereses totales
            - Cuotas iniciales más altas
            """)
        
        with st.expander("Conceptos Financieros Importantes"):
            st.markdown("""
            - **TEA**: Tasa Efectiva Anual
            - **TEM**: Tasa Efectiva Mensual
            - **TCEA**: Tasa de Costo Efectivo Anual
            - **Amortización**: Pago del capital
            - **Interés**: Costo del dinero
            - **Prepago**: Pago anticipado
            """)

elif opcion == "💰 Calculadora de Créditos":
    mostrar_calculadora_creditos()

elif opcion == "📊 Comparador de Créditos":
    mostrar_comparador_creditos()

elif opcion == "🔄 Simulador de Pagos Extras":
    mostrar_simulador_pagos()

elif opcion == "🎯 Recomendador Inteligente":
    mostrar_recomendador_inteligente()

elif opcion == "🧪 Prueba de Conexión":
    st.header("🧪 Prueba de Conexión con la API")
    st.caption("Verifica el estado del servidor y muestra tablas devueltas por los endpoints.")

    with st.spinner("Conectando con la API y obteniendo datos..."):
        try:
            async def _fetch_basico():
                client = OptiCredAPIClient()
                try:
                    health = await client.health_check()
                    tasas_activas = await client.get_tasas_activas()
                    bancos = await client.get_bancos()
                    return health, tasas_activas, bancos
                finally:
                    await client.close_session()

            health, tasas_activas, bancos = asyncio.run(_fetch_basico())
            st.success(f"API OK: {health.get('status')} | {health.get('timestamp')}")
        except Exception as e:
            st.error(f"Error al conectar con la API: {e}")
            tasas_activas, bancos = None, None

    if tasas_activas is not None:
        st.subheader("Tasas Activas")
        st.dataframe(tasas_activas, use_container_width=True)

    if bancos is not None:
        st.subheader("Bancos")
        st.dataframe(bancos, use_container_width=True)

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: gray;'>
        <p>OptiCred - Dashboard de Créditos | Desarrollado con Streamlit</p>
    </div>
    """,
    unsafe_allow_html=True
)