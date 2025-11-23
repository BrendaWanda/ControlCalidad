# modules/controles.py
import streamlit as st
import pandas as pd
from datetime import datetime
from database.db_connection import get_connection

# funciones de tus módulos existentes
from modules.ordenes import obtener_ordenes, obtener_detalles, obtener_orden_por_id
from modules.estandares import obtener_presentaciones_por_linea, obtener_parametros_por_presentacion, obtener_lineas_produccion

# ---------------------------------------------------------
# UTIL: obtener tipos por línea (desde BD)
# ---------------------------------------------------------
def obtener_tipos_por_linea_db(id_linea):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT idTipoControl, nombreTipo, descripcion
        FROM tipocontrol
        WHERE idLinea = %s
        ORDER BY nombreTipo
    """, (id_linea,))
    res = cursor.fetchall()
    cursor.close()
    conn.close()
    return res

# ---------------------------------------------------------
# FLUJO PRINCIPAL: Orden -> Detalle -> Presentación (del detalle) -> Tipo -> Parámetros
# ---------------------------------------------------------
def registrar_control():
    st.title("Registro de Controles de Calidad")
    st.markdown("---")

    # 1) Seleccionar ORDEN
    df_ordenes = obtener_ordenes()
    if df_ordenes.empty:
        st.info("No hay órdenes registradas.")
        return

    # formatear lista de órdenes
    df_ordenes["fecha"] = pd.to_datetime(df_ordenes["fecha"]).dt.date
    opciones_orden = ["— Seleccionar Orden —"] + [
        f"{row.codigoOrden} | {row.Linea} | {row.fecha} | ID:{int(row.ID)}"
        for _, row in df_ordenes.iterrows()
    ]
    sel_orden = st.selectbox("Seleccione una Orden de Trabajo", opciones_orden)

    if sel_orden == "— Seleccionar Orden —":
        st.info("Seleccione una orden para continuar.")
        return

    # extraer idOrden
    try:
        id_orden = int(sel_orden.split("ID:")[-1])
    except Exception:
        st.error("No se pudo interpretar la orden seleccionada.")
        return

    orden = obtener_orden_por_id(id_orden)
    if not orden:
        st.error("No se pudo cargar la orden seleccionada desde la base de datos.")
        return

    st.markdown(f"### Orden: **{orden.get('codigoOrden')}** — Línea: **{orden.get('nombreLinea')}**")

    # 2) Listar DETALLES de la orden (para elegir el detalle específico)
    detalles_df = obtener_detalles(id_orden)
    if detalles_df.empty:
        st.info("Esta orden no tiene detalles/productos asociados.")
        return

    opciones_det = ["— Seleccionar Detalle —"] + [
        f"Detalle {int(r['idDetalle'])} — {r['Producto']} (Lote: {r['Lote']})"
        for _, r in detalles_df.iterrows()
    ]
    sel_detalle = st.selectbox("Seleccione Detalle de Orden", opciones_det)

    if sel_detalle == "— Seleccionar Detalle —":
        return

    id_detalle = int(sel_detalle.split(" — ")[0].replace("Detalle ", ""))
    fila_det = detalles_df[detalles_df["idDetalle"] == id_detalle].iloc[0]

    # 3) La presentación será la del detalle seleccionado (Opción 1)
    id_presentacion_det = int(fila_det["idPresentacion"]) if pd.notna(fila_det["idPresentacion"]) else None
    presentacion_nombre = fila_det["Producto"] if pd.notna(fila_det["Producto"]) else "Presentación desconocida"

    st.markdown(f"**Detalle seleccionado:** {presentacion_nombre} — (idPresentacion: {id_presentacion_det})")
    if not id_presentacion_det:
        st.warning("El detalle seleccionado no tiene presentación asociada. No se pueden cargar parámetros.")
        return

    # 4) Obtener línea de la orden (ya viene en orden). Permitimos mostrarla pero no es obligatoria cambiar.
    id_linea = int(orden.get("idLinea"))
    # obtener nombre de línea para mostrar
    lineas = obtener_lineas_produccion()
    linea_nombre = next((l[1] for l in lineas if l[0] == id_linea), "Línea desconocida")
    st.write(f"**Línea asociada a la orden:** {linea_nombre}")

    # 5) Seleccionar TIPO DE CONTROL (filtrado por la línea)
    tipos = obtener_tipos_por_linea_db(id_linea)
    if not tipos:
        st.warning("No hay tipos de control configurados para esta línea.")
        return

    tipos_dict = {t["nombreTipo"]: t["idTipoControl"] for t in tipos}
    tipo_sel = st.selectbox("Seleccione Tipo de Control", ["— Seleccionar Tipo —"] + list(tipos_dict.keys()))
    if tipo_sel == "— Seleccionar Tipo —":
        return
    id_tipo = tipos_dict[tipo_sel]

    # 6) Presentación: usamos SOLO la del detalle seleccionado (Opción 1)
    st.write("**Presentación (tomada del detalle seleccionado)**")
    st.write(f"- {presentacion_nombre}")

    # 7) Cargar parámetros para la PRESENTACIÓN y filtrar por tipo de control
    df_params = obtener_parametros_por_presentacion(id_presentacion_det)
    df_params_filtrados = df_params[df_params["idTipoControl"] == id_tipo]
    if df_params_filtrados.empty:
        st.warning("No hay parámetros configurados para esta presentación y tipo de control.")
        return

    st.subheader("Parámetros a registrar")
    st.markdown("Ingrese los valores medidos. Se mostrarán los límites permitidos (si aplica).")

    # entrada de metadatos comunes
    col1, col2 = st.columns([3,1])
    with col1:
        sabor = st.text_input("Sabor (opcional)")
        observaciones = st.text_area("Observaciones generales (opcional)")
    with col2:
        fecha_control = st.date_input("Fecha", value=datetime.now().date())
        hora_control = st.time_input("Hora", value=datetime.now().time())

    # recolectar entradas por parámetro
    entradas = {}
    for _, row in df_params_filtrados.iterrows():
        id_param = int(row["idParametro"])
        nombre = row["nombreParametro"]
        tipo = row["tipoParametro"]
        lim_inf = row["limiteInferior"]
        lim_sup = row["limiteSuperior"]
        unidad = row.get("unidadMedida", "") if "unidadMedida" in row else ""

        key = f"param_{id_param}"
        if tipo == "numerico":
            label = f"{nombre} ({unidad}) — Rango: {lim_inf if pd.notna(lim_inf) else '-'} a {lim_sup if pd.notna(lim_sup) else '-'}"
            # number_input siempre devuelve 0.0 por default; usuario debe ingresar valor
            valor = st.number_input(label, step=0.01, format="%.4f", key=key)
            entradas[id_param] = {"tipo": "numerico", "valor": float(valor), "lim_inf": lim_inf, "lim_sup": lim_sup, "nombre": nombre}
        else:
            checked = st.checkbox(f"{nombre} (check)", key=key)
            entradas[id_param] = {"tipo": "check", "valor": 1 if checked else 0, "lim_inf": None, "lim_sup": None, "nombre": nombre}

    # Botón guardar
    if st.button("Guardar Control", use_container_width=True):
        # usuario
        id_usuario = None
        # intenamos varias formas de obtener idUsuario desde session_state
        if "usuario" in st.session_state:
            usr = st.session_state["usuario"]
            if isinstance(usr, dict):
                id_usuario = usr.get("idUsuario") or usr.get("id")
            else:
                # si guardas usuario como objeto con atributo idUsuario
                id_usuario = getattr(usr, "idUsuario", None) or getattr(usr, "id", None)
        # fallback: clave plana
        if not id_usuario:
            id_usuario = st.session_state.get("idUsuario") or st.session_state.get("usuario_id")

        if not id_usuario:
            st.warning("No se detectó usuario logueado. Inicia sesión para registrar controles.")
            return

        conn = get_connection()
        cursor = conn.cursor()
        try:
            inserted = []
            for id_param, data in entradas.items():
                fecha_hora = datetime.combine(fecha_control, hora_control)

                # insertar en controlcalidad
                cursor.execute("""
                    INSERT INTO controlcalidad
                        (fechaControl, resultado, observaciones, idUsuario, idParametro, idTipoControl, idLinea, idDetalle, sabor)
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
                    sabor
                ))
                conn.commit()
                id_control = cursor.lastrowid
                inserted.append((id_control, id_param, data))

                # generar alerta si numérico y fuera de rango
                if data["tipo"] == "numerico":
                    lim_inf = data["lim_inf"]
                    lim_sup = data["lim_sup"]
                    valor = data["valor"]
                    fuera = False
                    if pd.notna(lim_inf) and pd.notna(lim_sup):
                        if (valor < float(lim_inf)) or (valor > float(lim_sup)):
                            fuera = True
                    # si fuera => insertar alerta
                    if fuera:
                        descripcion = f"Valor fuera de rango para {data['nombre']}: {valor} (permitido {lim_inf} - {lim_sup}) — Orden {orden.get('codigoOrden')}"
                        fecha_alerta = datetime.now()
                        cursor.execute("""
                            INSERT INTO alerta
                            (tipoAlerta, descripcion, idControl, idParametro, idLinea, idDetalle, valorFuera, limiteInferior, limiteSuperior, fechaAlerta, estado)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """, (
                            "Fuera de Rango",
                            descripcion,
                            id_control,
                            id_param,
                            id_linea,
                            id_detalle,
                            valor,
                            data["lim_inf"],
                            data["lim_sup"],
                            fecha_alerta,
                            "pendiente"
                        ))
                        conn.commit()

            st.success("Controles registrados correctamente.")
            st.experimental_rerun()

        except Exception as e:
            st.error(f"Error al guardar controles: {e}")
        finally:
            cursor.close()
            conn.close()

