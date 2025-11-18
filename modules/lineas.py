import streamlit as st
from database.db_connection import get_connection
import pandas as pd

# ==========================================================
# CONSULTAS A BASE DE DATOS
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


# ------------------ INSERTAR ------------------

def insertar_linea(nombre):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO LineaProduccion (nombreLinea) VALUES (%s)", (nombre,))
    conn.commit()
    conn.close()

def insertar_presentacion(nombre, idLinea):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO PresentacionProducto (nombrePresentacion, idLinea)
        VALUES (%s, %s)
    """, (nombre, idLinea))
    conn.commit()
    conn.close()


# ------------------ EDITAR ------------------

def editar_linea(idLinea, nuevo_nombre):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE LineaProduccion
        SET nombreLinea = %s
        WHERE idLinea = %s
    """, (nuevo_nombre, idLinea))
    conn.commit()
    conn.close()

def editar_presentacion(idPresentacion, nuevo_nombre):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE PresentacionProducto
        SET nombrePresentacion = %s
        WHERE idPresentacion = %s
    """, (nuevo_nombre, idPresentacion))
    conn.commit()
    conn.close()


# ------------------ ELIMINAR ------------------

def eliminar_presentacion(idPresentacion):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM PresentacionProducto WHERE idPresentacion = %s", (idPresentacion,))
    conn.commit()
    conn.close()

def eliminar_linea(idLinea):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM LineaProduccion WHERE idLinea = %s", (idLinea,))
    conn.commit()
    conn.close()


# ==========================================================
# INTERFAZ PRINCIPAL
# ==========================================================

def gestionar_lineas():
    st.title("🧱 Gestión de Líneas de Producción")
    st.markdown("---")

    df_lineas = obtener_lineas()

    # -------------------------------------------------------
    # LISTA DE LÍNEAS
    # -------------------------------------------------------
    st.subheader("📋 Líneas Registradas")

    if df_lineas.empty:
        st.info("No hay líneas registradas.")
    else:
        st.dataframe(df_lineas, use_container_width=True)

    st.markdown("---")

    # -------------------------------------------------------
    # AGREGAR NUEVA LÍNEA
    # -------------------------------------------------------
    st.subheader("➕ Agregar Nueva Línea")

    with st.form("form_linea_add", clear_on_submit=True):
        nombre_linea = st.text_input("Nombre de la línea", placeholder="Ej: Línea Galletería")
        guardar = st.form_submit_button("Guardar")

        if guardar:
            if not nombre_linea:
                st.warning("Ingrese un nombre válido.")
            elif nombre_linea.strip().lower() in df_lineas["nombreLinea"].str.lower().values:
                st.error("Ya existe una línea con ese nombre.")
            else:
                insertar_linea(nombre_linea)
                st.success(f"Línea '{nombre_linea}' agregada correctamente.")
                st.rerun()

    st.markdown("---")

    # -------------------------------------------------------
    # EDITAR O ELIMINAR LÍNEA
    # -------------------------------------------------------
    st.subheader("🛠 Editar o Eliminar Línea")

    if not df_lineas.empty:
        col1, col2 = st.columns(2)

        with col1:
            linea_sel = st.selectbox("Seleccione una línea", df_lineas["nombreLinea"])
            idLinea = int(df_lineas.loc[df_lineas["nombreLinea"] == linea_sel, "idLinea"].iloc[0])

            nuevo_nombre = st.text_input("Nuevo nombre", value=linea_sel)

            if st.button("Guardar cambios"):
                if nuevo_nombre.strip() == "":
                    st.warning("El nombre no puede estar vacío.")
                elif nuevo_nombre.strip().lower() in df_lineas["nombreLinea"].str.lower().values:
                    st.error("Ya existe otra línea con ese nombre.")
                else:
                    editar_linea(idLinea, nuevo_nombre)
                    st.success("Nombre actualizado correctamente.")
                    st.rerun()

        with col2:
            df_present = obtener_presentaciones(idLinea)
            if st.button("Eliminar línea"):
                if not df_present.empty:
                    st.error("No se puede eliminar: la línea tiene presentaciones registradas.")
                else:
                    eliminar_linea(idLinea)
                    st.warning(f"Línea '{linea_sel}' eliminada.")
                    st.rerun()

    st.markdown("---")

    # -------------------------------------------------------
    # PRESENTACIONES
    # -------------------------------------------------------

    st.subheader("🎁 Administrar Presentaciones por Línea")

    if df_lineas.empty:
        st.info("Debe registrar líneas primero.")
        return

    linea_pres = st.selectbox("Seleccione una línea para ver sus presentaciones", df_lineas["nombreLinea"], key="linea_pres")

    idLinea_pres = int(df_lineas.loc[df_lineas["nombreLinea"] == linea_pres, "idLinea"].iloc[0])

    df_present = obtener_presentaciones(idLinea_pres)

    st.markdown(f"### Presentaciones de **{linea_pres}**")

    if df_present.empty:
        st.info("No hay presentaciones registradas.")
    else:
        st.dataframe(df_present, use_container_width=True)

    # -----------------------------------------
    # AGREGAR PRESENTACIÓN
    # -----------------------------------------
    st.markdown("#### ➕ Agregar Presentación")

    with st.form("form_present_add", clear_on_submit=True):
        nombre_present = st.text_input("Nombre de presentación", placeholder="Ej: Caja 12u, Bolsa 90g")
        add_pres = st.form_submit_button("Agregar")

        if add_pres:
            if not nombre_present:
                st.warning("Ingrese un nombre válido.")
            elif nombre_present.strip().lower() in df_present["nombrePresentacion"].str.lower().values:
                st.error("Ya existe esa presentación en la línea.")
            else:
                insertar_presentacion(nombre_present, idLinea_pres)
                st.success("Presentación registrada.")
                st.rerun()

    # -----------------------------------------
    # EDITAR PRESENTACIÓN
    # -----------------------------------------
    if not df_present.empty:
        st.markdown("#### 🛠 Editar Presentación")

        pres_sel = st.selectbox("Seleccionar presentación", df_present["nombrePresentacion"])

        idPresent = int(df_present.loc[df_present["nombrePresentacion"] == pres_sel, "idPresentacion"].iloc[0])

        nuevo_pres = st.text_input("Nuevo nombre", value=pres_sel, key="edit_pres")

        if st.button("Guardar cambios presentación"):
            if nuevo_pres.strip() == "":
                st.warning("El nombre no puede estar vacío.")
            elif nuevo_pres.strip().lower() in df_present["nombrePresentacion"].str.lower().values:
                st.error("Ya existe una presentación con ese nombre.")
            else:
                editar_presentacion(idPresent, nuevo_pres)
                st.success("Presentación actualizada.")
                st.rerun()

    # -----------------------------------------
    # ELIMINAR PRESENTACIÓN
    # -----------------------------------------
    if not df_present.empty:
        st.markdown("#### 🗑 Eliminar Presentación")

        pres_del = st.selectbox("Seleccione una presentación para eliminar", df_present["nombrePresentacion"], key="delete_pres")
        idPresDel = int(df_present.loc[df_present["nombrePresentacion"] == pres_del, "idPresentacion"].iloc[0])

        if st.button("Eliminar presentación"):
            eliminar_presentacion(idPresDel)
            st.warning(f"Presentación '{pres_del}' eliminada.")
            st.rerun()
