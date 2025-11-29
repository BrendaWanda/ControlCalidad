# modules/estandares.py
"""
Gestión de Estándares por Línea → Presentación → Tipo de Control
Interfaz mejorada visualmente por "cuadrantes" y panel de edición/eliminación por parámetro.
Usa database.db_connection.get_connection()
"""

import streamlit as st
import pandas as pd
import numpy as np
from database.db_connection import get_connection

# ==========================================================
# FUNCIONES DE BASE DE DATOS (igual que antes, con pequeños guards)
# ==========================================================

def obtener_lineas_produccion():
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT idLinea, nombreLinea FROM lineaproduccion ORDER BY nombreLinea;")
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()


def obtener_tipos_control():
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT t.idTipoControl, t.nombreTipo, t.descripcion, l.nombreLinea, t.idLinea
            FROM tipocontrol t
            LEFT JOIN lineaproduccion l ON t.idLinea = l.idLinea
            ORDER BY l.nombreLinea, t.nombreTipo;
        """)
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()


def obtener_tipos_por_linea(id_linea):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT idTipoControl, nombreTipo, descripcion, idLinea
            FROM tipocontrol
            WHERE idLinea = %s
            ORDER BY nombreTipo;
        """, (id_linea,))
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()


def insertar_tipo_control(nombre, descripcion, id_linea):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO tipocontrol (nombreTipo, descripcion, idLinea)
            VALUES (%s, %s, %s)
        """, (nombre, descripcion, id_linea))
        conn.commit()
    finally:
        cursor.close()
        conn.close()


def actualizar_tipo_control(id_tipo, nombre, descripcion, id_linea):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE tipocontrol
            SET nombreTipo = %s, descripcion = %s, idLinea = %s
            WHERE idTipoControl = %s
        """, (nombre, descripcion, id_linea, id_tipo))
        conn.commit()
    finally:
        cursor.close()
        conn.close()


def eliminar_tipo_control(id_tipo):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM tipocontrol WHERE idTipoControl = %s", (id_tipo,))
        conn.commit()
    finally:
        cursor.close()
        conn.close()


def obtener_parametros_por_tipo(id_tipo):
    conn = get_connection()
    query = """
        SELECT idParametro, nombreParametro, descripcion, unidadMedida,
                limiteInferior, limiteSuperior, tipoParametro, idTipoControl
        FROM parametrocalidad
        WHERE idTipoControl = %s
        ORDER BY nombreParametro;
    """
    try:
        df = pd.read_sql(query, conn, params=(id_tipo,))
        return df
    finally:
        conn.close()


def insertar_parametro(nombre, descripcion, unidad, lim_inf, lim_sup, tipo_parametro, id_tipo):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO parametrocalidad 
            (nombreParametro, descripcion, unidadMedida, limiteInferior, limiteSuperior, tipoParametro, idTipoControl)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (nombre, descripcion, unidad, lim_inf, lim_sup, tipo_parametro, id_tipo))
        conn.commit()

        cursor.execute("SELECT LAST_INSERT_ID()")
        row = cursor.fetchone()
        if row:
            return int(row[0])
    finally:
        cursor.close()
        conn.close()


def eliminar_parametro(id_parametro):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM parametrocalidad WHERE idParametro = %s", (id_parametro,))
        conn.commit()
    finally:
        cursor.close()
        conn.close()


def actualizar_parametro(id_parametro, nombre, descripcion, unidad, lim_inf, lim_sup, tipo_parametro, id_tipo=None):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        if id_tipo:
            cursor.execute("""
                UPDATE parametrocalidad
                SET nombreParametro = %s,
                    descripcion = %s,
                    unidadMedida = %s,
                    limiteInferior = %s,
                    limiteSuperior = %s,
                    tipoParametro = %s,
                    idTipoControl = %s
                WHERE idParametro = %s
            """, (nombre, descripcion, unidad, lim_inf, lim_sup, tipo_parametro, id_tipo, id_parametro))
        else:
            cursor.execute("""
                UPDATE parametrocalidad
                SET nombreParametro = %s,
                    descripcion = %s,
                    unidadMedida = %s,
                    limiteInferior = %s,
                    limiteSuperior = %s,
                    tipoParametro = %s
                WHERE idParametro = %s
            """, (nombre, descripcion, unidad, lim_inf, lim_sup, tipo_parametro, id_parametro))
        conn.commit()
    finally:
        cursor.close()
        conn.close()


