import streamlit as st
import pandas as pd
from datetime import date, datetime
from database.db_connection import get_connection
import traceback

# VALIDACIONES

MAX_CODIGO_LEN = 50
MAX_TEXT_LEN = 500

def sanitize_str(s: str):
    if s is None:
        return None
    s = str(s).strip()
    if len(s) > MAX_TEXT_LEN:
        return s[:MAX_TEXT_LEN]
    return s

def sanitize_codigo(s: str):
    if s is None:
        return None
    s = str(s).strip()
    if len(s) > MAX_CODIGO_LEN:
        s = s[:MAX_CODIGO_LEN]
    return s

def validar_fecha_not_past(fecha):
    # aquí decidimos: la fecha de la orden no puede ser mayor a hoy + 1 año ni menor a 2000
    if not isinstance(fecha, (date, datetime)):
        raise ValueError("Fecha inválida.")
    if fecha < date(2000,1,1):
        raise ValueError("Fecha demasiado antigua.")
    if fecha > date.today().replace(year=date.today().year+1):
        raise ValueError("Fecha fuera de rango.")
    return True

def validar_fecha_vencimiento(fecha_vencimiento, fecha_referencia=date.today()):
    if not isinstance(fecha_vencimiento, (date, datetime)):
        raise ValueError("Fecha de vencimiento inválida.")
    # Vencimiento no puede ser anterior a la fecha de referencia
    if fecha_vencimiento < fecha_referencia:
        raise ValueError("La fecha de vencimiento no puede ser anterior a la fecha de referencia.")
    return True

def validar_numero_positivo(val, nombre, allow_zero=False):
    try:
        if val is None:
            raise ValueError(f"{nombre} es requerido.")
        v = float(val)
    except Exception:
        raise ValueError(f"{nombre} debe ser numérico.")
    if allow_zero:
        if v < 0:
            raise ValueError(f"{nombre} no puede ser negativo.")
    else:
        if v <= 0:
            raise ValueError(f"{nombre} debe ser mayor que 0.")
    return True

def obtener_semana_iso(fecha):
    if isinstance(fecha, datetime):
        fecha = fecha.date()
    return fecha.isocalendar()[1]

# ---------------------------
# FUNCIONES DE BASE DE DATOS (con validaciones)
# ---------------------------

def obtener_lineas():
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT idLinea, nombreLinea FROM LineaProduccion ORDER BY nombreLinea;")
        lineas = cursor.fetchall()
    finally:
        conn.close()
    return lineas


def obtener_presentaciones_linea(idLinea):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT idPresentacion, nombrePresentacion
            FROM PresentacionProducto
            WHERE idLinea = %s
            ORDER BY nombrePresentacion
        """, (idLinea,))
        pres = cursor.fetchall()
    finally:
        conn.close()
    return pres


def codigo_orden_existe(codigoorden):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(1) FROM OrdenTrabajo WHERE codigoOrden = %s", (codigoorden,))
        res = cursor.fetchone()
        count = res[0] if res else 0
    finally:
        conn.close()
    return count > 0


def insertar_orden(codigoorden, fecha, semana, dia, turno, idLinea):
    """
    Inserta una orden con validaciones. Lanza ValueError si falla una validación.
    """
    # saneamiento
    codigoorden = sanitize_codigo(codigoorden)
    dia = sanitize_str(dia)
    turno = sanitize_str(turno)

    if not codigoorden:
        raise ValueError("El código de orden es obligatorio.")
    if len(codigoorden) == 0:
        raise ValueError("El código de orden no puede estar vacío.")
    if codigo_orden_existe(codigoorden):
        raise ValueError("Ya existe una orden con ese código. Use otro código.")

    # validar fecha
    validar_fecha_not_past(fecha)

    # validar semana coincide con fecha (estricto)
    semana_iso = obtener_semana_iso(fecha)
    if int(semana) != int(semana_iso):
        raise ValueError(f"La semana indicada ({semana}) no coincide con la semana ISO de la fecha ({semana_iso}).")

    # validar dia
    if not dia:
        raise ValueError("Día es obligatorio.")
    # turno valid
    if turno not in ["T1-8H","T2-8H","T3-8H"]:
        raise ValueError("Turno inválido.")

    # idLinea valid
    if not idLinea:
        raise ValueError("Debe seleccionar una línea de producción válida.")

    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO OrdenTrabajo (codigoOrden, fecha, semana, dia, turno, idLinea)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (codigoorden, fecha, semana, dia, turno, idLinea))
        conn.commit()
        # obtener id
        try:
            id_orden = cursor.lastrowid
        except Exception:
            # fallback: buscar por código (último)
            cursor.execute("SELECT idOrdenTrabajo FROM OrdenTrabajo WHERE codigoOrden = %s ORDER BY idOrdenTrabajo DESC LIMIT 1", (codigoorden,))
            r = cursor.fetchone()
            id_orden = r[0] if r else None
    except Exception as e:
        conn.rollback()
        raise
    finally:
        conn.close()
    return id_orden


def obtener_orden_por_id(idOrden):
    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT o.*, l.nombreLinea
            FROM OrdenTrabajo o
            LEFT JOIN LineaProduccion l ON o.idLinea = l.idLinea
            WHERE o.idOrdenTrabajo = %s
        """, (idOrden,))
        orden = cursor.fetchone()
    finally:
        conn.close()
    return orden


