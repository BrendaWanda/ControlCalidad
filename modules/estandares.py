# Código corregido con indentación adecuada y estructura ordenada
import streamlit as st
import pandas as pd
from database.db_connection import get_connection

# ==============================================================
# FUNCIONES DE BASE DE DATOS
# ==============================================================

def obtener_lineas_produccion():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT idLinea, nombreLinea FROM LineaProduccion ORDER BY nombreLinea;")
    lineas = cursor.fetchall()
    conn.close()
    return lineas


def obtener_tipos_control():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT t.idTipoControl, t.nombreTipo, t.descripcion, l.nombreLinea
        FROM TipoControl t
        LEFT JOIN LineaProduccion l ON t.idLinea = l.idLinea
        ORDER BY l.nombreLinea, t.nombreTipo;
    """)
    tipos = cursor.fetchall()
    conn.close()
    return tipos


def insertar_tipo_control(nombre, descripcion, id_linea):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO TipoControl (nombreTipo, descripcion, idLinea)
        VALUES (%s, %s, %s)
    """, (nombre, descripcion, id_linea))
    conn.commit()
    conn.close()


def actualizar_tipo_control(id_tipo, nombre, descripcion, id_linea):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE TipoControl
        SET nombreTipo = %s, descripcion = %s, idLinea = %s
        WHERE idTipoControl = %s
    """, (nombre, descripcion, id_linea, id_tipo))
    conn.commit()
    conn.close()


def eliminar_tipo_control(id_tipo):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM TipoControl WHERE idTipoControl = %s", (id_tipo,))
    conn.commit()
    conn.close()


def obtener_parametros_por_tipo(id_tipo):
    conn = get_connection()
    query = """
        SELECT idParametro, nombreParametro, descripcion, unidadMedida,
               limiteInferior, limiteSuperior, tipoParametro
        FROM ParametroCalidad
        WHERE idTipoControl = %s
        ORDER BY nombreParametro;
    """
    df = pd.read_sql(query, conn, params=(id_tipo,))
    conn.close()
    return df


def insertar_parametro(nombre, descripcion, unidad, lim_inf, lim_sup, tipo_parametro, id_tipo):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO ParametroCalidad 
        (nombreParametro, descripcion, unidadMedida, limiteInferior, limiteSuperior, tipoParametro, idTipoControl)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (nombre, descripcion, unidad, lim_inf, lim_sup, tipo_parametro, id_tipo))
    conn.commit()
    conn.close()


def eliminar_parametro(id_parametro):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM ParametroCalidad WHERE idParametro = %s", (id_parametro,))
    conn.commit()
    conn.close()


def actualizar_parametro(id_parametro, nombre, descripcion, unidad, lim_inf, lim_sup, tipo_parametro):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE ParametroCalidad
        SET nombreParametro = %s,
            descripcion = %s,
            unidadMedida = %s,
            limiteInferior = %s,
            limiteSuperior = %s,
            tipoParametro = %s
        WHERE idParametro = %s
    """, (nombre, descripcion, unidad, lim_inf, lim_sup, tipo_parametro, id_parametro))
    conn.commit()
    conn.close()


# ==============================================================
# INTERFAZ PRINCIPAL
# ==============================================================