# ---------------------------------------------------------
# HISTORIAL DE ALERTAS
# ---------------------------------------------------------
def ver_alertas():
    st.title("Historial de Alertas")
    st.markdown("---")
    conn = get_connection()
    try:
        df = pd.read_sql("""
            SELECT a.idAlerta, a.tipoAlerta, a.descripcion, a.fechaAlerta, a.estado,
                   a.idControl, a.idParametro, a.idLinea, a.idDetalle, a.valorFuera, a.limiteInferior, a.limiteSuperior,
                   c.fechaControl, o.codigoOrden, l.nombreLinea, p.nombrePresentacion, par.nombreParametro
            FROM alerta a
            LEFT JOIN controlcalidad c ON a.idControl = c.idControl
            LEFT JOIN detalleordentrabajo d ON a.idDetalle = d.idDetalle
            LEFT JOIN ordentrabajo o ON d.idOrdenTrabajo = o.idOrdenTrabajo
            LEFT JOIN lineaproduccion l ON a.idLinea = l.idLinea
            LEFT JOIN presentacionproducto p ON d.idPresentacion = p.idPresentacion
            LEFT JOIN parametrocalidad par ON a.idParametro = par.idParametro
            ORDER BY a.fechaAlerta DESC
        """, conn)
        if df.empty:
            st.info("No hay alertas registradas.")
            return

        # filtros
        col1, col2 = st.columns(2)
        with col1:
            estado_f = st.selectbox("Estado", ["Todos"] + sorted(df["estado"].dropna().unique().tolist()))
        with col2:
            linea_f = st.selectbox("Línea", ["Todas"] + sorted(df["nombreLinea"].dropna().unique().tolist()))

        df_fil = df.copy()
        if estado_f != "Todos":
            df_fil = df_fil[df_fil["estado"] == estado_f]
        if linea_f != "Todas":
            df_fil = df_fil[df_fil["nombreLinea"] == linea_f]

        st.dataframe(df_fil, use_container_width=True)

        # marcar alerta como confirmada
        sel = st.text_input("Marcar alerta (ingrese idAlerta) como confirmada")
        if st.button("Confirmar alerta"):
            try:
                id_alerta = int(sel)
                cursor = conn.cursor()
                cursor.execute("UPDATE alerta SET estado = 'confirmada' WHERE idAlerta = %s", (id_alerta,))
                conn.commit()
                st.success(f"Alerta {id_alerta} marcada como confirmada.")
                st.experimental_rerun()
            except Exception as ex:
                st.error(f"Error marcando alerta: {ex}")

    finally:
        conn.close()

# ---------------------------------------------------------
# ENTRY POINT (pestañas)
# ---------------------------------------------------------
def app_controles():
    menu = st.sidebar.radio("Control de Calidad", ["Registrar Control", "Ver Alertas"])
    if menu == "Registrar Control":
        registrar_control()
    else:
        ver_alertas()

if __name__ == "__main__":
    app_controles()