# ---------------------------
# PRESENTACIONES
# ---------------------------

def obtener_presentaciones_por_linea(id_linea):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT idPresentacion, nombrePresentacion
            FROM presentacionproducto
            WHERE idLinea = %s
            ORDER BY nombrePresentacion;
        """, (id_linea,))
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()


def insertar_parametro_presentacion(id_presentacion, id_parametro, tipo_parametro, lim_inf, lim_sup, unidad):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        if tipo_parametro == "check":
            lim_inf = None
            lim_sup = None

        cursor.execute("""
            INSERT INTO presentacionparametro
            (idPresentacion, idParametro, limiteInferior, limiteSuperior, tipoParametro, unidadMedida)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (id_presentacion, id_parametro, lim_inf, lim_sup, tipo_parametro, unidad))
        conn.commit()
    finally:
        cursor.close()
        conn.close()


def obtener_parametros_por_presentacion(id_presentacion):
    conn = get_connection()
    query = """
        SELECT 
            pp.idPresentacionParametro,
            p.idParametro,
            p.nombreParametro,
            p.idTipoControl,
            COALESCE(pp.tipoParametro, p.tipoParametro) AS tipoParametro,
            COALESCE(pp.limiteInferior, p.limiteInferior) AS limiteInferior,
            COALESCE(pp.limiteSuperior, p.limiteSuperior) AS limiteSuperior,
            COALESCE(pp.unidadMedida, p.unidadMedida) AS unidadMedida
        FROM presentacionparametro pp
        INNER JOIN parametrocalidad p ON p.idParametro = pp.idParametro
        WHERE pp.idPresentacion = %s
        ORDER BY p.nombreParametro;
    """
    try:
        df = pd.read_sql(query, conn, params=(id_presentacion,))
        return df
    finally:
        conn.close()


def actualizar_parametro_presentacion(id_pp, tipo_parametro, lim_inf, lim_sup):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        if tipo_parametro == "check":
            lim_inf = None
            lim_sup = None

        cursor.execute("""
            UPDATE presentacionparametro
            SET tipoParametro = %s,
                limiteInferior = %s,
                limiteSuperior = %s
            WHERE idPresentacionParametro = %s
        """, (tipo_parametro, lim_inf, lim_sup, id_pp))
        conn.commit()
    finally:
        cursor.close()
        conn.close()


def eliminar_parametro_presentacion(id_pp):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM presentacionparametro WHERE idPresentacionParametro = %s", (id_pp,))
        conn.commit()
    finally:
        cursor.close()
        conn.close()


# ==========================================================
# INTERFAZ STREAMLIT (MEJORADA)
# ==========================================================