def actualizar_orden(idOrden, codigo, fecha, semana, dia, turno, idLinea):
    """
    Actualiza la orden con validaciones.
    """
    codigo = sanitize_codigo(codigo)
    dia = sanitize_str(dia)
    turno = sanitize_str(turno)

    if not idOrden:
        raise ValueError("ID de orden inválido.")
    if not codigo:
        raise ValueError("Código vacío.")
    validar_fecha_not_past(fecha)

    semana_iso = obtener_semana_iso(fecha)
    if int(semana) != int(semana_iso):
        raise ValueError(f"La semana indicada ({semana}) no coincide con la semana ISO de la fecha ({semana_iso}).")

    if turno not in ["T1-8H","T2-8H","T3-8H"]:
        raise ValueError("Turno inválido.")

    # evitar duplicar códigos al actualizar (excepto si es la misma orden)
    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT idOrdenTrabajo FROM OrdenTrabajo WHERE codigoOrden = %s", (codigo,))
        fila = cursor.fetchone()
        if fila and int(fila["idOrdenTrabajo"]) != int(idOrden):
            raise ValueError("El código de orden ya pertenece a otra orden.")
        cursor.execute("""
            UPDATE OrdenTrabajo
            SET codigoOrden = %s,
                fecha = %s,
                semana = %s,
                dia = %s,
                turno = %s,
                idLinea = %s
            WHERE idOrdenTrabajo = %s
        """, (codigo, fecha, semana, dia, turno, idLinea, idOrden))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def eliminar_orden(idOrden):
    """
    No permite eliminar una orden si existen detalles asociados.
    Debe eliminarse primero los detalles o crear un flujo de confirmación explícita.
    """
    if not idOrden:
        raise ValueError("ID de orden inválido para eliminar.")
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(1) FROM DetalleOrdenTrabajo WHERE idOrdenTrabajo = %s", (idOrden,))
        cnt = cursor.fetchone()[0]
        if cnt and int(cnt) > 0:
            raise ValueError("No se puede eliminar la orden: existen detalles asociados. Elimine primero los detalles.")
        cursor.execute("DELETE FROM OrdenTrabajo WHERE idOrdenTrabajo = %s", (idOrden,))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def insertar_detalle(idOrden, idPresentacion, receta, fechaVencimiento, lote,
                        observacion, rendimientoReceta, rendimientoCajasB,
                        produccionUnidades, produccionCajasB):
    """
    Inserta un detalle con validaciones estrictas.
    """
    # saneamiento
    receta = sanitize_str(receta)
    lote = sanitize_str(lote)
    observacion = sanitize_str(observacion)

    if not idOrden:
        raise ValueError("ID de orden inválido para el detalle.")
    if not idPresentacion:
        raise ValueError("Presentación inválida. Seleccione una presentación.")
    if not receta:
        raise ValueError("Receta es obligatoria.")
    if not lote:
        raise ValueError("Lote es obligatorio.")
    validar_fecha_vencimiento(fechaVencimiento, fecha_referencia=date.today())
    # rendimientos y producciones: exigimos > 0 para algunos
    validar_numero_positivo(rendimientoReceta, "Rendimiento Receta", allow_zero=False)
    validar_numero_positivo(produccionUnidades, "Producción Unidades", allow_zero=False)
    # permitir que rendimientoCajasB y produccionCajasB sean >=0 (no negativos)
    validar_numero_positivo(rendimientoCajasB, "Rendimiento Cajas B", allow_zero=True)
    validar_numero_positivo(produccionCajasB, "Producción Cajas B", allow_zero=True)

    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO DetalleOrdenTrabajo (
                idPresentacion, receta, fechaVencimiento, lote,
                observacion, rendimientoReceta, rendimientoCajasB,
                produccionUnidades, produccionCajasB, idOrdenTrabajo
            )
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            idPresentacion, receta, fechaVencimiento, lote,
            observacion, rendimientoReceta, rendimientoCajasB,
            produccionUnidades, produccionCajasB, idOrden
        ))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def obtener_ordenes():
    conn = get_connection()
    query = """
        SELECT 
            o.idOrdenTrabajo AS ID,
            o.codigoOrden,
            o.fecha,
            o.semana,
            o.dia,
            o.turno,
            l.nombreLinea AS Linea,
            o.idLinea
        FROM OrdenTrabajo o
        INNER JOIN LineaProduccion l ON o.idLinea = l.idLinea
        ORDER BY o.fecha DESC, o.idOrdenTrabajo DESC;
    """
    try:
        df = pd.read_sql(query, conn)
    finally:
        conn.close()
    return df


