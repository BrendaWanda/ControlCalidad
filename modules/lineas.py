import streamlit as st
from database.db_connection import get_connection
import pandas as pd

# CONSULTAS A BASE DE DATOS

def obtener_lineas():
    conn = get_connection()
    df = pd.read_sql("SELECT idLinea, nombreLinea FROM LineaProduccion ORDER BY nombreLinea", conn)
    conn.close()
    return df

def obtener_presentaciones(idLinea):
    conn = get_connection()
    df = pd.read_sql("""
        SELECT idPresentacion, nombrePresentacion, codigoPresentacion
        FROM PresentacionProducto 
        WHERE idLinea = %s
        ORDER BY nombrePresentacion
    """, conn, params=(idLinea,))
    conn.close()
    return df

def obtener_parametros(idPresentacion):
    conn = get_connection()
    df = pd.read_sql("""
        SELECT 
            idPresentacionParametro,
            idParametro,
            limiteInferior,
            limiteSuperior,
            unidadMedida,
            tipoParametro
        FROM presentacionparametro
        WHERE idPresentacion = %s
    """, conn, params=(idPresentacion,))
    conn.close()
    return df

# INSERTAR

def insertar_linea(nombre):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO LineaProduccion (nombreLinea) VALUES (%s)", (nombre,))
    conn.commit()
    conn.close()

def insertar_presentacion(nombre, codigo, idLinea):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO PresentacionProducto (nombrePresentacion, codigoPresentacion, idLinea)
        VALUES (%s, %s, %s)
    """, (nombre, codigo, idLinea))
    conn.commit()
    conn.close()

def insertar_parametro(idPresentacion, idParametro, inf, sup, unidad, tipo):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO presentacionparametro 
        (idPresentacion, idParametro, limiteInferior, limiteSuperior, unidadMedida, tipoParametro)
        VALUES (%s,%s,%s,%s,%s,%s)
    """, (idPresentacion, idParametro, inf, sup, unidad, tipo))
    conn.commit()
    conn.close()

# EDITAR

def editar_linea(idLinea, nuevo_nombre):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE LineaProduccion SET nombreLinea = %s WHERE idLinea = %s", (nuevo_nombre, idLinea))
    conn.commit()
    conn.close()

def editar_presentacion(idPresentacion, nuevo_nombre, nuevo_codigo):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE PresentacionProducto
        SET nombrePresentacion = %s, codigoPresentacion = %s
        WHERE idPresentacion = %s
    """, (nuevo_nombre, nuevo_codigo, idPresentacion))
    conn.commit()
    conn.close()

def editar_parametro(idPP, inf, sup, unidad, tipo):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE presentacionparametro
        SET limiteInferior=%s, limiteSuperior=%s, unidadMedida=%s, tipoParametro=%s
        WHERE idPresentacionParametro=%s
    """, (inf, sup, unidad, tipo, idPP))
    conn.commit()
    conn.close()

# ELIMINAR

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

def eliminar_parametro(idPP):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM presentacionparametro WHERE idPresentacionParametro = %s", (idPP,))
    conn.commit()
    conn.close()

# INTERFAZ PRINCIPAL

def gestionar_lineas():
    st.title("Gestión de Líneas y Presentaciones")
    st.markdown("---")

    df_lineas = obtener_lineas()

    # LÍNEAS – LISTAR / EDITAR / ELIMINAR / AGREGAR

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Líneas registradas")
        st.dataframe(df_lineas, use_container_width=True)

        # Nuevo: editar línea
        st.subheader("Editar Línea")
        if not df_lineas.empty:
            linea_sel_editar = st.selectbox("Seleccione línea", df_lineas["nombreLinea"], key="edit_linea")
            idLinea_edit = int(df_lineas[df_lineas["nombreLinea"] == linea_sel_editar]["idLinea"].iloc[0])

            nuevo_nombre = st.text_input("Nuevo nombre", value=linea_sel_editar)

            if st.button("Actualizar línea"):
                editar_linea(idLinea_edit, nuevo_nombre)
                st.success("Línea actualizada")
                st.rerun()

        # Nuevo: eliminar línea
        st.subheader("Eliminar Línea")
        if not df_lineas.empty:
            linea_sel_del = st.selectbox("Seleccione línea a eliminar", df_lineas["nombreLinea"], key="del_linea")
            idLinea_del = int(df_lineas[df_lineas["nombreLinea"] == linea_sel_del]["idLinea"].iloc[0])

            if st.button("Eliminar línea"):
                eliminar_linea(idLinea_del)
                st.warning("Línea eliminada")
                st.rerun()

    with col2:
        st.subheader("Nueva Línea")
        with st.form("f_linea"):
            nombre = st.text_input("Nombre")
            if st.form_submit_button("Guardar"):
                insertar_linea(nombre)
                st.success("Registrado")
                st.rerun()

    # PRESENTACIONES
    st.markdown("---")
    st.subheader("Presentaciones por Línea")

    linea_sel = st.selectbox("Seleccione Línea", df_lineas["nombreLinea"])
    idLinea = int(df_lineas[df_lineas["nombreLinea"] == linea_sel]["idLinea"].iloc[0])

    df_pres = obtener_presentaciones(idLinea)
    col3, col4 = st.columns(2)

    with col3:
        st.dataframe(df_pres, use_container_width=True)

        # Editar presentación
        st.subheader("Editar Presentación")
        if not df_pres.empty:
            pres_sel = st.selectbox("Presentación", df_pres["nombrePresentacion"])
            fila = df_pres[df_pres["nombrePresentacion"] == pres_sel].iloc[0]

            nuevo_nombre = st.text_input("Nuevo nombre", value=fila["nombrePresentacion"])
            nuevo_codigo = st.text_input("Nuevo código", value=fila["codigoPresentacion"])

            if st.button("Actualizar presentación"):
                editar_presentacion(fila["idPresentacion"], nuevo_nombre, nuevo_codigo)
                st.success("Actualizado")
                st.rerun()

        # Eliminar presentación
        st.subheader("Eliminar Presentación")
        if not df_pres.empty:
            pres_del = st.selectbox("Eliminar", df_pres["nombrePresentacion"], key="del_pres")
            idPres_del = int(df_pres[df_pres["nombrePresentacion"] == pres_del]["idPresentacion"].iloc[0])

            if st.button("Eliminar presentación"):
                eliminar_presentacion(idPres_del)
                st.warning("Eliminado")
                st.rerun()

    with col4:
        st.subheader("Nueva Presentación")
        with st.form("f_pres"):
            nombre = st.text_input("Nombre presentación")
            codigo = st.text_input("Código presentación")
            if st.form_submit_button("Guardar"):
                insertar_presentacion(nombre, codigo, idLinea)
                st.success("Registrado")
                st.rerun()