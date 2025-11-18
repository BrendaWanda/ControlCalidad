# estandares.py
# Gestión de Estándares por Línea → Presentación → Tipo de Control
# Usa database.db_connection.get_connection()

import streamlit as st
import pandas as pd
from database.db_connection import get_connection

# ==========================================================
# FUNCIONES DE BASE DE DATOS
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
    """Retorna todos los tipos de control (sin filtrar)."""
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
    """Retorna solo los tipos de control asociados a una línea determinada."""
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


def insertar_parametro_presentacion(id_presentacion, id_parametro, tipo_parametro, lim_inf, lim_sup):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        if tipo_parametro == "check":
            lim_inf = None
            lim_sup = None

        cursor.execute("""
            INSERT INTO presentacionparametro
            (idPresentacion, idParametro, limiteInferior, limiteSuperior, tipoParametro)
            VALUES (%s, %s, %s, %s, %s)
        """, (id_presentacion, id_parametro, lim_inf, lim_sup, tipo_parametro))
        conn.commit()
    finally:
        cursor.close()
        conn.close()


def obtener_parametros_por_presentacion(id_presentacion):
    """
    Devuelve parámetros asignados a la presentación, incluyendo el idTipoControl del parámetro base.
    """
    conn = get_connection()
    query = """
        SELECT pp.idPresentacionParametro,
               p.idParametro,
               p.nombreParametro,
               p.idTipoControl,
               COALESCE(pp.tipoParametro, p.tipoParametro) AS tipoParametro,
               COALESCE(pp.limiteInferior, p.limiteInferior) AS limiteInferior,
               COALESCE(pp.limiteSuperior, p.limiteSuperior) AS limiteSuperior
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
# INTERFAZ STREAMLIT
# ==========================================================

def configurar_parametros():

    st.title("Configuración de Estándares de Calidad - Gustossi S.R.L.")
    st.markdown("---")

    menu = st.sidebar.radio("Menú de Configuración", [
        "Tipos de Control",
        "Parámetros de Calidad"
    ])

    # ==========================================================
    # TIPOS DE CONTROL
    # ==========================================================
    if menu == "Tipos de Control":
        st.subheader("Gestión de Tipos de Control")

        lineas = obtener_lineas_produccion()
        tipos = obtener_tipos_control()

        if tipos:
            df_tipos = pd.DataFrame(tipos, columns=["ID", "Tipo de Control", "Descripción", "Línea", "idLinea"])
            st.dataframe(df_tipos[["ID", "Tipo de Control", "Descripción", "Línea"]], use_container_width=True)
        else:
            st.info("No hay tipos de control registrados aún.")

        st.markdown("---")
        st.subheader("Agregar Nuevo Tipo de Control")

        with st.form("form_tipo_control", clear_on_submit=True):
            nombre = st.text_input("Nombre del Tipo de Control")
            descripcion = st.text_area("Descripción")

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

    # ==========================================================
    # PARÁMETROS DE CALIDAD POR PRESENTACIÓN
    # ==========================================================
    if menu == "Parámetros de Calidad":

        st.subheader("Gestión de Parámetros de Calidad por Presentación")

        # 1) Seleccionar Línea
        lineas = obtener_lineas_produccion()

        opciones_linea = ["— Seleccionar Línea —"] + [l[1] for l in lineas]
        sel_linea = st.selectbox("Seleccione una Línea", opciones_linea)

        if sel_linea == "— Seleccionar Línea —":
            st.info("Seleccione una línea para continuar.")
            return

        id_linea = next(l[0] for l in lineas if l[1] == sel_linea)

        # 2) Seleccionar Presentación (filtrada por línea)
        presentaciones = obtener_presentaciones_por_linea(id_linea)

        if not presentaciones:
            st.info("No hay presentaciones para la línea seleccionada.")
            return

        opciones_pres = ["— Seleccionar Presentación —"] + [p[1] for p in presentaciones]
        sel_pres = st.selectbox("Seleccione una Presentación", opciones_pres)

        if sel_pres == "— Seleccionar Presentación —":
            st.info("Seleccione una presentación para continuar.")
            return

        id_presentacion = next(p[0] for p in presentaciones if p[1] == sel_pres)

        # 3) Seleccionar Tipo de Control (filtrado por la misma línea)
        tipos_linea = obtener_tipos_por_linea(id_linea)

        if not tipos_linea:
            st.info("No hay tipos de control asociados a la línea seleccionada.")
            return

        opciones_tipo = ["— Seleccionar Tipo —"] + [t[1] for t in tipos_linea]
        sel_tipo = st.selectbox("Seleccione Tipo de Control", opciones_tipo)

        if sel_tipo == "— Seleccionar Tipo —":
            st.info("Seleccione un tipo de control para continuar.")
            return

        # obtener id_tipo desde tipos_linea (filtrado por nombre, ya que son de la misma línea)
        tipo_tuple = tipos_linea[opciones_tipo.index(sel_tipo) - 1]
        id_tipo = tipo_tuple[0]
        nombre_tipo = tipo_tuple[1]

        st.markdown(f"### Parámetros de **{nombre_tipo}** — Presentación **{sel_pres}**")

        # PARÁMETROS YA ASIGNADOS (a la presentación) — luego filtramos por el tipo seleccionado
        df_assigned_full = obtener_parametros_por_presentacion(id_presentacion)

        # Filtrar solo parámetros cuyo idTipoControl coincide con el tipo seleccionado
        df_assigned = df_assigned_full[df_assigned_full["idTipoControl"] == id_tipo]

        st.markdown("Parámetros asignados:")

        if df_assigned.empty:
            st.info("No hay parámetros asignados para este tipo de control en la presentación seleccionada.")
        else:
            st.dataframe(
                df_assigned[['nombreParametro','tipoParametro','limiteInferior','limiteSuperior']],
                use_container_width=True
            )

        # ===============================================================
        # ASIGNAR NUEVO PARÁMETRO A LA PRESENTACIÓN
        # ===============================================================

        st.markdown("---")
        st.subheader("Asignar nuevo parámetro a esta presentación")

        tipo_presentacion = st.selectbox(
            "Tipo de parámetro",
            ["numerico", "check"]
        )

        nombre_parametro = st.text_input("Nombre del parámetro")

        if tipo_presentacion == "numerico":
            unidad = st.text_input("Unidad (opcional)")
            lim_inf = st.number_input("Límite inferior", step=0.01, format="%.4f")
            lim_sup = st.number_input("Límite superior", step=0.01, format="%.4f")
        else:
            unidad = None
            lim_inf = None
            lim_sup = None

        if st.button("Asignar parámetro"):

            if nombre_parametro.strip() == "":
                st.warning("Debe ingresar un nombre de parámetro.")
                st.stop()

            if tipo_presentacion == "numerico" and (lim_sup is not None and lim_inf is not None) and lim_inf > lim_sup:
                st.warning("El límite inferior no puede ser mayor al límite superior.")
                st.stop()

            # 1. Insertar parámetro base (se asigna al tipo de control seleccionado)
            nuevo_id_parametro = insertar_parametro(
                nombre_parametro,
                descripcion="",
                unidad=unidad,
                lim_inf=lim_inf,
                lim_sup=lim_sup,
                tipo_parametro=tipo_presentacion,
                id_tipo=id_tipo
            )

            # 2. Insertar relación presentación-parametro (con límites concretos para la presentación)
            insertar_parametro_presentacion(
                id_presentacion=id_presentacion,
                id_parametro=nuevo_id_parametro,
                tipo_parametro=tipo_presentacion,
                lim_inf=lim_inf,
                lim_sup=lim_sup
            )

            st.success("✔ Parámetro asignado correctamente.")
            st.rerun()

        # ==========================================================
        # EDITAR / ELIMINAR
        # ==========================================================

        st.markdown("---")
        st.subheader("Editar / Eliminar parámetros asignados")

        # recargar asignados por presentación y filtrar por tipo seleccionado
        df_assigned_full = obtener_parametros_por_presentacion(id_presentacion)
        df_assigned = df_assigned_full[df_assigned_full["idTipoControl"] == id_tipo]

        if df_assigned.empty:
            st.info("No hay parámetros para editar/eliminar (para el tipo de control seleccionado).")
        else:
            opciones = ["— Seleccionar —"] + list(df_assigned["nombreParametro"])
            sel = st.selectbox("Seleccione parámetro", opciones)

            if sel != "— Seleccionar —":

                fila = df_assigned[df_assigned["nombreParametro"] == sel].iloc[0]

                id_pp = int(fila["idPresentacionParametro"])
                tipo_actual = fila["tipoParametro"]
                lim_inf_actual = fila["limiteInferior"]
                lim_sup_actual = fila["limiteSuperior"]

                with st.form("edit_param", clear_on_submit=True):
                    tipo_new = st.selectbox(
                        "Tipo",
                        ["numerico", "check"],
                        index=0 if tipo_actual == "numerico" else 1
                    )

                    if tipo_new == "numerico":
                        new_inf = st.number_input("Límite inferior", value=float(lim_inf_actual or 0.0), format="%.4f")
                        new_sup = st.number_input("Límite superior", value=float(lim_sup_actual or 0.0), format="%.4f")
                    else:
                        new_inf = None
                        new_sup = None

                    guardar = st.form_submit_button("Guardar cambios")

                    if guardar:
                        if tipo_new == "numerico" and new_inf is not None and new_sup is not None and new_inf > new_sup:
                            st.warning("El límite inferior no puede ser mayor al superior.")
                        else:
                            actualizar_parametro_presentacion(id_pp, tipo_new, new_inf, new_sup)
                            st.success("Actualizado.")
                            st.rerun()

                if st.button("Eliminar parámetro"):
                    eliminar_parametro_presentacion(id_pp)
                    st.success("Eliminado.")
                    st.rerun()


if __name__ == "__main__":
    configurar_parametros()
