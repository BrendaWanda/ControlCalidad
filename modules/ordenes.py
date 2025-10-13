import streamlit as st
from database.db_connection import get_connection
import pandas as pd
from datetime import date

# ==========================================================
# FUNCIONES DE BASE DE DATOS
# ==========================================================

def obtener_lineas():
    """Obtiene las líneas de producción registradas."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT idLinea, nombreLinea FROM LineaProduccion")
        lineas = cursor.fetchall()
        conn.close()
        return lineas
    except Exception as e:
        st.error(f"Error al obtener líneas de producción: {e}")
        return []

def insertar_orden(codigo, fecha, id_linea):
    """Crea una nueva orden de trabajo."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO OrdenTrabajo (codigoOrden, fecha, idLinea)
            VALUES (%s, %s, %s)
        """, (codigo, fecha, id_linea))
        conn.commit()
        id_orden = cursor.lastrowid
        conn.close()
        return id_orden
    except Exception as e:
        st.error(f"Error al insertar orden: {e}")
        return None

def insertar_detalle(descripcion, cantidad, id_orden):
    """Registra los productos o detalles asociados a una orden."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO DetalleOrdenTrabajo (descripcion, cantidad, idOrdenTrabajo)
            VALUES (%s, %s, %s)
        """, (descripcion, cantidad, id_orden))
        conn.commit()
        conn.close()
    except Exception as e:
        st.error(f"Error al insertar detalle: {e}")

def obtener_ordenes():
    """Obtiene todas las órdenes con su línea de producción."""
    try:
        conn = get_connection()
        df = pd.read_sql("""
            SELECT 
                o.idOrdenTrabajo AS ID,
                o.codigoOrden AS Código,
                o.fecha AS Fecha,
                l.nombreLinea AS Línea
            FROM OrdenTrabajo o
            JOIN LineaProduccion l ON o.idLinea = l.idLinea
            ORDER BY o.fecha DESC
        """, conn)
        conn.close()
        return df
    except Exception as e:
        st.error(f"Error al obtener órdenes: {e}")
        return pd.DataFrame()

def actualizar_orden(id_orden, codigo, fecha, id_linea):
    """Actualiza los datos de una orden existente."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE OrdenTrabajo
            SET codigoOrden = %s, fecha = %s, idLinea = %s
            WHERE idOrdenTrabajo = %s
        """, (codigo, fecha, id_linea, id_orden))
        conn.commit()
        conn.close()
    except Exception as e:
        st.error(f"Error al actualizar la orden: {e}")

# ==========================================================
# INTERFAZ DE STREAMLIT
# ==========================================================
def gestionar_ordenes():
    st.title("Gestión de Órdenes de Producción")
    st.markdown("---")

    # Obtener líneas de producción disponibles
    lineas = obtener_lineas()
    if not lineas:
        st.warning("No hay líneas de producción registradas. Agrega una en 'Líneas de Producción'.")
        return

    menu = st.sidebar.radio("Menú de Órdenes", [
        "Crear Nueva Orden",
        "Editar / Consultar Órdenes"
    ])

    # ======================================================
    # CREAR NUEVA ORDEN
    # ======================================================
    if menu == "Crear Nueva Orden":
        st.subheader("Crear Orden de Producción")

        codigo = st.text_input("Código de Orden", placeholder="Ej: OP-2025-0109")
        fecha = st.date_input("Fecha Programada", value=date.today())

        linea_nombre = st.selectbox("Línea de Producción", [l[1] for l in lineas])
        id_linea = next(l[0] for l in lineas if l[1] == linea_nombre)

        st.markdown("### Agregar Productos / Detalles")
        with st.form("form_detalles"):
            descripcion = st.text_input("Descripción del producto", placeholder="Ej: Galleta de Coco 90g")
            cantidad = st.number_input("Cantidad a Elaborar (unidades)", min_value=1, step=1)
            guardar = st.form_submit_button("Guardar Orden")

            if guardar:
                if not codigo:
                    st.warning("Debes ingresar un código de orden.")
                elif not descripcion:
                    st.warning("Debes ingresar al menos una descripción del producto.")
                else:
                    id_orden = insertar_orden(codigo, fecha, id_linea)
                    insertar_detalle(descripcion, cantidad, id_orden)
                    st.success(f"Orden '{codigo}' registrada correctamente en la línea '{linea_nombre}'.")

    # ======================================================
    # CONSULTAR / EDITAR ÓRDENES
    # ======================================================
    elif menu == "Editar / Consultar Órdenes":
        st.subheader("Consultar y Editar Órdenes Existentes")
        df_ordenes = obtener_ordenes()

        if df_ordenes.empty:
            st.info("No hay órdenes registradas.")
            return

        filtro_linea = st.selectbox("Filtrar por Línea", ["Todas"] + [l[1] for l in lineas])
        filtro_fecha = st.date_input("Filtrar por Fecha", value=None)

        # Aplicar filtros
        if filtro_linea != "Todas":
            df_ordenes = df_ordenes[df_ordenes["Línea"] == filtro_linea]
        if filtro_fecha:
            df_ordenes = df_ordenes[df_ordenes["Fecha"].dt.date == filtro_fecha]

        st.dataframe(df_ordenes, use_container_width=True)

        st.markdown("---")
        id_editar = st.number_input("Ingrese el ID de la orden a editar:", min_value=1, step=1)

        if st.button("✏️ Editar Orden"):
            orden_sel = df_ordenes[df_ordenes["ID"] == id_editar]
            if orden_sel.empty:
                st.warning("No se encontró ninguna orden con ese ID.")
            else:
                codigo = st.text_input("Nuevo Código de Orden", value=orden_sel.iloc[0]["Código"])
                fecha = st.date_input("Nueva Fecha", value=orden_sel.iloc[0]["Fecha"].date())
                linea_nombre = st.selectbox(
                    "Nueva Línea",
                    [l[1] for l in lineas],
                    index=[l[1] for l in lineas].index(orden_sel.iloc[0]["Línea"])
                )
                id_linea = next(l[0] for l in lineas if l[1] == linea_nombre)

                if st.button("Guardar Cambios"):
                    actualizar_orden(id_editar, codigo, fecha, id_linea)
                    st.success("Orden actualizada correctamente.")
                    st.rerun()

# ==========================================================
# EJECUCIÓN DIRECTA (solo para pruebas)
# ==========================================================
if __name__ == "__main__":
    gestionar_ordenes()
