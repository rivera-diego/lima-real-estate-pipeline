import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Dashboard Inmobiliario Lima", layout="wide")
st.title("🏠 Análisis del Mercado Inmobiliario en Lima")

# cargo los CSVs que armé a partir de los datos limpios de PostgreSQL
# son promedios por distrito, no datos individuales de cada anuncio
@st.cache_data
def cargar_datos():
    df_resumen = pd.read_csv("data/resumen_distritos.csv")
    df_hist = pd.read_csv("data/histograma_precios.csv")
    return df_resumen, df_hist

df_resumen, df_hist = cargar_datos()

# --- SIDEBAR ---
st.sidebar.header("🔍 Filtros")
st.sidebar.markdown("Selecciona uno o más distritos para comparar.")

distritos_disp = sorted(df_resumen['distrito_real'].unique())
distrito_seleccionado = st.sidebar.multiselect(
    "Distrito(s)",
    options=distritos_disp,
    default=[]
)

# si el usuario no seleccionó nada, muestro todos
if len(distrito_seleccionado) > 0:
    df_graficos = df_resumen[df_resumen['distrito_real'].isin(distrito_seleccionado)]
else:
    df_graficos = df_resumen

# métricas rápidas en el sidebar
st.sidebar.markdown("---")
st.sidebar.metric("📊 Distritos visibles", len(df_graficos))

total_casas = df_graficos['cantidad'].sum()
# promedio ponderado: no puedo solo promediar los promedios, tengo que ponderar por cantidad
precio_promedio_total = (
    (df_graficos['precio_promedio'] * df_graficos['cantidad']).sum() / total_casas
    if total_casas > 0 else 0
)
st.sidebar.metric("🏘️ Propiedades representadas", total_casas)
st.sidebar.metric("💰 Precio promedio", f"S/ {precio_promedio_total:,.0f}")


# --- GRÁFICOS DE BARRAS ---
st.write("---")
col1, col2 = st.columns(2)

with col1:
    st.subheader("Distritos más caros")
    top10_caros = df_graficos.sort_values(by='precio_promedio', ascending=False).head(10)

    if not top10_caros.empty:
        fig1 = px.bar(
            top10_caros,
            x="precio_promedio",
            y="distrito_real",
            orientation='h',
            text_auto='.3s',
            labels={'precio_promedio': 'Precio promedio (S/)', 'distrito_real': ''},
            color='precio_promedio',
            color_continuous_scale='sunsetdark'
        )
        # ordeno de mayor a menor (ascending porque el eje Y en horizontal se invierte)
        fig1.update_layout(yaxis={'categoryorder': 'total ascending'}, coloraxis_showscale=False)
        st.plotly_chart(fig1, use_container_width=True)

with col2:
    st.subheader("Distritos más económicos")
    top10_baratos = df_graficos.sort_values(by='precio_promedio', ascending=True).head(10)

    if not top10_baratos.empty:
        fig2 = px.bar(
            top10_baratos,
            x="precio_promedio",
            y="distrito_real",
            orientation='h',
            text_auto='.3s',
            labels={'precio_promedio': 'Precio promedio (S/)', 'distrito_real': ''},
            color='precio_promedio',
            color_continuous_scale='haline'
        )
        fig2.update_layout(yaxis={'categoryorder': 'total descending'}, coloraxis_showscale=False)
        st.plotly_chart(fig2, use_container_width=True)


# --- MAPA POR DISTRITOS ---
st.write("---")
st.subheader("Mapa por Distritos")
st.write("📌 *El tamaño de cada burbuja indica cuántas propiedades hay en ese distrito. El color indica el precio promedio.*")

if not df_graficos.empty:
    fig_mapa = px.scatter_mapbox(
        df_graficos,
        lat="latitud_centro",
        lon="longitud_centro",
        hover_name="distrito_real",
        # oculto lat/lon del tooltip porque no aportan nada al usuario
        hover_data={
            "latitud_centro": False,
            "longitud_centro": False,
            "precio_promedio": ":,.0f",
            "cantidad": True
        },
        color="precio_promedio",
        size="cantidad",
        color_continuous_scale="Plasma",
        size_max=40,
        zoom=10,
        mapbox_style="carto-darkmatter"
    )
    fig_mapa.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0})
    st.plotly_chart(fig_mapa, use_container_width=True)


# --- DISTRIBUCIÓN GLOBAL DE PRECIOS ---
st.write("---")
st.subheader("Distribución de Precios (todos los datos limpios)")

# este gráfico no cambia con el filtro, siempre muestra el histograma completo como referencia
fig3 = px.bar(
    df_hist,
    x="rango_inicio",
    y="cantidad",
    labels={'rango_inicio': 'Precio base del tramo (S/)', 'cantidad': 'Cantidad de propiedades'},
    color='cantidad',
    color_continuous_scale='Teal'
)
# bargap=0 para que las barras se toquen y parezca un histograma real
fig3.update_traces(marker_line_width=0)
fig3.update_layout(bargap=0, coloraxis_showscale=False)
st.plotly_chart(fig3, use_container_width=True)

st.markdown(
    "> 🛡️ *Los datos de este dashboard son promedios y conteos por distrito calculados a partir de anuncios públicos. "
    "No se redistribuyen datos individuales ni información de contacto de los anunciantes.*"
)
