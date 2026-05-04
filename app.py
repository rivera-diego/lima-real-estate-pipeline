import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(
    page_title="Mercado Inmobiliario Lima — Urbania",
    layout="wide",
    page_icon="🏠"
)

# ── CSS mínimo para mejorar tipografía ──────────────────────────────────────
st.markdown("""
<style>
  .source-badge {
    display: inline-block;
    background: #FF4B4B;
    color: white;
    font-size: 0.75rem;
    font-weight: 700;
    padding: 2px 10px;
    border-radius: 20px;
    letter-spacing: 0.05em;
    vertical-align: middle;
  }
  .section-note {
    font-size: 0.83rem;
    color: #888;
    font-style: italic;
  }
</style>
""", unsafe_allow_html=True)

# ── TÍTULO Y FUENTE ─────────────────────────────────────────────────────────
st.title("🏠 Mercado Inmobiliario — Lima, Perú")
st.markdown(
    "Datos reales obtenidos de <span class='source-badge'>urbania.com</span> · "
    "19 492 anuncios públicos · Fines académicos y de portafolio",
    unsafe_allow_html=True
)
st.markdown("---")


# ── CARGA DE DATOS ──────────────────────────────────────────────────────────
@st.cache_data
def cargar_datos():
    df_res       = pd.read_csv("data/resumen_distritos.csv")
    df_hist      = pd.read_csv("data/histograma_precios.csv")
    df_tipos     = pd.read_csv("data/tipos_propiedad.csv")
    df_meses     = pd.read_csv("data/publicaciones_por_mes.csv")
    df_amen      = pd.read_csv("data/amenidades.csv")
    df_dorm      = pd.read_csv("data/dormitorios.csv")
    df_ban       = pd.read_csv("data/banos.csv")
    df_tipo_dist = pd.read_csv("data/resumen_tipo_distrito.csv")
    return df_res, df_hist, df_tipos, df_meses, df_amen, df_dorm, df_ban, df_tipo_dist

df_res, df_hist, df_tipos, df_meses, df_amen, df_dorm, df_ban, df_tipo_dist = cargar_datos()


# ── HELPER: etiquetas legibles ───────────────────────────────────────────────
def label(col: str) -> str:
    """Convierte snake_case y nombres de columna en etiquetas legibles."""
    mapping = {
        "precio_promedio":  "Precio promedio (S/)",
        "cantidad":         "Cantidad de propiedades",
        "distrito_real":    "Distrito",
        "tipo":             "Tipo de propiedad",
        "amenidad":         "Amenidad",
        "dormitorios":      "Dormitorios",
        "banos":            "Baños",
        "rango_inicio":     "Precio base del tramo (S/)",
        "mes":              "Mes",
    }
    return mapping.get(col, col.replace("_", " ").capitalize())


# ── SIDEBAR ─────────────────────────────────────────────────────────────────
st.sidebar.header("🔍 Filtros")

# Filtro de tipo de propiedad
tipos_disponibles = sorted(df_tipos["tipo"].tolist())
tipo_sel = st.sidebar.multiselect(
    "Tipo de propiedad",
    options=tipos_disponibles,
    default=[]
)

# Filtro de distrito
# Si hay tipo activo, limitar distritos a los que tienen ese tipo
if tipo_sel:
    distritos_disp = sorted(
        df_tipo_dist[df_tipo_dist["tipo"].isin(tipo_sel)]["distrito_real"].unique()
    )
else:
    distritos_disp = sorted(df_res["distrito_real"].unique())

distrito_sel = st.sidebar.multiselect(
    "Distrito(s)",
    options=distritos_disp,
    default=[]
)

# ── Construir df_graficos según filtros activos ──────────────────────────────
if tipo_sel:
    df_base = df_tipo_dist[df_tipo_dist["tipo"].isin(tipo_sel)]
    if distrito_sel:
        df_base = df_base[df_base["distrito_real"].isin(distrito_sel)]
    # Reagrupar por distrito ponderando precio por cantidad
    df_graficos = (
        df_base
        .groupby(["distrito_real", "latitud_centro", "longitud_centro"], as_index=False)
        .apply(lambda g: pd.Series({
            "precio_promedio": (g["precio_promedio"] * g["cantidad"]).sum() / g["cantidad"].sum(),
            "cantidad": g["cantidad"].sum(),
        }))
        .reset_index(drop=True)
    )
else:
    if distrito_sel:
        df_graficos = df_res[df_res["distrito_real"].isin(distrito_sel)].copy()
    else:
        df_graficos = df_res.copy()