def obtener_detalles(idOrden):
    conn = get_connection()
    query = """
        SELECT 
            d.idDetalle,
            d.idPresentacion,
            p.nombrePresentacion AS Producto,
            d.receta AS Receta,
            d.lote AS Lote,
            d.fechaVencimiento AS FechaVencimiento,
            d.rendimientoReceta AS RendimientoReceta,
            d.rendimientoCajasB AS RendimientoCajasB,
            d.produccionUnidades AS ProduccionUnidades,
            d.produccionCajasB AS ProduccionCajasB,
            d.observacion AS Observacion
        FROM DetalleOrdenTrabajo d
        LEFT JOIN PresentacionProducto p 
            ON d.idPresentacion = p.idPresentacion
        WHERE d.idOrdenTrabajo = %s
        ORDER BY d.idDetalle;
    """
    try:
        df = pd.read_sql(query, conn, params=(idOrden,))
    finally:
        conn.close()
    return df


def actualizar_detalle(idDetalle, idPresentacion, receta, fechaVencimiento, lote,
                        observacion, rendimientoReceta, rendimientoCajasB,
                        produccionUnidades, produccionCajasB):
    # validaciones (similares a insertar_detalle)
    receta = sanitize_str(receta)
    lote = sanitize_str(lote)
    observacion = sanitize_str(observacion)

    if not idDetalle:
        raise ValueError("ID detalle inválido.")
    if not idPresentacion:
        raise ValueError("Presentación inválida.")
    if not receta:
        raise ValueError("Receta es obligatoria.")
    if not lote:
        raise ValueError("Lote es obligatorio.")
    validar_fecha_vencimiento(fechaVencimiento, fecha_referencia=date.today())
    validar_numero_positivo(rendimientoReceta, "Rendimiento Receta", allow_zero=False)
    validar_numero_positivo(produccionUnidades, "Producción Unidades", allow_zero=False)
    validar_numero_positivo(rendimientoCajasB, "Rendimiento Cajas B", allow_zero=True)
    validar_numero_positivo(produccionCajasB, "Producción Cajas B", allow_zero=True)

    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE DetalleOrdenTrabajo
            SET idPresentacion = %s,
                receta = %s,
                fechaVencimiento = %s,
                lote = %s,
                observacion = %s,
                rendimientoReceta = %s,
                rendimientoCajasB = %s,
                produccionUnidades = %s,
                produccionCajasB = %s
            WHERE idDetalle = %s
        """, (idPresentacion, receta, fechaVencimiento, lote,
                observacion, rendimientoReceta, rendimientoCajasB,
                produccionUnidades, produccionCajasB, idDetalle))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def eliminar_detalle(idDetalle):
    if not idDetalle:
        raise ValueError("ID detalle inválido para eliminar.")
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM DetalleOrdenTrabajo WHERE idDetalle = %s", (idDetalle,))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

# INTERFAZ STREAMLIT
def gestionar_ordenes():

    st.title("REGISTRO DE ÓRDENES DE PRODUCCIÓN - Gustossi S.R.L.")
    st.markdown("---")

    try:
        lineas = obtener_lineas()
    except Exception as e:
        st.error(f"Error cargando líneas: {e}")
        st.stop()

    if not lineas:
        st.warning("No existen líneas de producción registradas.")
        return

    menu = st.sidebar.radio("Menú de Órdenes", ["Registrar Nueva Orden", "Consultar Órdenes"])

    # REGISTRAR NUEVA ORDEN
    if menu == "Registrar Nueva Orden":

        st.subheader("Nueva Orden de Producción")
        linea_nombre = st.selectbox(
            "Línea de Producción",
            ["— Seleccionar Línea —"] + [l[1] for l in lineas]
        )

        if linea_nombre == "— Seleccionar Línea —":
            st.info("Seleccione una línea de producción para continuar.")
            return

        idLinea = next(l[0] for l in lineas if l[1] == linea_nombre)

        codigoorden = st.text_input("Código de Orden")
        codigoorden = sanitize_codigo(codigoorden)

        # Fecha y semana: asignamos la semana ISO por defecto y lo mostramos
        fecha = st.date_input("Fecha", value=date.today())
        try:
            validar_fecha_not_past(fecha)
        except Exception as e:
            st.error(f"Fecha inválida: {e}")
            return

        semana_iso = obtener_semana_iso(fecha)
        semana = st.number_input("Semana (ISO) — se ajusta a la fecha", min_value=1, max_value=53, value=semana_iso, step=1)
        # Forzamos coincidencia estricta: si usuario cambia, avisamos y corregimos al insertar
        if semana != semana_iso:
            st.warning(f"La semana seleccionada ({semana}) no coincide con la semana ISO de la fecha ({semana_iso}). Al guardar, se usará la semana correspondiente a la fecha ({semana_iso}).")

        dias_semana = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
        mapping = {
            "Monday": "Lunes",
            "Tuesday": "Martes",
            "Wednesday": "Miércoles",
            "Thursday": "Jueves",
            "Friday": "Viernes",
            "Saturday": "Sábado",
            "Sunday": "Domingo"
        }
        dia_default = mapping.get(fecha.strftime("%A"), "Lunes")
        dia = st.selectbox("Día", dias_semana, index=dias_semana.index(dia_default))

        turno = st.selectbox("Turno", ["T1-8H", "T2-8H", "T3-8H"])

        if st.button("Crear Orden"):
            try:
                if not codigoorden:
                    st.warning("Debe ingresar un código.")
                else:
                    # Forzamos semana correcta según fecha
                    semana_a_insertar = obtener_semana_iso(fecha)
                    if codigo_orden_existe(codigoorden):
                        st.error("Ya existe una orden con ese código. Cambie el código antes de crear.")
                    else:
                        id_orden = insertar_orden(codigoorden, fecha, semana_a_insertar, dia, turno, idLinea)
                        st.session_state["orden_activa"] = id_orden
                        st.session_state["codigo_activo"] = codigoorden
                        st.success(f"Orden {codigoorden} creada.")
                        st.experimental_rerun()
            except ValueError as ve:
                st.error(f"Validación: {ve}")
            except Exception as e:
                st.error(f"Error creando orden: {e}")
                st.write(traceback.format_exc())

        # FORMULARIO DE DETALLES (para la orden recién creada)
        if "orden_activa" in st.session_state:

            idOrden = st.session_state["orden_activa"]
            codigo_activo = st.session_state["codigo_activo"]

            st.markdown(f"### Agregar Productos — Orden {codigo_activo}")

            presentaciones = obtener_presentaciones_linea(idLinea)

            if not presentaciones:
                st.warning("No existen presentaciones para esta línea.")
                return

            opciones = {p[1]: p[0] for p in presentaciones}

            with st.form("detalle_form", clear_on_submit=True):
                present_sel = st.selectbox("Producto", list(opciones.keys()))
                idPresentacion = opciones[present_sel] if present_sel else None

                receta = st.text_input("Receta")
                lote = st.text_input("Lote")
                fechaVencimiento = st.date_input("Fecha de Vencimiento", value=date.today())

                rendimientoReceta = st.number_input("Rendimiento Receta", min_value=0.0, format="%.2f")
                rendimientoCajasB = st.number_input("Rendimiento Cajas B", min_value=0.0, format="%.2f")
                produccionUnidades = st.number_input("Producción Unidades", min_value=0.0, format="%.2f")
                produccionCajasB = st.number_input("Producción Cajas B", min_value=0.0, format="%.2f")

                observacion = st.text_area("Observaciones")

                agregar = st.form_submit_button("Agregar Detalle")

                if agregar:
                    try:
                        # Validaciones front
                        if not idPresentacion:
                            st.warning("Seleccione una presentación válida.")
                        else:
                            insertar_detalle(
                                idOrden, idPresentacion, receta, fechaVencimiento, lote,
                                observacion, rendimientoReceta, rendimientoCajasB,
                                produccionUnidades, produccionCajasB
                            )
                            st.success("Detalle agregado.")
                            st.experimental_rerun()
                    except ValueError as ve:
                        st.error(f"Validación: {ve}")
                    except Exception as e:
                        st.error(f"Error al insertar detalle: {e}")
                        st.write(traceback.format_exc())

            detalles_df = obtener_detalles(idOrden)

            if detalles_df.empty:
                st.info("No hay productos registrados.")
            else:
                st.dataframe(detalles_df, use_container_width=True)

    # CONSULTAR ÓRDENES
    elif menu == "Consultar Órdenes":

        st.subheader("Consultar Órdenes de Producción")
        st.markdown("---")

        try:
            df_ordenes = obtener_ordenes()
        except Exception as e:
            st.error(f"Error cargando órdenes: {e}")
            return

        if df_ordenes.empty:
            st.info("No hay órdenes registradas.")
            return

        df_ordenes["fecha"] = pd.to_datetime(df_ordenes["fecha"]).dt.date

        # FILTROS ORGANIZADOS
        col1, col2, col3 = st.columns(3)
        with col1:
            fecha_filtro = st.date_input("Fecha específica", value=date.today())
            usar_fecha = st.checkbox("Usar filtro de fecha", value=False)

        with col2:
            semana_filtro = st.number_input("Semana ISO", min_value=0, max_value=53, step=1, value=0)

        with col3:
            dia_filtro = st.selectbox(
                "Día",
                ["Todos", "Lunes", "Martes", "Miércoles",
                    "Jueves", "Viernes", "Sábado", "Domingo"]
            )

        col4, col5 = st.columns(2)
        with col4:
            turno_filtro = st.selectbox("Turno", ["Todos", "T1-8H", "T2-8H", "T3-8H"])

        with col5:
            linea_filtro = st.selectbox("Línea", ["Todas"] + [l[1] for l in lineas])

        # BUSCADOR
        codigo_buscar = st.text_input("Buscar por Código de Orden")

        # APLICAR FILTROS
        df_filtrado = df_ordenes.copy()

        if usar_fecha:
            df_filtrado = df_filtrado[df_filtrado["fecha"] == fecha_filtro]

        if semana_filtro != 0:
            df_filtrado = df_filtrado[df_filtrado["semana"] == semana_filtro]

        if dia_filtro != "Todos":
            df_filtrado = df_filtrado[df_filtrado["dia"].str.lower() == dia_filtro.lower()]

        if turno_filtro != "Todos":
            df_filtrado = df_filtrado[df_filtrado["turno"] == turno_filtro]

        if linea_filtro != "Todas":
            df_filtrado = df_filtrado[df_filtrado["Linea"] == linea_filtro]

        if codigo_buscar:
            df_filtrado = df_filtrado[df_filtrado["codigoOrden"].str.contains(codigo_buscar, case=False, na=False)]

        # RESULTADOS
        st.markdown("### Órdenes encontradas")

        if df_filtrado.empty:
            st.info("No se encontraron órdenes.")
            return

        st.dataframe(df_filtrado, use_container_width=True)

        st.markdown("### Detalle por orden (desplegar para ver / editar)")

        # Crear expanders por cada orden
        for _, row in df_filtrado.iterrows():
            idOrden = int(row["ID"])
            titulo = f"{row['codigoOrden']} — Semana {row['semana']} — {row['dia']} — {row['Linea']}"

            with st.expander(titulo, expanded=False):
                # Cargar datos completos de la orden
                try:
                    orden = obtener_orden_por_id(idOrden)
                except Exception as e:
                    st.error(f"Error cargando orden: {e}")
                    continue

                if not orden:
                    st.error("No se pudo cargar la orden desde la base de datos.")
                    continue

                st.write(f"**Código:** {orden.get('codigoOrden')}")
                st.write(f"**Fecha:** {orden.get('fecha')}")
                st.write(f"**Semana:** {orden.get('semana')}")
                st.write(f"**Día:** {orden.get('dia')}")
                st.write(f"**Turno:** {orden.get('turno')}")
                st.write(f"**Línea:** {orden.get('nombreLinea')}")

                st.markdown("---")

                # Detalles
                detalles_df = obtener_detalles(idOrden)

                if detalles_df.empty:
                    st.info("No hay detalles registrados para esta orden.")
                else:
                    # Mostrar cada detalle en su propio expander
                    for _, det in detalles_df.iterrows():
                        idDetalle = int(det["idDetalle"])
                        producto_nombre = det["Producto"]
                        with st.expander(f"Detalle {idDetalle} — {producto_nombre}", expanded=False):
                            st.write(f"Producto: {producto_nombre}")
                            st.write(f"Receta: {det['Receta']}")
                            st.write(f"Lote: {det['Lote']}")
                            st.write(f"Fecha Vencimiento: {det['FechaVencimiento']}")
                            st.write(f"Rend. Receta: {det['RendimientoReceta']}")
                            st.write(f"Rend. Cajas B: {det['RendimientoCajasB']}")
                            st.write(f"Prod. Unidades: {det['ProduccionUnidades']}")
                            st.write(f"Prod. Cajas B: {det['ProduccionCajasB']}")
                            st.write(f"Observación: {det['Observacion']}")

                            col_a, col_b = st.columns(2)
                            with col_a:
                                if st.button(f"Eliminar detalle {idDetalle}", key=f"elim_det_{idDetalle}"):
                                    try:
                                        eliminar_detalle(idDetalle)
                                        st.success("Detalle eliminado.")
                                        st.experimental_rerun()
                                    except ValueError as ve:
                                        st.error(f"Validación: {ve}")
                                    except Exception as e:
                                        st.error(f"Error al eliminar detalle: {e}")
                                        st.write(traceback.format_exc())

                            with col_b:
                                # Formulario para editar detalle
                                if st.button(f"Editar detalle {idDetalle}", key=f"edit_det_btn_{idDetalle}"):
                                    try:
                                        presentaciones = obtener_presentaciones_linea(orden.get("idLinea"))
                                        opciones_pres = {p[1]: p[0] for p in presentaciones} if presentaciones else {}

                                        with st.form(f"form_edit_det_{idDetalle}", clear_on_submit=False):
                                            pres_list = list(opciones_pres.keys()) if opciones_pres else []
                                            try:
                                                idx_default = pres_list.index(det["Producto"]) if det["Producto"] in pres_list else 0
                                            except Exception:
                                                idx_default = 0
                                            pres_sel = st.selectbox("Producto", pres_list, index=idx_default, key=f"pres_{idDetalle}")
                                            idPresentacion_new = opciones_pres.get(pres_sel) if pres_sel else det["idPresentacion"]

                                            receta_new = st.text_input("Receta", value=det["Receta"], key=f"rec_{idDetalle}")
                                            lote_new = st.text_input("Lote", value=det["Lote"], key=f"lot_{idDetalle}")
                                            try:
                                                fecha_venc_new = st.date_input("Fecha Vencimiento", value=pd.to_datetime(det["FechaVencimiento"]).date(), key=f"fv_{idDetalle}")
                                            except Exception:
                                                fecha_venc_new = st.date_input("Fecha Vencimiento", value=date.today(), key=f"fv_{idDetalle}")
                                            rendimientoRec_new = st.number_input("Rendimiento Receta", min_value=0.0, value=float(det["RendimientoReceta"] or 0), key=f"rr_{idDetalle}")
                                            rendimientoCajasB_new = st.number_input("Rendimiento Cajas B", min_value=0.0, value=float(det["RendimientoCajasB"] or 0), key=f"rcb_{idDetalle}")
                                            prodUni_new = st.number_input("Producción Unidades", min_value=0.0, value=float(det["ProduccionUnidades"] or 0), key=f"pu_{idDetalle}")
                                            prodCajas_new = st.number_input("Producción Cajas B", min_value=0.0, value=float(det["ProduccionCajasB"] or 0), key=f"pcb_{idDetalle}")
                                            observ_new = st.text_area("Observaciones", value=det["Observacion"] or "", key=f"obs_{idDetalle}")

                                            guardar_det = st.form_submit_button("Guardar cambios detalle", key=f"save_det_{idDetalle}")
                                            if guardar_det:
                                                try:
                                                    actualizar_detalle(
                                                        idDetalle,
                                                        idPresentacion_new,
                                                        receta_new,
                                                        fecha_venc_new,
                                                        lote_new,
                                                        observ_new,
                                                        rendimientoRec_new,
                                                        rendimientoCajasB_new,
                                                        prodUni_new,
                                                        prodCajas_new
                                                    )
                                                    st.success("Detalle actualizado.")
                                                    st.experimental_rerun()
                                                except ValueError as ve:
                                                    st.error(f"Validación: {ve}")
                                                except Exception as e:
                                                    st.error(f"Error al actualizar detalle: {e}")
                                                    st.write(traceback.format_exc())
                                    except Exception as e:
                                        st.error(f"Error preparando edición: {e}")
                                        st.write(traceback.format_exc())

                st.markdown("---")

                # Formulario para agregar nuevo detalle
                st.markdown("#### Agregar nuevo detalle a esta orden")
                presentaciones_linea = obtener_presentaciones_linea(orden.get("idLinea"))
                opciones_new = {p[1]: p[0] for p in presentaciones_linea} if presentaciones_linea else {}

                with st.form(f"form_agregar_detalle_{idOrden}", clear_on_submit=True):
                    if opciones_new:
                        pres_new_sel = st.selectbox("Producto", list(opciones_new.keys()), key=f"pres_new_{idOrden}")
                        idPresentacion_new = opciones_new.get(pres_new_sel)
                    else:
                        st.warning("No hay presentaciones registradas para la línea; no puede agregar detalles.")
                        pres_new_sel = None
                        idPresentacion_new = None

                    receta_new = st.text_input("Receta", key=f"rec_new_{idOrden}")
                    lote_new = st.text_input("Lote", key=f"lot_new_{idOrden}")
                    fechaVenc_new = st.date_input("Fecha de Vencimiento", value=date.today(), key=f"fv_new_{idOrden}")

                    rendimientoReceta_new = st.number_input("Rendimiento Receta", min_value=0.0, key=f"rr_new_{idOrden}")
                    rendimientoCajasB_new = st.number_input("Rendimiento Cajas B", min_value=0.0, key=f"rcb_new_{idOrden}")
                    produccionUnidades_new = st.number_input("Producción Unidades", min_value=0.0, key=f"pu_new_{idOrden}")
                    produccionCajasB_new = st.number_input("Producción Cajas B", min_value=0.0, key=f"pcb_new_{idOrden}")

                    observacion_new = st.text_area("Observaciones", key=f"obs_new_{idOrden}")

                    agregar_detalle_btn = st.form_submit_button("Agregar detalle a la orden")
                    if agregar_detalle_btn:
                        try:
                            if not idPresentacion_new:
                                st.warning("Seleccione una presentación válida.")
                            else:
                                insertar_detalle(
                                    idOrden,
                                    idPresentacion_new,
                                    receta_new,
                                    fechaVenc_new,
                                    lote_new,
                                    observacion_new,
                                    rendimientoReceta_new,
                                    rendimientoCajasB_new,
                                    produccionUnidades_new,
                                    produccionCajasB_new
                                )
                                st.success("Detalle agregado a la orden.")
                                st.experimental_rerun()
                        except ValueError as ve:
                            st.error(f"Validación: {ve}")
                        except Exception as e:
                            st.error(f"Error agregando detalle: {e}")
                            st.write(traceback.format_exc())

                st.markdown("---")

                # Edicion orden de produccion
                st.markdown("#### Editar datos de la orden")
                with st.form(f"form_edit_orden_{idOrden}", clear_on_submit=False):
                    codigo_new = st.text_input("Código de Orden", value=orden.get("codigoOrden"))
                    try:
                        fecha_new = st.date_input("Fecha", value=pd.to_datetime(orden.get("fecha")).date())
                    except Exception:
                        fecha_new = st.date_input("Fecha", value=date.today())
                    semana_new = st.number_input("Semana", min_value=1, max_value=53, value=int(orden.get("semana") or 1))
                    dias_semana_local = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
                    try:
                        idx_d = dias_semana_local.index(orden.get("dia"))
                    except Exception:
                        idx_d = 0
                    dia_new = st.selectbox("Día", dias_semana_local, index=idx_d)
                    turno_new = st.selectbox("Turno", ["T1-8H", "T2-8H", "T3-8H"], index=["T1-8H","T2-8H","T3-8H"].index(orden.get("turno")) if orden.get("turno") in ["T1-8H","T2-8H","T3-8H"] else 0)

                    # línea editable: mostrar lista de líneas para posible cambio
                    lineas_dict = {l[1]: l[0] for l in lineas}
                    try:
                        idx_linea = list(lineas_dict.keys()).index(orden.get("nombreLinea"))
                    except Exception:
                        idx_linea = 0
                    linea_sel = st.selectbox("Línea", list(lineas_dict.keys()), index=idx_linea)
                    idLinea_new = lineas_dict.get(linea_sel)

                    guardar_orden_btn = st.form_submit_button("Guardar cambios orden")
                    if guardar_orden_btn:
                        try:
                            # Forzamos semana correcta según fecha_new
                            semana_a_usar = obtener_semana_iso(fecha_new)
                            actualizar_orden(idOrden, codigo_new, fecha_new, semana_a_usar, dia_new, turno_new, idLinea_new)
                            st.success("Orden actualizada.")
                            st.experimental_rerun()
                        except ValueError as ve:
                            st.error(f"Validación: {ve}")
                        except Exception as e:
                            st.error(f"Error al actualizar orden: {e}")
                            st.write(traceback.format_exc())

                st.markdown("---")

                # Eliminar orden de produccion (solo si no tiene detalles)
                if st.button(f"Eliminar ORDEN {orden.get('codigoOrden')}", key=f"elim_ord_{idOrden}"):
                    try:
                        eliminar_orden(idOrden)
                        st.success("Orden eliminada correctamente.")
                        st.experimental_rerun()
                    except ValueError as ve:
                        st.error(f"Validación: {ve}")
                    except Exception as e:
                        st.error(f"Error al eliminar orden: {e}")
                        st.write(traceback.format_exc())

        st.markdown("---")


if __name__ == "__main__":
    gestionar_ordenes()