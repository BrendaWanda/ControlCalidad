import streamlit as st
from database.db_connection import get_connection
import pandas as pd

def gestionar_lineas():
    st.title("Gestión de Líneas de Producción")
    st.markdown("---")

    # ===================================
    # Mostrar todas las líneas existentes
    # ===================================
    conn = get_connection()
    df = pd.read_sql("SELECT idLinea AS ID, nombreLinea AS 'Línea de Producción' FROM LineaProduccion", conn)
    conn.close()

    st.subheader("Líneas Registradas")
    st.dataframe(df, use_container_width=True)

    st.markdown("---")

    # ===================================
    # Agregar nueva línea
    # ===================================
    st.subheader("Agregar Nueva Línea")
    with st.form("form_linea", clear_on_submit=True):
        nombre = st.text_input("Nombre de la línea", placeholder="Ej: Línea de Galletas de Coco")
        guardar = st.form_submit_button("Guardar")

        if guardar and nombre:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO LineaProduccion (nombreLinea) VALUES (%s)", (nombre,))
            conn.commit()
            conn.close()
            st.success(f"Línea '{nombre}' registrada correctamente.")
            st.rerun()
        elif guardar:
            st.warning("Ingrese un nombre válido antes de guardar.")

    st.markdown("---")

    # ===================================
    # Eliminar línea
    # ===================================
    st.subheader("Eliminar Línea de Producción")
    if not df.empty:
        linea_sel = st.selectbox("Seleccione una línea para eliminar", df["Línea de Producción"])
        if st.button("Eliminar Línea"):
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM LineaProduccion WHERE nombreLinea = %s", (linea_sel,))
            conn.commit()
            conn.close()
            st.warning(f"Línea '{linea_sel}' eliminada correctamente.")
            st.rerun()
    else:
        st.info("No hay líneas registradas para eliminar.")
