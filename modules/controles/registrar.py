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
    try:
        id_detalle = int(sel_det.split("—")[0].replace("Detalle", "").strip())
    except Exception:
        st.error("Detalle seleccionado inválido.")
        st.stop()
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

    # Validar rangos incoherentes (lim_inf > lim_sup)
    for _, r in df_params.iterrows():
        lim_inf = r.get("limiteInferior")
        lim_sup = r.get("limiteSuperior")
        if pd.notna(lim_inf) and pd.notna(lim_sup):
            try:
                if float(lim_inf) > float(lim_sup):
                    st.error(f"Rangos incoherentes en parámetro '{r.get('nombreParametro')}'. Verifique configuración.")
                    st.stop()
            except Exception:
                # si no son convertibles a float, no detener aquí; se validará al guardar
                pass

    st.subheader("Parámetros a registrar")
    col_a, col_b = st.columns([3,1])
    with col_a:
        observaciones = st.text_area("Observaciones (opcional)")
        if observaciones is None:
            observaciones = ""
        observaciones = observaciones.strip()
    with col_b:
        fecha_control = st.date_input("Fecha", datetime.now().date())
        hora_control = st.time_input("Hora", datetime.now().time())

    # VALIDACIÓN: fecha/hora no futura
    fecha_hora_control = datetime.combine(fecha_control, hora_control)
    if fecha_hora_control > datetime.now():
        st.warning("La fecha/hora seleccionada está en el futuro.")
        st.stop()

    # Construir entradas: para numéricos usamos text_input para detectar vacío; para checks mantenemos checkbox
    entradas = {}
    for _, row in df_params.iterrows():
        id_param = int(row["idParametro"])
        nombre = row["nombreParametro"]
        tipo_param = row["tipoParametro"]
        lim_inf = row.get("limiteInferior")
        lim_sup = row.get("limiteSuperior")
        unidad = row.get("unidadMedida", "")

        if tipo_param == "numerico":
            # Usar text_input para permitir detectar campo vacío
            label = f"{nombre} ({unidad}) — Rango: {lim_inf if pd.notna(lim_inf) else '-'} a {lim_sup if pd.notna(lim_sup) else '-'}"
            raw_val = st.text_input(label, key=f"param_{id_param}")
            # No convertimos aún; sólo almacenamos el raw para validación posterior
            entradas[id_param] = {
                "tipo": "numerico",
                "raw_val": raw_val,
                "lim_inf": lim_inf,
                "lim_sup": lim_sup,
                "nombre": nombre
            }
        else:
            checked = st.checkbox(f"{nombre} (check)", key=f"param_{id_param}")
            entradas[id_param] = {
                "tipo": "check",
                "valor": 1 if checked else 0,
                "lim_inf": None,
                "lim_sup": None,
                "nombre": nombre
            }

    # BOTÓN GUARDAR
    if st.button("Guardar Control", use_container_width=True):
        # Validaciones previas a insertar
        id_usuario = get_user_id_from_session()
        if not id_usuario:
            st.error("No hay usuario autenticado. Por favor inicie sesión.")
            st.stop()

        # Revalidar que orden, detalle, presentación y tipo estén bien
        if not id_orden or not id_detalle or not id_presentacion or not id_tipo:
            st.error("Falta información obligatoria (orden / detalle / presentación / tipo).")
            st.stop()

        # Validar valores numéricos: no vacíos y son numéricos
        errores = []
        entradas_parsed = {}  # mantendremos valores parseados para guardar
        for id_param, data in entradas.items():
            if data["tipo"] == "numerico":
                raw = data.get("raw_val")
                nombre = data.get("nombre")
                if raw is None or str(raw).strip() == "":
                    errores.append(f"El parámetro numérico '{nombre}' no puede quedar vacío.")
                    continue
                # intentar convertir a float
                try:
                    val = float(str(raw).strip())
                except Exception:
                    errores.append(f"El parámetro '{nombre}' debe ser numérico (ej: 12.5).")
                    continue
                # si existen límites, validar consistencia del valor (pero no impedir el guardado salvo que quieras)
                lim_inf = data.get("lim_inf")
                lim_sup = data.get("lim_sup")
                try:
                    if pd.notna(lim_inf):
                        lim_inf_f = float(lim_inf)
                    else:
                        lim_inf_f = None
                    if pd.notna(lim_sup):
                        lim_sup_f = float(lim_sup)
                    else:
                        lim_sup_f = None
                except Exception:
                    # si los límites no son convertibles, los ignoramos para esta validación
                    lim_inf_f = None
                    lim_sup_f = None

                # Si hay límites y el valor está fuera, se genera ALERTA luego (como ya haces); aquí no bloqueamos la inserción.
                entradas_parsed[id_param] = {
                    "tipo": "numerico",
                    "valor": val,
                    "lim_inf": lim_inf_f,
                    "lim_sup": lim_sup_f,
                    "nombre": nombre
                }
            else:
                # check
                entradas_parsed[id_param] = data  # ya tiene "valor"
        # Si hubo errores, mostrarlos y no insertar
        if errores:
            for e in errores:
                st.error(e)
            st.stop()

        # Si llegamos aquí, todo validado -> insertar
        conn = get_conn()
        cur = conn.cursor()
        try:
            for id_param, data in entradas_parsed.items():
                # Insertar control (usando data["valor"])
                if data["tipo"] == "numerico":
                    valor_a_guardar = data["valor"]
                else:
                    valor_a_guardar = data["valor"]

                insert_control_record(
                    cur,
                    fecha_hora_control,
                    valor_a_guardar,
                    observaciones,
                    id_usuario,
                    id_param,
                    id_tipo,
                    id_linea,
                    id_detalle,
                    id_orden,
                    id_presentacion
                )
                conn.commit()
                id_control = cur.lastrowid

                # Alertas (misma lógica que tenías)
                if data["tipo"] == "numerico" and data.get("lim_inf") is not None and data.get("lim_sup") is not None:
                    try:
                        if valor_a_guardar < float(data["lim_inf"]) or valor_a_guardar > float(data["lim_sup"]):
                            descripcion = (f"Parámetro '{data['nombre']}' fuera de rango: {valor_a_guardar} "
                                            f"(permitido {data['lim_inf']} - {data['lim_sup']}) — Orden {orden.get('codigoOrden')}")
                            save_alert(cur, "Fuera de Rango", descripcion, id_control, id_orden, id_linea, id_param, id_presentacion, valor_a_guardar, data["lim_inf"], data["lim_sup"])
                            conn.commit()
                    except Exception:
                        # no interrumpir por errores en chequeo de alerta
                        pass
                elif data["tipo"] == "check":
                    if valor_a_guardar == 0:
                        descripcion = f"Check NO cumplido — parámetro '{data['nombre']}' en orden {orden.get('codigoOrden')}"
                        save_alert(cur, "Check NO cumplido", descripcion, id_control, id_orden, id_linea, id_param, id_presentacion, 0, None, None)
                        conn.commit()

            st.success("Controles registrados correctamente.")
            st.rerun()
        except Exception as e:
            # Mostrar error claro y no enmascarar
            st.error(f"Error guardando controles: {e}")
        finally:
            try:
                cur.close()
            except Exception:
                pass
            try:
                conn.close()
            except Exception:
                pass