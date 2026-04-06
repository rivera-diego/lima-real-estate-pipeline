import streamlit as st
import pandas as pd
import plotly.express as px

# 1. Configuración de página
st.set_page_config(page_title="Dashboard Inmobiliario", layout="wide")
st.title("🏠 Análisis Agregado del Mercado Inmobiliario en Lima")

# 2. Cargar DATOS SEGUROS (Agregados, no individuales)
@st.cache_data
def cargar_datos():
    df_resumen = pd.read_csv("data/resumen_distritos.csv")
    df_hist = pd.read_csv("data/histograma_precios.csv")
    return df_resumen, df_hist

df_resumen, df_hist = cargar_datos()

# ==========================================
# --- SIDEBAR: FILTROS INTERACTIVOS ---
# ==========================================
st.sidebar.header("🔍 Parámetros de Selección")
st.sidebar.markdown("Filtra los distritos que deseas analizar frente a frente.")

distritos_disp = sorted(df_resumen['distrito_real'].unique())
distrito_seleccionado = st.sidebar.multiselect(
    "Selecciona Distrito(s)", 
    options=distritos_disp,
    default=[]
)

# Lógica del Filtro
if len(distrito_seleccionado) > 0:
    df_graficos = df_resumen[df_resumen['distrito_real'].isin(distrito_seleccionado)]
else:
    df_graficos = df_resumen

st.sidebar.markdown("---")
st.sidebar.metric(label="📊 Distritos Mostrados", value=len(df_graficos))
# Calculamos sumas y promedios base
total_casas = df_graficos['cantidad'].sum()
precio_promedio_total = (df_graficos['precio_promedio'] * df_graficos['cantidad']).sum() / total_casas if total_casas > 0 else 0
st.sidebar.metric(label="🏘️ Propiedades Representadas", value=total_casas)
st.sidebar.metric(label="💰 Promedio de esta región", value=f"S/ {precio_promedio_total:,.0f}")


# ==========================================
# --- GRÁFICOS PLOTLY (Bellos e interactivos) ---
# ==========================================
st.write("---")
col1, col2 = st.columns(2)

with col1:
    st.subheader("Top Distritos Más Caros (Promedio)")
    top10_caros = df_graficos.sort_values(by='precio_promedio', ascending=False).head(10)
    
    if not top10_caros.empty:
        # Gráfico dinámico de barras horizontales
        fig1 = px.bar(
            top10_caros, 
            x="precio_promedio", 
            y="distrito_real", 
            orientation='h', # Horizontal
            text_auto='.3s', # Agrega las etiquetas de números en las barras
            labels={'precio_promedio': 'Precio M. (S/.)', 'distrito_real': 'Distrito'},
            color='precio_promedio',
            color_continuous_scale='sunsetdark' # Paleta super profesional y oscura
        )
        # Volteamos el eje Y para que el Distrito más caro salga primero arriba
        fig1.update_layout(yaxis={'categoryorder':'total ascending'}, coloraxis_showscale=False)
        st.plotly_chart(fig1, use_container_width=True)

with col2:
    st.subheader("Top Distritos Más Económicos")
    top10_baratos = df_graficos.sort_values(by='precio_promedio', ascending=True).head(10)
    
    if not top10_baratos.empty:
        fig2 = px.bar(
            top10_baratos, 
            x="precio_promedio", 
            y="distrito_real", 
            orientation='h',
            text_auto='.3s',
            labels={'precio_promedio': 'Precio M. (S/.)', 'distrito_real': 'Distrito'},
            color='precio_promedio',
            color_continuous_scale='haline'
        )
        fig2.update_layout(yaxis={'categoryorder':'total descending'}, coloraxis_showscale=False)
        st.plotly_chart(fig2, use_container_width=True)


# MAPA PREMIUM Y OPTIMIZADO
st.write("---")
st.subheader("Mapa Sintético del Mercado por Distritos")
st.write("📌 *Cada burbuja representa la centralidad de oferta de un distrito. El **tamaño** es el volumen de casas en venta y el **color** indica precio promedio.*")

if not df_graficos.empty:
    fig_mapa = px.scatter_mapbox(
        df_graficos, 
        lat="latitud_centro", 
        lon="longitud_centro",
        hover_name="distrito_real", 
        # Que mostrar al pasar el mouse por encima
        hover_data={"latitud_centro": False, "longitud_centro": False, "precio_promedio": ":,.0f", "cantidad": True},
        color="precio_promedio",
        size="cantidad",            # Las burbujas grandes significan más casas
        color_continuous_scale="Plasma",
        size_max=40,                # Burbuja máxima
        zoom=10, 
        mapbox_style="carto-darkmatter"  # Mapa negro moderno
    )
    # Limpiamos los bordes muertos del grafico para que use todo el layout web
    fig_mapa.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
    st.plotly_chart(fig_mapa, use_container_width=True)


# HISTOGRAMA GLOBAL (Usa Base Completa para Referencia)
st.write("---")
st.subheader("Curva de Distribución de Propiedades (Global)")
fig3 = px.bar(
    df_hist, 
    x="rango_inicio", 
    y="cantidad", 
    labels={'rango_inicio': 'Rango Base (Precio Mínimo de Tramo)', 'cantidad': 'Cantidad Inmuebles'},
    color='cantidad',
    color_continuous_scale='Teal'
)
# Truco en Plotly para forzar que sea un histograma sin espacios y moderno
fig3.update_traces(marker_line_width=0)
fig3.update_layout(bargap=0, coloraxis_showscale=False)
st.plotly_chart(fig3, use_container_width=True)

st.markdown("> 🛡️ *Nota de Legalidad: Respetando estrictamente los Términos de Servicio, los datos de este dashboard son agregaciones matemáticas de nivel distrital y estadístico, sin contener datos crudos ni personales.*")
