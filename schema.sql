-- ============================================================
-- Urbania Lima — Esquema de base de datos (Star Schema)
-- PostgreSQL 18+
-- ============================================================

-- Dimensión: Anunciantes (inmobiliarias y personas naturales)
CREATE TABLE IF NOT EXISTS dim_anunciante (
    publisher_id     VARCHAR(50)  PRIMARY KEY,
    name             VARCHAR(255),
    publisher_type_id VARCHAR(50)
);

-- Dimensión: Ubicaciones (jerarquía Distrito → Urbanización)
-- Nota: en el JSON de Urbania, "ciudad" corresponde al distrito real
-- y "distrito" corresponde a la urbanización específica.
CREATE TABLE IF NOT EXISTS dim_ubicacion (
    location_id  SERIAL       PRIMARY KEY,
    distrito     VARCHAR(100) UNIQUE,   -- Urbanización (Armendáriz, Higuereta...)
    ciudad       VARCHAR(100)           -- Distrito real (Miraflores, La Molina...)
);

-- Tabla de hechos: Propiedades en venta
CREATE TABLE IF NOT EXISTS fact_propiedades (
    posting_id    VARCHAR(50)       PRIMARY KEY,
    title         TEXT,
    precio_usd    NUMERIC,
    precio_soles  NUMERIC,
    area_total    NUMERIC,
    area_techada  NUMERIC,
    dormitorios   INTEGER,
    banios        INTEGER,
    cocheras      INTEGER,
    antiguedad    INTEGER,
    publisher_id  VARCHAR(50)       REFERENCES dim_anunciante(publisher_id),
    location_id   INTEGER           REFERENCES dim_ubicacion(location_id),
    latitud       DOUBLE PRECISION,
    longitud      DOUBLE PRECISION,
    url           TEXT,
    es_valido     BOOLEAN           DEFAULT TRUE,  -- FALSE = outlier detectado por IQR
    created_at    TIMESTAMP         DEFAULT CURRENT_TIMESTAMP
);
