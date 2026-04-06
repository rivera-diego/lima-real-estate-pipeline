import folium
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
import streamlit as st
from streamlit_folium import st_folium

# 1. Configuración general
st.set_page_config(page_title="Dashboard Inmobiliario", layout="wide")
st.title("🏠 Análisis del Mercado Inmobiliario en Lima")

# 2. Cargar Datos
@st.cache_data
def cargar_datos():
    # En la nube ya no podemos usar la base local (postgresql://127.0.0.1)
    # Por eso leemos el extracto limpio que preparamos:
    df = pd.read_csv("data/propiedades_limpias.csv")
    return df

df = cargar_datos()

# ========================================================
# --- LA MAGIA: FILTROS INTERACTIVOS EN LA BARRA LATERAL ---
# ========================================================
st.sidebar.header("🔍 Filtros de Búsqueda")

# 1. Filtro Desplegable Múltiple (Distritos)
distritos_unicos = sorted(df['distrito_real'].dropna().unique())
distrito_seleccionado = st.sidebar.multiselect(
    "Selecciona Distrito(s)",
    options=distritos_unicos,
    default=[] # Por defecto inicia vacío (lo que significa: "mostrar todos")
)

# 2. Filtro Tipo Deslizador (Rango de Precio)
precio_min = int(df['precio_soles'].min())
precio_max = int(df['precio_soles'].max())

rango_precio = st.sidebar.slider(
    "Rango de Precio (S/)",
    min_value=precio_min,
    max_value=precio_max,
    value=(precio_min, precio_max), # Por defecto el slider abarca desde el menor al mayor
    step=50000,
    format="S/ %d"
)

# 3. APLICAR FILTROS (Crear el sub-dataframe df_filtrado)
df_filtrado = df.copy()

# A: Solo conservar (filtrar) aquellos que estén en los distritos seleccionados 
if len(distrito_seleccionado) > 0:
    # .isin() dice: "quédate con las filas cuyo distrito esté DE ADENTRO de esta lista"
    df_filtrado = df_filtrado[df_filtrado['distrito_real'].isin(distrito_seleccionado)]

# B: Y además, quedarse solo con los precios > Mínimo del slider y < Máximo del slider
df_filtrado = df_filtrado[
    (df_filtrado['precio_soles'] >= rango_precio[0]) & 
    (df_filtrado['precio_soles'] <= rango_precio[1])
]

# Imprimir en la barra cuántos registros sobrevivieron al filtro
st.sidebar.markdown("---")
st.sidebar.markdown(f"**📌 {len(df_filtrado)} propiedades mostradas.**")


# ========================================================
# --- GRÁFICOS DINÁMICOS (Ahora usan df_filtrado) ---
# ========================================================

# Pongo los dos primeros gráficos en 2 columnas para usar mejor el espacio
col1, col2 = st.columns(2)

with col1:
    st.subheader("Top distritos más caros")
    # Nota que aquí ya no uso "df", uso mi variable "df_filtrado" recién cortada
    top10_caros = df_filtrado.groupby("distrito_real")["precio_soles"].mean().round(2).sort_values(ascending=False).head(10).reset_index()
    
    if not top10_caros.empty:
        fig1, ax1 = plt.subplots(figsize=(8, 5))
        sns.barplot(data=top10_caros, x="precio_soles", y="distrito_real", ax=ax1)
        ax1.xaxis.set_major_formatter(lambda x, pos: f"S/ {x / 1e6:.1f}M" if x >= 1e6 else f"S/ {x / 1e3:.0f}K")
        plt.xlabel("Precio")
        plt.ylabel("")
        plt.tight_layout()
        st.pyplot(fig1)

with col2:
    st.subheader("Top distritos más económicos")
    top10_baratos = df_filtrado.groupby("distrito_real")["precio_soles"].mean().round(2).sort_values(ascending=True).head(10).reset_index()
    
    if not top10_baratos.empty:
        fig2, ax2 = plt.subplots(figsize=(8, 5))
        sns.barplot(data=top10_baratos, x="precio_soles", y="distrito_real", ax=ax2)
        ax2.xaxis.set_major_formatter(lambda x, pos: f"S/ {x / 1e6:.1f}M" if x >= 1e6 else f"S/ {x / 1e3:.0f}K")
        plt.xlabel("Precio")
        plt.ylabel("")
        plt.tight_layout()
        st.pyplot(fig2)

st.write("---")
st.subheader("Distribución de Precios")
if not df_filtrado.empty:
    fig3, ax3 = plt.subplots(figsize=(10, 3))
    sns.histplot(df_filtrado["precio_soles"].dropna(), bins=50, kde=True, ax=ax3)
    plt.xlabel("Precio (S/)")
    plt.ylabel("Cantidad")
    sns.despine(top=True, right=True, left=False, bottom=False, ax=ax3)
    ax3.xaxis.set_major_formatter(lambda x, pos: f"S/ {x / 1e6:.1f}M" if x >= 1e6 else f"S/ {x / 1e3:.0f}K")
    plt.tight_layout()
    st.pyplot(fig3)

st.write("---")
st.subheader("Mapa (Interactivo)")
# Filtramos mapa quitando nulos de gps, como siempre, pero basado en el total ya filtrado
df_mapa = df_filtrado.dropna(subset=["latitud", "longitud"])

if not df_mapa.empty:
    lima_coords = [-12.0464, -77.0428]
    mapa = folium.Map(location=lima_coords, zoom_start=11)
    
    # ⚠️ OPTIMIZACIÓN WEB: Streamlit procesa el mapa algo lento en el Frontend, 
    # En Data Science si hay más de 1000 puntos en folium para interfaz web, se toma una muestra (sample) 
    # al azar de 1500 puntos para que no colapse el navegador del computador de quien evalúe esto.
    if len(df_mapa) > 1500:
        st.info(f"Mostrando muestra de 1500 puntos (de {len(df_mapa)}) por rendimiento al navegador. Usa Filtros para explorar más.")
        df_mapa = df_mapa.sample(1500)

    for indice, fila in df_mapa.iterrows():
        folium.CircleMarker(
            location=[fila["latitud"], fila["longitud"]],
            radius=3,
            popup=str(fila["urbanizacion"]) + " - " + str(fila["distrito_real"]),
            color="blue",
            fill=True,
            fill_color="cyan",
            fill_opacity=0.6,
        ).add_to(mapa)

    st_folium(mapa, width="100%", height=500)
else:
    st.warning("No hay resultados de coordenadas para mostrar mapa con ese filtro.")
