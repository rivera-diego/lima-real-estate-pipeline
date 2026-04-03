# 🏠 Pipeline de Análisis del Mercado Inmobiliario — Lima, Perú

> **Pipeline de datos end-to-end**: desde la recolección automatizada de anuncios inmobiliarios públicos hasta un análisis exploratorio con visualizaciones y hallazgos de negocio. Proyecto de portafolio de Ingeniería y Análisis de Datos.

---

## 🧭 ¿Por qué este proyecto?

El mercado inmobiliario de Lima es uno de los más activos de Latinoamérica, pero sus datos no están disponibles en ningún dataset público estructurado. Para construir un análisis real — no con datos de Kaggle, sino con datos del mercado peruano actual — diseñé un pipeline de datos completo que va desde la recolección automatizada hasta los hallazgos de negocio.

El objetivo del proyecto tiene dos niveles:
1. **Técnico**: construir un pipeline ETL de producción (extracción → transformación → almacenamiento → análisis).
2. **Analítico**: responder preguntas concretas sobre el mercado inmobiliario limeño: ¿Cuáles son los distritos más caros? ¿Cómo está distribuida la oferta geográficamente? ¿Los precios publicados son confiables?

---

## ⚙️ El Pipeline — Arquitectura completa

```
┌─────────────────┐     ┌──────────────────┐     ┌──────────────────┐     ┌───────────────────┐
│  Fuente pública │     │  Extracción       │     │  Transformación  │     │  Almacenamiento   │
│  (HTML público) │────▶│  Python +         │────▶│  ETL + Calidad  │────▶│  PostgreSQL 18    │
│  ~944 páginas   │     │  requests         │     │  de datos (IQR)  │     │  Star Schema      │
└─────────────────┘     └──────────────────┘     └──────────────────┘     └───────────────────┘
                                                                                     │
                                                                          ┌──────────▼──────────┐
                                                                          │  Análisis & EDA     │
                                                                          │  Pandas + Seaborn   │
                                                                          │  + Folium (mapa)    │
                                                                          └─────────────────────┘
```

### Fase 1 — Extracción (Bronze Layer)

El primer desafío fue obtener los datos. La API interna de la plataforma (`/rplis-api/postings`) estaba protegida por mecanismos anti-bot que bloqueaban cualquier cliente automatizado.

La solución fue analizar en profundidad cómo el sitio carga sus datos antes de escribir una sola línea de código. Al tratarse de una aplicación con renderizado del lado del servidor, los datos de los listados viajan serializados en el propio HTML de la respuesta, antes de que el JavaScript del cliente los procese.

Este enfoque es cualitativamente distinto al web scraping tradicional basado en selectores CSS o XPath, que depende de la estructura visual del HTML y se rompe ante cualquier cambio de diseño. En este caso, los datos se interceptan **a nivel de la capa de estado de la aplicación** — estructurados, completos y listos para ser parseados — sin depender de la disposición de los elementos en la página ni de interacciones con el DOM.

**El reto de extracción del JSON**: el JSON embebido en el HTML está seguido de código JavaScript adicional, lo que hace que una expresión regular simple falle. La solución fue un algoritmo de **balanceo de llaves** — contar la profundidad de apertura y cierre de `{}` para identificar el límite exacto del objeto JSON, en lugar de buscar un patrón de texto.

**Comportamiento anti-detección**:
- Delay aleatorio de **2.5 a 5.0 segundos** entre cada request para simular navegación humana.
- Deduplicación por `postingId` en cada corrida, haciendo el proceso reanudable.
- Manejo explícito de errores HTTP (403, 429, timeouts) con reintentos progresivos.

**Límite práctico descubierto**: la plataforma tiene ~28,314 anuncios disponibles (~944 páginas × 30 anuncios), pero el ordenamiento por "relevancia" comienza a reciclar anuncios después de la página 668. El límite real de registros únicos es **~19,500**.