# ── Métricas en sidebar ──────────────────────────────────────────────────────
st.sidebar.markdown("---")
total_props = df_graficos["cantidad"].sum()
precio_pond = (
    (df_graficos["precio_promedio"] * df_graficos["cantidad"]).sum() / total_props
    if total_props > 0 else 0
)
mediana_est = df_graficos["precio_promedio"].median()

st.sidebar.metric("📊 Distritos visibles", len(df_graficos))
st.sidebar.metric("🏘️ Propiedades representadas", f"{int(total_props):,}")
st.sidebar.metric("💰 Precio promedio ponderado", f"S/ {precio_pond:,.0f}")
st.sidebar.metric("📍 Mediana de precios promedio", f"S/ {mediana_est:,.0f}")

if tipo_sel or distrito_sel:
    partes = []
    if tipo_sel: partes.append(f"**{', '.join(tipo_sel)}**")
    if distrito_sel: partes.append(f"**{len(distrito_sel)} distrito(s)**")
    st.sidebar.info("Filtrando por " + " · ".join(partes) + ".")
else:
    st.sidebar.caption("Sin filtros activos: se muestran todos los datos.")


# ════════════════════════════════════════════════════════════════════════════
# SECCIÓN 1 — RANKING POR PRECIO
# ════════════════════════════════════════════════════════════════════════════
if distrito_sel:
    # Con filtro activo: mostrar comparativa de los distritos seleccionados
    st.subheader("📊 Comparativa de Distritos Seleccionados")
    st.markdown(
        "<p class='section-note'>Precios promedio de los distritos que elegiste.</p>",
        unsafe_allow_html=True
    )

    df_cmp = df_graficos.sort_values("precio_promedio", ascending=False)
    fig_cmp = px.bar(
        df_cmp,
        x="distrito_real",
        y="precio_promedio",
        text=df_cmp["precio_promedio"].apply(lambda v: f"S/ {v/1e6:.2f}M" if v >= 1e6 else f"S/ {v/1e3:.0f}K"),
        labels={"distrito_real": label("distrito_real"), "precio_promedio": label("precio_promedio")},
        color="precio_promedio",
        color_continuous_scale="Plasma",
    )
    fig_cmp.update_layout(coloraxis_showscale=False, xaxis_title="", yaxis_tickformat=",.0f")
    fig_cmp.update_traces(textposition="outside")
    st.plotly_chart(fig_cmp, use_container_width=True)

else:
    # Sin filtro: ranking top 10 caros y baratos
    st.subheader("📊 Ranking de Distritos por Precio")
    st.markdown(
        "<p class='section-note'>Top 10 distritos más caros y más económicos según precio promedio.</p>",
        unsafe_allow_html=True
    )

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**🔴 Distritos más caros**")
        top10_caros = df_graficos.sort_values("precio_promedio", ascending=False).head(10)
        fig1 = px.bar(
            top10_caros,
            x="precio_promedio",
            y="distrito_real",
            orientation="h",
            text=top10_caros["precio_promedio"].apply(lambda v: f"S/ {v/1e6:.2f}M" if v >= 1e6 else f"S/ {v/1e3:.0f}K"),
            labels={"precio_promedio": label("precio_promedio"), "distrito_real": ""},
            color="precio_promedio",
            color_continuous_scale="Sunsetdark",
        )
        fig1.update_layout(yaxis={"categoryorder": "total ascending"}, coloraxis_showscale=False)
        fig1.update_traces(textposition="outside")
        st.plotly_chart(fig1, use_container_width=True)

    with col2:
        st.markdown("**🟢 Distritos más económicos**")
        top10_bar = df_graficos.sort_values("precio_promedio", ascending=True).head(10)
        fig2 = px.bar(
            top10_bar,
            x="precio_promedio",
            y="distrito_real",
            orientation="h",
            text=top10_bar["precio_promedio"].apply(lambda v: f"S/ {v/1e3:.0f}K"),
            labels={"precio_promedio": label("precio_promedio"), "distrito_real": ""},
            color="precio_promedio",
            color_continuous_scale="Haline",
        )
        fig2.update_layout(yaxis={"categoryorder": "total descending"}, coloraxis_showscale=False)
        fig2.update_traces(textposition="outside")
        st.plotly_chart(fig2, use_container_width=True)


