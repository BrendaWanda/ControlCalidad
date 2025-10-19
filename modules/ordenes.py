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


def insertar_orden(codigoorden, fecha, semana, dia, turno, idLinea):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO OrdenTrabajo (codigoOrden, fecha, semana, dia, turno, idLinea)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (codigoorden, fecha, semana, dia, turno, idLinea))
    conn.commit()
    id_orden = cursor.lastrowid
    conn.close()
    return id_orden


def insertar_detalle(idOrden, descripcionProducto, receta, fechaVencimiento, lote, plan, observacion,
                    presentacion, rendimientoReceta, rendimientoCajasB,
                    produccionUnidades, produccionCajasB, descripcion, cantidad):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO DetalleOrdenTrabajo (
            descripcionProducto, receta, fechaVencimiento, lote, plan, observacion,
            presentacion, rendimientoReceta, rendimientoCajasB,
            produccionUnidades, produccionCajasB, descripcion, cantidad, idOrden
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, (descripcionProducto, receta, fechaVencimiento, lote, plan, observacion, presentacion,
        rendimientoReceta, rendimientoCajasB, produccionUnidades, produccionCajasB, descripcion, cantidad, idOrden))
    conn.commit()
    conn.close()


def obtener_ordenes():
    conn = get_connection()
    query = """
        SELECT 
            o.idOrdenTrabajo AS ID,
            o.codigoOrden,
            o.fecha,
            o.semana,
            o.dia,
            o.turno,
            l.nombreLinea AS Linea
        FROM OrdenTrabajo o
        INNER JOIN LineaProduccion l ON o.idLinea = l.idLinea
        ORDER BY o.fecha DESC;
    """
    df = pd.read_sql(query, conn)
    conn.close()
    return df