**Formato de almacenamiento intermedio**: JSONL (JSON Lines) — un anuncio completo en formato JSON por línea. Cada anuncio tiene ~53 campos anidados que incluyen precios en dos monedas, características de la propiedad, datos del anunciante, geolocalización y más.

---

### Fase 2 — Transformación y Calidad de Datos (Silver Layer)

El JSON crudo tiene una estructura profundamente anidada que necesita ser aplanada y normalizada para ser analizable.

**Aplanamiento de estructuras complejas**:
Los precios vienen como una lista de objetos `{ currency, amount }`. Una propiedad puede tener precio en soles Y en dólares simultáneamente. El ETL itera sobre todos los precios para capturar ambas monedas correctamente, en lugar de asumir una posición fija.

Las características de la propiedad (m², dormitorios, baños, estacionamientos) se identifican con códigos internos (`CFT100`, `CFT2`, `CFT3`...) que se mapean a columnas con nombres legibles.

**Calidad de datos con IQR**:
Al explorar los datos, se encontraron precios anómalos: propiedades con precio `0`, con `1 sol`, o con miles de millones de soles (errores de digitación de las inmobiliarias). En lugar de eliminar estos registros —lo que comprometería la integridad del dataset original— se implementó una estrategia de **marcado con bandera**:

1. Se calcularon los cuartiles Q1 y Q3 del precio en soles (excluyendo ceros).
2. Se aplicó el método IQR estándar: límite superior = Q3 + 1.5 × (Q3 - Q1) ≈ **S/ 4,079,283**.
3. Se agregó la columna `es_valido BOOLEAN` a la tabla de hechos.
4. Los outliers se marcan con `es_valido = FALSE` sin borrarlos.
5. Todas las consultas analíticas usan `WHERE es_valido = TRUE`.

Esto preserva los datos originales y hace el proceso auditable.

**Resultado**:
| Estado | Registros | % |
|---|---|---|
| Válidos para análisis | 17,292 | 88.7% |
| Outliers marcados | 2,200 | 11.3% |
| **Total en base de datos** | **19,492** | 100% |

---

### Fase 3 — Almacenamiento (Star Schema en PostgreSQL)

Los datos se almacenan en un modelo dimensional (**Star Schema**) en PostgreSQL 18:

```
dim_anunciante ──┐
                 ├──▶ fact_propiedades
dim_ubicacion  ──┘
```

- **`dim_anunciante`**: inmobiliarias y personas naturales que publican los anuncios.
- **`dim_ubicacion`**: jerarquía de ubicación (distrito → urbanización específica).
- **`fact_propiedades`**: tabla de hechos con precios, características, coordenadas, y la columna `es_valido`.

La carga usa **UPSERT** (`INSERT ... ON CONFLICT DO UPDATE`): si el script se corre múltiples veces, los registros existentes se actualizan con los datos más recientes en lugar de duplicarse.

---

### Fase 4 — Análisis Exploratorio (EDA)

El análisis se realizó en dos capas:

**SQL directo en DBeaver** (exploración inicial):
- Precios máximos y mínimos por distrito con `JOIN` entre tablas.
- Promedio limpio con filtro `es_valido`.
- Ranking de anunciantes por volumen de propiedades publicadas.
- Cálculo de percentiles para detectar outliers (IQR).

**Jupyter Notebook** (`analisis/analisis_urbania.ipynb`):
Conexión a PostgreSQL vía `SQLAlchemy` + `pd.read_sql_query()`, que ejecuta el triple JOIN del modelo estrella y carga el resultado en un DataFrame Pandas para análisis y visualización.

---

## 📊 Hallazgos principales

### Hallazgo 1: La Molina es el distrito más caro — no Miraflores

| Distrito | Precio Promedio |
|---|---|
| 🥇 La Molina | S/ 2,058,105 |
| 🥈 San Isidro | S/ 1,622,430 |
| 🥉 Santa María del Mar | S/ 1,618,000 |
| Miraflores | ~S/ 1,300,000 |

La Molina supera a Miraflores porque concentra casas y terrenos grandes, mientras que Miraflores tiene más departamentos de lujo a menor precio por unidad.