def configurar_parametros():
    st.set_page_config(page_title="Configuración de Estándares", layout="wide")
    st.title("Configuración de Estándares de Calidad - Gustossi S.R.L.")
    st.markdown("---")

    # Menú superior simple
    menu = st.radio("Panel", ["Tipos de Control", "Parámetros de Calidad por Presentación"], horizontal=True)

    # -----------------
    # TIPOS DE CONTROL (panel simple, lista editable)
    # -----------------
    if menu == "Tipos de Control":
        st.subheader("Gestión de Tipos de Control")
        lineas = obtener_lineas_produccion()
        tipos = obtener_tipos_control()

        col1, col2 = st.columns([1, 2])

        with col1:
            st.markdown("**Líneas disponibles**")
            df_lines = pd.DataFrame(lineas, columns=["idLinea", "nombreLinea"]) if lineas else pd.DataFrame(columns=["idLinea", "nombreLinea"])
            st.dataframe(df_lines.rename(columns={"idLinea": "ID", "nombreLinea": "Línea"}), use_container_width=True)

            st.markdown("### Nuevo Tipo de Control")
            with st.form("form_tipo_control", clear_on_submit=True):
                nombre = st.text_input("Nombre del Tipo de Control")
                descripcion = st.text_area("Descripción", height=80)
                opciones = ["— Seleccionar Línea —"] + [l[1] for l in lineas]
                linea_nombre = st.selectbox("Línea de Producción", opciones)
                guardar = st.form_submit_button("Guardar Tipo")
                if guardar:
                    if linea_nombre == "— Seleccionar Línea —":
                        st.warning("Seleccione una línea válida.")
                    else:
                        id_linea = next(l[0] for l in lineas if l[1] == linea_nombre)
                        if nombre.strip() == "":
                            st.warning("El nombre del tipo de control no puede estar vacío.")
                        else:
                            insertar_tipo_control(nombre, descripcion, id_linea)
                            st.success("Tipo de control agregado.")
                            st.rerun()

        with col2:
            st.markdown("**Tipos de control existentes**")
            if tipos:
                df_tipos = pd.DataFrame(tipos, columns=["ID", "Tipo de Control", "Descripción", "Línea", "idLinea"])
                # Mostrar en tabla y además permitir editar/eliminar por fila con expanders
                for row in df_tipos.to_dict("records"):
                    with st.expander(f"{row['Tipo de Control']} — {row['Línea']}"):
                        st.write(row["Descripción"] or "—")
                        cola, colb = st.columns([3, 1])
                        with cola:
                            nuevo_nombre = st.text_input(f"Nombre ({row['ID']})", value=row['Tipo de Control'], key=f"tipo_nombre_{row['ID']}")
                            nueva_desc = st.text_area(f"Descripción ({row['ID']})", value=row['Descripción'] or "", key=f"tipo_desc_{row['ID']}")
                            # select línea
                            opciones_lineas = [l[1] for l in lineas]
                            linea_actual = next((l[1] for l in lineas if l[0] == row["idLinea"]), "—")
                            nueva_linea = st.selectbox(f"Línea ({row['ID']})", ["— Seleccionar —"] + opciones_lineas, index=(1 + opciones_lineas.index(linea_actual)) if linea_actual in opciones_lineas else 0, key=f"tipo_linea_{row['ID']}")
                        with colb:
                            if st.button("Guardar", key=f"guardar_tipo_{row['ID']}"):
                                if nueva_linea == "— Seleccionar —":
                                    st.warning("Seleccione una línea válida.")
                                else:
                                    id_new_linea = next(l[0] for l in lineas if l[1] == nueva_linea)
                                    actualizar_tipo_control(row['ID'], nuevo_nombre, nueva_desc, id_new_linea)
                                    st.success("Tipo actualizado.")
                                    st.rerun()
                            if st.button("Eliminar", key=f"eliminar_tipo_{row['ID']}"):
                                eliminar_tipo_control(row['ID'])
                                st.success("Eliminado.")
                                st.rerun()
            else:
                st.info("No hay tipos de control registrados aún.")

    # -----------------
    # PARÁMETROS POR PRESENTACIÓN (UI en cuadrantes)
    # -----------------
    else:
        st.subheader("Parámetros de Calidad por Presentación (cuadrantes)")

        # --- Obtener líneas y presentaciones ---
        lineas = obtener_lineas_produccion()
        if not lineas:
            st.info("No hay líneas de producción registradas.")
            return

        # LAYOUT: dos columnas principales (izq controles, der panel de parámetros)
        left_col, right_col = st.columns([1, 2])

        # LEFT TOP: selección cascade
        with left_col:
            st.markdown("### Filtros")
            opciones_linea = ["— Seleccionar Línea —"] + [l[1] for l in lineas]
            sel_linea = st.selectbox("Seleccione una Línea", opciones_linea, index=0, key="est_linea")
            if sel_linea == "— Seleccionar Línea —":
                st.info("Seleccione una línea para continuar.")
                return
            id_linea = next(l[0] for l in lineas if l[1] == sel_linea)

            # Presentaciones
            presentaciones = obtener_presentaciones_por_linea(id_linea)
            if not presentaciones:
                st.info("No hay presentaciones para la línea seleccionada.")
                return
            opciones_pres = ["— Seleccionar Presentación —"] + [p[1] for p in presentaciones]
            sel_pres = st.selectbox("Seleccione una Presentación", opciones_pres, key="est_pres")
            if sel_pres == "— Seleccionar Presentación —":
                st.info("Seleccione una presentación para continuar.")
                return
            id_presentacion = next(p[0] for p in presentaciones if p[1] == sel_pres)

            # Tipos de control para la linea
            tipos_linea = obtener_tipos_por_linea(id_linea)
            if not tipos_linea:
                st.info("No hay tipos de control asociados a la línea seleccionada.")
                return
            opciones_tipo = ["— Seleccionar Tipo —"] + [t[1] for t in tipos_linea]
            sel_tipo = st.selectbox("Seleccione Tipo de Control", opciones_tipo, key="est_tipo")
            if sel_tipo == "— Seleccionar Tipo —":
                st.info("Seleccione un tipo de control para continuar.")
                return
            # obtener id_tipo basado en seleccion
            tipo_tuple = tipos_linea[opciones_tipo.index(sel_tipo) - 1]
            id_tipo = tipo_tuple[0]
            nombre_tipo = tipo_tuple[1]

            st.markdown(f"**Tipo seleccionado:** {nombre_tipo}")
            st.markdown(f"**Presentación:** {sel_pres}")

            st.markdown("---")

            # Cuadrante inferior izquierdo: Form para agregar nuevo parámetro (rápido)
            st.markdown("### Asignar nuevo parámetro (rápido)")
            with st.form("form_asignar_param", clear_on_submit=True):
                tipo_presentacion = st.selectbox("Tipo de parámetro", ["numerico", "check"], key="asig_tipo")
                nombre_parametro = st.text_input("Nombre del parámetro", key="asig_nombre")
                descripcion_param = st.text_area("Descripción (opcional)", key="asig_desc", height=80)
                if tipo_presentacion == "numerico":
                    unidad = st.text_input("Unidad (opcional)", key="asig_unidad")
                    lim_inf = st.number_input("Límite inferior", step=0.01, format="%.4f", key="asig_inf")
                    lim_sup = st.number_input("Límite superior", step=0.01, format="%.4f", key="asig_sup")
                else:
                    unidad = None
                    lim_inf = None
                    lim_sup = None

                btn_asignar = st.form_submit_button("Asignar parámetro a presentación")
                if btn_asignar:
                    if nombre_parametro.strip() == "":
                        st.warning("Debe ingresar un nombre de parámetro.")
                    elif tipo_presentacion == "numerico" and (lim_inf is not None and lim_sup is not None) and lim_inf > lim_sup:
                        st.warning("El límite inferior no puede ser mayor al límite superior.")
                    else:
                        # Crear parámetro base (asignado al tipo)
                        nuevo_id_parametro = insertar_parametro(
                            nombre_parametro,
                            descripcion=descripcion_param,
                            unidad=unidad,
                            lim_inf=lim_inf,
                            lim_sup=lim_sup,
                            tipo_parametro=tipo_presentacion,
                            id_tipo=id_tipo
                        )
                        # Asignar a la presentacion
                        insertar_parametro_presentacion(
                            id_presentacion=id_presentacion,
                            id_parametro=nuevo_id_parametro,
                            tipo_parametro=tipo_presentacion,
                            lim_inf=lim_inf,
                            lim_sup=lim_sup,
                            unidad=unidad
                        )
                        st.success("✔ Parámetro asignado correctamente.")
                        st.rerun()

        # RIGHT column: panel de parámetros asignados y edición por fila (cuadrantes derechos)
        with right_col:
            st.markdown("## Parámetros asignados a la presentación")
            df_assigned_full = obtener_parametros_por_presentacion(id_presentacion)
            # Filtrar sólo los del tipo seleccionado
            df_assigned = df_assigned_full[df_assigned_full["idTipoControl"] == id_tipo]

            if df_assigned.empty:
                st.info("No hay parámetros asignados para este tipo de control en la presentación seleccionada.")
            else:
                # Mostrar resumen compacto en la parte superior
                c1, c2, c3 = st.columns([1,1,1])
                with c1:
                    st.metric("Parámetros totales", len(df_assigned))
                with c2:
                    tipos_counts = df_assigned["tipoParametro"].value_counts().to_dict()
                    st.write("Tipos:", tipos_counts)
                with c3:
                    unidades = df_assigned["unidadMedida"].fillna("—").unique().tolist()
                    st.write("Unidades:", ", ".join(map(str, unidades[:6])))

                st.markdown("---")
                st.markdown("### Lista y acciones (editar / eliminar)")

                # Iterar y mostrar cada parámetro como un 'card' (expander) con formulario de edición y botón eliminar
                for i, row in df_assigned.reset_index(drop=True).iterrows():
                    pid = int(row["idParametro"])
                    id_pp = int(row["idPresentacionParametro"])
                    nombre_p = row["nombreParametro"]
                    tipo_p = row["tipoParametro"]
                    unidad_p = row["unidadMedida"] if pd.notna(row["unidadMedida"]) else ""
                    lim_inf_p = None if pd.isna(row["limiteInferior"]) else float(row["limiteInferior"])
                    lim_sup_p = None if pd.isna(row["limiteSuperior"]) else float(row["limiteSuperior"])

                    with st.expander(f"{nombre_p}  —  tipo: {tipo_p}"):
                        colL, colR = st.columns([3,1])
                        with colL:
                            st.write(f"Unidad: **{unidad_p or '—'}**")
                            st.write(f"Límite inferior: **{lim_inf_p if lim_inf_p is not None else '—'}**")
                            st.write(f"Límite superior: **{lim_sup_p if lim_sup_p is not None else '—'}**")
                            st.write("---")
                            # Form de edición en línea
                            with st.form(key=f"form_edit_pp_{id_pp}", clear_on_submit=False):
                                nuevo_tipo = st.selectbox("Tipo de parámetro", ["numerico", "check"], index=0 if tipo_p == "numerico" else 1, key=f"tipo_{id_pp}")
                                if nuevo_tipo == "numerico":
                                    new_inf = st.number_input("Límite inferior", value=lim_inf_p if lim_inf_p is not None else 0.0, format="%.4f", key=f"inf_{id_pp}")
                                    new_sup = st.number_input("Límite superior", value=lim_sup_p if lim_sup_p is not None else 0.0, format="%.4f", key=f"sup_{id_pp}")
                                else:
                                    new_inf = None
                                    new_sup = None
                                submitted = st.form_submit_button("Guardar cambios", use_container_width=True, key=f"guardar_pp_{id_pp}")
                                if submitted:
                                    if nuevo_tipo == "numerico" and new_inf is not None and new_sup is not None and new_inf > new_sup:
                                        st.warning("Límite inferior no puede ser mayor al superior.")
                                    else:
                                        actualizar_parametro_presentacion(id_pp, nuevo_tipo, new_inf, new_sup)
                                        st.success("Parámetro actualizado.")
                                        st.rerun()
                        with colR:
                            if st.button("Eliminar parámetro", key=f"del_pp_{id_pp}"):
                                eliminar_parametro_presentacion(id_pp)
                                st.success("Parámetro eliminado.")
                                st.rerun()

                st.markdown("---")
                st.markdown("### Exportar / Tabla completa")
                st.dataframe(df_assigned[['idPresentacionParametro','idParametro','nombreParametro','tipoParametro','unidadMedida','limiteInferior','limiteSuperior']].rename(columns={
                    'idPresentacionParametro':'ID_PP','idParametro':'ID_PARAM','nombreParametro':'Nombre','tipoParametro':'Tipo','unidadMedida':'Unidad','limiteInferior':'LimInf','limiteSuperior':'LimSup'
                }), use_container_width=True)

                csv = df_assigned.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Descargar CSV (asignados)", data=csv, file_name="parametros_asignados.csv", mime="text/csv")

    # fin de interfaz

if __name__ == "__main__":
    configurar_parametros()
