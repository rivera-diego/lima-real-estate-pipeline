## Plan: Pipeline Urbania 5000 Registros

Objetivo: pasar de una extracción única de una página a un pipeline reproducible de adquisición, normalización y carga de datos inmobiliarios con control de calidad, enfocado en un proyecto de portafolio de ciencia de datos.

**Steps**
1. Auditoría técnica inicial del extractor actual en /home/diego/Escritorio/urbania_datos/urbania.py para confirmar supuestos de origen de datos, fragilidad del patrón de extracción y falta de paginación. Esta etapa define los requisitos mínimos del nuevo extractor.
2. Descubrimiento de estrategia de paginación/fetch incremental desde la web de Urbania (inspección de tráfico de red en navegador) para identificar endpoint o parámetros de página/cursor reutilizables. Este paso bloquea la implementación de recolección masiva.
3. Diseño del esquema canónico del dataset final usando los campos presentes en /home/diego/Escritorio/urbania_datos/data_urbania.json: identificadores, precios, ubicación, características, fechas y metadata del anunciante. Definir explícitamente tipos, nulos permitidos y reglas de coerción.
4. Diseño de normalización y deduplicación con llave primaria de negocio (postingId) y reglas para campos anidados (precios por moneda, features CFT, fotos, ubicación jerárquica). Esta etapa puede avanzar en paralelo con pruebas de captura de páginas adicionales.
5. Diseño del almacenamiento y carga incremental a base de datos para MVP de portafolio:
   - Opción recomendada: PostgreSQL para modelo relacional y consultas analíticas.
   - Opción rápida: SQLite para validar pipeline local.
   - Definir estrategia UPSERT para evitar duplicados y conservar cambios por fecha de modificación.
6. Diseño de observabilidad y resiliencia operativa: reintentos con backoff, timeout, delays aleatorios, logging estructurado por corrida y métricas clave (requests exitosos, anuncios nuevos, anuncios actualizados, tasa de error).
7. Plan de validación de calidad de datos previo a carga: completitud por columna, rangos válidos de precio y coordenadas, consistencia de moneda, detección de outliers y reporte QA por ejecución.
8. Definición de meta de adquisición de 5000 registros por lotes: ejecutar corridas segmentadas por páginas/zonas, persistir crudo y transformado, y detener automáticamente al alcanzar objetivo o agotar resultados sin novedad.
9. Entregables de portafolio: dataset limpio, diccionario de datos, notebook de EDA, consultas SQL de negocio y narrativa de arquitectura/limitaciones/ética de scraping.

**Relevant files**
- /home/diego/Escritorio/urbania_datos/urbania.py — extractor actual basado en requests + regex de estado precargado.
- /home/diego/Escritorio/urbania_datos/data_urbania.json — muestra real de estructura y campos a normalizar.

**Verification**
1. Verificar que la estrategia de paginación descubierta devuelve páginas distintas sin duplicar IDs en una muestra de prueba.
2. Validar que el esquema final parsea correctamente al menos 3 páginas consecutivas sin errores de tipado.
3. Confirmar deduplicación: una misma publicación no debe generar filas repetidas tras múltiples corridas.
4. Confirmar que el objetivo de 5000 registros se alcanza con integridad referencial y sin errores críticos de QA.
5. Ejecutar un chequeo manual de una muestra aleatoria comparando DB vs anuncio web para consistencia.

**Decisions**
- Incluido: diseño de pipeline ETL para scraping responsable y dataset analítico.
- Excluido por ahora: despliegue cloud, orquestación compleja y dashboard productivo.
- Supuesto operativo: uso con fines de portafolio y cumplimiento de términos de uso del sitio.

**Further Considerations**
1. Decidir nivel de complejidad inicial: MVP local rápido (SQLite) o base sólida relacional (PostgreSQL).
2. Definir granularidad de captura: una sola categoría inicial o múltiples categorías/zonas desde el inicio.
3. Definir política de refresco: corrida única para hito de 5000 o ingestión incremental diaria/semanal.
