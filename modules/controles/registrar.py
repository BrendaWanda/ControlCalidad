import streamlit as st
import pandas as pd
from datetime import datetime
from .utils import get_conn, insert_control_record, save_alert, get_user_id_from_session
from modules.ordenes import obtener_ordenes, obtener_detalles, obtener_orden_por_id
from modules.estandares import obtener_parametros_por_presentacion, obtener_lineas_produccion

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

    st.subheader(f"Orden: {orden.get('codigoOrden')} — Línea: {orden.get('nombreLinea')}")

    # 2) Detalle (producto) dentro de la orden
    detalles_df = obtener_detalles(id_orden)
    if detalles_df.empty:
        st.info("La orden no contiene detalles (productos).")
        st.stop()
    opciones_det = ["— Seleccionar Detalle —"] + [
        f"Detalle {int(r['idDetalle'])} — {r['Producto']} (Lote: {r['Lote']})" for _, r in detalles_df.iterrows()
    ]
    sel_det = st.selectbox("Seleccione Detalle de la Orden", opciones_det)
    if sel_det == "— Seleccionar Detalle —":
        st.stop()
    id_detalle = int(sel_det.split("—")[0].replace("Detalle", "").strip())
    fila_det = detalles_df[detalles_df["idDetalle"] == id_detalle].iloc[0]

    # 3) Presentación y línea
    id_presentacion = int(fila_det["idPresentacion"])
    nombre_presentacion = fila_det["Producto"]
    id_linea = int(orden.get("idLinea"))
    st.write(f"Presentación seleccionada: **{nombre_presentacion}**")
    st.write(f"Línea: **{orden.get('nombreLinea')}**")

    # 4) Tipo de control (filtrado por línea)
    conn = get_conn()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT idTipoControl, nombreTipo FROM tipocontrol WHERE idLinea = %s ORDER BY nombreTipo", (id_linea,))
    tipos_control = cur.fetchall()
    cur.close()
    conn.close()
    if not tipos_control:
        st.warning("No hay tipos de control configurados para esta línea.")
        st.stop()
    tipos_dict = {t["nombreTipo"]: t["idTipoControl"] for t in tipos_control}
    tipo_sel = st.selectbox("Seleccione Tipo de Control", ["— Seleccionar Tipo —"] + list(tipos_dict.keys()))
    if tipo_sel == "— Seleccionar Tipo —":
        st.stop()
    id_tipo = tipos_dict[tipo_sel]

    # 5) Parámetros para la presentación
    df_params = obtener_parametros_por_presentacion(id_presentacion)
    if "idTipoControl" in df_params.columns:
        df_params = df_params[df_params["idTipoControl"] == id_tipo]
    if df_params.empty:
        st.warning("No hay parámetros asignados a esta presentación para el tipo seleccionado.")
        st.stop()

    st.subheader("Parámetros a registrar")
    col_a, col_b = st.columns([3,1])
    with col_a:
        observaciones = st.text_area("Observaciones (opcional)")
    with col_b:
        fecha_control = st.date_input("Fecha", datetime.now().date())
        hora_control = st.time_input("Hora", datetime.now().time())

    entradas = {}
    for _, row in df_params.iterrows():
        id_param = int(row["idParametro"])
        nombre = row["nombreParametro"]
        tipo_param = row["tipoParametro"]
        lim_inf = row.get("limiteInferior")
        lim_sup = row.get("limiteSuperior")
        unidad = row.get("unidadMedida", "")
        if tipo_param == "numerico":
            label = f"{nombre} ({unidad}) — Rango: {lim_inf if pd.notna(lim_inf) else '-'} a {lim_sup if pd.notna(lim_sup) else '-'}"
            valor = st.number_input(label, step=0.01, key=f"param_{id_param}")
            entradas[id_param] = {"tipo":"numerico","valor":float(valor),"lim_inf":lim_inf,"lim_sup":lim_sup,"nombre":nombre}
        else:
            checked = st.checkbox(f"{nombre} (check)", key=f"param_{id_param}")
            entradas[id_param] = {"tipo":"check","valor":1 if checked else 0,"lim_inf":None,"lim_sup":None,"nombre":nombre}

    if st.button("Guardar Control", use_container_width=True):
        id_usuario = get_user_id_from_session()
        if not id_usuario:
            st.error("No hay usuario autenticado. Por favor inicie sesión.")
            st.stop()

        fecha_hora = datetime.combine(fecha_control, hora_control)

        conn = get_conn()
        cur = conn.cursor()
        try:
            for id_param, data in entradas.items():
                # Insert control
                insert_control_record(cur, fecha_hora, data["valor"], observaciones, id_usuario,
                                        id_param, id_tipo, id_linea, id_detalle, id_orden, id_presentacion)
                conn.commit()
                id_control = cur.lastrowid

                # Alertas
                if data["tipo"] == "numerico" and pd.notna(data["lim_inf"]) and pd.notna(data["lim_sup"]):
                    try:
                        if data["valor"] < float(data["lim_inf"]) or data["valor"] > float(data["lim_sup"]):
                            descripcion = (f"Parámetro '{data['nombre']}' fuera de rango: {data['valor']} "
                                            f"(permitido {data['lim_inf']} - {data['lim_sup']}) — Orden {orden.get('codigoOrden')}")
                            save_alert(cur, "Fuera de Rango", descripcion, id_control, id_orden, id_linea, id_param, id_presentacion, data["valor"], data["lim_inf"], data["lim_sup"])
                            conn.commit()
                    except Exception:
                        # silently continue on cast errors
                        pass
                elif data["tipo"] == "check":
                    if data["valor"] == 0:
                        descripcion = f"Check NO cumplido — parámetro '{data['nombre']}' en orden {orden.get('codigoOrden')}"
                        save_alert(cur, "Check NO cumplido", descripcion, id_control, id_orden, id_linea, id_param, id_presentacion, 0, None, None)
                        conn.commit()

            st.success("Controles registrados correctamente.")
            st.rerun()
        except Exception as e:
            st.error(f"Error guardando controles: {e}")
        finally:
            cur.close()
            conn.close()