# ════════════════════════════════════════════════════════════════════════════
# SECCIÓN 2 — MAPA
# ════════════════════════════════════════════════════════════════════════════
st.markdown("---")
st.subheader("🗺️ Mapa de Distritos")
st.markdown(
    "<p class='section-note'>"
    "El tamaño de cada burbuja indica cuántas propiedades hay en ese distrito. "
    "El color indica el precio promedio."
    "</p>",
    unsafe_allow_html=True
)

if not df_graficos.empty:
    df_mapa = df_graficos.copy()
    df_mapa["precio_fmt"] = df_mapa["precio_promedio"].apply(
        lambda v: f"S/ {v/1e6:.2f}M" if v >= 1e6 else f"S/ {v/1e3:.0f}K"
    )
    fig_mapa = px.scatter_mapbox(
        df_mapa,
        lat="latitud_centro",
        lon="longitud_centro",
        hover_name="distrito_real",
        hover_data={
            "latitud_centro": False,
            "longitud_centro": False,
            "precio_promedio": False,
            "precio_fmt": True,
            "cantidad": True,
        },
        labels={"precio_fmt": "Precio promedio", "cantidad": "Propiedades"},
        color="precio_promedio",
        size="cantidad",
        color_continuous_scale="Plasma",
        size_max=40,
        zoom=9,
        mapbox_style="carto-darkmatter",
    )
    fig_mapa.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0}, coloraxis_showscale=False)
    st.plotly_chart(fig_mapa, use_container_width=True)


# ════════════════════════════════════════════════════════════════════════════
# SECCIÓN 3 — DISTRIBUCIÓN DE PRECIOS (histograma global)
# ════════════════════════════════════════════════════════════════════════════
st.markdown("---")
st.subheader("📈 Distribución Global de Precios")
st.markdown(
    "<p class='section-note'>"
    "Histograma de todos los anuncios válidos (excluyendo outliers por IQR). "
    "No varía con el filtro de distrito."
    "</p>",
    unsafe_allow_html=True
)

df_hist_plot = df_hist.copy()
df_hist_plot["rango_label"] = df_hist_plot["rango_inicio"].apply(
    lambda v: f"S/ {v/1e3:.0f}K"
)
fig3 = px.bar(
    df_hist_plot,
    x="rango_inicio",
    y="cantidad",
    labels={"rango_inicio": label("rango_inicio"), "cantidad": label("cantidad")},
    color="cantidad",
    color_continuous_scale="Teal",
)
fig3.update_traces(marker_line_width=0)
fig3.update_layout(
    bargap=0,
    coloraxis_showscale=False,
    xaxis=dict(tickformat=",.0f"),
)
st.plotly_chart(fig3, use_container_width=True)


# ════════════════════════════════════════════════════════════════════════════
# SECCIÓN 4 — TIPOS DE PROPIEDAD
# ════════════════════════════════════════════════════════════════════════════
st.markdown("---")
st.subheader("🏗️ Tipos de Propiedad")
st.markdown(
    "<p class='section-note'>"
    "¿Qué se publica más en Lima? Distribución de los 19 492 anuncios por categoría."
    "</p>",
    unsafe_allow_html=True
)

# Filtrar por tipo si hay selección
df_tipos_plot = df_tipos.copy()
if tipo_sel:
    df_tipos_plot = df_tipos_plot[df_tipos_plot["tipo"].isin(tipo_sel)]

col_t1, col_t2 = st.columns([1, 1])

with col_t1:
    # Pie chart
    fig_pie = px.pie(
        df_tipos_plot,
        names="tipo",
        values="cantidad",
        color_discrete_sequence=px.colors.qualitative.Vivid,
        hole=0.35,
    )
    fig_pie.update_traces(textinfo="percent+label", textposition="outside")
    fig_pie.update_layout(showlegend=False, margin={"t": 20, "b": 20})
    st.plotly_chart(fig_pie, use_container_width=True)

with col_t2:
    df_tipos_bar = df_tipos_plot.sort_values("cantidad", ascending=True)
    fig_bar_t = px.bar(
        df_tipos_bar,
        x="cantidad",
        y="tipo",
        orientation="h",
        text="cantidad",
        labels={"tipo": label("tipo"), "cantidad": label("cantidad")},
        color="cantidad",
        color_continuous_scale="Purples",
    )
    fig_bar_t.update_layout(coloraxis_showscale=False, yaxis_title="")
    fig_bar_t.update_traces(textposition="outside")
    st.plotly_chart(fig_bar_t, use_container_width=True)


