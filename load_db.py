import json
import psycopg2

print("Iniciando conexión a PostgreSQL...")
try:
    # Nos conectamos a la base de datos local
    conn = psycopg2.connect(
        dbname="urbania_db",
        user="diego",
        password="admin",
        host="127.0.0.1",
        port="5432"
    )
    # Autocommit activado para que cada ejecución se guarde sola
    conn.autocommit = True
    cursor = conn.cursor()
    print("Conexión exitosa. Comenzando a leer datos...")

    ruta_archivo = "raw/postings_raw.jsonl"

    procesados = 0
    errores = 0

    with open(ruta_archivo, "r", encoding="utf-8") as f:
        for linea in f:
            try:
                anuncio = json.loads(linea)

                # ==========================================
                # 1. LIMPIEZA DE DATOS (Transformación)
                # ==========================================

                # A. Extraer Anunciante
                publisher = anuncio.get("publisher", {})
                pub_id = publisher.get("publisherId")
                pub_name = publisher.get("name")
                pub_type = publisher.get("publisherTypeId")

                # B. Extraer Ubicación (Distrito)
                loc_info = anuncio.get("postingLocation", {}).get("location", {})
                distrito = loc_info.get("name")
                ciudad = loc_info.get("parent", {}).get("name") if loc_info.get("parent") else None

                # C. Extraer Coordenadas de forma segura (Como en script.py)
                lat = None
                lon = None
                try:
                    geo = anuncio["postingLocation"]["postingGeolocation"]["geolocation"]
                    if geo:
                        lat = geo.get("latitude")
                        lon = geo.get("longitude")
                except (KeyError, TypeError):
                    pass

                # D. Extraer Precios (Soles y Dólares si hay)
                precio_usd = None
                precio_soles = None
                operaciones = anuncio.get("priceOperationTypes", [])
                if operaciones:
                    for precio in operaciones[0].get("prices", []):
                        if precio.get("currency") == "USD":
                            precio_usd = precio.get("amount")
                        elif precio.get("currency") == "S/":
                            precio_soles = precio.get("amount")

                # E. Extraer Características (CFT...)
                features = anuncio.get("mainFeatures", {})

                # Función auxiliar para sacar números de los textos ("5", "120")
                def extraer_numero(cft_clave):
                    val = features.get(cft_clave, {}).get("value")
                    try:
                        return float(val) if val else None
                    except ValueError:
                        return None

                area_total = extraer_numero("CFT100")
                area_techada = extraer_numero("CFT101")
                dormitorios = int(extraer_numero("CFT2")) if extraer_numero("CFT2") is not None else None
                banios = int(extraer_numero("CFT3")) if extraer_numero("CFT3") is not None else None
                cocheras = int(extraer_numero("CFT7")) if extraer_numero("CFT7") is not None else None
                antiguedad = int(extraer_numero("CFT20")) if extraer_numero("CFT20") is not None else None

                posting_id = anuncio.get("postingId")
                title = anuncio.get("title")
                url_anuncio = anuncio.get("url")

                # ==========================================
                # 2. INSERCIÓN EN POSTGRESQL (Load)
                # ==========================================

                # 2A. Insertar Dimension Anunciante
                # ON CONFLICT DO NOTHING sirve para ignorar silenciosamente si el anunciante ya existe
                if pub_id:
                    cursor.execute("""
                        INSERT INTO dim_anunciante (publisher_id, name, publisher_type_id)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (publisher_id) DO NOTHING
                    """, (pub_id, pub_name, pub_type))

                # 2B. Insertar Dimension Ubicacion y obtener su ID de vuelta
                # Si el distrito ya existe, agarramos su ID. Si no, lo inserta y nos da el nuevo ID.
                loc_id_bd = None
                if distrito:
                    cursor.execute("""
                        WITH insertado AS (
                            INSERT INTO dim_ubicacion (distrito, ciudad)
                            VALUES (%s, %s)
                            ON CONFLICT (distrito) DO NOTHING
                            RETURNING location_id
                        )
                        SELECT location_id FROM insertado
                        UNION ALL
                        SELECT location_id FROM dim_ubicacion WHERE distrito = %s
                        LIMIT 1;
                    """, (distrito, ciudad, distrito))

                    resultado = cursor.fetchone()
                    if resultado:
                        loc_id_bd = resultado[0]

                # 2C. Insertar Tabla de Hechos
                if posting_id:
                    cursor.execute("""
                        INSERT INTO fact_propiedades (
                            posting_id, title, precio_usd, precio_soles, area_total,
                            area_techada, dormitorios, banios, cocheras, antiguedad,
                            publisher_id, location_id, latitud, longitud, url
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                        )
                        ON CONFLICT (posting_id) DO UPDATE SET
                            precio_usd = EXCLUDED.precio_usd,   -- Actualizamos info vital si el anuncio cambió de precio a futuro
                            precio_soles = EXCLUDED.precio_soles
                    """, (
                        posting_id, title, precio_usd, precio_soles, area_total,
                        area_techada, dormitorios, banios, cocheras, antiguedad,
                        pub_id, loc_id_bd, lat, lon, url_anuncio
                    ))

                procesados += 1
                if procesados % 1000 == 0:
                    print(f"Propiedades guardadas: {procesados}...")

            except Exception as e:
                errores += 1
                # print(f"Error procesando una línea: {e}")

    print("\n¡Carga finalizada con éxito!")
    print(f"Total procesados: {procesados}")
    if errores > 0:
        print(f"Alertas de datos rotos ignoradas: {errores}")

except Exception as e:
    print(f"Error fatal: {e}")
finally:
    # Cerrar conexión
    if 'conn' in locals():
        cursor.close()
        conn.close()
