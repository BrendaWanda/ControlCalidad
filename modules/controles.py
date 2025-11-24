# modules/controles.py
import streamlit as st
import pandas as pd
from datetime import datetime
from database.db_connection import get_connection

# funciones de tus módulos existentes (ajusta import si tu estructura es distinta)
from modules.ordenes import obtener_ordenes, obtener_detalles, obtener_orden_por_id
from modules.estandares import obtener_parametros_por_presentacion, obtener_lineas_produccion

# -------------------------
# UTIL: obtener tipos por línea desde BD
# -------------------------
def obtener_tipos_por_linea_db(id_linea):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT idTipoControl, nombreTipo, descripcion
        FROM tipocontrol
        WHERE idLinea = %s
        ORDER BY nombreTipo
    """, (id_linea,))
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows


# -------------------------
# Registro principal: Orden -> Detalle -> Presentación (del detalle) -> Tipo -> Parámetros
# -------------------------
def registrar_control():
    st.title("Registro de Controles de Calidad")
    st.markdown("---")

    # 1) Seleccionar orden
    df_ordenes = obtener_ordenes()
    if df_ordenes.empty:
        st.info("No hay órdenes registradas.")
        return

    df_ordenes["fecha"] = pd.to_datetime(df_ordenes["fecha"]).dt.date
    opciones = ["— Seleccionar Orden —"] + [
        f"{row.codigoOrden} | {row.Linea} | {row.fecha} | ID:{int(row.ID)}"
        for _, row in df_ordenes.iterrows()
    ]
    sel = st.selectbox("Seleccione la Orden de Trabajo", opciones)
    if sel == "— Seleccionar Orden —":
        st.stop()

    try:
        id_orden = int(sel.split("ID:")[-1])
    except Exception:
        st.error("No se pudo interpretar la orden seleccionada.")
        st.stop()

    orden = obtener_orden_por_id(id_orden)
    if not orden:
        st.error("No se pudo cargar la orden desde la base de datos.")
        st.stop()

    st.markdown(f"### Orden: **{orden.get('codigoOrden')}** — Línea: **{orden.get('nombreLinea')}**")

    # 2) Detalles de la orden -> elegir detalle (OPCIÓN B)
    detalles_df = obtener_detalles(id_orden)
    if detalles_df.empty:
        st.info("La orden seleccionada no tiene detalles (productos).")
        st.stop()

    opciones_det = ["— Seleccionar Detalle —"] + [
        f"Detalle {int(r['idDetalle'])} — {r['Producto']} (Lote: {r['Lote']})"
        for _, r in detalles_df.iterrows()
    ]
    sel_det = st.selectbox("Seleccione Detalle de la Orden", opciones_det)
    if sel_det == "— Seleccionar Detalle —":
        st.stop()

    id_detalle = int(sel_det.split("—")[0].replace("Detalle", "").strip())
    fila_det = detalles_df[detalles_df["idDetalle"] == id_detalle].iloc[0]

    # 3) Presentación (OPCIÓN 1: usar la presentación del detalle)
    id_presentacion = int(fila_det["idPresentacion"]) if pd.notna(fila_det["idPresentacion"]) else None
    nombre_presentacion = fila_det["Producto"] if pd.notna(fila_det["Producto"]) else "Presentación desconocida"

    if not id_presentacion:
        st.warning("El detalle seleccionado no tiene presentación asociada. Verifique el detalle.")
        st.stop()
    st.write(f"**Presentación (del detalle):** {nombre_presentacion}")

    # 4) Línea (tomada desde la orden)
    id_linea = int(orden.get("idLinea"))
    lineas = obtener_lineas_produccion()
    nombre_linea = next((l[1] for l in lineas if l[0] == id_linea), "Línea desconocida")
    st.write(f"**Línea:** {nombre_linea}")

    # 5) Tipo de control (filtrado por línea)
    tipos = obtener_tipos_por_linea_db(id_linea)
    if not tipos:
        st.warning("No hay tipos de control configurados para esta línea.")
        st.stop()

    tipos_dict = {t["nombreTipo"]: t["idTipoControl"] for t in tipos}
    tipo_sel = st.selectbox("Seleccione Tipo de Control", ["— Seleccionar Tipo —"] + list(tipos_dict.keys()))
    if tipo_sel == "— Seleccionar Tipo —":
        st.stop()
    id_tipo = tipos_dict[tipo_sel]

    # 6) Cargar parámetros para la presentación y filtrar por tipo
    df_params = obtener_parametros_por_presentacion(id_presentacion)
    # Filtrar por idTipoControl
    if "idTipoControl" in df_params.columns:
        df_params = df_params[df_params["idTipoControl"] == id_tipo]
    if df_params.empty:
        st.warning("No hay parámetros configurados para esta presentación y tipo de control.")
        st.stop()

    st.subheader("Parámetros a registrar")
    st.markdown("Ingrese los valores medidos. Se mostrarán los límites permitidos si existen.")

    # 7) Datos generales
    col_a, col_b = st.columns([3, 1])
    with col_a:
        sabor = st.text_input("Sabor (opcional) — se guardará como idPresentacion / nombre")
        observaciones = st.text_area("Observaciones generales (opcional)")
    with col_b:
        fecha_control = st.date_input("Fecha", datetime.now().date())
        hora_control = st.time_input("Hora", datetime.now().time())

    # Preparar inputs para parámetros
    entradas = {}
    for _, row in df_params.iterrows():
        id_param = int(row["idParametro"])
        nombre = row["nombreParametro"]
        tipo_param = row["tipoParametro"]
        lim_inf = row["limiteInferior"] if "limiteInferior" in row else None
        lim_sup = row["limiteSuperior"] if "limiteSuperior" in row else None
        unidad = row.get("unidadMedida", "") if "unidadMedida" in row else ""

        key = f"param_{id_param}"
        if tipo_param == "numerico":
            label = f"{nombre} ({unidad}) — Rango: {lim_inf if pd.notna(lim_inf) else '-'} a {lim_sup if pd.notna(lim_sup) else '-'}"
            valor = st.number_input(label, step=0.01, format="%.4f", key=key)
            entradas[id_param] = {"tipo": "numerico", "valor": float(valor), "lim_inf": lim_inf, "lim_sup": lim_sup, "nombre": nombre}
        else:
            checked = st.checkbox(f"{nombre} (check)", key=key)
            entradas[id_param] = {"tipo": "check", "valor": 1 if checked else 0, "lim_inf": None, "lim_sup": None, "nombre": nombre}

    # 8) Guardar controles y generar alertas si aplica
    if st.button("Guardar Control", use_container_width=True):
        # obtener id_usuario desde sesión (varias posibilidades)
        id_usuario = None
        if "usuario" in st.session_state:
            usr = st.session_state["usuario"]
            if isinstance(usr, dict):
                id_usuario = usr.get("idUsuario") or usr.get("id") or usr.get("id_user")
            else:
                id_usuario = getattr(usr, "idUsuario", None) or getattr(usr, "id", None)
        if not id_usuario:
            id_usuario = st.session_state.get("usuario_id") or st.session_state.get("idUsuario")

        if not id_usuario:
            st.error("No se detectó usuario logueado. Inicie sesión para registrar controles.")
            st.stop()

        fecha_hora = datetime.combine(fecha_control, hora_control)

        conn = get_connection()
        cursor = conn.cursor()
        try:
            for id_param, data in entradas.items():
                # Intento insertar con campos extendidos (idOrdenTrabajo, idPresentacion).
                try:
                    cursor.execute("""
                        INSERT INTO controlcalidad
                        (fechaControl, resultado, observaciones, idUsuario, idParametro, idTipoControl,
                         idLinea, idDetalle, idOrdenTrabajo, idPresentacion, sabor)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        fecha_hora,
                        data["valor"],
                        observaciones,
                        id_usuario,
                        id_param,
                        id_tipo,
                        id_linea,
                        id_detalle,
                        id_orden,
                        id_presentacion,
                        nombre_presentacion  # opcional redundante; la BD también tiene idPresentacion
                    ))
                except Exception:
                    # Si tu tabla no tiene los campos idOrdenTrabajo/idPresentacion/sabor, intentamos insert sin ellos
                    cursor.execute("""
                        INSERT INTO controlcalidad
                        (fechaControl, resultado, observaciones, idUsuario, idParametro, idTipoControl,
                         idLinea, idDetalle, sabor)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        fecha_hora,
                        data["valor"],
                        observaciones,
                        id_usuario,
                        id_param,
                        id_tipo,
                        id_linea,
                        id_detalle,
                        nombre_presentacion
                    ))
                conn.commit()
                id_control = cursor.lastrowid

                # Generar alerta si es numérico y fuera de rango
                if data["tipo"] == "numerico":
                    lim_inf = data["lim_inf"]
                    lim_sup = data["lim_sup"]
                    valor = data["valor"]
                    fuera = False
                    # comprobar límites solo si existen valores numéricos definidos
                    if pd.notna(lim_inf) and pd.notna(lim_sup):
                        try:
                            if (valor < float(lim_inf)) or (valor > float(lim_sup)):
                                fuera = True
                        except Exception:
                            fuera = False

                    if fuera:
                        descripcion = (f"Parametro '{data['nombre']}' fuera de rango: {valor} "
                                       f"(permitido {lim_inf} - {lim_sup}) — Orden {orden.get('codigoOrden')}")
                        # insertar alerta (con campos extendidos)
                        try:
                            cursor.execute("""
                                INSERT INTO alerta
                                (tipoAlerta, descripcion, idControl, idOrdenTrabajo, idLinea, idParametro, idPresentacion,
                                 valorFuera, limiteInferior, limiteSuperior, fechaAlerta, estado)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), %s)
                            """, (
                                "Fuera de Rango",
                                descripcion,
                                id_control,
                                id_orden,
                                id_linea,
                                id_param,
                                id_presentacion,
                                valor,
                                lim_inf,
                                lim_sup,
                                "pendiente"
                            ))
                        except Exception:
                            # si tabla alerta no tiene todos los campos, insertar los esenciales
                            cursor.execute("""
                                INSERT INTO alerta
                                (tipoAlerta, descripcion, idControl)
                                VALUES (%s, %s, %s)
                            """, ("Fuera de Rango", descripcion, id_control))
                        conn.commit()

            st.success("Controles registrados correctamente.")
            st.rerun()

        except Exception as e:
            st.error(f"Error al guardar controles: {e}")
        finally:
            cursor.close()
            conn.close()


# -------------------------
# Buscar y mostrar controles (vista tipo 'Consultar Órdenes')
# -------------------------
def buscar_controles():
    st.title("Búsqueda de Registros de Control")
    st.markdown("---")

    conn = get_connection()
    try:
        query = """
            SELECT
                c.idControl,
                c.fechaControl,
                o.codigoOrden,
                l.nombreLinea,
                p.nombrePresentacion,
                tc.nombreTipo AS tipoControl,
                par.nombreParametro,
                c.resultado,
                c.observaciones,
                c.idUsuario,
                c.idDetalle,
                c.idOrdenTrabajo
            FROM controlcalidad c
            LEFT JOIN ordentrabajo o ON c.idOrdenTrabajo = o.idOrdenTrabajo
            LEFT JOIN lineaproduccion l ON c.idLinea = l.idLinea
            LEFT JOIN presentacionproducto p ON c.idPresentacion = p.idPresentacion
            LEFT JOIN tipocontrol tc ON c.idTipoControl = tc.idTipoControl
            LEFT JOIN parametrocalidad par ON c.idParametro = par.idParametro
            ORDER BY c.fechaControl DESC
        """
        df = pd.read_sql(query, conn)

        if df.empty:
            st.info("No se encontraron registros de control.")
            return

        # filtros
        col1, col2, col3 = st.columns(3)
        with col1:
            fecha = st.date_input("Fecha específica (opcional)", value=None)
            usar_fecha = st.checkbox("Usar filtro de fecha", value=False)
        with col2:
            linea_opts = ["Todas"] + sorted(df["nombreLinea"].dropna().unique().tolist())
            linea_sel = st.selectbox("Línea", linea_opts)
        with col3:
            orden_opts = ["Todas"] + sorted(df["codigoOrden"].dropna().unique().tolist())
            orden_sel = st.selectbox("Orden", orden_opts)

        parametro_opts = ["Todos"] + sorted(df["nombreParametro"].dropna().unique().tolist())
        parametro_sel = st.selectbox("Parámetro", parametro_opts)

        df_fil = df.copy()
        if usar_fecha and fecha:
            df_fil = df_fil[pd.to_datetime(df_fil["fechaControl"]).dt.date == fecha]
        if linea_sel != "Todas":
            df_fil = df_fil[df_fil["nombreLinea"] == linea_sel]
        if orden_sel != "Todas":
            df_fil = df_fil[df_fil["codigoOrden"] == orden_sel]
        if parametro_sel != "Todos":
            df_fil = df_fil[df_fil["nombreParametro"] == parametro_sel]

        st.dataframe(df_fil, use_container_width=True)

    finally:
        conn.close()

# -------------------------
# Historial / ver alertas
# -------------------------
def ver_alertas():
    st.title("Historial de Alertas")
    st.markdown("---")
    conn = get_connection()
    try:
        df = pd.read_sql("""
            SELECT a.idAlerta, a.tipoAlerta, a.descripcion, a.fechaAlerta, a.estado,
                   a.idControl, a.idOrdenTrabajo, a.idLinea, a.idParametro, a.idPresentacion,
                   a.valorFuera, a.limiteInferior, a.limiteSuperior,
                   o.codigoOrden, l.nombreLinea, p.nombrePresentacion, par.nombreParametro
            FROM alerta a
            LEFT JOIN ordentrabajo o ON a.idOrdenTrabajo = o.idOrdenTrabajo
            LEFT JOIN lineaproduccion l ON a.idLinea = l.idLinea
            LEFT JOIN presentacionproducto p ON a.idPresentacion = p.idPresentacion
            LEFT JOIN parametrocalidad par ON a.idParametro = par.idParametro
            ORDER BY a.fechaAlerta DESC
        """, conn)

        if df.empty:
            st.info("No hay alertas registradas.")
            return

        # filtros
        col1, col2 = st.columns(2)
        with col1:
            estado_sel = st.selectbox("Estado", ["Todos"] + sorted(df["estado"].dropna().unique().tolist()))
        with col2:
            linea_sel = st.selectbox("Línea", ["Todas"] + sorted(df["nombreLinea"].dropna().unique().tolist()))

        df_fil = df.copy()
        if estado_sel != "Todos":
            df_fil = df_fil[df_fil["estado"] == estado_sel]
        if linea_sel != "Todas":
            df_fil = df_fil[df_fil["nombreLinea"] == linea_sel]

        st.dataframe(df_fil, use_container_width=True)

        # confirmar alerta
        id_alerta = st.text_input("ID de alerta para confirmar")
        if st.button("Confirmar alerta"):
            try:
                cursor = conn.cursor()
                cursor.execute("UPDATE alerta SET estado = 'confirmada' WHERE idAlerta = %s", (int(id_alerta),))
                conn.commit()
                st.success(f"Alerta {id_alerta} marcada como confirmada.")
                st.rerun()
            except Exception as e:
                st.error(f"Error confirmando alerta: {e}")

    finally:
        conn.close()


# -------------------------
# Entrypoint para integrar en tu app.py
# -------------------------
def app_controles():
    menu = st.sidebar.radio("Control de Calidad", ["Registrar Control", "Buscar Registros", "Ver Alertas"])
    if menu == "Registrar Control":
        registrar_control()
    elif menu == "Buscar Registros":
        buscar_controles()
    else:
        ver_alertas()


if __name__ == "__main__":
    app_controles()