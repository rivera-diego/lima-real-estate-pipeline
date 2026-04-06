import json
import psycopg2

print("Conectando a la base de datos...")
try:
    conn = psycopg2.connect(
        dbname="urbania_db",
        user="diego",
        password="admin",
        host="127.0.0.1",
        port="5432"
    )
    conn.autocommit = True
    cursor = conn.cursor()
    print("Conexión lista. Leyendo el archivo JSONL...")

    ruta_archivo = "raw/postings_raw.jsonl"
    procesados = 0
    errores = 0

    with open(ruta_archivo, "r", encoding="utf-8") as f:
        for linea in f:
            try:
                anuncio = json.loads(linea)

                # ---- EXTRACCIÓN ----

                # datos del anunciante (puede ser inmobiliaria o persona natural)
                publisher = anuncio.get("publisher", {})
                pub_id = publisher.get("publisherId")
                pub_name = publisher.get("name")
                pub_type = publisher.get("publisherTypeId")

                # la ubicación viene anidada: location tiene el distrito, y parent tiene la ciudad/zona
                loc_info = anuncio.get("postingLocation", {}).get("location", {})
                distrito = loc_info.get("name")
                ciudad = loc_info.get("parent", {}).get("name") if loc_info.get("parent") else None

                # las coordenadas no siempre existen, muchos anuncios no las publican
                lat = None
                lon = None
                try:
                    geo = anuncio["postingLocation"]["postingGeolocation"]["geolocation"]
                    if geo:
                        lat = geo.get("latitude")
                        lon = geo.get("longitude")
                except (KeyError, TypeError):
                    pass  # si no hay coordenadas simplemente dejo lat/lon en None

                # los precios vienen en una lista porque un anuncio puede tener precio en soles Y en dólares
                precio_usd = None
                precio_soles = None
                operaciones = anuncio.get("priceOperationTypes", [])
                if operaciones:
                    for precio in operaciones[0].get("prices", []):
                        if precio.get("currency") == "USD":
                            precio_usd = precio.get("amount")
                        elif precio.get("currency") == "S/":
                            precio_soles = precio.get("amount")

                # las características vienen con códigos internos (CFT100 = área total, CFT2 = dormitorios, etc.)
                features = anuncio.get("mainFeatures", {})

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

                # ---- CARGA EN POSTGRESQL ----

                # primero inserto el anunciante
                # ON CONFLICT DO NOTHING para no romper nada si ya existe
                if pub_id:
                    cursor.execute("""
                        INSERT INTO dim_anunciante (publisher_id, name, publisher_type_id)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (publisher_id) DO NOTHING
                    """, (pub_id, pub_name, pub_type))

                # luego la ubicación — si ya existe el distrito, solo recupero su ID
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

                # finalmente la propiedad en la tabla de hechos
                # si el anuncio ya existe (mismo posting_id), actualizo el precio por si cambió
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
                            precio_usd = EXCLUDED.precio_usd,
                            precio_soles = EXCLUDED.precio_soles
                    """, (
                        posting_id, title, precio_usd, precio_soles, area_total,
                        area_techada, dormitorios, banios, cocheras, antiguedad,
                        pub_id, loc_id_bd, lat, lon, url_anuncio
                    ))

                procesados += 1
                if procesados % 1000 == 0:
                    print(f"  {procesados} propiedades cargadas...")

            except Exception as e:
                errores += 1
                # no rompo el loop por un error en una línea, sigo con la siguiente

    print(f"\nCarga terminada.")
    print(f"Propiedades cargadas: {procesados}")
    if errores > 0:
        print(f"Líneas con error ignoradas: {errores}")

except Exception as e:
    print(f"Error al conectar: {e}")
finally:
    if 'conn' in locals():
        cursor.close()
        conn.close()
