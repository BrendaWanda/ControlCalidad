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
        SELECT idParametro, nombreParametro, descripcion, unidadMedida, limiteInferior, limiteSuperior
        FROM ParametroCalidad
        WHERE idTipoControl = %s
        ORDER BY nombreParametro;
    """
    df = pd.read_sql(query, conn, params=(id_tipo,))
    conn.close()
    return df


def insertar_parametro(nombre, descripcion, unidad, lim_inf, lim_sup, id_tipo):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO ParametroCalidad (nombreParametro, descripcion, unidadMedida, limiteInferior, limiteSuperior, idTipoControl)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (nombre, descripcion, unidad, lim_inf, lim_sup, id_tipo))
    conn.commit()
    conn.close()


def eliminar_parametro(id_parametro):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM ParametroCalidad WHERE idParametro = %s", (id_parametro,))
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

        # --------------------------
        # AGREGAR NUEVO TIPO DE CONTROL
        # --------------------------
        st.markdown("---")
        st.subheader("Agregar Nuevo Tipo de Control")

        with st.form("form_tipo_control", clear_on_submit=True):
            nombre = st.text_input("Nombre del Tipo de Control", placeholder="Ej: Producto en Proceso")
            descripcion = st.text_area("Descripción", placeholder="Describe el tipo de control (ej. inspección visual, físico-química, etc.)")
            opciones_lineas = ["— Seleccionar Línea —"] + [l[1] for l in lineas]
            linea_nombre = st.selectbox("Línea de Producción", opciones_lineas)
            guardar = st.form_submit_button("Guardar Tipo")

            if guardar:
                if not nombre or linea_nombre == "— Seleccionar Línea —":
                    st.warning("Ingrese un nombre y seleccione una línea de producción.")
                else:
                    id_linea = next(l[0] for l in lineas if l[1] == linea_nombre)
                    insertar_tipo_control(nombre, descripcion, id_linea)
                    st.success(f"Tipo de control **{nombre}** agregado correctamente para la línea **{linea_nombre}**.")
                    st.rerun()

        # --------------------------
        # EDITAR O ELIMINAR TIPO DE CONTROL
        # --------------------------
        st.markdown("---")
        st.subheader("Editar o Eliminar Tipo de Control")

        if tipos:
            opciones_display = ["— Seleccionar Tipo de Control —"] + [
                f"{t[1]} — {t[3]}" if t[3] else t[1] for t in tipos
            ]
            opcion_sel = st.selectbox("Seleccionar Tipo de Control", opciones_display)

            if opcion_sel != "— Seleccionar Tipo de Control —":
                tipo_data = tipos[opciones_display.index(opcion_sel) - 1]
                id_tipo = tipo_data[0]
                tipo_nombre = tipo_data[1]
                desc_actual = tipo_data[2]
                linea_actual = tipo_data[3]

                lineas_nombres = [l[1] for l in lineas]
                index_linea = lineas_nombres.index(linea_actual) if linea_actual in lineas_nombres else 0

                with st.form("editar_tipo"):
                    nuevo_nombre = st.text_input("Nuevo nombre", value=tipo_nombre)
                    nueva_descripcion = st.text_area("Nueva descripción", value=desc_actual)
                    nueva_linea = st.selectbox("Línea asociada", lineas_nombres, index=index_linea)
                    id_linea = next(l[0] for l in lineas if l[1] == nueva_linea)
                    guardar_cambio = st.form_submit_button("Guardar Cambios")

                    if guardar_cambio:
                        actualizar_tipo_control(id_tipo, nuevo_nombre, nueva_descripcion, id_linea)
                        st.success(f"Tipo de control **{nuevo_nombre}** actualizado correctamente.")
                        st.rerun()

                st.markdown("---")
                st.subheader("Eliminar Tipo de Control")

                eliminar_confirm = st.checkbox(f"Confirmar eliminación de '{tipo_nombre} — {linea_actual}' antes de continuar")
                eliminar_boton = st.button("Eliminar Tipo de Control")

                if eliminar_boton:
                    if eliminar_confirm:
                        eliminar_tipo_control(id_tipo)
                        st.success(f"Tipo de control **{tipo_nombre} — {linea_actual}** eliminado correctamente.")
                        st.rerun()
                    else:
                        st.warning("Debes confirmar antes de eliminar.")

    # ==============================================================
    # SECCIÓN 2: PARÁMETROS DE CALIDAD
    # ==============================================================
    elif menu == "Parámetros de Calidad":
        st.subheader("Gestión de Parámetros de Calidad")

        tipos = obtener_tipos_control()
        if not tipos:
            st.warning("Primero registre tipos de control antes de añadir parámetros.")
            return

        opciones_display = ["— Seleccionar Tipo de Control —"] + [
            f"{t[1]} — {t[3]}" if t[3] else t[1] for t in tipos
        ]
        tipo_sel = st.selectbox("Seleccionar Tipo de Control", opciones_display)

        if tipo_sel == "— Seleccionar Tipo de Control —":
            st.info("Seleccione un tipo de control para ver o agregar parámetros.")
            return

        tipo_data = tipos[opciones_display.index(tipo_sel) - 1]
        id_tipo = tipo_data[0]
        tipo_nombre = tipo_data[1]
        linea_nombre = tipo_data[3]

        st.markdown(f"### Parámetros asociados a: **{tipo_nombre.upper()}** (Línea: {linea_nombre})")

        df = obtener_parametros_por_tipo(id_tipo)
        if df.empty:
            st.info("No hay parámetros registrados para este tipo de control.")
        else:
            st.dataframe(df, use_container_width=True)

        # --------------------------
        # AGREGAR NUEVO PARÁMETRO
        # --------------------------
        st.markdown("---")
        st.subheader("Agregar Nuevo Parámetro")

        with st.form("form_parametro", clear_on_submit=True):
            nombre = st.text_input("Nombre del Parámetro", placeholder="Ej: Humedad, Peso, Textura")
            descripcion = st.text_area("Descripción del Parámetro", placeholder="Ej: Evaluar la humedad en % del producto")
            unidad = st.text_input("Unidad de Medida", placeholder="Ej: %, g, mm")
            lim_inf = st.number_input("Límite Inferior", step=0.01, value=0.00)
            lim_sup = st.number_input("Límite Superior", step=0.01, value=0.00)
            guardar = st.form_submit_button("Guardar Parámetro")

            if guardar:
                if not nombre:
                    st.warning("Debes ingresar un nombre para el parámetro.")
                else:
                    insertar_parametro(nombre, descripcion, unidad, lim_inf, lim_sup, id_tipo)
                    st.success(f"Parámetro **{nombre}** agregado correctamente al tipo **{tipo_nombre}** (Línea: {linea_nombre}).")
                    st.rerun()

        # --------------------------
        # ELIMINAR PARÁMETRO
        # --------------------------
        if not df.empty:
            st.markdown("---")
            st.subheader("Eliminar Parámetro Existente")
            eliminar_nombre = st.selectbox("Seleccionar parámetro a eliminar", ["— Seleccionar Parámetro —"] + list(df["nombreParametro"]))
            if eliminar_nombre != "— Seleccionar Parámetro —":
                id_eliminar = int(df.loc[df["nombreParametro"] == eliminar_nombre, "idParametro"].iloc[0])
                if st.button("Eliminar Parámetro"):
                    eliminar_parametro(id_eliminar)
                    st.success(f"Parámetro **{eliminar_nombre}** eliminado correctamente.")
                    st.rerun()


# ==============================================================
# EJECUCIÓN DIRECTA
# ==============================================================
if __name__ == "__main__":
    configurar_parametros()