def configurar_parametros():
    st.title("Configuración de Estándares de Calidad - Gustossi S.R.L.")
    st.markdown("---")

    menu = st.sidebar.radio("Menú de Configuración", [
        "Tipos de Control",
        "Parámetros de Calidad"
    ])

    # ==============================================================
    # SECCIÓN 1: TIPOS DE CONTROL
    # ==============================================================
    if menu == "Tipos de Control":
        st.subheader("Gestión de Tipos de Control")

        lineas = obtener_lineas_produccion()
        tipos = obtener_tipos_control()

        if tipos:
            df_tipos = pd.DataFrame(tipos, columns=["ID", "Tipo de Control", "Descripción", "Línea"])
            st.dataframe(df_tipos, use_container_width=True)
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
                    insertar_tipo_control(nombre, descripcion, id_linea)
                    st.success("Tipo de control agregado.")
                    st.rerun()

        # Editar y eliminar
        st.markdown("---")
        st.subheader("Editar o Eliminar Tipo de Control")

        if tipos:
            opciones_display = ["— Seleccionar Tipo —"] + [
                f"{t[1]} — {t[3]}" for t in tipos
            ]
            sel = st.selectbox("Seleccionar", opciones_display)

            if sel != "— Seleccionar Tipo —":
                idx = opciones_display.index(sel) - 1
                tipo = tipos[idx]

                id_tipo = tipo[0]
                nombre_t = tipo[1]
                desc_t = tipo[2]
                linea_t = tipo[3]

                lineas_nombres = [l[1] for l in lineas]
                idx_linea = lineas_nombres.index(linea_t)

                with st.form("edit_tipo"):
                    nuevo_nombre = st.text_input("Nuevo nombre", value=nombre_t)
                    nueva_desc = st.text_area("Descripción", value=desc_t)
                    nueva_linea = st.selectbox("Línea", lineas_nombres, index=idx_linea)

                    guardar = st.form_submit_button("Guardar Cambios")

                    if guardar:
                        id_linea = next(l[0] for l in lineas if l[1] == nueva_linea)
                        actualizar_tipo_control(id_tipo, nuevo_nombre, nueva_desc, id_linea)
                        st.success("Actualizado correctamente.")
                        st.rerun()

                if st.button(f"Eliminar '{nombre_t}'"):
                    eliminar_tipo_control(id_tipo)
                    st.success("Tipo eliminado.")
                    st.rerun()

    # ==============================================================
    # SECCIÓN 2: PARÁMETROS DE CALIDAD
    # ==============================================================
    if menu == "Parámetros de Calidad":
        st.subheader("Gestión de Parámetros de Calidad")

        tipos = obtener_tipos_control()
        if not tipos:
            st.warning("No existen tipos de control.")
            return

        opciones = ["— Seleccionar Tipo —"] + [
            f"{t[1]} — {t[3]}" for t in tipos
        ]
        sel = st.selectbox("Seleccionar Tipo de Control", opciones)

        if sel == "— Seleccionar Tipo —":
            return

        tipo = tipos[opciones.index(sel) - 1]
        id_tipo = tipo[0]
        nombre_tipo = tipo[1]
        linea_tipo = tipo[3]

        st.markdown(f"### Parámetros para **{nombre_tipo}** — Línea {linea_tipo}")

        df = obtener_parametros_por_tipo(id_tipo)
        st.dataframe(df, use_container_width=True)

        st.markdown("---")
        st.subheader("Agregar Nuevo Parámetro")

        # ========= SELECCIÓN DE TIPO =========
        tipo_parametro = st.selectbox(
            "Seleccione el tipo de parámetro",
            ["— Seleccionar Tipo —", "Numérico (con límites)", "Check (Aprobado / No Aprobado)"],
            key="tipo_add"
        )

        if tipo_parametro != "— Seleccionar Tipo —":
            with st.form("add_param_form", clear_on_submit=True):

                nombre = st.text_input("Nombre del parámetro", key="add_nombre")
                descripcion = st.text_area("Descripción del parámetro", key="add_desc")

                if tipo_parametro.startswith("Numérico"):
                    unidad = st.text_input("Unidad (%, g, mm)", key="add_unidad")
                    lim_inf = st.number_input("Límite Inferior", step=0.01, key="add_lim_inf")
                    lim_sup = st.number_input("Límite Superior", step=0.01, key="add_lim_sup")
                    tipo_db = "numerico"
                else:
                    unidad = "CHECK"
                    lim_inf = None
                    lim_sup = None
                    tipo_db = "check"

                guardar = st.form_submit_button("Guardar Parámetro")

                if guardar:
                    if not nombre:
                        st.warning("Debe ingresar un nombre para el parámetro.")
                    elif tipo_db == "numerico" and lim_inf > lim_sup:
                        st.warning("El límite inferior no puede ser mayor al superior.")
                    else:
                        insertar_parametro(nombre, descripcion, unidad, lim_inf, lim_sup, tipo_db, id_tipo)
                        st.success("Parámetro agregado correctamente.")
                        st.rerun()

        # ===================================================
        # EDITAR / ELIMINAR PARÁMETROS EXISTENTES
        # ===================================================
        if not df.empty:
            st.markdown("---")
            st.subheader("Editar o Eliminar Parámetro")

            nombres = ["— Seleccionar Parámetro —"] + list(df["nombreParametro"])
            sel_param = st.selectbox("Seleccione para editar", nombres)

            if sel_param != "— Seleccionar Parámetro —":
                fila = df[df["nombreParametro"] == sel_param].iloc[0]
                id_param = int(fila["idParametro"])
                is_check = fila["tipoParametro"] == "check"

                with st.form("edit_param"):
                    tipo_edit = st.selectbox(
                        "Tipo de parámetro",
                        ["Numérico (con límites)", "Check (Aprobado / No Aprobado)"],
                        index=1 if is_check else 0,
                        key="edit_tipo_param"
                    )

                    nuevo_nombre = st.text_input("Nombre", value=fila["nombreParametro"], key="edit_p_name")
                    nueva_desc = st.text_area("Descripción", value=fila["descripcion"], key="edit_p_desc")

                    if tipo_edit.startswith("Numérico"):
                        nueva_unidad = st.text_input("Unidad", value=fila["unidadMedida"], key="edit_p_unidad")
                        valor_inf = float(fila["limiteInferior"]) if fila["limiteInferior"] is not None else 0.0
                        valor_sup = float(fila["limiteSuperior"]) if fila["limiteSuperior"] is not None else 0.0
                        nuevo_inf = st.number_input("Límite Inferior", value=valor_inf, step=0.01, key="edit_p_lim_inf")
                        nuevo_sup = st.number_input("Límite Superior", value=valor_sup, step=0.01, key="edit_p_lim_sup")
                        tipo_db = "numerico"
                    else:
                        nueva_unidad = "CHECK"
                        nuevo_inf = None
                        nuevo_sup = None
                        tipo_db = "check"

                    guardar = st.form_submit_button("Guardar Cambios")
                    if guardar:
                        if not nuevo_nombre:
                            st.warning("Ingrese un nombre para el parámetro.")
                        elif tipo_db == "numerico" and nuevo_inf is None:
                            st.warning("Ingrese límites válidos para parámetros numéricos.")
                        elif tipo_db == "numerico" and nuevo_inf > nuevo_sup:
                            st.warning("El límite inferior no puede ser mayor que el superior.")
                        else:
                            actualizar_parametro(id_param, nuevo_nombre, nueva_desc, nueva_unidad, nuevo_inf, nuevo_sup, tipo_db)
                            st.success("Parámetro actualizado.")
                            st.rerun()

                if st.button("Eliminar Parámetro"):
                    eliminar_parametro(id_param)
                    st.success("Parámetro eliminado correctamente.")
                    st.rerun()


# ==============================================================
# EJECUCIÓN DIRECTA
# ==============================================================
if __name__ == "__main__":
    configurar_parametros()