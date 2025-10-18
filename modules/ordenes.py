import streamlit as st
import pandas as pd
from datetime import date
from database.db_connection import get_connection

# =====================================================
# FUNCIONES DE BASE DE DATOS
# =====================================================

def obtener_lineas():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT idLinea, nombreLinea FROM LineaProduccion ORDER BY nombreLinea;")
    lineas = cursor.fetchall()
    conn.close()
    return lineas


def insertar_orden(fecha, semana, dia, turno, id_linea):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO OrdenTrabajo (fecha, semana, dia, turno, idLinea)
        VALUES (%s, %s, %s, %s, %s)
    """, (fecha, semana, dia, turno, id_linea))
    conn.commit()
    id_orden = cursor.lastrowid
    conn.close()
    return id_orden


def insertar_detalle(id_orden, descripcion, receta, fecha_venc, lote, plan, observacion,
                    presentacion, rendimiento_receta, rendimiento_cajasB,
                    produccion_unidades, produccion_cajasB):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO DetalleOrdenTrabajo (
            descripcionProducto, receta, fechaVencimiento, lote, plan, observacion,
            presentacion, rendimientoReceta, rendimientoCajasB,
            produccionUnidades, produccionCajasB, idOrden
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, (descripcion, receta, fecha_venc, lote, plan, observacion, presentacion,
        rendimiento_receta, rendimiento_cajasB, produccion_unidades, produccion_cajasB, id_orden))
    conn.commit()
    conn.close()


def obtener_ordenes():
    conn = get_connection()
    query = """
        SELECT o.idOrdenTrabajo AS ID, o.fecha, o.semana, o.dia, o.turno, l.nombreLinea AS linea
        FROM OrdenTrabajo o
        INNER JOIN LineaProduccion l ON o.idLinea = l.idLinea
        ORDER BY o.fecha DESC;
    """
    df = pd.read_sql(query, conn)
    conn.close()
    return df


def obtener_detalles(id_orden):
    conn = get_connection()
    query = """
        SELECT descripcionProducto AS 'Descripción del Producto',
            receta AS Receta,
            lote AS Lote,
            fechaVencimiento AS 'Fecha Vencimiento',
            plan AS Plan,
            presentacion AS Presentación,
            rendimientoReceta AS 'Rend. Receta',
            rendimientoCajasB AS 'Rend. Cajas B',
            produccionUnidades AS 'Prod. Unidades',
            produccionCajasB AS 'Prod. Cajas B',
            observacion AS Observaciones
        FROM DetalleOrdenTrabajo
        WHERE idOrden = %s;
    """
    df = pd.read_sql(query, conn, params=(id_orden,))
    conn.close()
    return df

# =====================================================
# INTERFAZ STREAMLIT
# =====================================================

def gestionar_ordenes():
    st.title("📋 REGISTRO DE ÓRDENES DE PRODUCCIÓN - Gustossi S.R.L.")
    st.markdown("---")

    lineas = obtener_lineas()
    if not lineas:
        st.warning("⚠️ No existen líneas de producción registradas.")
        return

    menu = st.sidebar.radio("Menú de Órdenes", ["Registrar Nueva Orden", "Consultar Órdenes"])

    # ---------------------------------------------
    # SECCIÓN 1: REGISTRO DE NUEVA ORDEN
    # ---------------------------------------------
    if menu == "Registrar Nueva Orden":
        st.subheader("🆕 Nueva Orden de Producción")

        linea_nombre = st.selectbox("Línea de Producción", [l[1] for l in lineas])
        id_linea = next(l[0] for l in lineas if l[1] == linea_nombre)
        fecha = st.date_input("Fecha de Producción", value=date.today())
        semana = fecha.isocalendar()[1]
        dia = fecha.strftime("%A").capitalize()
        turno = st.selectbox("Turno", ["T1-8H", "T2-8H", "T3-8H"])

        st.write(f"**Semana:** {semana} | **Día:** {dia}")

        if st.button("💾 Crear Orden de Producción"):
            id_orden = insertar_orden(fecha, semana, dia, turno, id_linea)
            st.session_state["orden_activa"] = id_orden
            st.success(f"✅ Orden creada para la línea **{linea_nombre}** en turno **{turno}**.")
            st.rerun()

        if "orden_activa" in st.session_state:
            id_orden = st.session_state["orden_activa"]
            st.markdown("### ➕ Agregar Productos / Detalles de Producción")

            with st.form("detalle_form"):
                descripcion = st.text_input("Descripción del Producto", placeholder="Ej: Galleta de Agua 90g")
                receta = st.text_input("Receta", placeholder="Ej: 0909-10")
                lote = st.text_input("Lote", placeholder="Ej: 2109-10")
                fecha_venc = st.date_input("Fecha de Vencimiento", value=date.today())
                plan = st.number_input("Plan (kg o recetas)", min_value=0.0, step=0.1)
                presentacion = st.text_input("Presentación", placeholder="Ej: Caja 12u o Bolsa 90g")
                rendimiento_receta = st.number_input("Rendimiento Receta", min_value=0)
                rendimiento_cajasB = st.number_input("Rendimiento Cajas B", min_value=0)
                produccion_unidades = st.number_input("Producción Unidades", min_value=0)
                produccion_cajasB = st.number_input("Producción Cajas B", min_value=0)
                observacion = st.text_area("Observaciones")

                agregar = st.form_submit_button("Agregar Detalle")

                if agregar:
                    insertar_detalle(id_orden, descripcion, receta, fecha_venc, lote, plan, observacion,
                                    presentacion, rendimiento_receta, rendimiento_cajasB,
                                    produccion_unidades, produccion_cajasB)
                    st.success(f"✅ Detalle del producto '{descripcion}' agregado correctamente.")

            st.markdown("#### Detalles registrados en esta orden:")
            detalles_df = obtener_detalles(id_orden)
            if not detalles_df.empty:
                st.dataframe(detalles_df, use_container_width=True)
            else:
                st.info("No hay productos registrados aún para esta orden.")

    # ---------------------------------------------
    # SECCIÓN 2: CONSULTA DE ÓRDENES
    # ---------------------------------------------
    elif menu == "Consultar Órdenes":
        st.subheader("🔍 Consultar Órdenes de Producción")

        df_ordenes = obtener_ordenes()
        if df_ordenes.empty:
            st.info("No hay órdenes registradas.")
            return

        semana_actual = date.today().isocalendar()[1]
        linea_filtro = st.selectbox("Filtrar por Línea", ["Todas"] + [l[1] for l in lineas])
        semana_filtro = st.number_input("Filtrar por Semana", min_value=1, max_value=53, step=1, value=semana_actual)

        if not df_ordenes.empty:
            if linea_filtro != "Todas":
                df_ordenes = df_ordenes[df_ordenes["linea"] == linea_filtro]
            if semana_filtro:
                df_ordenes = df_ordenes[df_ordenes["semana"] == semana_filtro]

        st.dataframe(df_ordenes, use_container_width=True)

        id_sel = st.number_input("Ingrese el ID de la Orden para ver detalles", min_value=1, step=1)
        if st.button("Ver Detalles"):
            detalles = obtener_detalles(id_sel)
            if detalles.empty:
                st.warning("No existen detalles para esa orden.")
            else:
                st.subheader(f"📦 Detalles de la Orden #{id_sel}")
                st.dataframe(detalles, use_container_width=True)


if __name__ == "__main__":
    gestionar_ordenes()