def obtener_detalles(idOrden):
    conn = get_connection()
    query = """
        SELECT 
            descripcionProducto AS 'Descripción del Producto',
            receta AS Receta,
            lote AS Lote,
            fechaVencimiento AS 'Fecha de Vencimiento',
            plan AS Plan,
            presentacion AS Presentación,
            rendimientoReceta AS 'Rend. Receta',
            rendimientoCajasB AS 'Rend. Cajas (B)',
            produccionUnidades AS 'Prod. Unidades',
            produccionCajasB AS 'Prod. Cajas (B)',
            descripcion AS Descripción,
            cantidad AS Cantidad,
            observacion AS Observaciones
        FROM DetalleOrdenTrabajo
        WHERE idOrden = %s;
    """
    df = pd.read_sql(query, conn, params=(idOrden,))
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

    # =====================================================
    # SECCIÓN 1: REGISTRO DE NUEVA ORDEN
    # =====================================================
    if menu == "Registrar Nueva Orden":
        st.subheader("🆕 Nueva Orden de Producción")

        linea_nombre = st.selectbox("Línea de Producción", ["— Seleccionar Línea —"] + [l[1] for l in lineas])
        if linea_nombre == "— Seleccionar Línea —":
            st.info("Seleccione una línea de producción para continuar.")
            return

        idLinea = next(l[0] for l in lineas if l[1] == linea_nombre)
        codigoorden = st.text_input("Código de Orden", placeholder="Ej: OP-2025-0109")
        fecha = st.date_input("Fecha de Producción", value=date.today())
        semana = fecha.isocalendar()[1]
        dia = fecha.strftime("%A").capitalize()
        turno = st.selectbox("Turno", ["T1-8H", "T2-8H", "T3-8H"])

        st.write(f"**Semana:** {semana} | **Día:** {dia}")

        if st.button("💾 Crear Orden de Producción"):
            if not codigoorden:
                st.warning("⚠️ Debe ingresar un código de orden.")
            else:
                id_orden = insertar_orden(codigoorden, fecha, semana, dia, turno, idLinea)
                st.session_state["orden_activa"] = id_orden
                st.session_state["codigo_activo"] = codigoorden
                st.success(f"✅ Orden **{codigoorden}** creada para la línea **{linea_nombre}** en turno **{turno}**.")
                st.rerun()

        if "orden_activa" in st.session_state:
            idOrden = st.session_state["orden_activa"]
            codigo_activo = st.session_state["codigo_activo"]
            st.markdown(f"### ➕ Agregar Productos / Detalles de Producción — Orden {codigo_activo}")

            with st.form("detalle_form", clear_on_submit=True):
                descripcionProducto = st.text_input("Descripción del Producto", placeholder="Ej: Galleta de Coco 90g")
                receta = st.text_input("Receta", placeholder="Ej: RC-001")
                lote = st.text_input("Lote", placeholder="Ej: L-2025-0109")
                fechaVencimiento = st.date_input("Fecha de Vencimiento", value=date.today())
                plan = st.number_input("Plan (kg o recetas)", min_value=0.0, step=0.1)
                presentacion = st.text_input("Presentación", placeholder="Ej: Caja 12u o Bolsa 90g")
                rendimientoReceta = st.number_input("Rendimiento Receta", min_value=0.0, step=0.1)
                rendimientoCajasB = st.number_input("Rendimiento Cajas B", min_value=0.0, step=0.1)
                produccionUnidades = st.number_input("Producción Unidades", min_value=0)
                produccionCajasB = st.number_input("Producción Cajas B", min_value=0)
                descripcion = st.text_area("Descripción del Proceso / Nota")
                cantidad = st.number_input("Cantidad (Unidades o Cajas)", min_value=0)
                observacion = st.text_area("Observaciones Generales")

                agregar = st.form_submit_button("Agregar Detalle")

                if agregar:
                    if not descripcionProducto:
                        st.warning("⚠️ Debe ingresar la descripción del producto.")
                    else:
                        insertar_detalle(idOrden, descripcionProducto, receta, fechaVencimiento, lote, plan, observacion,
                                        presentacion, rendimientoReceta, rendimientoCajasB,
                                        produccionUnidades, produccionCajasB, descripcion, cantidad)
                        st.success(f"✅ Detalle del producto **'{descripcionProducto}'** agregado correctamente.")
                        st.rerun()

            st.markdown("#### 📦 Detalles registrados en esta orden:")
            detalles_df = obtener_detalles(idOrden)
            if not detalles_df.empty:
                st.dataframe(detalles_df, use_container_width=True)
            else:
                st.info("ℹ️ No hay productos registrados aún para esta orden.")

    # =====================================================
    # SECCIÓN 2: CONSULTA DE ÓRDENES
    # =====================================================
    elif menu == "Consultar Órdenes":
        st.subheader("🔍 Consultar Órdenes de Producción")
        st.markdown("Filtra las órdenes por fecha, semana, día, turno o línea de producción.")
        st.markdown("---")

        df_ordenes = obtener_ordenes()

        if df_ordenes.empty:
            st.info("ℹ️ No hay órdenes registradas.")
            return

        df_ordenes["fecha"] = pd.to_datetime(df_ordenes["fecha"]).dt.date

        # 🎛️ Controles de filtro (sin errores de None)
        col1, col2, col3 = st.columns(3)
        with col1:
            fecha_filtro = st.date_input("📅 Fecha específica", value=date.today())
            usar_fecha = st.checkbox("Usar filtro de fecha", value=False)
        with col2:
            semana_filtro = st.number_input("📆 Semana ISO", min_value=0, max_value=53, step=1, value=0)
        with col3:
            dia_filtro = st.selectbox("🗓️ Día de la Semana", ["Todos", "Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"])

        col4, col5 = st.columns(2)
        with col4:
            turno_filtro = st.selectbox("🕐 Turno", ["Todos", "T1-8H", "T2-8H", "T3-8H"])
        with col5:
            linea_filtro = st.selectbox("🏭 Línea de Producción", ["Todas"] + [l[1] for l in lineas])

        codigo_buscar = st.text_input("🔤 Buscar por Código de Orden", placeholder="Ej: OP-2025-0109")

        df_filtrado = df_ordenes.copy()

        if usar_fecha:
            df_filtrado = df_filtrado[df_filtrado["fecha"] == fecha_filtro]
        if semana_filtro and semana_filtro != 0:
            df_filtrado = df_filtrado[df_filtrado["semana"] == semana_filtro]
        if dia_filtro != "Todos":
            df_filtrado = df_filtrado[df_filtrado["dia"].str.lower() == dia_filtro.lower()]
        if turno_filtro != "Todos":
            df_filtrado = df_filtrado[df_filtrado["turno"] == turno_filtro]
        if linea_filtro != "Todas":
            df_filtrado = df_filtrado[df_filtrado["Linea"] == linea_filtro]
        if codigo_buscar:
            df_filtrado = df_filtrado[df_filtrado["codigoOrden"].str.contains(codigo_buscar, case=False, na=False)]

        st.markdown("### 📋 Órdenes encontradas")
        if not df_filtrado.empty:
            st.dataframe(df_filtrado, use_container_width=True)
        else:
            st.info("⚠️ No se encontraron órdenes con los criterios seleccionados.")


# =====================================================
# EJECUCIÓN DIRECTA
# =====================================================
if __name__ == "__main__":
    gestionar_ordenes()