# ════════════════════════════════════════════════════════════════════════════
# SECCIÓN 5 — TENDENCIA DE PUBLICACIONES
# ════════════════════════════════════════════════════════════════════════════
st.markdown("---")
st.subheader("📅 Tendencia de Publicaciones en el Tiempo")
st.markdown(
    "<p class='section-note'>"
    "Cantidad de anuncios según su fecha de primera publicación en Urbania. "
    "Permite ver en qué períodos hubo más actividad inmobiliaria."
    "</p>",
    unsafe_allow_html=True
)

df_meses_plot = df_meses.copy()
df_meses_plot["mes_dt"] = pd.to_datetime(df_meses_plot["mes"])
df_meses_plot = df_meses_plot.sort_values("mes_dt")

fig_time = px.area(
    df_meses_plot,
    x="mes_dt",
    y="cantidad",
    labels={"mes_dt": "Mes", "cantidad": label("cantidad")},
    color_discrete_sequence=["#FF4B4B"],
)
fig_time.update_layout(
    xaxis=dict(showgrid=False),
    yaxis=dict(showgrid=True, gridcolor="#333"),
    plot_bgcolor="rgba(0,0,0,0)",
)
fig_time.update_traces(line_width=2, fillcolor="rgba(255,75,75,0.2)")
st.plotly_chart(fig_time, use_container_width=True)


# ════════════════════════════════════════════════════════════════════════════
# SECCIÓN 6 — CARACTERÍSTICAS DE CASAS Y DEPARTAMENTOS
# ════════════════════════════════════════════════════════════════════════════
st.markdown("---")
st.subheader("🛏️ Características: Dormitorios y Baños")
st.markdown(
    "<p class='section-note'>"
    "Distribución de dormitorios y baños en anuncios de casas y departamentos únicamente."
    "</p>",
    unsafe_allow_html=True
)

col_d, col_b = st.columns(2)

with col_d:
    st.markdown("**Dormitorios**")
    df_dorm_plot = df_dorm[df_dorm["dormitorios"] <= 8].copy()
    df_dorm_plot["dormitorios"] = df_dorm_plot["dormitorios"].astype(str)
    fig_dorm = px.bar(
        df_dorm_plot,
        x="dormitorios",
        y="cantidad",
        text="cantidad",
        labels={"dormitorios": label("dormitorios"), "cantidad": label("cantidad")},
        color="cantidad",
        color_continuous_scale="Blues",
    )
    fig_dorm.update_layout(coloraxis_showscale=False)
    fig_dorm.update_traces(textposition="outside")
    st.plotly_chart(fig_dorm, use_container_width=True)

with col_b:
    st.markdown("**Baños**")
    df_ban_plot = df_ban[df_ban["banos"] <= 8].copy()
    df_ban_plot["banos"] = df_ban_plot["banos"].astype(str)
    fig_ban = px.bar(
        df_ban_plot,
        x="banos",
        y="cantidad",
        text="cantidad",
        labels={"banos": label("banos"), "cantidad": label("cantidad")},
        color="cantidad",
        color_continuous_scale="Greens",
    )
    fig_ban.update_layout(coloraxis_showscale=False)
    fig_ban.update_traces(textposition="outside")
    st.plotly_chart(fig_ban, use_container_width=True)


# ════════════════════════════════════════════════════════════════════════════
# SECCIÓN 7 — AMENIDADES MÁS OFRECIDAS
# ════════════════════════════════════════════════════════════════════════════
st.markdown("---")
st.subheader("🏊 Amenidades más Ofrecidas")
st.markdown(
    "<p class='section-note'>"
    "Características destacadas que los anunciantes mencionan con más frecuencia "
    "(proyectos y desarrollos inmobiliarios)."
    "</p>",
    unsafe_allow_html=True
)

df_amen_plot = df_amen.sort_values("cantidad", ascending=True)
fig_amen = px.bar(
    df_amen_plot,
    x="cantidad",
    y="amenidad",
    orientation="h",
    text="cantidad",
    labels={"amenidad": label("amenidad"), "cantidad": label("cantidad")},
    color="cantidad",
    color_continuous_scale="Oranges",
)
fig_amen.update_layout(coloraxis_showscale=False, yaxis_title="")
fig_amen.update_traces(textposition="outside")
st.plotly_chart(fig_amen, use_container_width=True)


# ── FOOTER ───────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    "> 🛡️ *Los datos de este dashboard son agregaciones y conteos calculados a partir de "
    "anuncios públicos de [urbania.com](https://urbania.com). "
    "No se redistribuyen datos individuales ni información de contacto de los anunciantes. "
    "Proyecto académico de portafolio — Diego Rivera.*"
)
