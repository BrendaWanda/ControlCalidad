import streamlit as st
from database.db_connection import get_connection
import pandas as pd

# ==========================================================
# FUNCIONES DE BASE DE DATOS
# ==========================================================

def obtener_lineas():
    conn = get_connection()
    df = pd.read_sql("SELECT idLinea, nombreLinea FROM LineaProduccion ORDER BY nombreLinea", conn)
    conn.close()
    return df

def obtener_presentaciones(idLinea):
    conn = get_connection()
    df = pd.read_sql("""
        SELECT idPresentacion, nombrePresentacion 
        FROM PresentacionProducto 
        WHERE idLinea = %s
        ORDER BY nombrePresentacion
    """, conn, params=(idLinea,))
    conn.close()
    return df

def insertar_presentacion(nombre, idLinea):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO PresentacionProducto (nombrePresentacion, idLinea)
        VALUES (%s, %s)
    """, (nombre, idLinea))
    conn.commit()
    conn.close()

def eliminar_presentacion(idPresentacion):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM PresentacionProducto WHERE idPresentacion = %s", (idPresentacion,))
    conn.commit()
    conn.close()

# ==========================================================
# INTERFAZ PRINCIPAL
# ==========================================================

def gestionar_lineas():
    st.title("Gestión de Líneas de Producción")
    st.markdown("---")

    df_lineas = obtener_lineas()

    st.subheader("Líneas Registradas")
    st.dataframe(df_lineas, use_container_width=True)

    st.markdown("---")
    st.subheader("Agregar Nueva Línea")

    with st.form("form_linea", clear_on_submit=True):
        nombre = st.text_input("Nombre de la línea", placeholder="Ej: Línea Galletería")
        guardar = st.form_submit_button("Guardar")

        if guardar:
            if not nombre:
                st.warning("Ingrese un nombre válido.")
            else:
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute("INSERT INTO LineaProduccion (nombreLinea) VALUES (%s)", (nombre,))
                conn.commit()
                conn.close()
                st.success(f"Línea '{nombre}' registrada correctamente.")
                st.rerun()

    st.markdown("---")
    st.subheader("Administrar Presentaciones de una Línea")

    if df_lineas.empty:
        st.info("No hay líneas registradas.")
        return

    # Seleccionar línea
    linea_sel = st.selectbox("Seleccione una línea", df_lineas["nombreLinea"])

    idLinea = int(df_lineas.loc[df_lineas["nombreLinea"] == linea_sel, "idLinea"].iloc[0])

    # Mostrar presentaciones actuales
    st.markdown(f"### Presentaciones para: **{linea_sel}**")

    df_present = obtener_presentaciones(idLinea)

    if df_present.empty:
        st.info("No hay presentaciones registradas para esta línea.")
    else:
        st.dataframe(df_present, use_container_width=True)

    # Agregar presentación
    st.markdown("#### Agregar Presentación a la Línea")

    with st.form("form_presentacion", clear_on_submit=True):
        nombre_present = st.text_input("Nombre de presentación", placeholder="Ej: Caja 12u, Bolsa 90g")
        guardar_pres = st.form_submit_button("Agregar Presentación")

        if guardar_pres:
            if not nombre_present:
                st.warning("Ingrese un nombre válido para la presentación.")
            else:
                insertar_presentacion(nombre_present, idLinea)
                st.success(f"Presentación '{nombre_present}' registrada correctamente.")
                st.rerun()

    # Eliminar presentación
    if not df_present.empty:
        st.markdown("#### Eliminar Presentación")
        pres_sel = st.selectbox("Seleccione una presentación para eliminar", df_present["nombrePresentacion"])
        idPresentacion = int(df_present.loc[df_present["nombrePresentacion"] == pres_sel, "idPresentacion"].iloc[0])

        if st.button("Eliminar Presentación"):
            eliminar_presentacion(idPresentacion)
            st.warning(f"Presentación '{pres_sel}' eliminada correctamente.")
            st.rerun()

    st.markdown("---")
    st.subheader("Eliminar Línea de Producción")

    linea_delete = st.selectbox("Seleccione una línea para eliminar", df_lineas["nombreLinea"], key="delete_line")

    if st.button("Eliminar Línea"):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM LineaProduccion WHERE nombreLinea = %s", (linea_delete,))
        conn.commit()
        conn.close()
        st.warning(f"Línea '{linea_delete}' eliminada correctamente.")
        st.rerun()