### Hallazgo 2: Brecha de precios de 10x entre distritos

Los distritos más económicos son Huacho (S/ 204,600) e Independencia (S/ 280,375). La brecha entre La Molina y Huacho es de **10x**, reflejando una desigualdad marcada en el mercado inmobiliario limeño.

### Hallazgo 3: El promedio engaña — la mediana dice la verdad

| Métrica | Valor |
|---|---|
| Promedio (con outliers) | S/ 4,219,638 |
| Promedio (limpio, IQR) | S/ 1,707,789 |
| **Mediana** | **S/ 868,515** |

La distribución de precios está fuertemente sesgada a la derecha. La mediana (S/ 868K) representa mejor al comprador típico que el promedio (S/ 1.7M). Usar el promedio como referencia de mercado es estadísticamente engañoso.

### Hallazgo 4: La oferta se concentra en Lima centro-sur

El mapa geográfico muestra una alta densidad de anuncios en el eje Miraflores–Surco–La Molina, con disminución progresiva hacia la periferia norte y este. 1,799 propiedades (9.2%) no pudieron graficarse por carecer de coordenadas en el anuncio original.

---

## 🛠️ Stack técnico

| Capa | Tecnología |
|---|---|
| Lenguaje | Python 3.14 |
| Recolección | `requests` |
| Almacenamiento | PostgreSQL 18, modelo dimensional (Star Schema) |
| Conexión Python↔DB | `psycopg2-binary`, `SQLAlchemy` |
| Transformación / ETL | Python puro (sin frameworks) |
| Análisis | `pandas` |
| Visualización | `matplotlib`, `seaborn`, `folium` |
| Notebook | Jupyter / VS Code `.ipynb` |
| Entorno | CachyOS (Arch Linux), venv |

---

## 📁 Estructura del repositorio

```
urbania_datos/
├── analisis/
│   └── analisis_urbania.ipynb   # Notebook EDA completo con 4 hallazgos
├── load_db.py                   # Script ETL: JSONL → PostgreSQL (con UPSERT)
├── schema.sql                   # Definición del Star Schema en PostgreSQL
└── README.md
```

> ⚠️ **Nota sobre los datos**: Los datos provienen de páginas de resultados públicas de una plataforma inmobiliaria peruana. Los datos crudos y el script de recolección **no se incluyen en este repositorio** en cumplimiento de los términos de servicio de la plataforma. El repositorio contiene únicamente el código de transformación, almacenamiento y análisis.

---

## 🚀 Cómo reproducir el análisis

### Requisitos

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install pandas matplotlib seaborn sqlalchemy psycopg2-binary folium jupyter
```

### Base de datos

Crea una base de datos PostgreSQL y ejecuta el schema:

```bash
createdb urbania_db
psql -d urbania_db -f schema.sql
```

Carga tus datos con:

```bash
python3 load_db.py
```

### Análisis

```bash
jupyter notebook analisis/analisis_urbania.ipynb
```

---

## 🧠 Lo que apliqué en este proyecto

- **Análisis de estructura de datos en la web**: identificar dónde y cómo se almacenan los datos antes de iniciar la extracción.
- **Algoritmos de parsing**: balanceo de delimitadores para extraer JSON de texto mezclado con JavaScript.
- **Modelado dimensional**: diseño de Star Schema con separación de hechos y dimensiones.
- **Calidad de datos**: método IQR para detección estadística de outliers + reglas de negocio, sin borrar datos originales.
- **ETL con UPSERT**: pipelines reanudables e idempotentes.
- **EDA narrativo**: hallazgos con contexto de negocio, diferencia entre promedio y mediana, análisis geográfico.

---

## 👤 Autor

**Diego** — Estudiante de Ingeniería de Sistemas (UTP, 10° ciclo, décimo superior)
Orientado a Ingeniería de Datos y Análisis de Datos.

📎 LinkedIn: *(agregar URL)*
📎 GitHub: *(agregar URL)*
